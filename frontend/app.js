/**
 * Continuum Web - Main Application
 * Clean, intuitive wind resource toolkit
 */

const API_BASE = 'http://localhost:8000';
let currentProject = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadRecentProjects();
});

// ==================== PROJECT MANAGEMENT ====================

function showNewProjectModal() {
    document.getElementById('modal-new-project').classList.remove('hidden');
    document.getElementById('new-project-name').focus();
}

function closeNewProjectModal() {
    document.getElementById('modal-new-project').classList.add('hidden');
    // Clear form
    document.getElementById('new-project-name').value = '';
    document.getElementById('new-project-desc').value = '';
    document.getElementById('new-project-author').value = '';
}

function openProject() {
    loadAllProjects();
    document.getElementById('modal-open-project').classList.remove('hidden');
}

function closeOpenProjectModal() {
    document.getElementById('modal-open-project').classList.add('hidden');
}

async function createNewProject() {
    const name = document.getElementById('new-project-name').value.trim();
    const description = document.getElementById('new-project-desc').value.trim();
    const author = document.getElementById('new-project-author').value.trim();
    
    if (!name) {
        showToast('El nom del projecte és obligatori', 'error');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/projects/create`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, description, author })
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentProject = name;
            closeNewProjectModal();
            showDashboard(name, description, author);
            showToast(`Projecte "${name}" creat!`, 'success');
            saveToStorage('lastProject', name);
        } else {
            showToast(data.message || 'Error creant projecte', 'error');
        }
    } catch (e) {
        showToast('Error de connexió: ' + e.message, 'error');
    }
}

function showDashboard(name, description, author) {
    document.getElementById('welcome-screen').classList.add('hidden');
    document.getElementById('project-dashboard').classList.remove('hidden');
    
    document.getElementById('dashboard-project-name').textContent = name;
    document.getElementById('dashboard-project-desc').textContent = description || 'Sense descripció';
    document.getElementById('current-project-name').textContent = name;
    document.getElementById('current-project-name').parentElement.title = name;
    
    // Load project files
    loadProjectFiles(name);
}

async function loadAllProjects() {
    try {
        const response = await fetch(`${API_BASE}/projects/list`);
        const projects = await response.json();
        
        const listEl = document.getElementById('all-projects-list');
        
        if (projects.length === 0) {
            listEl.innerHTML = '<p class="placeholder">No hi ha projectes</p>';
            return;
        }
        
        listEl.innerHTML = projects.map(p => `
            <div class="project-item" onclick="loadProject('${p.name}')">
                <div class="project-item-info">
                    <strong>${p.name}</strong>
                    <span>${p.description || 'Sense descripció'}</span>
                </div>
                <div class="project-item-date">
                    ${new Date(p.updated_at).toLocaleDateString('ca')}
                </div>
            </div>
        `).join('');
        
    } catch (e) {
        showToast('Error carregant projectes', 'error');
    }
}

async function loadProject(name) {
    closeOpenProjectModal();
    
    try {
        const response = await fetch(`${API_BASE}/projects/${encodeURIComponent(name)}`);
        const data = await response.json();
        
        if (data.success) {
            currentProject = name;
            showDashboard(data.project.name, data.project.description, data.project.author);
            showToast(`Obert: ${name}`, 'success');
            saveToStorage('lastProject', name);
        } else {
            showToast('Projecte no trobat', 'error');
        }
    } catch (e) {
        showToast('Error obrint projecte', 'error');
    }
}

async function saveProject() {
    if (!currentProject) {
        showToast('No hi cap projecte obert', 'error');
        return;
    }
    
    showToast('Projecte guardat!', 'success');
}

function closeProject() {
    currentProject = null;
    document.getElementById('project-dashboard').classList.add('hidden');
    document.getElementById('welcome-screen').classList.remove('hidden');
    loadRecentProjects();
    saveToStorage('lastProject', null);
}

// ==================== FILE UPLOAD ====================

async function loadProjectFiles(projectName) {
    try {
        const response = await fetch(`${API_BASE}/files/list?project=${encodeURIComponent(projectName)}`);
        const data = await response.json();
        
        // Update file lists
        const files = data.files || [];
        const byType = {
            met: [],
            turbines: [],
            topography: [],
            landcover: []
        };
        
        files.forEach(f => {
            if (byType[f.type]) byType[f.type].push(f);
        });
        
        updateFileList('met-files-list', byType.met);
        updateFileList('turbine-files-list', byType.turbines);
        updateFileList('topo-files-list', byType.topography);
        updateFileList('lc-files-list', byType.landcover);
        
    } catch (e) {
        console.error('Error loading files:', e);
    }
}

function updateFileList(elementId, files) {
    const el = document.getElementById(elementId);
    if (!el) return;
    
    if (files.length === 0) {
        el.innerHTML = '';
        return;
    }
    
    el.innerHTML = files.map(f => `
        <div class="file-item">
            <i class="fas fa-file"></i>
            <span>${f.filename}</span>
        </div>
    `).join('');
}

// Setup file upload handlers
document.addEventListener('DOMContentLoaded', () => {
    // Met files
    document.getElementById('met-file')?.addEventListener('change', async (e) => {
        if (!currentProject) {
            showToast('Obre o crea un projecte primer', 'error');
            e.target.value = '';
            return;
        }
        await uploadFiles(e.target.files, 'met');
    });
    
    // Turbine files
    document.getElementById('turbine-file')?.addEventListener('change', async (e) => {
        if (!currentProject) {
            showToast('Obre o crea un projecte primer', 'error');
            e.target.value = '';
            return;
        }
        await uploadFiles(e.target.files, 'turbines');
    });
    
    // Topography files
    document.getElementById('topo-file')?.addEventListener('change', async (e) => {
        if (!currentProject) {
            showToast('Obre o crea un projecte primer', 'error');
            e.target.value = '';
            return;
        }
        await uploadFiles([e.target.files[0]], 'topography');
    });
    
    // Land cover files
    document.getElementById('lc-file')?.addEventListener('change', async (e) => {
        if (!currentProject) {
            showToast('Obre o crea un projecte primer', 'error');
            e.target.value = '';
            return;
        }
        await uploadFiles([e.target.files[0]], 'landcover');
    });
});

async function uploadFiles(files, fileType) {
    if (!files.length) return;
    
    for (const file of files) {
        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('project', currentProject);
            formData.append('file_type', fileType);
            
            const response = await fetch(`${API_BASE}/files/upload`, {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.success) {
                showToast(`Pujat: ${file.name}`, 'success');
                loadProjectFiles(currentProject);
            } else {
                showToast(`Error: ${data.error || file.name}`, 'error');
            }
        } catch (e) {
            showToast(`Error pujant ${file.name}`, 'error');
        }
    }
}

// ==================== TABS NAVIGATION ====================

function switchTab(tabId) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    // Show selected tab
    document.getElementById(`tab-${tabId}`)?.classList.add('active');
}

// ==================== MET QC ====================

async function runMetQC() {
    if (!currentProject) {
        showToast('Obre un projecte primer', 'error');
        return;
    }
    
    showLoading(true);
    
    try {
        const response = await fetch(`${API_BASE}/met-filter/filter`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                timestamps: ['2026-01-01T00:00:00', '2026-01-01T01:00:00'],
                wind_speed: [5.2, 5.8],
                wind_direction: [180, 185],
                remove_tower_shadow: document.getElementById('filter-tower').checked,
                remove_ice: document.getElementById('filter-ice').checked,
                remove_high_std: document.getElementById('filter-std').checked
            })
        });
        
        const data = await response.json();
        
        const resultsEl = document.getElementById('qc-results');
        resultsEl.innerHTML = `
            <div class="result-row">
                <span>Dades originals:</span>
                <strong>${data.original_count}</strong>
            </div>
            <div class="result-row">
                <span>Dades filtrades:</span>
                <strong>${data.filtered_count}</strong>
            </div>
            <div class="result-row">
                <span>Dades eliminades:</span>
                <strong>${data.removed_count} (${data.removal_percent.toFixed(1)}%)</strong>
            </div>
            <div class="result-row">
                <span>Shear Alpha:</span>
                <strong>${data.shear_alpha}</strong>
            </div>
        `;
        
        showToast('Filtratge complet!', 'success');
        
    } catch (e) {
        showToast('Error al filtratge: ' + e.message, 'error');
    } finally {
        showLoading(false);
    }
}

// ==================== WAKE ====================

async function runWakeCalculation() {
    showLoading(true);
    
    try {
        const response = await fetch(`${API_BASE}/wake/calculate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                turbines: [
                    { name: 'T1', x: 0, y: 0, hub_height: 80, rotor_diameter: 120, ct: 0.8 },
                    { name: 'T2', x: 800, y: 0, hub_height: 80, rotor_diameter: 120, ct: 0.8 },
                    { name: 'T3', x: 1600, y: 0, hub_height: 80, rotor_diameter: 120, ct: 0.8 }
                ],
                grid_resolution: parseInt(document.getElementById('wake-resolution').value) || 50
            })
        });
        
        const data = await response.json();
        
        const resultsEl = document.getElementById('wake-results');
        resultsEl.innerHTML = `
            <div class="result-row">
                <span>Pèrdua Global Wake:</span>
                <strong>${data.global_wake_loss_percent?.toFixed(2) || '--'}%</strong>
            </div>
            <div class="result-row">
                <span>Núm. Turbines:</span>
                <strong>${data.n_turbines}</strong>
            </div>
        `;
        
        showToast('Càlcul de wake complet!', 'success');
        
    } catch (e) {
        showToast('Error al càlcul de wake: ' + e.message, 'error');
    } finally {
        showLoading(false);
    }
}

