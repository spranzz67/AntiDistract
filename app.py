from flask import Flask, render_template, request, Response, jsonify
from flask_socketio import SocketIO
import cv2
import numpy as np
import time
import serial
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import threading

app = Flask(__name__)
# Enable CORS for SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")

# --- CONFIGURATION ---
SERIAL_PORT = 'COM4'
BAUD_RATE = 115200
FACE_MODEL_PATH = 'face_landmarker.task'
POSE_MODEL_PATH = 'pose_landmarker.task'

EYE_AR_THRESH = 0.22
AWAY_TIMEOUT = 20.0

# --- GLOBAL STATE ---
sys_state = {
    'is_active': False,
    'deviations': 0,
    'session_start_time': None,
    'current_status': 'I',
    'last_seen_time': time.time(),
    'd_frames': 0,
    'e_frames': 0
}

CONSEC_FRAMES = 10 # Require 10 consecutive frames (~1/3 second) before alerting

# --- INITIALIZATION ---
try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    print(f"Connected to ESP32 on {SERIAL_PORT}", flush=True)
except Exception as e:
    print(f"FAILED to connect to ESP32: {e}", flush=True)
    ser = None

# MediaPipe Initialization
base_options_face = python.BaseOptions(model_asset_path=FACE_MODEL_PATH)
options_face = vision.FaceLandmarkerOptions(base_options=base_options_face, output_face_blendshapes=True, num_faces=1)
face_detector = vision.FaceLandmarker.create_from_options(options_face)

base_options_pose = python.BaseOptions(model_asset_path=POSE_MODEL_PATH)
options_pose = vision.PoseLandmarkerOptions(base_options=base_options_pose, running_mode=vision.RunningMode.IMAGE)
pose_detector = vision.PoseLandmarker.create_from_options(options_pose)

LEFT_EYE = [362, 385, 387, 263, 373, 380]
RIGHT_EYE = [33, 160, 158, 133, 153, 144]

def send_to_esp32(status):
    if status != sys_state['current_status']:
        print(f"Sending ESP32: {status}", flush=True)
        if ser and ser.is_open:
            try:
                ser.write(status.encode())
            except Exception as e:
                print(f"Serial write error: {e}", flush=True)
        sys_state['current_status'] = status

def get_aspect_ratio(eye_landmarks_indices, landmarks):
    v1 = np.linalg.norm(np.array(landmarks[eye_landmarks_indices[1]]) - np.array(landmarks[eye_landmarks_indices[5]]))
    v2 = np.linalg.norm(np.array(landmarks[eye_landmarks_indices[2]]) - np.array(landmarks[eye_landmarks_indices[4]]))
    h = np.linalg.norm(np.array(landmarks[eye_landmarks_indices[0]]) - np.array(landmarks[eye_landmarks_indices[3]]))
    return (v1 + v2) / (2.0 * h) if h != 0 else 0.0

def format_time(seconds):
    if seconds < 0: seconds = 0
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"

# --- BACKGROUND METRICS THREAD ---
def update_metrics_thread():
    while True:
        if sys_state['is_active'] and sys_state['session_start_time']:
            elapsed = time.time() - sys_state['session_start_time']
            timer_str = format_time(elapsed)
            
            socketio.emit('update_metrics', {
                'status': sys_state['current_status'],
                'deviations': sys_state['deviations'],
                'timer': timer_str
            })
        time.sleep(1)

# Start background thread
metrics_thread = threading.Thread(target=update_metrics_thread, daemon=True)
metrics_thread.start()

