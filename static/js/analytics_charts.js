// analytics_charts.js
document.addEventListener('DOMContentLoaded', function() {
    // Check if we have data to display
    if (!window.hasAnalyticsData) {
        console.log("No analytics data available");
        return;
    }
    
    // Set Chart.js defaults
    Chart.defaults.font.family = 'Inter, sans-serif';
    Chart.defaults.color = '#64748b';
    
    // Define common colors
    const primaryColor = '#8b5cf6';
    const secondaryColor = '#0ea5e9';
    const tertiaryColor = '#f97316';
    const quaternaryColor = '#10b981';
    const grayColor = '#cbd5e1';
    
    // Helper function for RGBA conversion
    function hexToRGBA(hex, alpha) {
        const r = parseInt(hex.slice(1, 3), 16);
        const g = parseInt(hex.slice(3, 5), 16);
        const b = parseInt(hex.slice(5, 7), 16);
        return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    }
    
    // Initialize Timeline Chart
    if (document.getElementById('timelineChart') && window.scanDatesData) {
        try {
            const timelineDates = Object.keys(window.scanDatesData);
            const timelineCounts = Object.values(window.scanDatesData);
            
            // Sort dates chronologically
            const dateIndices = timelineDates.map((date, i) => i);
            dateIndices.sort((a, b) => new Date(timelineDates[a]) - new Date(timelineDates[b]));
            
            const sortedDates = dateIndices.map(i => timelineDates[i]);
            const sortedCounts = dateIndices.map(i => timelineCounts[i]);
            
            const timelineCtx = document.getElementById('timelineChart').getContext('2d');
            const timelineChart = new Chart(timelineCtx, {
                type: 'line',
                data: {
                    labels: sortedDates,
                    datasets: [{
                        label: 'Scans',
                        data: sortedCounts,
                        fill: true,
                        backgroundColor: hexToRGBA(primaryColor, 0.2),
                        borderColor: primaryColor,
                        borderWidth: 2,
                        tension: 0.4,
                        pointRadius: 4,
                        pointBackgroundColor: primaryColor
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: {
                            type: 'time',
                            time: {
                                parser: 'yyyy-MM-dd',
                                tooltipFormat: 'MMM d, yyyy',
                                unit: 'day'
                            },
                            grid: {
                                display: false
                            }
                        },
                        y: {
                            beginAtZero: true,
                            ticks: {
                                precision: 0
                            },
                            grid: {
                                color: '#e2e8f0'
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            backgroundColor: 'rgba(15, 23, 42, 0.8)',
                            padding: 12,
                            cornerRadius: 6
                        }
                    }
                }
            });
        } catch (error) {
            console.error("Error initializing timeline chart:", error);
            handleChartError('timelineChart');
        }
    }
    
    // Initialize Device Chart
    if (document.getElementById('deviceChart') && window.deviceData) {
        try {
            const deviceLabels = window.deviceData.map(item => item.device);
            const deviceCounts = window.deviceData.map(item => item.scans);
            const deviceColors = [secondaryColor, primaryColor, tertiaryColor, grayColor];
            
            const deviceCtx = document.getElementById('deviceChart').getContext('2d');
            const deviceChart = new Chart(deviceCtx, {
                type: 'doughnut',
                data: {
                    labels: deviceLabels,
                    datasets: [{
                        data: deviceCounts,
                        backgroundColor: deviceColors.slice(0, deviceLabels.length),
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '60%',
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                padding: 15,
                                usePointStyle: true,
                                pointStyle: 'circle'
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const label = context.label || '';
                                    const value = context.raw || 0;
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = Math.round(value / total * 100);
                                    return `${label}: ${value} (${percentage}%)`;
                                }
                            }
                        }
                    }
                }
            });
        } catch (error) {
            console.error("Error initializing device chart:", error);
            handleChartError('deviceChart');
        }
    }
    
    // Initialize OS Chart
    if (document.getElementById('osChart') && window.osData) {
        try {
            const osLabels = window.osData.map(item => item.os);
            const osCounts = window.osData.map(item => item.scans);
            const osColors = [primaryColor, secondaryColor, quaternaryColor, tertiaryColor, '#0f766e', grayColor];
            
            const osCtx = document.getElementById('osChart').getContext('2d');
            const osChart = new Chart(osCtx, {
                type: 'doughnut',
                data: {
                    labels: osLabels,
                    datasets: [{
                        data: osCounts,
                        backgroundColor: osColors.slice(0, osLabels.length),
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '60%',
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                padding: 15,
                                usePointStyle: true,
                                pointStyle: 'circle'
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const label = context.label || '';
                                    const value = context.raw || 0;
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = Math.round(value / total * 100);
                                    return `${label}: ${value} (${percentage}%)`;
                                }
                            }
                        }
                    }
                }
            });
        } catch (error) {
            console.error("Error initializing OS chart:", error);
            handleChartError('osChart');
        }
    }
    
    // Initialize Hourly Chart
    if (document.getElementById('hourlyChart') && window.hourlyData) {
        try {
            const hourLabels = Array.from({length: 24}, (_, i) => {
                const hour = i % 12 || 12;
                const ampm = i < 12 ? 'AM' : 'PM';
                return `${hour}${ampm}`;
            });
            
            const hourlyCtx = document.getElementById('hourlyChart').getContext('2d');
            const hourlyChart = new Chart(hourlyCtx, {
                type: 'bar',
                data: {
                    labels: hourLabels,
                    datasets: [{
                        label: 'Scans',
                        data: window.hourlyData,
                        backgroundColor: secondaryColor,
                        borderRadius: 4,
                        barPercentage: 0.6,
                        categoryPercentage: 0.8
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: {
                            grid: {
                                display: false
                            },
                            ticks: {
                                maxRotation: 45,
                                minRotation: 45
                            }
                        },
                        y: {
                            beginAtZero: true,
                            ticks: {
                                precision: 0
                            },
                            grid: {
                                color: '#e2e8f0'
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            display: false
                        }
                    }
                }
            });
        } catch (error) {
            console.error("Error initializing hourly chart:", error);
            handleChartError('hourlyChart');
        }
    }
    
    // Initialize Location Chart
    if (document.getElementById('locationChart') && window.locationData) {
        try {
            const locationLabels = window.locationData.map(item => item.location);
            const locationCounts = window.locationData.map(item => item.scans);
            
            const locationCtx = document.getElementById('locationChart').getContext('2d');
            const locationChart = new Chart(locationCtx, {
                type: 'bar',
                data: {
                    labels: locationLabels,
                    datasets: [{
                        label: 'Scans',
                        data: locationCounts,
                        backgroundColor: primaryColor,
                        borderRadius: 4
                    }]
                },
                options: {
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: {
                            beginAtZero: true,
                            ticks: {
                                precision: 0
                            },
                            grid: {
                                color: '#e2e8f0'
                            }
                        },
                        y: {
                            grid: {
                                display: false
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            display: false
                        }
                    }
                }
            });
        } catch (error) {
            console.error("Error initializing location chart:", error);
            handleChartError('locationChart');
        }
    }
    
    // Handle chart errors
    function handleChartError(chartId) {
        const container = document.getElementById(chartId);
        if (container) {
            const parent = container.parentElement;
            parent.innerHTML = `
                <div class="flex items-center justify-center h-full">
                    <div class="text-center p-4">
                        <div class="text-red-500 mb-2"><i class="fas fa-exclamation-circle text-xl"></i></div>
                        <p class="text-gray-500">Could not load chart data</p>
                    </div>
                </div>
            `;
        }
    }
});