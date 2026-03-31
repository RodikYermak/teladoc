import React from 'react';

export function TokenCard({ used, total }) {
    const progress = (used / total) * 100 + '%';

    return (
        <div className="card">
            <h3>Token Utilizations</h3>
            <div className="token-utilization">{used.toLocaleString()}</div>
            <div className="progress-container">
                <div className="progress" style={{ width: progress }}></div>
            </div>
            <div>{total.toLocaleString()}</div>
            <div className="warning">⚠️ WARNING</div>
        </div>
    );
}

export function EventForm() {
    return (
        <div className="card form">
            <h3>Event</h3>
            <input type="text" placeholder="Event Name" />
            <input type="number" placeholder="1,000" />
            <button>Create Event</button>
        </div>
    );
}
