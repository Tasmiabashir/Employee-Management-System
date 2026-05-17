from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, datetime

app = Flask(__name__)
app.secret_key = "ems_secret_key"

DB = "employees.db"


# ---------- DATABASE ----------
def get_db():
    return sqlite3.connect(DB)


def create_tables():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER,
            date TEXT,
            checkin_time TEXT,
            breakin_time TEXT,
            breakout_time TEXT,
            checkout_time TEXT,
            FOREIGN KEY (employee_id) REFERENCES employees(id)
        )
    """)
    conn.commit()
    conn.close()


# ---------- CREATE EMPLOYEE ----------
@app.route("/admin/create-employee", methods=["GET", "POST"])
def create_employee_page():
    message = ""

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        existing_user = conn.execute(
            "SELECT id FROM employees WHERE username=?",
            (username,)
        ).fetchone()

        if existing_user:
            message = "Username already exists"
        else:
            hashed_password = generate_password_hash(password)
            conn.execute(
                "INSERT INTO employees (username, password) VALUES (?, ?)",
                (username, hashed_password)
            )
            conn.commit()
            message = "Employee created successfully"

        conn.close()

    return render_template("create_employee.html", message=message)


# ---------- LOGIN ----------
@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM employees WHERE username=?",
            (username,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user[2], password):
            session["user_id"] = user[0]
            session["username"] = user[1]
            return redirect(url_for("home"))
        else:
            return "Invalid username or password"

    return render_template("login.html")


# ---------- HOME ----------
@app.route("/home")
def home():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("home.html", username=session["username"])


# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------- ATTENDANCE ----------
@app.route("/checkin", methods=["POST"])
def checkin():
    employee_id = session["user_id"]
    today = str(date.today())
    time_now = datetime.now().strftime("%H:%M:%S")

    conn = get_db()
    record = conn.execute(
        "SELECT id FROM attendance WHERE employee_id=? AND date=?",
        (employee_id, today)
    ).fetchone()

    if not record:
        conn.execute(
            "INSERT INTO attendance (employee_id, date, checkin_time) VALUES (?, ?, ?)",
            (employee_id, today, time_now)
        )
        flash(f"You checked in at {time_now}")
    else:
        flash("You already checked in today")

    conn.commit()
    conn.close()
    return redirect(url_for("home"))


@app.route("/breakin", methods=["POST"])
def breakin():
    employee_id = session["user_id"]
    today = str(date.today())
    time_now = datetime.now().strftime("%H:%M:%S")

    conn = get_db()
    conn.execute("""
        UPDATE attendance SET breakin_time=?
        WHERE employee_id=? AND date=?
    """, (time_now, employee_id, today))
    conn.commit()
    conn.close()

    flash(f"You started break at {time_now}")
    return redirect(url_for("home"))


@app.route("/breakout", methods=["POST"])
def breakout():
    employee_id = session["user_id"]
    today = str(date.today())
    time_now = datetime.now().strftime("%H:%M:%S")

    conn = get_db()
    conn.execute("""
        UPDATE attendance SET breakout_time=?
        WHERE employee_id=? AND date=?
    """, (time_now, employee_id, today))
    conn.commit()
    conn.close()

    flash(f"You ended break at {time_now}")
    return redirect(url_for("home"))


@app.route("/checkout", methods=["POST"])
def checkout():
    employee_id = session["user_id"]
    today = str(date.today())
    time_now = datetime.now().strftime("%H:%M:%S")

    conn = get_db()
    conn.execute("""
        UPDATE attendance SET checkout_time=?
        WHERE employee_id=? AND date=?
    """, (time_now, employee_id, today))
    conn.commit()
    conn.close()

    flash(f"You checked out at {time_now}")
    return redirect(url_for("home"))


# ---------- ADMIN EMPLOYEE LIST ----------
@app.route("/admin/employees")
def employee_list():
    conn = get_db()
    employees = conn.execute("SELECT id, username FROM employees").fetchall()
    conn.close()
    return render_template("employee_list.html", employees=employees)

# ---------- TIME DIFFERENCE ----------
def time_diff(start, end):
    if not start or not end:
        return 0
    fmt = "%H:%M:%S"
    start_dt = datetime.strptime(start, fmt)
    end_dt = datetime.strptime(end, fmt)
    return int((end_dt - start_dt).total_seconds())


# ---------- USER MONTHLY TIME LOG (UPDATED) ----------
@app.route("/user/timelog/<int:user_id>")
def user_timelog(user_id):
    year = date.today().year
    month = date.today().month

    conn = get_db()

    user = conn.execute(
        "SELECT username FROM employees WHERE id=?",
        (user_id,)
    ).fetchone()

    records = conn.execute("""
        SELECT date, checkin_time, checkout_time, breakin_time, breakout_time
        FROM attendance
        WHERE employee_id=?
        AND strftime('%Y', date)=?
        AND strftime('%m', date)=?
    """, (user_id, str(year), f"{month:02d}")).fetchall()

    conn.close()

    days = {}

    for r in records:
        day = int(r[0].split("-")[2])

        total_sec = time_diff(r[1], r[2])
        break_sec = time_diff(r[3], r[4])
        online_sec = total_sec - break_sec

        days[day] = {
            "total": total_sec,
            "online": online_sec,
            "break": break_sec
        }

    return render_template(
        "timelog.html",
        username=user[0],
        days=days,
        month=month,
        year=year
    )
def create_projects_table():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            color TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()
create_projects_table()

@app.route("/admin/projects")
def project_list():
    conn = get_db()
    projects = conn.execute(
        "SELECT id, name, color FROM projects"
    ).fetchall()
    conn.close()

    return render_template("projects.html", projects=projects)

def seed_projects():
    conn = get_db()
    conn.executemany("""
        INSERT INTO projects (name, color)
        VALUES (?, ?)
    """, [
        ("Sd Forge", "#6a007a"),
        ("Rp Generator", "#b3dbe8"),
        ("Tommy Project", "#ffa500"),
        ("Smarty Project", "#0000ff"),
        ("Glubbux Project", "#7a007a"),
        ("Youtube Arazhul Reallife Videos", "#90ee90"),
        ("Marketplace Map", "#c4a000"),
        ("Marketplace Project", "#cd7f32"),
        ("Marketplace Skin Packs", "#d32f2f"),
        ("Data management", "#ffff00"),
        ("Meetings/Correspondence", "#ffd700"),
    ])
    conn.commit()
    conn.close()

@app.route("/admin/projects/create", methods=["GET", "POST"])
def create_project():
    if request.method == "POST":
        name = request.form["name"]
        color = request.form["color"]

        conn = get_db()
        conn.execute(
            "INSERT INTO projects (name, color) VALUES (?, ?)",
            (name, color)
        )
        conn.commit()
        conn.close()

        return redirect(url_for("project_list"))

    return render_template("create_project.html")

def create_employee_projects_table():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS employee_projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER,
            project_id INTEGER,
            FOREIGN KEY (employee_id) REFERENCES employees(id),
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    """)
    conn.commit()
    conn.close()
