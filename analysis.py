import logging
import numpy as np
import json
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import pickle
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sklearn.ensemble import IsolationForest
import cv2
import mediapipe as mp

from models import TrainingLog, VideoAnalysis, UserProfile, Sport, db, Progress

# Dictionary of sport-specific feedback templates
FEEDBACK_TEMPLATES = {
    "Basketball": {
        "jump": "Your jumping technique shows {quality}. Keep your knees aligned with your toes and maintain a balanced landing position.",
        "shooting": "Your shooting form is {quality}. Focus on a consistent release point and follow-through.",
        "general": "Your overall basketball movement patterns show {quality}. Focus on maintaining proper posture and balance."
    },
    "Tennis": {
        "serve": "Your serving technique shows {quality}. Pay attention to the toss height and racket path.",
        "forehand": "Your forehand stroke is {quality}. Remember to rotate your shoulders and follow through.",
        "backhand": "Your backhand technique is {quality}. Maintain proper grip and weight transfer.",
        "general": "Your overall tennis movements show {quality}. Focus on footwork and preparation."
    },
    "Football": {
        "kick": "Your kicking technique shows {quality}. Focus on your plant foot position and follow-through.",
        "running": "Your running form is {quality}. Maintain an upright posture and proper arm movement.",
        "general": "Your overall football movements show {quality}. Remember to stay balanced and ready to change direction."
    },
    "Badminton": {
        "smash": "Your smash technique shows {quality}. Focus on wrist snap and racket angle.",
        "serve": "Your service technique is {quality}. Keep a consistent toss and proper stance.",
        "general": "Your overall badminton movements show {quality}. Work on quick footwork and recovery position."
    },
    "Running": {
        "form": "Your running form shows {quality}. Focus on arm swing and posture.",
        "stride": "Your stride length and frequency is {quality}. Work on maintaining consistent cadence.",
        "general": "Your overall running mechanics show {quality}. Remember to land midfoot and maintain good posture."
    },
    "default": {
        "general": "Your movement patterns show {quality}. Focus on maintaining proper form and alignment."
    }
}

