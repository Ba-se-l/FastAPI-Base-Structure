/**
 * Audit Logging & Forensics View
 * Features:
 * - Paginated Audit Log Exploration with Action, Entity, and Status filters
 * - Real-time state diff visualizer (old_state vs new_state)
 * - Multi-Format Export Hub (JSON, TXT, Markdown) with in-browser preview and file download
 */
import { listAuditLogs, getAuditLog, exportAuditLogs } from './audit.api.js';
import { showToast, formatDate, escapeHtml, renderBadge, syntaxHighlightJson } from '../../shared/ui-helpers.js';

export class AuditView {
    constructor() {
        this.page = 1;
        this.pageSize = 10;
        this.currentLogs = [];
        this.selectedLog = null;
    }

    render() {
        return `
            <div class="module-card">
                <div class="card-header">
                    <div class="header-title">
                        <h2>Audit Trail & Security Forensics</h2>
                        <span class="subtitle">Immutable record of mutation events, actor attribution, correlation IDs, and state diffs</span>
                    </div>
                    <div class="header-actions">
                        <button class="btn btn-primary" id="btn-audit-refresh">↻ Refresh Logs</button>
                    </div>
                </div>

                <!-- Filters Bar -->
                <div class="filter-toolbar">
                    <div class="filter-group">
                        <label>Action Type:</label>
                        <select id="filter-audit-action" class="form-select">
                            <option value="">All Actions</option>
                            <option value="LOGIN">LOGIN</option>
                            <option value="REGISTER">REGISTER</option>
                            <option value="UPDATE">UPDATE</option>
                            <option value="LOGOUT">LOGOUT</option>
                            <option value="TOKEN_REFRESH">TOKEN_REFRESH</option>
                        </select>
                    </div>
                    <div class="filter-group">
                        <label>Entity:</label>
                        <select id="filter-audit-entity" class="form-select">
                            <option value="">All Entities</option>
                            <option value="User">User</option>
                            <option value="Auth">Auth</option>
                        </select>
                    </div>
                    <div class="filter-group">
                        <label>Status:</label>
                        <select id="filter-audit-status" class="form-select">
                            <option value="">All Statuses</option>
                            <option value="SUCCESS">SUCCESS</option>
                            <option value="FAILURE">FAILURE</option>
                        </select>
                    </div>
                    <button class="btn btn-secondary" id="btn-apply-filters">Apply Filters</button>
                </div>

                <!-- Split Workspace: Logs Table on Left, Diff / Details on Right -->
                <div class="audit-split-view">
                    <!-- Logs Table Panel -->
                    <div class="audit-table-panel">
                        <div class="table-responsive">
                            <table class="data-table" id="table-audit-logs">
                                <thead>
                                    <tr>
                                        <th>Timestamp</th>
                                        <th>Action</th>
                                        <th>Entity</th>
                                        <th>Status</th>
                                        <th>Actor ID</th>
                                        <th>Action</th>
                                    </tr>
                                </thead>
                                <tbody id="tbody-audit-logs">
                                    <tr><td colspan="6" class="text-center text-muted">Loading audit trail...</td></tr>
                                </tbody>
                            </table>
                        </div>

                        <div class="pagination-footer">
                            <button class="btn btn-sm btn-outline" id="btn-audit-prev" disabled>&larr; Prev</button>
                            <span id="audit-page-indicator">Page 1</span>
                            <button class="btn btn-sm btn-outline" id="btn-audit-next">Next &rarr;</button>
                        </div>
                    </div>

                    <!-- Diff & Payload Inspector Panel -->
                    <div class="audit-detail-panel" id="audit-detail-panel">
                        <div class="empty-state">Select an audit log entry on the left to inspect state diff and metadata.</div>
                    </div>
                </div>

                <!-- Export Hub Section -->
                <div class="card-section mt-4">
                    <div class="section-header-row">
                        <div>
                            <h3>Audit Export Hub</h3>
                            <p class="section-desc">Generate compliance reports in JSON, Plaintext, or Markdown formats</p>
                        </div>
                        <div class="export-buttons">
                            <button class="btn btn-outline" id="btn-export-json">📄 Export JSON</button>
                            <button class="btn btn-outline" id="btn-export-txt">📝 Export TXT</button>
                            <button class="btn btn-outline" id="btn-export-md">📑 Export Markdown</button>
                        </div>
                    </div>

                    <div class="export-preview-box" id="export-preview-box" style="display: none;">
                        <div class="export-preview-header">
                            <h4 id="export-preview-title">Export Preview</h4>
                            <div class="actions">
                                <button class="btn btn-sm btn-primary" id="btn-download-export">⬇ Download File</button>
                                <button class="btn btn-sm btn-outline" id="btn-close-export">Close</button>
                            </div>
                        </div>
                        <pre class="syntax-code-block" id="export-preview-content"></pre>
                    </div>
                </div>
            </div>
        `;
    }

