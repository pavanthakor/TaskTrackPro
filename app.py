import os
import logging
from datetime import datetime
from flask import Flask, session, render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_login import LoginManager
from flask_socketio import SocketIO, emit
import json

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize extensions
login_manager = LoginManager()
socketio = SocketIO(cors_allowed_origins="*", async_mode='threading')

def create_app():
    # create the app
    app = Flask(__name__)
    app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    # Configure SQLite database
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///sports_coach.db")
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max file size
    app.config["UPLOAD_FOLDER"] = os.path.join(app.static_folder, "uploads")
    
    # Ensure upload directory exists
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Import models and initialize db
    from models import db, User, UserProfile, TrainingLog, VideoAnalysis, Sport
    db.init_app(app)
    
    # Initialize other extensions
    login_manager.init_app(app)
    socketio.init_app(app)

    # Configure Flask-Login
    login_manager.login_view = "login"
    login_manager.login_message_category = "info"

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Add from_json filter
    @app.template_filter('from_json')
    def from_json_filter(value):
        try:
            return json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return {}

    # Import and register routes
    from routes import register_routes
    register_routes(app)

    # Create database tables
    with app.app_context():
        db.create_all()

        # Initialize default sports if not exists
        sports = ["Basketball", "Tennis", "Football", "Badminton", "Running"]
        existing_sports = Sport.query.all()
        
        if not existing_sports:
            for sport_name in sports:
                sport = Sport(name=sport_name)
                db.session.add(sport)
            db.session.commit()
            logger.info("Default sports added to database")

    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('500.html'), 500

    # Socket.IO event handlers
    @socketio.on('connect')
    def handle_connect():
        logger.info('Client connected')
        emit('connection_response', {'status': 'connected'})

    @socketio.on('disconnect')
    def handle_disconnect():
        logger.info('Client disconnected')

    # Frame counter for skipping frames
    frame_counter = 0
    SKIP_FRAMES = 2  # Process every 3rd frame

    @socketio.on('pose_data')
    def handle_pose_data(data):
        global frame_counter
        try:
            # Skip frames to reduce processing load
            frame_counter += 1
            if frame_counter % (SKIP_FRAMES + 1) != 0:
                return

            landmarks = data.get('landmarks')
            sport = data.get('sport')
            analysis_type = data.get('analysis_type')
            
            if not landmarks or not sport or not analysis_type:
                emit('error', {'message': 'Missing required data'})
                return
                
            # Process the pose data
            from pose_estimation import analyze_pose
            analysis_result = analyze_pose(landmarks, sport, analysis_type)
            
            # Emit the analysis result back to the client
            emit('analysis_result', {
                'result': analysis_result,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f'Error processing pose data: {str(e)}')
            emit('error', {'message': f'Error processing pose data: {str(e)}'})

    return app

if __name__ == '__main__':
    app = create_app()
    socketio.run(app, debug=True)
