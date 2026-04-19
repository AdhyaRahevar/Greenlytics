from flask import Flask, render_template, request, jsonify, redirect, url_for, session, Response, flash
from functools import wraps
import database as db
import scraper
import schedule
import time
import threading
import csv
from io import StringIO
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Initialize database
db.init_db()

# --- BACKGROUND WORKER ---
def update_all_prices():
    """Background job that updates prices for all stored products"""
    print("Running scheduled price updates...")
    products = db.get_all_products()
    for product in products:
        result = scraper.scrape_product(product['url'])
        if result['success'] and result['price']:
            db.add_price(product['id'], result['price'])
            print(f"Updated {product['name']} - New Price: ₹{result['price']}")
            # Check alerts
            interested_users = db.get_interested_users(product['id'], result['price'])
            for user in interested_users:
                msg = f"🌿 ALERT: {product['name']} dropped to ₹{result['price']}! (Target: ₹{user[2]})"
                print(msg)
                db.add_notification(user[0], product['id'], msg)
        time.sleep(2)  # courteous delay between scrapes

def start_scheduler():
    schedule.every().day.at("02:00").do(update_all_prices)
    # schedule.every(20).seconds.do(update_all_prices) # Uncomment for aggressive dev testing
    while True:
        schedule.run_pending()
        time.sleep(1)

scheduler_thread = threading.Thread(target=start_scheduler, daemon=True)
scheduler_thread.start()


# --- AUTHENTICATION DECORATOR ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# --- AUTH ROUTES ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            flash('Username and Password are required', 'danger')
            return redirect(url_for('register'))
        
        success = db.register_user(username, password)
        if success:
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Username already exists.', 'danger')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user_id = db.login_user(username, password)
        if user_id:
            session['user_id'] = user_id
            session['username'] = username
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'danger')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Successfully logged out.', 'info')
    return redirect(url_for('login'))


# --- APP ROUTES ---
@app.route('/')
@login_required
def index():
    user_id = session['user_id']
    products = db.get_user_products(user_id)
    
    total_saved = 0.0
    total_eco = 0
    good_deals = 0
    
    for p in products:
        latest = db.get_latest_price(p['id'])
        avg = db.get_average_price(p['id'])
        
        p['current_price'] = latest['price'] if latest else 0.0
        p['avg_price'] = avg
        p['last_updated'] = latest['date'] if latest else "Never"
        
        total_eco += p['eco_score']
        
        # 🌿 Green Deal Logic
        if p['current_price'] > 0 and avg > 0:
            drop = ((avg - p['current_price']) / avg) * 100
            p['drop_pct'] = round(drop, 1) if drop > 0 else 0
            if p['current_price'] < avg:
                p['deal_status'] = '🟢 Good Deal'
                p['status_class'] = 'good-deal'
                good_deals += 1
            else:
                p['deal_status'] = '🔴 Wait'
                p['status_class'] = 'wait'
        else:
            p['drop_pct'] = 0
            p['deal_status'] = '⚪ Need Data'
            p['status_class'] = 'neutral'
            
    avg_eco = round(total_eco / len(products), 1) if products else 0
    top_deals = sorted([p for p in products if p.get('drop_pct', 0) > 0], key=lambda x: x['drop_pct'], reverse=True)[:3]
    
    return render_template('index.html', 
                           products=products, 
                           total_tracked=len(products),
                           avg_eco=avg_eco,
                           good_deals=good_deals,
                           top_deals=top_deals)

@app.route('/api/preview', methods=['POST'])
@login_required
def api_preview():
    url = request.json.get('url')
    if not url:
        return jsonify({'success': False, 'error': 'No URL provided'})
    result = scraper.scrape_product(url)
    if result['success']:
        result['expected_eco_score'] = len(result.get('tags', '').split(',')) * 10 if result.get('tags') else 0
    return jsonify(result)

