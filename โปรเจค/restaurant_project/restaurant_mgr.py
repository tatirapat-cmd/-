# restaurant_mgr.py
import json
import os
from datetime import datetime
from auth import add_user_points, deduct_user_points, get_user_points

# --- ฟังก์ชันช่วยอ่าน/เขียนไฟล์ JSON ---
def load_json(filename, default_value):
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading {filename}: {e}")
            return default_value
    return default_value

def save_json(filename, data):
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving {filename}: {e}")

def log_audit(username, action, details):
    logs = load_json("audit_logs.json", [])
    logs.append({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "username": username,
        "action": action,
        "details": details
    })
    save_json("audit_logs.json", logs)

# --- ข้อมูลเริ่มต้น ---
menu_db = load_json("menu.json", [])
tables_db = load_json("tables.json", [
    {"table_id": 1, "status": "ว่าง", "reservation": None, "current_customer": None, "qr_code_url": ""},
    {"table_id": 2, "status": "ว่าง", "reservation": None, "current_customer": None, "qr_code_url": ""},
    {"table_id": 3, "status": "ว่าง", "reservation": None, "current_customer": None, "qr_code_url": ""},
    {"table_id": 4, "status": "ว่าง", "reservation": None, "current_customer": None, "qr_code_url": ""}
])
orders_db = load_json("orders.json", [])

def get_categories():
    return [
        "อาหารเรียกน้ำย่อย / ของทานเล่น (Appetizers / Starters)",
        "อาหารจานหลัก (Main Courses)",
        "อาหารจานเดียว / ข้าวและเส้น (Single Dishes / Rice & Noodles)",
        "อาหารประเภทกับข้าว (Shared Dishes)",
        "ของหวาน (Desserts)",
        "เครื่องดื่ม (Beverages)"
    ]

# --- 🍲 ระบบจัดการเมนู ---
def get_all_menu():
    return load_json("menu.json", menu_db)

def get_menu_by_id(menu_id):
    menus = load_json("menu.json", menu_db)
    return next((m for m in menus if m['id'] == menu_id), None)

def add_menu_item(user, name, category, price, image_url="", options_config=None):
    if not user or user.get('role') != 'admin':
        return False, "สิทธิ์ไม่ถูกต้อง (ต้องเป็น Admin เท่านั้น)"
    
    menus = load_json("menu.json", menu_db)
    new_id = max([m['id'] for m in menus], default=0) + 1
    new_item = {
        "id": new_id,
        "name": name,
        "category": category,
        "price": float(price),
        "image_url": image_url,
        "is_available": True,
        "options_config": options_config if options_config else []
    }
    menus.append(new_item)
    save_json("menu.json", menus)
    log_audit(user['username'], "ADD_MENU", f"เพิ่มเมนู ID:{new_id} {name} ราคา {price}")
    return True, f"เพิ่มเมนู '{name}' เรียบร้อยแล้ว"

def update_menu_item(user, menu_id, name, category, price, image_url, is_available=True, options_config=None):
    if not user or user.get('role') != 'admin':
        return False, "เฉพาะผู้ดูแลระบบ (Admin) เท่านั้นที่สามารถแก้ไขเมนูได้"
    
    menus = load_json("menu.json", menu_db)
    for item in menus:
        if item['id'] == menu_id:
            item['name'] = name
            item['category'] = category
            item['price'] = float(price)
            item['image_url'] = image_url
            item['is_available'] = is_available
            item['options_config'] = options_config if options_config is not None else item.get('options_config', [])
            save_json("menu.json", menus)
            log_audit(user['username'], "EDIT_MENU", f"แก้ไขเมนู ID:{menu_id} {name}")
            return True, f"แก้ไขข้อมูลเมนู '{name}' เรียบร้อยแล้ว"
    
    return False, "ไม่พบเมนูที่ต้องการแก้ไข"

