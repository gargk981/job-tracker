from datetime import datetime
import pandas as pd
import os
import matplotlib
matplotlib.use("Agg")  
import matplotlib.pyplot as plt
from flask import Flask, render_template, request, redirect, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = "mysecret123"


def generate_graph(jobs):
    if not jobs:
        return None

    df = pd.DataFrame(jobs)
    status_count = df["status"].value_counts()

    plt.figure(figsize=(5,3))

    bars = plt.bar(
        status_count.index,
        status_count.values
    )

    # Custom colors
    colors = {
        "applied": "orange",
        "interview_round_1": "blue",
        "interview_round_2": "purple",
        "selected": "green",
        "rejected": "red"
    }

    for bar, label in zip(bars, status_count.index):
        bar.set_color(colors.get(label, "gray"))

    # Add values on top
    for i, v in enumerate(status_count.values):
        plt.text(i, v + 0.1, str(v), ha='center')

    plt.title("Job Status Overview", fontsize=14)
    plt.xlabel("Status")
    plt.ylabel("Count")

    plt.tight_layout()

    if not os.path.exists("static"):
        os.makedirs("static")

    path = f"static/status_chart_{jobs[0]['user_id']}.png"
    plt.savefig(path)
    plt.close()

    return path

def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        company TEXT,
        role TEXT,
        status TEXT,
        date TEXT
    )
    """)

    conn.commit()
    conn.close()

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect("/login")
        return f(*args, **kwargs)
    return wrapper

#USER SIGNUP
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # 🔐 Hash password
            hashed_password = generate_password_hash(password)

            cursor.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, hashed_password)
            )
            conn.commit()
        except sqlite3.IntegrityError:
            return "User already exists"

        conn.close()
        return redirect("/login")

    return render_template("signup.html")

#USER LOGIN
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE username=?",
            (username,)
        ).fetchone()

        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            return redirect("/")
        else:
            return "Invalid credentials"

    return render_template("login.html")

# HOME PAGE
@app.route("/")
@login_required
def home():
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]

    conn = get_db_connection()
    jobs = conn.execute(
        "SELECT * FROM jobs WHERE user_id=? ORDER BY date DESC",
        (user_id,)
    ).fetchall()
    conn.close()

    # Convert to list for graph
    jobs_list = [dict(job) for job in jobs]

    graph_path = generate_graph(jobs_list)

    # Stats
    total = len(jobs_list)
    applied = len([j for j in jobs_list if j["status"] == "applied"])
    r1 = len([j for j in jobs_list if j["status"] == "interview_round_1"])
    r2 = len([j for j in jobs_list if j["status"] == "interview_round_2"])
    selected = len([j for j in jobs_list if j["status"] == "selected"])
    rejected = len([j for j in jobs_list if j["status"] == "rejected"])

    return render_template(
        "index.html",
        jobs=jobs,
        total=total,
        applied=applied,
        r1=r1,
        r2=r2,
        selected=selected,
        rejected=rejected,
        graph_path=graph_path
    )


# ADD JOB
@app.route("/add", methods=["POST"])
@login_required
def add_job():
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]

    company = request.form["company"]
    role = request.form["role"]
    status = request.form["status"]
    date = datetime.now().strftime("%Y-%m-%d")

    conn = get_db_connection()
    conn.execute(
        "INSERT INTO jobs (user_id, company, role, status, date) VALUES (?, ?, ?, ?, ?)",
        (user_id, company, role, status, date)
    )
    conn.commit()
    conn.close()

    return redirect("/")

# DELETE JOB
@app.route("/delete/<int:id>")
@login_required
def delete_job(id):
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    user_id = session["user_id"]

    conn.execute(
        "DELETE FROM jobs WHERE id=? AND user_id=?",
        (id, user_id)
    )
    
    conn.commit()
    conn.close()

    return redirect("/")

# UPDATE STATUS
@app.route("/update/<int:id>", methods=["POST"])
@login_required
def update_job(id):
    if "user_id" not in session:
        return redirect("/login")

    new_status = request.form["status"]

    conn = get_db_connection()
    conn.execute(
        "UPDATE jobs SET status=? WHERE id=? AND user_id=?",
        (new_status, id, session["user_id"])
    )
    conn.commit()
    conn.close()

    return redirect("/")

#LOGOUT
@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect("/login")

init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

