/*
 * CardioSentinel Sensor Verification Suite
 * Targets: MAX30102 (Pulse/SpO2), MPU6050 (Motion), NEO-6M (GPS)
 * 
 * --- WIRING GUIDE ---
 * [I2C Bus - MAX30102 & MPU6050]
 * ESP32 GPIO 21 -> SDA
 * ESP32 GPIO 22 -> SCL
 * 
 * [UART Bus - NEO-6M GPS]
 * ESP32 GPIO 16 (RX2) -> GPS TX
 * ESP32 GPIO 17 (TX2) -> GPS RX
 * 
 * [Power]
 * ESP32 3.3V -> VCC (for all sensors)
 * ESP32 GND  -> GND (for all sensors)
 */

#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include "MAX30105.h"
#include <TinyGPS++.h>
#include <HardwareSerial.h>

// --- Sensors & GPS Objects ---
MAX30105 particleSensor;
Adafruit_MPU6050 mpu;
TinyGPSPlus gps;
HardwareSerial gpsSerial(2); // Using UART2 on GPIO 16/17

void setup() {
  Serial.begin(115200);
  while (!Serial) delay(10); // Wait for Serial Monitor

  Serial.println("\n--- CardioSentinel Sensor Test ---");

  // 1. Initialize GPS (UART2)
  gpsSerial.begin(9600, SERIAL_8N1, 16, 17);
  Serial.println("GPS Serial initialized (9600 baud, pins 16/17)");

  // 2. Initialize I2C Bus
  Wire.begin();

  // 3. Scan for I2C Devices
  Serial.println("Scanning I2C bus...");
  byte error, address;
  int nDevices = 0;
  for (address = 1; address < 127; address++) {
    Wire.beginTransmission(address);
    error = Wire.endTransmission();
    if (error == 0) {
      Serial.print("I2C device found at address 0x");
      if (address < 16) Serial.print("0");
      Serial.println(address, HEX);
      nDevices++;
    }
  }
  if (nDevices == 0) Serial.println("No I2C devices found\n");

  // 4. Setup MPU6050
  if (!mpu.begin()) {
    Serial.println("FAILED to find MPU6050 chip!");
  } else {
    Serial.println("MPU6050 Found!");
    mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
    mpu.setGyroRange(MPU6050_RANGE_500_DEG);
    mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);
  }

  // 5. Setup MAX30102
  if (!particleSensor.begin(Wire, I2C_SPEED_FAST)) {
    Serial.println("FAILED to find MAX30102!");
  } else {
    Serial.println("MAX30102 Found!");
    // Configure sensor with default settings
    byte ledBrightness = 60; // Options: 0=Off to 255=50mA
    byte sampleAverage = 4; // Options: 1, 2, 4, 8, 16, 32
    byte ledMode = 2; // Options: 1 = Red only, 2 = Red + IR, 3 = Red + IR + Green
    int sampleRate = 100; // Options: 50, 100, 200, 400, 800, 1000, 1600, 3200
    int pulseWidth = 411; // Options: 69, 118, 215, 411
    int adcRange = 4096; // Options: 2048, 4096, 8192, 16384
    particleSensor.setup(ledBrightness, sampleAverage, ledMode, sampleRate, pulseWidth, adcRange);
  }

  Serial.println("--- Setup Complete ---\n");
}

void loop() {
  Serial.println("--- Reading ---");

  // --- 1. MPU6050 Reading ---
  sensors_event_t a, g, temp;
  mpu.getEvent(&a, &g, &temp);
  Serial.print("Motion: Accel X:"); Serial.print(a.acceleration.x);
  Serial.print(" Y:"); Serial.print(a.acceleration.y);
  Serial.print(" Z:"); Serial.println(a.acceleration.z);

  // --- 2. MAX30102 Reading ---
  long irValue = particleSensor.getIR();
  long redValue = particleSensor.getRed();
  Serial.print("Heart:  IR:"); Serial.print(irValue);
  Serial.print(" RED:"); Serial.print(redValue);
  if (irValue < 50000) {
    Serial.print(" (No finger detected)");
  }
  Serial.println();

  // --- 3. GPS Reading ---
  // We read from GPS serial for 1 second to ensure we catch sentences
  unsigned long start = millis();
  bool gpsData = false;
  while (millis() - start < 1000) {
    while (gpsSerial.available() > 0) {
      if (gps.encode(gpsSerial.read())) {
        gpsData = true;
      }
    }
  }

  if (gpsData && gps.location.isValid()) {
    Serial.print("GPS:    Lat:"); Serial.print(gps.location.lat(), 6);
    Serial.print(" Lon:"); Serial.println(gps.location.lng(), 6);
    Serial.print("        Satellites:"); Serial.println(gps.satellites.value());
  } else {
    Serial.println("GPS:    Waiting for lock (Ensure outdoor view or near window)");
  }

  Serial.println();
  delay(1000); // 1-second interval between logs
}
