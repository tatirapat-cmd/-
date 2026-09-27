# app.py
import json
from flask import Flask, render_template, request, redirect, url_for, session, flash
from auth import (
    login_user, register_user, check_permission, get_user_points, 
    get_all_users, set_user_points
)
from restaurant_mgr import (
    get_all_menu, get_menu_by_id, add_menu_item, update_menu_item, delete_menu_item,
    get_all_tables, add_table_by_app, delete_table, reserve_table, update_table_qr_code,
    auto_reserve_table, cancel_reservation, occupy_reserved_table, mark_table_request_bill,
    move_or_merge_table, add_order, cancel_or_reduce_order, get_all_orders, get_kitchen_orders, 
    update_order_status, calculate_bill, process_checkout, generate_sales_report, get_categories
)

app = Flask(__name__)
app.secret_key = 'kku_restaurant_secret_key_tcas69'

@app.route('/')
def index():
    if session.get('user') and session['user'].get('role') == 'customer':
        return redirect(url_for('tables'))
    menu = get_all_menu()
    return render_template('dashboard.html', menu=menu)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = login_user(request.form['username'], request.form['password'])
        if user:
            session['user'] = user
            flash("เข้าสู่ระบบสำเร็จ!", "success")
            if user.get('role') == 'customer':
                return redirect(url_for('tables'))
            return redirect(url_for('index'))
        flash("Username หรือ Password ไม่ถูกต้อง", "error")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form.get('role', 'customer')
        
        success, msg = register_user(username, password, role)
        if success:
            flash(f"{msg} กรุณาเข้าสู่ระบบ", "success")
            return redirect(url_for('login'))
        else:
            flash(msg, "error")
            
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('my_table_id', None)
    flash("ออกจากระบบเรียบร้อยแล้ว", "success")
    return redirect(url_for('index'))

@app.route('/profile')
def profile():
    if not session.get('user'):
        flash("กรุณาเข้าสู่ระบบก่อนเข้าชมโปรไฟล์", "error")
        return redirect(url_for('login'))

    username = session['user']['username']
    points = get_user_points(username)
    all_tables = get_all_tables()
    all_orders = get_all_orders()

    my_table = next((t for t in all_tables if t.get('current_customer') == username or (t.get('reservation') and t['reservation'].get('customer_name') == username)), None)
    
    if not my_table and session.get('my_table_id'):
        my_table = next((t for t in all_tables if t['table_id'] == session.get('my_table_id')), None)

    my_orders = []
    if my_table:
        my_orders = [o for o in all_orders if o['table_id'] == my_table['table_id'] and o['status'] not in ["ชำระเงินแล้ว", "ปิดบิล"]]

    return render_template(
        'profile.html', 
        user=session['user'], 
        points=points, 
        my_table=my_table, 
        my_orders=my_orders
    )

@app.route('/admin/members')
def admin_members():
    if not session.get('user') or session['user']['role'] not in ['admin', 'staff']:
        flash("เฉพาะ Staff หรือ Admin เท่านั้นที่เข้าถึงหน้านี้ได้", "error")
        return redirect(url_for('index'))
    
    users = get_all_users()
    total_points_issued = 0
    for u in users:
        pts = u.get('points')
        if pts is not None:
            try:
                total_points_issued += int(pts)
            except (ValueError, TypeError):
                pass

    return render_template('admin_members.html', users=users, total_points=total_points_issued)

@app.route('/admin/update_points', methods=['POST'])
def handle_update_points():
    if not session.get('user') or session['user']['role'] != 'admin':
        flash("เฉพาะ Admin เท่านั้นที่ปรับแก้ไขแต้มได้", "error")
        return redirect(url_for('admin_members'))
    
    target_username = request.form.get('username')
    new_points = request.form.get('points')
    
    succ, msg = set_user_points(target_username, new_points)
    flash(msg, "success" if succ else "error")
    return redirect(url_for('admin_members'))

@app.route('/order/table/<int:table_id>')
def direct_table_order(table_id):
    tables = get_all_tables()
    table = next((t for t in tables if t['table_id'] == table_id), None)
    if not table:
        flash("ไม่พบหมายเลขโต๊ะนี้ในระบบ", "error")
        return redirect(url_for('index'))
    
    session['my_table_id'] = table_id
    if session.get('user'):
        table['current_customer'] = session['user']['username']
    flash(f"สแกนเข้าสู่โต๊ะหมายเลข {table_id} เรียบร้อยแล้ว", "success")
    return redirect(url_for('tables'))

