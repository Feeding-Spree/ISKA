from flask import Flask, render_template, request, redirect, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta
import sqlite3
import os

app = Flask(__name__)

app.secret_key = os.environ.get('ISKA_SECRET_KEY', 'iska-dev-key-change-me')
app.permanent_session_lifetime = timedelta(minutes=15) 

def get_db():
    conn = sqlite3.connect('iska_database.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.before_request
def make_session_permanent():
    session.permanent = True

# ==========================================
# AUTHENTICATION ROUTES
# ==========================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        db.close()
        
        if user and check_password_hash(user['password_hash'], password):
            session.clear() 
            session['user'] = user['username']
            return redirect('/')
        else:
            flash("Invalid username or password.")
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# ==========================================
# DASHBOARD ROUTE
# ==========================================
@app.route('/')
def index():
    if 'user' not in session: return redirect('/login')
    
    db = get_db()
    announcements = db.execute('SELECT * FROM announcements ORDER BY date_posted DESC').fetchall()
    inquiries = db.execute('SELECT * FROM kiosk_info ORDER BY last_updated DESC').fetchall()
    
    raw_logs = db.execute('SELECT * FROM query_logs ORDER BY timestamp ASC').fetchall()
    db.close()
    
    sessions_dict = {}
    for log in raw_logs:
        sid = log['session_id'] if log['session_id'] else f"legacy_{log['id']}" 
        
        if sid not in sessions_dict:
            sessions_dict[sid] = {'session_id': sid, 'timestamp': log['timestamp'], 'interactions': []}
            
        sessions_dict[sid]['interactions'].append(log)

    session_list = list(sessions_dict.values())
    session_list.sort(key=lambda x: x['timestamp'], reverse=True)
    recent_sessions = session_list[:50]
    
    return render_template('dashboard.html', 
                           announcements=announcements, 
                           inquiries=inquiries, 
                           sessions=recent_sessions,
                           user=session['user'])

# ==========================================
# ANNOUNCEMENTS CRUD OPERATIONS
# ==========================================
@app.route('/add_announcement', methods=['POST'])
def add_announcement():
    if 'user' not in session: return redirect('/login')
    db = get_db()
    db.execute('''
        INSERT INTO announcements (title_en, title_tl, content_en, content_tl, posted_by)
        VALUES (?, ?, ?, ?, ?)''', 
        (request.form['t_en'], request.form['t_tl'], request.form['c_en'], request.form['c_tl'], session['user']))
    db.commit()
    db.close()
    return redirect('/')

@app.route('/toggle_status/<int:announcement_id>')
def toggle_status(announcement_id):
    if 'user' not in session: return redirect('/login')
    db = get_db()
    current = db.execute('SELECT is_active FROM announcements WHERE id = ?', (announcement_id,)).fetchone()
    if current:
        new_status = 0 if current['is_active'] else 1
        db.execute('UPDATE announcements SET is_active = ? WHERE id = ?', (new_status, announcement_id))
        db.commit()
    db.close()
    return redirect('/')

@app.route('/edit_announcement/<int:id>', methods=['POST'])
def edit_announcement(id):
    if 'user' not in session: return redirect('/login')
    db = get_db()
    db.execute('''
        UPDATE announcements 
        SET title_en = ?, title_tl = ?, content_en = ?, content_tl = ?
        WHERE id = ?
    ''', (request.form['t_en'], request.form['t_tl'], request.form['c_en'], request.form['c_tl'], id))
    db.commit()
    db.close()
    return redirect('/')

# FIX 2: Delete routes changed from GET to POST so they can't be triggered by
# a browser link prefetch or a student accidentally clicking a shared URL.
# Update your dashboard.html delete buttons to use a small <form method="POST"> instead of <a href>.
@app.route('/delete_announcement/<int:announcement_id>', methods=['POST'])
def delete_announcement(announcement_id):
    if 'user' not in session: return redirect('/login')
    db = get_db()
    db.execute('DELETE FROM announcements WHERE id = ?', (announcement_id,))
    db.commit()
    db.close()
    return redirect('/')

# ==========================================
# INQUIRIES CRUD OPERATIONS
# ==========================================
@app.route('/add_inquiry', methods=['POST'])
def add_inquiry():
    if 'user' not in session: return redirect('/login')
    db = get_db()
    db.execute('''
        INSERT INTO kiosk_info (keyword, response_en, response_tl, category, posted_by)
        VALUES (?, ?, ?, ?, ?)''', 
        (request.form['keyword'].lower(), request.form['r_en'], request.form['r_tl'], request.form['category'], session['user']))
    db.commit()
    db.close()
    return redirect('/')

@app.route('/edit_inquiry/<int:id>', methods=['POST'])
def edit_inquiry(id):
    if 'user' not in session: return redirect('/login')
    db = get_db()
    db.execute('''
        UPDATE kiosk_info 
        SET keyword = ?, category = ?, response_en = ?, response_tl = ?
        WHERE id = ?
    ''', (request.form['keyword'].lower(), request.form['category'], request.form['r_en'], request.form['r_tl'], id))
    db.commit()
    db.close()
    return redirect('/')

@app.route('/delete_inquiry/<int:inquiry_id>', methods=['POST'])
def delete_inquiry(inquiry_id):
    if 'user' not in session: return redirect('/login')
    db = get_db()
    db.execute('DELETE FROM kiosk_info WHERE id = ?', (inquiry_id,))
    db.commit()
    db.close()
    return redirect('/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)