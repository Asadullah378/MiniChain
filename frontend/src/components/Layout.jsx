import React, { useState } from 'react';
import Sidebar from './Sidebar';
import { Outlet } from 'react-router-dom';
import { Menu, Loader2 } from 'lucide-react';
import ThemeToggle from './ThemeToggle';
import { useNode } from '../context/NodeContext';

const Layout = () => {
    const [isSidebarOpen, setIsSidebarOpen] = useState(false);
    const { isSwitching, selectedNode } = useNode();

    return (
        <div className="flex h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 font-sans overflow-hidden">
            <Sidebar isOpen={isSidebarOpen} onClose={() => setIsSidebarOpen(false)} />

            <div className="flex-1 flex flex-col h-full overflow-hidden relative">
                {/* Mobile Header */}
                <div className="md:hidden p-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-white/80 dark:bg-slate-950/80 backdrop-blur-md z-30 sticky top-0">
                    <span className="font-bold text-lg tracking-wide">MiniChain</span>
                    <div className="flex items-center gap-2">
                        <ThemeToggle />
                        <button
                            onClick={() => setIsSidebarOpen(true)}
                            className="p-2 text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-900 rounded-lg transition-colors"
                        >
                            <Menu className="w-6 h-6" />
                        </button>
                    </div>
                </div>

                <main className="flex-1 overflow-y-auto p-4 md:p-8 scroll-smooth">
                    <div className="w-full max-w-full pb-20">
                        <Outlet />
                    </div>
                </main>

                {/* Node Switch Overlay */}
                {isSwitching && (
                    <div className="absolute inset-0 z-50 bg-white/50 dark:bg-slate-950/50 backdrop-blur-sm flex items-center justify-center">
                        <div className="bg-white dark:bg-slate-900 p-6 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-800 flex flex-col items-center space-y-4 animate-in fade-in zoom-in duration-200">
                            <div className="relative">
                                <div className="absolute inset-0 bg-blue-500/20 rounded-full blur-xl animate-pulse" />
                                <Loader2 className="w-10 h-10 text-blue-500 animate-spin relative z-10" />
                            </div>
                            <div className="text-center">
                                <h3 className="text-lg font-bold text-slate-900 dark:text-white">Switching Node</h3>
                                <p className="text-slate-500 dark:text-slate-400 text-sm">Connecting to {selectedNode.name}...</p>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default Layout;
