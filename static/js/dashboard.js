// Dashboard functionality

document.addEventListener('DOMContentLoaded', function() {
    // Initialize charts
    initDashboardCharts();
    
    // Load recent activity
    loadRecentActivity();
});

// Initialize dashboard charts
function initDashboardCharts() {
    initTrainingIntensityChart();
    initRiskFactorChart();
}

// Training intensity chart
function initTrainingIntensityChart() {
    const intensityChartCanvas = document.getElementById('intensityChart');
    
    if (!intensityChartCanvas) return;
    
    // Get training log data from the page
    const trainingData = getTrainingData();
    
    if (!trainingData || trainingData.length === 0) {
        const noDataMessage = document.createElement('div');
        noDataMessage.className = 'text-center p-4 text-muted';
        noDataMessage.innerText = 'No training data available yet';
        intensityChartCanvas.parentNode.replaceChild(noDataMessage, intensityChartCanvas);
        return;
    }
    
    // Process data for chart
    const labels = trainingData.map(log => log.date);
    const intensities = trainingData.map(log => log.intensity);
    
    // Create chart
    const intensityChart = new Chart(intensityChartCanvas, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Training Intensity',
                data: intensities,
                backgroundColor: 'rgba(44, 123, 229, 0.2)',
                borderColor: 'rgba(44, 123, 229, 1)',
                borderWidth: 2,
                tension: 0.4,
                pointBackgroundColor: 'rgba(44, 123, 229, 1)',
                pointRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 10,
                    title: {
                        display: true,
                        text: 'Intensity (1-10)'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Date'
                    }
                }
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                },
                tooltip: {
                    enabled: true
                }
            }
        }
    });
}

// Risk factor chart
function initRiskFactorChart() {
    const riskChartCanvas = document.getElementById('riskFactorChart');
    
    if (!riskChartCanvas) return;
    
    // Get analysis data from the page
    const analysisData = getAnalysisData();
    
    if (!analysisData || analysisData.length === 0) {
        const noDataMessage = document.createElement('div');
        noDataMessage.className = 'text-center p-4 text-muted';
        noDataMessage.innerText = 'No analysis data available yet';
        riskChartCanvas.parentNode.replaceChild(noDataMessage, riskChartCanvas);
        return;
    }
    
    // Count risk levels
    const riskCounts = {
        'Low': 0,
        'Medium': 0,
        'High': 0
    };
    
    analysisData.forEach(analysis => {
        if (analysis.riskLevel in riskCounts) {
            riskCounts[analysis.riskLevel]++;
        }
    });
    
    // Create chart
    const riskChart = new Chart(riskChartCanvas, {
        type: 'doughnut',
        data: {
            labels: Object.keys(riskCounts),
            datasets: [{
                data: Object.values(riskCounts),
                backgroundColor: [
                    'rgba(40, 167, 69, 0.8)', // Green for Low
                    'rgba(255, 193, 7, 0.8)', // Yellow for Medium
                    'rgba(220, 53, 69, 0.8)'  // Red for High
                ],
                borderColor: [
                    'rgba(40, 167, 69, 1)',
                    'rgba(255, 193, 7, 1)',
                    'rgba(220, 53, 69, 1)'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.raw || 0;
                            const total = context.dataset.data.reduce((acc, curr) => acc + curr, 0);
                            const percentage = Math.round((value / total) * 100);
                            return `${label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

// Get training data from the page
function getTrainingData() {
    const dataElement = document.getElementById('trainingData');
    
    if (!dataElement) return [];
    
    try {
        return JSON.parse(dataElement.textContent);
    } catch (e) {
        console.error('Error parsing training data:', e);
        return [];
    }
}

// Get analysis data from the page
function getAnalysisData() {
    const dataElement = document.getElementById('analysisData');
    
    if (!dataElement) return [];
    
    try {
        return JSON.parse(dataElement.textContent);
    } catch (e) {
        console.error('Error parsing analysis data:', e);
        return [];
    }
}

// Load recent activity
function loadRecentActivity() {
    const activityContainer = document.getElementById('recentActivity');
    
    if (!activityContainer) return;
    
    // Get training logs and analysis data
    const trainingData = getTrainingData();
    const analysisData = getAnalysisData();
    
    // Combine and sort by date (most recent first)
    const allActivity = [
        ...trainingData.map(log => ({
            type: 'training',
            date: new Date(log.date),
            data: log
        })),
        ...analysisData.map(analysis => ({
            type: 'analysis',
            date: new Date(analysis.date),
            data: analysis
        }))
    ].sort((a, b) => b.date - a.date);
    
    // Display recent activity
    if (allActivity.length === 0) {
        activityContainer.innerHTML = '<p class="text-center text-muted">No recent activity</p>';
        return;
    }
    
    // Take the 5 most recent activities
    const recentActivities = allActivity.slice(0, 5);
    
    activityContainer.innerHTML = '';
    
    recentActivities.forEach(activity => {
        const activityCard = document.createElement('div');
        activityCard.className = 'card mb-3';
        
        const formattedDate = activity.date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
        
        if (activity.type === 'training') {
            activityCard.innerHTML = `
                <div class="card-body">
                    <h5 class="card-title">Training Log - ${activity.data.sport}</h5>
                    <h6 class="card-subtitle mb-2 text-muted">${formattedDate}</h6>
                    <p class="card-text">
                        Duration: ${activity.data.duration} minutes<br>
                        Intensity: ${activity.data.intensity}/10
                    </p>
                    <a href="/training-log" class="card-link">View All Logs</a>
                </div>
            `;
        } else {
            activityCard.innerHTML = `
                <div class="card-body">
                    <h5 class="card-title">Video Analysis - ${activity.data.sport}</h5>
                    <h6 class="card-subtitle mb-2 text-muted">${formattedDate}</h6>
                    <p class="card-text">
                        Risk Level: <span class="risk-level risk-${activity.data.riskLevel.toLowerCase()}">${activity.data.riskLevel}</span>
                    </p>
                    <a href="/analysis/${activity.data.id}" class="card-link">View Analysis</a>
                </div>
            `;
        }
        
        activityContainer.appendChild(activityCard);
    });
}
