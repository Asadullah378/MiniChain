import { Box, Flex, Icon, Text } from "@chakra-ui/react";
import { IconType } from "react-icons";

interface StatCardProps {
  label: string;
  value: string | number;
  sublabel?: string;
  icon?: IconType;
  accentColor?: string;
}

export const StatCard = ({ label, value, sublabel, icon, accentColor = "brand.400" }: StatCardProps) => (
  <Box
    p={5}
    rounded="xl"
    bg="gray.800"
    borderWidth="1px"
    borderColor="whiteAlpha.100"
    shadow="sm"
  >
    <Flex align="center" gap={4}>
      {icon && (
        <Flex
          align="center"
          justify="center"
          w={12}
          h={12}
          rounded="full"
          bg="whiteAlpha.50"
          color={accentColor}
        >
          <Icon as={icon} boxSize={6} />
        </Flex>
      )}
      <Box>
        <Text fontSize="sm" color="whiteAlpha.700" textTransform="uppercase" letterSpacing="wider">
          {label}
        </Text>
        <Text fontSize="2xl" fontWeight="bold" color="white">
          {value}
        </Text>
        {sublabel && (
          <Text fontSize="xs" color="whiteAlpha.600">
            {sublabel}
          </Text>
        )}
      </Box>
    </Flex>
  </Box>
);
