import cv2
import numpy as np
import time
import serial
import sys
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# --- CONFIGURATION ---
SERIAL_PORT = 'COM4'
BAUD_RATE = 115200
FACE_MODEL_PATH = 'face_landmarker.task'
POSE_MODEL_PATH = 'pose_landmarker.task'

# Thresholds
EYE_AR_THRESH = 0.22
AWAY_TIMEOUT = 20.0  # seconds

# --- INITIALIZATION ---
try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    print(f"Connected to {SERIAL_PORT}", flush=True)
except Exception as e:
    print(f"FAILED to connect to {SERIAL_PORT}: {e}", flush=True)
    ser = None

# Initialize Face Landmarker
base_options_face = python.BaseOptions(model_asset_path=FACE_MODEL_PATH)
options_face = vision.FaceLandmarkerOptions(
    base_options=base_options_face,
    output_face_blendshapes=True,
    num_faces=1
)
face_detector = vision.FaceLandmarker.create_from_options(options_face)

# Initialize Pose Landmarker
base_options_pose = python.BaseOptions(model_asset_path=POSE_MODEL_PATH)
options_pose = vision.PoseLandmarkerOptions(
    base_options=base_options_pose,
    running_mode=vision.RunningMode.IMAGE
)
pose_detector = vision.PoseLandmarker.create_from_options(options_pose)

cap = cv2.VideoCapture(0)

# State
current_status = 'I'
last_seen_time = time.time()
away_triggered = False

def send_to_esp32(status):
    global current_status
    if status != current_status:
        print(f"Sending: {status}", flush=True)
        if ser and ser.is_open:
            try:
                ser.write(status.encode())
            except Exception as e:
                print(f"Serial write error: {e}", flush=True)
        current_status = status

def get_aspect_ratio(eye_landmarks_indices, landmarks):
    v1 = np.linalg.norm(np.array(landmarks[eye_landmarks_indices[1]]) - np.array(landmarks[eye_landmarks_indices[5]]))
    v2 = np.linalg.norm(np.array(landmarks[eye_landmarks_indices[2]]) - np.array(landmarks[eye_landmarks_indices[4]]))
    h = np.linalg.norm(np.array(landmarks[eye_landmarks_indices[0]]) - np.array(landmarks[eye_landmarks_indices[3]]))
    return (v1 + v2) / (2.0 * h) if h != 0 else 0.0

LEFT_EYE = [362, 385, 387, 263, 373, 380]
RIGHT_EYE = [33, 160, 158, 133, 153, 144]

print("Advanced Monitor running... (Face + Pose) Press 'q' to quit.", flush=True)

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    frame = cv2.flip(frame, 1)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
    
    # Run detectors
    face_result = face_detector.detect(mp_image)
    pose_result = pose_detector.detect(mp_image)

    h, w, _ = frame.shape
    status = 'I'
    now = time.time()

    face_detected = len(face_result.face_landmarks) > 0
    pose_detected = len(pose_result.pose_landmarks) > 0

    if face_detected:
        last_seen_time = now
        away_triggered = False
        
        face_landmarks = face_result.face_landmarks[0]
        pixel_landmarks = [[lm.x * w, lm.y * h, lm.z * w] for lm in face_landmarks]

        left_ear = get_aspect_ratio(LEFT_EYE, pixel_landmarks)
        right_ear = get_aspect_ratio(RIGHT_EYE, pixel_landmarks)
        avg_ear = (left_ear + right_ear) / 2.0

        if avg_ear < EYE_AR_THRESH:
            status = 'E'
        else:
            nose_tip = pixel_landmarks[1]
            left_eye_outer = pixel_landmarks[33]
            right_eye_outer = pixel_landmarks[263]
            
            dist_left = np.linalg.norm(np.array(nose_tip) - np.array(left_eye_outer))
            dist_right = np.linalg.norm(np.array(nose_tip) - np.array(right_eye_outer))
            yaw_ratio = dist_left / dist_right if dist_right != 0 else 1.0
            
            eye_center_y = (left_eye_outer[1] + right_eye_outer[1]) / 2.0
            nose_y = nose_tip[1]

            if yaw_ratio > 1.8 or yaw_ratio < 0.55:
                status = 'D'
            elif nose_y < eye_center_y - 10 or nose_y > eye_center_y + 40:
                status = 'D'
            else:
                status = 'F'
                
        # Additional "Getting Up" check using Pose even if face is still there
        if pose_detected:
            # Nose landmark in pose is index 0
            pose_nose = pose_result.pose_landmarks[0][0]
            if pose_nose.y < 0.15: # Head is very high in frame
                status = 'A'

    else:
        # No face detected
        time_since_seen = now - last_seen_time
        
        # Check Pose to see if body is still there but head is gone/high
        if pose_detected:
            pose_nose = pose_result.pose_landmarks[0][0]
            # If head is very high or moving out of top
            if pose_nose.y < 0.1:
                status = 'A'
                away_triggered = True
            else:
                # Body still in seat but face not clear
                status = 'I'
        else:
            # No person detected at all
            if time_since_seen > AWAY_TIMEOUT:
                status = 'A'
                away_triggered = True
            else:
                status = 'I'

    # Send status
    send_to_esp32(status)

    # Visualization
    color = (0, 255, 0) # Green
    if status == 'D': color = (0, 165, 255) # Orange
    if status == 'E': color = (0, 0, 255) # Red
    if status == 'A': color = (255, 0, 0) # Blue
    if status == 'I': color = (128, 128, 128) # Grey

    label = f"Status: {status}"
    if status == 'A': label = "Status: AWAY"
    if not face_detected and not away_triggered:
        label += f" ({int(AWAY_TIMEOUT - (now - last_seen_time))}s)"

    cv2.putText(frame, label, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
    
    if face_detected:
        cv2.putText(frame, f"EAR: {avg_ear:.2f}", (50, 90), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

    cv2.imshow('Anti-Distraction Monitor v2', frame)
    if cv2.waitKey(5) & 0xFF == ord('q'):
        break

cap.release()
if ser:
    ser.close()
cv2.destroyAllWindows()
face_detector.close()
pose_detector.close()
