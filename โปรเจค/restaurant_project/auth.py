# auth.py
import json
import os

USERS_FILE = "users.json"

def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                users = json.load(f)
                # 🛡️ เติมค่าเริ่มต้น points ให้ผู้ใช้งานเดิมที่ไม่มี Key นี้
                for u in users:
                    if 'points' not in u or u['points'] is None:
                        u['points'] = 0
                return users
        except Exception:
            return []
    return [
        {"username": "admin", "password": "123", "role": "admin", "points": 0},
        {"username": "staff", "password": "123", "role": "staff", "points": 0},
        {"username": "customer", "password": "123", "role": "customer", "points": 100}
    ]

def save_users(users):
    try:
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving users: {e}")

def login_user(username, password):
    users = load_users()
    for u in users:
        if u['username'] == username and u['password'] == password:
            return u
    return None

def register_user(username, password, role="customer"):
    users = load_users()
    if any(u['username'] == username for u in users):
        return False, "Username นี้ถูกใช้งานแล้ว"
    users.append({
        "username": username, 
        "password": password, 
        "role": role, 
        "points": 0
    })
    save_users(users)
    return True, "สมัครสมาชิกสำเร็จ"

def check_permission(user, allowed_roles):
    if not user:
        return False
    return user.get('role') in allowed_roles

def get_all_users():
    return load_users()

def get_user_points(username):
    users = load_users()
    u = next((item for item in users if item['username'] == username), None)
    if u and u.get('points') is not None:
        try:
            return int(u['points'])
        except (ValueError, TypeError):
            return 0
    return 0

def add_user_points(username, points):
    users = load_users()
    for u in users:
        if u['username'] == username:
            u['points'] = int(u.get('points', 0) or 0) + int(points)
            save_users(users)
            return True
    return False

def deduct_user_points(username, points):
    users = load_users()
    for u in users:
        if u['username'] == username:
            current = int(u.get('points', 0) or 0)
            if current >= points:
                u['points'] = current - int(points)
                save_users(users)
                return True
    return False

def set_user_points(username, points):
    users = load_users()
    for u in users:
        if u['username'] == username:
            try:
                u['points'] = max(0, int(points))
                save_users(users)
                return True, f"อัปเดตแต้มของ '{username}' เป็น {points} แต้มเรียบร้อยแล้ว"
            except ValueError:
                return False, "จำนวนแต้มต้องเป็นตัวเลข"
    return False, "ไม่พบผู้ใช้งานนี้"