import React from 'react';

export default function TokenCard({ used, total }) {
    const percent = Math.min((used / total) * 100, 100);
    const isWarning = used / total >= 0.8;

    return (
        <div className="card">
            <h3>Token Utilization</h3>
            <div className="metric">{used.toLocaleString()}</div>

            <div className="progress-container">
                <div className="progress" style={{ width: `${percent}%` }} />
            </div>

            <div className="subtext">Quota: {total.toLocaleString()}</div>

            {isWarning && <div className="warning">⚠️ Warning: usage above 80%</div>}
        </div>
    );
}
