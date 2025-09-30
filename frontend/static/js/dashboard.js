const timelineCtx = document.getElementById('timeline-chart').getContext('2d');
const partyCtx = document.getElementById('party-chart').getContext('2d');

let timelineChart;
let partyChart;
let cachedTimeline = [];
let cachedProgress = [];

const scopeTypeInput = document.getElementById('scope-type');
const scopeCodeInput = document.getElementById('scope-code');
const slider = document.getElementById('history-slider');
const countedEl = document.getElementById('counted-districts');
const totalVotesEl = document.getElementById('total-votes');
const turnoutEl = document.getElementById('turnout');
const speedEl = document.getElementById('speed');

async function fetchDashboardData() {
    const scopeType = scopeTypeInput.value;
    const scopeCode = scopeCodeInput.value;
    const [timelineRes, progressRes] = await Promise.all([
        fetch(`/api/dashboard?scope_type=${scopeType}&scope_code=${scopeCode}`),
        fetch(`/api/progress?scope_type=${scopeType}&scope_code=${scopeCode}`)
    ]);

    if (!timelineRes.ok || !progressRes.ok) {
        console.warn('Failed to fetch data');
        return;
    }

    const timelineData = await timelineRes.json();
    const progressData = await progressRes.json();
    cachedTimeline = timelineData.timeline;
    cachedProgress = progressData.progress;
    slider.max = Math.max(cachedTimeline.length - 1, 0);
    slider.value = slider.max;
    updateDashboard(slider.max);
}

function updateDashboard(index) {
    if (!cachedTimeline.length || !cachedProgress.length) {
        return;
    }

    const snapshot = cachedTimeline[index];
    const progress = cachedProgress[index] || cachedProgress[cachedProgress.length - 1];

    countedEl.textContent = progress.counted_units ?? 0;
    totalVotesEl.textContent = progress.total_votes ?? 0;
    turnoutEl.textContent = progress.turnout ?? 0;
    speedEl.textContent = progress.speed_per_hour ?? 0;

    const timelineLabels = cachedTimeline.map(item => new Date(item.interval_start).toLocaleTimeString());
    const countedSeries = cachedProgress.map(item => item.counted_units ?? 0);

    const partyLabels = snapshot.data.parties.map(p => p.name);
    const partyVotes = snapshot.data.parties.map(p => p.votes);

    if (!timelineChart) {
        timelineChart = new Chart(timelineCtx, {
            type: 'line',
            data: {
                labels: timelineLabels,
                datasets: [{
                    label: 'Counted districts',
                    data: countedSeries,
                    borderColor: '#38bdf8',
                    fill: false,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
            }
        });
    } else {
        timelineChart.data.labels = timelineLabels;
        timelineChart.data.datasets[0].data = countedSeries;
        timelineChart.update();
    }

    if (!partyChart) {
        partyChart = new Chart(partyCtx, {
            type: 'bar',
            data: {
                labels: partyLabels,
                datasets: [{
                    label: 'Votes',
                    data: partyVotes,
                    backgroundColor: '#f472b6',
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
            }
        });
    } else {
        partyChart.data.labels = partyLabels;
        partyChart.data.datasets[0].data = partyVotes;
        partyChart.update();
    }
}

slider.addEventListener('input', (event) => {
    const index = Number(event.target.value);
    updateDashboard(index);
});

scopeTypeInput.addEventListener('change', fetchDashboardData);
scopeCodeInput.addEventListener('change', fetchDashboardData);

document.getElementById('export-json').addEventListener('click', () => {
    const scopeType = scopeTypeInput.value;
    const scopeCode = scopeCodeInput.value;
    window.open(`/api/export?scope_type=${scopeType}&scope_code=${scopeCode}&format=json`, '_blank');
});

document.getElementById('export-csv').addEventListener('click', () => {
    const scopeType = scopeTypeInput.value;
    const scopeCode = scopeCodeInput.value;
    window.open(`/api/export?scope_type=${scopeType}&scope_code=${scopeCode}&format=csv`, '_blank');
});

async function initWebSocket() {
    const ws = new WebSocket(`ws://${window.location.host}/ws`);
    ws.addEventListener('message', (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'refresh') {
            fetchDashboardData();
        }
    });
}

fetchDashboardData();
setInterval(fetchDashboardData, 10000);
initWebSocket();
