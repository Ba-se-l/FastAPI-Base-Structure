/**
 * Security Lab & Guardrail Stress Workbench
 * 1. 5 Automated One-Click Stress Tests
 * 2. Interactive CLI Command Generator
 */
import { httpClient } from '../../core/http-client.js';
import { showToast, copyToClipboard, escapeHtml, syntaxHighlightJson } from '../../shared/ui-helpers.js';
import { sessionStore } from '../../core/session-store.js';

export class SecurityLabView {
    constructor() {}

    render() {
        return `
            <div class="module-card">
                <div class="card-header">
                    <div class="header-title">
                        <h2>Security Stress Lab & Guardrails</h2>
                        <span class="subtitle">Live verification of enterprise defensive constraints, data sanitization, and CLI toolchain</span>
                    </div>
                </div>

                <!-- 5 Guardrail Tests Grid -->
                <div class="card-section">
                    <h3>Enterprise Guardrail Verification Suite</h3>
                    <p class="section-desc">Run atomic regression tests directly against live endpoints and observe envelope enforcement in the Network Inspector.</p>

                    <div class="tests-grid">
                        <!-- Test 1: Secret Redaction in 422 -->
                        <div class="test-card" id="test-card-1">
                            <div class="test-header">
                                <span class="test-num">01</span>
                                <h4>Secret Redaction in 422 Validation</h4>
                            </div>
                            <p class="test-desc">Submits a payload with an invalid email and a sensitive password to verify that Pydantic error details mask or strip raw password data.</p>
                            <div class="test-action">
                                <button class="btn btn-sm btn-primary btn-run-test" data-test="1">Run Test 01</button>
                                <span class="test-result-badge" id="test-1-badge">Not Run</span>
                            </div>
                            <div class="test-details" id="test-1-details"></div>
                        </div>

                        <!-- Test 2: Explicit Null Rejection -->
                        <div class="test-card" id="test-card-2">
                            <div class="test-header">
                                <span class="test-num">02</span>
                                <h4>Explicit Null Rejection in PATCH</h4>
                            </div>
                            <p class="test-desc">Submits <code>{"name": null}</code> to <code>PATCH /api/v1/users/{id}</code> to verify that explicit nulls are rejected according to schema strictness.</p>
                            <div class="test-action">
                                <button class="btn btn-sm btn-primary btn-run-test" data-test="2">Run Test 02</button>
                                <span class="test-result-badge" id="test-2-badge">Not Run</span>
                            </div>
                            <div class="test-details" id="test-2-details"></div>
                        </div>

                        <!-- Test 3: Non-String Email Type Guard -->
                        <div class="test-card" id="test-card-3">
                            <div class="test-header">
                                <span class="test-num">03</span>
                                <h4>Non-String Type Coercion Guard</h4>
                            </div>
                            <p class="test-desc">Sends non-string numeric or object value <code>{"email": 99999}</code> to test strict validation without silent coercion.</p>
                            <div class="test-action">
                                <button class="btn btn-sm btn-primary btn-run-test" data-test="3">Run Test 03</button>
                                <span class="test-result-badge" id="test-3-badge">Not Run</span>
                            </div>
                            <div class="test-details" id="test-3-details"></div>
                        </div>

                        <!-- Test 4: Argon2 Password Boundary -->
                        <div class="test-card" id="test-card-4">
                            <div class="test-header">
                                <span class="test-num">04</span>
                                <h4>Argon2id Boundary & Length Limit</h4>
                            </div>
                            <p class="test-desc">Submits extreme password length (>128 chars) to ensure DoS protection and memory bounds during hashing.</p>
                            <div class="test-action">
                                <button class="btn btn-sm btn-primary btn-run-test" data-test="4">Run Test 04</button>
                                <span class="test-result-badge" id="test-4-badge">Not Run</span>
                            </div>
                            <div class="test-details" id="test-4-details"></div>
                        </div>

                        <!-- Test 5: Correlation ID Sanitization -->
                        <div class="test-card" id="test-card-5">
                            <div class="test-header">
                                <span class="test-num">05</span>
                                <h4>X-Request-ID Sanitization & Safe Injection</h4>
                            </div>
                            <p class="test-desc">Injects malicious header <code>X-Request-ID: &lt;script&gt;alert(1)&lt;/script&gt;</code> to verify middleware sanitization.</p>
                            <div class="test-action">
                                <button class="btn btn-sm btn-primary btn-run-test" data-test="5">Run Test 05</button>
                                <span class="test-result-badge" id="test-5-badge">Not Run</span>
                            </div>
                            <div class="test-details" id="test-5-details"></div>
                        </div>
                    </div>
                </div>

                <!-- CLI Generator Section -->
                <div class="card-section mt-4">
                    <h3>Operational CLI Command Builder (manage.py)</h3>
                    <p class="section-desc">Generate verified CLI commands for database migrations, administrative bootstrapping, and seeding.</p>

                    <div class="cli-builder-grid">
                        <div class="cli-controls">
                            <div class="form-group">
                                <label>Command Category:</label>
                                <select id="cli-category" class="form-select">
                                    <option value="create-superuser">Create Superuser</option>
                                    <option value="seed-db">Seed Initial Database</option>
                                    <option value="alembic-upgrade">Alembic Upgrade Head</option>
                                    <option value="alembic-check">Alembic Drift Check</option>
                                    <option value="check-health">CLI Health Diagnostics</option>
                                </select>
                            </div>
                            <div class="form-group" id="cli-extra-opts">
                                <label>Email (for superuser):</label>
                                <input type="text" id="cli-opt-email" class="form-input" value="admin@example.com">
                            </div>
                        </div>

                        <div class="cli-output-box">
                            <label>Generated Shell Command:</label>
                            <div class="cli-code-row">
                                <pre class="syntax-code-block" id="cli-command-preview">python manage.py create-superuser --email admin@example.com</pre>
                                <button class="btn btn-sm btn-secondary" id="btn-copy-cli">Copy Command</button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    bindEvents() {
        document.querySelectorAll('.btn-run-test').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const testId = btn.dataset.test;
                this.runTest(testId);
            });
        });

        // CLI Generator
        const catSelect = document.getElementById('cli-category');
        const emailInput = document.getElementById('cli-opt-email');
        const preview = document.getElementById('cli-command-preview');
        const copyBtn = document.getElementById('btn-copy-cli');

        const updateCli = () => {
            const cat = catSelect?.value;
            const email = emailInput?.value || 'admin@example.com';
            let cmd = '';

            switch (cat) {
                case 'create-superuser':
                    cmd = `python manage.py create-superuser --email ${email}`;
                    break;
                case 'seed-db':
                    cmd = `python manage.py seed`;
                    break;
                case 'alembic-upgrade':
                    cmd = `alembic upgrade head`;
                    break;
                case 'alembic-check':
                    cmd = `alembic check`;
                    break;
                case 'check-health':
                    cmd = `python manage.py health-check`;
                    break;
                default:
                    cmd = `python manage.py --help`;
            }

            if (preview) preview.textContent = cmd;
        };

        if (catSelect) catSelect.addEventListener('change', updateCli);
        if (emailInput) emailInput.addEventListener('input', updateCli);
        if (copyBtn) {
            copyBtn.addEventListener('click', () => {
                const cmd = preview?.textContent || '';
                copyToClipboard(cmd).then(() => {
                    showToast('CLI command copied to clipboard!', 'success', 2000);
                });
            });
        }
    }

    cleanup() {}

    async runTest(testId) {
        const badge = document.getElementById(`test-${testId}-badge`);
        const details = document.getElementById(`test-${testId}-details`);
        if (badge) {
            badge.textContent = 'Running...';
            badge.className = 'test-result-badge badge-running';
        }

        try {
            switch (testId) {
                case '1':
                    await this.testSecretRedaction(badge, details);
                    break;
                case '2':
                    await this.testExplicitNull(badge, details);
                    break;
                case '3':
                    await this.testNonStringEmail(badge, details);
                    break;
                case '4':
                    await this.testPasswordBoundary(badge, details);
                    break;
                case '5':
                    await this.testCorrelationSanitization(badge, details);
                    break;
            }
        } catch (err) {
            if (badge) {
                badge.textContent = 'Error';
                badge.className = 'test-result-badge badge-failed';
            }
            if (details) {
                details.innerHTML = `<span class="text-danger">${escapeHtml(err.message)}</span>`;
            }
        }
    }

    async testSecretRedaction(badge, details) {
        // Send register payload with invalid email and raw password
        const sensitivePass = 'UltraSecretP@ssword999!';
        const res = await httpClient.post('/api/v1/auth/register', {
            email: 'not-an-email',
            password: sensitivePass,
            name: 'Test Redaction'
        });

        const rawJson = JSON.stringify(res.data);
        const leaked = rawJson.includes(sensitivePass);

        if (res.status === 422 && !leaked) {
            badge.textContent = 'Passed (Safe)';
            badge.className = 'test-result-badge badge-passed';
            details.innerHTML = `<span class="text-success">✓ 422 Unprocessable Entity returned without password reflection.</span>`;
        } else if (leaked) {
            badge.textContent = 'Failed (Leaked)';
            badge.className = 'test-result-badge badge-failed';
            details.innerHTML = `<span class="text-danger">⚠️ Secret password leaked in validation response!</span>`;
        } else {
            badge.textContent = `Status ${res.status}`;
            badge.className = 'test-result-badge badge-warning';
            details.innerHTML = `<span>Response received with status ${res.status}.</span>`;
        }
    }

    async testExplicitNull(badge, details) {
        // Send explicit null to PATCH /users/{id}
        const activeSlot = sessionStore.getActiveSlot();
        const session = sessionStore.getSession(activeSlot);
        const userId = session?.accessClaims?.sub || '00000000-0000-0000-0000-000000000000';

        const res = await httpClient.patch(`/api/v1/users/${userId}`, {
            name: null
        });

        if (res.status === 422) {
            badge.textContent = 'Passed (Rejected)';
            badge.className = 'test-result-badge badge-passed';
            details.innerHTML = `<span class="text-success">✓ Explicit null correctly rejected by Pydantic schema (422).</span>`;
        } else {
            badge.textContent = `Status ${res.status}`;
            badge.className = 'test-result-badge badge-info';
            details.innerHTML = `<span>Server responded with status ${res.status}.</span>`;
        }
    }

    async testNonStringEmail(badge, details) {
        const res = await httpClient.post('/api/v1/auth/login', {
            email: 99887766,
            password: 'SomePassword123'
        });

        if (res.status === 422) {
            badge.textContent = 'Passed (Type Enforced)';
            badge.className = 'test-result-badge badge-passed';
            details.innerHTML = `<span class="text-success">✓ Non-string type strictly rejected with 422 Unprocessable Entity.</span>`;
        } else {
            badge.textContent = `Status ${res.status}`;
            badge.className = 'test-result-badge badge-warning';
            details.innerHTML = `<span>Status ${res.status} returned.</span>`;
        }
    }

    async testPasswordBoundary(badge, details) {
        const giantPassword = 'A'.repeat(256);
        const res = await httpClient.post('/api/v1/auth/register', {
            email: `boundary_${Date.now()}@example.com`,
            password: giantPassword,
            name: 'Boundary Test'
        });

        if (res.status === 422) {
            badge.textContent = 'Passed (Bounded)';
            badge.className = 'test-result-badge badge-passed';
            details.innerHTML = `<span class="text-success">✓ Passwords exceeding max length are safely rejected before hashing (422).</span>`;
        } else {
            badge.textContent = `Status ${res.status}`;
            badge.className = 'test-result-badge badge-info';
            details.innerHTML = `<span>Status ${res.status} returned.</span>`;
        }
    }

    async testCorrelationSanitization(badge, details) {
        const maliciousId = "<script>alert('xss')</script>";
        const res = await httpClient.get('/health', {
            headers: {
                'X-Request-ID': maliciousId
            }
        });

        const returnedId = res.headers['x-request-id'] || '';
        const containsScript = returnedId.includes('<script>');

        if (!containsScript) {
            badge.textContent = 'Passed (Sanitized)';
            badge.className = 'test-result-badge badge-passed';
            details.innerHTML = `<span class="text-success">✓ X-Request-ID header sanitized safely. Echoed ID: <code>${escapeHtml(returnedId.substring(0, 20))}...</code></span>`;
        } else {
            badge.textContent = 'Failed (Unsanitized)';
            badge.className = 'test-result-badge badge-failed';
            details.innerHTML = `<span class="text-danger">⚠️ Script injection persisted in response header!</span>`;
        }
    }
}
