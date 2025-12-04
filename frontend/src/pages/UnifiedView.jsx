import React, { useState, useEffect, useRef, useCallback } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { 
    Server, Database, Users, Activity, Send, Layers, Clock, 
    Terminal, Pause, Play, Filter, Download, X, ChevronDown, ChevronUp, ArrowLeft, Maximize2, Minimize2 
} from 'lucide-react';
import { getStatus, setApiBaseUrl, api } from '../api/client';
import { nodes } from '../nodeConfig';
import usePoll from '../hooks/usePoll';
import MempoolDialog from '../components/MempoolDialog';
import BlocksDialog from '../components/BlocksDialog';
import SendTransactionDialog from '../components/SendTransactionDialog';
import clsx from 'clsx';

const LogLevelBadge = ({ level }) => {
    const colorClasses = {
        DEBUG: 'text-cyan-600 dark:text-cyan-400 bg-cyan-100 dark:bg-cyan-500/20',
        INFO: 'text-blue-600 dark:text-blue-400 bg-blue-100 dark:bg-blue-500/20',
        WARNING: 'text-amber-600 dark:text-amber-400 bg-amber-100 dark:bg-amber-500/20',
        ERROR: 'text-red-600 dark:text-red-400 bg-red-100 dark:bg-red-500/20',
        CRITICAL: 'text-red-700 dark:text-red-500 bg-red-200 dark:bg-red-600/30',
        UNKNOWN: 'text-slate-600 dark:text-slate-400 bg-slate-100 dark:bg-slate-500/20',
    };

    return (
        <span
            className={clsx(
                'px-1.5 py-0.5 rounded text-[10px] font-mono font-bold',
                colorClasses[level] || colorClasses.UNKNOWN
            )}
        >
            {level}
        </span>
    );
};

const LogLine = ({ entry }) => {
    const isError = entry.level === 'ERROR' || entry.level === 'CRITICAL';
    const isWarning = entry.level === 'WARNING';

    return (
        <div
            className={clsx(
                'font-mono text-xs leading-relaxed px-2 py-0.5 transition-colors text-[10px]',
                'hover:bg-slate-100 dark:hover:bg-slate-800/50',
                isError && 'bg-red-50 dark:bg-red-500/5 border-l-2 border-red-400 dark:border-red-500/50',
                isWarning && !isError && 'bg-amber-50 dark:bg-amber-500/5 border-l-2 border-amber-400 dark:border-amber-500/30'
            )}
        >
            <div className="flex items-start gap-2">
                <span className="text-slate-500 dark:text-slate-500 flex-shrink-0 w-16 text-right text-[9px]">
                    {entry.timestamp ? entry.timestamp.split(' ')[1] : '--:--'}
                </span>
                <div className="flex-shrink-0">
                    <LogLevelBadge level={entry.level} />
                </div>
                <span className={clsx(
                    'flex-1 break-words truncate',
                    isError
                        ? 'text-red-700 dark:text-red-300'
                        : isWarning
                        ? 'text-amber-700 dark:text-amber-300'
                        : 'text-slate-800 dark:text-slate-200'
                )}>
                    {entry.message}
                </span>
            </div>
        </div>
    );
};

