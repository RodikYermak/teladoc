import React, { useEffect, useState } from 'react';
import axios from 'axios';

// Create an Axios instance
const api = axios.create({
    baseURL: 'http://localhost:8000', // change if your backend URL is different
});

const FruitList = () => {
    const [fruits, setFruits] = useState([]);
    const [fruitName, setFruitName] = useState('');

    // Fetch fruits from the API
    useEffect(() => {
        const fetchFruits = async () => {
            try {
                const response = await api.get('/fruits');
                setFruits(response.data.fruits);
            } catch (error) {
                console.error('Error fetching fruits', error);
            }
        };

        fetchFruits();
    }, []);

    // Add a new fruit and update state
    const addFruit = async (name) => {
        if (!name) return;
        try {
            await api.post('/fruits', { name });
            // Optimistically update local state without refetching
            setFruits((prev) => [...prev, { name }]);
            setFruitName('');
        } catch (error) {
            console.error('Error adding fruit', error);
        }
    };

    // Handle form submission
    const handleSubmit = (e) => {
        e.preventDefault();
        addFruit(fruitName);
    };

    return (
        <div>
            <h2>Fruits List</h2>
            <ul>
                {fruits.map((fruit, index) => (
                    <li key={index}>{fruit.name}</li>
                ))}
            </ul>

            <form onSubmit={handleSubmit}>
                <input
                    type="text"
                    value={fruitName}
                    onChange={(e) => setFruitName(e.target.value)}
                    placeholder="Enter fruit name"
                />
                <button type="submit">Add Fruit</button>
            </form>
        </div>
    );
};

export default FruitList;
