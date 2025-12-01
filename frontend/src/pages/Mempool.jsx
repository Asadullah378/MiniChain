import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, RefreshCw, AlertCircle, CheckCircle } from 'lucide-react';
import { getMempool, submitTransaction } from '../api/client';
import usePoll from '../hooks/usePoll';

const Mempool = () => {
    const { data: mempool, loading, error } = usePoll(getMempool, 2000);
    const [formData, setFormData] = useState({ recipient: '', amount: '' });
    const [submitting, setSubmitting] = useState(false);
    const [submitStatus, setSubmitStatus] = useState(null);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setSubmitting(true);
        setSubmitStatus(null);
        try {
            await submitTransaction({
                sender: 'frontend-user', // Hardcoded for demo
                recipient: formData.recipient,
                amount: Number(formData.amount),
            });
            setSubmitStatus({ type: 'success', message: 'Transaction submitted!' });
            setFormData({ recipient: '', amount: '' });
        } catch (err) {
            setSubmitStatus({ type: 'error', message: 'Failed to submit transaction' });
        } finally {
            setSubmitting(false);
        }
    };

    if (loading && !mempool) return <div className="text-white">Loading mempool...</div>;
    if (error) return <div className="text-red-500">Error loading mempool: {error.message}</div>;

    return (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div className="lg:col-span-2 space-y-6">
                <div>
                    <h1 className="text-3xl font-bold text-white">Mempool</h1>
                    <p className="text-gray-400 mt-2">Pending transactions waiting to be confirmed</p>
                </div>

                <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
                    <div className="p-4 border-b border-gray-800 flex justify-between items-center">
                        <span className="font-medium text-gray-300">Pending Queue ({mempool.length})</span>
                        <RefreshCw className="w-4 h-4 text-gray-500 animate-spin" />
                    </div>
                    <div className="divide-y divide-gray-800">
                        <AnimatePresence>
                            {mempool.length === 0 ? (
                                <div className="p-8 text-center text-gray-500">No pending transactions</div>
                            ) : (
                                mempool.map((tx) => (
                                    <motion.div
                                        key={tx.id}
                                        initial={{ opacity: 0, height: 0 }}
                                        animate={{ opacity: 1, height: 'auto' }}
                                        exit={{ opacity: 0, height: 0 }}
                                        className="p-4 hover:bg-gray-800/50 transition-colors"
                                    >
                                        <div className="flex justify-between items-start">
                                            <div>
                                                <div className="flex items-center space-x-2">
                                                    <span className="text-blue-400 font-mono">{tx.sender}</span>
                                                    <span className="text-gray-500">→</span>
                                                    <span className="text-green-400 font-mono">{tx.recipient}</span>
                                                </div>
                                                <p className="text-xs text-gray-500 mt-1 font-mono">{tx.id}</p>
                                            </div>
                                            <div className="font-bold text-white">{tx.amount} MC</div>
                                        </div>
                                    </motion.div>
                                ))
                            )}
                        </AnimatePresence>
                    </div>
                </div>
            </div>

            <div className="space-y-6">
                <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
                    <h2 className="text-xl font-bold text-white mb-4 flex items-center space-x-2">
                        <Send className="w-5 h-5 text-blue-500" />
                        <span>New Transaction</span>
                    </h2>

                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-400 mb-1">Recipient</label>
                            <input
                                type="text"
                                required
                                value={formData.recipient}
                                onChange={(e) => setFormData({ ...formData, recipient: e.target.value })}
                                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500 transition-colors"
                                placeholder="Enter recipient ID"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-400 mb-1">Amount</label>
                            <input
                                type="number"
                                required
                                min="1"
                                value={formData.amount}
                                onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
                                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500 transition-colors"
                                placeholder="0.00"
                            />
                        </div>

                        <button
                            type="submit"
                            disabled={submitting}
                            className="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-2 px-4 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {submitting ? 'Sending...' : 'Send Transaction'}
                        </button>

                        {submitStatus && (
                            <motion.div
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                className={`p-3 rounded-lg flex items-center space-x-2 text-sm ${submitStatus.type === 'success' ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'
                                    }`}
                            >
                                {submitStatus.type === 'success' ? <CheckCircle className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
                                <span>{submitStatus.message}</span>
                            </motion.div>
                        )}
                    </form>
                </div>
            </div>
        </div>
    );
};

export default Mempool;