# Dictionary of sport-specific injury risk templates
INJURY_RECOMMENDATIONS = {
    "Low": "Continue with your current training program. Maintain regular stretching and recovery protocols.",
    "Medium": "Consider modifying your training intensity. Focus on proper form and technique. Include more rest days.",
    "High": "Reduce training volume immediately. Consult with a sports medicine professional. Focus on recovery and corrective exercises."
}

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_badminton_pose(landmarks):
    """Analyzes badminton-specific pose landmarks."""
    try:
        # Wrist angles (simplified example - needs refinement for accuracy)
        right_wrist = np.array([landmarks[16]['x'], landmarks[16]['y']])
        right_elbow = np.array([landmarks[14]['x'], landmarks[14]['y']])
        right_shoulder = np.array([landmarks[12]['x'], landmarks[12]['y']])

        left_wrist = np.array([landmarks[15]['x'], landmarks[15]['y']])
        left_elbow = np.array([landmarks[13]['x'], landmarks[13]['y']])
        left_shoulder = np.array([landmarks[11]['x'], landmarks[11]['y']])

        vec1_r = right_wrist - right_elbow
        vec2_r = right_elbow - right_shoulder
        vec1_l = left_wrist - left_elbow
        vec2_l = left_elbow - left_shoulder

        cosine_angle_r = np.dot(vec1_r, vec2_r) / (np.linalg.norm(vec1_r) * np.linalg.norm(vec2_r))
        cosine_angle_l = np.dot(vec1_l, vec2_l) / (np.linalg.norm(vec1_l) * np.linalg.norm(vec2_l))

        right_wrist_angle = np.arccos(np.clip(cosine_angle_r, -1.0, 1.0)) * 180 / np.pi
        left_wrist_angle = np.arccos(np.clip(cosine_angle_l, -1.0, 1.0)) * 180 / np.pi

        # Knee angles (simplified example)
        right_hip = np.array([landmarks[24]['x'], landmarks[24]['y']])
        right_knee = np.array([landmarks[26]['x'], landmarks[26]['y']])
        right_ankle = np.array([landmarks[28]['x'], landmarks[28]['y']])

        left_hip = np.array([landmarks[23]['x'], landmarks[23]['y']])
        left_knee = np.array([landmarks[25]['x'], landmarks[25]['y']])
        left_ankle = np.array([landmarks[27]['x'], landmarks[27]['y']])

        vec1_r = right_hip - right_knee
        vec2_r = right_ankle - right_knee
        vec1_l = left_hip - left_knee
        vec2_l = left_ankle - left_knee

        cosine_angle_r = np.dot(vec1_r, vec2_r) / (np.linalg.norm(vec1_r) * np.linalg.norm(vec2_r))
        cosine_angle_l = np.dot(vec1_l, vec2_l) / (np.linalg.norm(vec1_l) * np.linalg.norm(vec2_l))

        right_knee_angle = np.arccos(np.clip(cosine_angle_r, -1.0, 1.0)) * 180 / np.pi
        left_knee_angle = np.arccos(np.clip(cosine_angle_l, -1.0, 1.0)) * 180 / np.pi

        # Shoulder-hip rotation (simplified example)
        right_shoulder = np.array([landmarks[12]['x'], landmarks[12]['y']])
        right_hip = np.array([landmarks[24]['x'], landmarks[24]['y']])
        left_shoulder = np.array([landmarks[11]['x'], landmarks[11]['y']])
        left_hip = np.array([landmarks[23]['x'], landmarks[23]['y']])


        shoulder_rotation = np.arctan2(right_shoulder[1] - left_shoulder[1], right_shoulder[0] - left_shoulder[0]) * 180 / np.pi
        hip_rotation = np.arctan2(right_hip[1] - left_hip[1], right_hip[0] - left_hip[0]) * 180 / np.pi

        return {
            'wrist_angles': {'right': right_wrist_angle, 'left': left_wrist_angle},
            'knee_angles': {'right': right_knee_angle, 'left': left_knee_angle},
            'shoulder_rotation': shoulder_rotation,
            'hip_rotation': hip_rotation
        }

    except (KeyError, IndexError) as e:
        logging.error(f"Error in analyze_badminton_pose: {e}")
        return {'wrist_angles': {'right': 90, 'left': 90}, 'knee_angles': {'right': 90, 'left': 90},
                'shoulder_rotation': 0, 'hip_rotation': 0}

