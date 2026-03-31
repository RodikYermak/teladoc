import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import './index.css';
import Header from './components/Header';
import Dashboard from './pages/Dashboard';
import AdminPage from './components/AdminPage';

function App() {
    return (
        <Router>
            <Header />
            <main className="page">
                <Routes>
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/admin" element={<AdminPage />} />
                </Routes>
            </main>
        </Router>
    );
}

export default App;