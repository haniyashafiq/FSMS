import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, Response
from flask_pymongo import PyMongo
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from bson.objectid import ObjectId
from pymongo.uri_parser import parse_uri

app = Flask(__name__)

# --- CONFIGURATION ---
mongo_uri = os.environ.get("MONGO_URI", "mongodb+srv://taha_admin:hospital123@cluster0.ukoxtzf.mongodb.net/fsms_db?retryWrites=true&w=majority&appName=Cluster0&authSource=admin")
app.config["MONGO_URI"] = mongo_uri
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "fsms_secret_key_9988")

mongo = PyMongo(app)

# Startup diagnostics (safe: does not print credentials)
try:
    _parsed = parse_uri(mongo_uri)
    print(f"[FSMS] Connected MongoDB database: {mongo.db.name}")
    print(f"[FSMS] Connected MongoDB hosts: {_parsed.get('nodelist')}")
except Exception:
    print(f"[FSMS] Connected MongoDB database: {mongo.db.name}")
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- AUTOMATION ---
def send_automated_email(recipient_role, subject, content):
    print(f"\n[EMAIL SENT] To: {recipient_role} | Subject: {subject}")
    print(f"Body: {content}\n")

# --- USER LOADER ---
class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.username = user_data['username']
        self.role = user_data['role']

@login_manager.user_loader
def load_user(user_id):
    try:
        user_data = mongo.db.users.find_one({"_id": ObjectId(user_id)})
        if user_data:
            return User(user_data)
    except:
        return None
    return None

# --- ROUTES ---

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = mongo.db.users.find_one({"username": username})
        if user and user['password'] == password:
            login_user(User(user))
            return redirect(url_for('dashboard'))
        flash("Invalid Credentials")
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    safety_count = mongo.db.incidents.count_documents({"status": "Open"})
    maint_count = mongo.db.maintenance.count_documents({"status": "Pending"})
    
    # Simple score logic
    total = mongo.db.incidents.count_documents({})
    resolved = mongo.db.incidents.count_documents({"status": "Resolved"})
    score = int((resolved / total * 100)) if total > 0 else 100

    incidents = mongo.db.incidents.find().sort("date", -1).limit(5)
    maintenance = mongo.db.maintenance.find().sort("date", -1).limit(5)

    return render_template('dashboard.html', 
                           role=current_user.role,
                           safety_count=safety_count,
                           maint_count=maint_count,
                           score=score,
                           incidents=incidents,
                           maintenance=maintenance)

# --- INCIDENT & MAINTENANCE ROUTES ---

@app.route('/log_incident', methods=['GET', 'POST'])
@login_required
def log_incident():
    if request.method == 'POST':
        desc = request.form.get('description')
        severity = request.form.get('severity')
        mongo.db.incidents.insert_one({
            "type": "Safety", "description": desc, "severity": severity,
            "status": "Open", "reported_by": current_user.username, "date": datetime.now()
        })
        if severity == 'High':
            send_automated_email("MD & GM", "URGENT INCIDENT", desc)
        flash("Incident Logged Successfully")
        return redirect(url_for('dashboard'))
    return render_template('forms.html', form_type="Safety Incident")

@app.route('/request_maintenance', methods=['GET', 'POST'])
@login_required
def request_maintenance():
    if request.method == 'POST':
        request_date = request.form.get('request_date')
        apartment_no = request.form.get('apartment_no')
        contact_no = request.form.get('contact_no')
        availability = request.form.get('availability')
        allow_entry = request.form.get('allow_entry', 'no')
        allow_entry_notes = request.form.get('allow_entry_notes')

        request_entries = []
        for idx in range(1, 5):
            desc = request.form.get(f'request_desc_{idx}', '').strip()
            remarks = request.form.get(f'request_remarks_{idx}', '').strip()
            if desc:
                request_entries.append({
                    "line": idx,
                    "description": desc,
                    "remarks": remarks
                })

        if not request_entries:
            flash("Please describe at least one maintenance item before submitting the request.")
            return redirect(url_for('request_maintenance'))

        maintenance_doc = {
            "type": "Maintenance",
            "status": "Pending",
            "requested_by": current_user.username,
            "date": datetime.now(),
            "request_date": request_date,
            "apartment_no": apartment_no,
            "contact_no": contact_no,
            "availability": availability,
            "allow_entry": allow_entry,
            "allow_entry_notes": allow_entry_notes,
            "requests": request_entries,
            "materials_needed": request.form.get('materials_needed'),
            "technician_name": request.form.get('technician_name'),
            "job_completion_date": request.form.get('job_completion_date'),
            "service_rating": request.form.get('service_rating'),
            "service_feedback": request.form.get('service_feedback'),
            "resident_signature": request.form.get('resident_signature')
        }

        mongo.db.maintenance.insert_one(maintenance_doc)

        summary_lines = [f"{entry['description']} ({entry['remarks'] or 'No remarks'})" for entry in request_entries]
        email_body = (
            f"Apartment: {apartment_no or 'N/A'} | Contact: {contact_no or 'N/A'}\n"
            f"Availability: {availability or 'N/A'} | Allow Entry: {allow_entry.upper()}\n"
            + "\n".join(summary_lines)
        )
        send_automated_email("Maintenance Team", "New Maintenance Request", email_body)
        flash("Maintenance Request Submitted")
        return redirect(url_for('dashboard'))

    default_request_date = datetime.now().strftime("%Y-%m-%d")
    return render_template('forms.html', form_type="Maintenance Request", default_request_date=default_request_date)


