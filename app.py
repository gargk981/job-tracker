import json
from datetime import datetime
import pandas as pd
import os
import matplotlib
matplotlib.use("Agg")  
import matplotlib.pyplot as plt
from flask import Flask, render_template, request, redirect, session

app = Flask(__name__)
app.secret_key = "mysecret123"

jobs = []

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


# HOME PAGE
@app.route("/")
def home():
    jobs = session.get("jobs", [])

    total = len(jobs)
    applied = len([j for j in jobs if j["status"] == "applied"])
    r1 = len([j for j in jobs if j["status"] == "interview_round_1"])
    r2 = len([j for j in jobs if j["status"] == "interview_round_2"])
    selected = len([j for j in jobs if j["status"] == "selected"])
    rejected = len([j for j in jobs if j["status"] == "rejected"])

    graph_path = generate_graph(jobs)

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
def add_job():
    jobs = session.get("jobs", [])

    company = request.form["company"]
    role = request.form["role"]
    status = request.form["status"]
    date = datetime.now().strftime("%Y-%m-%d")

    jobs.append({
        "company": company,
        "role": role,
        "status": status,
        "date": date
    })

    session["jobs"] = jobs

    return redirect("/")

# DELETE JOB
@app.route("/delete/<int:index>")
def delete_job(index):
    jobs = session.get("jobs", [])

    if 0 <= index < len(jobs):
        jobs.pop(index)

    session["jobs"] = jobs
    return redirect("/")

# UPDATE STATUS
@app.route("/update/<int:index>", methods=["POST"])
def update_job(index):
    jobs = session.get("jobs", [])

    new_status = request.form["status"]

    if 0 <= index < len(jobs):
        jobs[index]["status"] = new_status

    session["jobs"] = jobs
    return redirect("/")

if __name__ == "__main__":
    load_jobs()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

