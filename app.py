from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import timedelta

app = Flask(__name__)

# 🔐 IMPORTANT: keep this constant
app.secret_key = "anonymous-confession-secret-key"

# ⏳ Session lifetime (unlimited devices)
app.permanent_session_lifetime = timedelta(days=30)

# ---------------- DATABASE ----------------
def get_db():
    return sqlite3.connect("/tmp/confessions.db")

def create_tables():
    db = get_db()
    c = db.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message TEXT,
            emoji TEXT,
            username TEXT,
            likes INTEGER DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER,
            username TEXT,
            comment TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            text TEXT,
            seen INTEGER DEFAULT 0
        )
    """)

    db.commit()
    db.close()

create_tables()

# ---------------- LANDING PAGE (INSTRUCTIONS) ----------------
@app.route("/")
def landing():
    return render_template("landing.html")

# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]

        try:
            db = get_db()
            c = db.cursor()
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (u, p))
            db.commit()
            db.close()
            return redirect("/login")
        except:
            return "Username already exists"

    return render_template("register.html")

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]

        db = get_db()
        c = db.cursor()
        c.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (u, p)
        )
        user = c.fetchone()
        db.close()

        if user:
            session.permanent = True
            session["user"] = u
            session["welcome"] = True
            return redirect("/feed")

        return "Invalid username or password"

    return render_template("login.html")

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.pop("user", None)
    session.pop("welcome", None)
    return redirect("/login")

# ---------------- FEED ----------------
@app.route("/feed", methods=["GET", "POST"])
def feed():
    if not session.get("user"):
        return redirect("/login")

    # ---- CREATE POST (POST → REDIRECT → GET) ----
    if request.method == "POST":
        msg = request.form.get("message")
        emoji = request.form.get("emoji")
        user = session["user"]

        if msg and emoji:
            db = get_db()
            c = db.cursor()
            c.execute(
                "INSERT INTO posts (message, emoji, username, likes) VALUES (?, ?, ?, 0)",
                (msg, emoji, user)
            )
            db.commit()
            db.close()

        return redirect("/feed")  # 🚀 prevents double post

    # ---- LOAD DATA ----
    db = get_db()
    c = db.cursor()

    c.execute("SELECT * FROM posts ORDER BY id DESC")
    posts = c.fetchall()

    c.execute("SELECT * FROM comments ORDER BY id ASC")
    comments = c.fetchall()

    c.execute(
        "SELECT COUNT(*) FROM notifications WHERE username=? AND seen=0",
        (session["user"],)
    )
    notif_count = c.fetchone()[0]

    db.close()

    return render_template(
        "index.html",
        posts=posts,
        comments=comments,
        user=session["user"],
        notif_count=notif_count
    )

# ---------------- COMMENT ----------------
@app.route("/comment/<int:post_id>", methods=["POST"])
def comment(post_id):
    if not session.get("user"):
        return redirect("/login")

    text = request.form.get("comment")
    user = session["user"]

    if not text:
        return redirect("/feed")

    db = get_db()
    c = db.cursor()

    c.execute(
        "INSERT INTO comments (post_id, username, comment) VALUES (?, ?, ?)",
        (post_id, user, text)
    )

    c.execute("SELECT username FROM posts WHERE id=?", (post_id,))
    row = c.fetchone()

    if row and row[0] != user:
        c.execute(
            "INSERT INTO notifications (username, text, seen) VALUES (?, ?, 0)",
            (row[0], f"{user} replied to your post")
        )

    db.commit()
    db.close()

    return redirect("/feed")

# ---------------- LIKE ----------------
@app.route("/like/<int:post_id>")
def like(post_id):
    db = get_db()
    c = db.cursor()
    c.execute("UPDATE posts SET likes = likes + 1 WHERE id=?", (post_id,))
    db.commit()
    db.close()
    return redirect("/feed")

# ---------------- PROFILE ----------------
@app.route("/profile")
def profile():
    if not session.get("user"):
        return redirect("/login")

    user = session["user"]
    db = get_db()
    c = db.cursor()

    c.execute("SELECT * FROM posts WHERE username=? ORDER BY id DESC", (user,))
    posts = c.fetchall()

    c.execute(
        "SELECT * FROM notifications WHERE username=? ORDER BY id DESC",
        (user,)
    )
    notifications = c.fetchall()

    c.execute("UPDATE notifications SET seen=1 WHERE username=?", (user,))
    db.commit()
    db.close()

    return render_template(
        "profile.html",
        user=user,
        posts=posts,
        notifications=notifications
    )

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
