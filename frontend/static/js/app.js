// ==============================================================================
// SMART MULTI-VENDOR E-COMMERCE ORDER MANAGEMENT SYSTEM
// File: frontend/static/js/app.js
// Client-side controller communicating with Flask Backend & MySQL
// ==============================================================================

let currentTab = 'dashboard';
let categoryChartInstance = null;
let cachedProducts = [];
let cachedOrders = [];

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    switchTab('dashboard');
    loadBootstrapData();
});

// ------------------------------------------------------------------------------
// NAVIGATION & TAB SWITCHING
// ------------------------------------------------------------------------------
function switchTab(tabId) {
    currentTab = tabId;

    // Update nav links
    const navButtons = document.querySelectorAll('nav button');
    navButtons.forEach(btn => {
        btn.classList.remove('sidebar-active');
        btn.classList.add('text-slate-600');
    });

    const activeBtn = document.getElementById(`nav-${tabId}`);
    if (activeBtn) {
        activeBtn.classList.add('sidebar-active');
        activeBtn.classList.remove('text-slate-600');
    }

    // Hide all sections
    const tabs = ['dashboard', 'orders', 'products', 'vendors', 'customers', 'inventory', 'analytics', 'audit'];
    tabs.forEach(t => {
        const el = document.getElementById(`tab-${t}`);
        if (el) el.classList.add('hidden');
    });

    // Show target section
    const targetSection = document.getElementById(`tab-${tabId}`);
    if (targetSection) targetSection.classList.remove('hidden');

    // Update Header
    updateHeader(tabId);

    // Refresh content for active tab
    refreshCurrentTab();
}

function updateHeader(tabId) {
    const titles = {
        dashboard: { title: "Dashboard Overview", desc: "Real-time e-commerce operational metrics and database status" },
        orders: { title: "Orders & Transaction Management", desc: "Multi-vendor orders executed with ACID transactions and stored procedures" },
        products: { title: "Product Catalog Management", desc: "Independent multi-vendor product listings, categories, and pricing" },
        vendors: { title: "Multi-Vendor Marketplace", desc: "Registered sellers, platform commission rates, and sales performance" },
        customers: { title: "Customer Directory", desc: "Registered shoppers, contact profiles, and lifetime spending" },
        inventory: { title: "Inventory & Stock Levels", desc: "Warehouse tracking protected by MySQL BEFORE/AFTER triggers" },
        analytics: { title: "Business Analytics & Cursors", desc: "Aggregated reports and MySQL cursor batch reconciliation" },
        audit: { title: "Database Trigger Audit Trail", desc: "Live event logging automatically populated by MySQL AFTER UPDATE triggers" }
    };

    const header = titles[tabId] || titles.dashboard;
    document.getElementById('section-title').innerText = header.title;
    document.getElementById('section-desc').innerText = header.desc;
}

function refreshCurrentTab() {
    switch (currentTab) {
        case 'dashboard': loadDashboard(); break;
        case 'orders': loadOrders(); break;
        case 'products': loadProducts(); break;
        case 'vendors': loadVendors(); break;
        case 'customers': loadCustomers(); break;
        case 'inventory': loadInventory(); break;
        case 'analytics': loadAnalytics(); break;
        case 'audit': loadAuditLogs(); break;
    }
}

// ------------------------------------------------------------------------------
// NOTIFICATIONS & ALERTS
// ------------------------------------------------------------------------------
function showAlert(message, type = 'success') {
    const banner = document.getElementById('alert-banner');
    const msg = document.getElementById('alert-message');
    msg.innerText = message;

    banner.className = 'mb-6 p-4 rounded-xl text-sm font-medium flex items-center justify-between ';
    if (type === 'success') {
        banner.classList.add('bg-emerald-50', 'text-emerald-800', 'border', 'border-emerald-200');
    } else {
        banner.classList.add('bg-rose-50', 'text-rose-800', 'border', 'border-rose-200');
    }
    banner.classList.remove('hidden');

    setTimeout(() => {
        hideAlert();
    }, 6000);
}

function hideAlert() {
    document.getElementById('alert-banner').classList.add('hidden');
}

