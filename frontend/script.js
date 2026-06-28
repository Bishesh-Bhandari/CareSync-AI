/* ═══════════════════════════════════════════════
   HealthSync AI — Frontend Logic
   ═══════════════════════════════════════════════ */

// ── Helpers ──

function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add('show'));
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

async function api(url, options = {}) {
    try {
        const res = await fetch(url, {
            headers: { 'Content-Type': 'application/json', ...options.headers },
            ...options
        });
        const data = await res.json();
        if (!res.ok) {
            throw new Error(data.error || 'Request failed');
        }
        return data;
    } catch (err) {
        throw err;
    }
}

// ── Auth: Register ──

const registerForm = document.getElementById('registerForm');
if (registerForm) {
    registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const errEl = document.getElementById('registerError');
        errEl.style.display = 'none';

        try {
            await api('/api/register', {
                method: 'POST',
                body: JSON.stringify({
                    full_name: document.getElementById('fullName').value.trim(),
                    username: document.getElementById('username').value.trim(),
                    email: document.getElementById('email').value.trim(),
                    password: document.getElementById('password').value
                })
            });
            showToast('Account created! Please log in.', 'success');
            setTimeout(() => window.location.href = '/login', 800);
        } catch (err) {
            errEl.textContent = err.message;
            errEl.style.display = 'block';
        }
    });
}

// ── Auth: Login ──

const loginForm = document.getElementById('loginForm');
if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const errEl = document.getElementById('loginError');
        errEl.style.display = 'none';

        try {
         await api('/api/login', {
                method: 'POST',
                body: JSON.stringify({
                    email: document.getElementById('email').value.trim(),
                    password: document.getElementById('password').value
                })
            });
            showToast('Welcome back!', 'success');
            setTimeout(() => window.location.href = '/dashboard', 600);
        } catch (err) {
            errEl.textContent = err.message;
            errEl.style.display = 'block';
        }
    });
}

// ── Auth: Logout ──

const logoutBtn = document.getElementById('logoutBtn');
if (logoutBtn) {
    logoutBtn.addEventListener('click', async () => {
        await api('/api/logout', { method: 'POST' });
        window.location.href = '/login';
    });
}

// ── Dashboard ──

let trajectoryChart = null;

async function loadDashboard() {
    try {
        const data = await api('/api/dashboard');
        renderDashboard(data);
    } catch (err) {
        if (err.message === 'Not authenticated' || err.message === 'User not found') {
            window.location.href = '/login';
        } else {
            showToast('Failed to load dashboard: ' + err.message, 'error');
        }
    }
}

