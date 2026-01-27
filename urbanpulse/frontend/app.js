// MetroMind - Smart Transit AI Dashboard
const API_BASE = 'http://127.0.0.1:8000';
let scoreChart = null;

const districtCenters = {
    'Central': { x: 220, y: 145 },
    'North': { x: 200, y: 75 },
    'East': { x: 355, y: 145 },
    'West': { x: 85, y: 140 }
};

const WEATHER_ICONS = {
    'Clear': '\u2600\uFE0F',
    'Light Rain': '\uD83C\uDF27\uFE0F',
    'Heavy Rain': '\uD83C\uDF27\uFE0F',
    'Thunderstorm': '\u26C8\uFE0F',
    'Haze': '\uD83C\uDF2B\uFE0F',
};

// ========== Init ==========
document.addEventListener('DOMContentLoaded', () => {
    initChart();
    fetchState();
});

function initChart() {
    const ctx = document.getElementById('score-chart').getContext('2d');
    scoreChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                { label: 'Liveability', data: [], borderColor: '#4fd1c5', backgroundColor: 'rgba(79,209,197,0.1)', tension: 0.3, fill: true, pointRadius: 0 },
                { label: 'Environment', data: [], borderColor: '#48bb78', backgroundColor: 'rgba(72,187,120,0.1)', tension: 0.3, fill: true, pointRadius: 0 },
            ],
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            interaction: { intersect: false, mode: 'index' },
            scales: {
                y: { min: 0, max: 100, grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#718096', font: { size: 10 } } },
                x: { grid: { display: false }, ticks: { color: '#718096', font: { size: 10 }, maxTicksLimit: 10 } },
            },
            plugins: { legend: { display: false } },
        },
    });
}

// ========== API Calls ==========
async function fetchState() {
    try {
        const r = await fetch(`${API_BASE}/api/state`);
        const data = await r.json();
        updateUI(data);
    } catch (e) {
        console.error('Fetch state error:', e);
        showError('Backend not reachable. Is uvicorn running?');
    }
}

async function simulateHour() {
    const hour = document.getElementById('hour-select').value;
    try {
        disableControls();
        await animateAgents();
        const r = await fetch(`${API_BASE}/api/simulate?hour=${hour}`, { method: 'POST' });
        const data = await r.json();
        if (data.actions && data.actions.length > 0) animateInterventions(data.actions);
        updateUI(data);
    } catch (e) {
        console.error('Simulate error:', e);
        showError('Failed to simulate');
    } finally {
        resetAgents();
        enableControls();
    }
}

async function resetSim() {
    try {
        disableControls();
        const r = await fetch(`${API_BASE}/api/reset`, { method: 'POST' });
        const data = await r.json();
        scoreChart.data.labels = [];
        scoreChart.data.datasets[0].data = [];
        scoreChart.data.datasets[1].data = [];
        scoreChart.update();
        updateUI(data);
    } catch (e) {
        console.error('Reset error:', e);
        showError('Failed to reset');
    } finally {
        enableControls();
    }
}

// ========== Map Switching ==========
function switchMap(which) {
    document.getElementById('bus-map-container').classList.toggle('hidden', which !== 'bus');
    document.getElementById('train-map-container').classList.toggle('hidden', which !== 'train');
    document.getElementById('tab-bus').classList.toggle('active', which === 'bus');
    document.getElementById('tab-train').classList.toggle('active', which === 'train');
}

// ========== Agent Animation ==========
async function animateAgents() {
    const agents = ['monitor', 'planner', 'policy', 'coordinator', 'executor'];
    const states = ['Observing city...', 'Proposing actions...', 'Validating rules...', 'Allocating resources...', 'Executing...'];
    for (let i = 0; i < agents.length; i++) {
        const card = document.getElementById(`agent-${agents[i]}`);
        const stateEl = document.getElementById(`${agents[i]}-state`);
        card.classList.add('active');
        stateEl.textContent = states[i];
        await sleep(120);
        if (i > 0) {
            document.getElementById(`agent-${agents[i-1]}`).classList.remove('active');
            document.getElementById(`${agents[i-1]}-state`).textContent = 'Done';
        }
    }
}

