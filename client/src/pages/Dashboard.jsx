import React, { useEffect, useMemo, useState } from 'react';
import api from '../api';
import TokenCard from '../components/TokenCard';
import EventForm from '../components/EventForm';
import EventList from '../components/EventList';

const TOKEN_QUOTA = 1200000;

export default function Dashboard() {
    const [events, setEvents] = useState([]);
    const [loading, setLoading] = useState(true);

    const fetchEvents = async () => {
        try {
            const response = await api.get('/events');
            setEvents(response.data.events);
        } catch (error) {
            console.error('Error fetching events:', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchEvents();
    }, []);

    const handleCreateEvent = async (payload) => {
        try {
            const response = await api.post('/events', payload);
            setEvents((prev) => [response.data, ...prev]);
        } catch (error) {
            console.error('Error creating event:', error);
            throw error;
        }
    };

    const tokenUsed = useMemo(() => {
        return events
            .filter((event) => event.type === 'tokens')
            .reduce((sum, event) => sum + event.amount, 0);
    }, [events]);

    return (
        <div className="container">
            <div className="cards">
                <TokenCard used={tokenUsed} total={TOKEN_QUOTA} />
                <EventForm onSubmit={handleCreateEvent} />
            </div>

            <section className="events-section">
                <h2>Events</h2>
                {loading ? <p>Loading...</p> : <EventList events={events} />}
            </section>
        </div>
    );
}