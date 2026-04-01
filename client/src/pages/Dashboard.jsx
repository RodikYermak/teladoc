import React, { useEffect, useMemo, useState } from 'react';
import api from '../api';
import TokenCard from '../components/TokenCard';
import EventForm from '../components/EventForm';
import EventList from '../components/EventList';

const TOKEN_QUOTA = 1200000;

export default function Dashboard() {
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

    const handleEventCreated = () => {
        // Hook available if you later lift state or add shared refresh logic.
        // For now, Dashboard state is already updated in handleCreateEvent.
    };

    const tokenUsed = useMemo(() => {
        return events
            .filter((event) => event.event_type === 'tokens')
            .reduce((sum, event) => sum + event.amount, 0);
    }, [events]);

    return (
        <div className="container">
            <div className="cards">
                <TokenCard used={tokenUsed} total={TOKEN_QUOTA} />
                <EventForm onSubmit={handleCreateEvent} onEventCreated={handleEventCreated} />
            </div>

            <section className="events-section">
                <h2>Events</h2>
                {loading ? <p>Loading...</p> : <EventList events={events} />}
            </section>
        </div>
    );
}
