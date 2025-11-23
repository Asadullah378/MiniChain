import { Badge, Box, Flex, HStack, Icon, SimpleGrid, Text } from "@chakra-ui/react";
import { FiActivity, FiClock, FiHash } from "react-icons/fi";
import { NodeOverview } from "../api/types";

interface Props {
  nodes?: NodeOverview[];
  isLoading?: boolean;
}

export const NodeStatusGrid = ({ nodes, isLoading }: Props) => {
  if (isLoading) {
    return (
      <Box p={6} bg="gray.800" rounded="lg" borderWidth="1px" borderColor="whiteAlpha.100">
        <Text color="whiteAlpha.700">Loading node metrics…</Text>
      </Box>
    );
  }

  if (!nodes?.length) {
    return (
      <Box p={6} bg="gray.800" rounded="lg" borderWidth="1px" borderColor="whiteAlpha.100">
        <Text color="whiteAlpha.600">No nodes discovered yet. Start a node to populate telemetry.</Text>
      </Box>
    );
  }

  return (
    <SimpleGrid columns={{ base: 1, md: nodes.length >= 2 ? 2 : 1, lg: nodes.length >= 3 ? 3 : 2 }} gap={4}>
      {nodes.map((node) => (
        <Box key={node.node_id} p={5} rounded="xl" bg="gray.800" borderWidth="1px" borderColor="whiteAlpha.100">
          <Flex justify="space-between" align="center" mb={4}>
            <Text fontWeight="bold" color="white">
              {node.node_id}
            </Text>
            <Badge colorScheme="green">online</Badge>
          </Flex>
          <HStack spacing={4} align="flex-start">
            <Icon as={FiActivity} color="brand.400" boxSize={5} mt={1} />
            <Box flex={1}>
              <Text fontSize="sm" color="whiteAlpha.700">
                Height
              </Text>
              <Text fontSize="xl" fontWeight="bold" color="white">
                {node.height}
              </Text>
            </Box>
          </HStack>
          <HStack spacing={4} align="flex-start" mt={3}>
            <Icon as={FiHash} color="brand.400" boxSize={5} mt={1} />
            <Box flex={1}>
              <Text fontSize="sm" color="whiteAlpha.700">
                Head Hash
              </Text>
              <Text fontFamily="mono" fontSize="sm" color="whiteAlpha.900" noOfLines={1}>
                {node.head_hash}
              </Text>
            </Box>
          </HStack>
          <HStack spacing={4} align="flex-start" mt={3}>
            <Icon as={FiClock} color="brand.400" boxSize={5} mt={1} />
            <Box flex={1}>
              <Text fontSize="sm" color="whiteAlpha.700">
                Accounts
              </Text>
              <Text color="white">{node.total_accounts}</Text>
              <Text fontSize="xs" color="whiteAlpha.600">
                Total balance {node.total_balance}
              </Text>
            </Box>
          </HStack>
        </Box>
      ))}
    </SimpleGrid>
  );
};
