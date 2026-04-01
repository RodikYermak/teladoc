import React, { useState } from 'react';

function generateIdempotencyKey() {
    return crypto.randomUUID();
}

export default function EventForm({ onSubmit }) {
    const [tenantId, setTenantId] = useState('');
    const [type, setType] = useState('tokens');
    const [amount, setAmount] = useState('');
    const [submitting, setSubmitting] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();

        if (!tenantId || !amount) return;

        setSubmitting(true);

        try {
            await onSubmit({
                tenant_id: tenantId,
                event_type: type,
                amount: Number(amount),
                idempotency_key: generateIdempotencyKey(),
            });

            setTenantId('');
            setType('tokens');
            setAmount('');
        } catch (error) {
            console.error(error);

            if (error.response?.status === 409) {
                alert('Duplicate event with different payload detected.');
            } else {
                alert('Failed to create event.');
            }
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

            <select value={type} onChange={(e) => setType(e.target.value)}>
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

            <button type="submit" disabled={submitting}>
                {submitting ? 'Creating...' : 'Create Event'}
            </button>
        </form>
    );
}
