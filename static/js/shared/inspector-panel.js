/**
 * Network Inspector Panel
 * Captures all HTTP transactions from HttpClient, provides split-pane inspection,
 * cURL generator, and latency/request-id telemetry.
 */
import { eventBus } from '../core/event-emitter.js';
import { syntaxHighlightJson, copyToClipboard, showToast, escapeHtml } from './ui-helpers.js';

class NetworkInspector {
    constructor() {
        this.transactions = [];
        this.activeTransaction = null;
        this.filter = 'all'; // 'all', '2xx', '4xx', '5xx'
        this.isDrawerExpanded = false;
        this._initListeners();
    }

    _initListeners() {
        eventBus.on('http:transaction', (tx) => {
            this.addTransaction(tx);
        });
    }

    bindDOM() {
        this.toggleBtn = document.getElementById('inspector-toggle-btn');
        this.drawer = document.getElementById('network-inspector-drawer');
        this.counterBadge = document.getElementById('inspector-count-badge');
        this.listEl = document.getElementById('inspector-tx-list');
        this.detailEl = document.getElementById('inspector-tx-detail');
        this.clearBtn = document.getElementById('inspector-clear-btn');
        this.filterBtns = document.querySelectorAll('.inspector-filter-btn');

        if (this.toggleBtn && this.drawer) {
            this.toggleBtn.addEventListener('click', () => this.toggleDrawer());
        }

        if (this.clearBtn) {
            this.clearBtn.addEventListener('click', () => this.clear());
        }

        if (this.filterBtns) {
            this.filterBtns.forEach(btn => {
                btn.addEventListener('click', (e) => {
                    this.filterBtns.forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');
                    this.filter = btn.dataset.filter || 'all';
                    this.renderList();
                });
            });
        }
    }

    toggleDrawer(forceState = null) {
        if (!this.drawer) return;
        this.isDrawerExpanded = forceState !== null ? forceState : !this.isDrawerExpanded;
        if (this.isDrawerExpanded) {
            this.drawer.classList.add('expanded');
        } else {
            this.drawer.classList.remove('expanded');
        }
    }

    addTransaction(tx) {
        // Prepend transaction with unique ID
        const item = {
            id: 'tx_' + Math.random().toString(36).substring(2, 9),
            ...tx,
        };
        this.transactions.unshift(item);
        if (this.transactions.length > 50) {
            this.transactions.pop();
        }

        // Auto-select the newest transaction
        this.activeTransaction = item;
        this.updateBadge();
        this.renderList();
        this.renderDetail();
    }

    clear() {
        this.transactions = [];
        this.activeTransaction = null;
        this.updateBadge();
        this.renderList();
        this.renderDetail();
        showToast('Inspector network log cleared', 'info', 2000);
    }

    updateBadge() {
        if (this.counterBadge) {
            this.counterBadge.textContent = this.transactions.length;
        }
    }

    renderList() {
        if (!this.listEl) return;
        
        let filtered = this.transactions;
        if (this.filter === '2xx') {
            filtered = this.transactions.filter(t => t.response.status >= 200 && t.response.status < 300);
        } else if (this.filter === '4xx') {
            filtered = this.transactions.filter(t => t.response.status >= 400 && t.response.status < 500);
        } else if (this.filter === '5xx') {
            filtered = this.transactions.filter(t => t.response.status >= 500 || t.response.status === 0);
        }

        if (filtered.length === 0) {
            this.listEl.innerHTML = '<div class="empty-state-small">No network transactions yet</div>';
            return;
        }

        this.listEl.innerHTML = filtered.map(t => {
            const isSelected = this.activeTransaction?.id === t.id ? 'active' : '';
            const status = t.response.status;
            let statusCls = 'status-2xx';
            if (status >= 400 && status < 500) statusCls = 'status-4xx';
            else if (status >= 500 || status === 0) statusCls = 'status-5xx';

            // Extract relative endpoint for display
            let urlDisplay = t.request.url;
            try {
                const parsed = new URL(t.request.url, window.location.origin);
                urlDisplay = parsed.pathname + parsed.search;
            } catch {}

            return `
                <div class="tx-item ${isSelected}" data-id="${t.id}">
                    <div class="tx-item-header">
                        <span class="method-pill method-${t.request.method.toLowerCase()}">${t.request.method}</span>
                        <span class="status-pill ${statusCls}">${status || 'ERR'}</span>
                        <span class="tx-duration">${t.response.durationMs}ms</span>
                    </div>
                    <div class="tx-url" title="${escapeHtml(t.request.url)}">${escapeHtml(urlDisplay)}</div>
                    <div class="tx-footer">
                        <span class="device-tag">${t.request.deviceSlot === 'device_b' ? 'Device B' : 'Device A'}</span>
                        <span class="tx-time">${new Date(t.request.timestamp).toLocaleTimeString()}</span>
                    </div>
                </div>
            `;
        }).join('');

        // Attach click listener
        this.listEl.querySelectorAll('.tx-item').forEach(el => {
            el.addEventListener('click', () => {
                const id = el.dataset.id;
                this.activeTransaction = this.transactions.find(t => t.id === id);
                this.renderList();
                this.renderDetail();
            });
        });
    }

