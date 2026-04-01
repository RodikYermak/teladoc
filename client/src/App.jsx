import React, { useEffect, useState } from 'react';
import {
    BrowserRouter as Router,
    Routes,
    Route,
    Link,
    Navigate,
    useNavigate,
    useLocation,
} from 'react-router-dom';
import axios from 'axios';
import './index.css';

const api = axios.create({
    baseURL: 'http://localhost:8000',
});

const AUTH_STORAGE_KEY = 'teladoc_auth';

function getStoredAuth() {
    try {
        const raw = localStorage.getItem(AUTH_STORAGE_KEY);
        return raw ? JSON.parse(raw) : null;
    } catch {
        return null;
    }
}

function setStoredAuth(auth) {
    localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(auth));
}

function clearStoredAuth() {
    localStorage.removeItem(AUTH_STORAGE_KEY);
}

function buildAuthHeaders(auth) {
    if (!auth?.token) return {};
    return {
        Authorization: `Bearer ${auth.token}`,
    };
}

function formatDate(value) {
    if (!value) return 'No activity yet';
    return new Date(value).toLocaleString();
}

function formatShortDate(value) {
    return new Date(value).toLocaleDateString('en-US', {
        month: 'long',
        day: 'numeric',
        year: 'numeric',
    });
}

function formatTime(value) {
    return new Date(value).toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit',
        second: '2-digit',
    });
}

function generateIdempotencyKey() {
    return crypto.randomUUID();
}

function ProtectedRoute({ isAuthenticated, children }) {
    if (!isAuthenticated) {
        return <Navigate to="/login" replace />;
    }
    return children;
}

function Header({ auth, onLogout }) {
    const location = useLocation();
    const isAdmin = auth?.user?.role === 'admin';

    return (
        <header className="app-header-wrap">
            <div className="header-inner">
                <div className="logo">
                    Teladoc <span>HEALTH</span>
                </div>

                <nav className="nav">
                    <Link
                        to="/"
                        className={location.pathname === '/' ? 'nav-link active' : 'nav-link'}>
                        Tenant Dashboard
                    </Link>

                    {isAdmin ? (
                        <Link
                            to="/admin"
                            className={
                                location.pathname === '/admin' ? 'nav-link active' : 'nav-link'
                            }>
                            Admin View
                        </Link>
                    ) : (
                        <span className="nav-link nav-link-disabled" title="Admin only">
                            Admin View
                        </span>
                    )}

                    <div className="profile">{auth?.user?.display_name?.[0] || 'A'}</div>

                    <button className="logout-btn" onClick={onLogout}>
                        Log out
                    </button>
                </nav>
            </div>
            <div className="header-divider" />
        </header>
    );
}

function LoginPage({ onLogin }) {
    const [identifier, setIdentifier] = useState('');
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [submitting, setSubmitting] = useState(false);
    const [errorMessage, setErrorMessage] = useState('');
    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setErrorMessage('');

        if (!identifier.trim() || !password.trim()) {
            setErrorMessage('Please enter your username/email and password.');
            return;
        }

        try {
            setSubmitting(true);

            const response = await api.post('/v1/auth/login', {
                identifier: identifier.trim(),
                password,
            });

            const authPayload = {
                token: response.data.access_token,
                expires_at: response.data.expires_at,
                user: response.data.user,
            };

            onLogin(authPayload);
            navigate('/', { replace: true });
        } catch (error) {
            setErrorMessage(error.response?.data?.message || 'Invalid username/email or password.');
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="login-page">
            <div className="login-brand-row">
                <div className="logo login-logo">
                    Teladoc <span>HEALTH</span>
                </div>
            </div>

            <div className="login-divider" />

            <div className="login-card">
                <h1 className="login-title">Sign in to your account</h1>

                <form onSubmit={handleSubmit} className="login-form">
                    <div className="login-field">
                        <label>Username or email</label>
                        <input
                            type="text"
                            value={identifier}
                            onChange={(e) => setIdentifier(e.target.value)}
                        />
                    </div>

                    <div className="login-field">
                        <label>Password</label>
                        <div className="password-input-wrap">
                            <input
                                type={showPassword ? 'text' : 'password'}
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                            />
                            <button
                                type="button"
                                className="password-toggle"
                                onClick={() => setShowPassword((prev) => !prev)}
                                aria-label="Toggle password visibility">
                                {showPassword ? '🙈' : '👁️'}
                            </button>
                        </div>
                    </div>

                    <div className="login-help-links">
                        Forgot <a href="#!">username</a> or <a href="#!">password?</a>
                    </div>

                    {errorMessage && <p className="login-error">{errorMessage}</p>}

                    <button type="submit" className="login-submit-btn" disabled={submitting}>
                        {submitting ? 'Signing In...' : 'Sign In'}
                    </button>

                    <div className="login-secondary-link">
                        <a href="#!">Create a new account</a>
                    </div>
                </form>

                <div className="login-demo-box">
                    <strong>Demo users</strong>
                    <div>admin / password123</div>
                    <div>tenant1 / password123</div>
                    <div>tenant2 / password123</div>
                    <div>tenant3 / password123</div>
                </div>
            </div>
        </div>
    );
}

