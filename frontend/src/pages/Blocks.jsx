import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Box, Clock, Hash, User, ArrowDown } from 'lucide-react';
import { getBlocks, getStatus } from '../api/client';
import usePoll from '../hooks/usePoll';
import clsx from 'clsx';

const BlockCard = ({ block, index, isLast }) => (
    <div className="relative pl-8 md:pl-0">
        {/* Connector Line */}
        {!isLast && (
            <div className="absolute left-8 md:left-1/2 top-full h-8 w-0.5 bg-slate-200 dark:bg-slate-800 -translate-x-1/2 z-0" />
        )}

        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            className="relative z-10 bg-white/50 dark:bg-slate-900/50 backdrop-blur-sm border border-slate-200 dark:border-slate-800 rounded-2xl p-6 hover:border-blue-500/30 transition-all duration-300 hover:shadow-lg hover:shadow-blue-500/5 group"
        >
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
                <div className="flex items-center space-x-4">
                    <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500/10 to-purple-500/10 flex items-center justify-center border border-slate-200 dark:border-slate-700/50 group-hover:border-blue-500/30 transition-colors">
                        <Box className="w-6 h-6 text-blue-400" />
                    </div>
                    <div>
                        <h3 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
                            Block #{block.height}
                            {index === 0 && (
                                <span className="px-2 py-0.5 rounded text-[10px] bg-blue-500 text-white font-bold uppercase tracking-wider">Latest</span>
                            )}
                        </h3>
                        <p className="text-sm text-slate-500 font-mono mt-1 flex items-center gap-1">
                            <Hash className="w-3 h-3" />
                            {block.hash.substring(0, 16)}...
                        </p>
                    </div>
                </div>

                <div className="flex items-center gap-4 text-sm text-slate-500 dark:text-slate-400 bg-slate-50 dark:bg-slate-950/50 px-4 py-2 rounded-lg border border-slate-200 dark:border-slate-800/50">
                    <div className="flex items-center gap-2">
                        <Clock className="w-4 h-4 text-slate-500" />
                        <span>{new Date(block.timestamp * 1000).toLocaleString()}</span>
                    </div>
                    <div className="w-px h-4 bg-slate-300 dark:bg-slate-700" />
                    <div className="font-medium text-slate-600 dark:text-slate-300">
                        {block.tx_count} txs
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                <div className="p-3 bg-slate-50 dark:bg-slate-950/30 rounded-xl border border-slate-200 dark:border-slate-800/50 flex items-center justify-between group-hover:bg-slate-100 dark:group-hover:bg-slate-900/50 transition-colors">
                    <span className="flex items-center gap-2 text-slate-500" title="The node ID of the validator that created this block">
                        <User className="w-4 h-4" />
                        Proposer
                    </span>
                    <span className="font-mono text-blue-400 bg-blue-500/10 px-2 py-1 rounded text-xs">
                        {block.proposer || 'Unknown'}
                    </span>
                </div>

                <div className="p-3 bg-slate-50 dark:bg-slate-950/30 rounded-xl border border-slate-200 dark:border-slate-800/50 flex items-center justify-between group-hover:bg-slate-100 dark:group-hover:bg-slate-900/50 transition-colors">
                    <span className="flex items-center gap-2 text-slate-500">
                        <Hash className="w-4 h-4" />
                        Prev Hash
                    </span>
                    <span className="font-mono text-slate-500 dark:text-slate-400 text-xs">
                        {block.prev_hash.substring(0, 12)}...
                    </span>
                </div>
            </div>
        </motion.div>

        {/* Mobile Connector Dot */}
        <div className="absolute left-0 top-1/2 -translate-y-1/2 w-16 flex justify-center md:hidden">
            <div className="w-0.5 h-full bg-slate-200 dark:bg-slate-800 absolute left-8 -translate-x-1/2" />
            <div className="w-3 h-3 rounded-full bg-slate-200 dark:bg-slate-800 border-2 border-slate-50 dark:border-slate-950 z-10 relative" />
        </div>
    </div>
);

const Blocks = () => {
    const [blocks, setBlocks] = React.useState([]);
    const [loading, setLoading] = React.useState(true);
    const [error, setError] = React.useState(null);

    const fetchBlocks = async () => {
        try {
            // 1. Get current height
            const status = await getStatus();
            const height = status.height;

            // 2. Calculate range for latest 20 blocks
            // If height is 100, we want 81-100 (or 80-99 depending on indexing).
            // API is 0-indexed usually.
            // If height is 5 (blocks 0,1,2,3,4), we want 0-5.
            // Let's assume we want the last 20.
            const limit = 20;
            const start = Math.max(0, height - limit + 1);

            // 3. Fetch blocks
            const newBlocks = await getBlocks(start, limit);

            // 4. Reverse to show newest first
            setBlocks([...newBlocks].reverse());
            setError(null);
        } catch (err) {
            console.error("Failed to fetch blocks:", err);
            setError(err);
        } finally {
            setLoading(false);
        }
    };

    usePoll(fetchBlocks, 3000);

    if (loading && blocks.length === 0) return <div className="text-slate-500 dark:text-slate-400 animate-pulse text-center mt-20">Loading blockchain...</div>;
    if (error && blocks.length === 0) return <div className="text-red-400 text-center mt-20">Error loading blocks: {error.message}</div>;

    return (
        <div className="space-y-8">
            <div>
                <h1 className="text-4xl font-bold text-slate-900 dark:text-white tracking-tight">Blockchain Explorer</h1>
                <p className="text-slate-500 dark:text-slate-400 mt-2 text-lg">Immutable ledger history</p>
            </div>

            <div className="space-y-4 w-full max-w-full pb-12">
                <AnimatePresence>
                    {blocks.map((block, index) => (
                        <BlockCard
                            key={block.hash}
                            block={block}
                            index={index}
                            isLast={index === blocks.length - 1}
                        />
                    ))}
                </AnimatePresence>
            </div>
        </div>
    );
};

export default Blocks;
