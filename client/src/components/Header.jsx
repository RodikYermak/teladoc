import React from 'react';
import { Link, useLocation } from 'react-router-dom';

export default function Header({ auth, onLogout }) {
    const location = useLocation();
    const isAdmin = auth?.user?.role === 'admin';

    return (
        <header className="app-header-wrap">
            <div className="header-inner">
                <div className="logo">
                    Teladoc <span>HEALTH</span>
                </div>

                <nav className="nav">
                    <Link
                        to="/"
                        className={location.pathname === '/' ? 'nav-link active' : 'nav-link'}>
                        Tenant Dashboard
                    </Link>

                    {isAdmin ? (
                        <Link
                            to="/admin"
                            className={
                                location.pathname === '/admin' ? 'nav-link active' : 'nav-link'
                            }>
                            Admin View
                        </Link>
                    ) : (
                        <span className="nav-link nav-link-disabled" title="Admin only">
                            Admin View
                        </span>
                    )}

                    <div className="profile">{auth?.user?.display_name?.[0] || 'A'}</div>

                    <button className="logout-btn" onClick={onLogout}>
                        Log out
                    </button>
                </nav>
            </div>
            <div className="header-divider" />
        </header>
    );
}
