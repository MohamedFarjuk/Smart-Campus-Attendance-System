import cv2
import mediapipe as mp
import numpy as np

mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(refine_landmarks=True)

# Eye landmark indices for MediaPipe Face Mesh
LEFT_EYE = [362, 385, 387, 263, 373, 380]
RIGHT_EYE = [33, 160, 158, 133, 153, 144]

def calculate_ear(eye_landmarks, landmarks, frame_width, frame_height):
    coords = np.array([(landmarks[p].x * frame_width, landmarks[p].y * frame_height) for p in eye_landmarks])
    vertical_dist1 = np.linalg.norm(coords[1] - coords[5])
    vertical_dist2 = np.linalg.norm(coords[2] - coords[4])
    horizontal_dist = np.linalg.norm(coords[0] - coords[3])
    ear = (vertical_dist1 + vertical_dist2) / (2.0 * horizontal_dist)
    return ear

def check_liveness(frame):
    h, w, _ = frame.shape
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb_frame)
    
    if results.multi_face_landmarks:
        for face_landmarks in results.multi_face_landmarks:
            landmarks = face_landmarks.landmark
            left_ear = calculate_ear(LEFT_EYE, landmarks, w, h)
            right_ear = calculate_ear(RIGHT_EYE, landmarks, w, h)
            avg_ear = (left_ear + right_ear) / 2.0
            
            # If EAR drops below threshold, blink is detected (Real human)
            if avg_ear < 0.20:
                return True 
    return False