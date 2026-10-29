// Classroom Intelligence Agent Dashboard Controller
let currentSessionId = null;
let liveIntervalTimer = null;
let engagementChart = null;

const chartData = {
    labels: [],
    datasets: [
        {
            label: 'Composite Engagement',
            data: [],
            borderColor: '#38bdf8',
            backgroundColor: 'rgba(56, 189, 248, 0.15)',
            borderWidth: 2.5,
            tension: 0.3,
            fill: true
        },
        {
            label: 'Visual Attention (65%)',
            data: [],
            borderColor: '#22c55e',
            borderWidth: 1.5,
            tension: 0.3,
            borderDash: [4, 4],
            fill: false
        },
        {
            label: 'Audio Activity (35%)',
            data: [],
            borderColor: '#f59e0b',
            borderWidth: 1.5,
            tension: 0.3,
            borderDash: [2, 2],
            fill: false
        }
    ]
};

// Initialize Chart
function initChart() {
    const ctx = document.getElementById('engagementChart').getContext('2d');
    engagementChart = new Chart(ctx, {
        type: 'line',
        data: chartData,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    title: { display: true, text: 'Session Time (Seconds)', color: '#94a3b8' },
                    grid: { color: 'rgba(51, 65, 85, 0.4)' },
                    ticks: { color: '#94a3b8' }
                },
                y: {
                    min: 0,
                    max: 100,
                    title: { display: true, text: 'Index (0 - 100%)', color: '#94a3b8' },
                    grid: { color: 'rgba(51, 65, 85, 0.4)' },
                    ticks: { color: '#94a3b8' }
                }
            },
            plugins: {
                legend: {
                    labels: { color: '#f8fafc', font: { size: 11 } }
                }
            }
        }
    });
}

function resetChart() {
    chartData.labels = [];
    chartData.datasets[0].data = [];
    chartData.datasets[1].data = [];
    chartData.datasets[2].data = [];
    if (engagementChart) engagementChart.update();
}

function appendChartPoint(timestampSec, composite, visual, audio) {
    chartData.labels.push(`${Math.round(timestampSec)}s`);
    chartData.datasets[0].data.push(composite);
    chartData.datasets[1].data.push(visual);
    chartData.datasets[2].data.push(audio);
    
    // Keep max 60 points on screen for real-time smoothness
    if (chartData.labels.length > 60) {
        chartData.labels.shift();
        chartData.datasets[0].data.shift();
        chartData.datasets[1].data.shift();
        chartData.datasets[2].data.shift();
    }
    if (engagementChart) engagementChart.update('none');
}

// Fetch session list
async function loadSessionsList() {
    try {
        const res = await fetch('/api/sessions');
        const data = await res.json();
        const select = document.getElementById('sessionSelect');
        select.innerHTML = '<option value="">-- Active Live Stream --</option>';
        (data.sessions || []).forEach(s => {
            const opt = document.createElement('option');
            opt.value = s.session_id;
            opt.textContent = `${s.session_id} - ${s.title} (${s.status})`;
            select.appendChild(opt);
        });
    } catch (err) {
        console.error('Failed loading sessions:', err);
    }
}

// Update UI Stat Cards
function updateStatCards(telemetry, attendanceSummary, audioDetails) {
    if (telemetry) {
        document.getElementById('statEngagementScore').textContent = `${telemetry.composite_engagement}%`;
        document.getElementById('statEngagementSub').textContent = 
            `Visual: ${telemetry.visual_attention_score}% | Audio: ${telemetry.audio_activity_score}%`;
        
        const stateEl = document.getElementById('statStateTag');
        stateEl.textContent = telemetry.state_tag;
        stateEl.style.backgroundColor = getStateColor(telemetry.state_tag);
    }

    if (attendanceSummary) {
        const total = attendanceSummary.total_enrolled || 10;
        const presentCount = attendanceSummary.currently_present_count || 0;
        const rate = Math.round((presentCount / total) * 100);
        document.getElementById('statAttendanceRate').textContent = `${rate}%`;
        document.getElementById('statAttendanceSub').textContent = `Present: ${presentCount} / Total: ${total}`;
        document.getElementById('statActiveParticipants').textContent = `Tracking ${presentCount} active participants`;
    }

    if (audioDetails) {
        document.getElementById('statAudioState').textContent = formatStateLabel(audioDetails.acoustic_state);
        document.getElementById('statAcousticSub').textContent = 
            `RMS: ${audioDetails.rms_energy} | Silence: ${audioDetails.consecutive_silence_sec}s`;
    }
}

function formatStateLabel(str) {
    if (!str) return '--';
    return str.replace(/_/g, ' ');
}

