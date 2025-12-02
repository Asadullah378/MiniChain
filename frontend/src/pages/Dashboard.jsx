import React from 'react';
import { motion } from 'framer-motion';
import { Server, Activity, Users, Database, ShieldCheck } from 'lucide-react';
import { getStatus } from '../api/client';
import usePoll from '../hooks/usePoll';
import clsx from 'clsx';

const StatCard = ({ icon: Icon, label, value, color, delay }) => (
    <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: delay * 0.1 }}
        className="relative overflow-hidden bg-white/50 dark:bg-slate-900/50 backdrop-blur-xl border border-slate-200 dark:border-slate-800 p-6 rounded-2xl hover:border-slate-300 dark:hover:border-slate-700 transition-all duration-300 group"
    >
        <div className={clsx("absolute top-0 right-0 p-20 rounded-full blur-3xl opacity-5 -translate-y-1/2 translate-x-1/2 transition-opacity group-hover:opacity-10", color.bg)} />

        <div className="flex items-start justify-between relative z-10">
            <div>
                <p className="text-slate-500 dark:text-slate-400 text-sm font-medium tracking-wide uppercase">{label}</p>
                <p className="text-3xl font-bold text-slate-900 dark:text-white mt-2 tracking-tight">{value}</p>
            </div>
            <div className={clsx("p-3 rounded-xl bg-opacity-10 ring-1 ring-inset", color.bg, color.text, color.ring)}>
                <Icon className="w-6 h-6" />
            </div>
        </div>
    </motion.div>
);

const Dashboard = () => {
    const { data: status, loading, error } = usePoll(getStatus, 2000);

    if (loading && !status) return (
        <div className="flex items-center justify-center h-64 text-slate-500 dark:text-slate-400 animate-pulse">
            Connecting to node...
        </div>
    );

    if (error) return (
        <div className="p-6 bg-red-500/10 border border-red-500/20 rounded-2xl text-red-400 flex items-center space-x-3">
            <Activity className="w-6 h-6" />
            <span>Error connecting to node: {error.message}</span>
        </div>
    );

    return (
        <div className="space-y-8">
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                <div>
                    <h1 className="text-4xl font-bold text-slate-900 dark:text-white tracking-tight">
                        Node Status
                    </h1>
                    <p className="text-slate-500 dark:text-slate-400 mt-2 text-lg">
                        Real-time overview of your distributed node
                    </p>
                </div>
                <div className="px-4 py-2 bg-white dark:bg-slate-900 rounded-full border border-slate-200 dark:border-slate-800 flex items-center space-x-2">
                    <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                    <span className="text-sm font-medium text-slate-600 dark:text-slate-300">System Operational</span>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <StatCard
                    delay={0}
                    icon={Server}
                    label="Node ID"
                    value={status.node_id}
                    color={{ bg: 'bg-blue-500', text: 'text-blue-400', ring: 'ring-blue-500/20' }}
                />
                <StatCard
                    delay={1}
                    icon={Database}
                    label="Block Height"
                    value={status.height}
                    color={{ bg: 'bg-emerald-500', text: 'text-emerald-400', ring: 'ring-emerald-500/20' }}
                />
                <StatCard
                    delay={2}
                    icon={Users}
                    label="Peers Connected"
                    value={status.peers_count}
                    color={{ bg: 'bg-violet-500', text: 'text-violet-400', ring: 'ring-violet-500/20' }}
                />
                <StatCard
                    delay={3}
                    icon={Activity}
                    label="Mempool Size"
                    value={status.mempool_size}
                    color={{ bg: 'bg-amber-500', text: 'text-amber-400', ring: 'ring-amber-500/20' }}
                />
            </div>

            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
                className="bg-white/50 dark:bg-slate-900/50 backdrop-blur-xl border border-slate-200 dark:border-slate-800 rounded-2xl p-8 relative overflow-hidden"
            >
                <div className="absolute top-0 right-0 w-64 h-64 bg-blue-500/5 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />

                <div className="relative z-10">
                    <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-6 flex items-center space-x-2">
                        <ShieldCheck className="w-6 h-6 text-blue-400" />
                        <span>Consensus Status</span>
                    </h2>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                        <div className="space-y-2">
                            <span className="text-slate-500 text-sm uppercase tracking-wider font-medium">Current Leader</span>
                            <div className="flex items-center space-x-3">
                                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-bold">
                                    {status.leader ? status.leader[0].toUpperCase() : '?'}
                                </div>
                                <span className="text-xl font-mono text-slate-900 dark:text-white">{status.leader || 'None'}</span>
                            </div>
                        </div>

                        <div className="space-y-2">
                            <span className="text-slate-500 text-sm uppercase tracking-wider font-medium">Your Role</span>
                            <div className="flex items-center space-x-2">
                                <span className={clsx(
                                    "px-4 py-2 rounded-lg font-bold text-sm border",
                                    status.leader === status.node_id
                                        ? "bg-blue-500/10 text-blue-400 border-blue-500/20"
                                        : "bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 border-slate-200 dark:border-slate-700"
                                )}>
                                    {status.leader === status.node_id ? 'LEADER' : 'FOLLOWER'}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>
            </motion.div>
        </div>
    );
};

export default Dashboard;
