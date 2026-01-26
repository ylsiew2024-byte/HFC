// UrbanPulse Frontend Application

const API_BASE = 'http://127.0.0.1:8000';

// Chart instance
let scoreChart = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initChart();
    fetchState();
});

// Initialize Chart.js
function initChart() {
    const ctx = document.getElementById('score-chart').getContext('2d');
    scoreChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'Liveability',
                    data: [],
                    borderColor: '#4fd1c5',
                    backgroundColor: 'rgba(79, 209, 197, 0.1)',
                    tension: 0.3,
                    fill: true,
                },
                {
                    label: 'Environment',
                    data: [],
                    borderColor: '#68d391',
                    backgroundColor: 'rgba(104, 211, 145, 0.1)',
                    tension: 0.3,
                    fill: true,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    min: 0,
                    max: 100,
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)',
                    },
                    ticks: {
                        color: '#a0aec0',
                    },
                },
                x: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)',
                    },
                    ticks: {
                        color: '#a0aec0',
                    },
                },
            },
            plugins: {
                legend: {
                    labels: {
                        color: '#e8e8e8',
                    },
                },
            },
        },
    });
}

// Fetch current state
async function fetchState() {
    try {
        const response = await fetch(`${API_BASE}/api/state`);
        const data = await response.json();
        updateUI(data);
    } catch (error) {
        console.error('Error fetching state:', error);
        showError('Failed to connect to backend. Is the server running?');
    }
}

// Step simulation
async function step() {
    try {
        disableButtons();
        const response = await fetch(`${API_BASE}/api/step`, { method: 'POST' });
        const data = await response.json();
        updateUI(data);
    } catch (error) {
        console.error('Error stepping:', error);
        showError('Failed to step simulation');
    } finally {
        enableButtons();
    }
}

// Run 10 steps
async function run10() {
    try {
        disableButtons();
        const response = await fetch(`${API_BASE}/api/run?n=10`, { method: 'POST' });
        const data = await response.json();
        updateUI(data);
    } catch (error) {
        console.error('Error running steps:', error);
        showError('Failed to run simulation');
    } finally {
        enableButtons();
    }
}

// Reset simulation
async function reset() {
    try {
        disableButtons();
        const response = await fetch(`${API_BASE}/api/reset`, { method: 'POST' });
        const data = await response.json();

        // Clear chart data
        scoreChart.data.labels = [];
        scoreChart.data.datasets[0].data = [];
        scoreChart.data.datasets[1].data = [];
        scoreChart.update();

        // Clear action feed
        document.getElementById('action-list').innerHTML = '';

        updateUI(data);
    } catch (error) {
        console.error('Error resetting:', error);
        showError('Failed to reset simulation');
    } finally {
        enableButtons();
    }
}

// Update UI with data
function updateUI(data) {
    // Update time display
    const t = data.t;
    const hour = t % 24;
    const day = Math.floor(t / 24) + 1;

    // Format time (12-hour format)
    const hour12 = hour % 12 || 12;
    const ampm = hour < 12 ? 'AM' : 'PM';
    document.getElementById('clock-time').textContent = `${hour12}:00 ${ampm}`;

    // Set period of day
    let period = 'Night';
    if (hour >= 6 && hour < 12) period = 'Morning';
    else if (hour >= 12 && hour < 17) period = 'Afternoon';
    else if (hour >= 17 && hour < 21) period = 'Evening';
    document.getElementById('clock-period').textContent = period;

    // Update day and hour counts
    document.getElementById('day-count').textContent = day;
    document.getElementById('hour-count').textContent = t;

    // Update scores
    const liveability = data.scores.liveability_score;
    const environment = data.scores.environment_score;

    document.getElementById('liveability-score').textContent = liveability.toFixed(1);
    document.getElementById('environment-score').textContent = environment.toFixed(1);
    document.getElementById('liveability-bar').style.width = `${liveability}%`;
    document.getElementById('environment-bar').style.width = `${environment}%`;

    // Update metrics
    document.getElementById('metric-station').textContent = formatPercent(data.metrics.avg_station);
    document.getElementById('metric-bus').textContent = formatPercent(data.metrics.avg_bus_load);
    document.getElementById('metric-mrt').textContent = formatPercent(data.metrics.avg_mrt_load);
    document.getElementById('metric-traffic').textContent = formatPercent(data.metrics.avg_traffic);
    document.getElementById('metric-air').textContent = data.metrics.avg_air.toFixed(1);

    // Update district table
    updateDistrictTable(data.districts);

    // Update chart with history
    updateChart(data.history_tail);

    // Update action feed
    if (data.actions && data.actions.length > 0) {
        addActions(data.actions);
    }
}

