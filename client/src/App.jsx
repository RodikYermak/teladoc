import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import './index.css';
import Header from './components/Header';
import LoginPage from './pages/LoginPage';
import Dashboard from './pages/Dashboard';
import AdminPage from './pages/AdminPage';

const AUTH_STORAGE_KEY = 'teladoc_auth';

function getStoredAuth() {
    try {
        const raw = localStorage.getItem(AUTH_STORAGE_KEY);
        return raw ? JSON.parse(raw) : null;
    } catch {
        return null;
    }
}

function setStoredAuth(auth) {
    localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(auth));
}

function clearStoredAuth() {
    localStorage.removeItem(AUTH_STORAGE_KEY);
}

function ProtectedRoute({ isAuthenticated, children }) {
    if (!isAuthenticated) {
        return <Navigate to="/login" replace />;
    }

    return children;
}

function AppShell({ auth, onLogout, onUnauthorized }) {
    return (
        <>
            <Header auth={auth} onLogout={onLogout} />
            <main className="page">
                <Routes>
                    <Route
                        path="/"
                        element={
                            <ProtectedRoute isAuthenticated={!!auth}>
                                <Dashboard auth={auth} onUnauthorized={onUnauthorized} />
                            </ProtectedRoute>
                        }
                    />
                    <Route
                        path="/admin"
                        element={
                            <ProtectedRoute isAuthenticated={!!auth}>
                                <AdminPage auth={auth} onUnauthorized={onUnauthorized} />
                            </ProtectedRoute>
                        }
                    />
                </Routes>
            </main>
        </>
    );
}

export default function App() {
    const [auth, setAuth] = useState(() => getStoredAuth());

    const handleLogin = (authPayload) => {
        setStoredAuth(authPayload);
        setAuth(authPayload);
    };

    const handleLogout = () => {
        clearStoredAuth();
        setAuth(null);
    };

    const handleUnauthorized = () => {
        clearStoredAuth();
        setAuth(null);
    };

    return (
        <Router>
            <Routes>
                <Route
                    path="/login"
                    element={
                        auth ? <Navigate to="/" replace /> : <LoginPage onLogin={handleLogin} />
                    }
                />
                <Route
                    path="/*"
                    element={
                        <AppShell
                            auth={auth}
                            onLogout={handleLogout}
                            onUnauthorized={handleUnauthorized}
                        />
                    }
                />
            </Routes>
        </Router>
    );
}
