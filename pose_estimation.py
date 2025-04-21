import os
import cv2
import numpy as np
import logging
import base64
from collections import deque
import atexit
import mediapipe as mp
from typing import List, Dict, Tuple, Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize MediaPipe Pose
mp_pose = mp.solutions.pose
pose_detector = None
camera = None

def init_pose_detector():
    """Initialize the MediaPipe pose detector."""
    global pose_detector
    try:
        pose_detector = mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        return True
    except Exception as e:
        logger.error(f"Failed to initialize pose detector: {str(e)}")
        return False

def init_camera(camera_id=0):
    """Initialize the camera."""
    global camera
    try:
        camera = cv2.VideoCapture(camera_id)
        if not camera.isOpened():
            logger.error("Failed to open camera")
            return False
            
        # Set camera properties for better performance
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        camera.set(cv2.CAP_PROP_FPS, 30)
        
        return True
    except Exception as e:
        logger.error(f"Failed to initialize camera: {str(e)}")
        return False

def get_frame():
    """Get a frame from the camera."""
    global camera
    if camera is None or not camera.isOpened():
        if not init_camera():
            return None
            
    try:
        ret, frame = camera.read()
        if not ret:
            logger.error("Failed to capture frame")
            return None
        return frame
    except Exception as e:
        logger.error(f"Error capturing frame: {str(e)}")
        return None

def process_live_video(frame) -> Optional[Dict]:
    """Process live video feed and return pose landmarks."""
    global pose_detector
    
    if pose_detector is None:
        if not init_pose_detector():
            return None
        
    try:
        # Convert to RGB for MediaPipe
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Process frame
        results = pose_detector.process(frame_rgb)
        
        if results.pose_landmarks:
            # Draw skeleton with improved visibility
            mp.solutions.drawing_utils.draw_landmarks(
                frame,
                results.pose_landmarks,
                mp_pose.POSE_CONNECTIONS,
                mp.solutions.drawing_utils.DrawingSpec(color=(0, 255, 0), thickness=3, circle_radius=3),
                mp.solutions.drawing_utils.DrawingSpec(color=(0, 255, 0), thickness=3)
            )
            
            return {
                'frame': frame,
                'landmarks': results.pose_landmarks.landmark,
                'segmentation_mask': results.segmentation_mask
            }
            
        return {'frame': frame, 'landmarks': None, 'segmentation_mask': None}
        
    except Exception as e:
        logger.error(f"Error processing video frame: {str(e)}")
        return None

def analyze_pose(landmarks, sport: str, analysis_type: str) -> List[Dict]:
    """Analyze pose and return feedback."""
    feedback = []
    
    if not landmarks:
        return [{'status': 'error', 'message': 'No pose detected'}]
    
    try:
        # Basic posture analysis
        left_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]
        right_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
        
        # Check shoulder alignment
        shoulder_diff = abs(left_shoulder.y - right_shoulder.y)
        if shoulder_diff > 0.1:
            feedback.append({
                'status': 'warning',
                'message': 'Keep your shoulders level'
            })
        else:
            feedback.append({
                'status': 'good',
                'message': 'Good shoulder alignment'
            })
        
        # Sport-specific analysis
        if sport == 'badminton':
            # Check arm position
            left_elbow = landmarks[mp_pose.PoseLandmark.LEFT_ELBOW]
            if left_elbow.y > left_shoulder.y:
                feedback.append({
                    'status': 'warning',
                    'message': 'Keep your racket arm up'
                })
        
        elif sport == 'running':
            # Check knee position
            left_knee = landmarks[mp_pose.PoseLandmark.LEFT_KNEE]
            right_knee = landmarks[mp_pose.PoseLandmark.RIGHT_KNEE]
            if left_knee.y > left_shoulder.y or right_knee.y > right_shoulder.y:
                feedback.append({
                    'status': 'warning',
                    'message': 'Lift your knees higher'
                })
        
        elif sport == 'football':
            # Check stance
            left_hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP]
            right_hip = landmarks[mp_pose.PoseLandmark.RIGHT_HIP]
            if abs(left_hip.y - right_hip.y) > 0.1:
                feedback.append({
                    'status': 'warning',
                    'message': 'Keep your hips level'
                })
        
        return feedback
        
    except Exception as e:
        logger.error(f"Error analyzing pose: {str(e)}")
        return [{'status': 'error', 'message': 'Error analyzing pose'}]

def calculate_stance_width(landmarks):
    """Calculate the width of the stance based on foot positions."""
    try:
        left_ankle = landmarks[27]  # Left ankle
        right_ankle = landmarks[28]  # Right ankle
        return abs(left_ankle['x'] - right_ankle['x'])
    except Exception as e:
        logger.error(f"Error calculating stance width: {str(e)}")
        return 0.4  # Default value

def check_arm_position(landmarks):
    """Check the position of arms relative to the body."""
    try:
        left_shoulder = landmarks[11]  # Left shoulder
        right_shoulder = landmarks[12]  # Right shoulder
        left_elbow = landmarks[13]  # Left elbow
        right_elbow = landmarks[14]  # Right elbow
        
        # Calculate average distance of elbows from shoulders
        left_distance = abs(left_elbow['x'] - left_shoulder['x'])
        right_distance = abs(right_elbow['x'] - right_shoulder['x'])
        return (left_distance + right_distance) / 2
    except Exception as e:
        logger.error(f"Error checking arm position: {str(e)}")
        return 0.3  # Default value

def check_head_position(landmarks):
    """Check if head is properly aligned with the spine."""
    try:
        nose = landmarks[0]  # Nose
        left_shoulder = landmarks[11]  # Left shoulder
        right_shoulder = landmarks[12]  # Right shoulder
        
        # Calculate shoulder midpoint
        shoulder_mid_x = (left_shoulder['x'] + right_shoulder['x']) / 2
        shoulder_mid_y = (left_shoulder['y'] + right_shoulder['y']) / 2
        
        # Calculate head position relative to shoulders
        return nose['x'] - shoulder_mid_x
    except Exception as e:
        logger.error(f"Error checking head position: {str(e)}")
        return 0  # Default value

def cleanup():
    """Clean up resources."""
    global camera, pose_detector
    if camera is not None:
        camera.release()
    if pose_detector is not None:
        pose_detector.close()
    logger.info("Cleaned up resources")

# Register cleanup function
atexit.register(cleanup)
