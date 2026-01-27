// MetroMind - Smart Transit AI Dashboard

const API_BASE = 'http://127.0.0.1:8000';

// Chart instance
let scoreChart = null;

// District center coordinates for animations (updated for realistic map)
const districtCenters = {
    'Central': { x: 220, y: 145 },
    'North': { x: 200, y: 75 },
    'South': { x: 190, y: 215 },
    'East': { x: 355, y: 145 },
    'West': { x: 85, y: 140 }
};

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
                    pointRadius: 0,
                },
                {
                    label: 'Environment',
                    data: [],
                    borderColor: '#48bb78',
                    backgroundColor: 'rgba(72, 187, 120, 0.1)',
                    tension: 0.3,
                    fill: true,
                    pointRadius: 0,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index',
            },
            scales: {
                y: {
                    min: 0,
                    max: 100,
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#718096', font: { size: 10 } },
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#718096', font: { size: 10 }, maxTicksLimit: 10 },
                },
            },
            plugins: {
                legend: { display: false },
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

// Step simulation with agent animations
async function step() {
    try {
        disableButtons();
        await animateAgents();

        const response = await fetch(`${API_BASE}/api/step`, { method: 'POST' });
        const data = await response.json();

        // Animate interventions on map
        if (data.actions && data.actions.length > 0) {
            animateInterventions(data.actions);
        }

        updateUI(data);
    } catch (error) {
        console.error('Error stepping:', error);
        showError('Failed to step simulation');
    } finally {
        resetAgents();
        enableButtons();
    }
}

// Run 10 steps
async function run10() {
    try {
        disableButtons();
        await animateAgents();

        const response = await fetch(`${API_BASE}/api/run?n=10`, { method: 'POST' });
        const data = await response.json();
        updateUI(data);
    } catch (error) {
        console.error('Error running steps:', error);
        showError('Failed to run simulation');
    } finally {
        resetAgents();
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
        document.getElementById('action-list').innerHTML = `
            <div class="action-placeholder">
                <span class="placeholder-icon">🚀</span>
                <span>Run simulation to see agent decisions</span>
            </div>
        `;

        updateUI(data);
    } catch (error) {
        console.error('Error resetting:', error);
        showError('Failed to reset simulation');
    } finally {
        enableButtons();
    }
}

// Animate agents during processing
async function animateAgents() {
    const agents = ['monitor', 'planner', 'policy', 'coordinator', 'executor'];
    const states = [
        'Observing city...',
        'Proposing actions...',
        'Validating rules...',
        'Allocating resources...',
        'Executing...'
    ];

    for (let i = 0; i < agents.length; i++) {
        const card = document.getElementById(`agent-${agents[i]}`);
        const stateEl = document.getElementById(`${agents[i]}-state`);

        // Activate current agent
        card.classList.add('active');
        stateEl.textContent = states[i];

        await sleep(150);

        // Deactivate after a moment
        if (i > 0) {
            const prevCard = document.getElementById(`agent-${agents[i-1]}`);
            prevCard.classList.remove('active');
            document.getElementById(`${agents[i-1]}-state`).textContent = 'Done';
        }
    }
}

// Reset agent states
function resetAgents() {
    const agents = ['monitor', 'planner', 'policy', 'coordinator', 'executor'];
    agents.forEach(agent => {
        const card = document.getElementById(`agent-${agent}`);
        card.classList.remove('active');
        document.getElementById(`${agent}-state`).textContent = 'Idle';
    });
}

// Animate interventions on the map
function animateInterventions(actions) {
    const animLayer = document.getElementById('animation-layer');

    actions.forEach((action, index) => {
        const center = districtCenters[action.district];
        if (!center) return;

        // Parse actions and create floating +1 texts
        action.actions.forEach((act, actIndex) => {
            setTimeout(() => {
                let text = '';
                let className = 'intervention-text';

                if (act.includes('BUS') || act.includes('BUSES')) {
                    const match = act.match(/\+(\d+)/);
                    text = match ? `🚌 +${match[1]}` : '🚌 +1';
                    className += ' bus';
                } else if (act.includes('TRAIN')) {
                    const match = act.match(/\+(\d+)/);
                    text = match ? `🚇 +${match[1]}` : '🚇 +1';
                    className += ' train';
                } else if (act.includes('CROWD')) {
                    text = '👥 Managed';
                    className += ' crowd';
                } else if (act.includes('PRIORITY')) {
                    text = '🚌 Priority';
                    className += ' bus';
                } else if (act.includes('NUDGE')) {
                    text = '📱 Nudge';
                }

                if (text) {
                    createFloatingText(animLayer, center.x, center.y - 10 - actIndex * 15, text, className);

                    // Pulse the district
                    const districtEl = document.getElementById(`district-${action.district.toLowerCase()}`);
                    if (districtEl) {
                        const shape = districtEl.querySelector('.district-shape');
                        shape.classList.add('district-pulse');
                        setTimeout(() => shape.classList.remove('district-pulse'), 500);
                    }
                }
            }, index * 200 + actIndex * 100);
        });
    });
}

// Create floating text animation
function createFloatingText(container, x, y, text, className) {
    const textEl = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    textEl.setAttribute('x', x);
    textEl.setAttribute('y', y);
    textEl.setAttribute('class', `${className} float-animation`);
    textEl.textContent = text;
    container.appendChild(textEl);

    // Remove after animation
    setTimeout(() => textEl.remove(), 1500);
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

    // Set period of day with icon
    let period = 'Night';
    let icon = '🌙';
    if (hour >= 5 && hour < 7) { period = 'Dawn'; icon = '🌅'; }
    else if (hour >= 7 && hour < 12) { period = 'Morning'; icon = '☀️'; }
    else if (hour >= 12 && hour < 17) { period = 'Afternoon'; icon = '🌤️'; }
    else if (hour >= 17 && hour < 20) { period = 'Evening'; icon = '🌆'; }
    else if (hour >= 20 && hour < 22) { period = 'Dusk'; icon = '🌇'; }

    document.getElementById('clock-period').textContent = period;
    document.getElementById('time-icon').textContent = icon;
    document.getElementById('day-count').textContent = day;
    document.getElementById('hour-count').textContent = t;

    // Update header scores
    const liveability = data.scores.liveability_score;
    const environment = data.scores.environment_score;
    document.getElementById('header-liveability').textContent = liveability.toFixed(1);
    document.getElementById('header-environment').textContent = environment.toFixed(1);

    // Update budgets
    if (data.budgets) {
        const busRemaining = data.budgets.bus_remaining;
        const mrtRemaining = data.budgets.mrt_remaining;
        document.getElementById('bus-budget-bar').style.width = `${(busRemaining / 40) * 100}%`;
        document.getElementById('mrt-budget-bar').style.width = `${(mrtRemaining / 12) * 100}%`;
        document.getElementById('bus-budget-value').textContent = `${busRemaining}/40`;
        document.getElementById('mrt-budget-value').textContent = `${mrtRemaining}/12`;
    }

    // Update economics
    if (data.economics) {
        const fundsEl = document.getElementById('city-funds');
        fundsEl.textContent = `$${data.economics.funds.toLocaleString()}K`;
        fundsEl.className = 'treasury-value' + (data.economics.funds < 200 ? ' low' : '');

        document.getElementById('hourly-revenue').textContent = data.economics.hourly_revenue.toFixed(1);
        document.getElementById('hourly-cost').textContent = data.economics.hourly_cost.toFixed(1);
    }

    // Update environment
    if (data.environment) {
        const sustainability = data.environment.sustainability_score;
        document.getElementById('sustainability-bar').style.width = `${sustainability}%`;
        document.getElementById('sustainability-value').textContent = sustainability.toFixed(0);

        const hourlyEmissions = data.environment.hourly_emissions;
        const hourlyEl = document.getElementById('hourly-emissions');
        hourlyEl.textContent = `${hourlyEmissions.toFixed(1)} kg`;
        hourlyEl.className = 'env-value emissions' + (hourlyEmissions > 100 ? ' high' : '');

        document.getElementById('total-emissions').textContent =
            `${data.environment.carbon_emissions.toFixed(0)} kg`;
    }

    // Update active events
    updateActiveEvents(data.active_events || []);

    // Update metrics with color coding
    updateMetric('metric-station', data.metrics.avg_station, 0.5, 0.7);
    updateMetric('metric-bus', data.metrics.avg_bus_load, 0.7, 0.85);
    updateMetric('metric-mrt', data.metrics.avg_mrt_load, 0.65, 0.8);
    updateMetric('metric-traffic', data.metrics.avg_traffic, 0.5, 0.7);

    const airEl = document.getElementById('metric-air');
    airEl.textContent = data.metrics.avg_air.toFixed(1);
    airEl.className = 'metric-value ' + getAirClass(data.metrics.avg_air);

    // Update map districts
    updateMapDistricts(data.districts);

    // Update chart with history
    updateChart(data.history_tail);

    // Update action feed
    if (data.actions && data.actions.length > 0) {
        addActions(data.actions);
    }
}

// Update a metric with color coding
function updateMetric(id, value, warnThreshold, critThreshold) {
    const el = document.getElementById(id);
    el.textContent = formatPercent(value);

    if (value > critThreshold) {
        el.className = 'metric-value critical';
    } else if (value > warnThreshold) {
        el.className = 'metric-value busy';
    } else if (value > warnThreshold * 0.7) {
        el.className = 'metric-value moderate';
    } else {
        el.className = 'metric-value good';
    }
}

// Get air quality class
function getAirClass(value) {
    if (value >= 80) return 'good';
    if (value >= 60) return 'moderate';
    if (value >= 40) return 'busy';
    return 'critical';
}

// Update map district colors and stats
function updateMapDistricts(districts) {
    for (const [name, d] of Object.entries(districts)) {
        const districtEl = document.getElementById(`district-${name.toLowerCase()}`);
        if (!districtEl) continue;

        const shape = districtEl.querySelector('.district-shape');
        const statsEl = document.getElementById(`${name.toLowerCase()}-stats`);

        // Calculate average load for color
        const avgLoad = (d.bus_load_factor + d.mrt_load_factor + d.station_crowding) / 3;

        // Remove old classes
        shape.classList.remove('load-low', 'load-moderate', 'load-busy', 'load-critical');

        // Add new class based on load
        if (avgLoad > 0.8) {
            shape.classList.add('load-critical');
        } else if (avgLoad > 0.6) {
            shape.classList.add('load-busy');
        } else if (avgLoad > 0.35) {
            shape.classList.add('load-moderate');
        } else {
            shape.classList.add('load-low');
        }

        // Update stats text
        statsEl.textContent = `${formatPercent(avgLoad)} load`;
    }
}

// Update chart
function updateChart(history) {
    if (!history || history.length === 0) return;

    const labels = history.map(h => `H${h.t}`);
    const liveabilityData = history.map(h => h.scores.liveability_score);
    const environmentData = history.map(h => h.scores.environment_score);

    scoreChart.data.labels = labels;
    scoreChart.data.datasets[0].data = liveabilityData;
    scoreChart.data.datasets[1].data = environmentData;
    scoreChart.update('none');
}

// Add actions to feed
function addActions(actions) {
    const list = document.getElementById('action-list');

    // Remove placeholder if present
    const placeholder = list.querySelector('.action-placeholder');
    if (placeholder) placeholder.remove();

    for (const action of actions) {
        const item = document.createElement('div');
        item.className = 'action-item';

        // Determine urgency class
        let urgencyClass = 'low';
        if (action.urgency >= 3) urgencyClass = 'high';
        else if (action.urgency >= 1.5) urgencyClass = 'medium';

        // Create action tags with proper classes
        const tags = action.actions.map(a => {
            let tagClass = 'action-tag';
            if (a.includes('BUS') || a.includes('PRIORITY')) tagClass += ' bus';
            else if (a.includes('TRAIN')) tagClass += ' train';
            else if (a.includes('CROWD')) tagClass += ' crowd';
            return `<span class="${tagClass}">${a}</span>`;
        }).join('');

        item.innerHTML = `
            <div class="action-header">
                <span class="action-time">Hour ${action.t}</span>
                <span class="action-urgency ${urgencyClass}">Urgency: ${action.urgency.toFixed(1)}</span>
            </div>
            <div class="action-district">${action.district}</div>
            <div class="action-tags">${tags}</div>
        `;

        list.insertBefore(item, list.firstChild);
    }

    // Keep only last 15 items
    while (list.children.length > 15) {
        list.removeChild(list.lastChild);
    }
}

// Update active events display
function updateActiveEvents(events) {
    const list = document.getElementById('events-list');

    if (!events || events.length === 0) {
        list.innerHTML = '<div class="no-events">No active events</div>';
        return;
    }

    list.innerHTML = events.map(event => `
        <div class="event-card">
            <span class="event-icon">${event.icon}</span>
            <div class="event-info">
                <div class="event-name">${event.name}</div>
                <div class="event-details">Affects: ${event.districts.join(', ')} | Demand: +${((event.demand_mult - 1) * 100).toFixed(0)}%</div>
            </div>
            <div class="event-timer">
                <span>&#128337;</span>
                <span>${event.remaining_hours}h</span>
            </div>
        </div>
    `).join('');
}

// Helper functions
function formatPercent(value) {
    return (value * 100).toFixed(1) + '%';
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
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
    const list = document.getElementById('action-list');
    const item = document.createElement('div');
    item.className = 'action-item';
    item.style.borderLeftColor = '#fc8181';
    item.innerHTML = `
        <div class="action-header">
            <span class="action-time" style="color: #fc8181;">Error</span>
        </div>
        <div class="action-district" style="color: #fc8181;">Connection Failed</div>
        <div class="action-tags">${message}</div>
    `;
    list.insertBefore(item, list.firstChild);
}
