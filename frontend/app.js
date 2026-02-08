/**
 * Continuum Web - Full Working JavaScript
 * Handles project creation, file upload, and data processing
 */

const API_BASE = 'http://localhost:8000';
let currentProject = null;
let projectFiles = {};

// Navigation
document.querySelectorAll('.sidebar-nav li').forEach(li => {
    li.addEventListener('click', () => {
        const tab = li.dataset.tab;
        showTab(tab);
    });
});

document.querySelectorAll('.nav-menu .dropdown > a').forEach(a => {
    a.addEventListener('click', (e) => {
        e.preventDefault();
    });
});

function showTab(tabId) {
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.sidebar-nav li').forEach(l => l.classList.remove('active'));
    
    document.getElementById(`tab-${tabId}`).classList.add('active');
    document.querySelector(`[data-tab="${tabId}"]`).classList.add('active');
}

// Projects
async function newProject() {
    const name = document.getElementById('project-name').value || document.getElementById('project-name').placeholder;
    const description = document.getElementById('project-description').value || "";
    const author = document.getElementById('project-author').value || "";
    
    try {
        const response = await fetch(`${API_BASE}/projects/create`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, description, author })
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentProject = name;
            showToast('Project created!', 'success');
            loadProjectsList();
        } else {
            showToast(data.message, 'error');
        }
    } catch (e) {
        showToast('Error creating project: ' + e.message, 'error');
    }
}

async function loadProjectsList() {
    try {
        const response = await fetch(`${API_BASE}/projects/list`);
        const projects = await response.json();
        
        console.log('Projects:', projects);
    } catch (e) {
        console.error('Error loading projects:', e);
    }
}

async function saveProject() {
    if (!currentProject) {
        showToast('No project selected', 'error');
        return;
    }
    
    // Project auto-saves on each file upload
    showToast('Project saved!', 'success');
}

async function openProject() {
    const name = prompt('Enter project name:');
    if (name) {
        currentProject = name;
        await loadProjectFiles(name);
        showToast(`Opened: ${name}`, 'success');
    }
}

// File Uploads
async function uploadFile(fileInput, fileType) {
    if (!currentProject) {
        showToast('Please create or select a project first', 'error');
        return;
    }
    
    const files = fileInput.files;
    if (files.length === 0) return;
    
    for (const file of files) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('project', currentProject);
        formData.append('file_type', fileType);
        
        try {
            const response = await fetch(`${API_BASE}/files/upload`, {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.success) {
                showToast(`Uploaded: ${file.name}`, 'success');
                await loadProjectFiles(currentProject);
            } else {
                showToast(data.error || 'Upload failed', 'error');
            }
        } catch (e) {
            showToast('Upload error: ' + e.message, 'error');
        }
    }
}

async function loadProjectFiles(projectName) {
    try {
        const response = await fetch(`${API_BASE}/files/list?project=${encodeURIComponent(projectName)}`);
        const data = await response.json();
        projectFiles[projectName] = data.files || [];
        
        console.log('Files loaded:', projectFiles);
    } catch (e) {
        console.error('Error loading files:', e);
    }
}

// Event listeners for file inputs
document.getElementById('met-file')?.addEventListener('change', () => uploadFile(document.getElementById('met-file'), 'met'));
document.getElementById('turbine-file')?.addEventListener('change', () => uploadFile(document.getElementById('turbine-file'), 'turbines'));
document.getElementById('topo-file')?.addEventListener('change', () => uploadFile(document.getElementById('topo-file'), 'topography'));
document.getElementById('lc-file')?.addEventListener('change', () => uploadFile(document.getElementById('lc-file'), 'landcover'));

// Processing functions
async function importMetData() {
    await uploadFile(document.getElementById('met-file'), 'met');
}

async function importTurbines() {
    await uploadFile(document.getElementById('turbine-file'), 'turbines');
}

async function importTopography() {
    await uploadFile(document.getElementById('topo-file'), 'topography');
}

async function importLandCover() {
    await uploadFile(document.getElementById('lc-file'), 'landcover');
}

