from flask import Flask, request, jsonify, render_template, redirect, session
import sqlite3
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "cardiosentinel_secret"

# -------- GLOBAL DATA --------
latest_data = {}

DB_PATH = "database.db"

# -------- DATABASE INIT --------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Users table
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)

    # Sensor data table
    c.execute("""
        CREATE TABLE IF NOT EXISTS sensor_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            heart_rate INTEGER,
            spo2 INTEGER,
            g_force REAL,
            fall_detected INTEGER,
            latitude REAL,
            longitude REAL
        )
    """)

    conn.commit()
    conn.close()

# -------- CREATE DEFAULT USER --------
def create_default_user():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    username = "admin"
    password = generate_password_hash("admin123")

    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        print("✅ Default user created (admin / admin123)")
    except:
        pass

    conn.close()

# -------- LOGIN --------
@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':
        try:
            username = request.form.get('username')
            password = request.form.get('password')

            if not username or not password:
                return "❌ Missing credentials", 400

            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT password FROM users WHERE username=?", (username,))
            result = c.fetchone()
            conn.close()

            if result and check_password_hash(result[0], password):
                session['user'] = username
                return redirect('/')
            else:
                return "❌ Invalid credentials"

        except Exception as e:
            return f"Error: {str(e)}", 500

    return render_template('login.html')
# -------- LOGOUT --------
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')


# -------- DASHBOARD --------
@app.route('/')
def dashboard():
    if 'user' not in session:
        return redirect('/login')
    return render_template('index.html')


# -------- GET LATEST DATA --------
@app.route('/latest')
def latest():
    return latest_data


# -------- RECEIVE SENSOR DATA --------
@app.route('/api/sensor-data', methods=['POST'])
def receive_sensor_data():
    try:
        data = request.get_json()

        global latest_data
        latest_data = data

        heart_rate = data.get("heart_rate")
        spo2 = data.get("spo2")
        g_force = data.get("g_force")
        fall_detected = data.get("fall_detected")
        latitude = data.get("latitude")
        longitude = data.get("longitude")

        print("\n📡 DATA RECEIVED")
        print(data)

        # -------- SAVE TO DATABASE --------
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        c.execute("""
            INSERT INTO sensor_data 
            (timestamp, heart_rate, spo2, g_force, fall_detected, latitude, longitude)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            str(datetime.now()),
            heart_rate,
            spo2,
            g_force,
            int(fall_detected),
            latitude,
            longitude
        ))

        conn.commit()
        conn.close()

        return jsonify({"status": "success"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------- HISTORY --------
@app.route('/history')
def history():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT * FROM sensor_data ORDER BY id DESC LIMIT 50")
    rows = c.fetchall()
    conn.close()

    return jsonify(rows)


# -------- MAIN --------
if __name__ == '__main__':
    init_db()
    create_default_user()

    print("\n🔥 SERVER STARTED")
    app.run(host='0.0.0.0', port=5000)
