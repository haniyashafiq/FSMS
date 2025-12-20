"""Seed the facility_checklist collection with baseline areas and items."""
import os
from datetime import datetime

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure


DEFAULT_URI = (
    "mongodb+srv://taha_admin:hospital123@cluster0.ukoxtzf.mongodb.net/"
    "fsms_db?retryWrites=true&w=majority&appName=Cluster0&authSource=admin"
)

SEED_DATA = [
    {
        "area": "Lobby & Reception",
        "items": [
            "Front desk counter clear and tidy",
            "Visitor seating sanitized and aligned",
            "Entry mats dry and free from trip hazards",
            "Digital signage running current content",
            "Ambient lighting levels within spec"
        ],
    },
    {
        "area": "Residential Corridors",
        "items": [
            "Emergency exit signs illuminated",
            "Housekeeping cart parked in designated zone",
            "Fire hose cabinets sealed and accessible",
            "Flooring free from spills or damage",
            "HVAC supply grills dust-free"
        ],
    },
    {
        "area": "Mechanical Plant Room",
        "items": [
            "Pump vibration guards secured",
            "Oil leak trays empty and clean",
            "Pressure gauges within operating band",
            "Spare parts rack organized",
            "Access pathways unobstructed"
        ],
    },
    {
        "area": "Electrical Room",
        "items": [
            "Panel schedules updated and legible",
            "No exposed conductors or open junction boxes",
            "Infrared inspection stickers current",
            "Cable trays free from debris",
            "Rubber mats and PPE available"
        ],
    },
    {
        "area": "Fire Pump Room",
        "items": [
            "Diesel tank level above 75%",
            "Pump controller indicator lights normal",
            "Weekly churn test recorded",
            "Jockey pump pressure switch calibrated",
            "Ventilation fans operational"
        ],
    },
    {
        "area": "Basement Parking",
        "items": [
            "CO sensors within calibration date",
            "Directional arrows freshly marked",
            "Drainage grates free of blockage",
            "Emergency call points tested",
            "Lighting occupancy sensors responsive"
        ],
    },
    {
        "area": "Roof & Facade",
        "items": [
            "Waterproofing membranes intact",
            "Fall protection anchors certified",
            "Gutter strainers cleared",
            "Lightning protection conductors secure",
            "Skylight glass free of cracks"
        ],
    },
    {
        "area": "Pool & Recreation Deck",
        "items": [
            "Chemical dosing logs updated",
            "Deck tiles non-slip and clean",
            "Life-saving equipment sealed",
            "Pool lighting timers synchronized",
            "Plant room exhaust running"
        ],
    },
]


def seed_collection():
    mongo_uri = os.environ.get("MONGO_URI", DEFAULT_URI)
    client = MongoClient(mongo_uri)
    try:
        client.admin.command("ping")
    except ConnectionFailure as exc:
        raise SystemExit(f"Unable to reach MongoDB: {exc}") from exc

    db = client.get_default_database()
    if db is None:
        db = client["fsms_db"]
    collection = db.facility_checklist

    inserted, skipped = 0, 0
    for block in SEED_DATA:
        area = block["area"].strip()
        for item in block["items"]:
            item_label = item.strip()
            existing = collection.find_one({"area": area, "item": item_label})
            if existing:
                skipped += 1
                continue
            collection.insert_one({
                "area": area,
                "item": item_label,
                "created_by": "system_seed",
                "created_at": datetime.utcnow(),
            })
            inserted += 1

    print(
        f"Facility checklist seeding complete. Inserted {inserted} item(s), skipped {skipped}."
    )


if __name__ == "__main__":
    seed_collection()
