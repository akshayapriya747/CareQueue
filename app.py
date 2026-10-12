from flask import Flask, request, redirect, url_for, render_template_string, flash
import sqlite3
from datetime import datetime
from statistics import mean, median, variance, stdev

app = Flask(__name__)
app.secret_key = "carequeue-demo"
DB_NAME = "hospital_queue.db"

DEPARTMENTS = [
    "General Medicine",
    "Cardiology",
    "Dermatology",
    "Orthopedics",
    "Pediatrics"
]


# ---------------- DATABASE ----------------

def connect_db():
    con = sqlite3.connect(DB_NAME)
    con.row_factory = sqlite3.Row
    return con


def initialize_database():
    with connect_db() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS departments (
                name TEXT PRIMARY KEY,
                doctors INTEGER NOT NULL DEFAULT 1
            )
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_code TEXT NOT NULL,
                department TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Waiting',
                check_in TEXT NOT NULL,
                start_time TEXT,
                end_time TEXT,
                duration REAL
            )
        """)

        for department in DEPARTMENTS:
            con.execute(
                "INSERT OR IGNORE INTO departments VALUES (?, ?)",
                (department, 1)
            )


# ---------------- STATISTICS ----------------

def calculate_statistics(durations):
    if not durations:
        return {
            "count": 0,
            "mean": 0,
            "median": 0,
            "variance": 0,
            "stdev": 0,
            "longest": 0
        }

    return {
        "count": len(durations),
        "mean": round(mean(durations), 2),
        "median": round(median(durations), 2),
        "variance": round(variance(durations), 2)
        if len(durations) > 1 else 0,
        "stdev": round(stdev(durations), 2)
        if len(durations) > 1 else 0,
        "longest": round(max(durations), 2)
    }


def get_department_statistics(con, department):
    rows = con.execute("""
        SELECT duration
        FROM patients
        WHERE department = ?
        AND status = 'Completed'
        AND duration IS NOT NULL
    """, (department,)).fetchall()

    durations = [float(row["duration"]) for row in rows]

    stats = calculate_statistics(durations)

    if not durations:
        stats["mean"] = 10

    return stats


def get_queue_data(con):
    result = []

    for department in DEPARTMENTS:

        waiting = con.execute("""
            SELECT COUNT(*) FROM patients
            WHERE department = ? AND status = 'Waiting'
        """, (department,)).fetchone()[0]

        active = con.execute("""
            SELECT COUNT(*) FROM patients
            WHERE department = ? AND status = 'In Consultation'
        """, (department,)).fetchone()[0]

        doctors = con.execute("""
            SELECT doctors FROM departments
            WHERE name = ?
        """, (department,)).fetchone()["doctors"]

        stats = get_department_statistics(con, department)

        estimated_wait = round(
            ((waiting + active) * stats["mean"]) / max(doctors, 1)
        )

        if waiting <= 2:
            level = "Low"
        elif waiting <= 5:
            level = "Moderate"
        else:
            level = "High"

        result.append({
            "name": department,
            "waiting": waiting,
            "active": active,
            "doctors": doctors,
            "average": stats["mean"],
            "estimated": estimated_wait,
            "level": level,
            "completed": stats["count"]
        })

    return result


# ---------------- WEBSITE DESIGN ----------------

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>CareQueue | Hospital Queue Analyzer</title>

<style>
* {
    box-sizing: border-box;
}

body {
    margin: 0;
    font-family: Arial, sans-serif;
    background: #f3f6fb;
    color: #17253b;
}

header {
    background: linear-gradient(120deg, #132238, #24558a);
    color: white;
    padding: 24px 6%;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 15px;
}

.logo {
    font-size: 27px;
    font-weight: bold;
}

.logo span {
    color: #4ee0ce;
}

header p {
    margin-bottom: 0;
    color: #d7e5f5;
    font-size: 13px;
}

nav a {
    display: inline-block;
    color: white;
    text-decoration: none;
    padding: 10px 14px;
    border: 1px solid #ffffff55;
    border-radius: 9px;
    margin: 3px;
}

nav a:hover {
    background: #ffffff22;
}

main {
    max-width: 1200px;
    margin: 30px auto;
    padding: 0 20px;
}

h1 {
    margin-bottom: 8px;
}

h2 {
    font-size: 19px;
}

.subtitle {
    color: #6b7890;
    line-height: 1.5;
}

.cards {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
    margin: 24px 0;
}

.card {
    background: white;
    padding: 22px;
    border-radius: 15px;
    border: 1px solid #e4eaf2;
    box-shadow: 0 5px 20px #13223808;
    margin-bottom: 20px;
}

.metric-title {
    color: #6b7890;
    font-size: 12px;
    font-weight: bold;
    text-transform: uppercase;
}

.metric {
    font-size: 30px;
    font-weight: bold;
    margin: 12px 0 5px;
}

.metric-note {
    color: #7b8799;
    font-size: 12px;
}

.columns {
    display: grid;
    grid-template-columns: 1fr 1.4fr;
    gap: 20px;
}

label {
    display: block;
    font-weight: bold;
    font-size: 13px;
    margin: 14px 0 7px;
}

input, select {
    width: 100%;
    padding: 12px;
    border: 1px solid #d9e1ed;
    border-radius: 9px;
    font-size: 14px;
    background: white;
}

button {
    background: #2878f0;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 11px 14px;
    cursor: pointer;
    font-weight: bold;
    margin-top: 14px;
}

button:hover {
    opacity: 0.88;
}

.start {
    background: #16a68c;
}

.complete {
    background: #16a68c;
}

table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
}

th {
    background: #f6f8fc;
    color: #6b7890;
    text-transform: uppercase;
    font-size: 11px;
    text-align: left;
}

th, td {
    padding: 13px 10px;
    border-bottom: 1px solid #e8edf4;
}

.status {
    display: inline-block;
    padding: 6px 9px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: bold;
}

.Waiting {
    background: #fff0c9;
    color: #916500;
}

.In-Consultation {
    background: #e1edff;
    color: #235db8;
}

.Completed {
    background: #d9f8eb;
    color: #08785d;
}

.level {
    font-weight: bold;
}

.Low {
    color: #0a997c;
}

.Moderate {
    color: #b27b00;
}

.High {
    color: #d94350;
}

.message {
    background: #dff8ed;
    color: #08785d;
    padding: 13px;
    border-radius: 9px;
    margin-bottom: 15px;
}

.message.error {
    background: #ffe7e7;
    color: #b52e37;
}

.small {
    color: #778397;
    font-size: 12px;
    line-height: 1.6;
}

.stats-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
}

.stat-box {
    padding: 15px;
    background: #f5f8fc;
    border-radius: 10px;
}

.stat-box span {
    display: block;
    color: #6b7890;
    font-size: 12px;
}

.stat-box strong {
    display: block;
    font-size: 20px;
    margin-top: 8px;
}

.bar-row {
    display: grid;
    grid-template-columns: 140px 1fr 30px;
    align-items: center;
    gap: 10px;
    margin: 18px 0;
    font-size: 12px;
}

.bar-background {
    height: 10px;
    background: #e9eef6;
    border-radius: 10px;
    overflow: hidden;
}

.bar {
    height: 100%;
    background: linear-gradient(90deg, #2878f0, #16b8a6);
    border-radius: 10px;
}

footer {
    text-align: center;
    padding: 25px;
    color: #78849a;
    font-size: 12px;
}

.table-wrap {
    overflow-x: auto;
}

@media(max-width: 850px) {
    .cards {
        grid-template-columns: repeat(2, 1fr);
    }

    .columns {
        grid-template-columns: 1fr;
    }
}

@media(max-width: 500px) {
    header {
        padding: 20px;
    }

    main {
        padding: 0 12px;
    }

    .cards {
        gap: 9px;
    }

    .card {
        padding: 14px;
    }

    .metric {
        font-size: 24px;
    }

    .stats-grid {
        grid-template-columns: repeat(2, 1fr);
    }

    .bar-row {
        grid-template-columns: 100px 1fr 25px;
    }
}
</style>
</head>

<body>

<header>
    <div>
        <div class="logo">Care<span>Queue</span></div>
        <p>Hospital Queue Analyzer | Computational Statistics Project</p>
    </div>

    <nav>
        <a href="{{ url_for('home') }}">Queue Overview</a>
        <a href="{{ url_for('dashboard') }}">Statistics Dashboard</a>
    </nav>
</header>

<main>

{% for category, message in get_flashed_messages(with_categories=true) %}
    <div class="message {{ category }}">{{ message }}</div>
{% endfor %}

{% if page == 'home' %}

<h1>Hospital Queue Overview</h1>
<p class="subtitle">
Monitor patient queues, estimate waiting times, and analyze department workloads.
</p>

<div class="cards">
    <div class="card">
        <div class="metric-title">Waiting Patients</div>
        <div class="metric">{{ totals.waiting }}</div>
        <div class="metric-note">Waiting for consultation</div>
    </div>

    <div class="card">
        <div class="metric-title">In Consultation</div>
        <div class="metric">{{ totals.active }}</div>
        <div class="metric-note">Currently being served</div>
    </div>

    <div class="card">
        <div class="metric-title">Completed Today</div>
        <div class="metric">{{ totals.completed }}</div>
        <div class="metric-note">Consultations completed today</div>
    </div>

    <div class="card">
        <div class="metric-title">Departments</div>
        <div class="metric">5</div>
        <div class="metric-note">Departments in the demo</div>
    </div>
</div>

<div class="columns">

    <section class="card">
        <h2>+ Register a Patient</h2>

        <form method="POST" action="{{ url_for('add_patient') }}">

            <label>Fictional Patient Code</label>
            <input
                type="text"
                name="patient_code"
                placeholder="Example: DEMO-101"
                maxlength="30"
                required
            >

            <label>Department</label>
            <select name="department" required>
                {% for department in departments %}
                    <option value="{{ department }}">{{ department }}</option>
                {% endfor %}
            </select>

            <button type="submit">Add to Queue →</button>
        </form>

        <p class="small">
            Use fictional codes only. Do not enter real patient names or medical details.
        </p>
    </section>

    <section class="card">
        <h2>Department Queue Status</h2>

        <div class="table-wrap">
        <table>
            <tr>
                <th>Department</th>
                <th>Waiting</th>
                <th>Doctors</th>
                <th>Est. Wait</th>
                <th>Load</th>
            </tr>

            {% for d in queue %}
            <tr>
                <td>
                    <strong>{{ d.name }}</strong>
                    <div class="small">{{ d.completed }} completed samples</div>
                </td>
                <td>{{ d.waiting }}</td>
                <td>{{ d.doctors }}</td>
                <td><strong>{{ d.estimated }} min</strong></td>
                <td><span class="level {{ d.level }}">{{ d.level }}</span></td>
            </tr>
            {% endfor %}
        </table>
        </div>

        <p class="small">
            Estimated waiting times are simplified statistical estimates, not clinical advice.
        </p>
    </section>

</div>

<section class="card">
    <h2>Patient Queue</h2>

    {% if patients %}
    <div class="table-wrap">
    <table>
        <tr>
            <th>Patient Code</th>
            <th>Department</th>
            <th>Status</th>
            <th>Check-in Time</th>
            <th>Action</th>
        </tr>

        {% for p in patients %}
        <tr>
            <td><strong>{{ p.patient_code }}</strong></td>
            <td>{{ p.department }}</td>
            <td>
                <span class="status {{ p.status|replace(' ', '-') }}">
                    {{ p.status }}
                </span>
            </td>
            <td>{{ p.check_in }}</td>
            <td>
                {% if p.status == 'Waiting' %}
                <form method="POST" action="{{ url_for('start_patient', patient_id=p.id) }}">
                    <button class="start">Start</button>
                </form>

                {% elif p.status == 'In Consultation' %}
                <form method="POST" action="{{ url_for('complete_patient', patient_id=p.id) }}">
                    <button class="complete">Complete</button>
                </form>

                {% else %}
                <span class="small">{{ p.duration|round(1) }} min</span>
                {% endif %}
            </td>
        </tr>
        {% endfor %}
    </table>
    </div>

    {% else %}
        <p class="subtitle">No patients yet. Register a fictional patient to get started.</p>
    {% endif %}
</section>

{% elif page == 'dashboard' %}

<h1>Statistics Dashboard</h1>
<p class="subtitle">
Analyze consultation duration using descriptive statistics.
</p>

<div class="cards">
    <div class="card">
        <div class="metric-title">Completed Consultations</div>
        <div class="metric">{{ stats.count }}</div>
        <div class="metric-note">Total recorded samples</div>
    </div>

    <div class="card">
        <div class="metric-title">Mean Duration</div>
        <div class="metric">{{ stats.mean }} min</div>
        <div class="metric-note">Average consultation time</div>
    </div>

    <div class="card">
        <div class="metric-title">Median Duration</div>
        <div class="metric">{{ stats.median }} min</div>
        <div class="metric-note">Middle observation</div>
    </div>

    <div class="card">
        <div class="metric-title">Standard Deviation</div>
        <div class="metric">{{ stats.stdev }} min</div>
        <div class="metric-note">Variation in durations</div>
    </div>
</div>

<div class="columns">

    <section class="card">
        <h2>Waiting Patients by Department</h2>

        {% for d in queue %}
        <div class="bar-row">
            <span>{{ d.name }}</span>

            <div class="bar-background">
                <div class="bar" style="width: {{ (d.waiting / max_wait * 100)|round }}%"></div>
            </div>

            <strong>{{ d.waiting }}</strong>
        </div>
        {% endfor %}

        <p class="small">Bars represent waiting-patient counts.</p>
    </section>

    <section class="card">
        <h2>Descriptive Statistics</h2>

        <div class="stats-grid">
            <div class="stat-box">
                <span>Mean</span>
                <strong>{{ stats.mean }} min</strong>
            </div>

            <div class="stat-box">
                <span>Median</span>
                <strong>{{ stats.median }} min</strong>
            </div>

            <div class="stat-box">
                <span>Sample Variance</span>
                <strong>{{ stats.variance }}</strong>
            </div>

            <div class="stat-box">
                <span>Standard Deviation</span>
                <strong>{{ stats.stdev }} min</strong>
            </div>

            <div class="stat-box">
                <span>Longest Duration</span>
                <strong>{{ stats.longest }} min</strong>
            </div>

            <div class="stat-box">
                <span>Sample Size</span>
                <strong>{{ stats.count }}</strong>
            </div>
        </div>
    </section>

</div>

<section class="card">
    <h2>Department Summary</h2>

    <div class="table-wrap">
    <table>
        <tr>
            <th>Department</th>
            <th>Waiting</th>
            <th>Active</th>
            <th>Mean Time</th>
            <th>Estimated Wait</th>
            <th>Load</th>
        </tr>

        {% for d in queue %}
        <tr>
            <td>{{ d.name }}</td>
            <td>{{ d.waiting }}</td>
            <td>{{ d.active }}</td>
            <td>{{ d.average }} min</td>
            <td>{{ d.estimated }} min</td>
            <td><span class="level {{ d.level }}">{{ d.level }}</span></td>
        </tr>
        {% endfor %}
    </table>
    </div>
</section>

{% endif %}

</main>

<footer>
CareQueue | Educational Project | Statistical estimates are illustrative only
</footer>

</body>
</html>
"""


