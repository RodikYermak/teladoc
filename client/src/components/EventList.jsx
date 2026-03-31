import React from 'react';

export default function EventList({ events }) {
    return (
        <div className="events">
            {events.map((day) => (
                <div key={day.date}>
                    <div className="event-day">{day.date}</div>
                    {day.items.map((item, idx) => (
                        <div className="event-item" key={idx}>
                            <span>{item.name}</span>
                            <span>{item.value.toLocaleString()}</span>
                        </div>
                    ))}
                </div>
            ))}
        </div>
    );
}
