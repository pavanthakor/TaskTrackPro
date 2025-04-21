from app import create_app, socketio
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    app = create_app()
    logger.info("Starting Flask application with Socket.IO...")
    logger.info("Access the application at: http://localhost:8080 or http://127.0.0.1:8080")
    socketio.run(app, host="0.0.0.0", port=8080, debug=True, allow_unsafe_werkzeug=True)