function renderDashboard(data) {
    const { user, latest, trend, trend_percent, active_symptoms, chart, heatmap, summary, checkins } = data;

    // User info
    document.getElementById('userMenuName').textContent = user.name;
    document.getElementById('userAvatar').textContent = user.name.charAt(0).toUpperCase();
    document.getElementById('patientName').textContent = user.name;
    document.getElementById('patientEmail').textContent = user.email;
    document.getElementById('patientSince').textContent = user.member_since;
    document.getElementById('patientCheckins').textContent = user.total_checkins;

    // Trend badge
    const trendBadge = document.getElementById('trendBadge');
    const trendLabels = { improving: 'Improving', worsening: 'Worsening', stable: 'Stable' };
    const trendArrows = { improving: '\u2191', worsening: '\u2193', stable: '\u2192' };
    trendBadge.innerHTML = `<span class="trend-badge ${trend}">${trendLabels[trend]} ${trendArrows[trend]} ${trend_percent}%</span>`;

    // Health ring
    const score = latest ? latest.health_score : 0;
    const ring = document.getElementById('healthRing');
    const circumference = 2 * Math.PI * 50; // r=50
    const offset = circumference * (1 - score / 100);
    ring.style.strokeDasharray = circumference;
    ring.style.strokeDashoffset = circumference;
    document.getElementById('ringScore').textContent = score || '—';

    // Color the ring based on score
    if (score >= 70) ring.style.stroke = 'var(--green)';
    else if (score >= 40) ring.style.stroke = 'var(--amber)';
    else if (score > 0) ring.style.stroke = 'var(--red)';
    else ring.style.stroke = 'var(--primary)';

    // Animate ring after a short delay
    setTimeout(() => { ring.style.strokeDashoffset = offset; }, 100);

    document.getElementById('ringCaption').textContent = latest
        ? `Severity ${latest.severity}/10`
        : 'No data yet';

    // Quick stats
    const quickStats = document.getElementById('quickStats');
    quickStats.innerHTML = `
        <div class="quick-stat">
            <span class="quick-stat-dot" style="background:var(--primary)"></span>
            <span class="quick-stat-label">Active symptoms</span>
            <span class="quick-stat-value">${active_symptoms.length}</span>
        </div>
        <div class="quick-stat">
            <span class="quick-stat-dot" style="background:var(--amber)"></span>
            <span class="quick-stat-label">Avg severity</span>
            <span class="quick-stat-value">${checkins.length ? (checkins.reduce((a, c) => a + c.severity, 0) / checkins.length).toFixed(1) : '—'}</span>
        </div>
        <div class="quick-stat">
            <span class="quick-stat-dot" style="background:var(--green)"></span>
            <span class="quick-stat-label">Latest mood</span>
            <span class="quick-stat-value">${latest ? latest.mood.charAt(0).toUpperCase() + latest.mood.slice(1) : '—'}</span>
        </div>
    `;

    // Chart
    renderChart(chart);

    // Status grid
    renderStatusGrid(data);

    // Heatmap
    renderHeatmap(heatmap);

    // Clinical brief
    renderSummary(summary);

    // Timeline
    renderTimeline(checkins);
}

// ── Chart ──

function renderChart(chartData) {
    const ctx = document.getElementById('trajectoryChart');
    if (!ctx) return;

    if (trajectoryChart) {
        trajectoryChart.destroy();
    }

    if (!chartData.labels.length) {
        ctx.parentElement.innerHTML = '<div class="empty-state"><p>Submit check-ins to see your health trajectory</p></div>';
        return;
    }

    trajectoryChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: chartData.labels,
            datasets: [{
                label: 'Health Score',
                data: chartData.scores,
                borderWidth: 3,
                pointRadius: 6,
                pointHoverRadius: 9,
                pointBackgroundColor: '#fff',
                pointBorderWidth: 2.5,
                tension: 0.35,
                fill: true,
                backgroundColor: 'rgba(13, 148, 136, 0.08)',
                segment: {
                    borderColor: function(ctx) {
                        if (!ctx.p0 || !ctx.p1) return '#0D9488';
                        const prev = ctx.p0.parsed.y;
                        const curr = ctx.p1.parsed.y;
                        if (curr > prev) return '#22C55E';
                        if (curr < prev) return '#EF4444';
                        return '#F59E0B';
                    },
                    backgroundColor: function(ctx) {
                        if (!ctx.p0 || !ctx.p1) return 'rgba(13,148,136,0.08)';
                        const prev = ctx.p0.parsed.y;
                        const curr = ctx.p1.parsed.y;
                        if (curr > prev) return 'rgba(34, 197, 94, 0.08)';
                        if (curr < prev) return 'rgba(239, 68, 68, 0.08)';
                        return 'rgba(245, 158, 11, 0.08)';
                    }
                },
                pointBorderColor: function(ctx) {
                    const val = ctx.parsed ? ctx.parsed.y : 50;
                    if (val >= 70) return '#22C55E';
                    if (val >= 40) return '#F59E0B';
                    return '#EF4444';
                }
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { intersect: false, mode: 'index' },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#1E293B',
                    titleFont: { family: 'DM Sans', size: 12 },
                    bodyFont: { family: 'DM Sans', size: 13, weight: '600' },
                    padding: 12,
                    cornerRadius: 8,
                    displayColors: false,
                    callbacks: {
                        title: function(items) { return items[0].label; },
                        label: function(ctx) {
                            const score = ctx.parsed.y;
                            const sev = 10 - Math.round(score / 10);
                            return `Health Score: ${score}/100  |  Severity: ${sev}/10`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    min: 0, max: 100,
                    grid: { color: 'rgba(0,0,0,0.04)', drawBorder: false },
                    ticks: {
                        font: { family: 'DM Sans', size: 11 },
                        color: '#94A3B8',
                        stepSize: 20,
                        callback: v => v
                    },
                    border: { display: false }
                },
                x: {
                    grid: { display: false },
                    ticks: {
                        font: { family: 'DM Sans', size: 11 },
                        color: '#94A3B8',
                        maxRotation: 45
                    },
                    border: { display: false }
                }
            }
        }
    });
}