create_employee_projects_table()

@app.route("/admin/assign-project", methods=["GET", "POST"])
def assign_project():
    conn = get_db()

    employees = conn.execute(
        "SELECT id, username FROM employees"
    ).fetchall()

    projects = conn.execute(
        "SELECT id, name FROM projects"
    ).fetchall()

    if request.method == "POST":
        employee_id = request.form["employee_id"]
        project_ids = request.form.getlist("project_ids[]")

        for project_id in project_ids:
            conn.execute(
                "INSERT INTO employee_projects (employee_id, project_id) VALUES (?, ?)",
                (employee_id, project_id)
            )

        conn.commit()
        conn.close()
        return redirect(url_for("employee_list"))

    conn.close()
    return render_template( "assign_project.html", employees=employees, projects=projects )

@app.route("/admin/projects/update/<int:project_id>", methods=["GET", "POST"])
def update_project(project_id):
    conn = get_db()

    project = conn.execute(
        "SELECT id, name, color FROM projects WHERE id=?",
        (project_id,)
    ).fetchone()

    employees = conn.execute(
        "SELECT id, username FROM employees"
    ).fetchall()

    assigned_employees = conn.execute(
        "SELECT employee_id FROM employee_projects WHERE project_id=?",
        (project_id,)
    ).fetchall()

    assigned_ids = [e[0] for e in assigned_employees]

    if request.method == "POST":
        name = request.form["name"]
        color = request.form["color"]
        employee_ids = request.form.getlist("employee_ids[]")

        # Update project info
        conn.execute(
            "UPDATE projects SET name=?, color=? WHERE id=?",
            (name, color, project_id)
        )

        # Remove old assignments
        conn.execute(
            "DELETE FROM employee_projects WHERE project_id=?",
            (project_id,)
        )

        # Add new assignments
        for emp_id in employee_ids:
            conn.execute(
                "INSERT INTO employee_projects (employee_id, project_id) VALUES (?, ?)",
                (emp_id, project_id)
            )

        conn.commit()
        conn.close()
        return redirect(url_for("project_list"))

    conn.close()
    return render_template(
        "update_project.html",
        project=project,
        employees=employees,
        assigned_ids=assigned_ids
    )
#  employee detail pages
@app.route("/admin/employee/<int:employee_id>")
def employee_detail(employee_id):

    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()

    employee = conn.execute(
        "SELECT id, username FROM employees WHERE id=?",
        (employee_id,)
    ).fetchone()

    if not employee:
        conn.close()
        return "Employee not found", 404

    projects = conn.execute("""
        SELECT p.id, p.name, p.color
        FROM projects p
        JOIN employee_projects ep ON p.id = ep.project_id
        WHERE ep.employee_id=?
    """, (employee_id,)).fetchall()

    conn.close()

    return render_template(
        "employee_detail.html",
        employee=employee,
        projects=projects
    )


# ---------- RUN ----------
if __name__ == "__main__":
    create_tables()
    app.run(debug=True)
