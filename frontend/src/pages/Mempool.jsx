import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, RefreshCw, AlertCircle, CheckCircle, ArrowRight, Wallet } from 'lucide-react';
import { getMempool, submitTransaction } from '../api/client';
import usePoll from '../hooks/usePoll';
import clsx from 'clsx';

const Mempool = () => {
    const { data: mempool, loading, error } = usePoll(getMempool, 2000);
    const [formData, setFormData] = useState({ sender: '', recipient: '', amount: '' });
    const [submitting, setSubmitting] = useState(false);
    const [submitStatus, setSubmitStatus] = useState(null);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setSubmitting(true);
        setSubmitStatus(null);
        try {
            await submitTransaction({
                sender: formData.sender,
                recipient: formData.recipient,
                amount: Number(formData.amount),
            });
            setSubmitStatus({ type: 'success', message: 'Transaction submitted successfully!' });
            setFormData({ sender: '', recipient: '', amount: '' });
            setTimeout(() => setSubmitStatus(null), 3000);
        } catch (err) {
            setSubmitStatus({ type: 'error', message: 'Failed to submit transaction. It might be a duplicate.' });
        } finally {
            setSubmitting(false);
        }
    };

    if (loading && !mempool) return <div className="text-slate-400 animate-pulse text-center mt-20">Loading mempool...</div>;
    if (error) return <div className="text-red-400 text-center mt-20">Error loading mempool: {error.message}</div>;

    return (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div className="lg:col-span-2 space-y-6">
                <div>
                    <h1 className="text-4xl font-bold text-white tracking-tight">Mempool</h1>
                    <p className="text-slate-400 mt-2 text-lg">Pending transactions waiting for confirmation</p>
                </div>

                <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-800 rounded-2xl overflow-hidden">
                    <div className="p-6 border-b border-slate-800 flex justify-between items-center bg-slate-900/50">
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-amber-500/10 rounded-lg">
                                <Wallet className="w-5 h-5 text-amber-500" />
                            </div>
                            <span className="font-bold text-slate-200">Pending Queue</span>
                            <span className="px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 text-xs font-mono">
                                {mempool.length}
                            </span>
                        </div>
                        <RefreshCw className="w-4 h-4 text-slate-500 animate-spin" />
                    </div>

                    <div className="divide-y divide-slate-800/50">
                        <AnimatePresence mode="popLayout">
                            {mempool.length === 0 ? (
                                <motion.div
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    className="p-12 text-center"
                                >
                                    <div className="w-16 h-16 bg-slate-800/50 rounded-full flex items-center justify-center mx-auto mb-4">
                                        <Send className="w-8 h-8 text-slate-600" />
                                    </div>
                                    <h3 className="text-slate-300 font-medium">No pending transactions</h3>
                                    <p className="text-slate-500 text-sm mt-1">New transactions will appear here</p>
                                </motion.div>
                            ) : (
                                mempool.map((tx) => (
                                    <motion.div
                                        key={tx.id}
                                        initial={{ opacity: 0, height: 0, backgroundColor: "rgba(30, 41, 59, 0)" }}
                                        animate={{ opacity: 1, height: 'auto' }}
                                        exit={{ opacity: 0, height: 0 }}
                                        className="p-4 hover:bg-slate-800/30 transition-colors group"
                                    >
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center gap-4">
                                                <div className="w-10 h-10 rounded-full bg-slate-800 flex items-center justify-center text-slate-400 font-mono text-xs">
                                                    Tx
                                                </div>
                                                <div>
                                                    <div className="flex items-center gap-2 text-sm">
                                                        <span className="font-mono text-blue-400 bg-blue-500/10 px-1.5 py-0.5 rounded">{tx.sender}</span>
                                                        <ArrowRight className="w-3 h-3 text-slate-600" />
                                                        <span className="font-mono text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded">{tx.recipient}</span>
                                                    </div>
                                                    <p className="text-xs text-slate-500 mt-1 font-mono tracking-wide opacity-60 group-hover:opacity-100 transition-opacity">
                                                        ID: {tx.id.substring(0, 16)}...
                                                    </p>
                                                </div>
                                            </div>
                                            <div className="text-right">
                                                <div className="font-bold text-white text-lg">{tx.amount} <span className="text-sm text-slate-500 font-normal">MC</span></div>
                                                <div className="text-xs text-slate-500">
                                                    {new Date(tx.timestamp * 1000).toLocaleTimeString()}
                                                </div>
                                            </div>
                                        </div>
                                    </motion.div>
                                ))
                            )}
                        </AnimatePresence>
                    </div>
                </div>
            </div>

            <div className="space-y-6">
                <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-800 rounded-2xl p-6 sticky top-6">
                    <h2 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
                        <Send className="w-5 h-5 text-blue-500" />
                        <span>New Transaction</span>
                    </h2>

                    <form onSubmit={handleSubmit} className="space-y-5">
                        <div>
                            <label className="block text-sm font-medium text-slate-400 mb-1.5">Sender Address</label>
                            <input
                                type="text"
                                required
                                value={formData.sender}
                                onChange={(e) => setFormData({ ...formData, sender: e.target.value })}
                                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-white placeholder:text-slate-600 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all"
                                placeholder="e.g. alice"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-slate-400 mb-1.5">Recipient Address</label>
                            <input
                                type="text"
                                required
                                value={formData.recipient}
                                onChange={(e) => setFormData({ ...formData, recipient: e.target.value })}
                                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-white placeholder:text-slate-600 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all"
                                placeholder="e.g. bob"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-slate-400 mb-1.5">Amount (MC)</label>
                            <div className="relative">
                                <input
                                    type="number"
                                    required
                                    min="0.1"
                                    step="0.1"
                                    value={formData.amount}
                                    onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
                                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-white placeholder:text-slate-600 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all"
                                    placeholder="0.00"
                                />
                                <div className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 text-sm font-medium pointer-events-none">
                                    MC
                                </div>
                            </div>
                        </div>

                        <button
                            type="submit"
                            disabled={submitting}
                            className="w-full bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white font-bold py-3.5 px-4 rounded-xl transition-all shadow-lg shadow-blue-500/20 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 group"
                        >
                            {submitting ? (
                                <>
                                    <RefreshCw className="w-4 h-4 animate-spin" />
                                    <span>Processing...</span>
                                </>
                            ) : (
                                <>
                                    <span>Send Transaction</span>
                                    <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                                </>
                            )}
                        </button>

                        <AnimatePresence>
                            {submitStatus && (
                                <motion.div
                                    initial={{ opacity: 0, y: 10, height: 0 }}
                                    animate={{ opacity: 1, y: 0, height: 'auto' }}
                                    exit={{ opacity: 0, height: 0 }}
                                    className={clsx(
                                        "p-4 rounded-xl flex items-start gap-3 text-sm border",
                                        submitStatus.type === 'success'
                                            ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                                            : "bg-red-500/10 text-red-400 border-red-500/20"
                                    )}
                                >
                                    {submitStatus.type === 'success' ? <CheckCircle className="w-5 h-5 shrink-0" /> : <AlertCircle className="w-5 h-5 shrink-0" />}
                                    <span className="leading-relaxed">{submitStatus.message}</span>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </form>
                </div>
            </div>
        </div>
    );
};

export default Mempool;