// ── Status Grid ──

function renderStatusGrid(data) {
    const grid = document.getElementById('statusGrid');
    const { trend, active_symptoms, latest, checkins } = data;
    const severity = latest ? latest.severity : 0;
    const score = latest ? latest.health_score : 0;
    const trendClass = trend;

    grid.innerHTML = `
        <div class="status-item ${trendClass}">
            <div class="status-label">Overall Trend</div>
            <div class="status-value">${trend.charAt(0).toUpperCase() + trend.slice(1)}</div>
        </div>
        <div class="status-item ${severity <= 3 ? 'improving' : severity <= 6 ? 'stable' : 'worsening'}">
            <div class="status-label">Current Severity</div>
            <div class="status-value">${severity}/10</div>
        </div>
        <div class="status-item ${score >= 70 ? 'improving' : score >= 40 ? 'stable' : 'worsening'}">
            <div class="status-label">Health Score</div>
            <div class="status-value">${score}/100</div>
        </div>
        <div class="status-item ${active_symptoms.length <= 2 ? 'improving' : active_symptoms.length <= 4 ? 'stable' : 'worsening'}">
            <div class="status-label">Active Symptoms</div>
            <div class="status-value">${active_symptoms.length}</div>
        </div>
    `;
}

// ── Symptom Heatmap ──

function renderHeatmap(heatmapData) {
    const container = document.getElementById('heatmapContainer');
    const empty = document.getElementById('heatmapEmpty');

    if (!heatmapData.symptoms.length) {
        if (empty) empty.style.display = 'block';
        return;
    }
    if (empty) empty.style.display = 'none';

    let html = `<div class="heatmap-grid" style="grid-template-columns: 100px repeat(${heatmapData.dates.length}, 48px);">`;

    // Header row
    html += '<div class="heatmap-cell header"></div>';
    heatmapData.dates.forEach(d => {
        const short = d.substring(5); // MM-DD
        html += `<div class="heatmap-cell header">${short}</div>`;
    });

    // Data rows
    heatmapData.symptoms.forEach((symptom, i) => {
        html += `<div class="heatmap-cell symptom-name">${symptom}</div>`;
        heatmapData.matrix[i].forEach(val => {
            let cls = 'empty';
            if (val >= 8) cls = 'severity-critical';
            else if (val >= 6) cls = 'severity-high';
            else if (val >= 3) cls = 'severity-mid';
            else if (val >= 1) cls = 'severity-low';
            html += `<div class="heatmap-cell ${cls}" title="${symptom}: ${val}/10">${val > 0 ? val : ''}</div>`;
        });
    });

    html += '</div>';
    container.innerHTML = html;
}

// ── Clinical Brief ──

function renderSummary(summary) {
    const el = document.getElementById('clinicalBrief');
    if (!summary || !summary.text) {
        el.textContent = 'No summary available.';
        return;
    }
    // Highlight FLAG lines safely
    el.innerHTML = summary.text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/^(FLAG:.*)$/gm, '<span class="flag-line">$1</span>');
}

// ── Check-in Timeline ──

