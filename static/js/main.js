// Theme Management
let currentThemeClass = localStorage.getItem('theme-color') || '';

function toggleThemeDropdown() {
    const d = document.getElementById('theme-dropdown');
    d.style.display = d.style.display === 'none' ? 'flex' : 'none';
}

function setTheme(themeClass) {
    if (currentThemeClass) document.body.classList.remove(currentThemeClass);
    if (themeClass) document.body.classList.add(themeClass);
    currentThemeClass = themeClass;
    localStorage.setItem('theme-color', themeClass);
    document.getElementById('theme-dropdown').style.display = 'none';
    if(typeof fetchCategoryAnalysis === 'function') fetchCategoryAnalysis(); 
    
    // Attempt redraw on existing graph if open
    if(priceChartInstance) {
        try { showGraph(window.lastGraphId, window.lastGraphName); } catch(e){}
    }
}

if (currentThemeClass) {
    document.body.classList.add(currentThemeClass);
}

function toggleTheme() {
    document.body.classList.toggle('dark-mode');
    const isDark = document.body.classList.contains('dark-mode');
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
    document.getElementById('theme-toggle').innerText = isDark ? '☀️' : '🌙';
    if(typeof fetchCategoryAnalysis === 'function') fetchCategoryAnalysis(); // Update chart colors
}

if (localStorage.getItem('theme') === 'dark') {
    document.body.classList.add('dark-mode');
    const toggleBtn = document.getElementById('theme-toggle');
    if(toggleBtn) toggleBtn.innerText = '☀️';
}

// Notification Logic
function toggleNotifications() {
    const dropdown = document.getElementById('notif-dropdown');
    dropdown.style.display = dropdown.style.display === 'none' ? 'flex' : 'none';
}

async function fetchNotifications() {
    try {
        const response = await fetch('/api/notifications');
        const data = await response.json();
        const badge = document.getElementById('notif-badge');
        const list = document.getElementById('notif-list');
        if (!badge || !list) return;
        
        if (data.length > 0) {
            badge.style.display = 'inline-block';
            badge.innerText = data.length;
            list.innerHTML = data.map(n => `<div class="notif-item"><strong>${n.product_name || 'Alert'}</strong><br>${n.message} <br><small>${n.created_at.substring(0,10)}</small></div>`).join('');
        } else {
            badge.style.display = 'none';
            list.innerHTML = '<div style="color:var(--text-muted); text-align:center;">No new alerts</div>';
        }
    } catch(err) { console.error("Error fetching notifications", err); }
}

async function markAllRead() {
    try {
        await fetch('/api/notifications/read', { method: 'POST' });
        document.getElementById('notif-dropdown').style.display = 'none';
        fetchNotifications();
    } catch(err) { console.error(err); }
}

// Product Preview Logic
async function previewProduct() {
    const urlInput = document.getElementById('product-url');
    if (!urlInput) return;
    const url = urlInput.value;
    if (!url) return;
    
    const btn = document.getElementById('preview-btn');
    btn.innerText = "Loading...";
    btn.disabled = true;
    
    try {
        const response = await fetch('/api/preview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url })
        });
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('preview-img').src = data.image_url || 'https://via.placeholder.com/150?text=No+Image';
            document.getElementById('preview-title').innerText = data.name || "Unknown Product";
            document.getElementById('preview-price').innerText = data.price ? `₹${data.price}` : "Price Not Found";
            
            let tagsHtml = `<span class="eco-tag" style="background:#3498db;">${data.category}</span> `;
            tagsHtml += data.tags ? data.tags.split(',').map(t => `<span class="eco-tag">${t}</span>`).join(' ') : '';
            tagsHtml += ` <span class="eco-tag score-tag">Eco Score: ${data.expected_eco_score || 0}</span>`;
            document.getElementById('preview-tags').innerHTML = tagsHtml;
            
            document.getElementById('hidden-url').value = url;
            document.getElementById('preview-container').style.display = 'block';
        } else {
            alert("Failed to preview: " + data.error);
        }
    } catch (err) {
        console.error(err);
        alert("Error generating preview. Please check the URL.");
    }
    btn.innerText = "Preview Link";
    btn.disabled = false;
}

// Chart Logic (Graph & Doughnut)
let priceChartInstance = null;
let categoryChartInstance = null;

function closeGraph() {
    document.getElementById('graph-modal').style.display = 'none';
}