def analyze_movement(pose_data, sport_name):
    """
    Analyze movement patterns based on pose data and provide feedback

    Args:
        pose_data: Dictionary containing pose landmarks and metadata
        sport_name: Name of the sport

    Returns:
        Tuple containing feedback text and recommendations
    """
    logging.info(f"Analyzing movement for sport: {sport_name}")

    # Default values if sport isn't recognized
    if sport_name not in FEEDBACK_TEMPLATES:
        sport_name = "default"

    feedback_parts = []
    templates = FEEDBACK_TEMPLATES[sport_name]

    # Basic analysis - this would be more sophisticated in a real implementation
    try:
        # Check if we have pose data
        if not pose_data or not pose_data.get("pose_data"):
            return "Insufficient pose data for analysis", "Please upload a clearer video with full body visibility"

        # Get some sample frames to analyze
        frame_indices = list(pose_data["pose_data"].keys())
        if not frame_indices:
            return "No valid pose data detected", "Please upload a clearer video with better lighting"

        # For demonstration, we'll implement some basic heuristic analysis
        # In a real system, this would be much more sophisticated

        # Check posture (based on shoulder and hip alignment)
        posture_score = 0
        frame_count = 0

        for frame_idx in frame_indices:
            landmarks = pose_data["pose_data"][frame_idx]
            if len(landmarks) < 33:  # MediaPipe provides 33 landmarks
                continue

            # Get shoulder landmarks
            left_shoulder = np.array([landmarks[11]['x'], landmarks[11]['y']])
            right_shoulder = np.array([landmarks[12]['x'], landmarks[12]['y']])

            # Get hip landmarks
            left_hip = np.array([landmarks[23]['x'], landmarks[23]['y']])
            right_hip = np.array([landmarks[24]['x'], landmarks[24]['y']])

            # Calculate shoulder line angle relative to horizontal
            shoulder_angle = np.arctan2(right_shoulder[1] - left_shoulder[1], 
                                       right_shoulder[0] - left_shoulder[0]) * 180 / np.pi

            # Calculate hip line angle relative to horizontal
            hip_angle = np.arctan2(right_hip[1] - left_hip[1], 
                                  right_hip[0] - left_hip[0]) * 180 / np.pi

            # Check if shoulders and hips are relatively aligned (parallel)
            angle_diff = abs(shoulder_angle - hip_angle)
            if angle_diff < 10:  # Good alignment
                posture_score += 1

            frame_count += 1

        # Calculate overall posture quality
        if frame_count > 0:
            posture_quality = posture_score / frame_count

            if posture_quality > 0.7:
                posture_feedback = "excellent posture alignment"
            elif posture_quality > 0.4:
                posture_feedback = "adequate posture but could use improvement"
            else:
                posture_feedback = "poor posture alignment that needs correction"

            feedback_parts.append(f"Your overall posture shows {posture_feedback}.")

        # Sport-specific analysis
        if sport_name == "Basketball":
            feedback_parts.append(templates["general"].format(quality="reasonable technique"))

            # Additional basketball-specific feedback would go here
            # For example, analyzing jump shot form

        elif sport_name == "Tennis":
            feedback_parts.append(templates["general"].format(quality="adequate form"))

            # Additional tennis-specific feedback would go here
            # For example, analyzing serve or forehand technique

        elif sport_name == "Football":
            feedback_parts.append(templates["general"].format(quality="good technique"))

            # Additional football-specific feedback would go here

        elif sport_name == "Badminton":
            for frame_idx, landmarks in pose_data["pose_data"].items():
                metrics = analyze_badminton_pose(landmarks)

                # Analyze wrist angles (critical for smash and clear shots)
                if any(angle > 100 for angle in metrics['wrist_angles'].values()):
                    feedback_parts.append(f"At frame {frame_idx}: Excessive wrist flexion detected. "
                                       "Keep wrist firm during shots to prevent injury.")

                # Check knee angles for proper stance
                if any(angle < 130 for angle in metrics['knee_angles'].values()):
                    feedback_parts.append(f"At frame {frame_idx}: Deep knee bend observed. "
                                       "Maintain moderate knee flexion for quick movements.")

                # Analyze shoulder-hip rotation (important for power generation)
                rotation_diff = abs(metrics['shoulder_rotation'] - metrics['hip_rotation'])
                if rotation_diff > 45:
                    feedback_parts.append(f"At frame {frame_idx}: Excessive upper body rotation. "
                                       "Coordinate shoulder and hip rotation for better shot control.")

            # Add general form assessment
            if len(feedback_parts) == 0:
                feedback_parts.append(templates["general"].format(quality="good form"))
            else:
                feedback_parts.append("\nFocus on maintaining proper form throughout your shots.")

        elif sport_name == "Running":
            feedback_parts.append(templates["form"].format(quality="adequate technique"))

            # Check vertical oscillation (less is usually better for running efficiency)
            vertical_movements = []

            for frame_idx in frame_indices:
                landmarks = pose_data["pose_data"][frame_idx]
                if len(landmarks) < 33:
                    continue

                # Track hip height as proxy for vertical oscillation
                left_hip_y = landmarks[23]['y']
                right_hip_y = landmarks[24]['y']
                avg_hip_y = (left_hip_y + right_hip_y) / 2
                vertical_movements.append(avg_hip_y)

            if vertical_movements:
                oscillation = np.std(vertical_movements)
                if oscillation < 0.02:
                    feedback_parts.append("Your vertical oscillation is minimal, which is excellent for running efficiency.")
                elif oscillation < 0.04:
                    feedback_parts.append("Your vertical oscillation is moderate. Try to minimize up-and-down movement for better efficiency.")
                else:
                    feedback_parts.append("Your vertical oscillation is high. Focus on reducing bouncing for better running economy.")

        else:
            # Default feedback
            feedback_parts.append(templates["general"].format(quality="reasonable form"))

        # Generate recommendations
        recommendations = [
            "Focus on maintaining proper form throughout your entire movement.",
            "Consider recording from multiple angles for more detailed analysis.",
            "Regular practice with attention to technique will help improve performance."
        ]

        if posture_score / frame_count < 0.4:
            recommendations.append("Work on core strength exercises to improve posture and alignment.")

        # Join feedback parts and recommendations
        feedback = " ".join(feedback_parts)
        recommendations_text = "\n".join(f"• {r}" for r in recommendations)

        return feedback, recommendations_text

    except Exception as e:
        logging.error(f"Error in movement analysis: {str(e)}")
        return "Error analyzing movement", "Please try again with a clearer video"

