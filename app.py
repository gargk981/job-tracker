import json
from datetime import datetime
import pandas as pd
import os
import matplotlib
matplotlib.use("Agg")  
import matplotlib.pyplot as plt
from flask import Flask, render_template, request, redirect, session
import sqlite3

app = Flask(__name__)
app.secret_key = "mysecret123"

jobs = []
users = {}

# Load jobs
def load_jobs():
    global jobs
    try:
        with open("jobs.json", "r") as file:
            jobs = json.load(file)
    except FileNotFoundError:
        jobs = []

# Save jobs
def save_jobs():
    with open("jobs.json", "w") as file:
        json.dump(jobs, file, indent=4)


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

    path = "static/status_chart.png"
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

#USER SIGNUP
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, password)
            )
            conn.commit()
        except:
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
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password)
        ).fetchone()

        conn.close()

        if user:
            session["user_id"] = user["id"]
            return redirect("/")
        else:
            return "Invalid credentials"

    return render_template("login.html")

# HOME PAGE
@app.route("/")
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


# ADD JOB
@app.route("/add", methods=["POST"])
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
def delete_job(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM jobs WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect("/")

# UPDATE STATUS
@app.route("/update/<int:id>", methods=["POST"])
def update_job(id):
    new_status = request.form["status"]

    conn = get_db_connection()
    conn.execute(
        "UPDATE jobs SET status=? WHERE id=?",
        (new_status, id)
    )
    conn.commit()
    conn.close()

    return redirect("/")

#LOGOUT
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/login")

init_db()

if __name__ == "__main__":
    load_jobs()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