def delete_menu_item(user, menu_id):
    if not user or user.get('role') != 'admin':
        return False, "เฉพาะผู้ดูแลระบบ (Admin) เท่านั้นที่สามารถลบเมนูได้"
    
    menus = load_json("menu.json", menu_db)
    initial_len = len(menus)
    updated_menus = [m for m in menus if m['id'] != menu_id]
    
    if len(updated_menus) < initial_len:
        save_json("menu.json", updated_menus)
        log_audit(user['username'], "DELETE_MENU", f"ลบเมนู ID:{menu_id}")
        return True, "ลบเมนูอาหารเรียบร้อยแล้ว"
    return False, "ไม่พบเมนูที่ต้องการลบ"

# --- 🪑 ระบบจัดการโต๊ะ & จองโต๊ะ ---
def get_all_tables():
    return load_json("tables.json", tables_db)

def add_table_by_app(table_id=None, username="System"):
    tables = load_json("tables.json", tables_db)
    if table_id is None or table_id == "":
        table_id = max([t['table_id'] for t in tables], default=0) + 1
    else:
        try:
            table_id = int(table_id)
        except ValueError:
            return False, "กรุณากรอกหมายเลขโต๊ะเป็นตัวเลข"

    if any(t['table_id'] == table_id for t in tables):
        return False, f"มีโต๊ะหมายเลข {table_id} ในระบบอยู่แล้ว"

    tables.append({"table_id": table_id, "status": "ว่าง", "reservation": None, "current_customer": None, "qr_code_url": ""})
    save_json("tables.json", tables)
    log_audit(username, "ADD_TABLE", f"เพิ่มโต๊ะหมายเลข {table_id}")
    return True, f"เพิ่มโต๊ะหมายเลข {table_id} เรียบร้อยแล้ว"

def delete_table(table_id, username="System"):
    tables = load_json("tables.json", tables_db)
    table = next((t for t in tables if t['table_id'] == table_id), None)
    if not table:
        return False, "ไม่พบโต๊ะดังกล่าว"
    if table['status'] != "ว่าง":
        return False, "ไม่สามารถลบโต๊ะที่มีลูกค้า ติดจอง หรือรอเช็คบิลอยู่ได้"

    tables = [t for t in tables if t['table_id'] != table_id]
    save_json("tables.json", tables)
    log_audit(username, "DELETE_TABLE", f"ลบโต๊ะหมายเลข {table_id}")
    return True, f"ลบโต๊ะหมายเลข {table_id} เรียบร้อยแล้ว"

def update_table_qr_code(table_id, qr_code_url):
    tables = load_json("tables.json", tables_db)
    table = next((t for t in tables if t['table_id'] == table_id), None)
    if not table:
        return False, "ไม่พบโต๊ะดังกล่าว"
    table['qr_code_url'] = qr_code_url.strip()
    save_json("tables.json", tables)
    return True, f"บันทึก URL รูป QR Code ของโต๊ะ {table_id} เรียบร้อยแล้ว"

def reserve_table(table_id, customer_name, phone, reserve_time):
    tables = load_json("tables.json", tables_db)
    table = next((t for t in tables if t['table_id'] == table_id), None)
    if not table:
        return False, "ไม่พบโต๊ะ"
    if table['status'] != "ว่าง":
        return False, "โต๊ะนี้ไม่ว่างสำหรับจอง"

    table['status'] = "จองแล้ว"
    table['current_customer'] = customer_name
    table['reservation'] = {
        "customer_name": customer_name,
        "phone": phone,
        "reserve_time": reserve_time
    }
    save_json("tables.json", tables)
    log_audit(customer_name, "RESERVE_TABLE", f"จองโต๊ะ {table_id} เวลา {reserve_time}")
    return True, f"จองโต๊ะ {table_id} สำเร็จ (คุณ {customer_name})"

