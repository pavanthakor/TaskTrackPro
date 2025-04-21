import os
import json
import logging
import threading
import time
import base64
import numpy as np
from datetime import datetime
from flask import render_template, redirect, url_for, flash, request, jsonify, session, Response, Blueprint, current_app
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.security import generate_password_hash, check_password_hash
import cv2
import mediapipe as mp
from multiprocessing import Pool
import hashlib

from models import db, User, UserProfile, TrainingLog, VideoAnalysis, Sport, Progress
from forms import LoginForm, RegisterForm, ProfileForm, TrainingLogForm, VideoUploadForm, ProgressForm
from pose_estimation import process_live_video, init_pose_detector, cleanup, analyze_pose
from analysis import analyze_movement, predict_injury_risk, analyze_video

# Initialize MediaPipe Pose
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(
    static_image_mode=False,
    model_complexity=1,
    min_detection_confidence=0.3,
    min_tracking_confidence=0.3
)

# Initialize process pool
pool = Pool(processes=1)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global camera variables
camera = None
camera_lock = threading.Lock()
camera_failed_attempts = 0
MAX_CAMERA_ATTEMPTS = 3

def init_camera():
    """Initialize the camera with proper locking."""
    global camera, camera_failed_attempts
    
    with camera_lock:
        try:
            # Release existing camera if it exists
            if camera is not None:
                camera.release()
                
            # Reset camera on too many failed attempts
            if camera_failed_attempts >= MAX_CAMERA_ATTEMPTS:
                logger.warning("Too many failed camera attempts, waiting before retry")
                time.sleep(2)  # Add a delay before trying again
                camera_failed_attempts = 0
                
            # Create new camera object
            camera = cv2.VideoCapture(0)
            
            # Test camera by reading a frame
            if not camera.isOpened():
                logger.error("Failed to open camera")
                camera_failed_attempts += 1
                return False
                
            success, test_frame = camera.read()
            if not success or test_frame is None:
                logger.error("Failed initial camera frame read")
                camera_failed_attempts += 1
                return False
                
            # Camera is working
            camera_failed_attempts = 0
            logger.info("Camera initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing camera: {str(e)}")
            camera_failed_attempts += 1
            return False

def release_camera():
    """Safely release the camera."""
    global camera
    
    with camera_lock:
        try:
            if camera is not None:
                camera.release()
                camera = None
                logger.info("Camera released")
        except Exception as e:
            logger.error(f"Error releasing camera: {str(e)}")

def get_frame():
    """Get the current frame from the camera with proper error handling."""
    global camera
    
    with camera_lock:
        try:
            if camera is None or not camera.isOpened():
                logger.warning("Camera not initialized, attempting to initialize")
                if not init_camera():
                    return None
            
            success, frame = camera.read()
            if not success or frame is None:
                logger.warning("Failed to read frame, attempting to reinitialize camera")
                if not init_camera():
                    return None
                    
                # Try one more time after reinitialization
                success, frame = camera.read()
                if not success or frame is None:
                    logger.error("Failed to read frame after reinitialization")
                    return None
            
            return frame
            
        except Exception as e:
            logger.error(f"Error in get_frame: {str(e)}")
            return None

routes = Blueprint('routes', __name__)

def process_live_video(frame):
    """Process a single video frame for pose detection."""
    try:
        # Convert the BGR image to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Process the frame with MediaPipe
        results = pose.process(rgb_frame)
        
        # If no pose detection results, return None
        if not results.pose_landmarks:
            return None
        
        # Extract landmarks
        landmarks = []
        for landmark in results.pose_landmarks.landmark:
            # Store normalized coordinates
            landmarks.append([landmark.x, landmark.y, landmark.z, landmark.visibility])
        
        # Log movement to help with debugging
        if hasattr(process_live_video, "prev_landmarks") and process_live_video.prev_landmarks is not None:
            # Calculate movement from previous frame
            movement = 0
            for i in range(min(len(landmarks), len(process_live_video.prev_landmarks))):
                movement += sum((landmarks[i][j] - process_live_video.prev_landmarks[i][j])**2 for j in range(2))
            
            logger.debug(f"Movement detected: {movement:.6f}")
            
            # If very little movement, consider using previous feedback
            if movement < 0.0001:  # Very small movement threshold
                logger.debug("Minimal movement detected")
            
        # Store current landmarks for next comparison
        process_live_video.prev_landmarks = landmarks
        
        return landmarks
        
    except Exception as e:
        logger.error(f"Error in process_live_video: {str(e)}")
        return None