    bindEvents() {
        const refreshBtn = document.getElementById('btn-audit-refresh');
        const filterBtn = document.getElementById('btn-apply-filters');
        if (refreshBtn) refreshBtn.addEventListener('click', () => this.loadLogs());
        if (filterBtn) filterBtn.addEventListener('click', () => {
            this.page = 1;
            this.loadLogs();
        });

        const prevBtn = document.getElementById('btn-audit-prev');
        const nextBtn = document.getElementById('btn-audit-next');
        if (prevBtn) {
            prevBtn.addEventListener('click', () => {
                if (this.page > 1) {
                    this.page--;
                    this.loadLogs();
                }
            });
        }
        if (nextBtn) {
            nextBtn.addEventListener('click', () => {
                this.page++;
                this.loadLogs();
            });
        }

        // Export Buttons
        document.getElementById('btn-export-json')?.addEventListener('click', () => this.handleExport('json'));
        document.getElementById('btn-export-txt')?.addEventListener('click', () => this.handleExport('txt'));
        document.getElementById('btn-export-md')?.addEventListener('click', () => this.handleExport('markdown'));
        document.getElementById('btn-close-export')?.addEventListener('click', () => {
            const box = document.getElementById('export-preview-box');
            if (box) box.style.display = 'none';
        });

        this.loadLogs();
    }

    cleanup() {}

    async loadLogs() {
        const tbody = document.getElementById('tbody-audit-logs');
        if (!tbody) return;

        const action = document.getElementById('filter-audit-action')?.value;
        const entity = document.getElementById('filter-audit-entity')?.value;
        const status = document.getElementById('filter-audit-status')?.value;

        const params = {
            page: this.page,
            page_size: this.pageSize,
        };
        if (action) params.action = action;
        if (entity) params.entity_type = entity;
        if (status) params.status = status;

        try {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">Fetching audit records...</td></tr>';
            const res = await listAuditLogs(params);

            if (res.ok && res.data) {
                const items = Array.isArray(res.data) ? res.data : (res.data.items || []);
                this.currentLogs = items;

                if (items.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No audit events matched current criteria.</td></tr>';
                    return;
                }

                tbody.innerHTML = items.map(log => {
                    const isSuccess = log.status === 'SUCCESS' || (log.status_code >= 200 && log.status_code < 400);
                    return `
                        <tr class="audit-row" data-id="${log.id}">
                            <td>${formatDate(log.timestamp || log.created_at)}</td>
                            <td><span class="bold">${escapeHtml(log.action)}</span></td>
                            <td>${escapeHtml(log.entity_type || log.resource || '-')}</td>
                            <td>${renderBadge(isSuccess ? 'success' : 'danger', log.status || (isSuccess ? 'SUCCESS' : 'FAILURE'))}</td>
                            <td class="code-font">${log.actor_id ? escapeHtml(log.actor_id.substring(0, 8)) + '...' : 'System'}</td>
                            <td>
                                <button class="btn btn-xs btn-outline btn-inspect-audit" data-id="${log.id}">View Diff</button>
                            </td>
                        </tr>
                    `;
                }).join('');

                // Attach click listeners
                tbody.querySelectorAll('.btn-inspect-audit').forEach(btn => {
                    btn.addEventListener('click', (e) => {
                        e.stopPropagation();
                        const id = btn.dataset.id;
                        this.inspectLog(id);
                    });
                });

                tbody.querySelectorAll('.audit-row').forEach(row => {
                    row.addEventListener('click', () => {
                        const id = row.dataset.id;
                        this.inspectLog(id);
                    });
                });

                // Update pagination controls
                const pageInd = document.getElementById('audit-page-indicator');
                const prevBtn = document.getElementById('btn-audit-prev');
                const nextBtn = document.getElementById('btn-audit-next');
                if (pageInd) pageInd.textContent = `Page ${this.page}`;
                if (prevBtn) prevBtn.disabled = this.page <= 1;
                if (nextBtn) nextBtn.disabled = items.length < this.pageSize;

            } else {
                tbody.innerHTML = `<tr><td colspan="6" class="text-center text-danger">Failed to load logs (Status ${res.status})</td></tr>`;
            }
        } catch (err) {
            tbody.innerHTML = `<tr><td colspan="6" class="text-center text-danger">Error: ${escapeHtml(err.message)}</td></tr>`;
        }
    }

