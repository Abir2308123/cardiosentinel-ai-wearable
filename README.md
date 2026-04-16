# cardiosentinel-ai-wearable
Real-time AI-powered cardiac monitoring wearable with edge ML, fall detection, and dual-role web dashboard
# 🫀 CardioSentinel

### AI-Powered Cardiac Monitoring Wearable System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/Flask-2.3+-green.svg)](https://flask.palletsprojects.com/)
[![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-5-red.svg)](https://www.raspberrypi.com/)

**CardioSentinel** is a production-ready edge AI wearable system that continuously monitors cardiac activity in real-time. It features an on-device Machine Learning pipeline (Random Forest) that predicts arrhythmias with sub-10ms latency, secure WebSocket streaming, and dual-role patient/caregiver dashboards.

---

## 📋 Table of Contents
- [Features](#features)
- [System Architecture](#system-architecture)
- [Hardware Requirements](#hardware-requirements)
- [Software Stack](#software-stack)
- [Installation](#installation)
- [Usage](#usage)
- [ML Model Training](#ml-model-training)
- [Security Features](#security-features)
- [Project Structure](#project-structure)
- [Future Roadmap](#future-roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## ✨ Features

### Core Functionality
- **Real-time Cardiac Monitoring** - Continuous heart rate & SpO₂ tracking via MAX30102 sensor
- **Fall Detection** - MPU6050 accelerometer with intelligent threshold detection
- **GPS Tracking** - NEO-6M module for emergency location services
- **Edge AI Inference** - Random Forest classifier (<10ms latency) trained on MIT-BIH Arrhythmia Database
- **Hybrid Detection** - Combines ML predictions with rule-based thresholds for zero false negatives

### Dashboard & Alerts
- **Dual-Role Access** - Separate patient and caregiver portals with role-based views
- **Live WebSocket Streaming** - Real-time vitals with <100ms latency
- **SMS Alerts** - Twilio integration for emergency notifications
- **Alert Escalation** - Unacknowledged alerts escalate to secondary caregivers
- **Historical Trends** - SQLite database with 24-hour vital history

### Security
- **Encrypted WebSockets (WSS)** - All communication encrypted
- **JWT Authentication** - Secure session management
- **SQLite User Database** - Hashed passwords with bcrypt
- **Audit Logging** - Complete access and alert history

---

## 🏗 System Architecture
