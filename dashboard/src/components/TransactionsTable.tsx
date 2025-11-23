import { Badge, Box, Table, Tbody, Td, Text, Th, Thead, Tr } from "@chakra-ui/react";
import { TransactionView } from "../api/types";

interface Props {
  transactions?: TransactionView[];
}

export const TransactionsTable = ({ transactions = [] }: Props) => (
  <Box bg="gray.800" rounded="xl" borderWidth="1px" borderColor="whiteAlpha.100" overflowX="auto">
    <Table variant="simple" colorScheme="whiteAlpha">
      <Thead>
        <Tr>
          <Th>Tx ID</Th>
          <Th>Sender</Th>
          <Th>Recipient</Th>
          <Th isNumeric>Amount</Th>
          <Th>Nonce</Th>
          <Th>Block</Th>
        </Tr>
      </Thead>
      <Tbody>
        {transactions.map((tx) => (
          <Tr key={`${tx.tx_id}-${tx.block_height}`}>
            <Td>
              <Text fontFamily="mono" fontSize="xs" noOfLines={1}>
                {tx.tx_id}
              </Text>
            </Td>
            <Td>{tx.sender}</Td>
            <Td>{tx.to}</Td>
            <Td isNumeric>
              <Badge colorScheme="orange">{tx.amount}</Badge>
            </Td>
            <Td>{tx.nonce}</Td>
            <Td>
              <Badge colorScheme="purple">#{tx.block_height}</Badge>
            </Td>
          </Tr>
        ))}
        {transactions.length === 0 && (
          <Tr>
            <Td colSpan={6}>
              <Text textAlign="center" color="whiteAlpha.600" py={6}>
                No transactions found.
              </Text>
            </Td>
          </Tr>
        )}
      </Tbody>
    </Table>
  </Box>
);
