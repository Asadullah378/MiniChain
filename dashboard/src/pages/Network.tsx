import { Stack } from "@chakra-ui/react";
import { useNodeOverview } from "../api/hooks";
import { PageHeader } from "../components/PageHeader";
import { NetworkOverview } from "../components/NetworkOverview";

export const NetworkPage = () => {
  const nodesQuery = useNodeOverview();
  return (
    <Stack spacing={8}>
      <PageHeader title="Network" subtitle="Validator heartbeat and topology snapshot" />
      <NetworkOverview nodes={nodesQuery.data} />
    </Stack>
  );
};
