import React, { useState } from 'react';

const tenantsData = [
    { email: 'tenant@email.com', quota: 1000000, used: 80, lastActivity: 'Tokens processed' },
    { email: 'tenant@email.com', quota: 1200000, used: 220000, lastActivity: 'Inference seconds' },
    { email: 'tenant@email.com', quota: 1500000, used: 70000, lastActivity: 'Requests' },
    { email: 'tenant@email.com', quota: 100000, used: 1200, lastActivity: 'Tokens processed' },
    { email: 'tenant@email.com', quota: 500, used: 300, lastActivity: 'Tokens processed' },
];

export default function AdminPage() {
    const [tenants, setTenants] = useState(tenantsData);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [currentTenant, setCurrentTenant] = useState(null);
    const [newQuota, setNewQuota] = useState('');
    const [reason, setReason] = useState('');

    const openModal = (tenant) => {
        setCurrentTenant(tenant);
        setNewQuota(tenant.quota);
        setReason('');
        setIsModalOpen(true);
    };

    const closeModal = () => {
        setIsModalOpen(false);
        setCurrentTenant(null);
    };

    const updateTenant = () => {
        if (!currentTenant) return;

        setTenants((prev) =>
            prev.map((t) =>
                t.email === currentTenant.email ? { ...t, quota: Number(newQuota) } : t,
            ),
        );
        closeModal();
    };

    return (
        <div style={{ padding: '40px' }}>
            <table>
                <thead>
                    <tr>
                        <th>TENANT</th>
                        <th>QUOTA</th>
                        <th>USED</th>
                        <th>LAST ACTIVITY</th>
                        <th></th>
                    </tr>
                </thead>
                <tbody>
                    {tenants.map((t, idx) => (
                        <tr key={idx}>
                            <td>{t.email}</td>
                            <td>{t.quota.toLocaleString()}</td>
                            <td>{t.used.toLocaleString()}</td>
                            <td>{t.lastActivity}</td>
                            <td>
                                <button className="edit-btn" onClick={() => openModal(t)}>
                                    Edit
                                </button>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>

            {/* Modal */}
            {isModalOpen && (
                <div className="overlay">
                    <div className="modal">
                        <h2>Edit Quota</h2>

                        <div className="field">
                            <label>Tenant</label>
                            <input type="text" value={currentTenant.email} readOnly />
                        </div>

                        <div className="field">
                            <label>Current Quota</label>
                            <input
                                type="text"
                                value={currentTenant.quota.toLocaleString()}
                                readOnly
                            />
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
                                placeholder="up to 8 characters"
                                maxLength={8}
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