# ---------------- ROUTES ----------------

@app.route("/")
def home():
    with connect_db() as con:
        patients = con.execute("""
            SELECT * FROM patients
            ORDER BY
                CASE status
                    WHEN 'Waiting' THEN 1
                    WHEN 'In Consultation' THEN 2
                    ELSE 3
                END,
                id ASC
        """).fetchall()

        queue = get_queue_data(con)

        waiting = con.execute("""
            SELECT COUNT(*) FROM patients WHERE status='Waiting'
        """).fetchone()[0]

        active = con.execute("""
            SELECT COUNT(*) FROM patients WHERE status='In Consultation'
        """).fetchone()[0]

        completed_today = con.execute("""
            SELECT COUNT(*) FROM patients
            WHERE status='Completed'
            AND date(end_time)=date('now','localtime')
        """).fetchone()[0]

    totals = {
        "waiting": waiting,
        "active": active,
        "completed": completed_today
    }

    return render_template_string(
        HTML,
        page="home",
        patients=patients,
        queue=queue,
        totals=totals,
        departments=DEPARTMENTS
    )


@app.route("/add", methods=["POST"])
def add_patient():
    code = request.form.get("patient_code", "").strip()
    department = request.form.get("department", "")

    if not code:
        flash("Please enter a patient code.", "error")
        return redirect(url_for("home"))

    if department not in DEPARTMENTS:
        flash("Please select a valid department.", "error")
        return redirect(url_for("home"))

    with connect_db() as con:
        con.execute("""
            INSERT INTO patients
            (patient_code, department, status, check_in)
            VALUES (?, ?, 'Waiting', ?)
        """, (
            code,
            department,
            datetime.now().strftime("%Y-%m-%d %H:%M")
        ))

    flash(f"{code} added to {department} queue.", "success")
    return redirect(url_for("home"))


