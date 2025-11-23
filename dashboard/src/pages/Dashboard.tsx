import { SimpleGrid, Stack } from "@chakra-ui/react";
import { FiActivity, FiClock, FiDatabase, FiHash } from "react-icons/fi";
import { PageHeader } from "../components/PageHeader";
import { StatCard } from "../components/StatCard";
import { NodeStatusGrid } from "../components/NodeStatusGrid";
import { BlocksTable } from "../components/BlocksTable";
import { TransactionsTable } from "../components/TransactionsTable";
import { useBlocks, useNodeOverview, useTransactions } from "../api/hooks";

export const DashboardPage = () => {
  const nodesQuery = useNodeOverview();
  const primaryNode = nodesQuery.data?.[0]?.node_id;
  const blocksQuery = useBlocks({ node_id: primaryNode, limit: 5 });
  const txQuery = useTransactions({ node_id: primaryNode, limit: 8 });

  const latestHeight = nodesQuery.data?.reduce((max, node) => Math.max(max, node.height), 0) ?? 0;
  const totalAccounts = nodesQuery.data?.reduce((sum, node) => sum + node.total_accounts, 0) ?? 0;
  const aggregateBalance = nodesQuery.data?.reduce((sum, node) => sum + node.total_balance, 0) ?? 0;

  return (
    <Stack spacing={8}>
      <PageHeader title="Control Center" subtitle="Live state for your MiniChain test network" />

      <SimpleGrid columns={{ base: 1, md: 2, xl: 4 }} gap={4}>
        <StatCard label="Best Height" value={latestHeight} icon={FiHash} sublabel="max across validators" />
        <StatCard label="Accounts" value={totalAccounts} icon={FiDatabase} sublabel="unique addresses" />
        <StatCard label="Total Balance" value={aggregateBalance} icon={FiActivity} sublabel="sum of visible balances" />
        <StatCard label="Last Refresh" value={new Date().toLocaleTimeString()} icon={FiClock} sublabel="local time" />
      </SimpleGrid>

      <NodeStatusGrid nodes={nodesQuery.data} isLoading={nodesQuery.isLoading} />

      <BlocksTable nodeId={primaryNode} blocks={blocksQuery.data?.items} pageSize={5} />

      <TransactionsTable transactions={txQuery.data?.items} />
    </Stack>
  );
};
