// Continuum Web - Frontend Application

const API_BASE = 'http://localhost:8000';

let turbineCount = 0;

// Page Navigation
document.querySelectorAll('.nav-links li').forEach(li => {
    li.addEventListener('click', () => {
        const page = li.dataset.page;
        showPage(page);
    });
});

function showPage(pageId) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-links li').forEach(l => l.classList.remove('active'));
    
    document.getElementById(pageId).classList.add('active');
    document.querySelector(`[data-page="${pageId}"]`).classList.add('active');
}

// API Helper
async function apiCall(endpoint, method = 'POST', data = null) {
    try {
        const options = {
            method,
            headers: { 'Content-Type': 'application/json' }
        };
        if (data) options.body = JSON.stringify(data);
        
        const response = await fetch(`${API_BASE}${endpoint}`, options);
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        return { error: error.message };
    }
}

// Met Filter
async function runMetFilter() {
    const input = document.getElementById('met-input').value;
    try {
        const data = JSON.parse(input);
        const result = await apiCall('/met-filter/filter', 'POST', {
            data,
            remove_tower_shadow: document.getElementById('filter-shadow').checked,
            remove_ice: document.getElementById('filter-ice').checked,
            remove_high_std: document.getElementById('filter-std').checked
        });
        
        document.getElementById('met-results').innerHTML = `
            <h3>Results</h3>
            <pre>${JSON.stringify(result, null, 2)}</pre>
        `;
    } catch (e) {
        document.getElementById('met-results').innerHTML = `<p style="color: var(--danger)">Error: ${e.message}</p>`;
    }
}

// MCP
async function runMCP() {
    const ref = document.getElementById('mcp-ref').value;
    const target = document.getElementById('mcp-target').value;
    try {
        const result = await apiCall('/mcp/analyze', 'POST', {
            reference_data: JSON.parse(ref),
            target_data: JSON.parse(target),
            method: document.getElementById('mcp-method').value
        });
        
        document.getElementById('mcp-results').innerHTML = `
            <h3>Results</h3>
            <pre>${JSON.stringify(result, null, 2)}</pre>
        `;
    } catch (e) {
        document.getElementById('mcp-results').innerHTML = `<p style="color: var(--danger)">Error: ${e.message}</p>`;
    }
}

// Wake Model
function addTurbine() {
    turbineCount++;
    const div = document.createElement('div');
    div.className = 'turbine-row';
    div.id = `turbine-${turbineCount}`;
    div.innerHTML = `
        <input type="text" placeholder="Name" value="T${turbineCount}">
        <input type="number" placeholder="X" value="${turbineCount * 300}">
        <input type="number" placeholder="Y" value="0">
        <input type="number" placeholder="Height" value="80">
        <button class="remove-btn" onclick="removeTurbine(${turbineCount})">×</button>
    `;
    document.getElementById('turbine-list').appendChild(div);
}

function removeTurbine(id) {
    document.getElementById(`turbine-${id}`).remove();
}

async function runWake() {
    const turbines = [];
    for (let i = 1; i <= turbineCount; i++) {
        const row = document.getElementById(`turbine-${i}`);
        if (row) {
            const inputs = row.querySelectorAll('input');
            turbines.push({
                name: inputs[0].value,
                x: parseFloat(inputs[1].value),
                y: parseFloat(inputs[2].value),
                hub_height: parseFloat(inputs[3].value),
                rotor_diameter: 100,
                ct: 0.8
            });
        }
    }
    
    try {
        const result = await apiCall('/wake/calculate', 'POST', {
            turbines,
            grid_resolution: 50,
            sectors: 12
        });
        
        document.getElementById('wake-results').innerHTML = `
            <h3>Results</h3>
            <pre>${JSON.stringify(result, null, 2)}</pre>
        `;
    } catch (e) {
        document.getElementById('wake-results').innerHTML = `<p style="color: var(--danger)">Error: ${e.message}</p>`;
    }
}

// Layout - Canvas
const canvas = document.getElementById('layoutCanvas');
const ctx = canvas.getContext('2d');

function resizeCanvas() {
    const container = document.getElementById('layout-canvas');
    canvas.width = container.clientWidth - 40;
    canvas.height = 400;
}
resizeCanvas();
window.addEventListener('resize', resizeCanvas);

function drawTurbines(turbines) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Grid
    ctx.strokeStyle = '#334155';
    ctx.lineWidth = 1;
    for (let x = 0; x < canvas.width; x += 50) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, canvas.height);
        ctx.stroke();
    }
    for (let y = 0; y < canvas.height; y += 50) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(canvas.width, y);
        ctx.stroke();
    }
    
    // Turbines
    turbines.forEach((t, i) => {
        const x = (t.x / 4000) * canvas.width;
        const y = canvas.height - (t.y / 3000) * canvas.height;
        
        // Shadow
        ctx.fillStyle = 'rgba(14, 165, 233, 0.3)';
        ctx.beginPath();
        ctx.arc(x, y, 25, 0, Math.PI * 2);
        ctx.fill();
        
        // Turbine
        ctx.fillStyle = '#0ea5e9';
        ctx.beginPath();
        ctx.arc(x, y, 15, 0, Math.PI * 2);
        ctx.fill();
        
        // Label
        ctx.fillStyle = '#f1f5f9';
        ctx.font = '12px Inter';
        ctx.textAlign = 'center';
        ctx.fillText(t.name || `T${i + 1}`, x, y + 30);
    });
}