function getStateColor(tag) {
    switch (tag) {
        case 'HIGH_INTERACTIVE_ENGAGEMENT':
        case 'OPTIMAL_ATTENTIVE_LECTURE':
            return 'rgba(34, 197, 94, 0.25)';
        case 'ATTENTION_DROPOFF':
        case 'DISENGAGED_OR_TIRED':
            return 'rgba(239, 68, 68, 0.3)';
        case 'DISRUPTIVE_DISTRACTION':
            return 'rgba(234, 179, 8, 0.3)';
        default:
            return 'rgba(56, 189, 248, 0.2)';
    }
}

// Render Student Behavioral Grid
function renderStudentGrid(studentDetails, attendanceList) {
    const grid = document.getElementById('studentGrid');
    grid.innerHTML = '';

    const list = attendanceList || Object.keys(studentDetails || {}).map(id => ({
        student_id: id,
        name: id,
        metrics: studentDetails[id]
    }));

    list.forEach(item => {
        const details = item.metrics || (studentDetails ? studentDetails[item.student_id] : null);
        const score = details ? details.attention_score : '--';
        const stateLabel = details ? details.state_label : 'TRACKING';
        const displayName = item.display_name || item.name || item.student_id;
        const initials = displayName.split(' ').map(n => n[0]).join('').substring(0, 2);

        const card = document.createElement('div');
        card.className = 'student-card';
        card.innerHTML = `
            <div class="student-avatar">${initials}</div>
            <div class="student-name" title="${displayName}">${displayName}</div>
            <div class="student-score">${score}%</div>
            <div class="student-tag">${formatStateLabel(stateLabel)}</div>
        `;
        grid.appendChild(card);
    });
}

// Append AI Teaching Suggestion
function addSuggestionItem(sugg) {
    const list = document.getElementById('suggestionsList');
    if (list.querySelector('.empty-state')) {
        list.innerHTML = '';
    }

    const item = document.createElement('div');
    item.className = `suggestion-item ${sugg.severity}`;
    item.innerHTML = `
        <div class="suggestion-header">
            <span class="suggestion-category">[${sugg.category}] ${sugg.severity}</span>
            <span class="suggestion-time">${Math.round(sugg.timestamp_sec)}s</span>
        </div>
        <div class="suggestion-text">${sugg.suggestion_text}</div>
    `;
    list.prepend(item);
}

// Render Attendance Table
function renderAttendanceTable(records) {
    const tbody = document.querySelector('#attendanceTable tbody');
    tbody.innerHTML = '';

    if (!records || records.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center">No attendance records yet.</td></tr>';
        return;
    }

    records.forEach(r => {
        const tr = document.createElement('tr');
        const ratioPct = Math.round((r.presence_ratio || 0) * 100);
        const firstSeen = r.first_seen_sec !== null && r.first_seen_sec !== undefined ? `${Math.round(r.first_seen_sec)}s` : 'N/A';
        const totalSec = r.total_present_sec !== undefined ? `${Math.round(r.total_present_sec)}s` : '--';
        const name = r.display_name || r.name || r.student_id;

        tr.innerHTML = `
            <td><strong>${name}</strong> <span style="color:#64748b; font-size:0.7rem;">(${r.student_id})</span></td>
            <td><span class="status-badge status-${r.status}">${r.status}</span></td>
            <td>${ratioPct}%</td>
            <td>${totalSec}</td>
            <td>${firstSeen}</td>
            <td style="color:#94a3b8; font-size:0.75rem;">${r.notes || 'Normal presence'}</td>
        `;
        tbody.appendChild(tr);
    });
}

// Step Live Simulation
async function stepSimulation() {
    try {
        const res = await fetch('/api/sessions/step', { method: 'POST' });
        const data = await res.json();

        if (data.status === 'COMPLETED') {
            pauseLiveStream();
            loadSessionDetails(data.session_id);
            alert(`Session ${data.session_id} has concluded! Final attendance and summary computed.`);
            return;
        }

        const t = data.telemetry;
        appendChartPoint(t.timestamp_sec, t.composite_engagement, t.visual_attention_score, t.audio_activity_score);
        updateStatCards(t, data.attendance_summary, data.audio_details);

        if (data.visual_details && data.visual_details.student_details) {
            renderStudentGrid(data.visual_details.student_details);
        }

        if (data.latest_suggestion) {
            addSuggestionItem(data.latest_suggestion);
        }
    } catch (err) {
        console.error('Step failed:', err);
    }
}

