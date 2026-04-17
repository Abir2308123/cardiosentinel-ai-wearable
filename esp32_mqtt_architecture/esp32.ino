#include <WiFi.h>
#include <PubSubClient.h>

// --- Network Setup ---
const char* ssid = "YOUR_WIFI_SSID";           // PLACEHOLDER: Enter your WiFi SSID
const char* password = "YOUR_WIFI_PASSWORD";   // PLACEHOLDER: Enter your WiFi Password
const char* mqtt_server = "192.168.1.100";     // PLACEHOLDER: Enter the Raspberry Pi IP

WiFiClient espClient;
PubSubClient client(espClient);

// --- Timing ---
unsigned long lastMsg = 0;
const int PUBLISH_INTERVAL = 2000; // 2 seconds

void setup() {
  Serial.begin(115200);
  setup_wifi();
  client.setServer(mqtt_server, 1883);
  
  // PLACEHOLDER: Initialize actual sensors here (e.g. MAX30102, MPU6050, NEO-6M)
  // pulseOximeter.begin();
  // mpu.initialize();
}

void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi connected");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    if (client.connect("ESP32_CardioClient")) {
      Serial.println("connected");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  unsigned long now = millis();
  if (now - lastMsg > PUBLISH_INTERVAL) {
    lastMsg = now;

    // PLACEHOLDER: Read real sensors here
    // int hr = pulseOximeter.getHeartRate();
    // int spo2 = pulseOximeter.getSpO2();
    // float motion = mpu.getAccelerationZ();
    
    // Simulating dummy sensor data
    int hr = random(60, 100);
    int spo2 = random(95, 100);
    float motion = random(5, 15) / 10.0;
    float lat = 40.7128;
    float lon = -74.0060;

    // Create JSON formatted string payload
    String payload = "{";
    payload += "\"hr\":" + String(hr) + ",";
    payload += "\"spo2\":" + String(spo2) + ",";
    payload += "\"motion\":" + String(motion) + ",";
    payload += "\"lat\":" + String(lat, 4) + ",";
    payload += "\"lon\":" + String(lon, 4);
    payload += "}";

    // Publish to the MQTT broker on the Raspberry Pi
    Serial.print("Publishing message: ");
    Serial.println(payload);
    client.publish("cardio/data", payload.c_str());
  }
}
