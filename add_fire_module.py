import os
from pymongo import MongoClient
from datetime import datetime

# --- CONFIGURATION ---
# Connect to the same database as your app
mongo_uri = os.environ.get("MONGO_URI", "mongodb+srv://taha_admin:hospital123@cluster0.ukoxtzf.mongodb.net/fsms_db?retryWrites=true&w=majority&appName=Cluster0&authSource=admin")
client = MongoClient(mongo_uri)
db = client.fsms_db
collection = db.fire_extinguishers

# --- DATA FROM WORD DOCUMENT  ---
fire_data = [
    # Ground Floor
    {"fe_id": "FE001", "location": "GF", "type": "P", "capacity": "6 KG", "nozzle": "√", "seal": "√", "body": "√", "pin": "√", "gauge": "√", "handle": "√", "last_insp": "", "next_insp": "", "remarks": "√"},
    {"fe_id": "FE002", "location": "GF", "type": "P", "capacity": "6 KG", "nozzle": "√", "seal": "√", "body": "√", "pin": "√", "gauge": "√", "handle": "√", "last_insp": "", "next_insp": "", "remarks": "√"},
    {"fe_id": "FE003", "location": "GF", "type": "P", "capacity": "6 KG", "nozzle": "√", "seal": "√", "body": "√", "pin": "√", "gauge": "√", "handle": "√", "last_insp": "", "next_insp": "", "remarks": "√"},
    {"fe_id": "FE004", "location": "GF", "type": "P", "capacity": "6 KG", "nozzle": "√", "seal": "√", "body": "√", "pin": "√", "gauge": "√", "handle": "√", "last_insp": "", "next_insp": "", "remarks": "√"},
    {"fe_id": "FE005", "location": "GF", "type": "Co2", "capacity": "", "nozzle": "√", "seal": "√", "body": "√", "pin": "√", "gauge": "√", "handle": "√", "last_insp": "", "next_insp": "", "remarks": "√"},
    {"fe_id": "FE006", "location": "GF", "type": "Co2", "capacity": "", "nozzle": "√", "seal": "√", "body": "√", "pin": "√", "gauge": "√", "handle": "√", "last_insp": "", "next_insp": "", "remarks": "√"},
    {"fe_id": "FE007", "location": "GF", "type": "Co2", "capacity": "", "nozzle": "√", "seal": "√", "body": "√", "pin": "√", "gauge": "√", "handle": "√", "last_insp": "", "next_insp": "", "remarks": "√"},
    {"fe_id": "FE008", "location": "GF", "type": "Co2", "capacity": "", "nozzle": "√", "seal": "√", "body": "√", "pin": "√", "gauge": "√", "handle": "√", "last_insp": "", "next_insp": "", "remarks": "√"},
    
    # 1st Floor
    {"fe_id": "FE009", "location": "1 floor", "type": "P", "capacity": "", "nozzle": "√", "seal": "√", "body": "√", "pin": "√", "gauge": "√", "handle": "√", "last_insp": "", "next_insp": "", "remarks": "√"},
    {"fe_id": "FE010", "location": "1 floor", "type": "Co2", "capacity": "", "nozzle": "√", "seal": "√", "body": "√", "pin": "√", "gauge": "√", "handle": "√", "last_insp": "", "next_insp": "", "remarks": "√"},
    {"fe_id": "FE011", "location": "1 floor", "type": "P", "capacity": "", "nozzle": "√", "seal": "√", "body": "√", "pin": "√", "gauge": "√", "handle": "√", "last_insp": "", "next_insp": "", "remarks": "√"},
    {"fe_id": "FE012", "location": "1 floor", "type": "Co2", "capacity": "", "nozzle": "√", "seal": "√", "body": "√", "pin": "√", "gauge": "√", "handle": "√", "last_insp": "", "next_insp": "", "remarks": "√"},
    {"fe_id": "FE013", "location": "1 floor", "type": "P", "capacity": "", "nozzle": "√", "seal": "√", "body": "√", "pin": "√", "gauge": "√", "handle": "√", "last_insp": "", "next_insp": "", "remarks": "√"},

    # 2nd Floor
    {"fe_id": "FE014", "location": "2 floor", "type": "Co2", "capacity": "", "nozzle": "√", "seal": "√", "body": "√", "pin": "√", "gauge": "√", "handle": "√", "last_insp": "", "next_insp": "", "remarks": "√"},
    {"fe_id": "FE015", "location": "2 floor", "type": "P", "capacity": "", "nozzle": "√", "seal": "√", "body": "√", "pin": "√", "gauge": "√", "handle": "√", "last_insp": "", "next_insp": "", "remarks": "√"},
    {"fe_id": "FE016", "location": "2 floor", "type": "Co2", "capacity": "", "nozzle": "√", "seal": "√", "body": "√", "pin": "√", "gauge": "√", "handle": "√", "last_insp": "", "next_insp": "", "remarks": "√"},
    {"fe_id": "FE017", "location": "2 floor", "type": "P", "capacity": "", "nozzle": "√", "seal": "√", "body": "√", "pin": "√", "gauge": "√", "handle": "√", "last_insp": "", "next_insp": "", "remarks": "√"},
    {"fe_id": "FE018", "location": "2 floor", "type": "Co2", "capacity": "", "nozzle": "√", "seal": "√", "body": "√", "pin": "√", "gauge": "√", "handle": "√", "last_insp": "", "next_insp": "", "remarks": "√"},
    {"fe_id": "FE019", "location": "2 floor", "type": "P", "capacity": "", "nozzle": "√", "seal": "√", "body": "√", "pin": "√", "gauge": "√", "handle": "√", "last_insp": "", "next_insp": "", "remarks": "√"},
    {"fe_id": "FE020", "location": "2 floor", "type": "P", "capacity": "", "nozzle": "√", "seal": "√", "body": "√", "pin": "√", "gauge": "√", "handle": "√", "last_insp": "", "next_insp": "", "remarks": "√"},

    # 3rd Floor
    {"fe_id": "FE021", "location": "3 floor", "type": "Co2", "capacity": "", "nozzle": "√", "seal": "√", "body": "√", "pin": "√", "gauge": "√", "handle": "√", "last_insp": "", "next_insp": "", "remarks": "√"},
    {"fe_id": "FE022", "location": "3 floor", "type": "P", "capacity": "", "nozzle": "√", "seal": "√", "body": "√", "pin": "√", "gauge": "√", "handle": "√", "last_insp": "", "next_insp": "", "remarks": "√"},
    {"fe_id": "FE023", "location": "3 floor", "type": "Co2", "capacity": "", "nozzle": "√", "seal": "√", "body": "√", "pin": "√", "gauge": "√", "handle": "√", "last_insp": "", "next_insp": "", "remarks": "√"},
    {"fe_id": "FE024", "location": "3 floor", "type": "P", "capacity": "", "nozzle": "√", "seal": "√", "body": "√", "pin": "√", "gauge": "√", "handle": "√", "last_insp": "", "next_insp": "", "remarks": "√"},
    {"fe_id": "FE025", "location": "3 floor", "type": "Co2", "capacity": "", "nozzle": "√", "seal": "√", "body": "√", "pin": "√", "gauge": "√", "handle": "√", "last_insp": "", "next_insp": "", "remarks": "√"},
    {"fe_id": "FE026", "location": "3 floor", "type": "P", "capacity": "", "nozzle": "√", "seal": "√", "body": "√", "pin": "√", "gauge": "√", "handle": "√", "last_insp": "", "next_insp": "", "remarks": "√"},
    {"fe_id": "FE027", "location": "3 floor", "type": "Co2", "capacity": "", "nozzle": "√", "seal": "√", "body": "√", "pin": "√", "gauge": "√", "handle": "√", "last_insp": "", "next_insp": "", "remarks": "√"},

    # Empty Rows from Source (Placeholders)
    {"fe_id": "FE028", "location": "", "type": "", "capacity": "", "nozzle": "", "seal": "", "body": "", "pin": "", "gauge": "", "handle": "", "last_insp": "", "next_insp": "", "remarks": ""},
    {"fe_id": "FE029", "location": "", "type": "", "capacity": "", "nozzle": "", "seal": "", "body": "", "pin": "", "gauge": "", "handle": "", "last_insp": "", "next_insp": "", "remarks": ""},
    {"fe_id": "FE030", "location": "", "type": "", "capacity": "", "nozzle": "", "seal": "", "body": "", "pin": "", "gauge": "", "handle": "", "last_insp": "", "next_insp": "", "remarks": ""}
]

# --- EXECUTION ---
def seed_db():
    print("Deleting old fire extinguisher records (if any)...")
    collection.delete_many({}) # Clear table to avoid duplicates
    
    print(f"Inserting {len(fire_data)} records...")
    collection.insert_many(fire_data)
    
    print("✅ Success! Database populated with 30 records.")

if __name__ == "__main__":
    seed_db()