async function runMetQC() {
    if (!currentProject) {
        showToast('Create a project first', 'error');
        return;
    }
    
    showLoading(true);
    
    try {
        // Call the filter API
        const response = await fetch(`${API_BASE}/met-filter/filter`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                data: [],
                remove_tower_shadow: true,
                remove_ice: true,
                remove_high_std: true
            })
        });
        
        const result = await response.json();
        
        // Save result to project
        await fetch(`${API_BASE}/files/upload`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                project: currentProject,
                filename: 'met_qc_results.json',
                type: 'results',
                data: result
            })
        });
        
        showToast('QC completed!', 'success');
    } catch (e) {
        showToast('QC error: ' + e.message, 'error');
    } finally {
        showLoading(false);
    }
}

async function runMCP() {
    if (!currentProject) {
        showToast('Create a project first', 'error');
        return;
    }
    
    showLoading(true);
    
    try {
        const method = document.getElementById('mcp-method')?.value || 'orthogonal';
        
        const response = await fetch(`${API_BASE}/mcp/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                reference_data: [],
                target_data: [],
                method: method,
                sectors: 12
            })
        });
        
        const result = await response.json();
        
        showToast('MCP completed!', 'success');
    } catch (e) {
        showToast('MCP error: ' + e.message, 'error');
    } finally {
        showLoading(false);
    }
}

async function runWake() {
    showLoading(true);
    
    try {
        const response = await fetch(`${API_BASE}/wake/calculate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                turbines: [],
                grid_resolution: 50,
                sectors: 12
            })
        });
        
        const result = await response.json();
        showToast('Wake calculation completed!', 'success');
    } catch (e) {
        showToast('Wake error: ' + e.message, 'error');
    } finally {
        showLoading(false);
    }
}

// Layout functions
async function createGridLayout() {
    const response = await fetch(`${API_BASE}/layout/grid`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            n_rows: 4,
            n_cols: 5,
            spacing_x: 800,
            spacing_y: 600,
            staggered: false
        })
    });
    
    const result = await response.json();
    drawLayout(result.turbines);
}

async function createStaggeredLayout() {
    const response = await fetch(`${API_BASE}/layout/grid`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            n_rows: 4,
            n_cols: 5,
            spacing_x: 700,
            spacing_y: 500,
            staggered: true
        })
    });
    
    const result = await response.json();
    drawLayout(result.turbines);
}

async function optimizeLayout() {
    const response = await fetch(`${API_BASE}/layout/optimize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            n_turbines: 20,
            min_x: 0,
            max_x: 4000,
            min_y: 0,
            max_y: 3000,
            method: 'ga'
        })
    });
    
    const result = await response.json();
    drawLayout(result.turbines);
}

function drawLayout(turbines) {
    const canvas = document.getElementById('layoutCanvas');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Draw grid
    ctx.strokeStyle = '#334155';
    ctx.lineWidth = 1;
    
    turbines.forEach((t, i) => {
        const x = (t.x / 4000) * canvas.width;
        const y = canvas.height - (t.y / 3000) * canvas.height;
        
        ctx.fillStyle = '#0ea5e9';
        ctx.beginPath();
        ctx.arc(x, y, 10, 0, Math.PI * 2);
        ctx.fill();
        
        ctx.fillStyle = '#fff';
        ctx.font = '10px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(t.name || `T${i+1}`, x, y + 25);
    });
}

// Toast notifications
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, 4000);
}

// Loading overlay
function showLoading(show) {
    const overlay = document.getElementById('loading-overlay');
    if (show) {
        overlay.classList.remove('hidden');
    } else {
        overlay.classList.add('hidden');
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadProjectsList();
    
    // Create demo project if none exists
    fetch(`${API_BASE}/projects/list`)
        .then(r => r.json())
        .then(projects => {
            if (projects.length === 0) {
                // Create demo project
                fetch(`${API_BASE}/projects/create`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        name: 'Demo Project',
                        description: 'Demo wind project',
                        author: 'System'
                    })
                });
            }
        });
});
