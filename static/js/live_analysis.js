// Configuration variables
const config = {
    processingMode: 'client-side',  // Try 'client-side' or 'server-side'
    captureInterval: 50,            // How often to capture frames (ms)
    skipFrames: 1,                  // Process every N frames
    imageQuality: 0.6,              // JPEG quality for server transmission
    predictionEnabled: true,        // Enable movement prediction
    useWebWorker: true              // Process in background thread
};

// Frame processing variables
let processingQueue = [];
let isProcessing = false;
let lastProcessedTime = 0;
let analysisActive = false;
let videoStreamActive = false;
let videoElement = null;
let skeletonCanvas = null;
let skeletonCtx = null;

// Variables for tracking video stream state
let videoInitAttempts = 0;
const MAX_VIDEO_INIT_ATTEMPTS = 5;

// Function to update feedback display
function updateFeedback(feedbackData) {
    const feedbackContainer = document.getElementById('feedbackContainer');
    if (!feedbackContainer) return;
    
    let feedbackHtml = '';
    
    if (feedbackData && feedbackData.length > 0) {
        feedbackHtml = '<ul class="list-group">';
        feedbackData.forEach(item => {
            const statusClass = item.status === 'good' ? 'success' : 
                              item.status === 'warning' ? 'warning' : 
                              item.status === 'error' ? 'danger' : 'info';
            
            feedbackHtml += `
                <li class="list-group-item list-group-item-${statusClass}">
                    <i class="fas ${item.status === 'good' ? 'fa-check-circle' : 
                                  item.status === 'warning' ? 'fa-exclamation-triangle' : 
                                  'fa-exclamation-circle'}"></i>
                    ${item.message}
                </li>
            `;
        });
        feedbackHtml += '</ul>';
    } else {
        feedbackHtml = '<div class="alert alert-info">Waiting for movement analysis...</div>';
    }
    
    feedbackContainer.innerHTML = feedbackHtml;
}

// Function to draw skeleton
function drawSkeleton(landmarks) {
    if (!skeletonCanvas || !skeletonCtx) return;
    
    // Clear previous skeleton
    skeletonCtx.clearRect(0, 0, skeletonCanvas.width, skeletonCanvas.height);
    
    // Set drawing style
    skeletonCtx.strokeStyle = '#00ff00';
    skeletonCtx.lineWidth = 2;
    
    // Draw connections between landmarks
    const connections = [
        // Torso
        [11, 12], [12, 24], [24, 23], [23, 11],
        // Left arm
        [11, 13], [13, 15],
        // Right arm
        [12, 14], [14, 16],
        // Left leg
        [23, 25], [25, 27],
        // Right leg
        [24, 26], [26, 28]
    ];
    
    connections.forEach(connection => {
        const [start, end] = connection;
        if (landmarks[start] && landmarks[end]) {
            skeletonCtx.beginPath();
            skeletonCtx.moveTo(
                landmarks[start].x * skeletonCanvas.width,
                landmarks[start].y * skeletonCanvas.height
            );
            skeletonCtx.lineTo(
                landmarks[end].x * skeletonCanvas.width,
                landmarks[end].y * skeletonCanvas.height
            );
            skeletonCtx.stroke();
        }
    });
    
    // Draw landmarks
    landmarks.forEach(landmark => {
        if (landmark.visibility > 0.5) {
            skeletonCtx.beginPath();
            skeletonCtx.arc(
                landmark.x * skeletonCanvas.width,
                landmark.y * skeletonCanvas.height,
                3,
                0,
                2 * Math.PI
            );
            skeletonCtx.fillStyle = '#00ff00';
            skeletonCtx.fill();
        }
    });
}

