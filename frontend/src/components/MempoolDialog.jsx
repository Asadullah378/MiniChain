import React, { useState, useEffect } from 'react';
import { Clock, ArrowRight } from 'lucide-react';
import { getMempool, setApiBaseUrl, api } from '../api/client';
import Dialog from './Dialog';
import { Link } from 'react-router-dom';

const MempoolDialog = ({ isOpen, onClose, nodeUrl, nodeName }) => {
    const [mempool, setMempool] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (!isOpen) return;

        const fetchMempool = async () => {
            try {
                setLoading(true);
                setError(null);
                // Temporarily change API base URL
                const originalUrl = api.defaults.baseURL || window.location.origin;
                setApiBaseUrl(nodeUrl);
                const data = await getMempool();
                setMempool(data || []);
                setApiBaseUrl(originalUrl);
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };

        fetchMempool();
        const interval = setInterval(fetchMempool, 2000);
        return () => clearInterval(interval);
    }, [isOpen, nodeUrl]);

    return (
        <Dialog
            isOpen={isOpen}
            onClose={onClose}
            title={`Mempool - ${nodeName}`}
            size="lg"
        >
            {loading && mempool.length === 0 ? (
                <div className="text-center py-12 text-slate-500 dark:text-slate-400">
                    Loading mempool...
                </div>
            ) : error ? (
                <div className="text-center py-12 text-red-400">
                    Error: {error}
                </div>
            ) : mempool.length === 0 ? (
                <div className="text-center py-12">
                    <Clock className="w-16 h-16 mx-auto mb-4 text-slate-400 dark:text-slate-600" />
                    <p className="text-slate-500 dark:text-slate-400">No pending transactions</p>
                </div>
            ) : (
                <div className="logs-scrollbar space-y-2 max-h-[60vh] overflow-y-auto">
                    {mempool.map((tx) => (
                        <div
                            key={tx.id}
                            className="p-4 bg-slate-50 dark:bg-slate-800/50 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                        >
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-4 flex-1">
                                    <div className="flex items-center gap-2 text-sm">
                                        <span className="font-mono text-blue-600 dark:text-blue-400 bg-blue-100 dark:bg-blue-500/20 px-2 py-1 rounded">
                                            {tx.sender}
                                        </span>
                                        <ArrowRight className="w-4 h-4 text-slate-400" />
                                        <span className="font-mono text-emerald-600 dark:text-emerald-400 bg-emerald-100 dark:bg-emerald-500/20 px-2 py-1 rounded">
                                            {tx.recipient}
                                        </span>
                                    </div>
                                    <Link
                                        to={`/transaction/${tx.id}`}
                                        onClick={onClose}
                                        className="text-xs text-slate-500 dark:text-slate-400 font-mono hover:text-blue-500 dark:hover:text-blue-400"
                                    >
                                        {tx.id.substring(0, 16)}...
                                    </Link>
                                </div>
                                <div className="text-right">
                                    <div className="font-bold text-slate-900 dark:text-white">
                                        {tx.amount} <span className="text-sm text-slate-500 font-normal">MC</span>
                                    </div>
                                    <div className="text-xs text-slate-500 dark:text-slate-400">
                                        {new Date(tx.timestamp * 1000).toLocaleTimeString()}
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

export default MempoolDialog;

