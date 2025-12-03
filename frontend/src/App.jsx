import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Blocks from './pages/Blocks';
import Mempool from './pages/Mempool';
import SendTransaction from './pages/SendTransaction';
import { NodeProvider } from './context/NodeContext';

function App() {
  return (
    <NodeProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="blocks" element={<Blocks />} />
            <Route path="mempool" element={<Mempool />} />
            <Route path="send-transaction" element={<SendTransaction />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </NodeProvider>
  );
}

export default App;