    renderDetail() {
        if (!this.detailEl) return;
        const tx = this.activeTransaction;
        if (!tx) {
            this.detailEl.innerHTML = '<div class="empty-state">Select a request on the left to inspect headers, payload, and envelopes.</div>';
            return;
        }

        const req = tx.request;
        const res = tx.response;
        const reqId = res.headers['x-request-id'] || req.headers['x-request-id'] || req.headers['X-Request-ID'] || 'None';

        this.detailEl.innerHTML = `
            <div class="detail-header-bar">
                <div class="detail-title-group">
                    <span class="method-badge method-${req.method.toLowerCase()}">${req.method}</span>
                    <span class="detail-url" title="${escapeHtml(req.url)}">${escapeHtml(req.url)}</span>
                </div>
                <div class="detail-actions">
                    <button class="btn btn-sm btn-outline" id="btn-copy-curl">Copy cURL</button>
                    <button class="btn btn-sm btn-outline" id="btn-copy-json">Copy JSON</button>
                </div>
            </div>

            <div class="detail-meta-grid">
                <div class="meta-item"><span class="meta-label">Status:</span> <span class="meta-value bold">${res.status} ${escapeHtml(res.statusText || '')}</span></div>
                <div class="meta-item"><span class="meta-label">Duration:</span> <span class="meta-value">${res.durationMs} ms</span></div>
                <div class="meta-item"><span class="meta-label">Device Slot:</span> <span class="meta-value badge badge-purple">${req.deviceSlot}</span></div>
                <div class="meta-item"><span class="meta-label">X-Request-ID:</span> <span class="meta-value code-font">${escapeHtml(reqId)}</span></div>
            </div>

            <div class="detail-tabs">
                <button class="detail-tab-btn active" data-tab="res-body">Response Body</button>
                <button class="detail-tab-btn" data-tab="req-body">Request Body</button>
                <button class="detail-tab-btn" data-tab="res-headers">Response Headers</button>
                <button class="detail-tab-btn" data-tab="req-headers">Request Headers</button>
            </div>

            <div class="detail-tab-contents">
                <div class="detail-pane active" id="pane-res-body">
                    <pre class="syntax-code-block">${syntaxHighlightJson(res.data)}</pre>
                </div>
                <div class="detail-pane" id="pane-req-body">
                    <pre class="syntax-code-block">${req.body ? syntaxHighlightJson(req.body) : '<span class="empty-dim">&lt;No Request Body&gt;</span>'}</pre>
                </div>
                <div class="detail-pane" id="pane-res-headers">
                    <table class="inspector-table">
                        <thead><tr><th>Header</th><th>Value</th></tr></thead>
                        <tbody>
                            ${Object.entries(res.headers).map(([k, v]) => `<tr><td class="bold">${escapeHtml(k)}</td><td>${escapeHtml(v)}</td></tr>`).join('')}
                        </tbody>
                    </table>
                </div>
                <div class="detail-pane" id="pane-req-headers">
                    <table class="inspector-table">
                        <thead><tr><th>Header</th><th>Value</th></tr></thead>
                        <tbody>
                            ${Object.entries(req.headers).map(([k, v]) => `<tr><td class="bold">${escapeHtml(k)}</td><td>${escapeHtml(v)}</td></tr>`).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        `;

        // Tab switching logic
        const tabBtns = this.detailEl.querySelectorAll('.detail-tab-btn');
        const panes = this.detailEl.querySelectorAll('.detail-pane');
        tabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                tabBtns.forEach(b => b.classList.remove('active'));
                panes.forEach(p => p.classList.remove('active'));
                btn.classList.add('active');
                const target = this.detailEl.querySelector(`#pane-${btn.dataset.tab}`);
                if (target) target.classList.add('active');
            });
        });

        // Copy cURL logic
        const copyCurlBtn = this.detailEl.querySelector('#btn-copy-curl');
        if (copyCurlBtn) {
            copyCurlBtn.addEventListener('click', () => {
                const curlCmd = this.generateCurl(tx);
                copyToClipboard(curlCmd).then(() => {
                    showToast('cURL command copied to clipboard!', 'success', 2500);
                });
            });
        }

        // Copy JSON logic
        const copyJsonBtn = this.detailEl.querySelector('#btn-copy-json');
        if (copyJsonBtn) {
            copyJsonBtn.addEventListener('click', () => {
                const jsonStr = JSON.stringify(res.data, null, 2);
                copyToClipboard(jsonStr).then(() => {
                    showToast('Response JSON copied to clipboard!', 'success', 2500);
                });
            });
        }
    }

    generateCurl(tx) {
        const req = tx.request;
        let cmd = `curl -X ${req.method} "${req.url}"`;
        for (const [k, v] of Object.entries(req.headers)) {
            cmd += ` \\n  -H "${k}: ${v.replace(/"/g, '\\"')}"`;
        }
        if (req.body) {
            const bodyStr = typeof req.body === 'string' ? req.body : JSON.stringify(req.body);
            cmd += ` \\n  --data '${bodyStr.replace(/'/g, "'\\''")}'`;
        }
        return cmd;
    }
}

export const networkInspector = new NetworkInspector();
