// Analysis page functionality

document.addEventListener('DOMContentLoaded', function() {
    // Initialize visualization
    initVisualization();
    
    // Set up playback controls
    setupPlaybackControls();
});

// Initialize visualization of pose data
function initVisualization() {
    const visualizationCanvas = document.getElementById('poseVisualization');
    const videoElement = document.getElementById('analysisVideo');
    
    if (!visualizationCanvas || !videoElement) return;
    
    // Get pose data from the page
    const poseDataElement = document.getElementById('poseData');
    
    if (!poseDataElement) return;
    
    let poseData;
    try {
        poseData = JSON.parse(poseDataElement.textContent);
    } catch (e) {
        console.error('Error parsing pose data:', e);
        return;
    }
    
    if (!poseData || !poseData.pose_data) {
        visualizationCanvas.style.display = 'none';
        return;
    }
    
    // Set up canvas
    const ctx = visualizationCanvas.getContext('2d');
    const canvasWidth = visualizationCanvas.width;
    const canvasHeight = visualizationCanvas.height;
    
    // Draw function for pose data
    function drawPose(frameIdx) {
        // Clear canvas
        ctx.clearRect(0, 0, canvasWidth, canvasHeight);
        
        // Get landmarks for the current frame
        const landmarks = poseData.pose_data[frameIdx];
        
        if (!landmarks) return;
        
        // Draw connections (skeleton)
        drawSkeleton(ctx, landmarks, canvasWidth, canvasHeight);
        
        // Draw landmarks
        drawLandmarks(ctx, landmarks, canvasWidth, canvasHeight);
    }
    
    // Draw initial frame
    const firstFrameIdx = Object.keys(poseData.pose_data)[0];
    if (firstFrameIdx) {
        drawPose(firstFrameIdx);
    }
    
    // Update visualization based on video playback
    videoElement.addEventListener('timeupdate', function() {
        const currentTime = videoElement.currentTime;
        const duration = videoElement.duration;
        
        if (isNaN(duration) || duration === 0) return;
        
        // Find closest frame based on current time
        const framePercent = currentTime / duration;
        const keyFrames = poseData.metadata.key_frames;
        
        const closestFrameIdx = keyFrames[Math.floor(framePercent * keyFrames.length)];
        
        if (closestFrameIdx && poseData.pose_data[closestFrameIdx]) {
            drawPose(closestFrameIdx);
        }
    });
}

// Draw skeleton connections between landmarks
function drawSkeleton(ctx, landmarks, canvasWidth, canvasHeight) {
    // Define connections as pairs of landmark indices
    const connections = [
        // Torso
        [11, 12], // Left shoulder to right shoulder
        [11, 23], // Left shoulder to left hip
        [12, 24], // Right shoulder to right hip
        [23, 24], // Left hip to right hip
        
        // Left arm
        [11, 13], // Left shoulder to left elbow
        [13, 15], // Left elbow to left wrist
        
        // Right arm
        [12, 14], // Right shoulder to right elbow
        [14, 16], // Right elbow to right wrist
        
        // Left leg
        [23, 25], // Left hip to left knee
        [25, 27], // Left knee to left ankle
        
        // Right leg
        [24, 26], // Right hip to right knee
        [26, 28], // Right knee to right ankle
    ];
    
    // Draw each connection
    connections.forEach(([startIdx, endIdx]) => {
        const start = landmarks[startIdx];
        const end = landmarks[endIdx];
        
        if (start && end) {
            ctx.beginPath();
            ctx.moveTo(start.x * canvasWidth, start.y * canvasHeight);
            ctx.lineTo(end.x * canvasWidth, end.y * canvasHeight);
            ctx.strokeStyle = '#00ff00';
            ctx.lineWidth = 2;
            ctx.stroke();
        }
    });
}

// Draw landmarks and angles
function drawLandmarks(ctx, landmarks, canvasWidth, canvasHeight) {
    // Draw each landmark
    landmarks.forEach((landmark, index) => {
        if (landmark) {
            ctx.beginPath();
            ctx.arc(
                landmark.x * canvasWidth,
                landmark.y * canvasHeight,
                3,
                0,
                2 * Math.PI
            );
            ctx.fillStyle = '#ff0000';
            ctx.fill();
        }
    });
    
    // Draw angles
    const drawAngle = (p1, p2, p3, label) => {
        if (p1 && p2 && p3) {
            const angle = calculateAngle(p1, p2, p3);
            const x = p2.x * canvasWidth;
            const y = p2.y * canvasHeight;
            
            ctx.fillStyle = '#ffffff';
            ctx.font = '12px Arial';
            ctx.fillText(`${label}: ${angle.toFixed(1)}°`, x, y);
        }
    };
    
    // Draw key angles
    drawAngle(landmarks[11], landmarks[13], landmarks[15], 'Left Elbow');
    drawAngle(landmarks[12], landmarks[14], landmarks[16], 'Right Elbow');
    drawAngle(landmarks[13], landmarks[11], landmarks[23], 'Left Shoulder');
    drawAngle(landmarks[14], landmarks[12], landmarks[24], 'Right Shoulder');
    drawAngle(landmarks[23], landmarks[25], landmarks[27], 'Left Knee');
    drawAngle(landmarks[24], landmarks[26], landmarks[28], 'Right Knee');
}

// Calculate angle between three points
function calculateAngle(p1, p2, p3) {
    const v1 = { x: p1.x - p2.x, y: p1.y - p2.y };
    const v2 = { x: p3.x - p2.x, y: p3.y - p2.y };
    
    const dotProduct = v1.x * v2.x + v1.y * v2.y;
    const magnitude1 = Math.sqrt(v1.x * v1.x + v1.y * v1.y);
    const magnitude2 = Math.sqrt(v2.x * v2.x + v2.y * v2.y);
    
    const angle = Math.acos(dotProduct / (magnitude1 * magnitude2));
    return angle * (180 / Math.PI);
}

// Set up video playback controls
function setupPlaybackControls() {
    const video = document.getElementById('analysisVideo');
    const playPauseBtn = document.getElementById('playPauseBtn');
    const speedBtns = document.querySelectorAll('.speed-btn');
    
    if (!video || !playPauseBtn) return;
    
    // Play/pause button
    playPauseBtn.addEventListener('click', function() {
        if (video.paused) {
            video.play();
            playPauseBtn.innerHTML = '<i class="fas fa-pause"></i>';
        } else {
            video.pause();
            playPauseBtn.innerHTML = '<i class="fas fa-play"></i>';
        }
    });
    
    // Speed control buttons
    speedBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const speed = parseFloat(this.dataset.speed);
            video.playbackRate = speed;
            
            // Update button states
            speedBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
        });
    });
    
    // Update play/pause button when video ends
    video.addEventListener('ended', function() {
        playPauseBtn.innerHTML = '<i class="fas fa-play"></i>';
    });
}

// Update speed button states
function updateSpeedButtonStates(activeBtn, inactiveBtn) {
    activeBtn.classList.add('active');
    inactiveBtn.classList.remove('active');
}
