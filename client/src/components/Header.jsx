import React from 'react';
import { Link } from 'react-router-dom';

export default function Header() {
    return (
        <header>
            <div className="logo">
                Teladoc <span>HEALTH</span>
            </div>
            <div className="nav">
                <Link to="/">Tenant Dashboard</Link>
                <Link to="/admin">Admin View</Link>
                <div className="profile">A</div>
            </div>
        </header>
    );
}
