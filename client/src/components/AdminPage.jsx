import React, { useEffect, useState } from 'react';
import api from '../api';

function formatDate(value) {
    if (!value) return 'No activity yet';
    return new Date(value).toLocaleString();
}

export default function AdminPage() {
    const [tenants, setTenants] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    const [isModalOpen, setIsModalOpen] = useState(false);
    const [currentTenant, setCurrentTenant] = useState(null);
    const [newQuota, setNewQuota] = useState('');
    const [reason, setReason] = useState('');
    const [updating, setUpdating] = useState(false);

    const fetchTenants = async () => {
        try {
            setError('');
            const response = await api.get('/v1/tenants');
            setTenants(response.data.tenants);
        } catch (err) {
            console.error('Error fetching tenants:', err);
            setError('Failed to load tenants.');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchTenants();
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

        if (!newQuota || Number(newQuota) <= 0) {
            alert('Please enter a valid quota.');
            return;
        }

        if (!reason.trim()) {
            alert('Please provide a reason.');
            return;
        }

        try {
            setUpdating(true);

            await api.put(
                `/v1/tenants/${currentTenant.tenant_id}/quota`,
                {
                    new_monthly_quota: Number(newQuota),
                    reason: reason.trim(),
                },
                {
                    headers: {
                        'x-admin': 'true',
                    },
                },
            );

            await fetchTenants();
            closeModal();
        } catch (err) {
            console.error('Error updating tenant quota:', err.response?.data || err);
            alert(err.response?.data?.detail || 'Failed to update quota.');
        } finally {
            setUpdating(false);
        }
    };

    if (loading) {
        return (
            <div className="admin-page">
                <h2>Admin View</h2>
                <p>Loading tenants...</p>
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
                    <button className="edit-btn" onClick={fetchTenants}>
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
                <button className="edit-btn" onClick={fetchTenants}>
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
                                placeholder="Reason for change"
                                maxLength={200}
                                value={reason}
                                onChange={(e) => setReason(e.target.value)}
                            />
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