@app.route('/maintenance')
@login_required
def maintenance_queue():
    if current_user.role != 'Admin':
        flash("Unauthorized")
        return redirect(url_for('dashboard'))

    pending = mongo.db.maintenance.find({"status": "Pending"}).sort("date", -1)
    resolved = mongo.db.maintenance.find({"status": "Resolved"}).sort("resolved_at", -1)
    return render_template('maintenance_queue.html', pending=pending, resolved=resolved)


@app.route('/maintenance/resolve/<id>', methods=['POST'])
@login_required
def resolve_maintenance(id):
    if current_user.role != 'Admin':
        flash("Unauthorized")
        return redirect(url_for('dashboard'))

    mongo.db.maintenance.update_one(
        {"_id": ObjectId(id)},
        {
            "$set": {
                "status": "Resolved",
                "resolved_by": current_user.username,
                "resolved_at": datetime.now(),
            }
        },
    )
    flash("Maintenance Request Resolved")
    return redirect(url_for('maintenance_queue'))


@app.route('/maintenance/report/send')
@login_required
def send_weekly_maintenance_report():
    if current_user.role != 'Admin':
        flash("Unauthorized")
        return redirect(url_for('dashboard'))

    pending = list(mongo.db.maintenance.find({"status": "Pending"}).sort("date", 1))
    if not pending:
        flash("No pending maintenance requests for this week's report")
        return redirect(url_for('maintenance_queue'))

    lines = ["Pending Maintenance Requests (auto-generated weekly report):"]
    for req in pending:
        stamped = req.get("date")
        timestamp = stamped.strftime("%b %d %H:%M") if stamped else "N/A"
        req_list = req.get("requests") or []
        primary = req_list[0] if req_list else {}
        primary_desc = primary.get("description") or req.get("item", "Unknown item")
        primary_remarks = primary.get("remarks") or req.get("issue", "No description")
        apt = req.get("apartment_no", "N/A")
        lines.append(
            f"- Apt {apt}: {primary_desc} ({primary_remarks}) | Reported by {req.get('requested_by', 'N/A')} on {timestamp}"
        )

    subject = "Weekly Pending Maintenance Report"
    content = "\n".join(lines)
    send_automated_email("Maintenance Team", subject, content)
    flash("Weekly maintenance report emailed to the maintenance team")
    return redirect(url_for('maintenance_queue'))

@app.route('/generate_report')
@login_required
def generate_report():
    if current_user.role not in ['Admin', 'MD', 'GM']:
        flash("Unauthorized")
        return redirect(url_for('dashboard'))
    
    # CSV Generator logic remains same...
    return redirect(url_for('dashboard'))

# --- NEW: FIRE EXTINGUISHER MODULE ---

@app.route('/fire_extinguishers')
@login_required
def fire_list():
    extinguishers = mongo.db.fire_extinguishers.find().sort("fe_id", 1)
    return render_template('fire_list.html', extinguishers=extinguishers)

@app.route('/fire_extinguishers/add', methods=['POST'])
@login_required
def add_fire_extinguisher():
    data = {
        "fe_id": request.form.get('fe_id'),
        "location": request.form.get('location'),
        "type": request.form.get('type'),
        "capacity": request.form.get('capacity'),
        # Checkboxes return 'on' if checked, else None. We convert to √ or X
        "nozzle": "√" if request.form.get('nozzle') else "X",
        "seal": "√" if request.form.get('seal') else "X",
        "body": "√" if request.form.get('body') else "X",
        "pin": "√" if request.form.get('pin') else "X",
        "gauge": "√" if request.form.get('gauge') else "X",
        "handle": "√" if request.form.get('handle') else "X",
        "last_insp": request.form.get('last_insp'),
        "next_insp": request.form.get('next_insp'),
        "remarks": request.form.get('remarks')
    }
    mongo.db.fire_extinguishers.insert_one(data)
    flash("Fire Extinguisher Added")
    return redirect(url_for('fire_list'))

@app.route('/fire_extinguishers/delete/<id>')
@login_required
def delete_fire_extinguisher(id):
    mongo.db.fire_extinguishers.delete_one({"_id": ObjectId(id)})
    flash("Entry Deleted")
    return redirect(url_for('fire_list'))

@app.route('/fire_report')
@login_required
def fire_report():
    extinguishers = mongo.db.fire_extinguishers.find().sort("fe_id", 1)
    # Get current date for the report header
    report_date = datetime.now().strftime("%d/ %m/ %Y")
    return render_template('fire_report.html', extinguishers=extinguishers, report_date=report_date)

if __name__ == "__main__":
    app.run(debug=True)