// Start Live Stream Simulation
async function startLiveStream() {
    pauseLiveStream();
    resetChart();
    document.getElementById('suggestionsList').innerHTML = '<div class="empty-state">Monitoring session dynamics...</div>';

    const res = await fetch('/api/sessions/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            title: "Advanced Multimodal Perception & Cognition",
            course: "CS-601",
            duration_sec: 180.0,
            step_sec: 5.0
        })
    });
    const data = await res.json();
    currentSessionId = data.session_id;

    document.getElementById('btnStep').disabled = false;
    document.getElementById('btnStartLive').style.display = 'none';
    document.getElementById('btnPauseLive').style.display = 'inline-block';

    // Step immediately and then every 2 seconds
    await stepSimulation();
    liveIntervalTimer = setInterval(stepSimulation, 2000);
}

function pauseLiveStream() {
    if (liveIntervalTimer) {
        clearInterval(liveIntervalTimer);
        liveIntervalTimer = null;
    }
    document.getElementById('btnStartLive').style.display = 'inline-block';
    document.getElementById('btnPauseLive').style.display = 'none';
}

// Run Full Fast Demo Simulation
async function runFullSimulation() {
    pauseLiveStream();
    resetChart();
    document.getElementById('btnRunFull').textContent = '⏳ Processing offline...';
    document.getElementById('btnRunFull').disabled = true;

    try {
        const res = await fetch('/api/sessions/run_full_sim', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title: "Cognitive AI in Physical Education Systems",
                course: "EDU-701",
                duration_sec: 180.0,
                step_sec: 5.0
            })
        });
        const data = await res.json();
        currentSessionId = data.session_id;
        await loadSessionDetails(currentSessionId);
        await loadSessionsList();
    } catch (err) {
        console.error('Full simulation failed:', err);
    } finally {
        document.getElementById('btnRunFull').textContent = '▶ Run Full Session Demo';
        document.getElementById('btnRunFull').disabled = false;
    }
}

// Load and Display Historical or Completed Session
async function loadSessionDetails(sessionId) {
    if (!sessionId) return;
    currentSessionId = sessionId;
    const res = await fetch(`/api/sessions/${sessionId}`);
    const data = await res.json();

    // Reset and populate chart with full telemetry
    resetChart();
    (data.telemetry || []).forEach(row => {
        appendChartPoint(row.timestamp_sec, row.composite_engagement, row.visual_attention_score, row.audio_activity_score);
    });

    // Populate suggestions
    const suggList = document.getElementById('suggestionsList');
    suggList.innerHTML = '';
    (data.suggestions || []).forEach(s => addSuggestionItem(s));
    if ((data.suggestions || []).length === 0) {
        suggList.innerHTML = '<div class="empty-state">No pedagogical alerts recorded for this session.</div>';
    }

    // Populate attendance
    renderAttendanceTable(data.attendance);

    // Populate stats
    if (data.metrics) {
        document.getElementById('statAttendanceRate').textContent = `${data.metrics.attendance_rate_percent}%`;
        document.getElementById('statAttendanceSub').textContent = 
            `Present: ${data.metrics.present_count} | Tardy: ${data.metrics.tardy_count} | Absent: ${data.metrics.absent_count}`;
        document.getElementById('statEngagementScore').textContent = `${data.metrics.avg_engagement_score}%`;
        document.getElementById('statStateTag').textContent = 'COMPLETED';
        document.getElementById('statStateTag').style.backgroundColor = 'rgba(56, 189, 248, 0.2)';
    }

    // Populate Student Grid
    renderStudentGrid(null, data.attendance);
}

// Event Listeners
document.addEventListener('DOMContentLoaded', () => {
    initChart();
    loadSessionsList();

    document.getElementById('btnStartLive').addEventListener('click', startLiveStream);
    document.getElementById('btnPauseLive').addEventListener('click', pauseLiveStream);
    document.getElementById('btnStep').addEventListener('click', stepSimulation);
    document.getElementById('btnRunFull').addEventListener('click', runFullSimulation);

    document.getElementById('sessionSelect').addEventListener('change', (e) => {
        if (e.target.value) {
            pauseLiveStream();
            loadSessionDetails(e.target.value);
        }
    });

    document.getElementById('btnExportCsv').addEventListener('click', () => {
        if (!currentSessionId) {
            alert('Please start or select a session first to export attendance.');
            return;
        }
        window.location.href = `/api/sessions/${currentSessionId}/export_csv`;
    });

    document.getElementById('btnExportJson').addEventListener('click', async () => {
        if (!currentSessionId) {
            alert('Please start or select a session first to export data.');
            return;
        }
        window.open(`/api/sessions/${currentSessionId}`, '_blank');
    });

    document.getElementById('anonToggle').addEventListener('change', async (e) => {
        const isAnon = e.target.checked;
        await fetch('/api/settings/privacy', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ anonymize: isAnon })
        });
        if (currentSessionId) {
            loadSessionDetails(currentSessionId);
        }
    });
});

