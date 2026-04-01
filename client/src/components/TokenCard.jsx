import React from 'react';

export default function TokenCard({ used, total }) {
    const percentRaw = total > 0 ? (used / total) * 100 : 0;
    const percent = total > 0 ? Math.min(percentRaw, 100) : 0;

    const isOver = total > 0 && used > total;
    const isWarning = total > 0 && used / total > 0.9 && !isOver;

    let statusText = 'NORMAL';
    let statusClassName = 'normal-pill';

    if (isOver) {
        statusText = 'OVER';
        statusClassName = 'over-pill';
    } else if (isWarning) {
        statusText = '⚠ WARNING';
        statusClassName = 'warning-pill';
    }

    return (
        <div className={`tenant-card usage-card ${isOver ? 'usage-card-over' : ''}`}>
            <div className="usage-card-header">
                <h3>Token Utilizations</h3>
            </div>

            <div className="usage-big-number">{used.toLocaleString()}</div>

            <div className="usage-progress-row">
                <div className="progress-container">
                    <div
                        className={`progress ${isOver ? 'progress-over' : ''}`}
                        style={{ width: `${percent}%` }}
                    />
                </div>
            </div>

            <div className="usage-footer-row">
                <div className={`pill ${statusClassName}`}>{statusText}</div>
                <div className="usage-total-number">{total.toLocaleString()}</div>
            </div>
        </div>
    );
}
