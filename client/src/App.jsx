import React, { useEffect, useMemo, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import axios from 'axios';
import './index.css';

const api = axios.create({
    baseURL: 'http://localhost:8000',
});

function formatDate(value) {
    if (!value) return 'No activity yet';
    return new Date(value).toLocaleString();
}

function formatTimestamp(timestamp) {
    return new Date(timestamp).toLocaleString();
}

function generateIdempotencyKey() {
    return crypto.randomUUID();
}

function Header() {
    return (
        <header className="header">
            <div className="logo">
                Teladoc <span>HEALTH</span>
            </div>

            <nav className="nav">
                <Link to="/">Tenant Dashboard</Link>
                <Link to="/admin">Admin View</Link>
                <div className="profile">A</div>
            </nav>
        </header>
    );
}

function TokenCard({ used, total }) {
    const percent = total > 0 ? Math.min((used / total) * 100, 100) : 0;
    const isWarning = total > 0 && used / total >= 0.8;

    return (
        <div className="card">
            <h3>Token Utilization</h3>
            <div className="metric">{used.toLocaleString()}</div>

            <div className="progress-container">
                <div className="progress" style={{ width: `${percent}%` }} />
            </div>

            <div className="subtext">Quota: {total.toLocaleString()}</div>

            {isWarning && <div className="warning">⚠️ Warning: usage above 80%</div>}
        </div>
    );
}

function EventList({ events }) {
    if (!events.length) {
        return <p>No events yet.</p>;
    }

    return (
        <div className="events">
            {events.map((event) => (
                <div className="event-item" key={event.event_id}>
                    <div>
                        <strong>{event.event_type}</strong> — {event.amount.toLocaleString()}
                    </div>
                    <div className="event-meta">Tenant: {event.tenant_id}</div>
                    <div className="event-meta">{formatTimestamp(event.timestamp)}</div>
                </div>
            ))}
        </div>
    );
}

function EventForm({ onSubmit, onEventCreated }) {
    const [tenantId, setTenantId] = useState('');
    const [eventType, setEventType] = useState('tokens');
    const [amount, setAmount] = useState('');
    const [allowOverage, setAllowOverage] = useState(false);
    const [submitting, setSubmitting] = useState(false);
    const [message, setMessage] = useState('');
    const [errorMessage, setErrorMessage] = useState('');

    const buildFriendlyErrorMessage = (error) => {
        const status = error.response?.status;
        const detail = error.response?.data?.detail;

        if (!error.response) {
            return 'Cannot reach the server. Make sure the backend is running on http://localhost:8000.';
        }

        if (status === 409 && detail?.code === 'quota_exceeded') {
            const remaining = Number(detail.remaining_units ?? 0).toLocaleString();
            const requested = Number(detail.requested_units ?? 0).toLocaleString();
            const used = Number(detail.month_to_date_usage ?? 0).toLocaleString();
            const quota = Number(detail.configured_monthly_quota ?? 0).toLocaleString();

            return (
                `Quota exceeded. This event would go over the tenant's monthly limit. ` +
                `Remaining units: ${remaining}. Requested units: ${requested}. ` +
                `Month-to-date usage: ${used} of ${quota}. ` +
                (detail.allow_overage_available_for_admin
                    ? 'An admin can retry with overage override enabled.'
                    : '')
            );
        }

        if (status === 409 && typeof detail === 'string') {
            return `Conflict: ${detail}`;
        }

        if (status === 404) {
            return 'Tenant not found. Please check the Tenant ID and try again.';
        }

        if (status === 403) {
            return 'You are not allowed to perform this action. Admin access is required for overage override.';
        }

        if (status === 422 && Array.isArray(error.response?.data?.detail)) {
            const messages = error.response.data.detail
                .map((item) => {
                    const field = item.loc?.[item.loc.length - 1];
                    return field ? `${field}: ${item.msg}` : item.msg;
                })
                .join('; ');

            return `Invalid input. ${messages}`;
        }

        if (typeof detail === 'string' && detail.trim()) {
            return detail;
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

        setSubmitting(true);

        const payload = {
            tenant_id: tenantId.trim(),
            event_type: eventType,
            amount: Number(amount),
            idempotency_key: generateIdempotencyKey(),
        };

        try {
            let result;

            if (allowOverage) {
                const response = await api.post('/v1/usage/events?allow_overage=true', payload, {
                    headers: {
                        'x-admin': 'true',
                    },
                });

                result = {
                    ok: true,
                    replayed: response.data.idempotency_replayed,
                    event: response.data,
                };
            } else {
                result = await onSubmit(payload);
            }

            if (!result.ok) {
                if (result.errorType === 'quota_exceeded') {
                    const remaining = Number(result.remainingUnits ?? 0).toLocaleString();
                    const requested = Number(result.requestedUnits ?? 0).toLocaleString();
                    const used = Number(result.monthToDateUsage ?? 0).toLocaleString();
                    const quota = Number(result.configuredQuota ?? 0).toLocaleString();

                    setErrorMessage(
                        `Quota exceeded. This event would go over the tenant's monthly limit. ` +
                            `Remaining units: ${remaining}. Requested units: ${requested}. ` +
                            `Month-to-date usage: ${used} of ${quota}. ` +
                            (result.allowOverageAvailableForAdmin
                                ? 'An admin can retry with overage override enabled.'
                                : '')
                    );
                } else if (result.errorType === 'conflict') {
                    setErrorMessage(
                        result.message ||
                            'Conflict detected. This idempotency key may already have been used with a different payload.'
                    );
                } else if (result.errorType === 'not_found') {
                    setErrorMessage(result.message || 'Tenant not found.');
                } else if (result.errorType === 'validation') {
                    setErrorMessage(result.message || 'Invalid input.');
                } else {
                    setErrorMessage(
                        result.message || 'Failed to create event for an unknown reason.'
                    );
                }
                return;
            }

            if (result.replayed) {
                setMessage(
                    'Duplicate request detected. Existing event was returned, and usage was not counted twice.'
                );
            } else {
                setMessage('Event created successfully.');
            }

            if (result.ok && typeof onEventCreated === 'function') {
                onEventCreated(result.event);
            }

            setTenantId('');
            setEventType('tokens');
            setAmount('');
            setAllowOverage(false);
        } catch (error) {
            console.error('Create event failed:', error);
            setErrorMessage(buildFriendlyErrorMessage(error));
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <form className="card form" onSubmit={handleSubmit}>
            <h3>Create Event</h3>

            <input
                type="text"
                placeholder="Tenant ID (UUID)"
                value={tenantId}
                onChange={(e) => setTenantId(e.target.value)}
            />

            <select value={eventType} onChange={(e) => setEventType(e.target.value)}>
                <option value="tokens">tokens</option>
                <option value="inference_seconds">inference_seconds</option>
            </select>

            <input
                type="number"
                min="1"
                placeholder="Amount"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
            />

            <label style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <input
                    type="checkbox"
                    checked={allowOverage}
                    onChange={(e) => setAllowOverage(e.target.checked)}
                />
                Allow overage (admin override)
            </label>

            <button type="submit" disabled={submitting}>
                {submitting ? 'Creating...' : 'Create Event'}
            </button>

            {message && <p style={{ color: 'green', marginTop: '10px' }}>{message}</p>}
            {errorMessage && <p style={{ color: 'red', marginTop: '10px' }}>{errorMessage}</p>}
        </form>
    );
}

function Dashboard() {
    const [events, setEvents] = useState([]);
    const [loading, setLoading] = useState(true);

    const fetchEvents = async () => {
        try {
            const response = await api.get('/v1/usage/events');
            setEvents(response.data.events);
        } catch (error) {
            console.error('Error fetching events:', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchEvents();
    }, []);

    const handleCreateEvent = async (payload) => {
        try {
            const response = await api.post('/v1/usage/events', payload);

            if (response.data.idempotency_replayed) {
                return {
                    ok: true,
                    replayed: true,
                    event: response.data,
                };
            }

            setEvents((prev) => [response.data, ...prev]);

            return {
                ok: true,
                replayed: false,
                event: response.data,
            };
        } catch (error) {
            const status = error.response?.status;
            const detail = error.response?.data?.detail;

            if (status === 409 && detail?.code === 'quota_exceeded') {
                return {
                    ok: false,
                    errorType: 'quota_exceeded',
                    message: detail.message,
                    remainingUnits: detail.remaining_units,
                    configuredQuota: detail.configured_monthly_quota,
                    monthToDateUsage: detail.month_to_date_usage,
                    requestedUnits: detail.requested_units,
                    allowOverageAvailableForAdmin: detail.allow_overage_available_for_admin,
                };
            }

            if (status === 409) {
                return {
                    ok: false,
                    errorType: 'conflict',
                    message: typeof detail === 'string' ? detail : 'Conflict error.',
                };
            }

            if (status === 404) {
                return {
                    ok: false,
                    errorType: 'not_found',
                    message: 'Tenant not found.',
                };
            }

            if (status === 422) {
                const messages = Array.isArray(error.response?.data?.detail)
                    ? error.response.data.detail
                          .map((item) => {
                              const field = item.loc?.[item.loc.length - 1];
                              return field ? `${field}: ${item.msg}` : item.msg;
                          })
                          .join('; ')
                    : 'Validation error.';

                return {
                    ok: false,
                    errorType: 'validation',
                    message: messages,
                };
            }

            return {
                ok: false,
                errorType: 'unknown',
                message:
                    typeof detail === 'string' && detail.trim()
                        ? detail
                        : 'Failed to create event.',
            };
        }
    };

    const tokenUsed = useMemo(() => {
        return events
            .filter((event) => event.event_type === 'tokens')
            .reduce((sum, event) => sum + event.amount, 0);
    }, [events]);

    const latestTokenEvent = [...events]
        .filter((event) => event.event_type === 'tokens')
        .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))[0];

    const tokenQuota = latestTokenEvent?.tenant_quota_snapshot ?? 1200000;

    return (
        <div className="container">
            <div className="cards">
                <TokenCard used={tokenUsed} total={tokenQuota} />
                <EventForm onSubmit={handleCreateEvent} />
            </div>

            <section className="events-section">
                <h2>Events</h2>
                {loading ? <p>Loading...</p> : <EventList events={events} />}
            </section>
        </div>
    );
}

function AdminPage() {
    const [tenants, setTenants] = useState([]);
    const [auditRecords, setAuditRecords] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    const [isModalOpen, setIsModalOpen] = useState(false);
    const [currentTenant, setCurrentTenant] = useState(null);
    const [newQuota, setNewQuota] = useState('');
    const [reason, setReason] = useState('');
    const [updating, setUpdating] = useState(false);

    const fetchTenants = async () => {
        const response = await api.get('/v1/tenants');
        setTenants(response.data.tenants);
    };

    const fetchAuditLogs = async () => {
        const response = await api.get('/v1/audit', {
            headers: {
                'x-admin': 'true',
            },
        });
        setAuditRecords(response.data.records);
    };

    const loadAdminData = async () => {
        try {
            setError('');
            await Promise.all([fetchTenants(), fetchAuditLogs()]);
        } catch (err) {
            console.error('Error loading admin data:', err);
            setError('Failed to load admin data.');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadAdminData();
    }, []);

    const openModal = (tenant) => {
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
                    headers: {
                        'x-admin': 'true',
                    },
                }
            );

            await Promise.all([fetchTenants(), fetchAuditLogs()]);
            closeModal();
        } catch (err) {
            console.error('Error updating tenant quota:', err.response?.data || err);

            if (err.response?.status === 422 && Array.isArray(err.response?.data?.detail)) {
                const message = err.response.data.detail.map((item) => item.msg).join('; ');
                alert(`Invalid request: ${message}`);
                return;
            }

            alert(err.response?.data?.detail || 'Failed to update quota.');
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
                <div
                    style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        marginBottom: '16px',
                    }}
                >
                    <h2>Admin View</h2>
                    <button className="edit-btn" onClick={loadAdminData}>
                        Refresh
                    </button>
                </div>
                <p>{error}</p>
            </div>
        );
    }

    return (
        <div className="admin-page">
            <div
                style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: '16px',
                }}
            >
                <h2>Admin View</h2>
                <button className="edit-btn" onClick={loadAdminData}>
                    Refresh
                </button>
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
                                    <button className="edit-btn" onClick={() => openModal(tenant)}>
                                        Edit
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            )}

            <div style={{ marginTop: '32px' }}>
                <h3>Audit Trail</h3>

                {!auditRecords.length ? (
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
                                disabled={updating}
                            >
                                Discard
                            </button>
                            <button
                                className="btn-update"
                                onClick={updateTenant}
                                disabled={updating}
                            >
                                {updating ? 'Updating...' : 'Update'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

function App() {
    return (
        <Router>
            <Header />
            <main className="page">
                <Routes>
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/admin" element={<AdminPage />} />
                </Routes>
            </main>
        </Router>
    );
}

export default App;