// Layout Methods
async function createGridLayout() {
    const result = await apiCall('/layout/grid', 'POST', {
        n_rows: 4,
        n_cols: 5,
        spacing_x: 800,
        spacing_y: 600,
        staggered: false
    });
    
    drawTurbines(result.turbines);
    document.getElementById('layout-stats').innerHTML = generateStats(result);
}

async function createStaggeredLayout() {
    const result = await apiCall('/layout/grid', 'POST', {
        n_rows: 4,
        n_cols: 5,
        spacing_x: 700,
        spacing_y: 500,
        staggered: true
    });
    
    drawTurbines(result.turbines);
    document.getElementById('layout-stats').innerHTML = generateStats(result);
}

async function optimizeLayout() {
    const result = await apiCall('/layout/optimize', 'POST', {
        n_turbines: 20,
        min_x: 0,
        max_x: 4000,
        min_y: 0,
        max_y: 3000,
        method: 'ga'
    });
    
    drawTurbines(result.turbines);
    document.getElementById('layout-stats').innerHTML = generateStats(result);
}

function generateStats(result) {
    return `
        <div class="stat"><div class="stat-value">${result.n_turbines}</div><div class="stat-label">Turbines</div></div>
        <div class="stat"><div class="stat-value">${result.metrics.avg_distance_m?.toFixed(0) || '--'}m</div><div class="stat-label">Avg Distance</div></div>
        <div class="stat"><div class="stat-value">${result.metrics.min_distance_m?.toFixed(0) || '--'}m</div><div class="stat-label">Min Distance</div></div>
        <div class="stat"><div class="stat-value">${(result.fitness * 100).toFixed(1)}%</div><div class="stat-label">Fitness</div></div>
    `;
}

// Neural MCP
async function runNeuralMCP() {
    const ref = document.getElementById('neural-ref').value;
    const target = document.getElementById('neural-target').value;
    
    try {
        // First train
        const trainResult = await apiCall('/mcp/neural/train', 'POST', {
            reference_data: JSON.parse(ref),
            target_data: JSON.parse(target),
            hidden_layers: document.getElementById('neural-layers').value.split(',').map(x => parseInt(x.trim())),
            epochs: parseInt(document.getElementById('neural-epochs').value),
            learning_rate: parseFloat(document.getElementById('neural-lr').value)
        });
        
        document.getElementById('neural-results').innerHTML = `
            <h3>Training Results</h3>
            <pre>${JSON.stringify(trainResult, null, 2)}</pre>
        `;
    } catch (e) {
        document.getElementById('neural-results').innerHTML = `<p style="color: var(--danger)">Error: ${e.message}</p>`;
    }
}

// Initialize with some demo data
document.addEventListener('DOMContentLoaded', () => {
    // Add initial turbines
    addTurbine();
    addTurbine();
    addTurbine();
    
    // Demo data for MCP
    document.getElementById('mcp-ref').value = JSON.stringify([
        { wind_speed: 8.5, wind_direction: 270 },
        { wind_speed: 7.2, wind_direction: 280 },
        { wind_speed: 9.1, wind_direction: 265 },
        { wind_speed: 6.8, wind_direction: 290 },
        { wind_speed: 10.2, wind_direction: 275 }
    ], null, 2);
    
    document.getElementById('mcp-target').value = JSON.stringify([
        { wind_speed: 8.1, wind_direction: 275 },
        { wind_speed: 6.9, wind_direction: 278 },
        { wind_speed: 8.7, wind_direction: 268 },
        { wind_speed: 6.5, wind_direction: 292 },
        { wind_speed: 9.8, wind_direction: 277 }
    ], null, 2);
    
    document.getElementById('met-input').value = JSON.stringify([
        { wind_speed: 8.5, wind_direction: 270, temperature: 15 },
        { wind_speed: 2.1, wind_direction: 45, temperature: -1 },
        { wind_speed: 12.3, wind_direction: 180, temperature: 22 }
    ], null, 2);
    
    // Draw initial grid layout
    createGridLayout();
});

// API Health Check
async function checkApiHealth() {
    try {
        const response = await fetch(`${API_BASE}/health`);
        const data = await response.json();
        document.querySelector('.api-status .status-text').textContent = data.status === 'healthy' ? 'API Connected' : 'API Error';
        document.querySelector('.api-status .status-dot').style.background = data.status === 'healthy' ? '#22c55e' : '#ef4444';
    } catch (e) {
        document.querySelector('.api-status .status-text').textContent = 'API Disconnected';
        document.querySelector('.api-status .status-dot').style.background = '#ef4444';
    }
}

checkApiHealth();
setInterval(checkApiHealth, 30000);