def auto_reserve_table(customer_name, phone, guests_count, reserve_time):
    tables = load_json("tables.json", tables_db)
    available_table = next((t for t in tables if t['status'] == "ว่าง"), None)
    if not available_table:
        return False, "ขออภัย ขณะนี้ไม่มีโต๊ะว่างสำหรับการจอง", None

    try:
        guests_count = int(guests_count)
    except (ValueError, TypeError):
        guests_count = 1

    available_table['status'] = "จองแล้ว"
    available_table['current_customer'] = customer_name
    available_table['reservation'] = {
        "customer_name": customer_name,
        "phone": phone,
        "guests_count": guests_count,
        "reserve_time": reserve_time
    }
    save_json("tables.json", tables)
    log_audit(customer_name, "AUTO_RESERVE_TABLE", f"จัดโต๊ะ {available_table['table_id']} สำหรับ {guests_count} ท่าน เวลา {reserve_time}")
    
    return True, f"จองสำเร็จ! ระบบจัดโต๊ะหมายเลข {available_table['table_id']} ให้คุณ {customer_name} ({guests_count} ท่าน เวลา {reserve_time})", available_table['table_id']

def cancel_reservation(table_id):
    tables = load_json("tables.json", tables_db)
    table = next((t for t in tables if t['table_id'] == table_id), None)
    if not table:
        return False, "ไม่พบโต๊ะ"
    if table['status'] != "จองแล้ว":
        return False, "โต๊ะนี้ไม่ได้อยู่ในสถานะจอง"

    table['status'] = "ว่าง"
    table['reservation'] = None
    table['current_customer'] = None
    save_json("tables.json", tables)
    return True, f"ยกเลิกการจองโต๊ะ {table_id} เรียบร้อยแล้ว"

def occupy_reserved_table(table_id):
    tables = load_json("tables.json", tables_db)
    table = next((t for t in tables if t['table_id'] == table_id), None)
    if not table:
        return False, "ไม่พบโต๊ะ"
    table['status'] = "มีลูกค้า"
    if table.get('reservation'):
        table['current_customer'] = table['reservation'].get('customer_name')
    table['reservation'] = None
    save_json("tables.json", tables)
    return True, f"เปิดโต๊ะ {table_id} สำหรับลูกค้าเรียบร้อยแล้ว"

def mark_table_request_bill(table_id):
    tables = load_json("tables.json", tables_db)
    table = next((t for t in tables if t['table_id'] == table_id), None)
    if not table:
        return False, "ไม่พบโต๊ะ"
    if table['status'] != "มีลูกค้า":
        return False, "โต๊ะต้องอยู่ในสถานะ 'มีลูกค้า' จึงจะเปลี่ยนเป็นรอเช็คบิลได้"
    
    table['status'] = "รอเช็คบิล"
    save_json("tables.json", tables)
    return True, f"เปลี่ยนสถานะโต๊ะ {table_id} เป็น 'รอเช็คบิล' แล้ว"

def move_or_merge_table(from_table_id, to_table_id, username="System"):
    try:
        from_table_id = int(from_table_id)
        to_table_id = int(to_table_id)
    except (ValueError, TypeError):
        return False, "หมายเลขโต๊ะไม่ถูกต้อง"

    if from_table_id == to_table_id:
        return False, "ไม่สามารถย้ายไปยังโต๊ะเดียวกันได้"

    tables = load_json("tables.json", tables_db)
    orders = load_json("orders.json", orders_db)

    from_table = next((t for t in tables if t['table_id'] == from_table_id), None)
    to_table = next((t for t in tables if t['table_id'] == to_table_id), None)

    if not from_table or not to_table:
        return False, "ไม่พบข้อมูลโต๊ะต้นทางหรือปลายทาง"

    active_orders = [o for o in orders if o['table_id'] == from_table_id and o['status'] not in ["ปิดบิล", "ชำระเงินแล้ว"]]
    if not active_orders:
        return False, f"โต๊ะ {from_table_id} ไม่มีรายการอาหารที่สั่งอยู่"

    for o in active_orders:
        o['table_id'] = to_table_id

    if from_table.get('current_customer') and not to_table.get('current_customer'):
        to_table['current_customer'] = from_table['current_customer']

    from_table['status'] = "ว่าง"
    from_table['reservation'] = None
    from_table['current_customer'] = None

    if to_table['status'] == "ว่าง":
        to_table['status'] = "มีลูกค้า"

    save_json("orders.json", orders)
    save_json("tables.json", tables)
    log_audit(username, "MOVE_TABLE", f"ย้าย/รวมรายการอาหารจากโต๊ะ {from_table_id} ไปยังโต๊ะ {to_table_id}")

    return True, f"ย้าย/รวมรายการอาหารจากโต๊ะ {from_table_id} ไปโต๊ะ {to_table_id} เรียบร้อยแล้ว"

