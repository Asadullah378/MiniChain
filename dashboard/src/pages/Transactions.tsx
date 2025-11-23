import { Stack } from "@chakra-ui/react";
import { PageHeader } from "../components/PageHeader";
import { TransactionsTable } from "../components/TransactionsTable";
import { useNodeOverview, useTransactions } from "../api/hooks";

export const TransactionsPage = () => {
  const nodesQuery = useNodeOverview();
  const primaryNode = nodesQuery.data?.[0]?.node_id;
  const txQuery = useTransactions({ node_id: primaryNode, limit: 30 });

  return (
    <Stack spacing={8}>
      <PageHeader title="Transactions" subtitle="Latest confirmed transfers" />
      <TransactionsTable transactions={txQuery.data?.items} />
    </Stack>
  );
};