def analyze_posture(landmarks, sport='general'):
    """Analyze posture based on sport-specific criteria using pose landmarks."""
    feedback = []
    
    if sport == 'badminton':
        # Check if person is standing or sitting by looking at hip/knee relationship
        left_hip = landmarks[23]  # Left hip landmark
        left_knee = landmarks[25]  # Left knee landmark
        right_hip = landmarks[24]  # Right hip landmark
        right_knee = landmarks[26]  # Right knee landmark
        
        # Calculate vertical difference between hips and knees
        hip_knee_diff = ((left_hip[1] - left_knee[1]) + (right_hip[1] - right_knee[1])) / 2
        
        # Sitting detection - if knees are roughly at same height as hips
        if abs(hip_knee_diff) < 0.1:  # Small vertical difference means sitting
            feedback.append(("You appear to be sitting. Stand up for proper badminton stance.", "red"))
            return feedback  # Return early with sitting feedback
        
        # Check shoulder position for badminton
        left_shoulder = landmarks[11]
        right_shoulder = landmarks[12]
        
        # Check for shoulder alignment/rotation appropriate for badminton
        shoulder_alignment = abs(left_shoulder[1] - right_shoulder[1])
        if shoulder_alignment < 0.05:  # Shoulders are level - good for badminton ready position
            feedback.append(("Good shoulder position for badminton stance.", "green"))
        else:
            feedback.append(("Keep shoulders level for better balance.", "yellow"))
        
        # Check elbow position for power shots
        left_elbow = landmarks[13]
        right_elbow = landmarks[14]
        left_wrist = landmarks[15]
        right_wrist = landmarks[16]
        
        # Check if arms are in a proper position for badminton
        elbow_wrist_distance = ((left_elbow[0] - left_wrist[0])**2 + (left_elbow[1] - left_wrist[1])**2)**0.5
        if 0.1 < elbow_wrist_distance < 0.3:  # Example range for proper elbow flexion
            feedback.append(("Good elbow position for power shots.", "green"))
        else:
            feedback.append(("Adjust elbow angle for better shot control.", "yellow"))
            
        # Check knee bend - important for badminton ready stance
        left_ankle = landmarks[27]
        right_ankle = landmarks[28]
        knee_ankle_diff = ((left_knee[1] - left_ankle[1]) + (right_knee[1] - right_ankle[1])) / 2
        
        if knee_ankle_diff > 0.15:  # Knees are bent appropriately
            feedback.append(("Good knee bend for quick movement.", "green"))
        else:
            feedback.append(("Bend knees more for better court movement.", "yellow"))
    
    # Add more sports conditions here...
    elif sport == 'tennis':
        # Tennis-specific posture analysis
        pass
    
    # Return at least one feedback item if none were generated
    if not feedback:
        feedback.append(("Stand in proper position for posture analysis.", "yellow"))
    
    return feedback

def calculate_shoulder_angle(landmarks):
    """Calculate the angle between shoulders and hips."""
    # Implementation details...
    return 90  # Placeholder

def calculate_elbow_angle(landmarks):
    """Calculate the angle at the elbow."""
    # Implementation details...
    return 120  # Placeholder

def calculate_knee_angle(landmarks):
    """Calculate the angle at the knee."""
    # Implementation details...
    return 150  # Placeholder

def calculate_hip_angle(landmarks):
    """Calculate the angle at the hip."""
    # Implementation details...
    return 170  # Placeholder

def calculate_stride_length(landmarks):
    """Calculate the stride length."""
    # Implementation details...
    return 0.8  # Placeholder

def calculate_arm_swing(landmarks):
    """Calculate the arm swing angle."""
    # Implementation details...
    return 60  # Placeholder

def calculate_spine_angle(landmarks):
    """Calculate the spine angle."""
    # Implementation details...
    return 175  # Placeholder

def check_shoulder_alignment(landmarks):
    """Check if shoulders are level."""
    # Implementation details...
    return True  # Placeholder