function resetAgents() {
    ['monitor','planner','policy','coordinator','executor'].forEach(a => {
        document.getElementById(`agent-${a}`).classList.remove('active');
        document.getElementById(`${a}-state`).textContent = 'Idle';
    });
}

// ========== Interventions Animation ==========
function animateInterventions(actions) {
    const layer = document.getElementById('bus-animation-layer');
    actions.forEach((action, i) => {
        if (action.type !== 'district') return;
        const c = districtCenters[action.district];
        if (!c) return;
        (action.actions || []).forEach((act, j) => {
            setTimeout(() => {
                let text = '';
                if (act.includes('BUS') && act.includes('+')) text = '\uD83D\uDE8C ' + act;
                else if (act.includes('PRIORITY')) text = '\uD83D\uDE8C Priority';
                else if (act.includes('TRAIN')) text = '\uD83D\uDE87 ' + act;
                else if (act.includes('CROWD')) text = '\uD83D\uDC65 Managed';
                else if (act.includes('NUDGE')) text = '\uD83D\uDCF1 Nudge';
                if (text) {
                    const el = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                    el.setAttribute('x', c.x);
                    el.setAttribute('y', c.y - 10 - j * 15);
                    el.setAttribute('class', 'intervention-text float-animation');
                    el.textContent = text;
                    layer.appendChild(el);
                    setTimeout(() => el.remove(), 1500);
                    // Pulse district
                    const de = document.getElementById(`district-${action.district.toLowerCase()}`);
                    if (de) {
                        const sh = de.querySelector('.district-shape');
                        sh.classList.add('district-pulse');
                        setTimeout(() => sh.classList.remove('district-pulse'), 500);
                    }
                }
            }, i * 200 + j * 100);
        });
    });
}

// ========== Main UI Update ==========
function updateUI(data) {
    // Time
    const hour = data.time.hour;
    const day = data.time.day;
    const hourStr = String(hour).padStart(2, '0') + ':00';

    document.getElementById('clock-time').textContent = hourStr;
    document.getElementById('day-count').textContent = day;
    document.getElementById('hour-count').textContent = hourStr;

    let period = 'Night', icon = '\uD83C\uDF19';
    if (hour >= 5 && hour < 7) { period = 'Dawn'; icon = '\uD83C\uDF05'; }
    else if (hour >= 7 && hour < 12) { period = 'Morning'; icon = '\u2600\uFE0F'; }
    else if (hour >= 12 && hour < 17) { period = 'Afternoon'; icon = '\uD83C\uDF24\uFE0F'; }
    else if (hour >= 17 && hour < 20) { period = 'Evening'; icon = '\uD83C\uDF06'; }
    else if (hour >= 20 && hour < 22) { period = 'Dusk'; icon = '\uD83C\uDF07'; }
    document.getElementById('clock-period').textContent = period;
    document.getElementById('time-icon').textContent = icon;

    // Scores
    document.getElementById('header-liveability').textContent = data.scores.liveability_score.toFixed(1);
    document.getElementById('header-environment').textContent = data.scores.environment_score.toFixed(1);

    // Weather
    updateWeather(data.weather);

    // Capacities
    if (data.capacities) {
        const busR = data.capacities.bus_fleet_remaining;
        const trainR = data.capacities.train_slots_remaining;
        document.getElementById('bus-budget-bar').style.width = `${(busR/40)*100}%`;
        document.getElementById('mrt-budget-bar').style.width = `${(trainR/12)*100}%`;
        document.getElementById('bus-budget-value').textContent = `${busR}/40`;
        document.getElementById('mrt-budget-value').textContent = `${trainR}/12`;
    }

    // Environment
    if (data.environment) {
        document.getElementById('sustainability-bar').style.width = `${data.environment.sustainability_score}%`;
        document.getElementById('sustainability-value').textContent = data.environment.sustainability_score.toFixed(0);
        const he = data.environment.hourly_emissions;
        const hel = document.getElementById('hourly-emissions');
        hel.textContent = `${he.toFixed(1)} kg`;
        hel.className = 'env-value emissions' + (he > 100 ? ' high' : '');
        document.getElementById('total-emissions').textContent = `${data.environment.carbon_emissions.toFixed(0)} kg`;
    }

    // Metrics
    updateMetric('metric-station', data.metrics.avg_station, 0.5, 0.7);
    updateMetric('metric-bus', data.metrics.avg_bus_load, 0.7, 0.85);
    updateMetric('metric-mrt', data.metrics.avg_mrt_load, 0.65, 0.8);
    updateMetric('metric-traffic', data.metrics.avg_traffic, 0.5, 0.7);
    const airEl = document.getElementById('metric-air');
    airEl.textContent = data.metrics.avg_air.toFixed(1);
    airEl.className = 'metric-value ' + (data.metrics.avg_air >= 80 ? 'good' : data.metrics.avg_air >= 60 ? 'moderate' : data.metrics.avg_air >= 40 ? 'busy' : 'critical');

    // District map
    updateBusMap(data.districts);

    // Train map
    updateTrainMap(data.train_lines);

    // Active Events panel
    updateActiveEventsPanel(data);

    // Chart
    updateChart(data.history_tail);
}

