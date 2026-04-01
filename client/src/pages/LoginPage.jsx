import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

const api = axios.create({
    baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
});

export default function LoginPage({ onLogin }) {
    const [identifier, setIdentifier] = useState('');
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [submitting, setSubmitting] = useState(false);
    const [errorMessage, setErrorMessage] = useState('');
    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setErrorMessage('');

        if (!identifier.trim() || !password.trim()) {
            setErrorMessage('Please enter your username/email and password.');
            return;
        }

        try {
            setSubmitting(true);

            const response = await api.post('/v1/auth/login', {
                identifier: identifier.trim(),
                password,
            });

            const authPayload = {
                token: response.data.access_token,
                expires_at: response.data.expires_at,
                user: response.data.user,
            };

            onLogin(authPayload);
            navigate('/', { replace: true });
        } catch (error) {
            setErrorMessage(error.response?.data?.message || 'Invalid username/email or password.');
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="login-page">
            <div className="login-brand-row">
                <div className="logo login-logo">
                    Teladoc <span>HEALTH</span>
                </div>
            </div>

            <div className="login-divider" />

            <div className="login-card">
                <h1 className="login-title">Sign in to your account</h1>

                <form onSubmit={handleSubmit} className="login-form">
                    <div className="login-field">
                        <label>Username or email</label>
                        <input
                            type="text"
                            value={identifier}
                            onChange={(e) => setIdentifier(e.target.value)}
                        />
                    </div>

                    <div className="login-field">
                        <label>Password</label>
                        <div className="password-input-wrap">
                            <input
                                type={showPassword ? 'text' : 'password'}
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                            />
                            <button
                                type="button"
                                className="password-toggle"
                                onClick={() => setShowPassword((prev) => !prev)}
                                aria-label="Toggle password visibility">
                                {showPassword ? '🙈' : '👁️'}
                            </button>
                        </div>
                    </div>

                    <div className="login-help-links">
                        Forgot <a href="#!">username</a> or <a href="#!">password?</a>
                    </div>

                    {errorMessage && <p className="login-error">{errorMessage}</p>}

                    <button type="submit" className="login-submit-btn" disabled={submitting}>
                        {submitting ? 'Signing In...' : 'Sign In'}
                    </button>

                    <div className="login-secondary-link">
                        <a href="#!">Create a new account</a>
                    </div>
                </form>

                <div className="login-demo-box">
                    <strong>Demo users</strong>
                    <div>admin / password123</div>
                    <div>tenant1 / password123</div>
                    <div>tenant2 / password123</div>
                    <div>tenant3 / password123</div>
                </div>
            </div>
        </div>
    );
}
