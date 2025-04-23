# Ai sports coach - Sports Training and Analysis Platform

AI sports coach is a comprehensive web application designed to help athletes and coaches track, analyze, and improve sports performance through real-time pose estimation and analysis.

## Features

- **User Management**
  - User registration and authentication
  - Profile management with personal details
  - Experience level tracking
  - Primary sport selection

- **Sports Training**
  - Support for multiple sports (Basketball, Tennis, Football, Badminton, Running)
  - Training log tracking
  - Duration and intensity monitoring
  - Notes and progress tracking

- **Real-time Pose Analysis**
  - Live pose estimation using MediaPipe
  - Sport-specific form analysis
  - Real-time feedback
  - Performance metrics tracking

- **Video Analysis**
  - Upload and analyze training videos
  - Store analysis results
  - Track progress over time

- **Progress Tracking**
  - Custom metrics for different sports
  - Historical data visualization
  - Performance trends analysis

## Technical Stack

- **Backend**
  - Flask (Python web framework)
  - SQLAlchemy (ORM)
  - Flask-Login (Authentication)
  - Flask-SocketIO (Real-time communication)
  - MediaPipe (Pose estimation)
  - OpenCV (Computer vision)

- **Frontend**
  - HTML/CSS/JavaScript
  - WebSocket for real-time updates
  - Modern responsive design

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/TaskTrackPro.git
cd TaskTrackPro
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
# Create a .env file with the following variables
SESSION_SECRET=your_secret_key
DATABASE_URL=sqlite:///sports_coach.db  # or your preferred database URL
```

5. Initialize the database:
```bash
python app.py
```

## Usage

1. Start the application:
```bash
python app.py
```

2. Access the application at `http://localhost:5000`

3. Register a new account or log in with existing credentials

4. Set up your profile with your primary sport and experience level

5. Start tracking your training sessions and analyzing your performance

## Project Structure

```
TaskTrackPro/
├── app.py              # Main application file
├── models.py           # Database models
├── routes.py           # Route definitions
├── forms.py            # Form definitions
├── pose_estimation.py  # Pose estimation logic
├── pose_analysis.py    # Pose analysis algorithms
├── analysis.py         # General analysis functions
├── static/            # Static files (CSS, JS, images)
├── templates/         # HTML templates
└── requirements.txt   # Project dependencies
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- MediaPipe for pose estimation capabilities
- Flask community for the excellent web framework
- All contributors who have helped shape this project

## Support

For support, please open an issue in the GitHub repository or contact the maintainers. 
