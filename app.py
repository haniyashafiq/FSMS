import os
import calendar
from datetime import datetime, timedelta
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

# --- FACILITY ROUND HELPERS ---
def month_key_from_date(dt=None):
    dt = dt or datetime.now()
    return dt.strftime("%Y-%m")


def parse_month_key(month_key):
    try:
        year, month = month_key.split("-")
        return int(year), int(month)
    except Exception:
        today = datetime.now()
        return today.year, today.month


def get_week_of_month(dt):
    return ((dt.day - 1) // 7) + 1


def get_week_date_range(year, month, week_number):
    days_in_month = calendar.monthrange(year, month)[1]
    start_day = (week_number - 1) * 7 + 1
    if start_day > days_in_month:
        return None, None
    start_date = datetime(year, month, start_day)
    month_end = datetime(year, month, days_in_month) + timedelta(days=1)
    end_date = min(start_date + timedelta(days=7), month_end)
    return start_date, end_date


def reset_auto_completed_week(month_key, week_number):
    mongo.db.facility_rounds.update_many(
        {"month_key": month_key, "week_number": week_number, "auto_completed": True},
        {"$set": {
            "auto_completed": False,
            "auto_completed_at": None,
            "auto_reason": None,
            "status": "Pending"
        }}
    )


def auto_complete_week_if_clear(month_key, week_number, pending_count=None):
    year, month = parse_month_key(month_key)
    start_date, end_date = get_week_date_range(year, month, week_number)
    if not start_date:
        return False
    now = datetime.now()
    if pending_count is None:
        pending_count = mongo.db.maintenance.count_documents({
            "status": "Pending",
            "date": {"$gte": start_date, "$lt": end_date}
        })
    if now < end_date:
        reset_auto_completed_week(month_key, week_number)
        return False
    if pending_count == 0:
        mongo.db.facility_rounds.update_many(
            {"month_key": month_key, "week_number": week_number},
            {"$set": {
                "status": "Completed",
                "auto_completed": True,
                "auto_completed_at": datetime.now(),
                "auto_reason": "All maintenance requests resolved for this week",
                "checked_by": "system"
            }}
        )
        return True
    reset_auto_completed_week(month_key, week_number)
    return False


def get_weekly_maintenance_snapshot(month_key):
    year, month = parse_month_key(month_key)
    summary = []
    now = datetime.now()
    for week in range(1, 6):
        start_date, end_date = get_week_date_range(year, month, week)
        if not start_date:
            summary.append({
                "week": week,
                "pending_requests": 0,
                "auto_completed": False,
                "manual_completed": 0,
                "window": "N/A",
                "state": "future"
            })
            continue
        pending = mongo.db.maintenance.count_documents({
            "status": "Pending",
            "date": {"$gte": start_date, "$lt": end_date}
        })
        state = "future"
        if start_date <= now < end_date:
            state = "active"
        elif now >= end_date:
            state = "past"
        auto_flag = auto_complete_week_if_clear(month_key, week, pending)
        manual_completed = mongo.db.facility_rounds.count_documents({
            "month_key": month_key,
            "week_number": week,
            "status": "Completed",
            "auto_completed": {"$ne": True}
        })
        window = f"{start_date.strftime('%b %d')} – {(end_date - timedelta(days=1)).strftime('%b %d')}"
        summary.append({
            "week": week,
            "pending_requests": pending,
            "auto_completed": auto_flag,
            "manual_completed": manual_completed,
            "window": window,
            "state": state
        })
    return summary


def get_recent_month_options(count=6):
    now = datetime.now()
    year = now.year
    month = now.month
    options = []
    for _ in range(count):
        anchor = datetime(year, month, 1)
        options.append({
            "key": anchor.strftime("%Y-%m"),
            "label": anchor.strftime("%B %Y")
        })
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    return options


def evaluate_auto_week_for_date(dt):
    if not dt:
        dt = datetime.now()
    month_key = month_key_from_date(dt)
    week_number = get_week_of_month(dt)
    auto_complete_week_if_clear(month_key, week_number)

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

    request_doc = mongo.db.maintenance.find_one({"_id": ObjectId(id)})
    if not request_doc:
        flash("Maintenance request not found")
        return redirect(url_for('maintenance_queue'))

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
    evaluate_auto_week_for_date(request_doc.get("date"))
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

# --- FACILITY ROUND CHECK MODULE ---

@app.route('/facility_rounds')
@login_required
def facility_rounds_view():
    if current_user.role != 'Admin':
        flash("Unauthorized")
        return redirect(url_for('dashboard'))

    month_key = request.args.get('month') or month_key_from_date()
    try:
        selected_week = int(request.args.get('week', 1))
    except (TypeError, ValueError):
        selected_week = 1
    selected_week = max(1, min(selected_week, 5))

    checklist_docs = list(mongo.db.facility_checklist.find().sort([("area", 1), ("item", 1)]))
    checklist_by_area = {}
    for doc in checklist_docs:
        area = (doc.get("area") or "General").strip() or "General"
        checklist_by_area.setdefault(area, []).append({
            "id": str(doc['_id']),
            "item": doc.get("item", "Unnamed item")
        })

    historic_areas = mongo.db.facility_rounds.distinct("area")
    for area_name in historic_areas:
        if area_name and area_name not in checklist_by_area:
            checklist_by_area[area_name] = []

    areas = sorted(checklist_by_area.keys())
    selected_area = request.args.get('area')
    if not selected_area and areas:
        selected_area = areas[0]
    selected_items = checklist_by_area.get(selected_area, []) if selected_area else []

    selected_round_doc = None
    selected_item_lookup = {}
    if selected_area:
        selected_round_doc = mongo.db.facility_rounds.find_one({
            "month_key": month_key,
            "area": selected_area,
            "week_number": selected_week
        })
    if selected_round_doc:
        for result in selected_round_doc.get("results", []):
            result_id = str(result.get("item_id"))
            selected_item_lookup[result_id] = {
                "checked": result.get("checked"),
                "note": result.get("note", "")
            }

    week_summary = get_weekly_maintenance_snapshot(month_key)
    year, month = parse_month_key(month_key)
    month_label = datetime(year, month, 1).strftime("%B %Y")
    selected_week_snapshot = next((w for w in week_summary if w["week"] == selected_week), {})

    context = {
        "month_key": month_key,
        "month_label": month_label,
        "month_options": get_recent_month_options(),
        "week_summary": week_summary,
        "selected_week": selected_week,
        "areas": areas,
        "selected_area": selected_area,
        "selected_items": selected_items,
        "selected_round": selected_round_doc,
        "selected_item_lookup": selected_item_lookup,
        "selected_round_status": selected_round_doc.get("status") if selected_round_doc else "Pending",
        "selected_round_notes": (selected_round_doc.get("notes") if selected_round_doc else "") or "",
        "has_checklist": bool(checklist_docs),
        "checklist_by_area": checklist_by_area,
        "selected_week_snapshot": selected_week_snapshot
    }
    return render_template('facility_rounds.html', **context)


@app.route('/facility_rounds/checklist/add', methods=['POST'])
@login_required
def add_facility_checklist_item():
    if current_user.role != 'Admin':
        flash("Unauthorized")
        return redirect(url_for('dashboard'))

    area = (request.form.get('area') or '').strip()
    item_label = (request.form.get('item') or '').strip()
    if not area or not item_label:
        flash("Area and checklist item are required")
        return redirect(url_for('facility_rounds_view'))

    mongo.db.facility_checklist.insert_one({
        "area": area,
        "item": item_label,
        "created_by": current_user.username,
        "created_at": datetime.now()
    })
    flash("Checklist item added")
    return redirect(url_for('facility_rounds_view', area=area))


@app.route('/facility_rounds/checklist/delete/<id>', methods=['POST'])
@login_required
def delete_facility_checklist_item(id):
    if current_user.role != 'Admin':
        flash("Unauthorized")
        return redirect(url_for('dashboard'))
    redirect_area = request.form.get('redirect_area')
    try:
        mongo.db.facility_checklist.delete_one({"_id": ObjectId(id)})
        flash("Checklist item removed")
    except Exception:
        flash("Unable to remove checklist item")
    if redirect_area:
        return redirect(url_for('facility_rounds_view', area=redirect_area))
    return redirect(url_for('facility_rounds_view'))


@app.route('/facility_rounds/week/save', methods=['POST'])
@login_required
def save_facility_round_week():
    if current_user.role != 'Admin':
        flash("Unauthorized")
        return redirect(url_for('dashboard'))

    month_key = request.form.get('month_key') or month_key_from_date()
    area = (request.form.get('area') or '').strip()
    if not area:
        flash("Please select an area before saving")
        return redirect(url_for('facility_rounds_view', month=month_key))

    try:
        week_number = int(request.form.get('week_number', 1))
    except (TypeError, ValueError):
        week_number = 1
    week_number = max(1, min(week_number, 5))

    notes = (request.form.get('notes') or '').strip()
    mark_complete = request.form.get('mark_complete') == 'on'
    checklist_ids = request.form.getlist('checklist_ids')

    results = []
    for checklist_id in checklist_ids:
        try:
            item_obj = mongo.db.facility_checklist.find_one({"_id": ObjectId(checklist_id)})
        except Exception:
            item_obj = None
        if not item_obj:
            continue
        results.append({
            "item_id": item_obj['_id'],
            "item": item_obj.get('item'),
            "area": item_obj.get('area'),
            "checked": request.form.get(f'status_{checklist_id}') == 'on',
            "note": (request.form.get(f'note_{checklist_id}') or '').strip()
        })

    update_doc = {
        "month_key": month_key,
        "area": area,
        "week_number": week_number,
        "results": results,
        "notes": notes,
        "status": "Completed" if mark_complete else "Pending",
        "checked_by": current_user.username,
        "updated_at": datetime.now(),
        "auto_completed": False,
        "auto_completed_at": None,
        "auto_reason": None
    }

    mongo.db.facility_rounds.update_one(
        {"month_key": month_key, "area": area, "week_number": week_number},
        {"$set": update_doc},
        upsert=True
    )

    auto_complete_week_if_clear(month_key, week_number)
    flash(f"Week {week_number} inspection saved for {area}")
    return redirect(url_for('facility_rounds_view', month=month_key, area=area, week=week_number))

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
