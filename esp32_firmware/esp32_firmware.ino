#include <WiFi.h>
#include <PubSubClient.h>
#include <Wire.h>
#include <TinyGPS++.h>
#include <ArduinoJson.h>

// Sensor Libraries (Example: SparkFun MAX3010x and Adafruit MPU6050)
#include "MAX30105.h" // Works for MAX30102
#include "heartRate.h"
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>

// ==========================================
// CONFIGURATION
// ==========================================
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

const char* mqtt_server = "192.168.1.100"; // Replace with your Pi's IP address
const int mqtt_port = 1883;
const char* mqtt_topic_telemetry = "cardiosentinel/telemetry";

// GPS Configuration
const int GPS_RX_PIN = 17;
const int GPS_TX_PIN = 16;
const int GPS_BAUD = 9600;

// Timing
unsigned long lastMsg = 0;
const long interval = 500; // 500ms Non-blocking interval

// ==========================================
// GLOBAL OBJECTS
// ==========================================
WiFiClient espClient;
PubSubClient client(espClient);
TinyGPSPlus gps;
HardwareSerial GPS_Serial(2);

MAX30105 particleSensor;
Adafruit_MPU6050 mpu;

// Heart rate variables
const byte RATE_SIZE = 4; // Increase this for more averaging.
byte rates[RATE_SIZE]; // Array of heart rates
byte rateSpot = 0;
long lastBeat = 0; // Time at which the last beat occurred
float beatsPerMinute = 0;
int beatAvg = 0;

void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Connecting to WiFi: ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWiFi connected.");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
}

void reconnect() {
  // Loop until we're reconnected
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    // Create a random client ID
    String clientId = "CardioSentinel-ESP-";
    clientId += String(random(0xffff), HEX);
    
    if (client.connect(clientId.c_str())) {
      Serial.println("connected");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  
  // Initialize I2C for MAX30102 and MPU6050 on same bus (SDA=21, SCL=22)
  Wire.begin(21, 22);

  // Initialize Sensors
  Serial.println("Initializing MAX30102...");
  if (!particleSensor.begin(Wire, I2C_SPEED_FAST)) // Use default I2C port, 400kHz speed
  {
    Serial.println("MAX30102 was not found. Please check wiring/power. ");
  } else {
    particleSensor.setup(); // Configure sensor with default settings
    particleSensor.setPulseAmplitudeRed(0x0A); // Turn Red LED to low to indicate sensor is running
    particleSensor.setPulseAmplitudeGreen(0); // Turn off Green LED
  }
  
  Serial.println("Initializing MPU6050...");
  if (!mpu.begin()) {
    Serial.println("Failed to find MPU6050 chip");
  } else {
    mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
    mpu.setGyroRange(MPU6050_RANGE_500_DEG);
    mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);
  }

  // Initialize GPS UART
  GPS_Serial.begin(GPS_BAUD, SERIAL_8N1, GPS_RX_PIN, GPS_TX_PIN);

  // Connectivity
  setup_wifi();
  client.setServer(mqtt_server, mqtt_port);
  client.setBufferSize(512); // Ensure buffer is large enough for JSON
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  // Non-blocking GPS reading
  while (GPS_Serial.available() > 0) {
    gps.encode(GPS_Serial.read());
  }

  // Non-blocking HR calculation continuously
  long irValue = particleSensor.getIR();
  if (checkForBeat(irValue) == true) {
    long delta = millis() - lastBeat;
    lastBeat = millis();

    beatsPerMinute = 60 / (delta / 1000.0);
    if (beatsPerMinute < 255 && beatsPerMinute > 20) {
      rates[rateSpot++] = (byte)beatsPerMinute; // Store this reading in the array
      rateSpot %= RATE_SIZE; // Wrap variable

      // Take average of readings
      beatAvg = 0;
      for (byte x = 0 ; x < RATE_SIZE ; x++)
        beatAvg += rates[x];
      beatAvg /= RATE_SIZE;
    }
  }

  // Publish every 'interval' ms
  unsigned long now = millis();
  if (now - lastMsg > interval) {
    lastMsg = now;

    // 1. Read MPU6050 Accelerometer
    sensors_event_t a, g, temp;
    if(mpu.begin()) { // Check if connected to avoid crash if disconnected
       mpu.getEvent(&a, &g, &temp);
    }

    // Calculate basic motion energy (magnitude of acceleration)
    float motion_energy = sqrt(pow(a.acceleration.x, 2) + pow(a.acceleration.y, 2) + pow(a.acceleration.z, 2));
    
    // Very basic fall detection heuristic (sudden stop after high acceleration)
    int fall_detected = (motion_energy > 15.0 || motion_energy < 2.0) ? 1 : 0; 

    // Build JSON Payload
    StaticJsonDocument<300> doc;
    
    // If finger is not detected, use mock/default values
    if (irValue < 50000) {
      doc["heart_rate"] = 0;
      doc["spo2"] = 0;
      doc["hrv"] = 0;
    } else {
      doc["heart_rate"] = beatAvg;
      doc["spo2"] = random(95, 100); // MAX30102 proper SpO2 requires complex algorithms, using proxy for demo
      doc["hrv"] = random(30, 80); // HRV proxy
    }
    
    doc["motion_energy"] = motion_energy;
    doc["fall_detected"] = fall_detected;

    // GPS Data
    if (gps.location.isValid()) {
      doc["lat"] = gps.location.lat();
      doc["lng"] = gps.location.lng();
    } else {
      doc["lat"] = 0.0;
      doc["lng"] = 0.0;
    }

    // Serialize and Publish
    char jsonBuffer[300];
    serializeJson(doc, jsonBuffer);
    
    client.publish(mqtt_topic_telemetry, jsonBuffer);
    Serial.print("Telemetry published: ");
    Serial.println(jsonBuffer);
  }
}
