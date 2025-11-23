import { Input, InputGroup, InputLeftElement, Stack } from "@chakra-ui/react";
import { useMemo, useState } from "react";
import { FiSearch } from "react-icons/fi";
import { useAccounts, useNodeOverview } from "../api/hooks";
import { PageHeader } from "../components/PageHeader";
import { AccountsTable } from "../components/AccountsTable";

export const AccountsPage = () => {
  const [query, setQuery] = useState("");
  const nodesQuery = useNodeOverview();
  const primaryNode = nodesQuery.data?.[0]?.node_id;
  const accountsQuery = useAccounts({ node_id: primaryNode, q: query || undefined, limit: 100 });

  const subtitle = useMemo(() => {
    if (accountsQuery.isLoading) return "Loading balances";
    const total = accountsQuery.data?.total ?? 0;
    return `${total} tracked accounts`;
  }, [accountsQuery.data?.total, accountsQuery.isLoading]);

  return (
    <Stack spacing={6}>
      <PageHeader title="Accounts" subtitle={subtitle} />
      <InputGroup maxW="320px">
        <InputLeftElement pointerEvents="none" children={<FiSearch />} />
        <Input
          placeholder="Filter by address"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          bg="gray.800"
          borderColor="whiteAlpha.200"
        />
      </InputGroup>
      <AccountsTable items={accountsQuery.data?.items} />
    </Stack>
  );
};
