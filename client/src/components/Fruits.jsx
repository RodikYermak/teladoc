import React, { useEffect, useState } from 'react';
import AddFruitForm from './AddFruitForm';
import api from '../api';

const FruitList = () => {
    const [fruits, setFruits] = useState([]);

    // Fetch fruits from the API
    useEffect(() => {
        const fetchFruits = async () => {
            try {
                const response = await api.get('/fruits');
                setFruits(response.data.fruits); // Safe async state update
            } catch (error) {
                console.error('Error fetching fruits', error);
            }
        };

        fetchFruits();
    }, []); // Run once on mount

    // Add a new fruit and refresh the list
    const addFruit = async (fruitName) => {
        try {
            await api.post('/fruits', { name: fruitName });
            // Refetch after adding
            const response = await api.get('/fruits');
            setFruits(response.data.fruits);
        } catch (error) {
            console.error('Error adding fruit', error);
        }
    };

    return (
        <div>
            <h2>Fruits List</h2>
            <ul>
                {fruits.map((fruit, index) => (
                    <li key={index}>{fruit.name}</li>
                ))}
            </ul>
            <AddFruitForm addFruit={addFruit} />
        </div>
    );
};

export default FruitList;