// Update district table
function updateDistrictTable(districts) {
    const tbody = document.getElementById('district-tbody');
    tbody.innerHTML = '';

    for (const [name, d] of Object.entries(districts)) {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td><strong>${name}</strong></td>
            <td>${d.population.toLocaleString()}</td>
            <td>${d.bus_capacity}</td>
            <td class="${getStatusClass(d.bus_load_factor, 0.85)}">${formatPercent(d.bus_load_factor)}</td>
            <td>${d.mrt_capacity}</td>
            <td class="${getStatusClass(d.mrt_load_factor, 0.80)}">${formatPercent(d.mrt_load_factor)}</td>
            <td class="${getStatusClass(d.station_crowding, 0.9)}">${formatPercent(d.station_crowding)}</td>
            <td class="${getStatusClass(d.road_traffic, 0.8)}">${formatPercent(d.road_traffic)}</td>
            <td>${d.air_quality.toFixed(1)}</td>
            <td>${d.nudges_active ? '<span class="nudge-active">ACTIVE</span>' : '<span class="nudge-inactive">-</span>'}</td>
        `;
        tbody.appendChild(row);
    }
}

// Update chart
function updateChart(history) {
    if (!history || history.length === 0) return;

    const labels = history.map(h => h.t);
    const liveabilityData = history.map(h => h.scores.liveability_score);
    const environmentData = history.map(h => h.scores.environment_score);

    scoreChart.data.labels = labels;
    scoreChart.data.datasets[0].data = liveabilityData;
    scoreChart.data.datasets[1].data = environmentData;
    scoreChart.update();
}

// Add actions to feed
function addActions(actions) {
    const list = document.getElementById('action-list');

    for (const action of actions) {
        const item = document.createElement('div');
        item.className = 'action-item';

        const tags = action.actions.map(a => `<span class="action-tag">${a}</span>`).join('');

        item.innerHTML = `
            <div class="action-time">Step ${action.t} | Urgency: ${action.urgency}</div>
            <div class="action-district">${action.district}</div>
            <div class="action-details">${tags}</div>
        `;

        list.insertBefore(item, list.firstChild);
    }

    // Keep only last 20 items
    while (list.children.length > 20) {
        list.removeChild(list.lastChild);
    }
}

// Helper functions
function formatPercent(value) {
    return (value * 100).toFixed(1) + '%';
}

function getStatusClass(value, threshold) {
    if (value > threshold + 0.1) return 'status-critical';
    if (value > threshold) return 'status-warning';
    return 'status-good';
}

function disableButtons() {
    document.getElementById('btn-step').disabled = true;
    document.getElementById('btn-run10').disabled = true;
    document.getElementById('btn-reset').disabled = true;
}

function enableButtons() {
    document.getElementById('btn-step').disabled = false;
    document.getElementById('btn-run10').disabled = false;
    document.getElementById('btn-reset').disabled = false;
}

function showError(message) {
    // Simple error display - could be improved with toast notifications
    const list = document.getElementById('action-list');
    const item = document.createElement('div');
    item.className = 'action-item';
    item.style.borderLeftColor = '#f56565';
    item.innerHTML = `
        <div class="action-time" style="color: #f56565;">Error</div>
        <div class="action-details">${message}</div>
    `;
    list.insertBefore(item, list.firstChild);
}
