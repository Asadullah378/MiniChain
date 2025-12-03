import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, Clock, CheckCircle, XCircle, Hash, User, ArrowRight, Box } from 'lucide-react';
import { getTransactionDetails } from '../api/client';
import clsx from 'clsx';

const TransactionDetails = () => {
    const { txId } = useParams();
    const [transaction, setTransaction] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchTransaction = async () => {
            try {
                setLoading(true);
                const data = await getTransactionDetails(txId);
                setTransaction(data);
                setError(null);
            } catch (err) {
                console.error("Failed to fetch transaction:", err);
                setError(err);
            } finally {
                setLoading(false);
            }
        };

        if (txId) {
            fetchTransaction();
        }
    }, [txId]);

    if (loading) return <div className="text-slate-500 dark:text-slate-400 animate-pulse text-center mt-20">Loading transaction details...</div>;

    if (error) {
        return (
            <div className="text-center mt-20 space-y-4">
                <div className="text-red-400">Error loading transaction: {error.message || "Transaction not found"}</div>
                <Link to="/" className="text-blue-500 hover:text-blue-400 flex items-center justify-center gap-2">
                    <ArrowLeft className="w-4 h-4" />
                    Back to Dashboard
                </Link>
            </div>
        );
    }

    if (!transaction) return null;

    const isConfirmed = transaction.status === 'Confirmed';

    return (
        <div className="space-y-8 max-w-4xl mx-auto">
            <div className="flex items-center gap-4">
                <Link to={-1} className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors">
                    <ArrowLeft className="w-6 h-6 text-slate-500" />
                </Link>
                <div>
                    <h1 className="text-3xl font-bold text-slate-900 dark:text-white tracking-tight">Transaction Details</h1>
                    <p className="text-slate-500 dark:text-slate-400 mt-1 flex items-center gap-2 font-mono text-sm">
                        <Hash className="w-4 h-4" />
                        {transaction.id}
                    </p>
                </div>
            </div>

            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-white/50 dark:bg-slate-900/50 backdrop-blur-xl border border-slate-200 dark:border-slate-800 rounded-2xl overflow-hidden"
            >
                {/* Status Header */}
                <div className={clsx(
                    "p-6 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between",
                    isConfirmed ? "bg-emerald-500/5" : "bg-amber-500/5"
                )}>
                    <div className="flex items-center gap-3">
                        {isConfirmed ? (
                            <div className="p-2 bg-emerald-500/10 rounded-full">
                                <CheckCircle className="w-6 h-6 text-emerald-500" />
                            </div>
                        ) : (
                            <div className="p-2 bg-amber-500/10 rounded-full">
                                <Clock className="w-6 h-6 text-amber-500" />
                            </div>
                        )}
                        <div>
                            <div className={clsx("font-bold text-lg", isConfirmed ? "text-emerald-500" : "text-amber-500")}>
                                {transaction.status}
                            </div>
                            {isConfirmed && (
                                <div className="text-sm text-slate-500 flex items-center gap-1">
                                    Included in Block #{transaction.block_height}
                                </div>
                            )}
                        </div>
                    </div>
                    <div className="text-right">
                        <div className="text-sm text-slate-500">Timestamp</div>
                        <div className="font-medium text-slate-900 dark:text-slate-200">
                            {new Date(transaction.timestamp * 1000).toLocaleString()}
                        </div>
                    </div>
                </div>

                {/* Transaction Info */}
                <div className="p-8 space-y-8">
                    {/* Amount */}
                    <div className="text-center p-8 bg-slate-50 dark:bg-slate-950/30 rounded-2xl border border-slate-200 dark:border-slate-800/50">
                        <div className="text-sm text-slate-500 uppercase tracking-wider font-semibold mb-2">Amount Transferred</div>
                        <div className="text-5xl font-bold text-slate-900 dark:text-white">
                            {transaction.amount} <span className="text-2xl text-slate-400 font-normal">MC</span>
                        </div>
                    </div>

                    {/* Sender -> Recipient */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-center">
                        <div className="p-4 bg-slate-50 dark:bg-slate-950/30 rounded-xl border border-slate-200 dark:border-slate-800/50">
                            <div className="flex items-center gap-2 text-slate-500 mb-2 text-sm">
                                <User className="w-4 h-4" />
                                From
                            </div>
                            <div className="font-mono text-blue-500 bg-blue-500/10 px-2 py-1 rounded break-all">
                                {transaction.sender}
                            </div>
                        </div>

                        <div className="flex justify-center">
                            <div className="p-2 bg-slate-100 dark:bg-slate-800 rounded-full">
                                <ArrowRight className="w-6 h-6 text-slate-400" />
                            </div>
                        </div>

                        <div className="p-4 bg-slate-50 dark:bg-slate-950/30 rounded-xl border border-slate-200 dark:border-slate-800/50">
                            <div className="flex items-center gap-2 text-slate-500 mb-2 text-sm">
                                <User className="w-4 h-4" />
                                To
                            </div>
                            <div className="font-mono text-emerald-500 bg-emerald-500/10 px-2 py-1 rounded break-all">
                                {transaction.recipient}
                            </div>
                        </div>
                    </div>

                    {/* Additional Details */}
                    {isConfirmed && (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="p-4 bg-slate-50 dark:bg-slate-950/30 rounded-xl border border-slate-200 dark:border-slate-800/50 flex items-center justify-between">
                                <div className="flex items-center gap-2 text-slate-500">
                                    <Box className="w-4 h-4" />
                                    Block Height
                                </div>
                                <div className="font-mono font-bold text-slate-900 dark:text-white">
                                    #{transaction.block_height}
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </motion.div>
        </div>
    );
};

export default TransactionDetails;
