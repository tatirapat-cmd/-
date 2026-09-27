# auth.py (เวอร์ชันใช้ Supabase)
from db import db_get, db_insert, db_update

def load_users():
    return db_get("users")

def save_users(users):
    # บน Supabase เราจะอัปเดตแบบรายแถวผ่านฟังก์ชันเฉพาะแทนการเขียนทับทั้งไฟล์
    pass

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
    
    new_user = {"username": username, "password": password, "role": role, "points": 0}
    db_insert("users", new_user)
    return True, "สมัครสมาชิกสำเร็จ"

def get_user_points(username):
    users = load_users()
    u = next((item for item in users if item['username'] == username), None)
    return int(u.get('points', 0)) if u else 0

def add_user_points(username, points):
    current = get_user_points(username)
    new_points = current + int(points)
    db_update("users", "username", username, {"points": new_points})
    return True

def deduct_user_points(username, points):
    current = get_user_points(username)
    if current >= points:
        new_points = current - int(points)
        db_update("users", "username", username, {"points": new_points})
        return True
    return False

def set_user_points(username, points):
    try:
        p = max(0, int(points))
        db_update("users", "username", username, {"points": p})
        return True, f"อัปเดตแต้มของ '{username}' เป็น {p} แต้มเรียบร้อยแล้ว"
    except Exception:
        return False, "เกิดข้อผิดพลาดในการอัปเดตแต้ม"

def get_all_users():
    return load_users()

def check_permission(user, allowed_roles):
    if not user:
        return False
    return user.get('role') in allowed_roles
