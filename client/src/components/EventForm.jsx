import React, { useState } from 'react';

export default function EventForm({ onSubmit }) {
    const [tenantId, setTenantId] = useState('');
    const [eventType, setEventType] = useState('tokens');
    const [amount, setAmount] = useState('');
    const [submitting, setSubmitting] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();

        if (!tenantId || !amount) return;

        setSubmitting(true);

        try {
            await onSubmit({
                tenant_id: tenantId,
                event_type: eventType,
                amount: Number(amount),
            });

            setTenantId('');
            setEventType('tokens');
            setAmount('');
        } catch (error) {
            console.error(error);
            alert('Failed to create event. Make sure Tenant ID is a valid UUID.');
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

            <button type="submit" disabled={submitting}>
                {submitting ? 'Creating...' : 'Create Event'}
            </button>
        </form>
    );
}
