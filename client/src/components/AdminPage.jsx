import React, { useEffect, useState } from 'react';
import api from '../api';

function formatDate(value) {
    if (!value) return 'No activity yet';
    return new Date(value).toLocaleString();
}

export default function AdminPage() {
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
                },
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
                    }}>
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
                }}>
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
