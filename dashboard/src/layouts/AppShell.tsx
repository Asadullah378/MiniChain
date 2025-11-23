import { Box, Flex, HStack, Icon, Link, Text } from "@chakra-ui/react";
import { FiActivity, FiGrid, FiLayers, FiShare2, FiSend, FiUsers } from "react-icons/fi";
import { NavLink, Outlet } from "react-router-dom";

const links = [
  { to: "/", label: "Overview", icon: FiGrid },
  { to: "/blocks", label: "Blocks", icon: FiLayers },
  { to: "/transactions", label: "Transactions", icon: FiSend },
  { to: "/accounts", label: "Accounts", icon: FiUsers },
  { to: "/network", label: "Network", icon: FiShare2 },
];

export const AppShell = () => (
  <Flex minH="100vh" bg="gray.900" color="white">
    <Box w={{ base: "70px", md: "220px" }} bg="blackAlpha.500" borderRightWidth="1px" borderColor="whiteAlpha.100">
      <Flex align="center" gap={3} px={6} py={6} borderBottomWidth="1px" borderColor="whiteAlpha.100">
        <Icon as={FiActivity} color="brand.400" boxSize={6} />
        <Text fontWeight="bold" display={{ base: "none", md: "block" }}>
          MiniChain
        </Text>
      </Flex>
      <Flex direction="column" as="nav" py={4}>
        {links.map((link) => (
          <NavLink key={link.to} to={link.to} end={link.to === "/"}>
            {({ isActive }) => (
              <HStack
                px={{ base: 0, md: 6 }}
                py={3}
                spacing={4}
                color={isActive ? "brand.300" : "whiteAlpha.700"}
                borderLeftWidth={{ base: 0, md: "3px" }}
                borderColor={isActive ? "brand.400" : "transparent"}
                justify={{ base: "center", md: "flex-start" }}
              >
                <Icon as={link.icon} boxSize={5} />
                <Text display={{ base: "none", md: "block" }}>{link.label}</Text>
              </HStack>
            )}
          </NavLink>
        ))}
      </Flex>
    </Box>

    <Box flex={1} px={{ base: 4, md: 10 }} py={8}>
      <Box maxW="1400px" mx="auto">
        <Outlet />
        <Text mt={8} fontSize="xs" color="whiteAlpha.500">
          Built for the MiniChain test network.
        </Text>
      </Box>
    </Box>
  </Flex>
);
