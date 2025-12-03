import React from 'react';
import { LayoutDashboard, Layers, Send, Activity, X, Clock } from 'lucide-react';
import { NavLink } from 'react-router-dom';
import clsx from 'clsx';
import ThemeToggle from './ThemeToggle';
import { useNode } from '../context/NodeContext';

const Sidebar = ({ isOpen, onClose }) => {
    const { selectedNode, nodes, changeNode } = useNode();
    const navItems = [
        { icon: LayoutDashboard, label: 'Dashboard', path: '/' },
        { icon: Layers, label: 'Blockchain', path: '/blocks' },
        { icon: Clock, label: 'Mempool', path: '/mempool' },
        { icon: Send, label: 'Send Transaction', path: '/send-transaction' },
    ];

    return (
        <>
            {/* Mobile Overlay */}
            <div
                className={clsx(
                    "fixed inset-0 bg-black/50 z-40 md:hidden transition-opacity duration-300",
                    isOpen ? "opacity-100" : "opacity-0 pointer-events-none"
                )}
                onClick={onClose}
            />

            {/* Sidebar Container */}
            <div className={clsx(
                "fixed md:static inset-y-0 left-0 z-50 w-64 bg-white dark:bg-slate-950 text-slate-900 dark:text-white border-r border-slate-200 dark:border-slate-800 flex flex-col transition-transform duration-300 transform md:translate-x-0",
                isOpen ? "translate-x-0" : "-translate-x-full"
            )}>
                <div className="p-6 flex items-center justify-between border-b border-slate-200 dark:border-slate-800">
                    <div className="flex items-center space-x-3">
                        <div className="p-2 bg-blue-600/20 rounded-lg">
                            <Activity className="w-6 h-6 text-blue-500" />
                        </div>
                        <span className="text-xl font-bold tracking-wider bg-gradient-to-r from-blue-600 to-purple-600 dark:from-blue-400 dark:to-purple-400 bg-clip-text text-transparent">
                            MiniChain
                        </span>
                    </div>
                    <button onClick={onClose} className="md:hidden text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white">
                        <X className="w-6 h-6" />
                    </button>
                </div>

                <nav className="flex-1 p-4 space-y-2">
                    {navItems.map((item) => (
                        <NavLink
                            key={item.path}
                            to={item.path}
                            onClick={() => window.innerWidth < 768 && onClose()}
                            className={({ isActive }) =>
                                clsx(
                                    "flex items-center space-x-3 px-4 py-3 rounded-xl transition-all duration-200 group",
                                    isActive
                                        ? "bg-blue-600/10 text-blue-400 border border-blue-600/20 shadow-[0_0_20px_rgba(37,99,235,0.1)]"
                                        : "text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-900 hover:text-slate-900 dark:hover:text-white hover:translate-x-1"
                                )
                            }
                        >
                            <item.icon className={clsx("w-5 h-5 transition-colors", ({ isActive }) => isActive ? "text-blue-400" : "group-hover:text-blue-400")} />
                            <span className="font-medium">{item.label}</span>
                        </NavLink>
                    ))}
                </nav>

                <div className="p-4 border-t border-slate-200 dark:border-slate-800 flex flex-col gap-4">
                    <div className="flex items-center justify-between gap-2">
                        <div className="flex-1">
                            <label className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-1.5 block uppercase tracking-wider">
                                Connected Node
                            </label>
                            <select
                                value={selectedNode.id}
                                onChange={(e) => changeNode(e.target.value)}
                                className="w-full bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white text-sm rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 block p-2.5 transition-colors cursor-pointer outline-none"
                            >
                                {nodes.map((node) => (
                                    <option key={node.id} value={node.id}>
                                        {node.name}
                                    </option>
                                ))}
                            </select>
                        </div>
                        <div className="self-end mb-1">
                            <ThemeToggle />
                        </div>
                    </div>

                    <div className="text-[10px] text-slate-400 text-center font-mono">
                        {selectedNode.url}
                    </div>
                </div>
            </div>
        </>
    );
};

export default Sidebar;
