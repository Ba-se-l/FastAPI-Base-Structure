/**
 * Health & Telemetry View
 * Monitors server status, database connectivity, latency, and uptime.
 */
import { checkHealth } from './health.api.js';
import { showToast, formatDate, escapeHtml } from '../../shared/ui-helpers.js';

export class HealthView {
    constructor() {
        this.pollInterval = null;
        this.isAutoPolling = false;
        this.countdown = 5;
    }

    render() {
        return `
            <div class="module-card">
                <div class="card-header">
                    <div class="header-title">
                        <h2>Infrastructure Health & Telemetry</h2>
                        <span class="subtitle">Real-time status of backend services, database engine, and connection pool</span>
                    </div>
                    <div class="header-actions">
                        <button class="btn btn-secondary" id="btn-health-poll-toggle">
                            <span class="poll-dot" id="poll-indicator"></span> Auto-Poll (5s): <strong id="poll-status-text">OFF</strong>
                        </button>
                        <button class="btn btn-primary" id="btn-health-refresh">
                            <span class="icon">↻</span> Ping Health Now
                        </button>
                    </div>
                </div>

                <div class="health-metrics-grid" id="health-metrics-grid">
                    <div class="metric-card metric-status">
                        <div class="metric-icon" id="metric-status-icon">⏳</div>
                        <div class="metric-content">
                            <span class="metric-label">System Status</span>
                            <span class="metric-val" id="metric-status-val">Checking...</span>
                        </div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-icon">🗄️</div>
                        <div class="metric-content">
                            <span class="metric-label">Database Status</span>
                            <span class="metric-val" id="metric-db-val">-</span>
                        </div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-icon">⚡</div>
                        <div class="metric-content">
                            <span class="metric-label">Response Latency</span>
                            <span class="metric-val" id="metric-latency-val">-</span>
                        </div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-icon">🏷️</div>
                        <div class="metric-content">
                            <span class="metric-label">App Environment</span>
                            <span class="metric-val" id="metric-env-val">-</span>
                        </div>
                    </div>
                </div>

                <div class="card-section mt-4">
                    <h3>Raw Health Payload</h3>
                    <div class="code-preview" id="health-raw-preview">
                        <pre>Click "Ping Health Now" to fetch live telemetry.</pre>
                    </div>
                </div>
            </div>
        `;
    }

    bindEvents() {
        const refreshBtn = document.getElementById('btn-health-refresh');
        const pollBtn = document.getElementById('btn-health-poll-toggle');

        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.fetchStatus(true));
        }

        if (pollBtn) {
            pollBtn.addEventListener('click', () => this.togglePolling());
        }

        // Fetch on first tab open
        this.fetchStatus(false);
    }

    cleanup() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
        this.isAutoPolling = false;
    }

    togglePolling() {
        this.isAutoPolling = !this.isAutoPolling;
        const statusText = document.getElementById('poll-status-text');
        const dot = document.getElementById('poll-indicator');

        if (this.isAutoPolling) {
            statusText.textContent = 'ON';
            dot?.classList.add('pulse-green');
            showToast('Live Health Auto-Polling enabled (5s interval)', 'info', 2000);
            this.fetchStatus();
            this.pollInterval = setInterval(() => this.fetchStatus(), 5000);
        } else {
            statusText.textContent = 'OFF';
            dot?.classList.remove('pulse-green');
            if (this.pollInterval) {
                clearInterval(this.pollInterval);
                this.pollInterval = null;
            }
            showToast('Health Auto-Polling stopped', 'info', 2000);
        }
    }

    async fetchStatus(manual = false) {
        const startTime = performance.now();
        const statusVal = document.getElementById('metric-status-val');
        const statusIcon = document.getElementById('metric-status-icon');
        const dbVal = document.getElementById('metric-db-val');
        const latencyVal = document.getElementById('metric-latency-val');
        const envVal = document.getElementById('metric-env-val');
        const rawPre = document.getElementById('health-raw-preview');

        try {
            const res = await checkHealth();
            const latency = Math.round(performance.now() - startTime);
            const data = res.data;

            if (res.ok && data) {
                const status = (data.status || 'OK').toUpperCase();
                if (statusVal) {
                    statusVal.textContent = status;
                    statusVal.className = 'metric-val status-green';
                }
                if (statusIcon) statusIcon.textContent = '🟢';
                if (dbVal) {
                    const dbStatus = data.database?.status || data.database || 'HEALTHY';
                    dbVal.textContent = String(dbStatus).toUpperCase();
                }
                if (latencyVal) {
                    latencyVal.textContent = `${latency} ms`;
                }
                if (envVal) {
                    envVal.textContent = data.environment || 'development';
                }
                if (rawPre) {
                    rawPre.innerHTML = `<pre class="syntax-code-block">${JSON.stringify(data, null, 2)}</pre>`;
                }

                if (manual) showToast(`Health check OK (${latency}ms)`, 'success', 2000);
            } else {
                throw new Error(data?.message || `HTTP ${res.status}`);
            }
        } catch (err) {
            if (statusVal) {
                statusVal.textContent = 'UNHEALTHY';
                statusVal.className = 'metric-val status-red';
            }
            if (statusIcon) statusIcon.textContent = '🔴';
            if (rawPre) {
                rawPre.innerHTML = `<pre class="syntax-code-block text-danger">Error: ${escapeHtml(err.message)}</pre>`;
            }
            if (manual) showToast(`Health check failed: ${err.message}`, 'danger', 3000);
        }
    }
}
