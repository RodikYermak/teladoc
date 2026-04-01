import React, { useState } from 'react';
import api from '../api';

function generateIdempotencyKey() {
    return crypto.randomUUID();
}

export default function EventForm({ onSubmit, onEventCreated }) {
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
                                : ''),
                    );
                } else if (result.errorType === 'conflict') {
                    setErrorMessage(
                        result.message ||
                            'Conflict detected. This idempotency key may already have been used with a different payload.',
                    );
                } else if (result.errorType === 'not_found') {
                    setErrorMessage(result.message || 'Tenant not found.');
                } else if (result.errorType === 'validation') {
                    setErrorMessage(result.message || 'Invalid input.');
                } else {
                    setErrorMessage(
                        result.message || 'Failed to create event for an unknown reason.',
                    );
                }
                return;
            }

            if (result.replayed) {
                setMessage(
                    'Duplicate request detected. Existing event was returned, and usage was not counted twice.',
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