def predict_injury_risk(pose_data, user_id, sport_name):
    """
    Predict injury risk based on pose data and user history

    Args:
        pose_data: Dictionary containing pose landmarks
        user_id: User ID for history lookup
        sport_name: Name of the sport

    Returns:
        Risk level (Low, Medium, High)
    """
    logging.info(f"Predicting injury risk for user {user_id} in {sport_name}")

    try:
        # Get user profile and training history
        profile = UserProfile.query.filter_by(user_id=user_id).first()

        # Get recent training logs
        training_logs = TrainingLog.query.filter_by(user_id=user_id).order_by(TrainingLog.date.desc()).limit(10).all()

        # Check if we have enough data
        if not profile or not training_logs or len(training_logs) < 3:
            # Not enough historical data, use simplified model
            return simplified_risk_assessment(pose_data, sport_name)

        # Extract features from pose data
        pose_features = extract_pose_features(pose_data)

        # Extract features from training history
        training_intensity = [log.intensity for log in training_logs]
        avg_intensity = sum(training_intensity) / len(training_intensity)
        max_intensity = max(training_intensity)

        # Check for reported symptoms
        has_symptoms = any(log.symptoms and len(log.symptoms.strip()) > 0 for log in training_logs)

        # Combine features
        features = pose_features + [
            avg_intensity / 10.0,  # Normalize to 0-1
            max_intensity / 10.0,  # Normalize to 0-1
            1.0 if has_symptoms else 0.0
        ]

        # In a real system, we would use a trained ML model here
        # For demonstration, we'll use a rule-based approach

        risk_score = 0

        # Check pose features (joint angles, imbalances)
        if pose_features[0] > 0.7:  # High knee angle variability
            risk_score += 2

        if pose_features[1] > 0.6:  # High shoulder imbalance
            risk_score += 1

        # Check training intensity
        if avg_intensity > 7:
            risk_score += 1

        if max_intensity > 8:
            risk_score += 1

        # Check symptoms
        if has_symptoms:
            risk_score += 2

        # Determine risk level
        if risk_score >= 4:
            return "High"
        elif risk_score >= 2:
            return "Medium"
        else:
            return "Low"

    except Exception as e:
        logging.error(f"Error in injury risk prediction: {str(e)}")
        return "Medium"  # Default to medium risk if an error occurs

