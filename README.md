# HabitFlow — Daily Habit Tracker

A fully responsive habit tracker built with Flask, SQLite, HTML/CSS/JS.

## Quick Start

1. Install dependencies:
   pip install -r requirements.txt

2. Run the app:
   python app.py

3. Open in browser:
   http://localhost:5000

## Project Structure

habit-tracker/
├── app.py                  # Flask backend + SQLite API
├── requirements.txt        # Python dependencies
├── templates/
│   └── index.html          # Main HTML template
└── static/
    ├── css/style.css       # All styles + responsive breakpoints
    └── js/app.js           # Frontend logic

## Features
- Add, edit, delete habits with custom icons & colors
- Daily check-off with streak tracking
- 7-day mini activity view per habit
- Progress page with bar charts and completion rates
- Fully responsive — hamburger sidebar on mobile
- SQLite database (auto-created on first run)
