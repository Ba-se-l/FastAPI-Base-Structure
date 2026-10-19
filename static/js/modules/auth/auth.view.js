/**
 * Authentication & Dual-Device Lineage Workbench View
 * Provides:
 * 1. 1-Click Demo Setup (Creates account, logs into Device A & B concurrently)
 * 2. Visual Device A vs Device B token cards with decoded JWT claims (sub, fid, jti, sec_ver, exp)
 * 3. Token Rotation trigger per device
 * 4. Token Replay Attack Simulator (tests family invalidation and isolation)
 * 5. Logout & Logout-all controls
 */
import { register, login, refreshToken, logout, logoutAll } from './auth.api.js';
import { sessionStore } from '../../core/session-store.js';
import { formatTimeRemaining } from '../../core/jwt-decoder.js';
import { showToast, escapeHtml } from '../../shared/ui-helpers.js';
import { eventBus } from '../../core/event-emitter.js';

export class AuthView {
    constructor() {
        this.unsubscribe = null;
    }

    render() {
        const activeSlot = sessionStore.getActiveSlot();
        const sessionA = sessionStore.getSession('device_a');
        const sessionB = sessionStore.getSession('device_b');
        const replay = sessionStore.getReplayBuffer();

        return `
            <div class="module-card">
                <div class="card-header">
                    <div class="header-title">
                        <h2>Authentication & Multi-Device Lineage</h2>
                        <span class="subtitle">Dual concurrent virtual devices, Argon2id validation, token rotation, and replay detection</span>
                    </div>
                    <div class="header-actions">
                        <button class="btn btn-warning" id="btn-1click-demo" title="Auto-registers test user and logs in to Device A and Device B simultaneously">
                            🚀 1-Click Demo Setup
                        </button>
                        <button class="btn btn-danger btn-outline" id="btn-clear-sessions">
                            Clear All Sessions
                        </button>
                    </div>
                </div>

                <!-- Active Slot Selector -->
                <div class="device-selector-bar">
                    <span class="selector-label">Active HTTP Client Target:</span>
                    <button class="device-pill ${activeSlot === 'device_a' ? 'active' : ''}" data-slot="device_a" id="pill-device-a">
                        📱 Device A (Laptop / Workstation)
                    </button>
                    <button class="device-pill ${activeSlot === 'device_b' ? 'active' : ''}" data-slot="device_b" id="pill-device-b">
                        📱 Device B (Mobile / Remote)
                    </button>
                </div>

                <!-- Dual Device Grid -->
                <div class="devices-grid">
                    <!-- Device A Card -->
                    <div class="device-card ${activeSlot === 'device_a' ? 'is-active-device' : ''}" id="card-device-a">
                        <div class="device-card-header">
                            <div class="device-name">
                                <span class="device-badge">Device A</span>
                                <h3>Laptop Workstation</h3>
                            </div>
                            <span class="device-status ${sessionA ? 'status-online' : 'status-offline'}">
                                ${sessionA ? '● Authenticated' : '○ Logged Out'}
                            </span>
                        </div>
                        <div class="device-body">
                            ${this._renderDeviceContent('device_a', sessionA)}
                        </div>
                    </div>

                    <!-- Device B Card -->
                    <div class="device-card ${activeSlot === 'device_b' ? 'is-active-device' : ''}" id="card-device-b">
                        <div class="device-card-header">
                            <div class="device-name">
                                <span class="device-badge badge-purple">Device B</span>
                                <h3>Mobile Device</h3>
                            </div>
                            <span class="device-status ${sessionB ? 'status-online' : 'status-offline'}">
                                ${sessionB ? '● Authenticated' : '○ Logged Out'}
                            </span>
                        </div>
                        <div class="device-body">
                            ${this._renderDeviceContent('device_b', sessionB)}
                        </div>
                    </div>
                </div>

                <!-- Replay Attack Simulator Panel -->
                <div class="card-section mt-4">
                    <div class="section-header-row">
                        <div>
                            <h3>Token Family Replay Attack Simulator</h3>
                            <p class="section-desc">When a refresh token is rotated, the old token becomes stale. If a malicious actor (or network duplicate) attempts to replay the old token, the backend detects token theft, burns the token family, and invalidates all descendant sessions.</p>
                        </div>
                        <div class="replay-actions">
                            <button class="btn btn-danger" id="btn-trigger-replay" ${!replay ? 'disabled' : ''}>
                                ⚠️ Execute Replay Attack on Rotated Token
                            </button>
                        </div>
                    </div>

                    <div class="replay-status-box" id="replay-status-box">
                        ${this._renderReplayStatus(replay)}
                    </div>
                </div>

                <!-- Manual Login & Registration Forms -->
                <div class="card-section mt-4">
                    <h3>Manual Credential Operations (Targeting ${activeSlot === 'device_a' ? 'Device A' : 'Device B'})</h3>
                    <div class="auth-forms-grid">
                        <!-- Login Form -->
                        <div class="form-card">
                            <h4>Login to ${activeSlot === 'device_a' ? 'Device A' : 'Device B'}</h4>
                            <form id="form-login">
                                <div class="form-group">
                                    <label>Email Address</label>
                                    <input type="email" id="login-email" class="form-input" placeholder="user@example.com" required value="admin@example.com">
                                </div>
                                <div class="form-group">
                                    <label>Password</label>
                                    <input type="password" id="login-password" class="form-input" placeholder="••••••••" required value="SecureAdmin@2026!">
                                </div>
                                <button type="submit" class="btn btn-primary w-100" id="btn-login-submit">Login</button>
                            </form>
                        </div>

                        <!-- Register Form -->
                        <div class="form-card">
                            <h4>Register New User</h4>
                            <form id="form-register">
                                <div class="form-group">
                                    <label>Full Name</label>
                                    <input type="text" id="reg-name" class="form-input" placeholder="Jane Doe" required value="Test Engineer">
                                </div>
                                <div class="form-group">
                                    <label>Email Address</label>
                                    <input type="email" id="reg-email" class="form-input" placeholder="engineer@example.com" required value="test_user_${Date.now().toString().slice(-4)}@example.com">
                                </div>
                                <div class="form-group">
                                    <label>Password (Argon2id)</label>
                                    <input type="password" id="reg-password" class="form-input" placeholder="Min 8 chars" required value="StrongP@ssw0rd!2026">
                                </div>
                                <button type="submit" class="btn btn-secondary w-100" id="btn-register-submit">Register Account</button>
                            </form>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    _renderDeviceContent(slot, session) {
        if (!session) {
            return `
                <div class="device-empty">
                    <p>No active token session for this device slot.</p>
                    <p class="text-muted small">Use 1-Click Demo or Login below to populate tokens.</p>
                </div>
            `;
        }

        const access = session.accessClaims || {};
        const refresh = session.refreshClaims || {};

        return `
            <div class="claims-summary">
                <div class="claims-row">
                    <span class="claim-label">Subject (User ID):</span>
                    <span class="claim-val code-font">${escapeHtml(access.sub || '-')}</span>
                </div>
                <div class="claims-row">
                    <span class="claim-label">Family ID (fid):</span>
                    <span class="claim-val code-font badge-fid">${escapeHtml(refresh.fid || access.fid || 'None')}</span>
                </div>
                <div class="claims-row">
                    <span class="claim-label">Security Version (sec_ver):</span>
                    <span class="claim-val bold">${escapeHtml(access.sec_ver ?? refresh.sec_ver ?? 1)}</span>
                </div>
                <div class="claims-row">
                    <span class="claim-label">Refresh JTI:</span>
                    <span class="claim-val code-font">${escapeHtml(refresh.jti ? refresh.jti.substring(0, 16) + '...' : '-')}</span>
                </div>
                <div class="claims-row">
                    <span class="claim-label">Access Expiry:</span>
                    <span class="claim-val">${formatTimeRemaining(access.exp)}</span>
                </div>
                <div class="claims-row">
                    <span class="claim-label">Refresh Expiry:</span>
                    <span class="claim-val">${formatTimeRemaining(refresh.exp)}</span>
                </div>
            </div>

            <div class="device-actions-bar">
                <button class="btn btn-sm btn-outline btn-rotate" data-slot="${slot}" title="Rotates refresh token and saves previous token to replay buffer">
                    🔄 Rotate Token
                </button>
                <button class="btn btn-sm btn-outline btn-logout" data-slot="${slot}">
                    Logout Device
                </button>
                <button class="btn btn-sm btn-outline btn-danger btn-logout-all" data-slot="${slot}" title="Invalidates all sessions across all devices for this user">
                    Logout All Devices
                </button>
            </div>
        `;
    }

    _renderReplayStatus(replay) {
        if (!replay) {
            return `
                <div class="replay-empty">
                    <span>No stale token captured yet. Click <strong>"Rotate Token"</strong> on Device A or B above to prepare a replay test.</span>
                </div>
            `;
        }
        return `
            <div class="replay-captured">
                <div class="replay-info-line">
                    <span class="badge badge-warning">Stale Token Armed</span>
                    <span>Captured from <strong>${replay.deviceSlot === 'device_b' ? 'Device B' : 'Device A'}</strong> at ${new Date(replay.capturedAt).toLocaleTimeString()}</span>
                    <span>Family ID: <code>${escapeHtml(replay.previousFid || 'N/A')}</code></span>
                    <span>Previous JTI: <code>${escapeHtml(replay.previousJti ? replay.previousJti.substring(0, 12) + '...' : 'N/A')}</code></span>
                </div>
            </div>
        `;
    }

    bindEvents() {
        // Unsubscribe previous session changes if any
        if (this.unsubscribe) this.unsubscribe();
        this.unsubscribe = eventBus.on('session:changed', () => {
            this.updateView();
        });

        // 1-Click Demo
        const demoBtn = document.getElementById('btn-1click-demo');
        if (demoBtn) {
            demoBtn.addEventListener('click', () => this.handle1ClickDemo());
        }

        // Clear All Sessions
        const clearBtn = document.getElementById('btn-clear-sessions');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => {
                sessionStore.clearAllSessions();
                showToast('All local device sessions cleared', 'info', 2000);
            });
        }

        // Slot Switchers
        const pillA = document.getElementById('pill-device-a');
        const pillB = document.getElementById('pill-device-b');
        if (pillA) {
            pillA.addEventListener('click', () => {
                sessionStore.setActiveSlot('device_a');
                showToast('Active HTTP client switched to Device A', 'info', 1500);
            });
        }
        if (pillB) {
            pillB.addEventListener('click', () => {
                sessionStore.setActiveSlot('device_b');
                showToast('Active HTTP client switched to Device B', 'info', 1500);
            });
        }

        // Action Buttons inside device cards
        document.querySelectorAll('.btn-rotate').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const slot = btn.dataset.slot;
                this.handleRotate(slot);
            });
        });

        document.querySelectorAll('.btn-logout').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const slot = btn.dataset.slot;
                this.handleLogout(slot);
            });
        });

        document.querySelectorAll('.btn-logout-all').forEach(btn => {
            btn.addEventListener('click', () => {
                this.handleLogoutAll();
            });
        });

        // Replay Trigger
        const replayBtn = document.getElementById('btn-trigger-replay');
        if (replayBtn) {
            replayBtn.addEventListener('click', () => this.handleReplayAttack());
        }

        // Forms
        const loginForm = document.getElementById('form-login');
        if (loginForm) {
            loginForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleManualLogin();
            });
        }

        const regForm = document.getElementById('form-register');
        if (regForm) {
            regForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleManualRegister();
            });
        }
    }

    cleanup() {
        if (this.unsubscribe) {
            this.unsubscribe();
            this.unsubscribe = null;
        }
    }

    updateView() {
        // Re-render whole module or parts
        const container = document.getElementById('view-auth');
        if (container) {
            container.innerHTML = this.render();
            this.bindEvents();
        }
    }

    async handle1ClickDemo() {
        showToast('Initiating 1-Click Multi-Device Demo Setup...', 'info', 2500);
        const randomNum = Math.floor(1000 + Math.random() * 9000);
        const demoEmail = `demo.architect.${randomNum}@example.com`;
        const demoPassword = 'DemoPassword!2026';
        const demoName = `Workbench Demo User ${randomNum}`;

        try {
            // Step 1: Register User
            const regRes = await register({
                email: demoEmail,
                password: demoPassword,
                name: demoName
            });

            if (!regRes.ok) {
                throw new Error(regRes.data?.message || 'Registration failed');
            }

            // Step 2: Login Device A
            sessionStore.setActiveSlot('device_a');
            const loginResA = await login({
                email: demoEmail,
                password: demoPassword
            });
            if (!loginResA.ok) throw new Error('Device A Login failed');
            sessionStore.setSession('device_a', {
                accessToken: loginResA.data.access_token,
                refreshToken: loginResA.data.refresh_token,
                user: loginResA.data.user || { email: demoEmail }
            });

            // Step 3: Login Device B
            sessionStore.setActiveSlot('device_b');
            const loginResB = await login({
                email: demoEmail,
                password: demoPassword
            });
            if (!loginResB.ok) throw new Error('Device B Login failed');
            sessionStore.setSession('device_b', {
                accessToken: loginResB.data.access_token,
                refreshToken: loginResB.data.refresh_token,
                user: loginResB.data.user || { email: demoEmail }
            });

            // Switch default back to Device A
            sessionStore.setActiveSlot('device_a');

            showToast(`Success! Logged in as ${demoEmail} on Device A and Device B simultaneously.`, 'success', 4000);

        } catch (err) {
            showToast(`1-Click Demo failed: ${err.message}`, 'danger', 4000);
        }
    }

    async handleRotate(slot) {
        const session = sessionStore.getSession(slot);
        if (!session?.refreshToken) {
            showToast('No active session or refresh token found for this device', 'warning', 2500);
            return;
        }

        const oldRefreshToken = session.refreshToken;
        const oldRefreshClaims = session.refreshClaims;

        try {
            showToast(`Rotating token on ${slot}...`, 'info', 2000);
            const res = await refreshToken(oldRefreshToken);
            if (!res.ok) {
                throw new Error(res.data?.message || `Rotation failed (${res.status})`);
            }

            // Save old token into replay buffer for replay attack testing!
            sessionStore.setReplayBuffer({
                token: oldRefreshToken,
                deviceSlot: slot,
                previousFid: oldRefreshClaims?.fid,
                previousJti: oldRefreshClaims?.jti
            });

            // Update device session with new pair
            sessionStore.setSession(slot, {
                accessToken: res.data.access_token,
                refreshToken: res.data.refresh_token,
                user: session.user
            });

            showToast(`Token successfully rotated! Stale token captured into Replay Simulator.`, 'success', 3500);

        } catch (err) {
            showToast(`Token rotation failed: ${err.message}`, 'danger', 3500);
        }
    }

    async handleReplayAttack() {
        const replay = sessionStore.getReplayBuffer();
        if (!replay?.token) {
            showToast('No captured stale token available in replay buffer', 'warning', 2500);
            return;
        }

        try {
            showToast(`Simulating REPLAY ATTACK with previously rotated token...`, 'warning', 3000);
            // Attempt to refresh using the stale token
            const res = await refreshToken(replay.token);

            if (res.status === 401 || !res.ok) {
                // Expected defense behavior! Token family invalidated!
                showToast(`🛡️ Defense Activated! Backend rejected stale token (Status ${res.status}). Family invalidated!`, 'success', 5000);
                // Clear the replayed device session because backend invalidated it
                sessionStore.clearSession(replay.deviceSlot);
                sessionStore.clearReplayBuffer();
            } else {
                showToast(`⚠️ Warning: Backend unexpectedly accepted the replayed token!`, 'danger', 4000);
            }
        } catch (err) {
            showToast(`Replay execution error: ${err.message}`, 'danger', 3500);
        }
    }

    async handleLogout(slot) {
        const session = sessionStore.getSession(slot);
        if (!session?.refreshToken) {
            sessionStore.clearSession(slot);
            showToast(`Cleared ${slot} session`, 'info', 2000);
            return;
        }

        try {
            const res = await logout(session.refreshToken);
            sessionStore.clearSession(slot);
            if (res.ok) {
                showToast(`Successfully logged out ${slot}`, 'success', 2500);
            } else {
                showToast(`Logout completed locally (Server returned ${res.status})`, 'warning', 2500);
            }
        } catch (err) {
            sessionStore.clearSession(slot);
            showToast(`Logout completed locally`, 'info', 2000);
        }
    }

    async handleLogoutAll() {
        try {
            const res = await logoutAll();
            sessionStore.clearAllSessions();
            if (res.ok) {
                showToast('All sessions invalidated across all devices (Security version incremented)', 'success', 4000);
            } else {
                showToast(`Logout-all executed locally (Server returned ${res.status})`, 'warning', 2500);
            }
        } catch (err) {
            sessionStore.clearAllSessions();
            showToast('Cleared all local device sessions', 'info', 2000);
        }
    }

    async handleManualLogin() {
        const email = document.getElementById('login-email')?.value;
        const password = document.getElementById('login-password')?.value;
        const slot = sessionStore.getActiveSlot();

        try {
            showToast(`Logging in to ${slot}...`, 'info', 2000);
            const res = await login({ email, password });
            if (!res.ok) {
                throw new Error(res.data?.message || `Login failed (${res.status})`);
            }
            sessionStore.setSession(slot, {
                accessToken: res.data.access_token,
                refreshToken: res.data.refresh_token,
                user: res.data.user || { email }
            });
            showToast(`Login successful for ${slot}!`, 'success', 2500);
        } catch (err) {
            showToast(`Login failed: ${err.message}`, 'danger', 3500);
        }
    }

    async handleManualRegister() {
        const name = document.getElementById('reg-name')?.value;
        const email = document.getElementById('reg-email')?.value;
        const password = document.getElementById('reg-password')?.value;

        try {
            showToast('Registering user...', 'info', 2000);
            const res = await register({ name, email, password });
            if (!res.ok) {
                throw new Error(res.data?.message || `Registration failed (${res.status})`);
            }
            showToast('Registration successful! You can now log in.', 'success', 3000);
            // Autofill login email
            const loginEmailInput = document.getElementById('login-email');
            if (loginEmailInput) loginEmailInput.value = email;
            const loginPassInput = document.getElementById('login-password');
            if (loginPassInput) loginPassInput.value = password;
        } catch (err) {
            showToast(`Registration failed: ${err.message}`, 'danger', 3500);
        }
    }
}
