import cv2
import mediapipe as mp
import numpy as np
import base64
from typing import Tuple, Optional

class PoseAnalyzer:
    def __init__(self):
        self.camera = None
        self.pose = None
        self.is_analyzing = False
        
    def init_camera(self) -> bool:
        """Initialize the camera with optimal settings."""
        try:
            self.camera = cv2.VideoCapture(0)
            if not self.camera.isOpened():
                return False
                
            # Set optimal camera settings
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            self.camera.set(cv2.CAP_PROP_FPS, 30)
            self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            return True
        except Exception as e:
            print(f"Error initializing camera: {e}")
            return False
            
    def init_pose_detector(self):
        """Initialize MediaPipe Pose detector."""
        self.pose = mp.solutions.pose.Pose(
            model_complexity=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
    def process_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, dict]:
        """Process a single frame for pose detection and analysis."""
        if not self.pose:
            return frame, {}
            
        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Process the frame
        results = self.pose.process(rgb_frame)
        
        # Initialize feedback dictionary
        feedback = {
            'posture': 'Good',
            'warnings': [],
            'landmarks': []
        }
        
        # Draw pose landmarks if detected
        if results.pose_landmarks:
            # Convert landmarks to list of coordinates
            landmarks = []
            for landmark in results.pose_landmarks.landmark:
                landmarks.append({
                    'x': landmark.x,
                    'y': landmark.y,
                    'z': landmark.z,
                    'visibility': landmark.visibility
                })
            feedback['landmarks'] = landmarks
            
            # Draw skeleton
            self._draw_skeleton(frame, results.pose_landmarks)
            
            # Analyze posture
            self._analyze_posture(frame, results.pose_landmarks, feedback)
            
        return frame, feedback
        
    def _draw_skeleton(self, frame: np.ndarray, landmarks):
        """Draw the pose skeleton on the frame."""
        mp_drawing = mp.solutions.drawing_utils
        mp_drawing_styles = mp.solutions.drawing_styles
        
        mp_drawing.draw_landmarks(
            frame,
            landmarks,
            mp.solutions.pose.POSE_CONNECTIONS,
            landmark_drawing_spec=mp_drawing_styles.get_default_pose_landmarks_style()
        )
        
    def _analyze_posture(self, frame: np.ndarray, landmarks, feedback: dict):
        """Analyze posture and provide feedback."""
        # Get key points
        left_shoulder = landmarks.landmark[mp.solutions.pose.PoseLandmark.LEFT_SHOULDER]
        right_shoulder = landmarks.landmark[mp.solutions.pose.PoseLandmark.RIGHT_SHOULDER]
        left_hip = landmarks.landmark[mp.solutions.pose.PoseLandmark.LEFT_HIP]
        right_hip = landmarks.landmark[mp.solutions.pose.PoseLandmark.RIGHT_HIP]
        
        # Calculate shoulder and hip angles
        shoulder_angle = self._calculate_angle(left_shoulder, right_shoulder)
        hip_angle = self._calculate_angle(left_hip, right_hip)
        
        # Check for slouching
        if shoulder_angle < 160:  # Shoulders are not level
            feedback['posture'] = 'Poor'
            feedback['warnings'].append('Shoulders are not level - try to straighten your posture')
            
        # Check for hip alignment
        if abs(hip_angle - 180) > 10:  # Hips are not level
            feedback['warnings'].append('Hips are not level - maintain proper alignment')
            
    def _calculate_angle(self, point1, point2) -> float:
        """Calculate the angle between two points."""
        angle = np.arctan2(point2.y - point1.y, point2.x - point1.x) * 180 / np.pi
        return abs(angle)
        
    def get_frame(self) -> Optional[Tuple[bool, bytes]]:
        """Get a frame from the camera and convert it to base64."""
        if not self.camera or not self.camera.isOpened():
            return None
            
        ret, frame = self.camera.read()
        if not ret:
            return None
            
        # Process frame if analysis is active
        if self.is_analyzing:
            frame, _ = self.process_frame(frame)
            
        # Convert frame to base64
        _, buffer = cv2.imencode('.jpg', frame)
        frame_base64 = base64.b64encode(buffer).decode('utf-8')
        
        return ret, frame_base64
        
    def start_analysis(self):
        """Start the pose analysis."""
        self.is_analyzing = True
        
    def stop_analysis(self):
        """Stop the pose analysis."""
        self.is_analyzing = False
        
    def cleanup(self):
        """Release resources."""
        if self.camera:
            self.camera.release()
        if self.pose:
            self.pose.close()
        self.camera = None
        self.pose = None 