// ------------------------------------------------------------------------------
// 1. DASHBOARD CONTROLLER
// ------------------------------------------------------------------------------
async function loadDashboard() {
    try {
        const res = await fetch('/api/dashboard/stats');
        const json = await res.json();
        if (json.status !== 'success') return;

        const k = json.kpis || {};
        document.getElementById('stat-revenue').innerText = `₹${Number(k.total_revenue || 0).toLocaleString('en-IN')}`;
        document.getElementById('stat-orders').innerText = k.total_orders || 0;
        document.getElementById('stat-vendors').innerText = k.total_vendors || 0;
        document.getElementById('stat-low-stock').innerText = k.low_stock_products || 0;

        // Render Recent Orders
        const tbody = document.getElementById('dashboard-recent-orders');
        tbody.innerHTML = '';
        (json.recent_orders || []).forEach(o => {
            const tr = document.createElement('tr');
            tr.className = "hover:bg-slate-50/50 transition";
            tr.innerHTML = `
                <td class="py-3 px-3 font-semibold text-slate-800">#${o.order_id}</td>
                <td class="py-3 px-3 font-medium text-slate-700">${escapeHtml(o.customer_name)}</td>
                <td class="py-3 px-3 font-semibold text-slate-900">₹${Number(o.total_amount).toLocaleString('en-IN')}</td>
                <td class="py-3 px-3">${getStatusBadge(o.order_status)}</td>
                <td class="py-3 px-3 text-xs text-slate-500">${o.payment_method || 'N/A'} (${o.payment_status || 'Pending'})</td>
            `;
            tbody.appendChild(tr);
        });

        // Render Chart.js
        renderCategoryChart(json.category_distribution || []);
    } catch (err) {
        console.error('Failed to load dashboard stats:', err);
    }
}

function renderCategoryChart(data) {
    const ctx = document.getElementById('categoryChart');
    if (!ctx) return;

    if (categoryChartInstance) {
        categoryChartInstance.destroy();
    }

    const labels = data.map(d => d.category_name);
    const values = data.map(d => d.category_revenue);

    categoryChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: [
                    '#0284c7', '#06b6d4', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6'
                ],
                borderWidth: 2,
                borderColor: '#ffffff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 10 } } }
            }
        }
    });
}

// ------------------------------------------------------------------------------
// 2. ORDERS CONTROLLER
// ------------------------------------------------------------------------------
async function loadOrders() {
    try {
        const res = await fetch('/api/orders');
        const json = await res.json();
        if (json.status === 'success') {
            cachedOrders = json.data || [];
            renderOrdersTable();
        }
    } catch (err) {
        console.error('Failed to load orders:', err);
    }
}

