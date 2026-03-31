# Cyberpunk Anti-Distraction System

A functional web-based dashboard that monitors user focus via a webcam and provides physical alerts using an ESP32.

## Features
- **Real-time Focus Monitoring**: Monitors head orientation, eye closure, and presence using MediaPipe.
- **Hardware Feedback**: Synchronizes focus status to an ESP32 for physical alerts (buzzer/LCD).
- **Interactive Dashboard**: Modern, themed UI to track distractions in real-time.

## Setup

1. **Virtual Environment**: Initialize a virtual environment and install dependencies.
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. **ESP32 Firmware**: Flash the firmware in `./firmware/anti_distraction_firmware.ino` using the Arduino IDE.
3. **Run the Server**:
   ```bash
   python app.py
   ```
4. **Access Dashboard**: Open `http://localhost:5000` in your browser.

## Technologies Used
- Flask
- Flask-SocketIO
- MediaPipe
- OpenCV
- pyserial
- HTML/CSS/JS
