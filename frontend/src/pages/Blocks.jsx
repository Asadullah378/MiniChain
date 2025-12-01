import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Box, ArrowRight, Clock, Hash, User } from 'lucide-react';
import { getBlocks } from '../api/client';
import usePoll from '../hooks/usePoll';

const BlockCard = ({ block, index }) => (
    <motion.div
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: index * 0.1 }}
        className="bg-gray-900 border border-gray-800 rounded-xl p-6 hover:border-blue-500/50 transition-colors group"
    >
        <div className="flex items-start justify-between mb-4">
            <div className="flex items-center space-x-3">
                <div className="p-2 bg-blue-500/10 rounded-lg text-blue-500 group-hover:bg-blue-500 group-hover:text-white transition-colors">
                    <Box className="w-6 h-6" />
                </div>
                <div>
                    <h3 className="text-lg font-bold text-white">Block #{block.height}</h3>
                    <p className="text-xs text-gray-500 font-mono">{block.block_hash.substring(0, 16)}...</p>
                </div>
            </div>
            <div className="text-right">
                <div className="flex items-center text-gray-400 text-sm space-x-1">
                    <Clock className="w-4 h-4" />
                    <span>{new Date(block.timestamp * 1000).toLocaleTimeString()}</span>
                </div>
                <p className="text-xs text-gray-500 mt-1">{block.tx_count} transactions</p>
            </div>
        </div>

        <div className="space-y-2 text-sm text-gray-400">
            <div className="flex items-center justify-between p-2 bg-gray-800/50 rounded">
                <span className="flex items-center space-x-2">
                    <User className="w-4 h-4" />
                    <span>Proposer</span>
                </span>
                <span className="font-mono text-blue-400">{block.proposer_id}</span>
            </div>
            <div className="flex items-center justify-between p-2 bg-gray-800/50 rounded">
                <span className="flex items-center space-x-2">
                    <Hash className="w-4 h-4" />
                    <span>Prev Hash</span>
                </span>
                <span className="font-mono text-xs">{block.prev_hash.substring(0, 16)}...</span>
            </div>
        </div>
    </motion.div>
);

const Blocks = () => {
    const { data: blocks, loading, error } = usePoll(() => getBlocks(0, 20), 3000);

    if (loading && !blocks) return <div className="text-white">Loading blockchain...</div>;
    if (error) return <div className="text-red-500">Error loading blocks: {error.message}</div>;

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold text-white">Blockchain Explorer</h1>
                <p className="text-gray-400 mt-2">View the most recent blocks added to the chain</p>
            </div>

            <div className="grid grid-cols-1 gap-4">
                <AnimatePresence>
                    {blocks.map((block, index) => (
                        <BlockCard key={block.block_hash} block={block} index={index} />
                    ))}
                </AnimatePresence>
            </div>
        </div>
    );
};

export default Blocks;