@app.route('/add', methods=['POST'])
@login_required
def add_url():
    url = request.form.get('url')
    if not url:
        flash("Invalid URL provided", "danger")
        return redirect(url_for('index'))
        
    result = scraper.scrape_product(url)
    if result['success']:
        eco_score = len(result.get('tags', '').split(',')) * 10 if result.get('tags') else 0
        
        # 1. Add to global products (or ignore if exists)
        product_id = db.add_product(url, result['name'], result.get('image_url', ''), result.get('tags', ''), eco_score, result.get('category', 'Others'))
        
        # 2. Map to user's watchlist
        db.add_user_product(session['user_id'], product_id)
        
        # Mock initial data if completely new
        history = db.get_price_history(product_id)
        if len(history) == 0:
            import datetime, random
            base_price = result['price'] if result['price'] else random.uniform(50, 150)
            for i in range(5, 0, -1):
                date_obj = datetime.datetime.now() - datetime.timedelta(days=i)
                mock_price = abs(round(base_price + random.uniform(-15, 15), 2))
                # Add price manually avoiding real time stamp
                conn = db.get_connection()
                c = conn.cursor()
                c.execute('INSERT INTO prices (product_id, price, date) VALUES (?, ?, ?)', 
                          (product_id, mock_price, date_obj.strftime("%Y-%m-%d %H:%M:%S")))
                conn.commit()
                conn.close()

        if result['price']:
            db.add_price(product_id, result['price'])
            
        flash(f"Successfully added {result['name']} to your Watchlist!", "success")
    else:
        flash(f"Error scraping {url}", "danger")
        
    return redirect(url_for('index'))

@app.route('/remove/<int:product_id>', methods=['POST'])
@login_required
def remove_product(product_id):
    db.remove_user_product(session['user_id'], product_id)
    flash("Product removed from your watchlist.", "info")
    return redirect(url_for('index'))

@app.route('/set_target/<int:product_id>', methods=['POST'])
@login_required
def set_target(product_id):
    try:
        target_price = float(request.form.get('target_price', 0.0))
        db.set_target_price(session['user_id'], product_id, target_price)
        flash("Target price updated!", "success")
    except ValueError:
        flash("Invalid target price", "danger")
    return redirect(url_for('index'))

@app.route('/api/history/<int:product_id>')
@login_required
def api_history(product_id):
    # Verify user owns it
    products = db.get_user_products(session['user_id'])
    if not any(p['id'] == product_id for p in products):
        return jsonify({'error': 'Unauthorized'}), 401
        
    history = db.get_price_history(product_id)
    labels = [h['date'] for h in history]
    data = [h['price'] for h in history]
    
    return jsonify({'labels': labels, 'data': data})

@app.route('/export')
@login_required
def export_csv():
    products = db.get_user_products(session['user_id'])
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['Product Name', 'URL', 'Current Price', 'Average Price', 'Target Price', 'Eco Score', 'Category', 'Tags'])
    
    for p in products:
        latest = db.get_latest_price(p['id'])
        avg = db.get_average_price(p['id'])
        curr_price = latest['price'] if latest else 0.0
        cw.writerow([p['name'], p['url'], curr_price, avg, p['target_price'], p['eco_score'], p.get('category', 'Others'), p['tags']])
        
    output = si.getvalue()
    return Response(output, mimetype='text/csv', headers={"Content-Disposition": f"attachment;filename=watchlist_{session['username']}.csv"})

@app.route('/api/category_analysis')
@login_required
def api_category_analysis():
    stats = db.get_category_stats(session['user_id'])
    return jsonify(stats)

@app.route('/api/notifications')
@login_required
def api_notifications():
    notifications = db.get_unread_notifications(session['user_id'])
    return jsonify(notifications)

@app.route('/api/notifications/read', methods=['POST'])
@login_required
def mark_notifications_read():
    db.mark_notifications_read(session['user_id'])
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False, port=5001)