@app.route('/update_table_qr/<int:table_id>', methods=['POST'])
def handle_update_table_qr(table_id):
    if not session.get('user') or session['user']['role'] not in ['admin', 'staff']:
        flash("เฉพาะพนักงานหรือผู้ดูแลระบบเท่านั้นที่ตั้งค่า QR Code ได้", "error")
        return redirect(url_for('tables'))
    
    qr_url = request.form.get('qr_code_url', '').strip()
    succ, msg = update_table_qr_code(table_id, qr_url)
    flash(msg, "success" if succ else "error")
    return redirect(url_for('tables'))

@app.route('/customer_reserve', methods=['GET', 'POST'])
def customer_reserve():
    if not session.get('user'):
        flash("กรุณาเข้าสู่ระบบก่อนทำการจองโต๊ะ", "error")
        return redirect(url_for('login'))

    if request.method == 'POST':
        try:
            c_name = request.form['customer_name']
            phone = request.form['phone']
            guests = request.form.get('guests_count', 1)
            r_time = request.form['reserve_time']
            
            succ, msg, t_id = auto_reserve_table(c_name, phone, guests, r_time)
            flash(msg, "success" if succ else "error")
            if succ:
                session['my_table_id'] = t_id
                return redirect(url_for('tables'))
        except (KeyError, ValueError):
            flash("กรุณากรอกข้อมูลการจองให้ถูกต้อง", "error")
            
    return render_template('customer_reserve.html')

@app.route('/add_menu', methods=['GET', 'POST'])
def add_menu():
    if not session.get('user') or session['user']['role'] != 'admin':
        flash("เฉพาะผู้ดูแลระบบ (Admin) เท่านั้นที่สามารถเพิ่มเมนูได้", "error")
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        name = request.form['name']
        category = request.form['category']
        try:
            price = float(request.form['price'])
            image_url = request.form.get('image_url', '').strip()
            
            options_json = request.form.get('options_config_json', '[]')
            try:
                options_config = json.loads(options_json)
            except Exception:
                options_config = []
            
            succ, msg = add_menu_item(session['user'], name, category, price, image_url, options_config)
            flash(msg, "success" if succ else "error")
            if succ:
                return redirect(url_for('index'))
        except ValueError:
            flash("กรุณากรอกราคาให้ถูกต้อง", "error")
            
    return render_template('add_menu.html')

@app.route('/edit_menu/<int:menu_id>', methods=['GET', 'POST'])
def edit_menu(menu_id):
    if not session.get('user') or session['user']['role'] != 'admin':
        flash("เฉพาะผู้ดูแลระบบ (Admin) เท่านั้นที่สามารถแก้ไขเมนูได้", "error")
        return redirect(url_for('index'))
    
    item = get_menu_by_id(menu_id)
    if not item:
        flash("ไม่พบเมนูอาหารที่ต้องการแก้ไข", "error")
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        name = request.form['name']
        category = request.form['category']
        try:
            price = float(request.form['price'])
            image_url = request.form.get('image_url', '').strip()
            is_available = 'is_available' in request.form
            
            options_json = request.form.get('options_config_json', '[]')
            try:
                options_config = json.loads(options_json)
            except Exception:
                options_config = []
            
            succ, msg = update_menu_item(session['user'], menu_id, name, category, price, image_url, is_available, options_config)
            flash(msg, "success" if succ else "error")
            if succ:
                return redirect(url_for('index'))
        except ValueError:
            flash("กรุณากรอกราคาให้ถูกต้อง", "error")
            
    categories = get_categories()
    return render_template('edit_menu.html', item=item, categories=categories)

@app.route('/delete_menu/<int:menu_id>', methods=['POST'])
def handle_delete_menu(menu_id):
    if not session.get('user') or session['user']['role'] != 'admin':
        flash("เฉพาะผู้ดูแลระบบ (Admin) เท่านั้นที่สามารถลบเมนูได้", "error")
        return redirect(url_for('index'))
    
    succ, msg = delete_menu_item(session['user'], menu_id)
    flash(msg, "success" if succ else "error")
    return redirect(url_for('index'))

