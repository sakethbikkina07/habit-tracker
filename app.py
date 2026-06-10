from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import secrets
from datetime import date, timedelta
from functools import wraps

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
CORS(app, supports_credentials=True)

DB_PATH = os.path.join(os.path.dirname(__file__), "habits.db")

# ─── DB ───
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE COLLATE NOCASE,
            email TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT (date('now'))
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            icon TEXT DEFAULT '⭐',
            color TEXT DEFAULT '#6366f1',
            target_days INTEGER DEFAULT 7,
            created_at TEXT DEFAULT (date('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
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

# ─── AUTH DECORATOR ───
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "Unauthorized", "redirect": "/login"}), 401
        return f(*args, **kwargs)
    return decorated

def get_current_user_id():
    return session.get('user_id')

# ─── PAGES ───
@app.route("/")
def index():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    return render_template("index.html")

@app.route("/login")
def login_page():
    if 'user_id' in session:
        return redirect(url_for('index'))
    return render_template("auth.html", page="login")

@app.route("/register")
def register_page():
    if 'user_id' in session:
        return redirect(url_for('index'))
    return render_template("auth.html", page="register")

# ─── AUTH API ───
@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.json or {}
    username = data.get("username", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not username or not email or not password:
        return jsonify({"error": "All fields are required"}), 400
    if len(username) < 3:
        return jsonify({"error": "Username must be at least 3 characters"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400
    if "@" not in email:
        return jsonify({"error": "Invalid email address"}), 400

    conn = get_db()
    existing = conn.execute(
        "SELECT id FROM users WHERE username=? OR email=?", (username, email)
    ).fetchone()
    if existing:
        conn.close()
        return jsonify({"error": "Username or email already exists"}), 409

    pw_hash = generate_password_hash(password)
    c = conn.cursor()
    c.execute("INSERT INTO users (username, email, password_hash) VALUES (?,?,?)",
              (username, email, pw_hash))
    conn.commit()
    user_id = c.lastrowid
    conn.close()

    session['user_id'] = user_id
    session['username'] = username
    return jsonify({"message": "Account created", "username": username}), 201

@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.json or {}
    identifier = data.get("identifier", "").strip()  # username or email
    password = data.get("password", "")

    if not identifier or not password:
        return jsonify({"error": "All fields are required"}), 400

    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE username=? OR email=?",
        (identifier, identifier.lower())
    ).fetchone()
    conn.close()

    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid username/email or password"}), 401

    session['user_id'] = user['id']
    session['username'] = user['username']
    return jsonify({"message": "Logged in", "username": user['username']})

@app.route("/api/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out"})

@app.route("/api/auth/me")
def me():
    if 'user_id' not in session:
        return jsonify({"error": "Not logged in"}), 401
    return jsonify({"user_id": session['user_id'], "username": session['username']})

# ─── HABITS API (all scoped to current user) ───
@app.route("/api/habits", methods=["GET"])
@login_required
def get_habits():
    uid = get_current_user_id()
    conn = get_db()
    habits = conn.execute("SELECT * FROM habits WHERE user_id=? ORDER BY created_at", (uid,)).fetchall()
    today = str(date.today())
    result = []
    for h in habits:
        hid = h["id"]
        streak = calc_streak(conn, hid, today)
        total = conn.execute("SELECT COUNT(*) FROM completions WHERE habit_id=?", (hid,)).fetchone()[0]
        done_today = conn.execute(
            "SELECT 1 FROM completions WHERE habit_id=? AND completed_date=?", (hid, today)
        ).fetchone() is not None
        week = []
        for i in range(6, -1, -1):
            d = str(date.today() - timedelta(days=i))
            done = conn.execute("SELECT 1 FROM completions WHERE habit_id=? AND completed_date=?", (hid, d)).fetchone() is not None
            week.append({"date": d, "done": done})
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
@login_required
def add_habit():
    uid = get_current_user_id()
    data = request.json
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "Name is required"}), 400
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO habits (user_id, name, icon, color, target_days) VALUES (?,?,?,?,?)",
              (uid, name, data.get("icon","⭐"), data.get("color","#6366f1"), data.get("target_days",7)))
    conn.commit()
    new_id = c.lastrowid
    conn.close()
    return jsonify({"id": new_id, "message": "Habit created"}), 201

@app.route("/api/habits/<int:habit_id>", methods=["PUT"])
@login_required
def update_habit(habit_id):
    uid = get_current_user_id()
    data = request.json
    conn = get_db()
    # Ensure habit belongs to this user
    habit = conn.execute("SELECT id FROM habits WHERE id=? AND user_id=?", (habit_id, uid)).fetchone()
    if not habit:
        conn.close()
        return jsonify({"error": "Not found"}), 404
    conn.execute("UPDATE habits SET name=?, icon=?, color=?, target_days=? WHERE id=?",
                 (data["name"], data["icon"], data["color"], data["target_days"], habit_id))
    conn.commit()
    conn.close()
    return jsonify({"message": "Updated"})

@app.route("/api/habits/<int:habit_id>", methods=["DELETE"])
@login_required
def delete_habit(habit_id):
    uid = get_current_user_id()
    conn = get_db()
    habit = conn.execute("SELECT id FROM habits WHERE id=? AND user_id=?", (habit_id, uid)).fetchone()
    if not habit:
        conn.close()
        return jsonify({"error": "Not found"}), 404
    conn.execute("DELETE FROM completions WHERE habit_id=?", (habit_id,))
    conn.execute("DELETE FROM habits WHERE id=?", (habit_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Deleted"})

@app.route("/api/habits/<int:habit_id>/toggle", methods=["POST"])
@login_required
def toggle(habit_id):
    uid = get_current_user_id()
    data = request.json or {}
    day = data.get("date", str(date.today()))
    conn = get_db()
    # Verify ownership
    habit = conn.execute("SELECT id FROM habits WHERE id=? AND user_id=?", (habit_id, uid)).fetchone()
    if not habit:
        conn.close()
        return jsonify({"error": "Not found"}), 404
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

@app.route("/api/stats")
@login_required
def stats():
    uid = get_current_user_id()
    conn = get_db()
    today = str(date.today())
    total_habits = conn.execute("SELECT COUNT(*) FROM habits WHERE user_id=?", (uid,)).fetchone()[0]
    done_today = conn.execute(
        """SELECT COUNT(DISTINCT c.habit_id) FROM completions c
           JOIN habits h ON c.habit_id=h.id
           WHERE h.user_id=? AND c.completed_date=?""", (uid, today)
    ).fetchone()[0]
    habits = conn.execute("SELECT id FROM habits WHERE user_id=?", (uid,)).fetchall()
    rates = [calc_rate(conn, h["id"], 30) for h in habits]
    avg_rate = round(sum(rates) / len(rates), 1) if rates else 0
    best_streak = max([calc_streak(conn, h["id"], today) for h in habits], default=0)
    per_habit = []
    for h in conn.execute("SELECT id, name, color FROM habits WHERE user_id=?", (uid,)).fetchall():
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

# ─── HELPERS ───
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
