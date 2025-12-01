import React from 'react';
import { motion } from 'framer-motion';
import { Server, Activity, Users, Database } from 'lucide-react';
import { getStatus } from '../api/client';
import usePoll from '../hooks/usePoll';

const StatCard = ({ icon: Icon, label, value, color }) => (
    <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-gray-900 border border-gray-800 p-6 rounded-xl flex items-center space-x-4 hover:border-gray-700 transition-colors"
    >
        <div className={`p-3 rounded-lg bg-opacity-10 ${color.bg} ${color.text}`}>
            <Icon className="w-6 h-6" />
        </div>
        <div>
            <p className="text-gray-400 text-sm font-medium">{label}</p>
            <p className="text-2xl font-bold text-white mt-1">{value}</p>
        </div>
    </motion.div>
);

const Dashboard = () => {
    const { data: status, loading, error } = usePoll(getStatus, 2000);

    if (loading && !status) return <div className="text-white">Loading node status...</div>;
    if (error) return <div className="text-red-500">Error connecting to node: {error.message}</div>;

    return (
        <div className="space-y-8">
            <div>
                <h1 className="text-3xl font-bold text-white">Node Status</h1>
                <p className="text-gray-400 mt-2">Real-time overview of your MiniChain node</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <StatCard
                    icon={Server}
                    label="Node ID"
                    value={status.node_id}
                    color={{ bg: 'bg-blue-500', text: 'text-blue-500' }}
                />
                <StatCard
                    icon={Database}
                    label="Block Height"
                    value={status.height}
                    color={{ bg: 'bg-green-500', text: 'text-green-500' }}
                />
                <StatCard
                    icon={Users}
                    label="Peers Connected"
                    value={status.peers_count}
                    color={{ bg: 'bg-purple-500', text: 'text-purple-500' }}
                />
                <StatCard
                    icon={Activity}
                    label="Mempool Size"
                    value={status.mempool_size}
                    color={{ bg: 'bg-orange-500', text: 'text-orange-500' }}
                />
            </div>

            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.2 }}
                className="bg-gray-900 border border-gray-800 rounded-xl p-6"
            >
                <h2 className="text-xl font-bold text-white mb-4">Consensus Status</h2>
                <div className="flex items-center space-x-2">
                    <span className="text-gray-400">Current Leader:</span>
                    <span className="px-3 py-1 bg-blue-500/10 text-blue-400 rounded-full text-sm font-mono">
                        {status.leader || 'None'}
                    </span>
                </div>
            </motion.div>
        </div>
    );
};

export default Dashboard;