def generate_frames():
    """Generate video frames with pose analysis."""
    camera = cv2.VideoCapture(0)
    if not camera.isOpened():
        logger.error("Failed to open camera")
        return
    
    try:
        while True:
            success, frame = camera.read()
            if not success:
                logger.error("Failed to read frame from camera")
                break
            
            try:
                # Process the frame
                landmarks = process_live_video(frame)
                
                # Draw landmarks on the frame
                if landmarks:
                    # Convert landmarks to MediaPipe format for drawing
                    pose_landmarks = mp.solutions.pose.PoseLandmark
                    for landmark in landmarks:
                        x = int(landmark['x'] * frame.shape[1])
                        y = int(landmark['y'] * frame.shape[0])
                        cv2.circle(frame, (x, y), 5, (0, 255, 0), -1)
                
                # Encode the frame
                ret, buffer = cv2.imencode('.jpg', frame)
                if not ret:
                    logger.error("Failed to encode frame")
                    continue
                frame = buffer.tobytes()
                
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            except Exception as e:
                logger.error(f"Error processing frame: {str(e)}")
                continue
    finally:
        camera.release()
        logger.info("Camera released")

def register_routes(app):
    # Home page
    @app.route('/')
    def index():
        return render_template('index.html')

    # Login route
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(username=form.username.data).first()
            
            if user and user.check_password(form.password.data):
                login_user(user)
                next_page = request.args.get('next')
                flash('Login successful!', 'success')
                return redirect(next_page or url_for('dashboard'))
            else:
                flash('Invalid username or password', 'danger')
        
        return render_template('login.html', form=form)

    # Register route
    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        
        form = RegisterForm()
        if form.validate_on_submit():
            user = User(
                username=form.username.data,
                email=form.email.data
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        
        return render_template('register.html', form=form)

    # Logout route
    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('You have been logged out.', 'info')
        return redirect(url_for('index'))

    # Dashboard route
    @app.route('/dashboard')
    @login_required
    def dashboard():
        # Get user's recent analyses and training logs
        recent_analyses = VideoAnalysis.query.filter_by(user_id=current_user.id)\
            .order_by(VideoAnalysis.timestamp.desc())\
            .limit(5).all()
        
        recent_logs = TrainingLog.query.filter_by(user_id=current_user.id)\
            .order_by(TrainingLog.date.desc())\
            .limit(5).all()
        
        # Check if profile is complete
        profile_complete = False
        if current_user.profile:
            profile = current_user.profile
            profile_complete = all([
                profile.age is not None,
                profile.height is not None,
                profile.weight is not None,
                profile.primary_sport_id is not None,
                profile.experience_level is not None
            ])
        
        return render_template('dashboard.html',
                             recent_analyses=recent_analyses,
                             recent_logs=recent_logs,
                             profile_complete=profile_complete)

    # Profile route
    @app.route('/profile', methods=['GET', 'POST'])
    @login_required
    def profile():
        form = ProfileForm()
        
        # Set sport choices before validation
        form.primary_sport.choices = [(s.id, s.name) for s in Sport.query.all()]
        
        if form.validate_on_submit():
            # Update user profile
            profile = current_user.profile
            if not profile:
                profile = UserProfile(user_id=current_user.id)
                db.session.add(profile)
            
            profile.age = form.age.data
            profile.height = form.height.data
            profile.weight = form.weight.data
            profile.primary_sport_id = form.primary_sport.data
            profile.experience_level = form.experience_level.data
            
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('profile'))
        
        # Pre-populate form with existing data
        if current_user.profile:
            form.age.data = current_user.profile.age
            form.height.data = current_user.profile.height
            form.weight.data = current_user.profile.weight
            form.primary_sport.data = current_user.profile.primary_sport_id
            form.experience_level.data = current_user.profile.experience_level
        
        return render_template('profile.html', form=form)

    # Sports route
    @app.route('/sports')
    @login_required
    def sports():
        sports = Sport.query.all()
        return render_template('sports.html', sports=sports)

    # Training log route
    @app.route('/training-log', methods=['GET', 'POST'])
    @login_required
    def training_log():
        form = TrainingLogForm()
        # Set sport choices before validation
        form.sport.choices = [(s.id, s.name) for s in Sport.query.all()]
        
        if form.validate_on_submit():
            try:
                log = TrainingLog(
                    user_id=current_user.id,
                    sport_id=form.sport.data,
                    date=datetime.strptime(form.date.data, '%Y-%m-%d'),
                    duration=form.duration.data,
                    intensity=int(form.intensity.data),
                    notes=form.notes.data
                )
                
                db.session.add(log)
                db.session.commit()
                
                flash('Training log added successfully!', 'success')
                return redirect(url_for('dashboard'))
                
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error adding training log: {str(e)}")
                flash(f'Error adding training log: {str(e)}', 'error')
                return redirect(url_for('training_log'))
        
        return render_template('training_log.html', form=form)

    # Video upload route
    @app.route('/upload', methods=['GET', 'POST'])
    @login_required
    def upload():
        form = VideoUploadForm()
        # Set sport choices before validation
        form.sport.choices = [(s.id, s.name) for s in Sport.query.all()]
        
        if form.validate_on_submit():
            try:
                # Save the uploaded file
                video_file = form.video.data
                filename = secure_filename(video_file.filename)
                filepath = os.path.join(current_app.static_folder, 'uploads', filename)
                video_file.save(filepath)
                
                # Analyze the video
                analysis_results = analyze_video(filepath)
                
                # Create new analysis record
                analysis = VideoAnalysis(
                    user_id=current_user.id,
                    sport_id=form.sport.data,
                    filename=filename,
                    result=json.dumps(analysis_results),
                    timestamp=datetime.utcnow()
                )
                
                db.session.add(analysis)
                db.session.commit()
                
                flash('Video uploaded and analyzed successfully!', 'success')
                return redirect(url_for('analysis', analysis_id=analysis.id))
                
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error processing video: {str(e)}")
                flash(f'Error processing video: {str(e)}', 'error')
                return redirect(url_for('upload'))
        
        return render_template('upload.html', form=form)

    # Analysis route
    @app.route('/analysis/<int:analysis_id>')
    @login_required
    def analysis(analysis_id):
        try:
            analysis = VideoAnalysis.query.get_or_404(analysis_id)
            if analysis.user_id != current_user.id:
                flash('You do not have permission to view this analysis.', 'error')
                return redirect(url_for('index'))
            
            # Get the video file path
            video_path = os.path.join('uploads', analysis.filename)
            video_url = url_for('static', filename=video_path)
            
            # Parse the analysis data
            analysis_data = json.loads(analysis.result)
            
            # Get sport name
            sport = Sport.query.get(analysis.sport_id)
            
            # Analyze movement and get feedback
            feedback_text, recommendations = analyze_movement(analysis_data, sport.name)
            
            # Predict injury risk
            injury_risk = predict_injury_risk(analysis_data, current_user.id, sport.name)
            
            # Define injury risk recommendations
            INJURY_RECOMMENDATIONS = {
                'Low': 'Your form looks good! Keep up the good work and maintain proper technique.',
                'Medium': 'Some areas need attention. Focus on improving your form to reduce injury risk.',
                'High': 'Significant risk detected. Please consult with a coach or trainer to improve your technique.'
            }
            
            # Structure the data for the template
            result = {
                'feedback': [
                    {
                        'status': 'good',
                        'message': feedback_text
                    }
                ],
                'injury_risk': {
                    'risk_level': injury_risk.lower(),
                    'risk_percentage': 15 if injury_risk == 'Low' else 50 if injury_risk == 'Medium' else 85,
                    'message': INJURY_RECOMMENDATIONS.get(injury_risk, 'No specific recommendations available.'),
                    'recommendations': recommendations.split('\n') if recommendations else []
                }
            }
            
            # Update the analysis result with the structured data
            analysis.result = json.dumps(result)
            
            return render_template('analysis.html', 
                                 analysis=analysis,
                                 video_url=video_url)
                             
        except Exception as e:
            current_app.logger.error(f"Error displaying analysis: {str(e)}")
            flash('Error displaying analysis. Please try again.', 'error')
            return redirect(url_for('index'))

    # Progress route
    @app.route('/progress', methods=['GET', 'POST'])
    @login_required
    def progress():
        form = ProgressForm()
        if form.validate_on_submit():
            progress = Progress(
                user_id=current_user.id,
                sport_id=form.sport.data,
                metric_name=form.metric_name.data,
                metric_value=form.metric_value.data,
                unit=form.unit.data,
                date=form.date.data,
                notes=form.notes.data
            )
            db.session.add(progress)
            db.session.commit()
            flash('Progress recorded successfully!', 'success')
            return redirect(url_for('progress'))
        
        # Get all sports (they are shared among users)
        sports = Sport.query.all()
        
        # Get progress entries for the current user
        progress_entries = Progress.query.filter_by(user_id=current_user.id)\
            .order_by(Progress.date.desc())\
            .all()
        
        # Convert Sport objects to dictionaries
        serializable_sports = [{"id": sport.id, "name": sport.name} for sport in sports]
        
        return render_template('progress.html', 
                             form=form, 
                             progress_entries=progress_entries, 
                             sports=serializable_sports)

    # Progress chart data route
    @app.route('/progress/chart/<int:sport_id>/<metric_name>')
    @login_required
    def progress_chart(sport_id, metric_name):
        progress_entries = Progress.query.filter_by(
            user_id=current_user.id,
            sport_id=sport_id,
            metric_name=metric_name
        ).order_by(Progress.date.asc()).all()
        
        data = {
            'values': [entry.metric_value for entry in progress_entries],
            'dates': [entry.date.strftime('%Y-%m-%d') for entry in progress_entries],
            'unit': progress_entries[0].unit if progress_entries else None
        }
        
        return jsonify(data)

    # Video feed route
    @app.route('/video_feed')
    @login_required
    def video_feed():
        """Stream video feed with pose analysis."""
        return Response(generate_frames(),
                       mimetype='multipart/x-mixed-replace; boundary=frame')

    # Live analysis route
    @app.route('/live_analysis')
    @login_required
    def live_analysis():
        """Live analysis page."""
        return render_template('live_analysis.html')

    # Video analysis route
    @app.route('/video_analysis')
    @login_required
    def video_analysis():
        """Render the video analysis page."""
        # Initialize pose detector and camera
        if not init_pose_detector():
            flash('Failed to initialize pose detector', 'error')
        if not init_camera():
            flash('Failed to initialize camera', 'error')
        return render_template('video_analysis.html')

    # Add frame caching
    def get_frame_hash(frame):
        return hashlib.md5(frame.tobytes()).hexdigest()

    # Process frame in separate process
    def process_frame(frame):
        try:
            # Convert to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Process with MediaPipe
            results = pose.process(frame_rgb)
            
            if results.pose_landmarks:
                landmarks = []
                for landmark in results.pose_landmarks.landmark:
                    landmarks.append({
                        'x': landmark.x,
                        'y': landmark.y,
                        'z': landmark.z,
                        'visibility': landmark.visibility
                    })
                return landmarks
            return None
        except Exception as e:
            print(f"Error processing frame: {str(e)}")
            return None

    # Update the analyze_posture_route
    @app.route('/analyze_posture', methods=['POST'])
    @login_required
    def analyze_posture_route():
        """Analyze posture from video frame."""
        try:
            # Add a timestamp to prevent caching
            timestamp = datetime.now().isoformat()
            sport = request.form.get('sport', 'general')
            
            # Get image data or capture from camera
            image_data = request.form.get('image_data')
            frame = None
            
            if image_data:
                # Process image data from frontend
                try:
                    # Remove the data URI header
                    image_data = image_data.split(',')[1]
                    # Decode base64 image
                    image_bytes = base64.b64decode(image_data)
                    # Convert to numpy array
                    nparr = np.frombuffer(image_bytes, np.uint8)
                    # Decode into OpenCV frame
                    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                except Exception as e:
                    logger.error(f"Error processing image data: {str(e)}")
                    return jsonify({'error': 'Failed to process image data', 'timestamp': timestamp})
            else:
                # Use backend camera
                frame = get_frame()
                if frame is None:
                    return jsonify({'error': 'Failed to capture frame', 'timestamp': timestamp})
            
            # Process the frame and get landmarks
            landmarks = process_live_video(frame)
            
            if landmarks is None or len(landmarks) == 0:
                return jsonify({'error': 'No pose detected', 'timestamp': timestamp})
            
            # Convert landmarks to a format suitable for drawing
            formatted_landmarks = []
            for i, landmark in enumerate(landmarks):
                formatted_landmarks.append({
                    'x': float(landmark[0]),  # Normalize to 0-1 range
                    'y': float(landmark[1]),
                    'z': float(landmark[2]),
                    'visibility': float(landmark[3]),
                    'index': i  # Add index for connection mapping
                })
            
            # Analyze posture with the landmarks
            feedback = analyze_posture(landmarks, sport)
            
            # Format feedback
            formatted_feedback = []
            for message, status in feedback:
                status_map = {"green": "good", "yellow": "warning", "red": "error"}
                formatted_status = status_map.get(status.lower(), "info")
                formatted_feedback.append({
                    "status": formatted_status,
                    "message": message
                })
            
            # Add timestamp to response to prevent caching
            return jsonify({
                'feedback': formatted_feedback,
                'landmarks': formatted_landmarks,
                'timestamp': timestamp
            })
            
        except Exception as e:
            logger.error(f"Error in analyze_posture_route: {str(e)}")
            return jsonify({'error': str(e), 'timestamp': timestamp})

    # Error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('500.html'), 500

    @app.teardown_appcontext
    def shutdown_camera(exception=None):
        """Release camera resources when app shuts down."""
        release_camera()

# Initialize the property
process_live_video.prev_landmarks = None
