import { Box, Table, Tbody, Td, Text, Th, Thead, Tr } from "@chakra-ui/react";
import { AccountEntry } from "../api/types";

interface Props {
  items?: AccountEntry[];
}

export const AccountsTable = ({ items = [] }: Props) => (
  <Box bg="gray.800" rounded="xl" borderWidth="1px" borderColor="whiteAlpha.100" overflowX="auto">
    <Table variant="simple" colorScheme="whiteAlpha">
      <Thead>
        <Tr>
          <Th>Address</Th>
          <Th isNumeric>Balance</Th>
        </Tr>
      </Thead>
      <Tbody>
        {items.map((account) => (
          <Tr key={account.address}>
            <Td>
              <Text fontFamily="mono" fontSize="sm" noOfLines={1}>
                {account.address}
              </Text>
            </Td>
            <Td isNumeric>{account.balance}</Td>
          </Tr>
        ))}
        {items.length === 0 && (
          <Tr>
            <Td colSpan={2}>
              <Text textAlign="center" color="whiteAlpha.600" py={6}>
                No accounts match the current filter.
              </Text>
            </Td>
          </Tr>
        )}
      </Tbody>
    </Table>
  </Box>
);
