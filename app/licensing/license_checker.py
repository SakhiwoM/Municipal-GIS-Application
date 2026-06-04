import json
import os
import datetime

LICENSE_FILE = "license.json"

def load_local_license():
    if not os.path.exists(LICENSE_FILE):
        return None
    with open(LICENSE_FILE, "r") as f:
        return json.load(f)

def save_local_license(data):
    with open(LICENSE_FILE, "w") as f:
        json.dump(data, f)

def is_license_valid():
    data = load_local_license()
    if not data:
        return False

    expiry = datetime.datetime.strptime(data["expiry"], "%Y-%m-%d")
    return datetime.datetime.now() < expiry

def activate_license(key):
    # For now, we simulate a license server
    if key == "TEST-1234":
        expiry = (datetime.datetime.now() + datetime.timedelta(days=365)).strftime("%Y-%m-%d")
        save_local_license({"key": key, "expiry": expiry})
        return True
    return False