# --- 🛒 ระบบออเดอร์ ---
def add_order(table_id, menu_id, quantity, options="", final_price=None):
    try:
        quantity = int(quantity)
        if quantity <= 0:
            return False, "จำนวนต้องมากกว่า 0"
    except ValueError:
        return False, "กรุณากรอกจำนวนให้ถูกต้อง"

    menus = load_json("menu.json", menu_db)
    menu_item = next((m for m in menus if m['id'] == menu_id and m['is_available']), None)
    if not menu_item:
        return False, "เมนูนี้ไม่พร้อมให้บริการ"

    orders = load_json("orders.json", orders_db)
    next_order_id = max([o['order_id'] for o in orders], default=0) + 1

    unit_price = float(final_price) if final_price is not None else float(menu_item['price'])

    order = {
        "order_id": next_order_id,
        "table_id": table_id,
        "menu_id": menu_id,
        "menu_name": menu_item['name'],
        "price": unit_price,
        "quantity": quantity,
        "options": options.strip(),
        "status": "รอดำเนินการ",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    orders.append(order)
    save_json("orders.json", orders)

    tables = load_json("tables.json", tables_db)
    for t in tables:
        if t['table_id'] == table_id and t['status'] == "ว่าง":
            t['status'] = "มีลูกค้า"
    save_json("tables.json", tables)

    return True, f"สั่งอาหาร '{menu_item['name']}' จำนวน {quantity} เรียบร้อย"

def cancel_or_reduce_order(order_id, quantity_to_remove=1):
    orders = load_json("orders.json", orders_db)
    for o in orders:
        if o['order_id'] == order_id:
            if o['status'] in ["ปิดบิล", "ชำระเงินแล้ว"]:
                return False, "ไม่สามารถยกเลิกรายการที่ปิดบิลแล้วได้"
            
            try:
                quantity_to_remove = int(quantity_to_remove)
            except ValueError:
                quantity_to_remove = 1

            if o['quantity'] > quantity_to_remove:
                o['quantity'] -= quantity_to_remove
                save_json("orders.json", orders)
                return True, f"ลดจำนวนรายการ {o['menu_name']} เหลือ {o['quantity']} รายการ"
            else:
                updated_orders = [item for item in orders if item['order_id'] != order_id]
                save_json("orders.json", updated_orders)
                return True, f"ยกเลิกรายการ {o['menu_name']} เรียบร้อยแล้ว"
                
    return False, "ไม่พบรายการออเดอร์"

def get_all_orders():
    return load_json("orders.json", orders_db)

def get_kitchen_orders():
    orders = load_json("orders.json", orders_db)
    return [o for o in orders if o['status'] in ["รอดำเนินการ", "กำลังเตรียม"]]

def update_order_status(order_id, new_status):
    orders = load_json("orders.json", orders_db)
    for o in orders:
        if o['order_id'] == order_id:
            o['status'] = new_status
            save_json("orders.json", orders)
            return True, f"อัปเดตสถานะออเดอร์ #{order_id} เป็น '{new_status}' แล้ว"
    return False, "ไม่พบออเดอร์"

# --- 💳 การเช็คบิลและสะสมแต้มสมาชิก ---
def calculate_bill(table_id):
    orders = load_json("orders.json", orders_db)
    table_orders = [o for o in orders if o['table_id'] == table_id and o['status'] not in ["ชำระเงินแล้ว", "ปิดบิล"]]
    if not table_orders:
        return {"items": [], "bill_items": [], "raw_total": 0.0}
    
    raw_total = sum(o['price'] * o['quantity'] for o in table_orders)
    return {
        "items": table_orders,
        "bill_items": table_orders,
        "raw_total": raw_total
    }

def process_checkout(user, table_id, discount_pct=0.0, used_points=0, customer_username=None):
    if not user or user.get('role') not in ['admin', 'staff']:
        return False, "ไม่มีสิทธิ์ทำรายการ", 0.0

    bill = calculate_bill(table_id)
    if not bill['bill_items']:
        return False, "ไม่พบรายการอาหารที่ต้องชำระในโต๊ะนี้", 0.0

    raw_total = bill['raw_total']
    service_charge = raw_total * 0.10
    subtotal = raw_total + service_charge
    
    # 1. หัก ส่วนลดเปอร์เซ็นต์
    discount_amount = subtotal * (discount_pct / 100.0)
    amount_after_pct_discount = subtotal - discount_amount

    # 2. หัก แต้มแลกส่วนลด (1 แต้ม = 1 บาท)
    try:
        used_points = int(used_points)
    except (ValueError, TypeError):
        used_points = 0

    if customer_username and used_points > 0:
        cur_points = get_user_points(customer_username)
        if used_points > cur_points:
            used_points = cur_points
        deduct_user_points(customer_username, used_points)
    else:
        used_points = 0

    # ยอดชำระสุทธิ (ไม่มี VAT)
    net_total = max(0.0, amount_after_pct_discount - used_points)

    # 3. คำนวณแต้มสะสมใหม่ที่จะได้รับ (10 บาท = 1 แต้ม)
    earned_points = int(net_total // 10)
    if customer_username and earned_points > 0:
        add_user_points(customer_username, earned_points)

    # อัปเดตสถานะออเดอร์เป็น ปิดบิล
    orders = load_json("orders.json", orders_db)
    for o in orders:
        if o['table_id'] == table_id and o['status'] not in ["ชำระเงินแล้ว", "ปิดบิล"]:
            o['status'] = "ปิดบิล"
    save_json("orders.json", orders)

    # เคลียร์สถานะโต๊ะกลับเป็น ว่าง
    tables = load_json("tables.json", tables_db)
    for t in tables:
        if t['table_id'] == table_id:
            t['status'] = "ว่าง"
            t['reservation'] = None
            t['current_customer'] = None
    save_json("tables.json", tables)

    log_msg = f"เช็คบิลโต๊ะ {table_id} ยอดรวม {net_total:.2f} บาท"
    if customer_username:
        log_msg += f" (ลูกค้า: {customer_username}, แลดแต้ม: {used_points}, ได้รับแต้ม: +{earned_points})"
    log_audit(user['username'], "CHECKOUT", log_msg)

    return True, f"เช็คบิลโต๊ะ {table_id} เรียบร้อย ยอดสุทธิ: {net_total:.2f} บาท (ได้รับแต้มสะสม +{earned_points} แต้ม)", net_total

def generate_sales_report():
    orders = load_json("orders.json", orders_db)
    completed_sales = [o for o in orders if o.get('status') in ["ปิดบิล", "ชำระเงินแล้ว"]]
    menus = load_json("menu.json", menu_db)
    
    raw_revenue = 0.0
    item_counts = {}
    category_revenue = {}

    for item in completed_sales:
        try:
            price = float(item.get('price', 0))
            qty = int(item.get('quantity', 0))
        except (ValueError, TypeError):
            price = 0.0
            qty = 0

        item_raw = price * qty
        item_net = item_raw * 1.10  # รวม Service Charge 10% (ไม่มี VAT)
        raw_revenue += item_raw
        
        name = item.get('menu_name', 'ไม่ระบุเมนู')
        item_counts[name] = item_counts.get(name, 0) + qty

        m_id = str(item.get('menu_id', ''))
        menu_info = next((m for m in menus if str(m.get('id', '')) == m_id), None)
        
        category = menu_info.get('category', 'อื่นๆ') if menu_info else "อื่นๆ"
        category_revenue[category] = category_revenue.get(category, 0.0) + item_net

    total_service_charge = raw_revenue * 0.10
    total_revenue = raw_revenue + total_service_charge

    sorted_bestsellers = sorted(item_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "raw_revenue": raw_revenue,
        "total_service_charge": total_service_charge,
        "total_revenue": total_revenue,
        "total_orders": len(completed_sales),
        "best_sellers": sorted_bestsellers,
        "category_revenue": category_revenue
    }