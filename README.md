# Anti-Distraction System


<img width="1654" height="829" alt="Screenshot 2026-03-31 215259" src="https://github.com/user-attachments/assets/adb6f648-4212-4b70-9408-7a22f8f452c0" />  ![WhatsApp Image 2026-03-31 at 9 47 36 PM](https://github.com/user-attachments/assets/c2ecc8f6-3d69-4e2a-b7c1-5ed27d041978)








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
