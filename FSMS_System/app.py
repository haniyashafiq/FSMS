import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, Response
from flask_pymongo import PyMongo
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from bson.objectid import ObjectId

app = Flask(__name__)

# --- CONFIGURATION ---
# Using 'fsms_db' to keep it separate from your Hospital CRM
mongo_uri = os.environ.get("MONGO_URI", "mongodb+srv://taha_admin:hospital123@cluster0.ukoxtzf.mongodb.net/fsms_db?retryWrites=true&w=majority&appName=Cluster0&authSource=admin")
app.config["MONGO_URI"] = mongo_uri
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "fsms_secret_key_9988")

mongo = PyMongo(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- MOCK EMAIL AUTOMATION ---
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
    safety_issues = mongo.db.incidents.count_documents({"status": "Open"})
    maintenance_reqs = mongo.db.maintenance.count_documents({"status": "Pending"})
    
    total_checks = mongo.db.incidents.count_documents({})
    resolved_checks = mongo.db.incidents.count_documents({"status": "Resolved"})
    compliance_score = int((resolved_checks / total_checks * 100)) if total_checks > 0 else 100

    recent_incidents = mongo.db.incidents.find().sort("date", -1).limit(5)
    recent_maintenance = mongo.db.maintenance.find().sort("date", -1).limit(5)

    return render_template('dashboard.html', 
                           role=current_user.role,
                           safety_count=safety_issues,
                           maint_count=maintenance_reqs,
                           score=compliance_score,
                           incidents=recent_incidents,
                           maintenance=recent_maintenance)

@app.route('/log_incident', methods=['GET', 'POST'])
@login_required
def log_incident():
    if request.method == 'POST':
        desc = request.form.get('description')
        severity = request.form.get('severity')
        
        incident_data = {
            "type": "Safety",
            "description": desc,
            "severity": severity,
            "status": "Open",
            "reported_by": current_user.username,
            "date": datetime.now()
        }
        mongo.db.incidents.insert_one(incident_data)
        
        if severity == 'High':
            send_automated_email("MD & GM", "URGENT: High Severity Incident", f"Reported by {current_user.username}: {desc}")
            
        flash("Incident Logged Successfully")
        return redirect(url_for('dashboard'))
    return render_template('forms.html', form_type="Safety Incident")

@app.route('/request_maintenance', methods=['GET', 'POST'])
@login_required
def request_maintenance():
    if request.method == 'POST':
        item = request.form.get('item')
        issue = request.form.get('issue')
        
        maint_data = {
            "type": "Maintenance",
            "item": item,
            "issue": issue,
            "status": "Pending",
            "requested_by": current_user.username,
            "date": datetime.now()
        }
        mongo.db.maintenance.insert_one(maint_data)
        
        send_automated_email("Maintenance Team", "New Request", f"Item: {item} - Issue: {issue}")
        
        flash("Maintenance Request Sent")
        return redirect(url_for('dashboard'))
    return render_template('forms.html', form_type="Maintenance Request")

@app.route('/generate_report')
@login_required
def generate_report():
    if current_user.role not in ['Admin', 'MD', 'GM']:
        flash("Unauthorized")
        return redirect(url_for('dashboard'))

    incidents = mongo.db.incidents.find()
    
    def generate():
        data = [["ID", "Type", "Description", "Severity/Item", "Status", "Date"]]
        for i in incidents:
            data.append([str(i['_id']), "Incident", i['description'], i['severity'], i['status'], i['date']])
        
        yield ','.join(data[0]) + '\n'
        for row in data[1:]:
            yield ','.join([str(x) for x in row]) + '\n'

    return Response(generate(), mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=weekly_fsms_report.csv"})

@app.route('/setup')
def setup():
    if not mongo.db.users.find_one({"username": "admin"}):
        mongo.db.users.insert_one({"username": "admin", "password": "123", "role": "Admin"})
        mongo.db.users.insert_one({"username": "md", "password": "123", "role": "MD"})
        return "Users Created! Login with admin/123"
    return "Users already exist."

if __name__ == "__main__":
    app.run(debug=True)