function TokenCard({ used, total }) {
    const percentRaw = total > 0 ? (used / total) * 100 : 0;
    const percent = total > 0 ? Math.min(percentRaw, 100) : 0;

    const isOver = total > 0 && used > total;
    const isWarning = total > 0 && used / total > 0.9 && !isOver;

    let statusText = 'Month-to-date usage';
    let statusClassName = 'usage-caption';

    if (isOver) {
        statusText = 'OVER';
        statusClassName = 'over-pill';
    } else if (isWarning) {
        statusText = '⚠ WARNING';
        statusClassName = 'warning-pill';
    }

    return (
        <div className={`tenant-card usage-card ${isOver ? 'usage-card-over' : ''}`}>
            <h3>Token Utilizations</h3>

            <div className="usage-big-number">{used.toLocaleString()}</div>

            <div className="usage-progress-row">
                <div className="progress-container">
                    <div
                        className={`progress ${isOver ? 'progress-over' : ''}`}
                        style={{ width: `${percent}%` }}
                    />
                </div>
            </div>

            <div className="usage-footer-row">
                <div className={statusClassName}>{statusText}</div>
                <div className="usage-total-number">{total.toLocaleString()}</div>
            </div>
        </div>
    );
}

function UsageByDayTable({ events }) {
    if (!events.length) {
        return <p>No usage events yet.</p>;
    }

    const grouped = events.reduce((acc, event) => {
        const dayKey = new Date(event.timestamp).toDateString();
        if (!acc[dayKey]) acc[dayKey] = [];
        acc[dayKey].push(event);
        return acc;
    }, {});

    const orderedDays = Object.keys(grouped).sort((a, b) => new Date(b) - new Date(a));

    return (
        <div className="usage-table-wrap">
            {orderedDays.map((dayKey) => {
                const items = grouped[dayKey].sort(
                    (a, b) => new Date(b.timestamp) - new Date(a.timestamp),
                );

                return (
                    <div key={dayKey} className="usage-day-group">
                        <div className="usage-day-title">{formatShortDate(items[0].timestamp)}</div>

                        <table className="usage-day-table">
                            <tbody>
                                {items.map((event) => (
                                    <tr key={event.event_id}>
                                        <td className="usage-time-cell">
                                            {formatTime(event.timestamp)}
                                        </td>
                                        <td className="usage-type-cell">
                                            {event.event_type === 'tokens'
                                                ? 'Tokens processed'
                                                : 'Inference seconds'}
                                        </td>
                                        <td className="usage-amount-cell">
                                            {event.amount.toLocaleString()}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                );
            })}
        </div>
    );
}

function EventForm({ onSubmit, isAdmin, auth }) {
    const tenantScopedId = auth?.user?.tenant_id || '';
    const [tenantId, setTenantId] = useState(tenantScopedId);
    const [eventType, setEventType] = useState('tokens');
    const [amount, setAmount] = useState('');
    const [allowOverage, setAllowOverage] = useState(false);
    const [submitting, setSubmitting] = useState(false);
    const [message, setMessage] = useState('');
    const [errorMessage, setErrorMessage] = useState('');

    useEffect(() => {
        if (!isAdmin && tenantScopedId) {
            setTenantId(tenantScopedId);
        }
    }, [isAdmin, tenantScopedId]);

    const buildFriendlyErrorMessage = (error) => {
        const status = error.response?.status;
        const responseData = error.response?.data;
        const code = responseData?.code;
        const message = responseData?.message;

        if (!error.response) {
            return 'Cannot reach the server. Make sure the backend is running on http://localhost:8000.';
        }

        if (status === 401) {
            return 'Your session has expired or is invalid. Please sign in again.';
        }

        if (status === 403) {
            return message || 'You do not have permission to perform this action.';
        }

        if (status === 409 && code === 'quota_exceeded') {
            const remaining = Number(responseData.remaining_units ?? 0).toLocaleString();
            const requested = Number(responseData.requested_units ?? 0).toLocaleString();
            const used = Number(responseData.month_to_date_usage ?? 0).toLocaleString();
            const quota = Number(responseData.configured_monthly_quota ?? 0).toLocaleString();

            return (
                `Quota exceeded. This event would go over the tenant's monthly limit. ` +
                `Remaining units: ${remaining}. Requested units: ${requested}. ` +
                `Month-to-date usage: ${used} of ${quota}. ` +
                (responseData.allow_overage_available_for_admin
                    ? 'An admin can retry with overage override enabled.'
                    : '')
            );
        }

        if (status === 409 && code === 'idempotency_conflict') {
            return `Conflict: ${message}`;
        }

        if (status === 404 && code === 'tenant_not_found') {
            return 'Tenant not found. Please check the Tenant ID and try again.';
        }

        if (status === 400 && code === 'event_timestamp_in_future') {
            return 'Invalid timestamp. Event timestamp cannot be more than 5 minutes in the future.';
        }

        if (status === 400 && code === 'event_timestamp_too_old') {
            return 'Invalid timestamp. Event timestamp cannot be more than 30 days in the past.';
        }

        if (status === 422 && Array.isArray(responseData?.details)) {
            const messages = responseData.details
                .map((item) => `${item.field}: ${item.message}`)
                .join('; ');
            return `Invalid input. ${messages}`;
        }

        if (typeof message === 'string' && message.trim()) {
            return message;
        }

        return `Failed to create event. Server returned status ${status}.`;
    };

    const handleSubmit = async (e) => {
        e.preventDefault();

        setMessage('');
        setErrorMessage('');

        if (!tenantId.trim()) {
            setErrorMessage('Tenant ID is required.');
            return;
        }

        if (!amount || Number(amount) <= 0) {
            setErrorMessage('Amount must be greater than 0.');
            return;
        }

        if (!isAdmin && tenantScopedId && tenantId.trim() !== tenantScopedId) {
            setErrorMessage('Tenant users can only ingest usage for their own tenant.');
            return;
        }

        setSubmitting(true);

        const payload = {
            tenant_id: tenantId.trim(),
            event_type: eventType,
            amount: Number(amount),
            idempotency_key: generateIdempotencyKey(),
        };

        try {
            const result = await onSubmit(payload, allowOverage);

            if (!result.ok) {
                setErrorMessage(result.message || 'Failed to create event.');
                return;
            }

            if (result.replayed) {
                setMessage(
                    'Duplicate request detected. Existing event was returned, and usage was not counted twice.',
                );
            } else {
                setMessage('Event created successfully.');
            }

            if (isAdmin) {
                setTenantId('');
            }
            setEventType('tokens');
            setAmount('');
            setAllowOverage(false);
        } catch (error) {
            setErrorMessage(buildFriendlyErrorMessage(error));
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <form className="tenant-card dashboard-event-card" onSubmit={handleSubmit}>
            <h3>Event</h3>

            <label className="dashboard-form-label">Event Name</label>
            <select value={eventType} onChange={(e) => setEventType(e.target.value)}>
                <option value="tokens">Tokens processed</option>
                <option value="inference_seconds">Inference seconds</option>
            </select>

            <label className="dashboard-form-label">Tenant ID</label>
            <input
                type="text"
                placeholder="Tenant UUID"
                value={tenantId}
                onChange={(e) => setTenantId(e.target.value)}
                readOnly={!isAdmin}
            />

            <label className="dashboard-form-label">Amount</label>
            <input
                type="number"
                min="1"
                placeholder="1,000"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
            />

            {isAdmin ? (
                <label className="dashboard-checkbox-row">
                    <input
                        type="checkbox"
                        checked={allowOverage}
                        onChange={(e) => setAllowOverage(e.target.checked)}
                    />
                    <span>Allow overage (admin override)</span>
                </label>
            ) : (
                <div className="dashboard-checkbox-row dashboard-checkbox-disabled">
                    <input type="checkbox" checked={false} disabled readOnly />
                    <span>Allow overage (admin only)</span>
                </div>
            )}

            <button type="submit" className="dashboard-submit-btn" disabled={submitting}>
                {submitting ? 'Creating...' : 'Create Event'}
            </button>

            {message && <p className="dashboard-success-text">{message}</p>}
            {errorMessage && <p className="dashboard-error-text">{errorMessage}</p>}
        </form>
    );
}

function Dashboard({ auth, onUnauthorized }) {
    const [events, setEvents] = useState([]);
    const [tenantSummary, setTenantSummary] = useState(null);
    const [loading, setLoading] = useState(true);

    const isAdmin = auth?.user?.role === 'admin';
    const tenantScopedId = auth?.user?.tenant_id || null;

    const fetchDashboardData = async () => {
        try {
            const headers = buildAuthHeaders(auth);

            const [eventsResponse, tenantsResponse] = await Promise.all([
                api.get('/v1/usage/events', { headers }),
                api.get('/v1/tenants', { headers }),
            ]);

            setEvents(eventsResponse.data.events);

            if (isAdmin) {
                const firstTenant = tenantsResponse.data.tenants?.[0] || null;
                setTenantSummary(firstTenant);
            } else {
                const myTenantId = auth?.user?.tenant_id;
                const myTenant =
                    tenantsResponse.data.tenants?.find(
                        (tenant) => tenant.tenant_id === myTenantId,
                    ) || null;
                setTenantSummary(myTenant);
            }
        } catch (error) {
            if (error.response?.status === 401) {
                onUnauthorized();
            }
            console.error('Error fetching dashboard data:', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchDashboardData();
    }, []);

    const handleCreateEvent = async (payload, allowOverage) => {
        try {
            const response = await api.post(
                `/v1/usage/events${allowOverage ? '?allow_overage=true' : ''}`,
                payload,
                {
                    headers: buildAuthHeaders(auth),
                },
            );

            if (!response.data.idempotency_replayed) {
                setEvents((prev) => [response.data, ...prev]);

                if (response.data.event_type === 'tokens') {
                    setTenantSummary((prev) => {
                        if (!prev) return prev;
                        if (prev.tenant_id !== response.data.tenant_id) return prev;

                        return {
                            ...prev,
                            month_to_date_usage:
                                Number(prev.month_to_date_usage || 0) +
                                Number(response.data.amount),
                            last_activity_at: response.data.timestamp,
                        };
                    });
                }
            }

            return {
                ok: true,
                replayed: response.data.idempotency_replayed,
                event: response.data,
            };
        } catch (error) {
            if (error.response?.status === 401) {
                onUnauthorized();
            }

            const status = error.response?.status;
            const responseData = error.response?.data;
            const message = responseData?.message;

            return {
                ok: false,
                message:
                    typeof message === 'string' && message.trim()
                        ? message
                        : `Failed to create event. Status ${status}.`,
            };
        }
    };

    const tokenUsed = tenantSummary?.month_to_date_usage ?? 0;
    const tokenQuota = tenantSummary?.configured_monthly_quota ?? 0;

    const dashboardTitle = isAdmin
        ? 'Admin Dashboard View'
        : `${auth?.user?.display_name || 'Tenant'} Dashboard`;

    const dashboardSubtitle = isAdmin
        ? 'Viewing platform-wide access with tenant management controls.'
        : `Logged in for tenant ${tenantScopedId}`;

    return (
        <div className="tenant-dashboard">
            <div className="dashboard-heading-block">
                <h1 className="dashboard-page-title">{dashboardTitle}</h1>
                <p className="dashboard-page-subtitle">{dashboardSubtitle}</p>
            </div>

            <div className="tenant-dashboard-top">
                <TokenCard used={tokenUsed} total={tokenQuota} />
                <EventForm onSubmit={handleCreateEvent} isAdmin={isAdmin} auth={auth} />
            </div>

            <section className="usage-history-section">
                <h2>Events</h2>
                {loading ? <p>Loading...</p> : <UsageByDayTable events={events} />}
            </section>
        </div>
    );
}

function AdminPage({ auth, onUnauthorized }) {
    const [tenants, setTenants] = useState([]);
    const [auditRecords, setAuditRecords] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    const [isModalOpen, setIsModalOpen] = useState(false);
    const [currentTenant, setCurrentTenant] = useState(null);
    const [newQuota, setNewQuota] = useState('');
    const [reason, setReason] = useState('');
    const [updating, setUpdating] = useState(false);

    const isAdmin = auth?.user?.role === 'admin';

    const fetchTenants = async () => {
        const response = await api.get('/v1/tenants', {
            headers: buildAuthHeaders(auth),
        });
        setTenants(response.data.tenants);
    };

    const fetchAuditLogs = async () => {
        if (!isAdmin) {
            setAuditRecords([]);
            return;
        }

        const response = await api.get('/v1/audit', {
            headers: buildAuthHeaders(auth),
        });
        setAuditRecords(response.data.records);
    };

    const loadAdminData = async () => {
        try {
            setError('');
            await Promise.all([fetchTenants(), fetchAuditLogs()]);
        } catch (err) {
            if (err.response?.status === 401) {
                onUnauthorized();
            }
            console.error('Error loading admin data:', err);
            setError(err.response?.data?.message || 'Failed to load admin data.');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadAdminData();
    }, []);

    const openModal = (tenant) => {
        if (!isAdmin) return;

        setCurrentTenant(tenant);
        setNewQuota(String(tenant.configured_monthly_quota));
        setReason('');
        setIsModalOpen(true);
    };

    const closeModal = () => {
        if (updating) return;
        setIsModalOpen(false);
        setCurrentTenant(null);
        setNewQuota('');
        setReason('');
    };

    const updateTenant = async () => {
        if (!isAdmin) {
            alert('Only admins can update tenant quota.');
            return;
        }

        if (!currentTenant) return;

        const trimmedReason = reason.trim();

        if (!newQuota || Number(newQuota) <= 0) {
            alert('Please enter a valid quota greater than 0.');
            return;
        }

        if (trimmedReason.length < 10) {
            alert('Reason is required and must be at least 10 characters.');
            return;
        }

        try {
            setUpdating(true);

            await api.put(
                `/v1/tenants/${currentTenant.tenant_id}/quota`,
                {
                    new_monthly_quota: Number(newQuota),
                    reason: trimmedReason,
                },
                {
                    headers: buildAuthHeaders(auth),
                },
            );

            await Promise.all([fetchTenants(), fetchAuditLogs()]);
            closeModal();
        } catch (err) {
            if (err.response?.status === 401) {
                onUnauthorized();
            }
            console.error('Error updating tenant quota:', err.response?.data || err);

            if (err.response?.status === 422 && Array.isArray(err.response?.data?.details)) {
                const message = err.response.data.details
                    .map((item) => `${item.field}: ${item.message}`)
                    .join('; ');
                alert(`Invalid request: ${message}`);
                return;
            }

            alert(err.response?.data?.message || 'Failed to update quota.');
        } finally {
            setUpdating(false);
        }
    };

    if (loading) {
        return (
            <div className="admin-page">
                <h2>Admin View</h2>
                <p>Loading admin data...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="admin-page">
                <div className="admin-page-topbar">
                    <h2>Admin View</h2>
                    {isAdmin && (
                        <button className="edit-btn" onClick={loadAdminData}>
                            Refresh
                        </button>
                    )}
                </div>
                <p>{error}</p>
            </div>
        );
    }

    return (
        <div className="admin-page">
            <div className="admin-page-topbar">
                <h2>Admin View</h2>
                {isAdmin && (
                    <button className="edit-btn" onClick={loadAdminData}>
                        Refresh
                    </button>
                )}
            </div>

            {!tenants.length ? (
                <p>No tenants found.</p>
            ) : (
                <table className="tenant-table">
                    <thead>
                        <tr>
                            <th>Tenant ID</th>
                            <th>Monthly Quota</th>
                            <th>Month-to-Date Usage</th>
                            <th>Last Activity</th>
                            <th></th>
                        </tr>
                    </thead>
                    <tbody>
                        {tenants.map((tenant) => (
                            <tr key={tenant.tenant_id}>
                                <td>{tenant.tenant_id}</td>
                                <td>{tenant.configured_monthly_quota.toLocaleString()}</td>
                                <td>{tenant.month_to_date_usage.toLocaleString()}</td>
                                <td>{formatDate(tenant.last_activity_at)}</td>
                                <td>
                                    {isAdmin ? (
                                        <button
                                            className="edit-btn"
                                            onClick={() => openModal(tenant)}>
                                            Edit
                                        </button>
                                    ) : (
                                        <button
                                            className="edit-btn edit-btn-disabled"
                                            disabled
                                            title="Admin only">
                                            Edit
                                        </button>
                                    )}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            )}

            <div className="audit-trail-block">
                <h3>Audit Trail</h3>

                {!isAdmin ? (
                    <p>Audit trail is visible to admins only.</p>
                ) : !auditRecords.length ? (
                    <p>No audit records yet.</p>
                ) : (
                    <table className="tenant-table">
                        <thead>
                            <tr>
                                <th>When</th>
                                <th>Tenant ID</th>
                                <th>Action</th>
                                <th>Old Quota</th>
                                <th>New Quota</th>
                                <th>Changed By</th>
                                <th>Reason</th>
                            </tr>
                        </thead>
                        <tbody>
                            {auditRecords
                                .slice()
                                .reverse()
                                .map((record) => (
                                    <tr key={record.audit_id}>
                                        <td>{formatDate(record.timestamp)}</td>
                                        <td>{record.tenant_id}</td>
                                        <td>{record.action}</td>
                                        <td>{Number(record.old_value).toLocaleString()}</td>
                                        <td>{Number(record.new_value).toLocaleString()}</td>
                                        <td>{record.actor}</td>
                                        <td>{record.reason}</td>
                                    </tr>
                                ))}
                        </tbody>
                    </table>
                )}
            </div>

            {isModalOpen && currentTenant && (
                <div className="overlay">
                    <div className="modal">
                        <h3>Edit Quota</h3>

                        <div className="field">
                            <label>Tenant</label>
                            <input type="text" value={currentTenant.tenant_id} readOnly />
                        </div>

                        <div className="field">
                            <label>Current Quota</label>
                            <input
                                type="text"
                                value={currentTenant.configured_monthly_quota.toLocaleString()}
                                readOnly
                            />
                        </div>

                        <div className="field">
                            <label>New Quota</label>
                            <input
                                type="number"
                                min="1"
                                value={newQuota}
                                onChange={(e) => setNewQuota(e.target.value)}
                            />
                        </div>

                        <div className="field">
                            <label>Reason</label>
                            <input
                                type="text"
                                placeholder="Minimum 10 characters"
                                maxLength={200}
                                value={reason}
                                onChange={(e) => setReason(e.target.value)}
                            />
                            <small style={{ color: '#6b7280' }}>
                                Required for audit trail. Minimum 10 characters.
                            </small>
                        </div>

                        <div className="actions">
                            <button
                                className="btn-discard"
                                onClick={closeModal}
                                disabled={updating}>
                                Discard
                            </button>
                            <button
                                className="btn-update"
                                onClick={updateTenant}
                                disabled={updating}>
                                {updating ? 'Updating...' : 'Update'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

function AppShell({ auth, onLogout, onUnauthorized }) {
    return (
        <>
            <Header auth={auth} onLogout={onLogout} />
            <main className="page">
                <Routes>
                    <Route
                        path="/"
                        element={
                            <ProtectedRoute isAuthenticated={!!auth}>
                                <Dashboard auth={auth} onUnauthorized={onUnauthorized} />
                            </ProtectedRoute>
                        }
                    />
                    <Route
                        path="/admin"
                        element={
                            <ProtectedRoute isAuthenticated={!!auth}>
                                <AdminPage auth={auth} onUnauthorized={onUnauthorized} />
                            </ProtectedRoute>
                        }
                    />
                </Routes>
            </main>
        </>
    );
}

function App() {
    const [auth, setAuth] = useState(() => getStoredAuth());

    const handleLogin = (authPayload) => {
        setStoredAuth(authPayload);
        setAuth(authPayload);
    };

    const handleLogout = () => {
        clearStoredAuth();
        setAuth(null);
    };

    const handleUnauthorized = () => {
        clearStoredAuth();
        setAuth(null);
    };

    return (
        <Router>
            <Routes>
                <Route
                    path="/login"
                    element={
                        auth ? <Navigate to="/" replace /> : <LoginPage onLogin={handleLogin} />
                    }
                />
                <Route
                    path="/*"
                    element={
                        <AppShell
                            auth={auth}
                            onLogout={handleLogout}
                            onUnauthorized={handleUnauthorized}
                        />
                    }
                />
            </Routes>
        </Router>
    );
}

export default App;
