const scopeSelect = document.getElementById('scope-select');
const countedEl = document.getElementById('counted');
const totalVotesEl = document.getElementById('total-votes');
const turnoutEl = document.getElementById('turnout');
const speedEl = document.getElementById('speed');
const timelineSlider = document.getElementById('timeline-slider');
const timelineLabel = document.getElementById('timeline-label');
const compareButton = document.getElementById('compare-button');
const compareA = document.getElementById('compare-a');
const compareB = document.getElementById('compare-b');
const comparisonResult = document.getElementById('comparison-result');
const exportJson = document.getElementById('export-json');
const exportCsv = document.getElementById('export-csv');

let aggregatedData = [];
let progressChart;
let partyChart;
let latestScope = { scope: 'country', code: 'CZ' };

function parseScope(value) {
    const [scope, code] = value.split('|');
    return { scope, code: code || null };
}

async function fetchAggregated() {
    const url = `/api/aggregated?scope=${latestScope.scope}&scope_code=${latestScope.code || ''}`;
    const response = await fetch(url);
    if (!response.ok) {
        return [];
    }
    return response.json();
}

async function fetchSummary() {
    const url = `/api/summary?scope=${latestScope.scope}&scope_code=${latestScope.code || ''}`;
    const response = await fetch(url);
    if (!response.ok) {
        return null;
    }
    return response.json();
}

async function fetchProgress(minute) {
    let url = `/api/progress?scope=${latestScope.scope}&scope_code=${latestScope.code || ''}`;
    if (minute) {
        url += `&minute=${encodeURIComponent(minute)}`;
    }
    const response = await fetch(url);
    if (!response.ok) {
        return null;
    }
    return response.json();
}

function updateStats(summary) {
    if (!summary) {
        countedEl.textContent = '0 / 0';
        totalVotesEl.textContent = '0';
        turnoutEl.textContent = '0%';
        return;
    }
    countedEl.textContent = `${summary.counted_precincts} / ${summary.total_precincts}`;
    totalVotesEl.textContent = summary.total_votes.toLocaleString();
    turnoutEl.textContent = `${summary.turnout.toFixed(2)}%`;
    const speed = computeSpeed(summary.minute_bucket);
    speedEl.textContent = `${speed.toFixed(0)} districts/h`;
}

function computeSpeed(latestMinute) {
    if (!aggregatedData.length) {
        return 0;
    }
    const latest = aggregatedData.findIndex(item => item.minute_bucket === latestMinute);
    if (latest <= 0) {
        return 0;
    }
    const latestBucket = new Date(aggregatedData[latest].minute_bucket);
    const oneHourBefore = new Date(latestBucket.getTime() - 60 * 60 * 1000).toISOString();
    const past = aggregatedData.find(item => item.minute_bucket >= oneHourBefore);
    if (!past) {
        return 0;
    }
    const latestVotes = aggregatedData[latest].total_votes;
    const pastVotes = past.total_votes;
    return (latestVotes - pastVotes) / 60;
}

function prepareTimeline() {
    if (!aggregatedData.length) {
        timelineSlider.max = 0;
        timelineSlider.value = 0;
        timelineLabel.textContent = '';
        return;
    }
    timelineSlider.max = aggregatedData.length - 1;
    timelineSlider.value = aggregatedData.length - 1;
    const latest = aggregatedData[aggregatedData.length - 1];
    timelineLabel.textContent = new Date(latest.minute_bucket).toLocaleString();
}

function initCharts() {
    const progressCtx = document.getElementById('progress-chart').getContext('2d');
    const partyCtx = document.getElementById('party-chart').getContext('2d');

    progressChart = new Chart(progressCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: []
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });

    partyChart = new Chart(partyCtx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Votes',
                backgroundColor: '#38bdf8',
                data: []
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

function updatePartyChart(parties) {
    if (!partyChart) return;
    partyChart.data.labels = parties.map(p => p.party_name);
    partyChart.data.datasets[0].data = parties.map(p => p.votes);
    partyChart.update();
}

function updateProgressChart() {
    if (!progressChart || !aggregatedData.length) return;
    const labels = aggregatedData.map(item => new Date(item.minute_bucket).toLocaleTimeString());
    const datasets = [];
    const partyCodes = new Set();
    aggregatedData.forEach(item => {
        Object.keys(item.data || {}).forEach(code => partyCodes.add(code));
    });
    partyCodes.forEach(code => {
        datasets.push({
            label: code,
            data: aggregatedData.map(item => (item.data || {})[code] || 0),
            fill: false,
            borderWidth: 2,
        });
    });
    progressChart.data.labels = labels;
    progressChart.data.datasets = datasets;
    progressChart.update();
}

async function refreshData() {
    aggregatedData = await fetchAggregated();
    aggregatedData = aggregatedData.map(item => ({
        ...item,
        total_votes: item.total_votes || Object.values(item.data || {}).reduce((sum, val) => sum + val, 0)
    }));
    prepareTimeline();
    updateProgressChart();
    const summary = await fetchSummary();
    updateStats(summary);
    const progress = await fetchProgress();
    if (progress) {
        updatePartyChart(progress.parties);
    }
}

function openWebSocket() {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const wsUrl = `${wsProtocol}://${window.location.host}/ws/summary?scope=${latestScope.scope}&scope_code=${latestScope.code || ''}`;
    const socket = new WebSocket(wsUrl);
    socket.onmessage = event => {
        try {
            const payload = JSON.parse(event.data);
            if (payload && payload.minute_bucket) {
                totalVotesEl.textContent = (payload.total_votes || 0).toLocaleString();
                turnoutEl.textContent = `${(payload.turnout || 0).toFixed(2)}%`;
            }
        } catch (err) {
            console.error('WebSocket parse error', err);
        }
    };
    socket.onclose = () => {
        setTimeout(openWebSocket, 5000);
    };
}

async function compareRegions() {
    const scopeA = parseScope(compareA.value);
    const scopeB = parseScope(compareB.value);
    const [summaryA, summaryB] = await Promise.all([
        fetch(`/api/summary?scope=${scopeA.scope}&scope_code=${scopeA.code || ''}`).then(res => res.json()),
        fetch(`/api/summary?scope=${scopeB.scope}&scope_code=${scopeB.code || ''}`).then(res => res.json())
    ]);
    const diffTurnout = (summaryA.turnout - summaryB.turnout).toFixed(2);
    comparisonResult.textContent = `Turnout difference: ${diffTurnout}% | Votes difference: ${(summaryA.total_votes - summaryB.total_votes).toLocaleString()}`;
}

async function exportData(format) {
    const response = await fetch(`/api/export?format=${format}`);
    const data = await response.text();
    const blob = new Blob([data], { type: format === 'json' ? 'application/json' : 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `election-data.${format}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
}

scopeSelect.addEventListener('change', async () => {
    latestScope = parseScope(scopeSelect.value);
    await refreshData();
});

timelineSlider.addEventListener('input', async () => {
    if (!aggregatedData.length) return;
    const index = parseInt(timelineSlider.value, 10);
    const item = aggregatedData[index];
    timelineLabel.textContent = new Date(item.minute_bucket).toLocaleString();
    const progress = await fetchProgress(item.minute_bucket);
    if (progress) {
        updatePartyChart(progress.parties);
    }
});

compareButton.addEventListener('click', compareRegions);
exportJson.addEventListener('click', () => exportData('json'));
exportCsv.addEventListener('click', () => exportData('csv'));

initCharts();
refreshData();
openWebSocket();
setInterval(refreshData, 10000);
