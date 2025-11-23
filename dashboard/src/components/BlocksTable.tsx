import React from "react";
import {
  Badge,
  Box,
  HStack,
  IconButton,
  Table,
  Tbody,
  Td,
  Text,
  Th,
  Thead,
  Tr,
  useDisclosure,
  Drawer,
  DrawerBody,
  DrawerContent,
  DrawerHeader,
  DrawerOverlay,
  Stack,
  Divider,
} from "@chakra-ui/react";
import { FiEye } from "react-icons/fi";
import { BlockSummary } from "../api/types";
import { useBlockDetail } from "../api/hooks";

interface Props {
  nodeId?: string;
  blocks?: BlockSummary[];
  total?: number;
  onPageChange?: (page: number) => void;
  page?: number;
  pageSize?: number;
}

export const BlocksTable = ({ nodeId, blocks = [], page = 0, pageSize = 20 }: Props) => {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedHeight, setSelectedHeight] = React.useState<number | null>(null);
  const detailQuery = useBlockDetail(selectedHeight ?? 0, { node_id: nodeId }, { enabled: !!selectedHeight });

  const openDrawer = (height: number) => {
    setSelectedHeight(height);
    onOpen();
  };

  return (
    <Box bg="gray.800" rounded="xl" borderWidth="1px" borderColor="whiteAlpha.100" overflowX="auto">
      <Table variant="simple" colorScheme="whiteAlpha">
        <Thead>
          <Tr>
            <Th>#</Th>
            <Th>Hash</Th>
            <Th>Proposer</Th>
            <Th isNumeric>Tx</Th>
            <Th>Timestamp</Th>
            <Th></Th>
          </Tr>
        </Thead>
        <Tbody>
          {blocks.map((block) => (
            <Tr key={block.block_hash}>
              <Td>{block.height}</Td>
              <Td>
                <Text fontFamily="mono" fontSize="sm" noOfLines={1}>
                  {block.block_hash}
                </Text>
              </Td>
              <Td>
                <Badge colorScheme="purple">{block.proposer_id}</Badge>
              </Td>
              <Td isNumeric>{block.tx_count}</Td>
              <Td>{new Date(block.timestamp * 1000).toLocaleTimeString()}</Td>
              <Td textAlign="right">
                <IconButton
                  aria-label="View block"
                  size="sm"
                  icon={<FiEye />}
                  variant="ghost"
                  onClick={() => openDrawer(block.height)}
                />
              </Td>
            </Tr>
          ))}
        </Tbody>
      </Table>

      <Drawer isOpen={isOpen} placement="right" onClose={onClose} size="md">
        <DrawerOverlay />
        <DrawerContent bg="gray.900">
          <DrawerHeader borderBottomWidth="1px">Block {selectedHeight}</DrawerHeader>
          <DrawerBody>
            {detailQuery.isLoading && <Text color="whiteAlpha.700">Loading block details…</Text>}
            {detailQuery.data && (
              <Stack spacing={4} color="whiteAlpha.900">
                <Box>
                  <Text fontSize="sm" color="whiteAlpha.600">
                    Hash
                  </Text>
                  <Text fontFamily="mono">{detailQuery.data.block_hash}</Text>
                </Box>
                <Box>
                  <Text fontSize="sm" color="whiteAlpha.600">
                    Transactions
                  </Text>
                  <Stack spacing={3} mt={2}>
                    {detailQuery.data.tx_list.length === 0 && <Text>No transactions in this block.</Text>}
                    {detailQuery.data.tx_list.map((tx) => (
                      <Box key={tx.tx_id ?? `${tx.sender}-${tx.nonce}`} p={3} bg="gray.800" rounded="md">
                        <HStack justify="space-between" mb={2}>
                          <Text fontWeight="semibold">{tx.sender}</Text>
                          <Badge>{tx.amount}</Badge>
                        </HStack>
                        <Text fontSize="sm">→ {tx.to}</Text>
                        <Text fontSize="xs" color="whiteAlpha.600">
                          nonce {tx.nonce}
                        </Text>
                      </Box>
                    ))}
                  </Stack>
                </Box>
                <Divider borderColor="whiteAlpha.200" />
                <Box>
                  <Text fontSize="sm" color="whiteAlpha.600">
                    Raw data
                  </Text>
                  <Box as="pre" fontSize="xs" bg="blackAlpha.700" p={3} rounded="md" overflowX="auto">
                    {JSON.stringify(detailQuery.data, null, 2)}
                  </Box>
                </Box>
              </Stack>
            )}
          </DrawerBody>
        </DrawerContent>
      </Drawer>
    </Box>
  );
};
