from flask import Flask, render_template, request, redirect, session
import sqlite3

app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- DATABASE ----------------
def get_db():
    return sqlite3.connect("confessions.db")

def create_tables():
    db = get_db()
    c = db.cursor()

    # Users
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)

    # Posts
    c.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message TEXT,
            emoji TEXT,
            username TEXT,
            likes INTEGER DEFAULT 0
        )
    """)

    # Comments
    c.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER,
            username TEXT,
            comment TEXT
        )
    """)

    # Notifications
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

# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        try:
            db = get_db()
            c = db.cursor()
            c.execute("INSERT INTO users VALUES (NULL, ?, ?)", (username, password))
            db.commit()
            db.close()
            return redirect("/login")
        except:
            return "Username already exists!"

    return render_template("register.html")

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        db = get_db()
        c = db.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = c.fetchone()
        db.close()

        if user:
            session["user"] = username
            return redirect("/")
        return "Invalid login!"

    return render_template("login.html")

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ---------------- HOME ----------------
@app.route("/", methods=["GET", "POST"])
def index():
    if not session.get("user"):
        return redirect("/login")

    db = get_db()
    c = db.cursor()

    # Create post
    if request.method == "POST":
        msg = request.form["message"]
        emoji = request.form["emoji"]
        username = session["user"]

        c.execute(
            "INSERT INTO posts (message, emoji, username, likes) VALUES (?, ?, ?, 0)",
            (msg, emoji, username)
        )
        db.commit()

    # Load posts
    c.execute("SELECT * FROM posts ORDER BY id DESC")
    posts = c.fetchall()

    # Load comments
    c.execute("SELECT * FROM comments")
    comments = c.fetchall()

    # Notification count
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

    text = request.form["comment"]
    username = session["user"]

    db = get_db()
    c = db.cursor()

    # Save comment
    c.execute(
        "INSERT INTO comments (post_id, username, comment) VALUES (?, ?, ?)",
        (post_id, username, text)
    )

    # Find post owner
    c.execute("SELECT username FROM posts WHERE id=?", (post_id,))
    owner = c.fetchone()[0]

    # Create notification (if not self)
    if owner != username:
        c.execute(
            "INSERT INTO notifications (username, text, seen) VALUES (?, ?, 0)",
            (owner, f"{username} commented on your post")
        )

    db.commit()
    db.close()
    return redirect("/")

# ---------------- PROFILE ----------------
@app.route("/profile")
def profile():
    if not session.get("user"):
        return redirect("/login")

    username = session["user"]
    db = get_db()
    c = db.cursor()

    # User posts
    c.execute("SELECT * FROM posts WHERE username=? ORDER BY id DESC", (username,))
    my_posts = c.fetchall()

    # Notifications
    c.execute("SELECT * FROM notifications WHERE username=? ORDER BY id DESC", (username,))
    notifications = c.fetchall()

    # Mark notifications as seen
    c.execute("UPDATE notifications SET seen=1 WHERE username=?", (username,))
    db.commit()
    db.close()

    return render_template(
        "profile.html",
        user=username,
        posts=my_posts,
        notifications=notifications
    )

# ---------------- LIKE ----------------
@app.route("/like/<int:id>")
def like(id):
    db = get_db()
    c = db.cursor()
    c.execute("UPDATE posts SET likes = likes + 1 WHERE id=?", (id,))
    db.commit()
    db.close()
    return redirect("/")

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
