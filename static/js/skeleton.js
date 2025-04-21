// Define pose connections for drawing the skeleton
const POSE_CONNECTIONS = [
    // Face connections
    [0, 1], [1, 2], [2, 3], [3, 4],  // Right face
    [0, 5], [5, 6], [6, 7], [7, 8],  // Left face
    [0, 9], [9, 10],                 // Mid face
    
    // Upper body connections
    [11, 12], [11, 13], [13, 15],    // Left arm
    [12, 14], [14, 16],              // Right arm
    [11, 23], [12, 24],              // Torso
    
    // Lower body connections
    [23, 24], [23, 25], [25, 27],    // Left leg
    [24, 26], [26, 28],              // Right leg
    
    // Hands
    [15, 17], [15, 19], [15, 21],    // Left hand
    [16, 18], [16, 20], [16, 22]     // Right hand
];

// Motion prediction variables
let lastLandmarks = null;
let prevTimestamp = null;
const smoothingFactor = 0.3; // Lower = smoother but more lag, higher = more responsive but jittery

// Draw skeleton on video with motion prediction
function drawSkeleton(landmarks) {
    if (!videoElement || !landmarks || landmarks.length === 0) return;
    
    const currentTime = performance.now();
    
    // Apply motion prediction if we have previous landmarks
    if (lastLandmarks && prevTimestamp) {
        const timeDelta = currentTime - prevTimestamp;
        const predictionFactor = Math.min(timeDelta / 33, 1.0) * smoothingFactor; // Normalize for ~30fps
        
        // Predict landmark positions based on their velocity
        for (let i = 0; i < landmarks.length; i++) {
            if (landmarks[i] && lastLandmarks[i] && landmarks[i].visibility > 0.5 && lastLandmarks[i].visibility > 0.5) {
                // Calculate predicted position
                const dx = landmarks[i].x - lastLandmarks[i].x;
                const dy = landmarks[i].y - lastLandmarks[i].y;
                
                // Apply prediction with smoothing
                landmarks[i].x += dx * predictionFactor;
                landmarks[i].y += dy * predictionFactor;
            }
        }
    }
    
    // Create canvas if needed
    let canvas = document.getElementById('skeletonCanvas');
    if (!canvas) {
        canvas = document.createElement('canvas');
        canvas.id = 'skeletonCanvas';
        canvas.style.position = 'absolute';
        canvas.style.top = '0';
        canvas.style.left = '0';
        canvas.style.pointerEvents = 'none';
        
        const videoContainer = videoElement.parentElement;
        videoContainer.style.position = 'relative';
        videoContainer.insertBefore(canvas, videoElement.nextSibling);
    }
    
    // Match canvas size to video
    const displayWidth = videoElement.offsetWidth;
    const displayHeight = videoElement.offsetHeight;
    
    // Update canvas size if needed
    if (canvas.width !== displayWidth || canvas.height !== displayHeight) {
        canvas.width = displayWidth;
        canvas.height = displayHeight;
    }
    
    // Get drawing context and clear previous frame
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Draw connections with improved rendering
    ctx.lineWidth = 3;
    ctx.strokeStyle = '#00FF00';
    ctx.fillStyle = '#00FF00';
    
    // Using optimized batched rendering
    ctx.beginPath();
    for (const [i, j] of POSE_CONNECTIONS) {
        if (landmarks[i] && landmarks[j] && landmarks[i].visibility > 0.5 && landmarks[j].visibility > 0.5) {
            const x1 = landmarks[i].x * displayWidth;
            const y1 = landmarks[i].y * displayHeight;
            const x2 = landmarks[j].x * displayWidth;
            const y2 = landmarks[j].y * displayHeight;
            
            ctx.moveTo(x1, y1);
            ctx.lineTo(x2, y2);
        }
    }
    ctx.stroke();
    
    // Draw landmark points
    for (const landmark of landmarks) {
        if (landmark.visibility > 0.5) {
            const x = landmark.x * displayWidth;
            const y = landmark.y * displayHeight;
            
            ctx.beginPath();
            ctx.arc(x, y, 5, 0, 2 * Math.PI);
            ctx.fill();
        }
    }
    
    // Store current landmarks for next prediction
    lastLandmarks = JSON.parse(JSON.stringify(landmarks));
    prevTimestamp = currentTime;
}

// Clear the skeleton
function clearSkeleton() {
    const canvas = document.getElementById('skeletonCanvas');
    if (canvas) {
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
    // Reset motion prediction variables
    lastLandmarks = null;
    prevTimestamp = null;
}

// Add resize event listener to adjust canvas when window is resized
window.addEventListener('resize', function() {
    // Redraw skeleton if active
    const canvas = document.getElementById('skeletonCanvas');
    if (canvas && videoStreamActive && analysisActive) {
        // We need to resize the canvas and redraw
        canvas.width = videoElement.offsetWidth;
        canvas.height = videoElement.offsetHeight;
        
        // Clear existing drawing
        clearSkeleton();
    }
}); 