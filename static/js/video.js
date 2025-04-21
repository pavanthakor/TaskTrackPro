// Video upload and recording functionality

document.addEventListener('DOMContentLoaded', function() {
    // Video file input handling
    setupVideoFileInput();
    
    // Video recording functionality
    setupVideoRecording();
    
    // Form validation
    const uploadForm = document.getElementById('videoUploadForm');
    if (uploadForm) {
        uploadForm.addEventListener('submit', function(event) {
            if (!validateVideoForm()) {
                event.preventDefault();
            }
        });
    }
});

// Handle video file input changes
function setupVideoFileInput() {
    const videoInput = document.getElementById('video');
    const videoPreview = document.getElementById('videoPreview');
    const videoContainer = document.getElementById('videoContainer');
    const uploadPlaceholder = document.getElementById('uploadPlaceholder');
    
    if (!videoInput) return;
    
    videoInput.addEventListener('change', function(event) {
        const file = event.target.files[0];
        
        if (file) {
            // Check if file is a video
            if (!file.type.match('video.*')) {
                alert('Please select a valid video file');
                videoInput.value = '';
                return;
            }
            
            // Check file size (max 16MB)
            if (file.size > 16 * 1024 * 1024) {
                alert('Video file is too large. Maximum size is 16MB.');
                videoInput.value = '';
                return;
            }
            
            // Create object URL for preview
            const videoURL = URL.createObjectURL(file);
            
            if (uploadPlaceholder) {
                uploadPlaceholder.style.display = 'none';
            }
            
            if (videoPreview) {
                videoPreview.src = videoURL;
                videoPreview.style.display = 'block';
                videoPreview.controls = true;
                
                videoPreview.addEventListener('loadedmetadata', function() {
                    if (!isNaN(videoPreview.duration) && videoPreview.duration > 120) {
                        alert('Video is too long. Maximum duration is 2 minutes.');
                        videoInput.value = '';
                        videoPreview.src = '';
                        videoPreview.style.display = 'none';
                        if (uploadPlaceholder) {
                            uploadPlaceholder.style.display = 'flex';
                        }
                        URL.revokeObjectURL(videoURL);
                        return;
                    }
                });

                // Revoke the object URL after usage
                videoPreview.addEventListener('ended', function() {
                    URL.revokeObjectURL(videoURL);
                });
            }
        } else {
            // No file selected, reset UI
            if (videoPreview) {
                videoPreview.src = '';
                videoPreview.style.display = 'none';
            }
            
            if (uploadPlaceholder) {
                uploadPlaceholder.style.display = 'flex';
            }
        }
    });
}

// Set up video recording functionality
function setupVideoRecording() {
    const recordButton = document.getElementById('recordButton');
    const videoPreview = document.getElementById('videoPreview');
    const videoInput = document.getElementById('video');
    const uploadPlaceholder = document.getElementById('uploadPlaceholder');
    
    if (!recordButton || !videoPreview || !videoInput) return;
    
    if (!window.MediaRecorder) {
        alert('Recording is not supported in this browser.');
        return;
    }
    
    let mediaRecorder;
    let recordedChunks = [];
    let stream;
    
    recordButton.addEventListener('click', function() {
        if (mediaRecorder && mediaRecorder.state === 'recording') {
            // Stop recording
            mediaRecorder.stop();
            recordButton.textContent = 'Record Video';
            recordButton.classList.remove('btn-danger');
            recordButton.classList.add('btn-primary');
            
            if (stream) {
                stream.getTracks().forEach(track => track.stop());
            }
        } else {
            // Start recording
            navigator.mediaDevices.getUserMedia({ video: true, audio: true })
                .then(function(mediaStream) {
                    stream = mediaStream;
                    videoPreview.srcObject = mediaStream;
                    videoPreview.style.display = 'block';
                    videoPreview.play();
                    
                    if (uploadPlaceholder) {
                        uploadPlaceholder.style.display = 'none';
                    }
                    
                    // Start recording
                    mediaRecorder = new MediaRecorder(mediaStream);
                    recordedChunks = [];
                    
                    mediaRecorder.addEventListener('dataavailable', function(e) {
                        if (e.data.size > 0) {
                            recordedChunks.push(e.data);
                        }
                    });
                    
                    mediaRecorder.addEventListener('stop', function() {
                        // Create blob from recorded chunks
                        const blob = new Blob(recordedChunks, { type: 'video/webm' });
                        
                        // Create a File object from the Blob
                        const now = new Date();
                        const fileName = `recorded_video_${now.getTime()}.webm`;
                        const file = new File([blob], fileName, { type: 'video/webm' });
                        
                        // Create a FileList-like object
                        const dataTransfer = new DataTransfer();
                        dataTransfer.items.add(file);
                        
                        // Set the file input's files
                        videoInput.files = dataTransfer.files;
                        
                        // Update preview
                        videoPreview.srcObject = null;
                        const objectURL = URL.createObjectURL(blob);
                        videoPreview.src = objectURL;
                        videoPreview.controls = true;
                        
                        // Trigger change event on file input
                        const event = document.createEvent('HTMLEvents');
                        event.initEvent('change', true, false);
                        videoInput.dispatchEvent(event);

                        // Revoke URL on unload or video end
                        videoPreview.addEventListener('ended', () => URL.revokeObjectURL(objectURL));
                    });
                    
                    mediaRecorder.start();
                    recordButton.textContent = 'Stop Recording';
                    recordButton.classList.remove('btn-primary');
                    recordButton.classList.add('btn-danger');
                })
                .catch(function(err) {
                    console.error('Error accessing media devices:', err);
                    alert('Could not access camera. Please check permissions or use file upload instead.');
                });
        }
    });
}

// Validate video upload form
function validateVideoForm() {
    const sportSelect = document.getElementById('sport');
    const videoInput = document.getElementById('video');
    let isValid = true;
    
    // Validate sport selection
    if (sportSelect && (!sportSelect.value || sportSelect.value === '0')) {
        sportSelect.classList.add('is-invalid');
        isValid = false;
        
        // Add error message
        let errorDiv = sportSelect.nextElementSibling;
        if (!errorDiv || !errorDiv.classList.contains('invalid-feedback')) {
            errorDiv = document.createElement('div');
            errorDiv.classList.add('invalid-feedback');
            sportSelect.parentNode.insertBefore(errorDiv, sportSelect.nextSibling);
        }
        errorDiv.textContent = 'Please select a sport';
    } else if (sportSelect) {
        sportSelect.classList.remove('is-invalid');
    }
    
    // Validate video file
    if (videoInput && (!videoInput.files || videoInput.files.length === 0)) {
        videoInput.classList.add('is-invalid');
        isValid = false;
        
        // Add error message
        let errorDiv = videoInput.nextElementSibling;
        if (!errorDiv || !errorDiv.classList.contains('invalid-feedback')) {
            errorDiv = document.createElement('div');
            errorDiv.classList.add('invalid-feedback');
            videoInput.parentNode.insertBefore(errorDiv, videoInput.nextSibling);
        }
        errorDiv.textContent = 'Please select or record a video';
    } else if (videoInput) {
        videoInput.classList.remove('is-invalid');
    }
    
    return isValid;
}