function renderTimeline(checkins) {
    const container = document.getElementById('checkinTimeline');
    const empty = document.getElementById('timelineEmpty');

    if (!checkins.length) {
        if (empty) empty.style.display = 'block';
        return;
    }
    if (empty) empty.style.display = 'none';

    let html = '';
    checkins.forEach(c => {
        const dateObj = new Date(c.datetime + 'T00:00:00');
        const dateStr = dateObj.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });

        const tags = c.symptoms.map(s => {
            let cls = 'mild';
            if (s.severity >= 7) cls = 'severe';
            else if (s.severity >= 4) cls = 'moderate';
            return `<span class="symptom-tag ${cls}">${s.name} ${s.severity}/10</span>`;
        }).join('');

        // Safely escape user text to prevent XSS
        const safeText = c.text.replace(/[<>"&]/g, '');
        const safeMeds = c.medications ? c.medications.replace(/[<>"&]/g, '') : '';

        html += `
            <div class="timeline-item">
                <div class="timeline-dot-col"><div class="timeline-dot"></div></div>
                <div class="timeline-content">
                    <div class="timeline-date">${dateStr}</div>
                    <div class="timeline-symptoms">${tags}</div>
                    <div class="timeline-text">"${safeText}"</div>
                    <div class="timeline-meta">
                        <span>Mood: ${c.mood.charAt(0).toUpperCase() + c.mood.slice(1)}</span>
                        ${safeMeds ? `<span>Meds: ${safeMeds}</span>` : ''}
                        <span>Score: ${c.health_score}/100</span>
                    </div>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

// ── Check-in Modal ──

const newCheckinBtn = document.getElementById('newCheckinBtn');
const checkinModal = document.getElementById('checkinModal');
const cancelCheckin = document.getElementById('cancelCheckin');

if (newCheckinBtn) {
    newCheckinBtn.addEventListener('click', () => {
        checkinModal.classList.add('active');
        document.getElementById('symptomText').focus();
    });
}
if (cancelCheckin) {
    cancelCheckin.addEventListener('click', closeModal);
}
if (checkinModal) {
    checkinModal.addEventListener('click', (e) => {
        if (e.target === checkinModal) closeModal();
    });
}

function closeModal() {
    checkinModal.classList.remove('active');
    document.getElementById('checkinForm').reset();
    document.getElementById('checkinError').style.display = 'none';
    stopVoice();
}

const checkinForm = document.getElementById('checkinForm');
if (checkinForm) {
    checkinForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const errEl = document.getElementById('checkinError');
        errEl.style.display = 'none';

        const symptoms = document.getElementById('symptomText').value.trim();
        if (!symptoms) {
            errEl.textContent = 'Please describe your symptoms.';
            errEl.style.display = 'block';
            return;
        }

        try {
            const result = await api('/api/checkin', {
                method: 'POST',
                body: JSON.stringify({
                    symptoms: symptoms,
                    mood: document.getElementById('moodSelect').value,
                    medications: document.getElementById('medications').value.trim(),
                    notes: document.getElementById('notes').value.trim()
                })
            });

            showToast(`Check-in recorded! Severity: ${result.severity}/10`, 'success');
            closeModal();
            loadDashboard(); // Refresh dashboard
        } catch (err) {
            errEl.textContent = err.message;
            errEl.style.display = 'block';
        }
    });
}

// ── Refresh Summary ──

const refreshSummary = document.getElementById('refreshSummary');
if (refreshSummary) {
    refreshSummary.addEventListener('click', () => {
        showToast('Refreshing summary...', 'info');
        loadDashboard();
    });
}

// ── Voice Input ──

let recognition = null;
let isRecording = false;

const voiceBtn = document.getElementById('voiceBtn');
if (voiceBtn) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-US';

        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            const textarea = document.getElementById('symptomText');
            textarea.value = textarea.value ? textarea.value + ' ' + transcript : transcript;
            stopVoice();
        };

        recognition.onerror = () => { stopVoice(); };
        recognition.onend = () => { stopVoice(); };

        voiceBtn.addEventListener('click', () => {
            if (isRecording) {
                stopVoice();
            } else {
                startVoice();
            }
        });
    } else {
        voiceBtn.style.display = 'none'; // Browser doesn't support speech
    }
}

function startVoice() {
    if (!recognition) return;
    isRecording = true;
    voiceBtn.classList.add('recording');
    try { recognition.start(); } catch(e) { stopVoice(); }
}

function stopVoice() {
    isRecording = false;
    if (voiceBtn) voiceBtn.classList.remove('recording');
    try { recognition.stop(); } catch(e) {}
}

// ── Init: Load dashboard if on dashboard page ──

if (document.getElementById('trajectoryChart')) {
    loadDashboard();
}