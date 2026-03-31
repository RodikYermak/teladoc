import React, { useState } from 'react';

const initialTenants = [
    {
        id: 1,
        email: 'tenant1@email.com',
        quota: 1000000,
        used: 800000,
        lastActivity: 'Tokens processed',
    },
    {
        id: 2,
        email: 'tenant2@email.com',
        quota: 1200000,
        used: 220000,
        lastActivity: 'Inference seconds',
    },
    {
        id: 3,
        email: 'tenant3@email.com',
        quota: 1500000,
        used: 70000,
        lastActivity: 'Tokens processed',
    },
];

export default function AdminPage() {
    const [tenants, setTenants] = useState(initialTenants);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [currentTenant, setCurrentTenant] = useState(null);
    const [newQuota, setNewQuota] = useState('');
    const [reason, setReason] = useState('');

    const openModal = (tenant) => {
        setCurrentTenant(tenant);
        setNewQuota(String(tenant.quota));
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
        if (!currentTenant || !newQuota || !reason.trim()) return;

        setTenants((prev) =>
            prev.map((tenant) =>
                tenant.id === currentTenant.id ? { ...tenant, quota: Number(newQuota) } : tenant,
            ),
        );

        closeModal();
    };

    return (
        <div className="admin-page">
            <h2>Admin View</h2>

            <table className="tenant-table">
                <thead>
                    <tr>
                        <th>Tenant</th>
                        <th>Quota</th>
                        <th>Used</th>
                        <th>Last Activity</th>
                        <th></th>
                    </tr>
                </thead>
                <tbody>
                    {tenants.map((tenant) => (
                        <tr key={tenant.id}>
                            <td>{tenant.email}</td>
                            <td>{tenant.quota.toLocaleString()}</td>
                            <td>{tenant.used.toLocaleString()}</td>
                            <td>{tenant.lastActivity}</td>
                            <td>
                                <button className="edit-btn" onClick={() => openModal(tenant)}>
                                    Edit
                                </button>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>

            {isModalOpen && currentTenant && (
                <div className="overlay">
                    <div className="modal">
                        <h3>Edit Quota</h3>

                        <div className="field">
                            <label>Tenant</label>
                            <input type="text" value={currentTenant.email} readOnly />
                        </div>

                        <div className="field">
                            <label>Current Quota</label>
                            <input type="text" value={currentTenant.quota} readOnly />
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
                                type="text"
                                placeholder="Reason for change"
                                maxLength={100}
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
