import React, { useEffect, useState } from 'react';
import api from '../api';

function formatDate(value) {
    if (!value) return 'No activity yet';
    return new Date(value).toLocaleString();
}

export default function AdminPage() {
    const [tenants, setTenants] = useState([]);
    const [loading, setLoading] = useState(true);

    const [isModalOpen, setIsModalOpen] = useState(false);
    const [currentTenant, setCurrentTenant] = useState(null);
    const [newQuota, setNewQuota] = useState('');
    const [reason, setReason] = useState('');

    useEffect(() => {
        const fetchTenants = async () => {
            try {
                const res = await api.get('/v1/tenants');
                setTenants(res.data.tenants);
            } catch (err) {
                console.error('Error fetching tenants:', err);
            } finally {
                setLoading(false);
            }
        };

        fetchTenants();
    }, []);

    const openModal = (tenant) => {
        setCurrentTenant(tenant);
        setNewQuota(String(tenant.configured_monthly_quota));
        setReason('');
        setIsModalOpen(true);
    };

    const closeModal = () => {
        setIsModalOpen(false);
        setCurrentTenant(null);
        setNewQuota('');
        setReason('');
    };

    const updateTenant = () => {
        if (!currentTenant) return;

        // 🔥 For now: update locally (no backend yet)
        setTenants((prev) =>
            prev.map((t) =>
                t.tenant_id === currentTenant.tenant_id
                    ? { ...t, configured_monthly_quota: Number(newQuota) }
                    : t,
            ),
        );

        closeModal();
    };

    if (loading) {
        return (
            <div className="admin-page">
                <h2>Admin View</h2>
                <p>Loading tenants...</p>
            </div>
        );
    }

    return (
        <div className="admin-page">
            <h2>Admin View</h2>

            <table className="tenant-table">
                <thead>
                    <tr>
                        <th>Tenant ID</th>
                        <th>Quota</th>
                        <th>Used</th>
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

            {/* 🔥 Modal */}
            {isModalOpen && currentTenant && (
                <div className="overlay">
                    <div className="modal">
                        <h3>Edit Quota</h3>

                        <div className="field">
                            <label>Tenant</label>
                            <input value={currentTenant.tenant_id} readOnly />
                        </div>

                        <div className="field">
                            <label>Current Quota</label>
                            <input value={currentTenant.configured_monthly_quota} readOnly />
                        </div>

                        <div className="field">
                            <label>New Quota</label>
                            <input
                                type="number"
                                value={newQuota}
                                onChange={(e) => setNewQuota(e.target.value)}
                            />
                        </div>

                        <div className="field">
                            <label>Reason</label>
                            <input
                                placeholder="Reason for change"
                                value={reason}
                                onChange={(e) => setReason(e.target.value)}
                            />
                        </div>

                        <div className="actions">
                            <button className="btn-discard" onClick={closeModal}>
                                Discard
                            </button>
                            <button className="btn-update" onClick={updateTenant}>
                                Update
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
