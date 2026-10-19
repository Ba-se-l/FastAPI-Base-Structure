/**
 * User Management & RBAC View
 * Inspects current profile (/me), tests PATCH updates, Casbin 403 authorization,
 * soft deactivation, and paginated user directory.
 */
import { getMe, listUsers, updateUser } from './user.api.js';
import { sessionStore } from '../../core/session-store.js';
import { showToast, formatDate, escapeHtml, renderBadge } from '../../shared/ui-helpers.js';

export class UserView {
    constructor() {
        this.currentUser = null;
        this.directoryPage = 1;
        this.directoryPageSize = 5;
    }

    render() {
        const activeSlot = sessionStore.getActiveSlot();
        const session = sessionStore.getSession(activeSlot);

        if (!session?.accessToken) {
            return `
                <div class="module-card">
                    <div class="card-header">
                        <h2>User Management & RBAC</h2>
                    </div>
                    <div class="auth-gate-banner">
                        <div class="gate-icon">🔒</div>
                        <h3>Authentication Required</h3>
                        <p>No active token found for <strong>${activeSlot === 'device_b' ? 'Device B' : 'Device A'}</strong>.</p>
                        <p>Please log in or click <strong>"1-Click Demo Setup"</strong> in the Authentication tab first.</p>
                    </div>
                </div>
            `;
        }

        return `
            <div class="module-card">
                <div class="card-header">
                    <div class="header-title">
                        <h2>User Identity & Access Management (RBAC)</h2>
                        <span class="subtitle">Inspecting current subject (${activeSlot}), testing attribute mutations, and Casbin access policy checks</span>
                    </div>
                    <div class="header-actions">
                        <button class="btn btn-secondary" id="btn-user-refresh">↻ Refresh Profile</button>
                    </div>
                </div>

                <div class="profile-layout-grid">
                    <!-- Current User Card -->
                    <div class="profile-card">
                        <div class="profile-header">
                            <div class="avatar-circle" id="user-avatar">👤</div>
                            <div class="profile-title">
                                <h3 id="user-display-name">Loading Profile...</h3>
                                <span class="profile-email" id="user-display-email">-</span>
                            </div>
                        </div>

                        <div class="profile-details-table">
                            <div class="detail-row">
                                <span class="label">User ID:</span>
                                <span class="val code-font" id="user-detail-id">-</span>
                            </div>
                            <div class="detail-row">
                                <span class="label">Assigned Role:</span>
                                <span class="val" id="user-detail-role">-</span>
                            </div>
                            <div class="detail-row">
                                <span class="label">Account Status:</span>
                                <span class="val" id="user-detail-status">-</span>
                            </div>
                            <div class="detail-row">
                                <span class="label">Email Verified:</span>
                                <span class="val" id="user-detail-verified">-</span>
                            </div>
                            <div class="detail-row">
                                <span class="label">Security Version:</span>
                                <span class="val bold" id="user-detail-sec-ver">-</span>
                            </div>
                            <div class="detail-row">
                                <span class="label">Created At:</span>
                                <span class="val" id="user-detail-created">-</span>
                            </div>
                            <div class="detail-row">
                                <span class="label">Last Updated:</span>
                                <span class="val" id="user-detail-updated">-</span>
                            </div>
                        </div>
                    </div>

                    <!-- Actions & Mutation Box -->
                    <div class="profile-actions-box">
                        <div class="card-section">
                            <h4>Update User Profile (PATCH)</h4>
                            <form id="form-user-update">
                                <div class="form-group">
                                    <label>Full Name</label>
                                    <input type="text" id="edit-user-fullname" class="form-input" placeholder="Enter updated name" required>
                                </div>
                                <button type="submit" class="btn btn-primary w-100" id="btn-save-profile">
                                    Save Changes (PATCH /api/v1/users/{id})
                                </button>
                            </form>
                        </div>

                        <div class="card-section mt-3">
                            <h4>Security & Governance Controls</h4>
                            <div class="security-btn-stack">
                                <button class="btn btn-outline btn-warning w-100" id="btn-test-rbac-forbidden" title="Simulates a normal user attempting to access Admin endpoints (Casbin 403 check)">
                                    🛡️ Test Casbin RBAC Guard (Attempt Admin Action)
                                </button>
                                <button class="btn btn-outline btn-danger w-100 mt-2" id="btn-deactivate-user" title="Sets is_active=false on this account">
                                    ⚠️ Soft-Deactivate My Account
                                </button>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Paginated Directory Table -->
                <div class="card-section mt-4">
                    <div class="section-header-row">
                        <div>
                            <h3>Tenant User Directory</h3>
                            <p class="section-desc">Paginated list of users across tenant (Requires READ permissions)</p>
                        </div>
                        <div class="pagination-controls">
                            <button class="btn btn-sm btn-outline" id="btn-dir-prev" disabled>&larr; Prev</button>
                            <span class="page-indicator" id="dir-page-indicator">Page 1</span>
                            <button class="btn btn-sm btn-outline" id="btn-dir-next">Next &rarr;</button>
                        </div>
                    </div>

                    <div class="table-responsive">
                        <table class="data-table" id="table-user-directory">
                            <thead>
                                <tr>
                                    <th>ID</th>
                                    <th>Email</th>
                                    <th>Full Name</th>
                                    <th>Role</th>
                                    <th>Status</th>
                                    <th>Verified</th>
                                    <th>Created</th>
                                </tr>
                            </thead>
                            <tbody id="tbody-user-directory">
                                <tr><td colspan="7" class="text-center text-muted">Loading directory...</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;
    }

    bindEvents() {
        const refreshBtn = document.getElementById('btn-user-refresh');
        if (refreshBtn) refreshBtn.addEventListener('click', () => this.loadProfile(true));

        const updateForm = document.getElementById('form-user-update');
        if (updateForm) {
            updateForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleUpdateProfile();
            });
        }

        const rbacBtn = document.getElementById('btn-test-rbac-forbidden');
        if (rbacBtn) {
            rbacBtn.addEventListener('click', () => this.handleTestRbac());
        }

        const deactBtn = document.getElementById('btn-deactivate-user');
        if (deactBtn) {
            deactBtn.addEventListener('click', () => this.handleDeactivate());
        }

        const prevBtn = document.getElementById('btn-dir-prev');
        const nextBtn = document.getElementById('btn-dir-next');
        if (prevBtn) {
            prevBtn.addEventListener('click', () => {
                if (this.directoryPage > 1) {
                    this.directoryPage--;
                    this.loadDirectory();
                }
            });
        }
        if (nextBtn) {
            nextBtn.addEventListener('click', () => {
                this.directoryPage++;
                this.loadDirectory();
            });
        }

        this.loadProfile(false);
        this.loadDirectory();
    }

    cleanup() {}

    async loadProfile(manual = false) {
        try {
            const res = await getMe();
            if (res.ok && res.data) {
                const user = res.data;
                this.currentUser = user;

                const nameEl = document.getElementById('user-display-name');
                const emailEl = document.getElementById('user-display-email');
                const idEl = document.getElementById('user-detail-id');
                const roleEl = document.getElementById('user-detail-role');
                const statusEl = document.getElementById('user-detail-status');
                const verEl = document.getElementById('user-detail-verified');
                const secEl = document.getElementById('user-detail-sec-ver');
                const createdEl = document.getElementById('user-detail-created');
                const updatedEl = document.getElementById('user-detail-updated');
                const editInput = document.getElementById('edit-user-fullname');

                if (nameEl) nameEl.textContent = user.name || 'Unnamed User';
                if (emailEl) emailEl.textContent = user.email;
                if (idEl) idEl.textContent = user.id;
                if (roleEl) roleEl.innerHTML = renderBadge(user.role === 'admin' ? 'danger' : 'info', user.role || 'user');
                if (statusEl) statusEl.innerHTML = renderBadge(user.is_active ? 'success' : 'danger', user.is_active ? 'Active' : 'Inactive');
                if (verEl) verEl.innerHTML = renderBadge(user.is_verified ? 'success' : 'warning', user.is_verified ? 'Verified' : 'Unverified');
                if (secEl) secEl.textContent = user.security_version ?? 1;
                if (createdEl) createdEl.textContent = formatDate(user.created_at);
                if (updatedEl) updatedEl.textContent = formatDate(user.updated_at);
                if (editInput) editInput.value = user.name || '';

                if (manual) showToast('Profile refreshed', 'success', 1500);
            } else {
                showToast(`Failed to load profile: ${res.data?.message || res.status}`, 'danger', 3000);
            }
        } catch (err) {
            showToast(`Profile load error: ${err.message}`, 'danger', 3000);
        }
    }

    async handleUpdateProfile() {
        if (!this.currentUser) return;
        const fullNameInput = document.getElementById('edit-user-fullname');
        const newName = fullNameInput?.value.trim();

        if (!newName) {
            showToast('Full name cannot be empty', 'warning', 2000);
            return;
        }

        try {
            showToast('Updating profile...', 'info', 1500);
            const res = await updateUser(this.currentUser.id, { name: newName });
            if (res.ok) {
                showToast('Profile updated successfully!', 'success', 2500);
                this.loadProfile(false);
                this.loadDirectory();
            } else {
                showToast(`Update rejected: ${res.data?.message || res.status}`, 'danger', 3500);
            }
        } catch (err) {
            showToast(`Update error: ${err.message}`, 'danger', 3500);
        }
    }

    async handleTestRbac() {
        showToast('Testing Casbin RBAC Authorization...', 'info', 2000);
        try {
            // Attempt an operation that tests permission limits
            const res = await listUsers(1, 10);
            if (res.status === 403) {
                showToast('🛡️ Casbin RBAC Verified: 403 Forbidden! Non-admin is correctly denied.', 'warning', 4500);
            } else if (res.ok) {
                showToast('Action allowed (Your current token has permission for this resource).', 'success', 3000);
            } else {
                showToast(`Server returned status: ${res.status}`, 'info', 2500);
            }
        } catch (err) {
            showToast(`RBAC Test result: ${err.message}`, 'info', 3000);
        }
    }

    async handleDeactivate() {
        if (!this.currentUser) return;
        if (!confirm(`Are you sure you want to deactivate account (${this.currentUser.email})? You will be logged out immediately.`)) {
            return;
        }

        try {
            showToast('Deactivating account...', 'warning', 2000);
            const res = await updateUser(this.currentUser.id, { is_active: false });
            if (res.ok) {
                showToast('Account deactivated. Clearing sessions...', 'danger', 3500);
                sessionStore.clearSession();
                setTimeout(() => window.location.reload(), 1500);
            } else {
                showToast(`Deactivation rejected: ${res.data?.message || res.status}`, 'danger', 3500);
            }
        } catch (err) {
            showToast(`Deactivation error: ${err.message}`, 'danger', 3500);
        }
    }

    async loadDirectory() {
        const tbody = document.getElementById('tbody-user-directory');
        const indicator = document.getElementById('dir-page-indicator');
        const prevBtn = document.getElementById('btn-dir-prev');
        const nextBtn = document.getElementById('btn-dir-next');

        if (!tbody) return;

        try {
            const res = await listUsers(this.directoryPage, this.directoryPageSize);
            if (res.ok && res.data) {
                const items = Array.isArray(res.data) ? res.data : (res.data.items || []);
                const total = res.data.total ?? items.length;

                if (items.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">No users found.</td></tr>';
                    return;
                }

                tbody.innerHTML = items.map(u => `
                    <tr>
                        <td class="code-font" title="${escapeHtml(String(u.id))}">${escapeHtml(String(u.id))}</td>
                        <td class="bold">${escapeHtml(u.email)}</td>
                        <td>${escapeHtml(u.name || '-')}</td>
                        <td>${renderBadge(u.role === 'admin' ? 'danger' : 'info', u.role || 'user')}</td>
                        <td>${renderBadge(u.is_active ? 'success' : 'danger', u.is_active ? 'Active' : 'Inactive')}</td>
                        <td>${renderBadge(u.is_verified ? 'success' : 'warning', u.is_verified ? 'Yes' : 'No')}</td>
                        <td>${formatDate(u.created_at)}</td>
                    </tr>
                `).join('');

                if (indicator) indicator.textContent = `Page ${this.directoryPage}`;
                if (prevBtn) prevBtn.disabled = this.directoryPage <= 1;
                if (nextBtn) nextBtn.disabled = items.length < this.directoryPageSize;
            } else {
                tbody.innerHTML = `<tr><td colspan="7" class="text-center text-danger">Access Denied or Error (Status ${res.status})</td></tr>`;
            }
        } catch (err) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-center text-danger">Error: ${escapeHtml(err.message)}</td></tr>`;
        }
    }
}
