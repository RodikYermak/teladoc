import React from 'react';

function formatTimestamp(timestamp) {
    return new Date(timestamp).toLocaleString();
}

export default function EventList({ events }) {
    if (!events.length) {
        return <p>No events yet.</p>;
    }

    return (
        <div className="events">
            {events.map((event) => (
                <div className="event-item" key={event.event_id}>
                    <div>
                        <strong>{event.type}</strong> — {event.amount.toLocaleString()}
                    </div>
                    <div className="event-meta">Tenant: {event.tenant_id}</div>
                    <div className="event-meta">{formatTimestamp(event.timestamp)}</div>
                </div>
            ))}
        </div>
    );
}
