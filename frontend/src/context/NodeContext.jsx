import React, { createContext, useState, useContext, useEffect } from 'react';
import { nodes } from '../nodeConfig';
import { setApiBaseUrl } from '../api/client';

const NodeContext = createContext();

export const NodeProvider = ({ children }) => {
    const [selectedNode, setSelectedNode] = useState(nodes[0]);
    const [isSwitching, setIsSwitching] = useState(false);

    useEffect(() => {
        // Initialize API client with the default node
        setApiBaseUrl(nodes[0].url);
    }, []);

    const changeNode = (nodeId) => {
        const node = nodes.find(n => n.id === nodeId);
        if (node) {
            setIsSwitching(true);
            setSelectedNode(node);
            setApiBaseUrl(node.url);

            // Artificial delay to show the transition
            setTimeout(() => {
                setIsSwitching(false);
            }, 800);
        }
    };

    return (
        <NodeContext.Provider value={{ selectedNode, nodes, changeNode, isSwitching }}>
            {children}
        </NodeContext.Provider>
    );
};

export const useNode = () => {
    const context = useContext(NodeContext);
    if (!context) {
        throw new Error('useNode must be used within a NodeProvider');
    }
    return context;
};
