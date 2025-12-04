import React, { useState, useEffect } from 'react';
import { Box, Hash, User, Clock } from 'lucide-react';
import { getBlocks, getStatus, setApiBaseUrl, api } from '../api/client';
import Dialog from './Dialog';

const BlocksDialog = ({ isOpen, onClose, nodeUrl, nodeName }) => {
    const [blocks, setBlocks] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (!isOpen) return;

        const fetchBlocks = async () => {
            try {
                setLoading(true);
                setError(null);
                const originalUrl = api.defaults.baseURL || window.location.origin;
                setApiBaseUrl(nodeUrl);
                
                const status = await getStatus();
                const height = status.height;
                const limit = 20;
                const start = Math.max(0, height - limit + 1);
                
                const data = await getBlocks(start, limit);
                setBlocks([...data].reverse());
                setApiBaseUrl(originalUrl);
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };

        fetchBlocks();
        const interval = setInterval(fetchBlocks, 3000);
        return () => clearInterval(interval);
    }, [isOpen, nodeUrl]);

    return (
        <Dialog
            isOpen={isOpen}
            onClose={onClose}
            title={`Blocks - ${nodeName}`}
            size="lg"
        >
            {loading && blocks.length === 0 ? (
                <div className="text-center py-12 text-slate-500 dark:text-slate-400">
                    Loading blocks...
                </div>
            ) : error ? (
                <div className="text-center py-12 text-red-400">
                    Error: {error}
                </div>
            ) : blocks.length === 0 ? (
                <div className="text-center py-12">
                    <Box className="w-16 h-16 mx-auto mb-4 text-slate-400 dark:text-slate-600" />
                    <p className="text-slate-500 dark:text-slate-400">No blocks found</p>
                </div>
            ) : (
                <div className="logs-scrollbar space-y-3 max-h-[60vh] overflow-y-auto">
                    {blocks.map((block) => (
                        <div
                            key={block.hash}
                            className="p-4 bg-slate-50 dark:bg-slate-800/50 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                        >
                            <div className="flex items-center justify-between mb-3">
                                <div className="flex items-center gap-3">
                                    <Box className="w-5 h-5 text-blue-500" />
                                    <span className="font-bold text-slate-900 dark:text-white">
                                        Block #{block.height}
                                    </span>
                                </div>
                                <div className="text-sm text-slate-500 dark:text-slate-400 flex items-center gap-2">
                                    <Clock className="w-4 h-4" />
                                    {new Date(block.timestamp * 1000).toLocaleString()}
                                </div>
                            </div>
                            <div className="grid grid-cols-2 gap-3 text-sm">
                                <div>
                                    <div className="text-slate-500 dark:text-slate-400 text-xs mb-1 flex items-center gap-1">
                                        <Hash className="w-3 h-3" />
                                        Hash
                                    </div>
                                    <div className="font-mono text-xs text-slate-700 dark:text-slate-300">
                                        {block.hash.substring(0, 32)}...
                                    </div>
                                </div>
                                <div>
                                    <div className="text-slate-500 dark:text-slate-400 text-xs mb-1 flex items-center gap-1">
                                        <User className="w-3 h-3" />
                                        Proposer
                                    </div>
                                    <div className="font-mono text-xs text-blue-600 dark:text-blue-400">
                                        {block.proposer || 'Unknown'}
                                    </div>
                                </div>
                                <div className="col-span-2">
                                    <div className="text-slate-500 dark:text-slate-400 text-xs mb-1">
                                        Transactions
                                    </div>
                                    <div className="text-slate-700 dark:text-slate-300">
                                        {block.tx_count} transaction{block.tx_count !== 1 ? 's' : ''}
                                    </div>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </Dialog>
    );
};

export default BlocksDialog;

