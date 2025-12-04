import React, { createContext, useState, useContext, useEffect } from 'react';
import { useLocation } from 'react-router-dom';

const ViewContext = createContext();

export const ViewProvider = ({ children }) => {
    const location = useLocation();
    const [viewMode, setViewMode] = useState(
        location.pathname === '/unified' ? 'unified' : 'separate'
    );

    // Sync view mode with route
    useEffect(() => {
        if (location.pathname === '/unified') {
            setViewMode('unified');
        } else {
            setViewMode('separate');
        }
    }, [location.pathname]);

    const toggleView = () => {
        setViewMode(prev => prev === 'separate' ? 'unified' : 'separate');
    };

    return (
        <ViewContext.Provider value={{ viewMode, setViewMode, toggleView }}>
            {children}
        </ViewContext.Provider>
    );
};

export const useView = () => {
    const context = useContext(ViewContext);
    if (!context) {
        throw new Error('useView must be used within a ViewProvider');
    }
    return context;
};