// ========== Weather ==========
function updateWeather(w) {
    const badge = document.getElementById('weather-badge');
    const icon = WEATHER_ICONS[w.condition] || '\u2600\uFE0F';
    document.getElementById('weather-icon').textContent = icon;
    document.getElementById('weather-text').textContent = w.condition;
    document.getElementById('weather-region').textContent = w.affected_regions.join(', ');

    badge.className = 'weather-badge';
    if (w.condition === 'Heavy Rain' || w.condition === 'Thunderstorm') badge.classList.add('weather-severe');
    else if (w.condition === 'Light Rain') badge.classList.add('weather-rain');
    else if (w.condition === 'Haze') badge.classList.add('weather-haze');
}

// ========== Bus Map ==========
function updateBusMap(districts) {
    for (const [name, d] of Object.entries(districts)) {
        const el = document.getElementById(`district-${name.toLowerCase()}`);
        if (!el) continue;
        const shape = el.querySelector('.district-shape');
        const stats = document.getElementById(`${name.toLowerCase()}-stats`);
        const avg = (d.bus_load_factor + d.mrt_load_factor + d.station_crowding) / 3;
        shape.classList.remove('load-low', 'load-moderate', 'load-busy', 'load-critical');
        if (avg > 0.8) shape.classList.add('load-critical');
        else if (avg > 0.6) shape.classList.add('load-busy');
        else if (avg > 0.35) shape.classList.add('load-moderate');
        else shape.classList.add('load-low');
        stats.textContent = `${(avg*100).toFixed(0)}% load`;
    }
}

// ========== Train Map ==========
function updateTrainMap(trainLines) {
    if (!trainLines) return;
    const lineColors = { NSL: '#e53e3e', EWL: '#48bb78', NEL: '#9f7aea', CCL: '#ed8936' };

    for (const [id, line] of Object.entries(trainLines)) {
        const lid = id.toLowerCase();
        const infoEl = document.getElementById(`${lid}-info`);
        const actionEl = document.getElementById(`${lid}-action`);
        const pathEl = document.getElementById(`${lid}-path`);

        if (infoEl) infoEl.textContent = `Load: ${(line.line_load*100).toFixed(0)}% | Freq: ${line.frequency}/h`;
        if (actionEl) {
            const acts = line.actions_this_hour;
            actionEl.textContent = acts && acts.length > 0 ? acts.join(', ') : 'No actions';
            actionEl.setAttribute('fill', acts && acts.length > 0 ? '#4fd1c5' : '#718096');
        }

        // Color intensity based on load
        if (pathEl) {
            const load = line.line_load;
            let opacity = 0.5 + load * 0.5;
            let width = load > 0.8 ? 10 : load > 0.6 ? 9 : 8;
            pathEl.setAttribute('opacity', opacity);
            pathEl.setAttribute('stroke-width', width);
            if (line.disruption_level > 0.2) {
                pathEl.setAttribute('stroke-dasharray', '12,4');
            } else {
                pathEl.removeAttribute('stroke-dasharray');
            }
        }
    }
}

