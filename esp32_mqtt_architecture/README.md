# CardioSentinel - Simplified MQTT Architecture

Setup instructions to run the localized ESP32 + MQTT + ML pipeline.

## 1. Install Mosquitto (MQTT Broker)
On your Raspberry Pi or Windows machine, install the Mosquitto MQTT broker so the ESP32 has a server to push data to.
**Linux/Raspberry Pi:** `sudo apt-get install mosquitto mosquitto-clients`
*(Ensure the service is running: `sudo systemctl start mosquitto`)*

## 2. Install Python Packages
Install the required libraries bridging Flask, WebSockets, MQTT, and the ML pipeline.
```bash
pip install paho-mqtt flask flask-socketio joblib numpy scikit-learn
```

## 3. Flash the ESP32
Open `esp32.ino` in the Arduino IDE. 
- Install the **PubSubClient** library from the Library Manager.
- Modify the `ssid`, `password`, and `mqtt_server` variables at the top of the file to match your network and the Raspberry Pi's IP address.
- Upload/Compile to your ESP32.

## 4. Run the Python Script
Ensure your compiled Machine Learning model (`trained_model.pkl`) is either copied into this folder or exists one directory up (as referenced in the code `../trained_model.pkl`).
Start the server:
```bash
python pi_server.py
```

## 5. Open Web Dashboard
Find out your Raspberry Pi's local network IP address (e.g. 192.168.1.100).
On any device on the same WiFi network, open a web browser and go to:
```text
http://<your-pi-ip>:5000
```
*(If testing on the same PC running the python script, navigate to `http://127.0.0.1:5000`)*
