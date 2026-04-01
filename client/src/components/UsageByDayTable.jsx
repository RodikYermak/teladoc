import React from 'react';

function formatShortDate(value) {
    return new Date(value).toLocaleDateString('en-US', {
        month: 'long',
        day: 'numeric',
        year: 'numeric',
    });
}

function formatTime(value) {
    return new Date(value).toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit',
        second: '2-digit',
    });
}

export default function UsageByDayTable({ events }) {
    if (!events.length) {
        return <p>No usage events yet.</p>;
    }

    const grouped = events.reduce((acc, event) => {
        const dayKey = new Date(event.timestamp).toDateString();
        if (!acc[dayKey]) acc[dayKey] = [];
        acc[dayKey].push(event);
        return acc;
    }, {});

    const orderedDays = Object.keys(grouped).sort((a, b) => new Date(b) - new Date(a));

    return (
        <div className="usage-table-wrap">
            {orderedDays.map((dayKey) => {
                const items = grouped[dayKey].sort(
                    (a, b) => new Date(b.timestamp) - new Date(a.timestamp),
                );

                return (
                    <div key={dayKey} className="usage-day-group">
                        <div className="usage-day-title">{formatShortDate(items[0].timestamp)}</div>

                        <table className="usage-day-table">
                            <tbody>
                                {items.map((event) => (
                                    <tr key={event.event_id}>
                                        <td className="usage-time-cell">
                                            {formatTime(event.timestamp)}
                                        </td>
                                        <td className="usage-type-cell">
                                            {event.event_type === 'tokens'
                                                ? 'Tokens processed'
                                                : 'Inference seconds'}
                                        </td>
                                        <td className="usage-amount-cell">
                                            {event.amount.toLocaleString()}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                );
            })}
        </div>
    );
}