// ========== Active Events Panel ==========
function updateActiveEventsPanel(data) {
    // Weather
    const weatherDiv = document.getElementById('events-weather');
    const w = data.weather;
    if (w.condition !== 'Clear') {
        const icon = WEATHER_ICONS[w.condition] || '';
        const severity = w.intensity > 0.6 ? 'Severe' : w.intensity > 0.3 ? 'Moderate' : 'Light';
        weatherDiv.innerHTML = `
            <div class="event-card weather-event">
                <span class="event-icon">${icon}</span>
                <div class="event-info">
                    <div class="event-name">${w.condition}</div>
                    <div class="event-details">Intensity: ${severity} (${(w.intensity*100).toFixed(0)}%) | ${w.affected_regions.join(', ')}</div>
                </div>
            </div>`;
    } else {
        weatherDiv.innerHTML = '<div class="no-events">\u2600\uFE0F Clear skies</div>';
    }

    // Train lines
    const trainsDiv = document.getElementById('events-trains');
    if (data.train_lines) {
        let html = '';
        for (const [id, line] of Object.entries(data.train_lines)) {
            const loadPct = (line.line_load * 100).toFixed(0);
            const loadClass = line.line_load > 0.8 ? 'critical' : line.line_load > 0.6 ? 'busy' : line.line_load > 0.4 ? 'moderate' : 'good';
            const disrupted = line.disruption_level > 0.1;
            const actions = line.actions_this_hour && line.actions_this_hour.length > 0
                ? line.actions_this_hour.join(', ') : '';

            html += `<div class="train-status-row">
                <span class="train-line-badge" style="background:${line.color}">${id}</span>
                <span class="train-line-name">${line.line_name}</span>
                <span class="train-load ${loadClass}">${loadPct}%</span>
                <span class="train-freq">${line.frequency}/h</span>
                ${disrupted ? '<span class="train-disruption">\u26A0\uFE0F</span>' : ''}
                ${actions ? `<span class="train-action-tag">${actions}</span>` : ''}
            </div>`;
        }
        trainsDiv.innerHTML = html || '<div class="no-events">All lines normal</div>';
    }

    // District alerts
    const distDiv = document.getElementById('events-districts');
    if (data.districts) {
        let alerts = '';
        for (const [name, d] of Object.entries(data.districts)) {
            const issues = [];
            if (d.station_crowding > 0.7) issues.push(`Crowding ${(d.station_crowding*100).toFixed(0)}%`);
            if (d.bus_load_factor > 0.85) issues.push(`Bus ${(d.bus_load_factor*100).toFixed(0)}%`);
            if (d.road_traffic > 0.7) issues.push(`Traffic ${(d.road_traffic*100).toFixed(0)}%`);
            if (d.air_quality < 60) issues.push(`Air ${d.air_quality.toFixed(0)}`);
            if (issues.length > 0) {
                alerts += `<div class="district-alert"><span class="district-alert-name">${name}</span><span class="district-alert-issues">${issues.join(' | ')}</span></div>`;
            }
        }
        distDiv.innerHTML = alerts || '<div class="no-events">All districts nominal</div>';
    }

    // City events
    const cityDiv = document.getElementById('events-city');
    const events = data.active_events || [];
    if (events.length > 0) {
        cityDiv.innerHTML = events.map(ev => `
            <div class="event-card">
                <span class="event-icon">${ev.icon}</span>
                <div class="event-info">
                    <div class="event-name">${ev.name}</div>
                    <div class="event-details">Affects: ${ev.districts.join(', ')} | +${((ev.demand_mult-1)*100).toFixed(0)}% demand | ${ev.remaining_hours}h left</div>
                </div>
            </div>`).join('');
    } else {
        cityDiv.innerHTML = '<div class="no-events">No active events</div>';
    }
}

// ========== Helpers ==========
function updateMetric(id, value, warn, crit) {
    const el = document.getElementById(id);
    el.textContent = (value * 100).toFixed(1) + '%';
    el.className = 'metric-value ' + (value > crit ? 'critical' : value > warn ? 'busy' : value > warn * 0.7 ? 'moderate' : 'good');
}

function updateChart(history) {
    if (!history || history.length === 0) return;
    scoreChart.data.labels = history.map(h => `${String(h.hour).padStart(2,'0')}:00`);
    scoreChart.data.datasets[0].data = history.map(h => h.scores.liveability_score);
    scoreChart.data.datasets[1].data = history.map(h => h.scores.environment_score);
    scoreChart.update('none');
}

function disableControls() {
    document.getElementById('btn-simulate').disabled = true;
}
function enableControls() {
    document.getElementById('btn-simulate').disabled = false;
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

function showError(msg) {
    console.error(msg);
}
