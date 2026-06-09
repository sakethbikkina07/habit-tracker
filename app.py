from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import sqlite3
import os
from datetime import date, timedelta, datetime

app = Flask(__name__)
CORS(app)

DB_PATH = os.path.join(os.path.dirname(__file__), "habits.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            icon TEXT DEFAULT '⭐',
            color TEXT DEFAULT '#6366f1',
            target_days INTEGER DEFAULT 7,
            created_at TEXT DEFAULT (date('now'))
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS completions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            habit_id INTEGER NOT NULL,
            completed_date TEXT NOT NULL,
            UNIQUE(habit_id, completed_date),
            FOREIGN KEY (habit_id) REFERENCES habits(id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    conn.close()

@app.route("/")
def index():
    return render_template("index.html")

# --- Habits CRUD ---
@app.route("/api/habits", methods=["GET"])
def get_habits():
    conn = get_db()
    habits = conn.execute("SELECT * FROM habits ORDER BY created_at").fetchall()
    today = str(date.today())
    result = []
    for h in habits:
        hid = h["id"]
        # streak
        streak = calc_streak(conn, hid, today)
        # total completions
        total = conn.execute("SELECT COUNT(*) FROM completions WHERE habit_id=?", (hid,)).fetchone()[0]
        # completed today
        done_today = conn.execute(
            "SELECT 1 FROM completions WHERE habit_id=? AND completed_date=?", (hid, today)
        ).fetchone() is not None
        # last 7 days for mini chart
        week = []
        for i in range(6, -1, -1):
            d = str(date.today() - timedelta(days=i))
            done = conn.execute("SELECT 1 FROM completions WHERE habit_id=? AND completed_date=?", (hid, d)).fetchone() is not None
            week.append({"date": d, "done": done})
        # completion rate (last 30 days)
        rate = calc_rate(conn, hid, 30)
        result.append({
            "id": hid,
            "name": h["name"],
            "icon": h["icon"],
            "color": h["color"],
            "target_days": h["target_days"],
            "created_at": h["created_at"],
            "streak": streak,
            "total": total,
            "done_today": done_today,
            "week": week,
            "rate": rate
        })
    conn.close()
    return jsonify(result)

@app.route("/api/habits", methods=["POST"])
def add_habit():
    data = request.json
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "Name is required"}), 400
    icon = data.get("icon", "⭐")
    color = data.get("color", "#6366f1")
    target_days = data.get("target_days", 7)
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO habits (name, icon, color, target_days) VALUES (?,?,?,?)",
              (name, icon, color, target_days))
    conn.commit()
    new_id = c.lastrowid
    conn.close()
    return jsonify({"id": new_id, "message": "Habit created"}), 201

@app.route("/api/habits/<int:habit_id>", methods=["PUT"])
def update_habit(habit_id):
    data = request.json
    conn = get_db()
    conn.execute("""
        UPDATE habits SET name=?, icon=?, color=?, target_days=? WHERE id=?
    """, (data["name"], data["icon"], data["color"], data["target_days"], habit_id))
    conn.commit()
    conn.close()
    return jsonify({"message": "Updated"})

@app.route("/api/habits/<int:habit_id>", methods=["DELETE"])
def delete_habit(habit_id):
    conn = get_db()
    conn.execute("DELETE FROM completions WHERE habit_id=?", (habit_id,))
    conn.execute("DELETE FROM habits WHERE id=?", (habit_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Deleted"})

# --- Completions ---
@app.route("/api/habits/<int:habit_id>/toggle", methods=["POST"])
def toggle(habit_id):
    data = request.json or {}
    day = data.get("date", str(date.today()))
    conn = get_db()
    existing = conn.execute(
        "SELECT id FROM completions WHERE habit_id=? AND completed_date=?", (habit_id, day)
    ).fetchone()
    if existing:
        conn.execute("DELETE FROM completions WHERE habit_id=? AND completed_date=?", (habit_id, day))
        done = False
    else:
        conn.execute("INSERT INTO completions (habit_id, completed_date) VALUES (?,?)", (habit_id, day))
        done = True
    conn.commit()
    conn.close()
    return jsonify({"done": done, "date": day})

# --- Analytics ---
@app.route("/api/stats")
def stats():
    conn = get_db()
    today = str(date.today())
    total_habits = conn.execute("SELECT COUNT(*) FROM habits").fetchone()[0]
    done_today = conn.execute(
        "SELECT COUNT(DISTINCT habit_id) FROM completions WHERE completed_date=?", (today,)
    ).fetchone()[0]
    # overall 30-day avg
    habits = conn.execute("SELECT id FROM habits").fetchall()
    rates = [calc_rate(conn, h["id"], 30) for h in habits]
    avg_rate = round(sum(rates) / len(rates), 1) if rates else 0
    # best streak across all habits
    best_streak = max([calc_streak(conn, h["id"], today) for h in habits], default=0)
    # Per-habit 7-day chart data
    per_habit = []
    for h in conn.execute("SELECT id, name, color FROM habits").fetchall():
        week_data = []
        for i in range(6, -1, -1):
            d = str(date.today() - timedelta(days=i))
            done = conn.execute(
                "SELECT 1 FROM completions WHERE habit_id=? AND completed_date=?", (h["id"], d)
            ).fetchone() is not None
            week_data.append({"date": d, "done": done})
        per_habit.append({"id": h["id"], "name": h["name"], "color": h["color"], "week": week_data})
    conn.close()
    return jsonify({
        "total_habits": total_habits,
        "done_today": done_today,
        "avg_rate": avg_rate,
        "best_streak": best_streak,
        "per_habit": per_habit
    })

def calc_streak(conn, habit_id, today_str):
    today_date = date.fromisoformat(today_str)
    streak = 0
    current = today_date
    while True:
        done = conn.execute(
            "SELECT 1 FROM completions WHERE habit_id=? AND completed_date=?",
            (habit_id, str(current))
        ).fetchone()
        if done:
            streak += 1
            current -= timedelta(days=1)
        else:
            break
    return streak

def calc_rate(conn, habit_id, days):
    created = conn.execute("SELECT created_at FROM habits WHERE id=?", (habit_id,)).fetchone()
    if not created:
        return 0
    created_date = date.fromisoformat(created["created_at"])
    today = date.today()
    start = max(today - timedelta(days=days - 1), created_date)
    total_days = (today - start).days + 1
    done_count = conn.execute(
        "SELECT COUNT(*) FROM completions WHERE habit_id=? AND completed_date >= ? AND completed_date <= ?",
        (habit_id, str(start), str(today))
    ).fetchone()[0]
    return round((done_count / total_days) * 100, 1) if total_days > 0 else 0

if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
