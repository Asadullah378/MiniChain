import { createBrowserRouter } from "react-router-dom";
import { AppShell } from "./layouts/AppShell";
import { DashboardPage } from "./pages/Dashboard";
import { BlocksPage } from "./pages/Blocks";
import { TransactionsPage } from "./pages/Transactions";
import { AccountsPage } from "./pages/Accounts";
import { NetworkPage } from "./pages/Network";
import { NotFoundPage } from "./pages/NotFound";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppShell />,
    errorElement: <NotFoundPage />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: "blocks", element: <BlocksPage /> },
      { path: "transactions", element: <TransactionsPage /> },
      { path: "accounts", element: <AccountsPage /> },
      { path: "network", element: <NetworkPage /> },
    ],
  },
]);
