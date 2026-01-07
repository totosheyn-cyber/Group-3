from flask import Flask, render_template, request, redirect, session
import sqlite3

app = Flask(__name__)
app.secret_key = "secret123"

# ---------- DATABASE ----------
def get_db():
    return sqlite3.connect("confessions.db")

def create_table():
    db = get_db()
    c = db.cursor()

    # Create table
    c.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message TEXT,
            emoji TEXT,
            grade TEXT,
            likes INTEGER DEFAULT 0
        )
    """)

    # Try adding columns if old DB exists
    for column in ["emoji TEXT", "grade TEXT", "likes INTEGER DEFAULT 0"]:
        try:
            c.execute(f"ALTER TABLE posts ADD COLUMN {column}")
        except:
            pass

    db.commit()
    db.close()

create_table()

# ---------- HOME PAGE ----------
@app.route("/", methods=["GET", "POST"])
def index():
    db = get_db()
    c = db.cursor()

    if request.method == "POST":
        msg = request.form["message"]
        emoji = request.form["emoji"]
        grade = request.form["grade"]

        c.execute(
            "INSERT INTO posts (message, emoji, grade, likes) VALUES (?, ?, ?, 0)",
            (msg, emoji, grade)
        )
        db.commit()

    c.execute("SELECT * FROM posts ORDER BY id DESC")
    posts = c.fetchall()
    db.close()

    return render_template("index.html", posts=posts)

# ---------- LIKE ----------
@app.route("/like/<int:id>")
def like(id):
    db = get_db()
    c = db.cursor()
    c.execute("UPDATE posts SET likes = likes + 1 WHERE id=?", (id,))
    db.commit()
    db.close()
    return redirect("/")

# ---------- ADMIN ----------
@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        if request.form["password"] == "admin123":
            session["admin"] = True
        else:
            return "Wrong password!"

    if not session.get("admin"):
        return '''
        <form method="post" style="text-align:center;padding:50px;">
            <h3>Admin Login</h3>
            <input type="password" name="password">
            <br><br>
            <button>Login</button>
        </form>
        '''

    db = get_db()
    c = db.cursor()
    c.execute("SELECT * FROM posts ORDER BY id DESC")
    posts = c.fetchall()
    db.close()

    return render_template("admin.html", posts=posts)

# ---------- DELETE ----------
@app.route("/delete/<int:id>")
def delete(id):
    if not session.get("admin"):
        return "Unauthorized"

    db = get_db()
    c = db.cursor()
    c.execute("DELETE FROM posts WHERE id=?", (id,))
    db.commit()
    db.close()

    return redirect("/admin")

# ---------- RUN ----------
if __name__ == "__main__":
    app.run(debug=True)