@app.route("/start/<int:patient_id>", methods=["POST"])
def start_patient(patient_id):
    with connect_db() as con:
        patient = con.execute(
            "SELECT * FROM patients WHERE id=?",
            (patient_id,)
        ).fetchone()

        if patient and patient["status"] == "Waiting":
            con.execute("""
                UPDATE patients
                SET status='In Consultation', start_time=?
                WHERE id=?
            """, (
                datetime.now().isoformat(timespec="seconds"),
                patient_id
            ))

            flash(
                f"Consultation started for {patient['patient_code']}.",
                "success"
            )
        else:
            flash("Patient not found in the waiting queue.", "error")

    return redirect(url_for("home"))


@app.route("/complete/<int:patient_id>", methods=["POST"])
def complete_patient(patient_id):
    with connect_db() as con:
        patient = con.execute(
            "SELECT * FROM patients WHERE id=?",
            (patient_id,)
        ).fetchone()

        if patient and patient["status"] == "In Consultation":
            start_time = datetime.fromisoformat(patient["start_time"])
            end_time = datetime.now()

            duration = max(
                0.1,
                (end_time - start_time).total_seconds() / 60
            )

            con.execute("""
                UPDATE patients
                SET status='Completed', end_time=?, duration=?
                WHERE id=?
            """, (
                end_time.isoformat(timespec="seconds"),
                duration,
                patient_id
            ))

            flash(
                f"Consultation completed. Duration: {duration:.1f} minutes.",
                "success"
            )
        else:
            flash("Start the consultation before completing it.", "error")

    return redirect(url_for("home"))


@app.route("/dashboard")
def dashboard():
    with connect_db() as con:
        queue = get_queue_data(con)

        rows = con.execute("""
            SELECT duration FROM patients
            WHERE status='Completed' AND duration IS NOT NULL
        """).fetchall()

        durations = [float(row["duration"]) for row in rows]

    stats = calculate_statistics(durations)

    max_wait = max(
        [d["waiting"] for d in queue] + [1]
    )

    return render_template_string(
        HTML,
        page="dashboard",
        queue=queue,
        stats=stats,
        max_wait=max_wait,
        departments=DEPARTMENTS
    )


# ---------------- RUN APPLICATION ----------------

if __name__ == "__main__":
    initialize_database()

    print("CareQueue Hospital Queue Analyzer is starting...")
    print("Open your browser at http://127.0.0.1:5000")

    app.run(debug=True)