@app.route('/tables')
def tables():
    if not session.get('user'):
        flash("กรุณาเข้าสู่ระบบก่อน", "error")
        return redirect(url_for('login'))

    user = session['user']
    all_tables = get_all_tables()

    if user.get('role') == 'customer':
        my_table_id = session.get('my_table_id')

        if not my_table_id:
            c_name = user.get('username')
            t_found = next((t for t in all_tables if (t.get('current_customer') == c_name) or (t.get('reservation') and t['reservation'].get('customer_name') == c_name)), None)
            if t_found:
                my_table_id = t_found['table_id']
                session['my_table_id'] = my_table_id

        if not my_table_id:
            flash("คุณยังไม่มีโต๊ะที่จองไว้ กรุณาทำการจองโต๊ะก่อนสั่งอาหาร", "error")
            return redirect(url_for('customer_reserve'))

        customer_tables = [t for t in all_tables if t['table_id'] == my_table_id]

        if customer_tables and customer_tables[0]['status'] == "ว่าง":
            session.pop('my_table_id', None)
            flash("โต๊ะของคุณถูกเช็คบิลเรียบร้อยแล้ว กรุณาทำการจองใหม่หากต้องการใช้บริการเพิ่ม", "success")
            return redirect(url_for('customer_reserve'))

        if not customer_tables:
            session.pop('my_table_id', None)
            flash("ไม่พบข้อมูลโต๊ะของคุณ กรุณาจองโต๊ะใหม่อีกครั้ง", "error")
            return redirect(url_for('customer_reserve'))

        return render_template('tables.html', tables=customer_tables, menu=get_all_menu(), orders=get_all_orders())

    return render_template('tables.html', tables=all_tables, menu=get_all_menu(), orders=get_all_orders())

@app.route('/add_table', methods=['POST'])
def handle_add_table():
    if not session.get('user') or session['user']['role'] not in ['admin', 'staff']:
        flash("เฉพาะพนักงานหรือผู้ดูแลระบบเท่านั้นที่เพิ่มโต๊ะได้", "error")
        return redirect(url_for('tables'))
    
    custom_id = request.form.get('table_id', '').strip()
    username = session['user']['username']
    t_id = int(custom_id) if custom_id else None
    succ, msg = add_table_by_app(t_id, username=username)
    flash(msg, "success" if succ else "error")
    return redirect(url_for('tables'))

@app.route('/delete_table/<int:table_id>', methods=['POST'])
def handle_delete_table(table_id):
    if not session.get('user') or session['user']['role'] != 'admin':
        flash("เฉพาะผู้ดูแลระบบ (Admin) เท่านั้นที่ลบโต๊ะได้", "error")
        return redirect(url_for('tables'))
    
    username = session['user']['username']
    succ, msg = delete_table(table_id, username=username)
    flash(msg, "success" if succ else "error")
    return redirect(url_for('tables'))

@app.route('/move_table', methods=['POST'])
def handle_move_table():
    if not session.get('user') or session['user']['role'] not in ['admin', 'staff']:
        flash("เฉพาะ Staff หรือ Admin เท่านั้นที่ย้าย/รวมโต๊ะได้", "error")
        return redirect(url_for('tables'))

    from_id = request.form.get('from_table_id')
    to_id = request.form.get('to_table_id')
    username = session['user']['username']

    succ, msg = move_or_merge_table(from_id, to_id, username=username)
    flash(msg, "success" if succ else "error")
    return redirect(url_for('tables'))

@app.route('/auto_reserve', methods=['POST'])
def handle_auto_reserve():
    try:
        c_name = request.form['customer_name']
        phone = request.form['phone']
        guests = request.form.get('guests_count', 1)
        r_time = request.form['reserve_time']
        
        succ, msg, t_id = auto_reserve_table(c_name, phone, guests, r_time)
        if succ:
            session['my_table_id'] = t_id
        flash(msg, "success" if succ else "error")
    except (KeyError, ValueError):
        flash("กรุณากรอกข้อมูลการจองให้ถูกต้อง", "error")
    return redirect(url_for('tables'))

@app.route('/cancel_reservation/<int:table_id>', methods=['POST'])
def handle_cancel_reservation(table_id):
    succ, msg = cancel_reservation(table_id)
    if session.get('user', {}).get('role') == 'customer' and session.get('my_table_id') == table_id:
        session.pop('my_table_id', None)
    flash(msg, "success" if succ else "error")
    return redirect(url_for('tables'))

@app.route('/occupy_table/<int:table_id>', methods=['POST'])
def handle_occupy_table(table_id):
    succ, msg = occupy_reserved_table(table_id)
    flash(msg, "success" if succ else "error")
    return redirect(url_for('tables'))

@app.route('/request_bill/<int:table_id>', methods=['POST'])
def handle_request_bill(table_id):
    succ, msg = mark_table_request_bill(table_id)
    flash(msg, "success" if succ else "error")
    return redirect(url_for('tables'))