function renderOrdersTable() {
    const filter = document.getElementById('order-status-filter').value;
    const tbody = document.getElementById('orders-table-body');
    tbody.innerHTML = '';

    const list = filter === 'ALL' ? cachedOrders : cachedOrders.filter(o => o.order_status === filter);

    if (list.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" class="py-8 text-center text-slate-400">No orders matching selected criteria</td></tr>`;
        return;
    }

    list.forEach(o => {
        const tr = document.createElement('tr');
        tr.className = "hover:bg-slate-50/50 transition";
        const isCancelable = o.order_status !== 'Cancelled' && o.order_status !== 'Delivered';

        tr.innerHTML = `
            <td class="py-3 px-4 font-bold text-slate-800">#${o.order_id}</td>
            <td class="py-3 px-4">
                <div class="font-medium text-slate-800">${escapeHtml(o.customer_name)}</div>
                <div class="text-xs text-slate-400">${escapeHtml(o.customer_city || '')}</div>
            </td>
            <td class="py-3 px-4 text-xs text-slate-600 max-w-xs truncate" title="${escapeHtml(o.order_summary || '')}">
                ${escapeHtml(o.order_summary || 'No line items')}
            </td>
            <td class="py-3 px-4 font-bold text-slate-900">₹${Number(o.total_amount).toLocaleString('en-IN')}</td>
            <td class="py-3 px-4">
                <select onchange="changeOrderStatus(${o.order_id}, this.value)" class="text-xs font-semibold px-2 py-1 rounded-md border border-slate-200 bg-white">
                    <option value="Pending" ${o.order_status === 'Pending' ? 'selected' : ''}>Pending</option>
                    <option value="Processing" ${o.order_status === 'Processing' ? 'selected' : ''}>Processing</option>
                    <option value="Shipped" ${o.order_status === 'Shipped' ? 'selected' : ''}>Shipped</option>
                    <option value="Delivered" ${o.order_status === 'Delivered' ? 'selected' : ''}>Delivered</option>
                    <option value="Cancelled" ${o.order_status === 'Cancelled' ? 'selected' : ''}>Cancelled</option>
                </select>
            </td>
            <td class="py-3 px-4 text-xs">
                <span class="font-medium text-slate-700">${o.payment_method || 'COD'}</span>
                <div class="text-[11px] text-slate-400">${o.payment_status || 'Pending'}</div>
            </td>
            <td class="py-3 px-4 text-right">
                ${isCancelable ? `
                    <button onclick="cancelOrderProcedure(${o.order_id})" class="px-2.5 py-1 text-xs text-rose-600 hover:bg-rose-50 border border-rose-200 rounded-lg transition font-medium" title="Invokes cancel_order_procedure()">
                        <i class="fa-solid fa-ban"></i> Cancel
                    </button>
                ` : `<span class="text-xs text-slate-400 font-medium">—</span>`}
            </td>
        `;
        tbody.appendChild(tr);
    });
}

async function changeOrderStatus(orderId, newStatus) {
    try {
        const res = await fetch(`/api/orders/${orderId}/status`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: newStatus })
        });
        const json = await res.json();
        if (json.status === 'success') {
            showAlert(`Order #${orderId} updated to ${newStatus}. (Audit Trigger Fired)`, 'success');
            loadOrders();
        } else {
            showAlert(json.message, 'error');
        }
    } catch (err) {
        showAlert('Failed to update status', 'error');
    }
}

async function cancelOrderProcedure(orderId) {
    if (!confirm(`Are you sure you want to cancel Order #${orderId}? This will invoke MySQL cancel_order_procedure() and automatically restock items.`)) return;

    try {
        const res = await fetch(`/api/orders/${orderId}/cancel`, { method: 'POST' });
        const json = await res.json();
        if (json.status === 'success') {
            showAlert(json.message, 'success');
            loadOrders();
        } else {
            showAlert(json.message, 'error');
        }
    } catch (err) {
        showAlert('Cancellation request failed', 'error');
    }
}

// ------------------------------------------------------------------------------
// 3. PRODUCTS CONTROLLER
// ------------------------------------------------------------------------------
async function loadProducts() {
    try {
        const res = await fetch('/api/products');
        const json = await res.json();
        if (json.status === 'success') {
            cachedProducts = json.data || [];
            renderProductsTable(cachedProducts);
        }
    } catch (err) {
        console.error('Failed to load products:', err);
    }
}