// Function to properly initialize video stream
function initVideoStream() {
    videoElement = document.getElementById('video-element');
    const canvasElement = document.getElementById('output-canvas');
    const ctx = canvasElement.getContext('2d');
    skeletonCanvas = document.getElementById('skeletonCanvas');
    skeletonCtx = skeletonCanvas.getContext('2d');
    
    // Reset video stream if it exists
    if (videoStreamActive) {
        stopVideoStream();
    }
    
    if (videoInitAttempts >= MAX_VIDEO_INIT_ATTEMPTS) {
        console.error("Failed to initialize video after multiple attempts");
        showErrorMessage("Could not access camera. Please check your camera permissions and try refreshing the page.");
        return false;
    }
    
    try {
        console.log("Starting video stream");
        
        // Request camera access with constraints
        navigator.mediaDevices.getUserMedia({ 
            video: { 
                width: { ideal: 640 },
                height: { ideal: 480 },
                frameRate: { ideal: 30 },
                facingMode: "user"
            },
            audio: false 
        })
        .then(function(stream) {
            videoElement.srcObject = stream;
            videoStreamActive = true;
            videoInitAttempts = 0;
            
            // Make video element visible
            videoElement.style.display = 'block';
            
            // Wait for video to be ready
            videoElement.onloadedmetadata = function(e) {
                console.log("Video stream started successfully");
                videoElement.play();
                
                // Set canvas dimensions
                canvasElement.width = videoElement.videoWidth;
                canvasElement.height = videoElement.videoHeight;
                skeletonCanvas.width = videoElement.videoWidth;
                skeletonCanvas.height = videoElement.videoHeight;
                
                // Start the video rendering loop
                function renderVideoLoop() {
                    if (videoElement.readyState === videoElement.HAVE_ENOUGH_DATA) {
                        // Draw the video frame
                        ctx.drawImage(videoElement, 0, 0, canvasElement.width, canvasElement.height);
                    }
                    requestAnimationFrame(renderVideoLoop);
                }
                
                renderVideoLoop();
                
                // Start analysis after video is ready
                if (analysisActive) {
                    startAnalysis();
                }
            };
            
            return true;
        })
        .catch(function(err) {
            console.error("Error accessing camera: ", err);
            videoInitAttempts++;
            showErrorMessage("Camera access error: " + err.message);
            return false;
        });
    } catch (error) {
        console.error("Exception initializing video: ", error);
        videoInitAttempts++;
        return false;
    }
}

// Function to properly stop video stream
function stopVideoStream() {
    if (videoElement && videoElement.srcObject) {
        let tracks = videoElement.srcObject.getTracks();
        tracks.forEach(track => {
            track.stop();
            console.log("Stopped video track:", track.kind);
        });
        videoElement.srcObject = null;
        videoStreamActive = false;
        videoElement.style.display = 'none';
        
        // Clear the canvases
        const canvas = document.getElementById('output-canvas');
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        if (skeletonCanvas && skeletonCtx) {
            skeletonCtx.clearRect(0, 0, skeletonCanvas.width, skeletonCanvas.height);
        }
        
        console.log("Video stream stopped and cleaned up");
    }
}

// Capture and analyze frames
function captureAndAnalyze() {
    if (!analysisActive) return;
    
    const currentTime = performance.now();
    const timeSinceLastProcess = currentTime - lastProcessedTime;
    
    // Check if we should process this frame
    if (processingQueue.length === 0 && timeSinceLastProcess >= config.captureInterval) {
        lastProcessedTime = currentTime;
        
        // Capture frame
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('2d');
        canvas.width = videoElement.videoWidth;
        canvas.height = videoElement.videoHeight;
        context.drawImage(videoElement, 0, 0, canvas.width, canvas.height);
        
        // Reduce resolution for faster processing
        const scaleFactor = 0.5;
        const scaledCanvas = document.createElement('canvas');
        scaledCanvas.width = canvas.width * scaleFactor;
        scaledCanvas.height = canvas.height * scaleFactor;
        const scaledContext = scaledCanvas.getContext('2d');
        scaledContext.drawImage(canvas, 0, 0, scaledCanvas.width, scaledCanvas.height);
        
        // Add to processing queue
        const imageData = scaledCanvas.toDataURL('image/jpeg', config.imageQuality);
        processingQueue.push({
            imageData: imageData,
            timestamp: currentTime
        });
        
        // Process queue if not already processing
        if (!isProcessing) {
            processNextInQueue();
        }
    }
    
    // Request next frame
    requestAnimationFrame(captureAndAnalyze);
}

