import { Box, Heading, Text } from "@chakra-ui/react";

interface Props {
  title: string;
  subtitle?: string;
}

export const PageHeader = ({ title, subtitle }: Props) => (
  <Box>
    <Heading size="lg" color="white">
      {title}
    </Heading>
    {subtitle && (
      <Text color="whiteAlpha.700" mt={2}>
        {subtitle}
      </Text>
    )}
  </Box>
);
