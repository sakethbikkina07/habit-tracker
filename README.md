# HabitFlow — Daily Habit Tracker

A fully responsive, multi-user habit tracker with login/register,
built with Flask, SQLite, HTML/CSS/JS.

## Quick Start

1. Install dependencies:
   pip install -r requirements.txt

2. Run the app:
   python app.py

3. Open in browser:
   http://localhost:5000

   You'll be redirected to the login page. Create an account and start tracking!

## Features
- Secure registration & login (passwords hashed with werkzeug)
- Per-user habit isolation — each account sees only their own data
- Add/edit/delete habits with custom icons & colors
- Daily check-off with streak tracking
- 7-day activity view + 30-day completion rates
- Progress analytics page
- Fully responsive — hamburger sidebar on mobile

## Project Structure

habit-tracker/
├── app.py                  # Flask backend + SQLite + auth API
├── requirements.txt
├── README.md
├── templates/
│   ├── auth.html           # Login / Register page
│   └── index.html          # Main app (protected)
└── static/
    ├── css/style.css       # All styles + responsive breakpoints
    └── js/app.js           # Frontend logic + auth handling