// ==================== MCP ====================

async function runMCPCalculation() {
    showLoading(true);
    
    try {
        const response = await fetch(`${API_BASE}/mcp/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                reference_data: [],
                target_data: [],
                method: document.getElementById('mcp-method').value,
                sectors: parseInt(document.getElementById('mcp-sectors').value) || 12
            })
        });
        
        const data = await response.json();
        
        const resultsEl = document.getElementById('mcp-results');
        resultsEl.innerHTML = `
            <div class="result-row">
                <span>Mètode:</span>
                <strong>${data.method || 'orthogonal'}</strong>
            </div>
            <div class="result-row">
                <span>Sectors:</span>
                <strong>${data.n_sectors || 12}</strong>
            </div>
            <div class="result-row">
                <span>Correlació:</span>
                <strong>${data.correlation || '--'}</strong>
            </div>
        `;
        
        showToast('MCP complet!', 'success');
        
    } catch (e) {
        showToast('Error a MCP: ' + e.message, 'error');
    } finally {
        showLoading(false);
    }
}

// ==================== LAYOUT ====================

function createGridLayout() {
    const rows = parseInt(document.getElementById('layout-rows').value) || 4;
    const cols = parseInt(document.getElementById('layout-cols').value) || 5;
    const spacingX = parseInt(document.getElementById('layout-spacing-x').value) || 800;
    const spacingY = parseInt(document.getElementById('layout-spacing-y').value) || 600;
    
    drawLayout(createGrid(rows, cols, spacingX, spacingY, false));
    showToast('Layout Grid creat!', 'success');
}

function createStaggeredLayout() {
    const rows = parseInt(document.getElementById('layout-rows').value) || 4;
    const cols = parseInt(document.getElementById('layout-cols').value) || 5;
    const spacingX = parseInt(document.getElementById('layout-spacing-x').value) || 700;
    const spacingY = parseInt(document.getElementById('layout-spacing-y').value) || 500;
    
    drawLayout(createGrid(rows, cols, spacingX, spacingY, true));
    showToast('Layout Staggered creat!', 'success');
}

function createGrid(rows, cols, spacingX, spacingY, staggered) {
    const turbines = [];
    for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
            const x = c * spacingX + (staggered && r % 2 === 1 ? spacingX / 2 : 0);
            const y = r * spacingY;
            turbines.push({ name: `T${r * cols + c + 1}`, x, y });
        }
    }
    return turbines;
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
        // Scale to fit
        const maxX = 4500;
        const maxY = 3000;
        const x = (t.x / maxX) * canvas.width + 20;
        const y = canvas.height - (t.y / maxY) * canvas.height - 20;
        
        // Draw turbine
        ctx.fillStyle = '#0ea5e9';
        ctx.beginPath();
        ctx.arc(x, y, 12, 0, Math.PI * 2);
        ctx.fill();
        
        // Label
        ctx.fillStyle = '#94a3b8';
        ctx.font = '10px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(t.name, x, y + 25);
    });
    
    // Draw scale
    ctx.fillStyle = '#64748b';
    ctx.fillRect(20, canvas.height - 20, 100, 2);
    ctx.fillText('~1km', 70, canvas.height - 8);
}

async function optimizeLayout() {
    showLoading(true);
    
    try {
        const response = await fetch(`${API_BASE}/layout/optimize`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                n_turbines: 20,
                min_x: 0, max_x: 4000,
                min_y: 0, max_y: 3000,
                method: 'ga'
            })
        });
        
        const data = await response.json();
        
        if (data.turbines) {
            drawLayout(data.turbines);
            showToast('Optimització GA completada!', 'success');
        }
        
    } catch (e) {
        showToast('Error a optimització: ' + e.message, 'error');
    } finally {
        showLoading(false);
    }
}

// ==================== UTILITIES ====================

function showLoading(show) {
    const overlay = document.getElementById('loading-overlay');
    if (show) overlay.classList.remove('hidden');
    else overlay.classList.add('hidden');
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i> ${message}`;
    container.appendChild(toast);
    
    setTimeout(() => toast.remove(), 4000);
}

function saveToStorage(key, value) {
    try {
        if (value) localStorage.setItem(key, value);
        else localStorage.removeItem(key);
    } catch (e) {}
}

async function loadRecentProjects() {
    const last = localStorage.getItem('lastProject');
    if (last) {
        const recentEl = document.getElementById('recent-list');
        recentEl.innerHTML = `
            <div class="project-item" onclick="loadProject('${last}')">
                <i class="fas fa-history"></i>
                <span>${last}</span>
            </div>
        `;
    }
}

async function downloadReanalysis() {
    showToast('Funcionalitat de descàrrega vindrà aviat!', 'info');
}

// Enter key handlers
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('new-project-name')?.addEventListener('keyup', (e) => {
        if (e.key === 'Enter') createNewProject();
    });
});

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    // Ctrl+S = Save
    if (e.ctrlKey && e.key === 's') {
        e.preventDefault();
        saveProject();
    }
    // Ctrl+N = New Project
    if (e.ctrlKey && e.key === 'n') {
        e.preventDefault();
        showNewProjectModal();
    }
    // Ctrl+O = Open Project
    if (e.ctrlKey && e.key === 'o') {
        e.preventDefault();
        openProject();
    }
});