def extract_pose_features(pose_data):
    """
    Extract relevant features from pose data for injury risk assessment

    Args:
        pose_data: Dictionary containing pose landmarks

    Returns:
        List of features
    """
    # For demonstration, extract some basic features
    # In a real system, this would be much more sophisticated

    try:
        frames = pose_data.get("pose_data", {})
        if not frames:
            return [0.5, 0.5]  # Default values if no data

        knee_angles = []
        shoulder_heights = []

        for frame_idx, landmarks in frames.items():
            if len(landmarks) < 33:  # Need full body landmarks
                continue

            # Calculate knee angles
            # Right leg
            right_hip = np.array([landmarks[24]['x'], landmarks[24]['y'], landmarks[24].get('z', 0)])
            right_knee = np.array([landmarks[26]['x'], landmarks[26]['y'], landmarks[26].get('z', 0)])
            right_ankle = np.array([landmarks[28]['x'], landmarks[28]['y'], landmarks[28].get('z', 0)])

            vec1 = right_hip - right_knee
            vec2 = right_ankle - right_knee

            cosine_angle = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
            right_knee_angle = np.arccos(np.clip(cosine_angle, -1.0, 1.0)) * 180 / np.pi

            # Left leg
            left_hip = np.array([landmarks[23]['x'], landmarks[23]['y'], landmarks[23].get('z', 0)])
            left_knee = np.array([landmarks[25]['x'], landmarks[25]['y'], landmarks[25].get('z', 0)])
            left_ankle = np.array([landmarks[27]['x'], landmarks[27]['y'], landmarks[27].get('z', 0)])

            vec1 = left_hip - left_knee
            vec2 = left_ankle - left_knee

            cosine_angle = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
            left_knee_angle = np.arccos(np.clip(cosine_angle, -1.0, 1.0)) * 180 / np.pi

            knee_angles.append((right_knee_angle, left_knee_angle))

            # Get shoulder heights
            left_shoulder_y = landmarks[11]['y']
            right_shoulder_y = landmarks[12]['y']

            shoulder_heights.append((left_shoulder_y, right_shoulder_y))

        # Calculate features
        knee_angle_diffs = [abs(right - left) for right, left in knee_angles]
        knee_variability = np.std(knee_angle_diffs) / 180.0  # Normalize to 0-1

        shoulder_height_diffs = [abs(left - right) for left, right in shoulder_heights]
        shoulder_imbalance = np.mean(shoulder_height_diffs)

        return [knee_variability, shoulder_imbalance]

    except Exception as e:
        logging.error(f"Error extracting pose features: {str(e)}")
        return [0.5, 0.5]  # Default values on error

def simplified_risk_assessment(pose_data, sport_name):
    """
    Simplified risk assessment when insufficient user history is available

    Args:
        pose_data: Dictionary containing pose landmarks
        sport_name: Name of the sport

    Returns:
        Risk level (Low, Medium, High)
    """
    try:
        # Extract basic features
        pose_features = extract_pose_features(pose_data)

        # Very simple rule-based assessment
        knee_variability, shoulder_imbalance = pose_features

        if knee_variability > 0.7 or shoulder_imbalance > 0.7:
            return "High"
        elif knee_variability > 0.4 or shoulder_imbalance > 0.4:
            return "Medium"
        else:
            return "Low"

    except Exception as e:
        logging.error(f"Error in simplified risk assessment: {str(e)}")
        return "Medium"  # Default to medium

def analyze_video(filepath):
    """
    Analyze a video file and return pose data and analysis results.
    
    Args:
        filepath: Path to the video file
        
    Returns:
        Dictionary containing pose data and analysis results
    """
    try:
        # Initialize pose detector
        mp_pose = mp.solutions.pose
        pose = mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # Open video file
        cap = cv2.VideoCapture(filepath)
        if not cap.isOpened():
            raise ValueError("Could not open video file")
            
        pose_data = {}
        frame_count = 0
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Process frame
            results = pose.process(rgb_frame)
            
            if results.pose_landmarks:
                # Convert landmarks to dictionary format
                landmarks = []
                for landmark in results.pose_landmarks.landmark:
                    landmarks.append({
                        'x': landmark.x,
                        'y': landmark.y,
                        'z': landmark.z,
                        'visibility': landmark.visibility
                    })
                
                pose_data[frame_count] = landmarks
            
            frame_count += 1
            
        # Clean up
        cap.release()
        pose.close()
        
        return {
            'pose_data': pose_data,
            'frame_count': frame_count,
            'analysis_timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logging.error(f"Error analyzing video: {str(e)}")
        return {
            'pose_data': {},
            'frame_count': 0,
            'analysis_timestamp': datetime.now().isoformat(),
            'error': str(e)
        }