@app.route('/add_batch_order', methods=['POST'])
def handle_add_batch_order():
    if not session.get('user'):
        return {"success": False, "message": "กรุณาเข้าสู่ระบบก่อนทำรายการ"}, 401
    
    data = request.get_json()
    if not data or 'table_id' not in data or 'items' not in data:
        return {"success": False, "message": "ข้อมูลออเดอร์ไม่ถูกต้อง"}, 400
    
    table_id = int(data['table_id'])
    
    if session.get('user', {}).get('role') == 'customer':
        my_t = session.get('my_table_id')
        if my_t and int(my_t) != table_id:
            return {"success": False, "message": "ไม่สามารถสั่งอาหารเข้าโต๊ะผู้อื่นได้"}, 403

    items = data['items']
    if not items:
        return {"success": False, "message": "ไม่มีรายการอาหารในตะกร้า"}, 400

    success_count = 0
    for item in items:
        m_id = int(item['menu_id'])
        qty = int(item['quantity'])
        options = item.get('options', '')
        unit_price = item.get('price', None)
        succ, _ = add_order(table_id, m_id, qty, options, final_price=unit_price)
        if succ:
            success_count += 1
            
    if success_count > 0:
        flash(f"สั่งอาหารเข้าโต๊ะ {table_id} เรียบร้อยแล้ว ({success_count} รายการ)", "success")
        return {"success": True, "message": "สั่งอาหารสำเร็จ"}
    return {"success": False, "message": "ไม่สามารถสั่งอาหารได้"}, 500

@app.route('/cancel_order/<int:order_id>', methods=['POST'])
def handle_cancel_order():
    if not session.get('user'):
        flash("กรุณาเข้าสู่ระบบก่อนทำรายการ", "error")
        return redirect(url_for('login'))
        
    qty = request.form.get('quantity', 1)
    succ, msg = cancel_or_reduce_order(order_id, qty)
    flash(msg, "success" if succ else "error")
    return redirect(url_for('tables'))

@app.route('/kitchen')
def kitchen():
    if not session.get('user') or session['user']['role'] not in ['admin', 'staff']:
        flash("ไม่มีสิทธิ์เข้าถึงหน้านี้", "error")
        return redirect(url_for('index'))
    return render_template('kitchen.html', orders=get_kitchen_orders())

@app.route('/update_kitchen', methods=['POST'])
def update_kitchen():
    order_id_raw = request.form.get('order_id')
    status = request.form.get('status')
    
    if order_id_raw and status:
        try:
            order_id = int(order_id_raw)
            succ, msg = update_order_status(order_id, status)
            flash(msg, "success" if succ else "error")
        except ValueError:
            flash("หมายเลขออเดอร์ไม่ถูกต้อง", "error")
    else:
        flash("ไม่สามารถอัปเดตสถานะครัวได้", "error")
        
    return redirect(url_for('kitchen'))

@app.route('/checkout/<int:table_id>')
def checkout_view(table_id):
    if not session.get('user') or session['user']['role'] not in ['admin', 'staff']:
        flash("เฉพาะ Staff หรือ Admin เท่านั้นที่สามารถเช็คบิลได้", "error")
        return redirect(url_for('tables'))
    
    bill = calculate_bill(table_id)
    raw_total = bill['raw_total']

    tables = get_all_tables()
    t_info = next((t for t in tables if t['table_id'] == table_id), None)
    customer_username = None
    customer_points = 0
    if t_info:
        customer_username = t_info.get('current_customer')
        if not customer_username and t_info.get('reservation'):
            customer_username = t_info['reservation'].get('customer_name')
            
        if customer_username:
            customer_points = get_user_points(customer_username)

    return render_template(
        'checkout.html', 
        table_id=table_id, 
        bill=bill, 
        raw_total=raw_total, 
        customer_username=customer_username,
        customer_points=customer_points
    )

@app.route('/process_checkout', methods=['POST'])
def handle_process_checkout():
    if not session.get('user') or session['user']['role'] not in ['admin', 'staff']:
        flash("เฉพาะ Staff หรือ Admin เท่านั้นที่ทำรายการได้", "error")
        return redirect(url_for('tables'))
    
    try:
        table_id = int(request.form['table_id'])
        discount_raw = request.form.get('discount', '0').strip()
        discount = float(discount_raw) if discount_raw else 0.0
        
        used_points_raw = request.form.get('used_points', '0').strip()
        used_points = int(used_points_raw) if used_points_raw else 0
        
        customer_username = request.form.get('customer_username', '').strip() or None
    except ValueError:
        discount = 0.0
        used_points = 0
        customer_username = None
    
    succ, msg, _ = process_checkout(
        session['user'], 
        table_id, 
        discount_pct=discount, 
        used_points=used_points, 
        customer_username=customer_username
    )
    flash(msg, "success" if succ else "error")
    return redirect(url_for('tables'))

@app.route('/report')
def report():
    if not session.get('user') or session['user']['role'] != 'admin':
        flash("เฉพาะ Admin เท่านั้นที่เข้าถึงหน้านี้ได้", "error")
        return redirect(url_for('index'))
    return render_template('report.html', report=generate_sales_report())

# app.py (เฉพาะบรรทัดล่างสุด)
if __name__ == '__main__':
    app.run(debug=True, port=5000)
