import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, RefreshCw, AlertCircle, CheckCircle, ArrowRight } from 'lucide-react';
import { submitTransaction } from '../api/client';
import clsx from 'clsx';

const SendTransaction = () => {
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

    return (
        <div className="max-w-2xl mx-auto space-y-8">
            <div>
                <h1 className="text-4xl font-bold text-slate-900 dark:text-white tracking-tight">Send Transaction</h1>
                <p className="text-slate-500 dark:text-slate-400 mt-2 text-lg">Create and broadcast a new transaction to the network</p>
            </div>

            <div className="bg-white/50 dark:bg-slate-900/50 backdrop-blur-xl border border-slate-200 dark:border-slate-800 rounded-2xl p-8 shadow-sm">
                <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-8 flex items-center gap-3">
                    <div className="p-2 bg-blue-500/10 rounded-lg">
                        <Send className="w-6 h-6 text-blue-500" />
                    </div>
                    <span>Transaction Details</span>
                </h2>

                <form onSubmit={handleSubmit} className="space-y-6">
                    <div>
                        <label className="block text-sm font-medium text-slate-500 dark:text-slate-400 mb-2">Sender Address</label>
                        <input
                            type="text"
                            required
                            value={formData.sender}
                            onChange={(e) => setFormData({ ...formData, sender: e.target.value })}
                            className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl px-4 py-3.5 text-slate-900 dark:text-white placeholder:text-slate-400 dark:placeholder:text-slate-600 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all"
                            placeholder="e.g. alice"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-slate-500 dark:text-slate-400 mb-2">Recipient Address</label>
                        <input
                            type="text"
                            required
                            value={formData.recipient}
                            onChange={(e) => setFormData({ ...formData, recipient: e.target.value })}
                            className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl px-4 py-3.5 text-slate-900 dark:text-white placeholder:text-slate-400 dark:placeholder:text-slate-600 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all"
                            placeholder="e.g. bob"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-slate-500 dark:text-slate-400 mb-2">Amount (MC)</label>
                        <div className="relative">
                            <input
                                type="number"
                                required
                                min="0.1"
                                step="0.1"
                                value={formData.amount}
                                onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
                                className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl pl-4 pr-12 py-3.5 text-slate-900 dark:text-white placeholder:text-slate-400 dark:placeholder:text-slate-600 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all"
                                placeholder="0.00"
                            />
                            <div className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 text-sm font-medium pointer-events-none">
                                MC
                            </div>
                        </div>
                    </div>

                    <div className="pt-4">
                        <button
                            type="submit"
                            disabled={submitting}
                            className="w-full bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white font-bold py-4 px-6 rounded-xl transition-all shadow-lg shadow-blue-500/20 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 group text-lg"
                        >
                            {submitting ? (
                                <>
                                    <RefreshCw className="w-5 h-5 animate-spin" />
                                    <span>Processing...</span>
                                </>
                            ) : (
                                <>
                                    <span>Send Transaction</span>
                                    <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                                </>
                            )}
                        </button>
                    </div>

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
    );
};

export default SendTransaction;
