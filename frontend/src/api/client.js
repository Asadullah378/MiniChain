import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || window.location.origin;

const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

export const getStatus = async () => {
    const response = await api.get('/status');
    return response.data;
};

export const getBlocks = async (start = 0, limit = 10) => {
    const response = await api.get('/blocks', {
        params: { start, limit },
    });
    return response.data;
};

export const getBlockDetails = async (height) => {
    const response = await api.get(`/blocks/${height}`);
    return response.data;
};

export const getMempool = async () => {
    const response = await api.get('/mempool');
    return response.data;
};

export const submitTransaction = async (transaction) => {
    const response = await api.post('/submit', transaction);
    return response.data;
};

export default api;
