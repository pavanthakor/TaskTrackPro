// Chart configuration
const chartConfig = {
    metrics: ['Speed', 'Accuracy', 'Endurance', 'Strength', 'Flexibility', 'Technique'],
    colors: {
        'Speed': 'rgb(75, 192, 192)',
        'Accuracy': 'rgb(255, 99, 132)',
        'Endurance': 'rgb(54, 162, 235)',
        'Strength': 'rgb(255, 159, 64)',
        'Flexibility': 'rgb(153, 102, 255)',
        'Technique': 'rgb(255, 205, 86)'
    }
};

// Store chart instances
const chartInstances = {};

// Function to show messages
function showMessage(canvas, message, type) {
    const container = canvas.parentNode;
    const existingMsg = container.querySelector('.alert');
    if (existingMsg) {
        existingMsg.remove();
    }

    canvas.style.display = type === 'error' || type === 'info' ? 'none' : 'block';

    const msgElement = document.createElement('div');
    msgElement.className = `alert alert-${type} text-center mt-3`;
    msgElement.textContent = message;
    container.appendChild(msgElement);

    if (type === 'success') {
        setTimeout(() => msgElement.remove(), 3000);
    }
}

// Function to initialize a chart
function initializeChart(sportId, sportName) {
    const chartCanvas = document.getElementById(`chart-${sportId}`);
    if (!chartCanvas) return null;

    async function updateChartData() {
        try {
            const datasets = [];
            for (const metric of chartConfig.metrics) {
                const response = await fetch(`/progress/chart/${sportId}/${metric}`);
                if (!response.ok) {
                    throw new Error(`Failed to fetch ${metric} data: ${response.statusText}`);
                }
                const data = await response.json();
                
                if (!data || !Array.isArray(data.values) || !Array.isArray(data.dates)) {
                    console.warn(`Invalid data format for ${metric}`);
                    continue;
                }

                if (data.values.length > 0 && data.dates.length === data.values.length) {
                    datasets.push({
                        label: `${metric} (${data.unit || 'N/A'})`,
                        data: data.values,
                        dates: data.dates,
                        borderColor: chartConfig.colors[metric],
                        backgroundColor: chartConfig.colors[metric].replace('rgb', 'rgba').replace(')', ', 0.1)'),
                        tension: 0.1,
                        fill: true
                    });
                }
            }

            if (datasets.length === 0) {
                showMessage(chartCanvas, 'No progress data available yet', 'info');
                return;
            }

            const allDates = [...new Set(datasets.flatMap(ds => ds.dates))].sort();

            if (chartInstances[sportId]) {
                chartInstances[sportId].destroy();
            }

            chartInstances[sportId] = new Chart(chartCanvas, {
                type: 'line',
                data: {
                    labels: allDates,
                    datasets: datasets.map(ds => ({
                        ...ds,
                        data: allDates.map(date => {
                            const idx = ds.dates.indexOf(date);
                            return idx >= 0 ? ds.values[idx] : null;
                        })
                    }))
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {
                        mode: 'index',
                        intersect: false
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Value'
                            }
                        },
                        x: {
                            type: 'time',
                            time: {
                                unit: 'day',
                                displayFormats: {
                                    day: 'MMM D, YYYY'
                                }
                            },
                            title: {
                                display: true,
                                text: 'Date'
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            position: 'top',
                            labels: {
                                usePointStyle: true,
                                padding: 10
                            }
                        },
                        tooltip: {
                            mode: 'index',
                            intersect: false,
                            callbacks: {
                                title: function(context) {
                                    return moment(context[0].label).format('MMMM D, YYYY');
                                }
                            }
                        }
                    }
                }
            });
            
            showMessage(chartCanvas, 'Progress chart updated successfully', 'success');
            
        } catch (error) {
            console.error('Error updating chart:', error);
            showMessage(chartCanvas, 'Error loading progress data: ' + error.message, 'error');
        }
    }

    updateChartData();
    return { updateChartData };
}

// Initialize everything when the document is ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize all charts
    window.SPORTS_DATA.forEach(sport => {
        chartInstances[sport.id] = initializeChart(sport.id, sport.name);
    });

    // Handle form submission
    const progressForm = document.getElementById('progressForm');
    if (progressForm) {
        progressForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            try {
                const formData = new FormData(this);
                const response = await fetch(this.action, {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) {
                    throw new Error('Failed to submit progress data');
                }

                await new Promise(resolve => setTimeout(resolve, 500));
                
                // Update all charts
                for (const sportId in chartInstances) {
                    if (chartInstances[sportId] && chartInstances[sportId].updateChartData) {
                        await chartInstances[sportId].updateChartData();
                    }
                }
                
                this.reset();
                
            } catch (error) {
                console.error('Error submitting form:', error);
                const sportId = formData.get('sport');
                const chartCanvas = document.getElementById(`chart-${sportId}`);
                if (chartCanvas) {
                    showMessage(chartCanvas, 'Error submitting progress data: ' + error.message, 'error');
                }
            }
        });
    }
}); 