import json
import random
import datetime
from datetime import timedelta
import os
import re

def has_link(text: str) -> bool:
    # Regex for URL
    url_pattern = r"(https?://[^\s]+|www\.[^\s]+)"
    # Regex for @mention (letters, numbers, underscores, dots)
    mention_pattern = r"@\w[\w.]*"
    return re.search(url_pattern, text) is not None or re.search(mention_pattern, text) is not None


otps_dir = "otps.json"  # your JSON file
users_dir = "users.json"  # your JSON file
blocked_dir = 'blocked.json'

def generate_otp():
    global otps_dir
    # Load existing OTPs
    with open(otps_dir, 'r') as file:
        otps_json = json.load(file)

    existing = [int(number['otp']) for number in otps_json]

    # Generate unique OTP
    otp = random.randint(100000, 999999)
    while otp in existing:
        otp = random.randint(100000, 999999)

    # Add new entry
    new_data = {
        "otp": otp,
        "created_at": None,
        "user_id":None,
        'interval':2
    }
    otps_json.append(new_data)

    # Save back to JSON
    with open(otps_dir, 'w') as file:
        json.dump(otps_json, file, indent=4)

    return otp


def is_user_otp_verified(id):
    global otps_dir
    with open(otps_dir, 'r') as file:
        otps = json.load(file)
    return any(otp["user_id"] == id for otp in otps)

def occupy_otp(id, otp):
    global otps_dir
    with open(otps_dir, 'r') as file:
        otps = json.load(file)
    for data in otps:
        if data['otp'] == otp:
            data['user_id'] = id
            data['created_at'] = datetime.datetime.now().isoformat()
            break
    with open(otps_dir, 'w') as file:
        json.dump(otps, file, indent=4)
    

def is_free_otp(otp):
    global otps_dir
    with open(otps_dir, 'r') as file:
        otps = json.load(file)

    return any(entry.get("otp") == otp and entry.get("user_id") is None for entry in otps)



def sortify_otp():
    users = []
    sortified = []
    global otps_dir
    with open(otps_dir, 'r') as file:
        otps = json.load(file)
    for val in otps:
        created_at = datetime.datetime.fromisoformat(val['created_at'])
        if datetime.datetime.utcnow() - created_at > timedelta(days=30):
            users.append(val['user_id'])
        else:
            sortified.append(val)
    with open(otps_dir, 'w') as file:
        json.dump(sortified, file, indent=4)
    return users

def add_users(user_id: int):
    global users_dir

    # Load existing users (or start with empty list if file doesn't exist yet)
    if os.path.exists(users_dir):
        with open(users_dir, 'r') as file:
            users = json.load(file)
    else:
        users = []

    # Extract only IDs
    user_ids = [u['user_id'] for u in users]

    # Add if not exists
    if user_id not in user_ids:
        users.append({'user_id': user_id})

        with open(users_dir, 'w') as file:
            json.dump(users, file, indent=4)

        return True  # new user added
    return False  # already exists

def get_user_num():
    global users_dir
    with open(users_dir, 'r') as file:
        user_json = json.load(file)
    return len(user_json)

def add_interval():
    global otps_dir
    with open(otps_dir, 'r') as file:
        otps = json.load(file)
    for otp in otps:
        otp['interval']= 2
    with open(otps_dir, 'w') as file:
        json.dump(otps, file, indent=4)


def update_interval(id, interval):
    global otps_dir
    with open(otps_dir, 'r') as file:
        otps = json.load(file)
    for otp in otps:
        if otp['user_id'] == id:
            otp['interval'] = interval
            break
    with open(otps_dir, 'w') as file:
        json.dump(otps, file, indent=4)

def get_interval(id):
    global otps_dir
    with open(otps_dir, 'r') as file:
        otps = json.load(file)
    for otp in otps:
        if otp['user_id'] == id:
            return otp['interval']
        

def block_user_from_sending(user_id: str):
    global blocked_dir
    user_id = int(user_id)
    with open(blocked_dir, 'r') as file:
        users = json.load(file)

    if user_id not in users:  # avoid duplicates
        users.append(user_id)

    with open(blocked_dir, 'w') as file:
        json.dump(users, file, indent=4)


def unblock_user_from_sending(user_id: str) -> bool:
    global blocked_dir
    user_id = int(user_id)
    with open(blocked_dir, 'r') as file:
        users: list = json.load(file)

    if user_id in users:
        users.remove(user_id)
        with open(blocked_dir, 'w') as file:
            json.dump(users, file, indent=4)  # ✅ save changes
        return True
    return False

def is_blocked_user(id:str):
    global blocked_dir
    id = int(id)
    with open(blocked_dir, 'r') as file:
        users: list = json.load(file)
    return id in users