# --- CV STREAM GENERATOR ---
def generate_frames():
    cap = cv2.VideoCapture(0)
    sys_state['last_seen_time'] = time.time()
    
    last_eval_status = 'I'
    
    while True:
        if not sys_state['is_active']:
            # Turn off camera if inactive to save resources
            cap.release()
            send_to_esp32('I') # Reset ESP32
            break
            
        success, frame = cap.read()
        if not success:
            break

        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        
        face_result = face_detector.detect(mp_image)
        pose_result = pose_detector.detect(mp_image)

        h, w, _ = frame.shape
        status = 'I'
        now = time.time()

        face_detected = len(face_result.face_landmarks) > 0
        pose_detected = len(pose_result.pose_landmarks) > 0
        away_triggered = False

        if face_detected:
            sys_state['last_seen_time'] = now
            raw_status = 'F'
            
            face_landmarks = face_result.face_landmarks[0]
            pixel_landmarks = [[lm.x * w, lm.y * h, lm.z * w] for lm in face_landmarks]

            left_ear = get_aspect_ratio(LEFT_EYE, pixel_landmarks)
            right_ear = get_aspect_ratio(RIGHT_EYE, pixel_landmarks)
            avg_ear = (left_ear + right_ear) / 2.0

            if avg_ear < EYE_AR_THRESH:
                raw_status = 'E'
            else:
                nose_tip = pixel_landmarks[1]
                left_eye_outer = pixel_landmarks[33]
                right_eye_outer = pixel_landmarks[263]
                
                dist_left = np.linalg.norm(np.array(nose_tip) - np.array(left_eye_outer))
                dist_right = np.linalg.norm(np.array(nose_tip) - np.array(right_eye_outer))
                yaw_ratio = dist_left / dist_right if dist_right != 0 else 1.0
                
                eye_center_y = (left_eye_outer[1] + right_eye_outer[1]) / 2.0
                nose_y = nose_tip[1]

                if yaw_ratio > 1.8 or yaw_ratio < 0.55 or nose_y < eye_center_y - 10 or nose_y > eye_center_y + 40:
                    raw_status = 'D'
                    
            if pose_detected:
                pose_nose = pose_result.pose_landmarks[0][0]
                if pose_nose.y < 0.15:
                    raw_status = 'A'

            # Smoothing logic
            if raw_status == 'E':
                sys_state['e_frames'] += 1
                sys_state['d_frames'] = 0
            elif raw_status == 'D':
                sys_state['d_frames'] += 1
                sys_state['e_frames'] = 0
            elif raw_status == 'A':
                status = 'A'
            else:
                sys_state['d_frames'] = 0
                sys_state['e_frames'] = 0
                status = 'F'
            
            if sys_state['e_frames'] >= CONSEC_FRAMES:
                status = 'E'
            elif sys_state['d_frames'] >= CONSEC_FRAMES:
                status = 'D'

        else:
            time_since_seen = now - sys_state['last_seen_time']
            if pose_detected:
                pose_nose = pose_result.pose_landmarks[0][0]
                if pose_nose.y < 0.1:
                    status = 'A'
                    away_triggered = True
                else:
                    status = 'I'
            else:
                if time_since_seen > AWAY_TIMEOUT:
                    status = 'A'
                    away_triggered = True
                else:
                    status = 'I'
                    
        # Track derivations (Only count when state flips to D or E from F/I)
        if status in ['D', 'E'] and last_eval_status not in ['D', 'E']:
            sys_state['deviations'] += 1
        last_eval_status = status

        send_to_esp32(status)

        # Drawing visuals for stream
        color = (0, 255, 0) # Green 
        if status == 'D': color = (0, 165, 255) # Orange
        if status == 'E': color = (0, 0, 255) # Red
        if status == 'A': color = (255, 0, 0) # Blue
        
        # Draw tech-style corners
        cv2.rectangle(frame, (10, 10), (30, 30), color, 2)
        cv2.line(frame, (10, 10), (10, 30), color, 4)
        cv2.line(frame, (10, 10), (30, 10), color, 4)
        
        cv2.rectangle(frame, (w-30, 10), (w-10, 30), color, 2)
        cv2.line(frame, (w-10, 10), (w-10, 30), color, 4)
        cv2.line(frame, (w-30, 10), (w-10, 10), color, 4)
        
        cv2.rectangle(frame, (10, h-30), (30, h-10), color, 2)
        cv2.line(frame, (10, h-10), (10, h-30), color, 4)
        cv2.line(frame, (10, h-10), (30, h-10), color, 4)

        cv2.rectangle(frame, (w-30, h-30), (w-10, h-10), color, 2)
        cv2.line(frame, (w-10, h-10), (w-10, h-30), color, 4)
        cv2.line(frame, (w-30, h-10), (w-10, h-10), color, 4)
        
        label = f"SYS_STATUS: {status}"
        if not face_detected and not away_triggered:
            label += f" | AWAY_IN: {int(AWAY_TIMEOUT - (now - sys_state['last_seen_time']))}s"
            
        cv2.putText(frame, label, (40, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

# --- ROUTES ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/toggle_system', methods=['POST'])
def toggle_system():
    sys_state['is_active'] = not sys_state['is_active']
    
    if sys_state['is_active']:
        sys_state['session_start_time'] = time.time()
        sys_state['deviations'] = 0 # Reset counters on new session
    else:
        sys_state['session_start_time'] = None
        send_to_esp32('I') # Reset ESP32

    return jsonify({'is_active': sys_state['is_active']})

if __name__ == '__main__':
    # Use socketio.run for integrated websocket serving
    socketio.run(app, debug=True, use_reloader=False, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
