import { Box, Flex, SimpleGrid, Text } from "@chakra-ui/react";
import { NodeOverview } from "../api/types";

interface Props {
  nodes?: NodeOverview[];
}

export const NetworkOverview = ({ nodes = [] }: Props) => (
  <Box bg="gray.800" rounded="xl" borderWidth="1px" borderColor="whiteAlpha.100" p={6}>
    <Text fontSize="lg" fontWeight="bold" color="white" mb={4}>
      Peer Topology
    </Text>
    {nodes.length === 0 && <Text color="whiteAlpha.600">No peers to visualize.</Text>}
    {nodes.length > 0 && (
      <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} gap={4}>
        {nodes.map((node) => (
          <Flex
            key={node.node_id}
            direction="column"
            borderWidth="1px"
            borderColor="whiteAlpha.100"
            rounded="lg"
            p={4}
            bg="blackAlpha.400"
          >
            <Text fontWeight="semibold" color="white">
              {node.node_id}
            </Text>
            <Text fontSize="sm" color="whiteAlpha.600">
              Height {node.height}
            </Text>
            <Text fontSize="xs" color="whiteAlpha.500" fontFamily="mono" mt={2}>
              {node.head_hash}
            </Text>
          </Flex>
        ))}
      </SimpleGrid>
    )}
  </Box>
);
