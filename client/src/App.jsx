import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import './index.css';
import Header from './components/Header';
import { TokenCard, EventForm } from './components/Card';
import EventList from './components/EventList';
import AdminPage from './components/AdminPage';
import FruitList from './components/Fruits';

const eventsData = [
    {
        date: 'March 28, 2026',
        items: [
            { name: '10:00:00 AM Tokens processed', value: 2000 },
            { name: '9:00:00 AM Inference seconds', value: 3000 },
            { name: '8:00:00 AM Requests', value: 1000 },
        ],
    },
    {
        date: 'March 27, 2026',
        items: [
            { name: '10:00:00 AM Tokens processed', value: 2000 },
            { name: '9:00:00 AM Inference seconds', value: 3000 },
            { name: '8:00:00 AM Requests', value: 1000 },
        ],
    },
    {
        date: 'March 26, 2026',
        items: [
            { name: '10:00:00 AM Tokens processed', value: 2000 },
            { name: '9:00:00 AM Inference seconds', value: 3000 },
            { name: '8:00:00 AM Requests', value: 1000 },
        ],
    },
];

function Dashboard() {
    return (
        <div className="container">
            <div className="cards">
                <TokenCard used={1000000} total={1200000} />
                <EventForm />
            </div>
            <h2>Events</h2>
            <EventList events={eventsData} />
        </div>
    );
}

function App() {
    return (
        <Router>
            <Header />
            <main>
                <FruitList />
            </main>
            <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/admin" element={<AdminPage />} />
            </Routes>
        </Router>
    );
}

export default App;