const NodePanel = ({ node, index }) => {
    const [nodeStatus, setNodeStatus] = useState(null);
    const [logs, setLogs] = useState([]);
    const [isConnected, setIsConnected] = useState(false);
    const [isPaused, setIsPaused] = useState(false);
    const [showMempool, setShowMempool] = useState(false);
    const [showBlocks, setShowBlocks] = useState(false);
    const [showSendTx, setShowSendTx] = useState(false);
    const [isFullscreen, setIsFullscreen] = useState(false);
    const eventSourceRef = useRef(null);
    const containerRef = useRef(null);
    const fullscreenContainerRef = useRef(null);

    // Fetch status
    const fetchStatus = useCallback(async () => {
        try {
            const originalUrl = api.defaults.baseURL || window.location.origin;
            setApiBaseUrl(node.url);
            const status = await getStatus();
            setNodeStatus(status);
            setApiBaseUrl(originalUrl);
            return status;
        } catch (err) {
            console.error(`Error fetching status for ${node.name}:`, err);
            return null;
        }
    }, [node.url, node.name]);

    const { data: statusData } = usePoll(fetchStatus, 2000);

    useEffect(() => {
        if (statusData) {
            setNodeStatus(statusData);
        }
    }, [statusData]);

    // SSE for logs
    useEffect(() => {
        if (isPaused) return;

        let initialLogsBatch = [];
        let initialBatchTimeout = null;
        let initialBatchSet = false; // Flag to track if initial batch has been set

        const connectSSE = () => {
            try {
                const url = `${node.url}/logs/stream`;
                const eventSource = new EventSource(url);
                eventSourceRef.current = eventSource;

                eventSource.onopen = () => {
                    setIsConnected(true);
                    setLogs([]);
                    initialLogsBatch = [];
                    initialBatchSet = false;
                };

                eventSource.onmessage = (event) => {
                    if (event.data.startsWith(':')) return;

                    try {
                        const entry = JSON.parse(event.data);
                        if (!entry.error) {
                            // Collect initial batch (first 50 logs) and add them all at once
                            if (!initialBatchSet && initialLogsBatch.length < 50) {
                                initialLogsBatch.push(entry);
                                
                                if (initialBatchTimeout) {
                                    clearTimeout(initialBatchTimeout);
                                }
                                
                                // Wait a bit to collect the initial batch, then set them all at once
                                initialBatchTimeout = setTimeout(() => {
                                    if (initialLogsBatch.length > 0 && !initialBatchSet) {
                                        // Backend sends newest first, so we keep that order
                                        setLogs([...initialLogsBatch]);
                                        initialLogsBatch = [];
                                        initialBatchSet = true; // Mark as set so we never overwrite again
                                        
                                        // Scroll to top after initial batch (for both regular and fullscreen containers)
                                        const currentContainer = isFullscreen ? fullscreenContainerRef.current : containerRef.current;
                                        if (currentContainer) {
                                            currentContainer.scrollTop = 0;
                                        }
                                    }
                                }, 500);
                            } else {
                                // After initial batch is set, add new logs normally to existing logs
                                setLogs((prev) => {
                                    const newLogs = [entry, ...prev];
                                    return newLogs.slice(0, 100); // Keep last 100 logs per node
                                });

                                // Auto-scroll to top if at top (for both regular and fullscreen containers)
                                const currentContainer = isFullscreen ? fullscreenContainerRef.current : containerRef.current;
                                if (currentContainer && currentContainer.scrollTop < 50) {
                                    requestAnimationFrame(() => {
                                        if (currentContainer) {
                                            currentContainer.scrollTop = 0;
                                        }
                                    });
                                }
                            }
                        }
                    } catch (err) {
                        console.error('Error parsing log entry:', err);
                    }
                };

                eventSource.onerror = () => {
                    setIsConnected(false);
                    setTimeout(() => {
                        if (eventSourceRef.current) {
                            eventSourceRef.current.close();
                        }
                        connectSSE();
                    }, 3000);
                };
            } catch (err) {
                setIsConnected(false);
            }
        };

        connectSSE();

        return () => {
            if (initialBatchTimeout) {
                clearTimeout(initialBatchTimeout);
            }
            if (eventSourceRef.current) {
                eventSourceRef.current.close();
            }
        };
    }, [node.url, isPaused, isFullscreen]);

    const handleClearLogs = () => {
        setLogs([]);
    };

    return (
        <div className="flex flex-col h-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg overflow-hidden">
            {/* Header */}
            <div className="bg-slate-50 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 px-4 py-3">
                <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                        <div className={clsx(
                            'w-2 h-2 rounded-full',
                            isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'
                        )} />
                        <h3 className="font-bold text-slate-900 dark:text-white">{node.name}</h3>
                    </div>
                    <div className="flex items-center gap-1">
                        <button
                            onClick={() => setIsFullscreen(true)}
                            className="p-1.5 hover:bg-slate-200 dark:hover:bg-slate-700 rounded text-xs"
                            title="Fullscreen logs"
                        >
                            <Maximize2 className="w-3.5 h-3.5 text-slate-600 dark:text-slate-400" />
                        </button>
                        <button
                            onClick={() => setIsPaused(!isPaused)}
                            className="p-1.5 hover:bg-slate-200 dark:hover:bg-slate-700 rounded text-xs"
                            title={isPaused ? 'Resume' : 'Pause'}
                        >
                            {isPaused ? (
                                <Play className="w-3.5 h-3.5 text-slate-600 dark:text-slate-400" />
                            ) : (
                                <Pause className="w-3.5 h-3.5 text-slate-600 dark:text-slate-400" />
                            )}
                        </button>
                        <button
                            onClick={handleClearLogs}
                            className="p-1.5 hover:bg-slate-200 dark:hover:bg-slate-700 rounded text-xs"
                            title="Clear logs"
                        >
                            <X className="w-3.5 h-3.5 text-slate-600 dark:text-slate-400" />
                        </button>
                    </div>
                </div>
                <p className="text-xs text-slate-500 dark:text-slate-400 font-mono">{node.url}</p>
            </div>

            {/* Status Cards */}
            <div className="p-3 bg-slate-50 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-700 grid grid-cols-2 gap-2">
                <div className="bg-white dark:bg-slate-900 p-2 rounded border border-slate-200 dark:border-slate-700">
                    <div className="text-[10px] text-slate-500 dark:text-slate-400 uppercase">Node ID</div>
                    <div className="text-xs font-mono font-bold text-slate-900 dark:text-white truncate" title={nodeStatus?.node_id}>
                        {nodeStatus?.node_id || '--'}
                    </div>
                </div>
                <div className="bg-white dark:bg-slate-900 p-2 rounded border border-slate-200 dark:border-slate-700">
                    <div className="text-[10px] text-slate-500 dark:text-slate-400 uppercase">Height</div>
                    <div className="text-xs font-bold text-slate-900 dark:text-white">
                        {nodeStatus?.height ?? '--'}
                    </div>
                </div>
                <div className="bg-white dark:bg-slate-900 p-2 rounded border border-slate-200 dark:border-slate-700">
                    <div className="text-[10px] text-slate-500 dark:text-slate-400 uppercase">Peers</div>
                    <div className="text-xs font-bold text-slate-900 dark:text-white">
                        {nodeStatus?.peers ?? '--'}
                    </div>
                </div>
                <div className="bg-white dark:bg-slate-900 p-2 rounded border border-slate-200 dark:border-slate-700">
                    <div className="text-[10px] text-slate-500 dark:text-slate-400 uppercase">Mempool</div>
                    <div className="text-xs font-bold text-slate-900 dark:text-white">
                        {nodeStatus?.mempool_size ?? '--'}
                    </div>
                </div>
            </div>

            {/* Action Buttons */}
            <div className="p-2 bg-slate-50 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-700 flex gap-2">
                <button
                    onClick={() => setShowMempool(true)}
                    className="flex-1 px-2 py-1.5 bg-blue-100 dark:bg-blue-500/20 text-blue-700 dark:text-blue-400 rounded text-xs font-medium hover:bg-blue-200 dark:hover:bg-blue-500/30 transition-colors flex items-center justify-center gap-1"
                >
                    <Clock className="w-3 h-3" />
                    Mempool
                </button>
                <button
                    onClick={() => setShowBlocks(true)}
                    className="flex-1 px-2 py-1.5 bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400 rounded text-xs font-medium hover:bg-emerald-200 dark:hover:bg-emerald-500/30 transition-colors flex items-center justify-center gap-1"
                >
                    <Layers className="w-3 h-3" />
                    Blocks
                </button>
                <button
                    onClick={() => setShowSendTx(true)}
                    className="flex-1 px-2 py-1.5 bg-purple-100 dark:bg-purple-500/20 text-purple-700 dark:text-purple-400 rounded text-xs font-medium hover:bg-purple-200 dark:hover:bg-purple-500/30 transition-colors flex items-center justify-center gap-1"
                >
                    <Send className="w-3 h-3" />
                    Send
                </button>
            </div>

            {/* Logs */}
            <div
                ref={containerRef}
                className="logs-scrollbar flex-1 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 font-mono text-xs overflow-y-auto"
            >
                {logs.length === 0 ? (
                    <div className="flex items-center justify-center h-full text-slate-400 dark:text-slate-600 text-xs">
                        Waiting for logs...
                    </div>
                ) : (
                    <div className="py-1">
                        {logs.map((entry, idx) => (
                            <LogLine key={`${entry.timestamp}-${idx}-${entry.raw}`} entry={entry} />
                        ))}
                    </div>
                )}
            </div>

            {/* Footer */}
            <div className="bg-slate-50 dark:bg-slate-800 border-t border-slate-200 dark:border-slate-700 px-3 py-1.5 flex items-center justify-between text-[10px] text-slate-600 dark:text-slate-400">
                <span className="font-mono">{logs.length} logs</span>
                <span className="font-mono">{isPaused ? '⏸' : '▶'}</span>
            </div>

            {/* Fullscreen Logs Modal */}
            {isFullscreen && (
                <div className="fixed inset-0 z-50 bg-slate-900 dark:bg-black flex flex-col">
                    {/* Header */}
                    <div className="bg-slate-800 dark:bg-slate-900 border-b border-slate-700 px-6 py-4 flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className={clsx(
                                'w-2 h-2 rounded-full',
                                isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'
                            )} />
                            <h2 className="text-xl font-bold text-white">{node.name} - Logs</h2>
                            <span className="text-sm text-slate-400 font-mono">{node.url}</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <button
                                onClick={() => setIsPaused(!isPaused)}
                                className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-white rounded text-sm flex items-center gap-2"
                                title={isPaused ? 'Resume' : 'Pause'}
                            >
                                {isPaused ? (
                                    <>
                                        <Play className="w-4 h-4" />
                                        <span>Resume</span>
                                    </>
                                ) : (
                                    <>
                                        <Pause className="w-4 h-4" />
                                        <span>Pause</span>
                                    </>
                                )}
                            </button>
                            <button
                                onClick={handleClearLogs}
                                className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-white rounded text-sm flex items-center gap-2"
                                title="Clear logs"
                            >
                                <X className="w-4 h-4" />
                                <span>Clear</span>
                            </button>
                            <button
                                onClick={() => setIsFullscreen(false)}
                                className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-white rounded text-sm flex items-center gap-2"
                                title="Exit fullscreen"
                            >
                                <Minimize2 className="w-4 h-4" />
                                <span>Exit Fullscreen</span>
                            </button>
                        </div>
                    </div>

                    {/* Logs Container */}
                    <div
                        ref={fullscreenContainerRef}
                        className="logs-scrollbar flex-1 bg-slate-950 dark:bg-black text-slate-100 font-mono text-sm overflow-y-auto"
                    >
                        {logs.length === 0 ? (
                            <div className="flex items-center justify-center h-full text-slate-500 text-sm">
                                Waiting for logs...
                            </div>
                        ) : (
                            <div className="py-2">
                                {logs.map((entry, idx) => (
                                    <div
                                        key={`${entry.timestamp}-${idx}-${entry.raw}`}
                                        className={clsx(
                                            'font-mono text-sm leading-relaxed px-6 py-1.5 transition-colors',
                                            'hover:bg-slate-800/50',
                                            (entry.level === 'ERROR' || entry.level === 'CRITICAL') && 'bg-red-500/10 border-l-2 border-red-500',
                                            entry.level === 'WARNING' && entry.level !== 'ERROR' && entry.level !== 'CRITICAL' && 'bg-amber-500/10 border-l-2 border-amber-500'
                                        )}
                                    >
                                        <div className="flex items-start gap-4">
                                            <span className="text-slate-400 flex-shrink-0 w-24 text-right text-xs">
                                                {entry.timestamp ? entry.timestamp.split(' ')[1] : '--:--'}
                                            </span>
                                            <div className="flex-shrink-0">
                                                <LogLevelBadge level={entry.level} />
                                            </div>
                                            <span className={clsx(
                                                'flex-1 break-words',
                                                (entry.level === 'ERROR' || entry.level === 'CRITICAL')
                                                    ? 'text-red-300'
                                                    : entry.level === 'WARNING'
                                                    ? 'text-amber-300'
                                                    : 'text-slate-200'
                                            )}>
                                                {entry.message}
                                            </span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Footer */}
                    <div className="bg-slate-800 dark:bg-slate-900 border-t border-slate-700 px-6 py-2 flex items-center justify-between text-sm text-slate-400">
                        <span className="font-mono">{logs.length} logs</span>
                        <span className="font-mono">{isPaused ? '⏸ Paused' : '▶ Live'}</span>
                    </div>
                </div>
            )}

            {/* Dialogs */}
            <MempoolDialog
                isOpen={showMempool}
                onClose={() => setShowMempool(false)}
                nodeUrl={node.url}
                nodeName={node.name}
            />
            <BlocksDialog
                isOpen={showBlocks}
                onClose={() => setShowBlocks(false)}
                nodeUrl={node.url}
                nodeName={node.name}
            />
            <SendTransactionDialog
                isOpen={showSendTx}
                onClose={() => setShowSendTx(false)}
                nodeUrl={node.url}
                nodeName={node.name}
            />
        </div>
    );
};

const UnifiedView = () => {
    const navigate = useNavigate();

    return (
        <div className="h-[97vh] flex flex-col min-h-0">
            <div className="mb-4 flex-shrink-0 flex items-start justify-between">
                <div>
                    <span className="text-3xl font-bold tracking-wider bg-gradient-to-r from-blue-600 to-purple-600 dark:from-blue-400 dark:to-purple-400 bg-clip-text text-transparent">
                            MiniChain
                        </span>
                    <p className="text-slate-500 dark:text-slate-400 mt-1">
                        Real-time status and logs for all nodes
                    </p>
                </div>
                <button
                    onClick={() => navigate('/')}
                    className="flex items-center gap-2 px-4 py-2 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-lg transition-colors border border-slate-300 dark:border-slate-700"
                >
                    <ArrowLeft className="w-4 h-4" />
                    <span className="text-sm font-medium">Exit Unified View</span>
                </button>
            </div>

            <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-4 min-h-0 overflow-hidden">
                {nodes.map((node, index) => (
                    <NodePanel key={node.id} node={node} index={index} />
                ))}
            </div>
        </div>
    );
};

export default UnifiedView;

