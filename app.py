import os
from flask import Flask, render_template, request, redirect, session, send_file
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "your-secret-key"

# File paths for storing credentials and leave applications
STUDENT_CREDENTIALS_FILE = "student_credentials.txt"
HOD_CREDENTIALS_FILE = "hod_credentials.txt"
LEAVE_APPLICATIONS_FILE = "leave_applications.txt"
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def write_credentials(username, password, role):
    """
    Write student or HOD credentials to a file.
    """
    if role == "student":
        credentials_file = STUDENT_CREDENTIALS_FILE
    else:
        credentials_file = HOD_CREDENTIALS_FILE

    with open(credentials_file, "a") as file:
        file.write(f"{username}:{password}\n")


def verify_credentials(username, password, role):
    """
    Verify student or HOD credentials from a file.
    """
    if role == "student":
        credentials_file = STUDENT_CREDENTIALS_FILE
    else:
        credentials_file = HOD_CREDENTIALS_FILE

    with open(credentials_file, "r") as file:
        for line in file:
            stored_username, stored_password = line.strip().split(":")
            if username == stored_username and password == stored_password:
                return True
    return False


def save_leave_application(username, leave_reason, from_date, till_date, year, filename):
    """
    Save leave application and filename to a file.
    """
    with open(LEAVE_APPLICATIONS_FILE, "a") as file:
        file.write(f"{username}:{leave_reason}:{from_date}:{till_date}:{year}:{filename}\n")


def get_leave_applications():
    """
    Retrieve all leave applications from a file.
    """
    leave_applications = []
    with open(LEAVE_APPLICATIONS_FILE, "r") as file:
        for line in file:
            values = line.strip().split(":")
            if len(values) == 6:
                username, leave_reason, from_date, till_date, year, filename = values
                leave_applications.append({
                    'username': username,
                    'leave_reason': leave_reason,
                    'from_date': from_date,
                    'till_date': till_date,
                    'year': year,
                    'filename': filename
                })
            elif len(values) == 7:  # Include the decision in the dictionary
                username, leave_reason, from_date, till_date, year, filename, decision = values
                leave_applications.append({
                    'username': username,
                    'leave_reason': leave_reason,
                    'from_date': from_date,
                    'till_date': till_date,
                    'year': year,
                    'filename': filename,
                    'decision': decision
                })
            else:
                print(f"Ignoring invalid leave application: {line.strip()}")
    return leave_applications


@app.route("/")
def home():
    return redirect("/login")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        role = request.form["role"]

        if verify_credentials(username, password, role):
            session["username"] = username
            session["role"] = role
            if role == "student":
                return redirect("/student/dashboard")
            else:
                return redirect("/hod/dashboard")
        else:
            return render_template("login.html", error="Invalid credentials.")

    return render_template("login.html", error="")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        role = request.form["role"]
        write_credentials(username, password, role)
        return redirect("/login")
    return render_template("register.html")


@app.route("/student/dashboard")
def student_dashboard():
    if "username" not in session or session["role"] != "student":
        return redirect("/login")
    return render_template("student.html")


@app.route("/student/apply_leave", methods=["GET", "POST"])
def apply_leave():
    if "username" not in session or session["role"] != "student":
        return redirect("/login")

    if request.method == "POST":
        username = session["username"]
        leave_reason = request.form["leave_reason"]
        from_date = request.form["from_date"]
        till_date = request.form["till_date"]
        year = request.form["year"]
        
        # Check if a file is uploaded
        if 'file' in request.files:
            file = request.files['file']
            # Secure the filename to prevent any malicious file names
            filename = secure_filename(file.filename)
            # Save the file to the upload folder
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        else:
            filename = None

        save_leave_application(username, leave_reason, from_date, till_date, year, filename)
        return redirect("/student/leave_status")
    return render_template("apply_leave.html")


@app.route("/student/leave_status")
def leave_status():
    if "username" not in session or session["role"] != "student":
        return redirect("/login")

    username = session["username"]
    leave_applications = get_leave_applications()
    user_applications = [app for app in leave_applications if app['username'] == username]
    return render_template("leave_status.html", applications=user_applications)


@app.route("/hod/review_leave", methods=["POST"])
def review_leave():
    if "username" not in session or session["role"] != "hod":
        return redirect("/login")

    application_id = int(request.form["application_id"])
    decision = request.form["decision"]
    leave_applications = get_leave_applications()

    if 0 <= application_id < len(leave_applications):
        application = leave_applications[application_id]
        application['decision'] = decision
        with open(LEAVE_APPLICATIONS_FILE, "w") as file:
            for app in leave_applications:
                file.write(f"{app['username']}:{app['leave_reason']}:{app['from_date']}:{app['till_date']}:{app['year']}:{app['filename']}:{app.get('decision', '')}\n")
        return redirect("/hod/dashboard")
    return "Invalid application ID."


@app.route("/hod/dashboard")
def hod_dashboard():
    if "username" not in session or session["role"] != "hod":
        return redirect("/login")

    leave_applications = get_leave_applications()
    return render_template("hod_dashboard.html", applications=leave_applications)


@app.route("/hod/download_file/<filename>")
def download_file(filename):
    if "username" not in session or session["role"] != "hod":
        return redirect("/login")
    
    # Check if the file exists in the upload folder
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True, download_name=filename)
    else:
        return "File not found."


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


if __name__ == "__main__":
    app.run(debug=True, port=8001)