// Process frames in queue
function processNextInQueue() {
    if (processingQueue.length === 0) {
        isProcessing = false;
        return;
    }
    
    isProcessing = true;
    const frameToProcess = processingQueue.shift();
    
    // Clear queue backlog
    if (processingQueue.length > 1) {
        processingQueue = [processingQueue[processingQueue.length - 1]];
    }
    
    // Get selected sport
    const sportSelect = document.getElementById('sportSelect');
    const selectedSport = sportSelect ? sportSelect.value : 'general';
    
    // Send to server for processing
    fetch('/analyze_posture', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({
            'image_data': frameToProcess.imageData,
            'sport': selectedSport
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            console.error("Error from analyze_posture:", data.error);
            clearSkeleton();
        } else if (data.landmarks && data.landmarks.length > 0) {
            drawSkeleton(data.landmarks);
            if (data.feedback && data.feedback.length > 0) {
                updateFeedback(data.feedback);
            }
        }
        
        // Process next frame
        processNextInQueue();
    })
    .catch(error => {
        console.error("Fetch error:", error);
        clearSkeleton();
        processNextInQueue();
    });
}

// Clear skeleton
function clearSkeleton() {
    if (skeletonCanvas && skeletonCtx) {
        skeletonCtx.clearRect(0, 0, skeletonCanvas.width, skeletonCanvas.height);
    }
}

// Start analysis
function startAnalysis() {
    if (!analysisActive) {
        analysisActive = true;
        processingQueue = [];
        lastProcessedTime = 0;
        
        // Update UI
        const startButton = document.getElementById('startAnalysis');
        const stopButton = document.getElementById('stopAnalysis');
        if (startButton) startButton.style.display = 'none';
        if (stopButton) stopButton.style.display = 'inline-block';
        
        // Start capture loop
        captureAndAnalyze();
    }
}

// Stop analysis
function stopAnalysis() {
    analysisActive = false;
    processingQueue = [];
    isProcessing = false;
    
    // Stop video stream
    stopVideoStream();
    
    // Update UI
    const startButton = document.getElementById('startAnalysis');
    const stopButton = document.getElementById('stopAnalysis');
    if (startButton) startButton.style.display = 'inline-block';
    if (stopButton) stopButton.style.display = 'none';
    
    // Clear feedback
    const feedbackContainer = document.getElementById('feedbackContainer');
    if (feedbackContainer) {
        feedbackContainer.innerHTML = `
            <div class="alert alert-info">
                Analysis stopped. Click "Start Analysis" to begin again.
            </div>
        `;
    }
    
    console.log("Analysis stopped and UI reset");
}

// Show error message to user
function showErrorMessage(message) {
    const feedbackContainer = document.getElementById('feedbackContainer');
    if (feedbackContainer) {
        feedbackContainer.innerHTML = `
            <div class="alert alert-danger">
                <strong>Error:</strong> ${message}
                <button type="button" class="btn btn-primary mt-2" onclick="initVideoStream()">
                    Retry Camera
                </button>
            </div>
        `;
    }
}

// Initialize everything when page loads
document.addEventListener('DOMContentLoaded', function() {
    initVideoStream();
    
    // Add event listeners
    const startButton = document.getElementById('startAnalysis');
    const stopButton = document.getElementById('stopAnalysis');
    
    if (startButton) {
        startButton.addEventListener('click', startAnalysis);
    }
    
    if (stopButton) {
        stopButton.addEventListener('click', stopAnalysis);
    }
    
    // Clean up when page is unloaded
    window.addEventListener('beforeunload', function() {
        stopAnalysis();
        stopVideoStream();
    });
}); 