function renderProductsTable(list) {
    const tbody = document.getElementById('products-table-body');
    tbody.innerHTML = '';

    list.forEach(p => {
        const tr = document.createElement('tr');
        tr.className = "hover:bg-slate-50/50 transition";
        tr.innerHTML = `
            <td class="py-3 px-4 font-semibold text-slate-700">#${p.product_id}</td>
            <td class="py-3 px-4">
                <span class="font-bold text-slate-800">${escapeHtml(p.product_name)}</span>
                <div class="text-xs text-amber-500 font-medium"><i class="fa-solid fa-star text-[11px]"></i> ${p.product_rating}</div>
            </td>
            <td class="py-3 px-4 text-xs font-medium text-slate-600">${escapeHtml(p.category_name)}</td>
            <td class="py-3 px-4 text-xs font-semibold text-sky-700">${escapeHtml(p.seller_name)}</td>
            <td class="py-3 px-4 font-bold text-slate-900">₹${Number(p.price).toLocaleString('en-IN')}</td>
            <td class="py-3 px-4 text-xs font-semibold text-emerald-600">${p.discount_percent}% off</td>
            <td class="py-3 px-4">${getStockBadge(p.stock_quantity)}</td>
            <td class="py-3 px-4 text-right">
                <button onclick="deleteProduct(${p.product_id})" class="text-slate-400 hover:text-rose-600 text-sm" title="Delete product">
                    <i class="fa-solid fa-trash-can"></i>
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function filterProducts() {
    const term = document.getElementById('product-search').value.toLowerCase();
    const cat = document.getElementById('product-category-filter').value;

    const filtered = cachedProducts.filter(p => {
        const matchTerm = p.product_name.toLowerCase().includes(term) || p.seller_name.toLowerCase().includes(term);
        const matchCat = cat === '' || String(p.category_id) === cat;
        return matchTerm && matchCat;
    });

    renderProductsTable(filtered);
}

async function deleteProduct(id) {
    if (!confirm(`Are you sure you want to delete product #${id}?`)) return;
    try {
        const res = await fetch(`/api/products/${id}`, { method: 'DELETE' });
        const json = await res.json();
        if (json.status === 'success') {
            showAlert(json.message, 'success');
            loadProducts();
        } else {
            showAlert(json.message, 'error');
        }
    } catch (err) {
        showAlert('Delete failed', 'error');
    }
}

// ------------------------------------------------------------------------------
// 4. VENDORS CONTROLLER
// ------------------------------------------------------------------------------
async function loadVendors() {
    try {
        const res = await fetch('/api/vendors');
        const json = await res.json();
        if (json.status === 'success') {
            const tbody = document.getElementById('vendors-table-body');
            tbody.innerHTML = '';
            (json.data || []).forEach(v => {
                const tr = document.createElement('tr');
                tr.className = "hover:bg-slate-50/50 transition";
                tr.innerHTML = `
                    <td class="py-3 px-4 font-bold text-slate-700">#${v.seller_id}</td>
                    <td class="py-3 px-4 font-bold text-slate-800">${escapeHtml(v.seller_name)}</td>
                    <td class="py-3 px-4 text-xs text-slate-600">${escapeHtml(v.city || 'N/A')}</td>
                    <td class="py-3 px-4 text-xs font-semibold text-amber-500"><i class="fa-solid fa-star"></i> ${v.rating}</td>
                    <td class="py-3 px-4 font-semibold text-slate-800">${v.commission_rate}%</td>
                    <td class="py-3 px-4 text-xs text-slate-600">${v.total_products} items</td>
                    <td class="py-3 px-4 font-bold text-slate-900">₹${Number(v.gross_sales).toLocaleString('en-IN')}</td>
                    <td class="py-3 px-4 text-right">
                        <button onclick="viewVendorPerformance(${v.seller_id})" class="px-2.5 py-1 text-xs text-sky-600 hover:bg-sky-50 border border-sky-200 rounded-lg transition font-medium">
                            <i class="fa-solid fa-chart-simple"></i> Procedure Report
                        </button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        }
    } catch (err) {
        console.error('Failed to load vendors:', err);
    }
}

async function viewVendorPerformance(sellerId) {
    try {
        const res = await fetch(`/api/vendors/${sellerId}/performance`);
        const json = await res.json();
        if (json.status === 'success' && json.data) {
            const d = json.data;
            alert(
                `=== VENDOR PERFORMANCE REPORT (STORED PROCEDURE) ===\n\n` +
                `Vendor: ${d.seller_name} (ID: ${d.seller_id})\n` +
                `Rating: ${d.rating} / 5.0\n` +
                `Commission Rate: ${d.commission_rate}%\n` +
                `Active Products: ${d.active_catalog_products}\n` +
                `Total Units Sold: ${d.total_units_sold}\n` +
                `Gross Sales Amount: ₹${Number(d.gross_sales_amount).toLocaleString('en-IN')}\n` +
                `Platform Commission: ₹${Number(d.platform_commission).toLocaleString('en-IN')}\n` +
                `Net Vendor Earnings: ₹${Number(d.net_vendor_earnings).toLocaleString('en-IN')}`
            );
        } else {
            showAlert('No performance records found.', 'error');
        }
    } catch (err) {
        showAlert('Failed to fetch performance report', 'error');
    }
}

// ------------------------------------------------------------------------------
// 5. CUSTOMERS CONTROLLER
// ------------------------------------------------------------------------------
async function loadCustomers() {
    try {
        const search = document.getElementById('customer-search').value;
        const res = await fetch(`/api/customers?search=${encodeURIComponent(search)}`);
        const json = await res.json();
        if (json.status === 'success') {
            const tbody = document.getElementById('customers-table-body');
            tbody.innerHTML = '';
            (json.data || []).forEach(c => {
                const tr = document.createElement('tr');
                tr.className = "hover:bg-slate-50/50 transition";
                tr.innerHTML = `
                    <td class="py-3 px-4 font-bold text-slate-700">#${c.customer_id}</td>
                    <td class="py-3 px-4 font-bold text-slate-800">${escapeHtml(c.first_name)} ${escapeHtml(c.last_name)}</td>
                    <td class="py-3 px-4 text-xs text-slate-600">${escapeHtml(c.email)}</td>
                    <td class="py-3 px-4 text-xs text-slate-500">${escapeHtml(c.phone || '—')}</td>
                    <td class="py-3 px-4 text-xs text-slate-700 font-medium">${escapeHtml(c.city || '—')}</td>
                    <td class="py-3 px-4 text-xs font-semibold text-slate-800">${c.total_orders}</td>
                    <td class="py-3 px-4 font-bold text-slate-900">₹${Number(c.total_spent).toLocaleString('en-IN')}</td>
                    <td class="py-3 px-4"><span class="px-2 py-0.5 text-xs font-semibold rounded-full ${c.status === 'Active' ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-600'}">${c.status}</span></td>
                    <td class="py-3 px-4 text-right">
                        <button onclick="deleteCustomer(${c.customer_id})" class="text-slate-400 hover:text-rose-600 text-sm">
                            <i class="fa-solid fa-trash-can"></i>
                        </button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        }
    } catch (err) {
        console.error('Failed to load customers:', err);
    }
}

async function deleteCustomer(id) {
    if (!confirm(`Delete customer #${id}?`)) return;
    try {
        const res = await fetch(`/api/customers/${id}`, { method: 'DELETE' });
        const json = await res.json();
        if (json.status === 'success') {
            showAlert(json.message, 'success');
            loadCustomers();
        } else {
            showAlert(json.message, 'error');
        }
    } catch (err) {
        showAlert('Delete failed', 'error');
    }
}

// ------------------------------------------------------------------------------
// 6. INVENTORY CONTROLLER
// ------------------------------------------------------------------------------
async function loadInventory() {
    try {
        const res = await fetch('/api/inventory');
        const json = await res.json();
        if (json.status === 'success') {
            const tbody = document.getElementById('inventory-table-body');
            tbody.innerHTML = '';
            (json.data || []).forEach(p => {
                const tr = document.createElement('tr');
                tr.className = "hover:bg-slate-50/50 transition";
                tr.innerHTML = `
                    <td class="py-3 px-4 font-bold text-slate-700">#${p.product_id}</td>
                    <td class="py-3 px-4 font-semibold text-slate-800">${escapeHtml(p.product_name)}</td>
                    <td class="py-3 px-4 text-xs text-sky-700 font-medium">${escapeHtml(p.seller_name)}</td>
                    <td class="py-3 px-4 text-xs text-slate-500">${escapeHtml(p.category_name)}</td>
                    <td class="py-3 px-4 font-bold text-slate-900">₹${Number(p.price).toLocaleString('en-IN')}</td>
                    <td class="py-3 px-4 font-bold text-slate-800">${p.stock_quantity} units</td>
                    <td class="py-3 px-4">${getStockBadge(p.stock_quantity)}</td>
                    <td class="py-3 px-4 text-right">
                        <div class="inline-flex items-center gap-1.5">
                            <input type="number" id="stock-input-${p.product_id}" value="${p.stock_quantity}" min="0" class="w-16 px-2 py-1 border border-slate-200 rounded text-xs">
                            <button onclick="updateStockLevel(${p.product_id})" class="px-2 py-1 bg-slate-100 hover:bg-sky-600 hover:text-white rounded text-xs font-semibold transition">
                                Save
                            </button>
                        </div>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        }
    } catch (err) {
        console.error('Failed to load inventory:', err);
    }
}

async function updateStockLevel(prodId) {
    const val = parseInt(document.getElementById(`stock-input-${prodId}`).value);
    try {
        const res = await fetch('/api/inventory/update-stock', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ product_id: prodId, stock_quantity: val })
        });
        const json = await res.json();
        if (json.status === 'success') {
            showAlert(json.message, 'success');
            loadInventory();
        } else {
            showAlert(`Trigger Rejection: ${json.message}`, 'error');
        }
    } catch (err) {
        showAlert('Stock update failed', 'error');
    }
}

// ------------------------------------------------------------------------------
// 7. ANALYTICS & CURSORS CONTROLLER
// ------------------------------------------------------------------------------
async function loadAnalytics() {
    try {
        const res = await fetch('/api/analytics');
        const json = await res.json();
        if (json.status !== 'success') return;

        // Top products
        const topProdBody = document.getElementById('top-products-body');
        topProdBody.innerHTML = '';
        (json.top_products || []).forEach(p => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td class="py-2.5 px-3 font-semibold text-slate-800">${escapeHtml(p.product_name)}</td>
                <td class="py-2.5 px-3 text-xs text-sky-700">${escapeHtml(p.seller_name)}</td>
                <td class="py-2.5 px-3 text-xs font-semibold text-slate-600">${p.units_sold}</td>
                <td class="py-2.5 px-3 font-bold text-slate-900">₹${Number(p.total_revenue).toLocaleString('en-IN')}</td>
            `;
            topProdBody.appendChild(tr);
        });

        // Top customers
        const topCustBody = document.getElementById('top-customers-body');
        topCustBody.innerHTML = '';
        (json.top_customers || []).forEach(c => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td class="py-2.5 px-3 font-semibold text-slate-800">${escapeHtml(c.customer_name)}</td>
                <td class="py-2.5 px-3 text-xs text-slate-500">${escapeHtml(c.city)}</td>
                <td class="py-2.5 px-3 text-xs font-semibold text-slate-600">${c.orders_count}</td>
                <td class="py-2.5 px-3 font-bold text-slate-900">₹${Number(c.total_spent).toLocaleString('en-IN')}</td>
            `;
            topCustBody.appendChild(tr);
        });
    } catch (err) {
        console.error('Failed to load analytics:', err);
    }
}

async function runCursorBatchPayouts() {
    try {
        const res = await fetch('/api/admin/run-cursor-payouts', { method: 'POST' });
        const json = await res.json();
        if (json.status === 'success') {
            showAlert(json.message, 'success');
            document.getElementById('cursor-output-container').classList.remove('hidden');

            const tbody = document.getElementById('cursor-payouts-table-body');
            tbody.innerHTML = '';
            (json.data || []).forEach(row => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td class="py-2.5 px-3 font-bold text-slate-700">#${row.payout_id}</td>
                    <td class="py-2.5 px-3 font-bold text-slate-800">${escapeHtml(row.seller_name)}</td>
                    <td class="py-2.5 px-3 font-semibold text-slate-700">₹${Number(row.total_sales).toLocaleString('en-IN')}</td>
                    <td class="py-2.5 px-3 font-semibold text-amber-600">₹${Number(row.commission_deducted).toLocaleString('en-IN')}</td>
                    <td class="py-2.5 px-3 font-bold text-emerald-600">₹${Number(row.net_payout).toLocaleString('en-IN')}</td>
                    <td class="py-2.5 px-3 text-xs text-slate-500">${row.payout_date}</td>
                `;
                tbody.appendChild(tr);
            });
        } else {
            showAlert(json.message, 'error');
        }
    } catch (err) {
        showAlert('Cursor batch execution failed', 'error');
    }
}

// ------------------------------------------------------------------------------
// 8. AUDIT LOGS CONTROLLER
// ------------------------------------------------------------------------------
async function loadAuditLogs() {
    try {
        const res = await fetch('/api/audit-logs');
        const json = await res.json();
        if (json.status === 'success') {
            const tbody = document.getElementById('audit-logs-table-body');
            tbody.innerHTML = '';
            (json.data || []).forEach(l => {
                const tr = document.createElement('tr');
                tr.className = "hover:bg-slate-50/50 transition";
                tr.innerHTML = `
                    <td class="py-3 px-4 font-mono text-xs font-bold text-slate-600">#LOG-${l.log_id}</td>
                    <td class="py-3 px-4 font-bold text-slate-800">Order #${l.order_id}</td>
                    <td class="py-3 px-4 text-xs font-semibold text-slate-500">${l.old_status || '—'}</td>
                    <td class="py-3 px-4 text-xs font-bold text-sky-700">${l.new_status}</td>
                    <td class="py-3 px-4 text-xs font-mono text-emerald-600">${l.action_type}</td>
                    <td class="py-3 px-4 text-xs text-slate-400 font-mono">${l.changed_at}</td>
                `;
                tbody.appendChild(tr);
            });
        }
    } catch (err) {
        console.error('Failed to load audit logs:', err);
    }
}

// ------------------------------------------------------------------------------
// BOOTSTRAP LOOKUPS & MODALS
// ------------------------------------------------------------------------------
async function loadBootstrapData() {
    try {
        // Load categories into select
        const catRes = await fetch('/api/categories');
        const catJson = await catRes.json();
        if (catJson.status === 'success') {
            const prodFilter = document.getElementById('product-category-filter');
            const newCat = document.getElementById('new-prod-category');
            (catJson.data || []).forEach(c => {
                if (prodFilter) {
                    const opt = document.createElement('option');
                    opt.value = c.category_id;
                    opt.innerText = c.category_name;
                    prodFilter.appendChild(opt);
                }
                if (newCat) {
                    const opt = document.createElement('option');
                    opt.value = c.category_id;
                    opt.innerText = c.category_name;
                    newCat.appendChild(opt);
                }
            });
        }

        // Load vendors into select
        const venRes = await fetch('/api/vendors');
        const venJson = await venRes.json();
        if (venJson.status === 'success') {
            const newVend = document.getElementById('new-prod-vendor');
            (venJson.data || []).forEach(v => {
                if (newVend) {
                    const opt = document.createElement('option');
                    opt.value = v.seller_id;
                    opt.innerText = v.seller_name;
                    newVend.appendChild(opt);
                }
            });
        }
    } catch (err) {
        console.error('Failed loading bootstrap selects:', err);
    }
}

async function openPlaceOrderModal() {
    // Populate customers and products
    const custRes = await fetch('/api/customers');
    const custJson = await custRes.json();
    const custSelect = document.getElementById('order-cust-select');
    custSelect.innerHTML = '';
    (custJson.data || []).forEach(c => {
        const opt = document.createElement('option');
        opt.value = c.customer_id;
        opt.innerText = `${c.first_name} ${c.last_name} (${c.city})`;
        custSelect.appendChild(opt);
    });

    const prodRes = await fetch('/api/products');
    const prodJson = await prodRes.json();
    const prodSelect = document.getElementById('order-prod-select');
    prodSelect.innerHTML = '';
    (prodJson.data || []).forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.product_id;
        opt.innerText = `${p.product_name} - ₹${p.price} [${p.stock_quantity} in stock]`;
        prodSelect.appendChild(opt);
    });

    openModal('modal-place-order');
}

function openAddProductModal() { openModal('modal-add-product'); }
function openAddVendorModal() { openModal('modal-add-vendor'); }
function openAddCustomerModal() { openModal('modal-add-customer'); }

function openModal(id) {
    document.getElementById(id).classList.remove('hidden');
}

function closeModal(id) {
    document.getElementById(id).classList.add('hidden');
}

// ------------------------------------------------------------------------------
// FORM SUBMISSIONS
// ------------------------------------------------------------------------------
async function submitPlaceOrder(e) {
    e.preventDefault();
    const payload = {
        customer_id: document.getElementById('order-cust-select').value,
        product_id: document.getElementById('order-prod-select').value,
        quantity: document.getElementById('order-qty').value,
        payment_method: document.getElementById('order-pay-method').value
    };

    try {
        const res = await fetch('/api/orders', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const json = await res.json();
        if (json.status === 'success') {
            closeModal('modal-place-order');
            showAlert(`Procedure Execution Success: ${json.message}`, 'success');
            refreshCurrentTab();
        } else {
            showAlert(`Order Placement Failed: ${json.message}`, 'error');
        }
    } catch (err) {
        showAlert('Checkout request failed', 'error');
    }
}

async function submitAddProduct(e) {
    e.preventDefault();
    const payload = {
        product_name: document.getElementById('new-prod-name').value,
        category_id: document.getElementById('new-prod-category').value,
        seller_id: document.getElementById('new-prod-vendor').value,
        price: document.getElementById('new-prod-price').value,
        stock_quantity: document.getElementById('new-prod-stock').value,
        discount_percent: document.getElementById('new-prod-discount').value
    };

    try {
        const res = await fetch('/api/products', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const json = await res.json();
        if (json.status === 'success') {
            closeModal('modal-add-product');
            showAlert(json.message, 'success');
            loadProducts();
        } else {
            showAlert(json.message, 'error');
        }
    } catch (err) {
        showAlert('Product creation failed', 'error');
    }
}

async function submitAddVendor(e) {
    e.preventDefault();
    const payload = {
        seller_name: document.getElementById('new-vendor-name').value,
        email: document.getElementById('new-vendor-email').value,
        phone: document.getElementById('new-vendor-phone').value,
        city: document.getElementById('new-vendor-city').value,
        commission_rate: document.getElementById('new-vendor-comm').value
    };

    try {
        const res = await fetch('/api/vendors', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const json = await res.json();
        if (json.status === 'success') {
            closeModal('modal-add-vendor');
            showAlert(json.message, 'success');
            loadVendors();
            loadBootstrapData();
        } else {
            showAlert(json.message, 'error');
        }
    } catch (err) {
        showAlert('Vendor onboarding failed', 'error');
    }
}

async function submitAddCustomer(e) {
    e.preventDefault();
    const payload = {
        first_name: document.getElementById('new-cust-first').value,
        last_name: document.getElementById('new-cust-last').value,
        email: document.getElementById('new-cust-email').value,
        phone: document.getElementById('new-cust-phone').value,
        city: document.getElementById('new-cust-city').value
    };

    try {
        const res = await fetch('/api/customers', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const json = await res.json();
        if (json.status === 'success') {
            closeModal('modal-add-customer');
            showAlert(json.message, 'success');
            loadCustomers();
        } else {
            showAlert(json.message, 'error');
        }
    } catch (err) {
        showAlert('Customer registration failed', 'error');
    }
}

// ------------------------------------------------------------------------------
// UI HELPERS
// ------------------------------------------------------------------------------
function getStatusBadge(status) {
    const map = {
        Delivered: 'bg-emerald-50 text-emerald-700 border-emerald-200',
        Shipped: 'bg-sky-50 text-sky-700 border-sky-200',
        Processing: 'bg-indigo-50 text-indigo-700 border-indigo-200',
        Pending: 'bg-amber-50 text-amber-700 border-amber-200',
        Cancelled: 'bg-rose-50 text-rose-700 border-rose-200'
    };
    const c = map[status] || 'bg-slate-100 text-slate-700 border-slate-200';
    return `<span class="px-2.5 py-0.5 text-xs font-semibold rounded-full border ${c}">${status}</span>`;
}

function getStockBadge(qty) {
    if (qty === 0) {
        return `<span class="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-rose-50 text-rose-700 border border-rose-200">Out of Stock</span>`;
    } else if (qty <= 10) {
        return `<span class="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-amber-50 text-amber-700 border border-amber-200">Low Stock (${qty})</span>`;
    } else {
        return `<span class="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">In Stock (${qty})</span>`;
    }
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
