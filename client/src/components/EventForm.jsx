import React, { useEffect, useState } from 'react';

function generateIdempotencyKey() {
    return crypto.randomUUID();
}

export default function EventForm({
    onSubmit,
    isAdmin,
    auth,
    defaultTenantId = '',
    tenants = [],
    onTenantChange,
}) {
    const tenantScopedId = auth?.user?.tenant_id || '';
    const [tenantId, setTenantId] = useState(tenantScopedId || defaultTenantId);
    const [eventType, setEventType] = useState('tokens');
    const [amount, setAmount] = useState('');
    const [allowOverage, setAllowOverage] = useState(false);
    const [submitting, setSubmitting] = useState(false);
    const [message, setMessage] = useState('');
    const [errorMessage, setErrorMessage] = useState('');

    useEffect(() => {
        if (!isAdmin && tenantScopedId) {
            setTenantId(tenantScopedId);
            return;
        }

        if (isAdmin && defaultTenantId) {
            setTenantId(defaultTenantId);
        }
    }, [isAdmin, tenantScopedId, defaultTenantId]);

    const handleAdminTenantChange = (value) => {
        setTenantId(value);
        onTenantChange?.(value);
    };

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
                setTenantId(defaultTenantId || '');
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

            {isAdmin ? (
                <select value={tenantId} onChange={(e) => handleAdminTenantChange(e.target.value)}>
                    {tenants.map((tenant) => (
                        <option key={tenant.tenant_id} value={tenant.tenant_id}>
                            {tenant.tenant_id}
                        </option>
                    ))}
                </select>
            ) : (
                <input
                    type="text"
                    placeholder="Tenant UUID"
                    value={tenantId}
                    onChange={(e) => setTenantId(e.target.value)}
                    readOnly
                />
            )}

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
