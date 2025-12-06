import React, { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Terminal, Filter, Download, X, Pause, Play, Maximize2, Minimize2 } from 'lucide-react';
import { getLogs } from '../api/client';
import { useNode } from '../context/NodeContext';
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

const LogLine = ({ entry, index }) => {
  const isError = entry.level === 'ERROR' || entry.level === 'CRITICAL';
  const isWarning = entry.level === 'WARNING';
  
  return (
    <div
      className={clsx(
        'font-mono text-xs leading-relaxed px-4 py-1 transition-colors',
        'hover:bg-slate-100 dark:hover:bg-slate-800/50',
        isError && 'bg-red-50 dark:bg-red-500/5 border-l-2 border-red-400 dark:border-red-500/50',
        isWarning && !isError && 'bg-amber-50 dark:bg-amber-500/5 border-l-2 border-amber-400 dark:border-amber-500/30'
      )}
    >
      <div className="flex items-start gap-3">
        <span className="text-slate-500 dark:text-slate-500 flex-shrink-0 w-20 text-right">
          {entry.timestamp || '--:--:--'}
        </span>
        <div className="flex-shrink-0">
          <LogLevelBadge level={entry.level} />
        </div>
        <span className="text-slate-500 dark:text-slate-500 flex-shrink-0 w-32 truncate">
          {entry.logger || 'unknown'}
        </span>
        <span className={clsx(
          'flex-1 break-words',
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

const Logs = () => {
  const { selectedNode } = useNode();
  const [logs, setLogs] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [levelFilter, setLevelFilter] = useState(null);
  const [showFilters, setShowFilters] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [error, setError] = useState(null);
  const eventSourceRef = useRef(null);
  const containerRef = useRef(null);
  const isUserScrollingRef = useRef(false);
  const scrollTimeoutRef = useRef(null);

  // Check if user is at top (for auto-scroll)
  const isAtTop = () => {
    if (!containerRef.current) return true;
    return containerRef.current.scrollTop < 50;
  };

  // Auto-scroll to top when new logs arrive (only if user is at top)
  const handleNewLog = useCallback((entry) => {
    setLogs((prev) => {
      // Add new log at the beginning (newest first)
      const newLogs = [entry, ...prev];
      // Keep only last 1000 logs to prevent memory issues
      return newLogs.slice(0, 1000);
    });

    // Auto-scroll to top if user is at top
    if (isAtTop() && !isPaused && containerRef.current) {
      requestAnimationFrame(() => {
        if (containerRef.current) {
          containerRef.current.scrollTop = 0;
        }
      });
    }
  }, [isPaused]);

  // Connect to SSE stream
  useEffect(() => {
    if (isPaused) return;

    let initialLogsBatch = [];
    let initialBatchTimeout = null;
    let initialBatchSet = false; // Flag to track if initial batch has been set

    const connectSSE = () => {
      try {
        const baseUrl = selectedNode.url;
        const url = `${baseUrl}/logs/stream${levelFilter ? `?level=${levelFilter}` : ''}`;
        
        const eventSource = new EventSource(url);
        eventSourceRef.current = eventSource;

        eventSource.onopen = () => {
          setIsConnected(true);
          setError(null);
          // Clear any existing logs when reconnecting
          setLogs([]);
          initialLogsBatch = [];
          initialBatchSet = false;
        };

        eventSource.onmessage = (event) => {
          if (event.data.startsWith(':')) {
            // Keepalive message, ignore
            return;
          }

          try {
            const entry = JSON.parse(event.data);
            if (entry.error) {
              setError(entry.error);
            } else {
              // Collect initial batch (first 50 logs) and add them all at once in correct order
              // The backend sends them in reverse order (newest first), so we collect them
              // and then set them all at once to maintain order
              if (!initialBatchSet && initialLogsBatch.length < 500) {
                initialLogsBatch.push(entry);
                
                // Clear any existing timeout
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
                    
                    // Scroll to top after initial batch
                    if (containerRef.current) {
                      containerRef.current.scrollTop = 0;
                    }
                  }
                }, 500);
              } else {
                // After initial batch is set, add new logs normally to existing logs
                setLogs((prev) => {
                  const newLogs = [entry, ...prev];
                  return newLogs.slice(0, 1000);
                });
                
                // Auto-scroll to top if at top
                if (isAtTop() && !isPaused && containerRef.current) {
                  requestAnimationFrame(() => {
                    if (containerRef.current) {
                      containerRef.current.scrollTop = 0;
                    }
                  });
                }
              }
            }
          } catch (err) {
            console.error('Error parsing log entry:', err);
          }
        };

        eventSource.onerror = (err) => {
          console.error('SSE error:', err);
          setIsConnected(false);
          setError('Connection lost. Reconnecting...');
          
          // Reconnect after delay
          setTimeout(() => {
            if (eventSourceRef.current) {
              eventSourceRef.current.close();
            }
            connectSSE();
          }, 3000);
        };
      } catch (err) {
        setError(`Failed to connect: ${err.message}`);
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
        eventSourceRef.current = null;
      }
    };
  }, [selectedNode.url, levelFilter, isPaused, handleNewLog]);

  // Handle scroll detection
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const handleScroll = () => {
      isUserScrollingRef.current = true;
      
      if (scrollTimeoutRef.current) {
        clearTimeout(scrollTimeoutRef.current);
      }
      
      scrollTimeoutRef.current = setTimeout(() => {
        isUserScrollingRef.current = false;
      }, 1000);
    };

    container.addEventListener('scroll', handleScroll);
    return () => {
      container.removeEventListener('scroll', handleScroll);
      if (scrollTimeoutRef.current) {
        clearTimeout(scrollTimeoutRef.current);
      }
    };
  }, []);

  // Note: Initial logs are loaded via SSE stream, which sends them in reverse order (newest first)
  // So we don't need to load them separately here

  const handleDownload = () => {
    if (logs.length === 0) return;

    const logText = logs
      .map((entry) => entry.raw)
      .reverse() // Reverse back to chronological order for download
      .join('\n');

    const blob = new Blob([logText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `minichain-logs-${selectedNode.name}-${new Date().toISOString()}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleClear = () => {
    setLogs([]);
  };

  const logLevels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'];

  return (
    <div className={clsx(
      'flex flex-col h-full',
      isFullscreen && 'fixed inset-0 z-50 bg-white dark:bg-slate-950'
    )}>
      {/* Header */}
      <div className="bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Terminal className="w-5 h-5 text-blue-600 dark:text-blue-400" />
          <div>
            <h1 className="text-lg font-bold text-slate-900 dark:text-slate-100">Node Logs</h1>
            <p className="text-xs text-slate-600 dark:text-slate-400">{selectedNode.name} • {selectedNode.url}</p>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          {/* Connection Status */}
          <div className={clsx(
            'flex items-center gap-2 px-3 py-1.5 rounded text-xs font-mono border',
            isConnected 
              ? 'bg-green-100 dark:bg-green-500/20 text-green-700 dark:text-green-400 border-green-300 dark:border-green-500/30' 
              : 'bg-red-100 dark:bg-red-500/20 text-red-700 dark:text-red-400 border-red-300 dark:border-red-500/30'
          )}>
            <div className={clsx(
              'w-2 h-2 rounded-full',
              isConnected ? 'bg-green-600 dark:bg-green-400 animate-pulse' : 'bg-red-600 dark:bg-red-400'
            )} />
            {isConnected ? 'LIVE' : 'DISCONNECTED'}
          </div>

          {/* Filters */}
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={clsx(
              'px-3 py-1.5 rounded text-xs border transition-colors flex items-center gap-2',
              showFilters
                ? 'bg-blue-100 dark:bg-blue-500/20 text-blue-700 dark:text-blue-400 border-blue-300 dark:border-blue-500/30'
                : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-300 dark:border-slate-700 hover:bg-slate-200 dark:hover:bg-slate-700'
            )}
          >
            <Filter className="w-3.5 h-3.5" />
            Filters
          </button>

          {/* Pause/Resume */}
          <button
            onClick={() => setIsPaused(!isPaused)}
            className={clsx(
              'px-3 py-1.5 rounded text-xs border transition-colors flex items-center gap-2',
              isPaused
                ? 'bg-amber-100 dark:bg-amber-500/20 text-amber-700 dark:text-amber-400 border-amber-300 dark:border-amber-500/30'
                : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-300 dark:border-slate-700 hover:bg-slate-200 dark:hover:bg-slate-700'
            )}
          >
            {isPaused ? (
              <>
                <Play className="w-3.5 h-3.5" />
                Resume
              </>
            ) : (
              <>
                <Pause className="w-3.5 h-3.5" />
                Pause
              </>
            )}
          </button>

          {/* Clear */}
          <button
            onClick={handleClear}
            className="px-3 py-1.5 rounded text-xs border border-slate-300 dark:border-slate-700 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
          >
            Clear
          </button>

          {/* Download */}
          <button
            onClick={handleDownload}
            disabled={logs.length === 0}
            className="px-3 py-1.5 rounded text-xs border border-slate-300 dark:border-slate-700 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Download className="w-3.5 h-3.5" />
            Download
          </button>

          {/* Fullscreen */}
          <button
            onClick={() => setIsFullscreen(!isFullscreen)}
            className="px-3 py-1.5 rounded text-xs border border-slate-300 dark:border-slate-700 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
          >
            {isFullscreen ? (
              <Minimize2 className="w-3.5 h-3.5" />
            ) : (
              <Maximize2 className="w-3.5 h-3.5" />
            )}
          </button>
        </div>
      </div>

      {/* Filters Panel */}
      <AnimatePresence>
        {showFilters && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 px-4 py-3 overflow-hidden"
          >
            <div className="flex items-center gap-4">
              <label className="text-xs text-slate-600 dark:text-slate-400 font-medium">Filter by Level:</label>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setLevelFilter(null)}
                  className={clsx(
                    'px-3 py-1 rounded text-xs border transition-colors',
                    !levelFilter
                      ? 'bg-blue-100 dark:bg-blue-500/20 text-blue-700 dark:text-blue-400 border-blue-300 dark:border-blue-500/30'
                      : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-300 dark:border-slate-700 hover:bg-slate-200 dark:hover:bg-slate-700'
                  )}
                >
                  All
                </button>
                {logLevels.map((level) => (
                  <button
                    key={level}
                    onClick={() => setLevelFilter(levelFilter === level ? null : level)}
                    className={clsx(
                      'px-3 py-1 rounded text-xs border transition-colors',
                      levelFilter === level
                        ? 'bg-blue-100 dark:bg-blue-500/20 text-blue-700 dark:text-blue-400 border-blue-300 dark:border-blue-500/30'
                        : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-300 dark:border-slate-700 hover:bg-slate-200 dark:hover:bg-slate-700'
                    )}
                  >
                    {level}
                  </button>
                ))}
              </div>
              {levelFilter && (
                <button
                  onClick={() => setLevelFilter(null)}
                  className="text-xs text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300 flex items-center gap-1"
                >
                  <X className="w-3 h-3" />
                  Clear
                </button>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Error Banner */}
      {error && (
        <div className="bg-red-50 dark:bg-red-500/10 border-b border-red-200 dark:border-red-500/30 px-4 py-2 text-sm text-red-700 dark:text-red-400">
          {error}
        </div>
      )}

      {/* Logs Container - Terminal Style */}
      <div
        ref={containerRef}
        className="logs-scrollbar flex-1 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 font-mono text-xs overflow-y-auto"
        style={{ scrollBehavior: 'smooth' }}
      >
        {logs.length === 0 && !error && (
          <div className="flex items-center justify-center h-full text-slate-500 dark:text-slate-500">
            <div className="text-center">
              <Terminal className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>Waiting for logs...</p>
              <p className="text-xs mt-1">Logs will appear here in real-time</p>
            </div>
          </div>
        )}

        {logs.length > 0 && (
          <div className="py-2">
            <AnimatePresence>
              {logs.map((entry, index) => (
                <LogLine key={`${entry.timestamp}-${index}-${entry.raw}`} entry={entry} index={index} />
              ))}
            </AnimatePresence>
          </div>
        )}

        {/* Scroll anchor at top */}
        <div style={{ height: 0 }} />
      </div>

      {/* Footer Stats */}
      <div className="bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800 px-4 py-2 flex items-center justify-between text-xs text-slate-600 dark:text-slate-400">
        <div className="flex items-center gap-4">
          <span className="font-mono">Lines: {logs.length.toLocaleString()}</span>
          {levelFilter && (
            <span className="font-mono">Filter: {levelFilter}</span>
          )}
        </div>
        <div className="font-mono">
          {isPaused ? '⏸ Paused' : '▶ Live'}
        </div>
      </div>
    </div>
  );
};

export default Logs;
