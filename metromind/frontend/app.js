// MetroMind v2 - Smart Transit AI Dashboard
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

const NO_SERVICE_HOURS = new Set([1, 2, 3, 4, 5]);

// ========== Init ==========
document.addEventListener('DOMContentLoaded', () => {
    initChart();
    fetchState();
    document.getElementById('hour-select').addEventListener('change', () => simulateHour());
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
                { label: 'Cost Eff.', data: [], borderColor: '#ed8936', backgroundColor: 'rgba(237,137,54,0.1)', tension: 0.3, fill: true, pointRadius: 0 },
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
        document.getElementById('hour-select').value = data.time.hour;
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

async function stepHourPlus() {
    try {
        disableControls();
        await animateAgents();
        const r = await fetch(`${API_BASE}/api/step_hour?delta=1`, { method: 'POST' });
        const data = await r.json();
        document.getElementById('hour-select').value = data.time.hour;
        if (data.actions && data.actions.length > 0) animateInterventions(data.actions);
        updateUI(data);
    } catch (e) {
        console.error('Step+ error:', e);
        showError('Failed to step forward');
    } finally {
        resetAgents();
        enableControls();
    }
}

async function stepHourMinus() {
    try {
        disableControls();
        await animateAgents();
        const r = await fetch(`${API_BASE}/api/step_hour?delta=-1`, { method: 'POST' });
        const data = await r.json();
        document.getElementById('hour-select').value = data.time.hour;
        if (data.actions && data.actions.length > 0) animateInterventions(data.actions);
        updateUI(data);
    } catch (e) {
        console.error('Step- error:', e);
        showError('Failed to step backward');
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
        scoreChart.data.datasets.forEach(ds => ds.data = []);
        scoreChart.update();
        document.getElementById('hour-select').value = 8;
        document.getElementById('interventions-content').innerHTML = '<div class="no-events">Run a simulation step to see agent interventions</div>';
        document.getElementById('forecast-content').innerHTML = '<div class="no-events">Run simulation to see forecasts</div>';
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
    const states = ['Observing city...', 'Forecasting + planning...', 'Validating rules...', 'Allocating resources...', 'Executing...'];
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
                if (act.includes('DEPLOY_RESERVE')) text = '\uD83D\uDE8C ' + act;
                else if (act.includes('SHORT_TURN')) text = '\uD83D\uDE8C Short Turn';
                else if (act.includes('HOLD_AT_TERMINAL')) text = '\u23F8 Hold';
                else if (act.includes('REROUTE')) text = '\u21BB Reroute';
                else if (act.includes('CROWD')) text = '\uD83D\uDC65 Managed';
                else if (act.includes('ADVISORY')) text = '\uD83D\uDCE2 Advisory';
                else if (act.includes('ESCALATE')) text = '\u26A0 Escalate';
                else if (act.includes('TRAIN')) text = '\uD83D\uDE87 ' + act;
                if (text) {
                    const el = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                    el.setAttribute('x', c.x);
                    el.setAttribute('y', c.y - 10 - j * 15);
                    el.setAttribute('class', 'intervention-text float-animation');
                    el.textContent = text;
                    layer.appendChild(el);
                    setTimeout(() => el.remove(), 1500);
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

    // No-service banner
    const noService = data.no_service || NO_SERVICE_HOURS.has(hour);
    const banner = document.getElementById('no-service-banner');
    banner.classList.toggle('hidden', !noService);

    // Scores
    document.getElementById('header-liveability').textContent = data.scores.liveability_score.toFixed(1);
    document.getElementById('header-environment').textContent = data.scores.environment_score.toFixed(1);
    // Cost efficiency score (v2)
    if (data.scores.cost_score !== undefined) {
        document.getElementById('header-cost').textContent = data.scores.cost_score.toFixed(1);
    }

    // Weather
    updateWeather(data.weather);

    // Service Unit Capacities
    if (data.capacities) {
        const busActive = data.capacities.bus_service_units_active;
        const busMax = data.capacities.bus_service_units_max;
        const trainActive = data.capacities.train_service_units_active;
        const trainMax = data.capacities.train_service_units_max;
        const busPct = busMax > 0 ? (busActive / busMax) * 100 : 0;
        const trainPct = trainMax > 0 ? (trainActive / trainMax) * 100 : 0;

        const busBar = document.getElementById('bus-budget-bar');
        busBar.style.width = `${busPct}%`;
        busBar.className = 'budget-fill bus-fill ' + capacityColor(busPct);

        const trainBar = document.getElementById('mrt-budget-bar');
        trainBar.style.width = `${trainPct}%`;
        trainBar.className = 'budget-fill mrt-fill ' + capacityColor(trainPct);

        document.getElementById('bus-budget-value').textContent = `${busActive} / ${busMax} active`;
        document.getElementById('mrt-budget-value').textContent = `${trainActive} / ${trainMax} active`;
    }

    // Cost (v2)
    if (data.cost) {
        const costHour = document.getElementById('cost-this-hour');
        const costDay = document.getElementById('cost-today');
        costHour.textContent = `${data.cost.cost_this_hour.toFixed(0)} CU`;
        costDay.textContent = `${data.cost.cost_today.toFixed(0)} CU`;
        costHour.className = 'cost-value' + (data.cost.cost_this_hour > 500 ? ' cost-high' : '');
    }

    // Forecast (v2)
    if (data.forecast) {
        updateForecastPanel(data.forecast, noService);
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
    updateBusMap(data.districts, noService);

    // Train map
    updateTrainMap(data.train_lines, noService);

    // Active Events panel
    updateActiveEventsPanel(data, noService);

    // Live Interventions
    if (data.agent_trace) {
        updateInterventionsPanel(data.agent_trace);
    }

    // Chart
    updateChart(data.history_tail);
}

// ========== Forecast Panel (v2) ==========
function updateForecastPanel(forecast, noService) {
    const container = document.getElementById('forecast-content');

    // During no-service hours, show glass banner
    if (noService) {
        container.innerHTML = `<div class="forecast-no-service">
            <span class="forecast-no-service-icon">\uD83D\uDEAB</span>
            <span class="forecast-no-service-text">No Bus/Train Service (01:00 \u2013 05:00)</span>
        </div>`;
        return;
    }

    let html = '';

    // District forecasts
    for (const [name, fc] of Object.entries(forecast.districts || {})) {
        const vals = fc.forecast || [];
        const current = fc.current_load || 0;
        const peak = Math.max(...vals);
        const peakClass = peak > 0.85 ? 'critical' : peak > 0.7 ? 'busy' : peak > 0.5 ? 'moderate' : 'good';

        html += `<div class="forecast-row">
            <span class="forecast-name">${name}</span>
            <span class="forecast-current">${(current*100).toFixed(0)}%</span>
            <div class="forecast-bars">`;
        vals.forEach((v, i) => {
            const pct = Math.min(100, v * 100);
            const cls = v > 0.85 ? 'critical' : v > 0.7 ? 'busy' : v > 0.5 ? 'moderate' : 'good';
            html += `<div class="forecast-bar-wrap" title="+${i+1}h: ${(v*100).toFixed(0)}%">
                <div class="forecast-bar ${cls}" style="height:${pct}%"></div>
                <span class="forecast-label">+${i+1}h</span>
            </div>`;
        });
        html += `</div>
            <span class="forecast-peak ${peakClass}">${(peak*100).toFixed(0)}%</span>
        </div>`;
    }

    // Forecast alerts
    const alerts = forecast.alerts || [];
    if (alerts.length > 0) {
        html += '<div class="forecast-alerts">';
        alerts.forEach(a => {
            html += `<div class="forecast-alert">${a}</div>`;
        });
        html += '</div>';
    }

    container.innerHTML = html || '<div class="no-events">No forecast data</div>';
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
function updateBusMap(districts, noService) {
    for (const [name, d] of Object.entries(districts)) {
        const el = document.getElementById(`district-${name.toLowerCase()}`);
        if (!el) continue;
        const shape = el.querySelector('.district-shape');
        const stats = document.getElementById(`${name.toLowerCase()}-stats`);

        shape.classList.remove('load-low', 'load-moderate', 'load-busy', 'load-critical', 'no-service-district');

        if (noService) {
            shape.classList.add('no-service-district');
            stats.textContent = 'No Service';
        } else {
            const avg = (d.bus_load_factor + d.mrt_load_factor + d.station_crowding) / 3;
            if (avg > 0.8) shape.classList.add('load-critical');
            else if (avg > 0.6) shape.classList.add('load-busy');
            else if (avg > 0.35) shape.classList.add('load-moderate');
            else shape.classList.add('load-low');
            stats.textContent = `${(avg*100).toFixed(0)}% load`;
        }
    }
}

// ========== Train Map ==========
function updateTrainMap(trainLines, noService) {
    if (!trainLines) return;

    for (const [id, line] of Object.entries(trainLines)) {
        const lid = id.toLowerCase();
        const infoEl = document.getElementById(`${lid}-info`);
        const actionEl = document.getElementById(`${lid}-action`);
        const pathEl = document.getElementById(`${lid}-path`);

        if (noService) {
            if (infoEl) infoEl.textContent = 'No Service';
            if (actionEl) {
                actionEl.textContent = 'Out of service (01:00-05:00)';
                actionEl.setAttribute('fill', '#718096');
            }
            if (pathEl) {
                pathEl.setAttribute('opacity', '0.2');
                pathEl.setAttribute('stroke-width', '4');
                pathEl.setAttribute('stroke-dasharray', '8,6');
            }
        } else {
            if (infoEl) infoEl.textContent = `Load: ${(line.line_load*100).toFixed(0)}% | Freq: ${line.frequency}/h`;
            if (actionEl) {
                const acts = line.actions_this_hour;
                actionEl.textContent = acts && acts.length > 0 ? acts.join(', ') : 'No actions';
                actionEl.setAttribute('fill', acts && acts.length > 0 ? '#4fd1c5' : '#718096');
            }
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
}

// ========== Live Interventions Panel ==========
function updateInterventionsPanel(trace) {
    const container = document.getElementById('interventions-content');
    const hourStr = String(trace.hour).padStart(2, '0') + ':00';
    let html = `<div class="intervention-timestamp">${hourStr}</div>`;

    if (trace.no_service) {
        html += `<div class="intervention-standby">
            <div class="intervention-banner">Out of Operating Hours (01:00-05:00)</div>
            <div class="intervention-note">All agents in standby mode. No bus/train service.</div>
        </div>`;
    }

    // Monitoring
    const alerts = trace.monitoring?.alerts || [];
    html += `<div class="intervention-section">
        <div class="intervention-agent"><span class="intervention-agent-icon">\uD83D\uDC41\uFE0F</span> Monitor</div>`;
    if (alerts.length > 0) {
        html += '<ul class="intervention-list">' + alerts.map(a => `<li>${a}</li>`).join('') + '</ul>';
    } else {
        html += '<div class="intervention-quiet">No alerts detected</div>';
    }
    html += '</div>';

    // Planner
    const planner = trace.planner || {};
    html += `<div class="intervention-section">
        <div class="intervention-agent"><span class="intervention-agent-icon">\uD83D\uDCCB</span> Planner</div>`;
    if (planner.note) {
        html += `<div class="intervention-quiet">${planner.note}</div>`;
    } else {
        const reasons = planner.reasoning || [];
        if (reasons.length > 0) {
            html += '<ul class="intervention-list reasoning-items">' + reasons.map(r => `<li>${r}</li>`).join('') + '</ul>';
        } else {
            html += '<div class="intervention-quiet">No capacity changes needed — demand within targets</div>';
        }
    }
    html += '</div>';

    // Policy
    const policy = trace.policy || {};
    html += `<div class="intervention-section">
        <div class="intervention-agent"><span class="intervention-agent-icon">\u2696\uFE0F</span> Policy</div>`;
    if (policy.note) {
        html += `<div class="intervention-quiet">${policy.note}</div>`;
    } else {
        const pItems = [...(policy.blocked || []), ...(policy.adjustments || [])];
        if (pItems.length > 0) {
            html += '<ul class="intervention-list policy-items">' + pItems.map(i => `<li>${i}</li>`).join('') + '</ul>';
        } else {
            html += '<div class="intervention-quiet">All proposals valid</div>';
        }
    }
    html += '</div>';

    // Coordinator
    const coord = trace.coordinator || {};
    html += `<div class="intervention-section">
        <div class="intervention-agent"><span class="intervention-agent-icon">\uD83C\uDFAF</span> Coordinator</div>`;
    if (coord.note) {
        html += `<div class="intervention-quiet">${coord.note}</div>`;
    } else {
        const allocs = coord.allocations || [];
        if (allocs.length > 0) {
            html += '<ul class="intervention-list">' + allocs.map(a => `<li>${a}</li>`).join('') + '</ul>';
        } else {
            html += '<div class="intervention-quiet">No allocations needed</div>';
        }
        if (coord.remaining_capacity) {
            const rc = coord.remaining_capacity;
            html += `<div class="intervention-remaining">Available: ${rc.bus_service_units || 0} bus units, ${rc.train_service_units || 0} train units (after reserve)</div>`;
        }
    }
    html += '</div>';

    // Executor
    const exec = trace.executor || {};
    html += `<div class="intervention-section">
        <div class="intervention-agent"><span class="intervention-agent-icon">\u26A1</span> Executor</div>`;
    if (exec.note) {
        html += `<div class="intervention-quiet">${exec.note}</div>`;
    } else {
        const applied = exec.applied || [];
        if (applied.length > 0) {
            const flat = applied.flat();
            html += '<ul class="intervention-list exec-items">' + flat.map(a => `<li>${a}</li>`).join('') + '</ul>';
        } else {
            html += '<div class="intervention-quiet">No actions executed</div>';
        }
    }
    html += '</div>';

    // Escalations (v2)
    const escalations = trace.escalations || [];
    if (escalations.length > 0) {
        html += `<div class="intervention-section escalation-section">
            <div class="intervention-agent"><span class="intervention-agent-icon">\u26A0\uFE0F</span> Operator Escalation</div>
            <ul class="intervention-list escalation-items">`;
        escalations.forEach(e => {
            html += `<li>${e.reason} (${e.district || e.line_id})</li>`;
        });
        html += '</ul></div>';
    }

    // Environment
    const env = trace.env || {};
    html += `<div class="intervention-section">
        <div class="intervention-agent"><span class="intervention-agent-icon">\uD83C\uDF0D</span> Environment</div>`;
    const envItems = [];
    if (env.events_triggered && env.events_triggered.length > 0) envItems.push(...env.events_triggered.map(e => `Event triggered: ${e}`));
    if (env.emissions !== undefined) envItems.push(`Emissions: ${env.emissions} kg CO2`);
    if (env.cost_this_hour !== undefined) envItems.push(`Operating cost: ${env.cost_this_hour} CU`);
    if (envItems.length > 0) {
        html += '<ul class="intervention-list">' + envItems.map(i => `<li>${i}</li>`).join('') + '</ul>';
    } else {
        html += '<div class="intervention-quiet">Normal environment cycle</div>';
    }
    html += '</div>';

    container.innerHTML = html;
}

// ========== Active Events Panel ==========
function updateActiveEventsPanel(data, noService) {
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
        if (noService) {
            html = '<div class="no-service-event-card">No Service (01:00-05:00)</div>';
        } else {
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
        }
        trainsDiv.innerHTML = html || '<div class="no-events">All lines normal</div>';
    }

    // District alerts
    const distDiv = document.getElementById('events-districts');
    if (data.districts) {
        let alerts = '';
        if (noService) {
            alerts = '<div class="no-service-event-card">No Service - Stations closed</div>';
        } else {
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
        }
        distDiv.innerHTML = alerts || '<div class="no-events">All districts nominal</div>';
    }

    // City events
    const cityDiv = document.getElementById('events-city');
    const events = data.active_events || [];
    if (events.length > 0) {
        cityDiv.innerHTML = events.map(ev => `
            <div class="event-card${ev.road_incident ? ' road-incident' : ''}">
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
    scoreChart.data.datasets[2].data = history.map(h => h.scores.cost_score || 0);
    scoreChart.update('none');
}

function disableControls() {
    document.getElementById('btn-hour-minus').disabled = true;
    document.getElementById('btn-hour-plus').disabled = true;
    document.getElementById('hour-select').disabled = true;
}
function enableControls() {
    document.getElementById('btn-hour-minus').disabled = false;
    document.getElementById('btn-hour-plus').disabled = false;
    document.getElementById('hour-select').disabled = false;
}

function capacityColor(pct) {
    if (pct > 90) return 'cap-red';
    if (pct > 70) return 'cap-yellow';
    return 'cap-green';
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

function showError(msg) {
    console.error(msg);
}
