import React from 'react';
import { LayoutDashboard, Link, Layers, Send, Activity } from 'lucide-react';
import { NavLink } from 'react-router-dom';

const Sidebar = () => {
    const navItems = [
        { icon: LayoutDashboard, label: 'Dashboard', path: '/' },
        { icon: Layers, label: 'Blockchain', path: '/blocks' },
        { icon: Send, label: 'Mempool', path: '/mempool' },
    ];

    return (
        <div className="w-64 h-screen bg-gray-900 text-white border-r border-gray-800 flex flex-col">
            <div className="p-6 flex items-center space-x-3 border-b border-gray-800">
                <Activity className="w-8 h-8 text-blue-500" />
                <span className="text-xl font-bold tracking-wider">MiniChain</span>
            </div>

            <nav className="flex-1 p-4 space-y-2">
                {navItems.map((item) => (
                    <NavLink
                        key={item.path}
                        to={item.path}
                        className={({ isActive }) =>
                            `flex items-center space-x-3 px-4 py-3 rounded-lg transition-all duration-200 ${isActive
                                ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/20'
                                : 'text-gray-400 hover:bg-gray-800 hover:text-white'
                            }`
                        }
                    >
                        <item.icon className="w-5 h-5" />
                        <span className="font-medium">{item.label}</span>
                    </NavLink>
                ))}
            </nav>

            <div className="p-4 border-t border-gray-800">
                <div className="text-xs text-gray-500 text-center">
                    MiniChain Node Visualization
                </div>
            </div>
        </div>
    );
};

export default Sidebar;
