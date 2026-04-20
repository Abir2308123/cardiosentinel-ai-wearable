from flask import Flask, request, jsonify, render_template, redirect, session
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import joblib

app = Flask(__name__)
app.secret_key = "cardiosentinel_secret"

# -------- GLOBAL DATA --------
latest_data = {}
DB_PATH = "database.db"

# -------- LOAD ML MODEL --------
MODEL_PATH = "trained_model.pkl"
model = None

try:
    model = joblib.load(MODEL_PATH)
    print("✅ ML model loaded successfully")
    print(f"📊 Model expects {model.n_features_in_} features")
except Exception as e:
    print("⚠️ Model not loaded:", e)

# -------- DATABASE INIT --------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS sensor_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            heart_rate INTEGER,
            spo2 INTEGER,
            g_force REAL,
            fall_detected INTEGER,
            latitude REAL,
            longitude REAL,
            prediction INTEGER
        )
    """)

    conn.commit()
    conn.close()

# -------- CREATE DEFAULT USER --------
def create_default_user():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (
            "admin",
            generate_password_hash("admin123")
        ))
        conn.commit()
        print("✅ Default user: admin / admin123")
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
            role = request.form.get('role')

            if not username or not password:
                return render_template('login.html', error="Missing credentials")

            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT password FROM users WHERE username=?", (username,))
            result = c.fetchone()
            conn.close()

            if result and check_password_hash(result[0], password):
                session['user'] = username

                if role == "patient":
                    return redirect('/patient')
                else:
                    return redirect('/caretaker')

            else:
                return render_template('login.html', error="Invalid username or password")

        except Exception as e:
            return f"Error: {str(e)}", 500

    return render_template('login.html')

# -------- LOGOUT --------
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')

# -------- ROOT --------
@app.route('/')
def root():
    if 'user' not in session:
        return redirect('/login')
    return redirect('/patient')

# -------- PATIENT --------
@app.route('/patient')
def patient():
    if 'user' not in session:
        return redirect('/login')
    return render_template('patient.html')

# -------- CARETAKER --------
@app.route('/caretaker')
def caretaker():
    if 'user' not in session:
        return redirect('/login')
    return render_template('caretaker.html')

# -------- LIVE DATA --------
@app.route('/latest')
def latest():
    return latest_data

# -------- RECEIVE SENSOR DATA --------
@app.route('/api/sensor-data', methods=['POST'])
def receive_sensor_data():
    try:
        data = request.get_json()

        heart_rate = data.get("heart_rate", 0)
        spo2 = data.get("spo2", 0)
        g_force = data.get("g_force", 0)
        fall_detected = data.get("fall_detected", False)
        latitude = data.get("latitude", 0)
        longitude = data.get("longitude", 0)

        print("\n📡 DATA RECEIVED")
        print(data)

        # -------- ML PREDICTION --------
        prediction = None

        try:
            if model and heart_rate > 0 and spo2 > 0:

                # 🔥 Estimate HRV (approximation)
                hrv = max(20, min(100, 60000 / max(heart_rate, 1)))

                # 🔥 Use G-force as motion energy
                motion_energy = g_force

                features = [[
                    heart_rate,
                    spo2,
                    hrv,
                    motion_energy
                ]]

                prediction = int(model.predict(features)[0])

                print(f"🧠 Prediction: {prediction}")
                print(f"📊 Features → HR:{heart_rate}, SpO2:{spo2}, HRV:{hrv:.1f}, Motion:{motion_energy}")

        except Exception as e:
            print("ML Error:", e)

        # -------- STORE LATEST --------
        global latest_data
        latest_data = {
            **data,
            "prediction": prediction
        }

        # -------- SAVE TO DATABASE --------
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        c.execute("""
            INSERT INTO sensor_data 
            (timestamp, heart_rate, spo2, g_force, fall_detected, latitude, longitude, prediction)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(datetime.now()),
            heart_rate,
            spo2,
            g_force,
            int(fall_detected),
            latitude,
            longitude,
            prediction
        ))

        conn.commit()
        conn.close()

        return jsonify({
            "status": "success",
            "prediction": prediction
        }), 200

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
