import React from 'react';
import { Link } from 'react-router-dom';

export default function Header() {
    return (
        <header className="header">
            <div className="logo">
                Teladoc <span>HEALTH</span>
            </div>

            <nav className="nav">
                <Link to="/">Tenant Dashboard</Link>
                <Link to="/admin">Admin View</Link>
                <div className="profile">A</div>
            </nav>
        </header>
    );
}
