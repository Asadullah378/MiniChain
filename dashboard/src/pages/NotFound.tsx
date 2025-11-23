import { Box, Button, Heading, Text } from "@chakra-ui/react";
import { Link } from "react-router-dom";

export const NotFoundPage = () => (
  <Box textAlign="center" py={20} color="white">
    <Heading size="2xl">404</Heading>
    <Text color="whiteAlpha.700" mt={4}>
      The page you were looking for does not exist.
    </Text>
    <Button as={Link} to="/" mt={6} colorScheme="brand">
      Back to dashboard
    </Button>
  </Box>
);