async function showGraph(productId, productName) {
    window.lastGraphId = productId;
    window.lastGraphName = productName;
    
    const titleEl = document.getElementById('graph-title');
    if(titleEl) titleEl.innerText = 'Price History: ' + productName;
    
    const modal = document.getElementById('graph-modal');
    if(modal) modal.style.display = 'flex';
    
    try {
        const response = await fetch(`/api/history/${productId}`);
        const data = await response.json();
        
        if(data.error) {
            alert(data.error);
            closeGraph();
            return;
        }
        renderChart(data.labels, data.data);
    } catch (error) {
        console.error("Failed to load history", error);
    }
}

function renderChart(labels, data) {
    const ctx = document.getElementById('priceChart').getContext('2d');
    if (priceChartInstance) priceChartInstance.destroy();
    
    const isDark = document.body.classList.contains('dark-mode');
    const color = getComputedStyle(document.body).getPropertyValue('--primary-color').trim() || '#2ecc71';
    const gridColor = isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)';
    const textColor = isDark ? '#e0e0e0' : '#2c3e50';
    
    priceChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Price (₹)',
                data: data,
                borderColor: color,
                backgroundColor: 'rgba(46, 204, 113, 0.2)',
                borderWidth: 3,
                pointBackgroundColor: color,
                pointRadius: 4,
                pointHoverRadius: 6,
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { beginAtZero: false, grid: { color: gridColor }, ticks: { color: textColor } },
                x: { grid: { color: gridColor }, ticks: { color: textColor } }
            },
            plugins: {
                legend: { display: false },
                tooltip: { backgroundColor: isDark ? '#333' : '#fff', titleColor: isDark ? '#fff' : '#000', bodyColor: isDark ? '#fff' : '#000', borderColor: color, borderWidth: 1 }
            }
        }
    });
}

async function fetchCategoryAnalysis() {
    const ctxElement = document.getElementById('categoryChart');
    if (!ctxElement) return;
    
    try {
        const response = await fetch('/api/category_analysis');
        const data = await response.json();
        const labels = Object.keys(data);
        const values = Object.values(data);
        
        if (labels.length === 0) return;
        
        const ctx = ctxElement.getContext('2d');
        const isDark = document.body.classList.contains('dark-mode');
        const textColor = isDark ? '#e0e0e0' : '#2c3e50';
        
        if (categoryChartInstance) categoryChartInstance.destroy();
        
        categoryChartInstance = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: ['#2ecc71', '#3498db', '#9b59b6', '#e74c3c', '#f1c40f', '#1abc9c', '#34495e'],
                    borderWidth: 2,
                    borderColor: isDark ? '#1a1a1a' : '#f8fbf9'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'right', labels: { color: textColor, boxWidth: 10, font: {size: 11} } }
                }
            }
        });
    } catch(err) { console.error(err); }
}

document.addEventListener("DOMContentLoaded", fetchCategoryAnalysis);

// Comparison Logic
function initCompareDropdown() {
    if (typeof userProducts === 'undefined') return;
    const cats = [...new Set(userProducts.map(p => p.category).filter(c => c))];
    const select = document.getElementById('compare-cat-select');
    if (!select) return;
    cats.forEach(c => {
        const op = document.createElement('option');
        op.value = c; op.text = c;
        select.appendChild(op);
    });
}
document.addEventListener("DOMContentLoaded", initCompareDropdown);

function compareCategory(category) {
    const strip = document.getElementById('compare-strip');
    if (!category) {
        strip.style.display = 'none';
        return;
    }
    const matches = userProducts.filter(p => p.category === category);
    
    if (matches.length === 0) {
        strip.innerHTML = '<p style="color:var(--text-muted); padding:1rem;">No products found.</p>';
    } else {
        strip.innerHTML = matches.map(p => `
            <div class="glass deal-card shadow" style="display:flex; flex-direction:column; justify-content:space-between;">
                <h5 title="${p.name}">${p.name.substring(0, 45)}...</h5>
                <img src="${p.image_url}" style="height:60px; object-fit:contain; margin:0.8rem 0; background:white; border-radius:4px; padding:2px;">
                <div class="deal-metrics mt-2" style="flex-direction:column; align-items:flex-start; gap:0.4rem; font-size:0.9rem;">
                    <div><strong>Price:</strong> <span style="font-size:1.1rem; color:var(--primary-dark); font-weight:bold;">₹${(p.current_price || 0).toFixed(2)}</span> 
                        ${p.current_price < p.avg_price ? '<span style="color:var(--primary-color)">▼ Deals</span>' : ''}
                    </div>
                    <div><strong>Avg:</strong> ₹${(p.avg_price || 0).toFixed(2)}</div>
                    <div><strong>Target:</strong> ₹${(p.target_price || 0).toFixed(2)}</div>
                    <div><span class="eco-tag mt-2 d-inline-block">Eco: ${p.eco_score}</span></div>
                </div>
            </div>
        `).join('');
    }
    strip.style.display = 'flex';
}
