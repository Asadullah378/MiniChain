import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, RefreshCw, ArrowRight, Wallet } from 'lucide-react';
import { getMempool } from '../api/client';
import usePoll from '../hooks/usePoll';
import clsx from 'clsx';

const Mempool = () => {
    const { data: mempool, loading, error } = usePoll(getMempool, 2000);

    if (loading && !mempool) return <div className="text-slate-400 animate-pulse text-center mt-20">Loading mempool...</div>;
    if (error) return <div className="text-red-400 text-center mt-20">Error loading mempool: {error.message}</div>;

    return (
        <div className="space-y-8">
            <div>
                <h1 className="text-4xl font-bold text-slate-900 dark:text-white tracking-tight">Mempool</h1>
                <p className="text-slate-500 dark:text-slate-400 mt-2 text-lg">Pending transactions waiting for confirmation</p>
            </div>

            <div className="w-full">
                {/* Mempool List - Full Width */}
                <div className="space-y-6">
                    <div className="bg-white/50 dark:bg-slate-900/50 backdrop-blur-xl border border-slate-200 dark:border-slate-800 rounded-2xl overflow-hidden">
                        <div className="p-6 border-b border-slate-200 dark:border-slate-800 flex justify-between items-center bg-slate-50 dark:bg-slate-900/50">
                            <div className="flex items-center gap-3">
                                <div className="p-2 bg-amber-500/10 rounded-lg">
                                    <Wallet className="w-5 h-5 text-amber-500" />
                                </div>
                                <span className="font-bold text-slate-900 dark:text-slate-200">Pending Queue</span>
                                <span className="px-2 py-0.5 rounded-full bg-slate-200 dark:bg-slate-800 text-slate-500 dark:text-slate-400 text-xs font-mono">
                                    {mempool.length}
                                </span>
                            </div>
                            <RefreshCw className="w-4 h-4 text-slate-500 animate-spin" />
                        </div>

                        <div className="divide-y divide-slate-200/50 dark:divide-slate-800/50">
                            <AnimatePresence mode="popLayout">
                                {mempool.length === 0 ? (
                                    <motion.div
                                        initial={{ opacity: 0 }}
                                        animate={{ opacity: 1 }}
                                        className="p-12 text-center"
                                    >
                                        <div className="w-16 h-16 bg-slate-100 dark:bg-slate-800/50 rounded-full flex items-center justify-center mx-auto mb-4">
                                            <Send className="w-8 h-8 text-slate-400 dark:text-slate-600" />
                                        </div>
                                        <h3 className="text-slate-400 dark:text-slate-300 font-medium">No pending transactions</h3>
                                        <p className="text-slate-500 text-sm mt-1">New transactions will appear here</p>
                                    </motion.div>
                                ) : (
                                    mempool.map((tx) => (
                                        <motion.div
                                            key={tx.id}
                                            initial={{ opacity: 0, height: 0, backgroundColor: "rgba(30, 41, 59, 0)" }}
                                            animate={{ opacity: 1, height: 'auto' }}
                                            exit={{ opacity: 0, height: 0 }}
                                            className="p-4 hover:bg-slate-50 dark:hover:bg-slate-800/30 transition-colors group"
                                        >
                                            <div className="flex items-center justify-between">
                                                <div className="flex items-center gap-4">
                                                    <div className="w-10 h-10 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-500 dark:text-slate-400 font-mono text-xs">
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
                                                    <div className="font-bold text-slate-900 dark:text-white text-lg">{tx.amount} <span className="text-sm text-slate-500 font-normal">MC</span></div>
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
            </div>
        </div>
    );
};

export default Mempool;
