import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Blocks from './pages/Blocks';
import Mempool from './pages/Mempool';
import SendTransaction from './pages/SendTransaction';
import TransactionDetails from './pages/TransactionDetails';
import Logs from './pages/Logs';
import UnifiedView from './pages/UnifiedView';
import { NodeProvider } from './context/NodeContext';
import { ViewProvider } from './context/ViewContext';

function App() {
  return (
    <NodeProvider>
      <BrowserRouter>
        <ViewProvider>
          <Routes>
            <Route path="/" element={<Layout />}>
              <Route index element={<Dashboard />} />
              <Route path="blocks" element={<Blocks />} />
              <Route path="mempool" element={<Mempool />} />
              <Route path="send-transaction" element={<SendTransaction />} />
              <Route path="transaction/:txId" element={<TransactionDetails />} />
              <Route path="logs" element={<Logs />} />
              <Route path="unified" element={<UnifiedView />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </ViewProvider>
      </BrowserRouter>
    </NodeProvider>
  );
}

export default App;
