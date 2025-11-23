import { Stack } from "@chakra-ui/react";
import { PageHeader } from "../components/PageHeader";
import { BlocksTable } from "../components/BlocksTable";
import { useBlocks, useNodeOverview } from "../api/hooks";

export const BlocksPage = () => {
  const nodesQuery = useNodeOverview();
  const primaryNode = nodesQuery.data?.[0]?.node_id;
  const blocksQuery = useBlocks({ node_id: primaryNode, limit: 20 });

  return (
    <Stack spacing={8}>
      <PageHeader title="Blocks" subtitle="Chain history pulled directly from node snapshots" />
      <BlocksTable nodeId={primaryNode} blocks={blocksQuery.data?.items} />
    </Stack>
  );
};