    inspectLog(logId) {
        const log = this.currentLogs.find(l => String(l.id) === String(logId));
        if (!log) return;
        this.selectedLog = log;

        const panel = document.getElementById('audit-detail-panel');
        if (!panel) return;

        const oldState = log.old_state || log.previous_state || null;
        const newState = log.new_state || log.current_state || log.changes || null;

        panel.innerHTML = `
            <div class="audit-detail-header">
                <h3>Event: ${escapeHtml(log.action)} on ${escapeHtml(log.entity_type || 'Unknown')}</h3>
                <span class="code-font small text-muted">ID: ${escapeHtml(log.id)}</span>
            </div>

            <div class="audit-meta-summary">
                <div class="meta-line"><strong>Actor:</strong> <code>${escapeHtml(log.actor_id || 'Anonymous / System')}</code></div>
                <div class="meta-line"><strong>Client IP:</strong> <code>${escapeHtml(log.ip_address || log.client_ip || '127.0.0.1')}</code></div>
                <div class="meta-line"><strong>Request ID:</strong> <code>${escapeHtml(log.request_id || '-')}</code></div>
                <div class="meta-line"><strong>Timestamp:</strong> <span>${formatDate(log.timestamp || log.created_at)}</span></div>
            </div>

            <div class="diff-viewer-wrapper mt-3">
                <div class="diff-header-bar">
                    <span class="diff-title">State Mutation Diff</span>
                </div>
                <div class="diff-columns">
                    <div class="diff-column">
                        <span class="diff-col-title diff-col-old">Previous State (Before)</span>
                        <pre class="syntax-code-block">${syntaxHighlightJson(oldState)}</pre>
                    </div>
                    <div class="diff-column">
                        <span class="diff-col-title diff-col-new">New State (After)</span>
                        <pre class="syntax-code-block">${syntaxHighlightJson(newState)}</pre>
                    </div>
                </div>
            </div>
        `;
    }

    async handleExport(format) {
        showToast(`Preparing ${format.toUpperCase()} export...`, 'info', 2000);
        try {
            const res = await exportAuditLogs(format, {});
            if (res.ok && res.data) {
                const content = typeof res.data === 'object' ? JSON.stringify(res.data, null, 2) : String(res.data);
                const previewBox = document.getElementById('export-preview-box');
                const titleEl = document.getElementById('export-preview-title');
                const contentEl = document.getElementById('export-preview-content');
                const downloadBtn = document.getElementById('btn-download-export');

                if (previewBox && titleEl && contentEl) {
                    titleEl.textContent = `Export Preview: audit_export.${format === 'markdown' ? 'md' : format}`;
                    contentEl.textContent = content;
                    previewBox.style.display = 'block';

                    if (downloadBtn) {
                        downloadBtn.onclick = () => {
                            const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
                            const url = URL.createObjectURL(blob);
                            const a = document.createElement('a');
                            a.href = url;
                            a.download = `audit_export_${Date.now()}.${format === 'markdown' ? 'md' : format}`;
                            document.body.appendChild(a);
                            a.click();
                            a.remove();
                            URL.revokeObjectURL(url);
                            showToast('File download started', 'success', 2000);
                        };
                    }
                }
            } else {
                showToast(`Export failed: ${res.data?.message || res.status}`, 'danger', 3000);
            }
        } catch (err) {
            showToast(`Export error: ${err.message}`, 'danger', 3000);
        }
    }
}
