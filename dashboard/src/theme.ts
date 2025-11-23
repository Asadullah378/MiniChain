import { extendTheme, ThemeConfig } from "@chakra-ui/react";

const config: ThemeConfig = {
  initialColorMode: "dark",
  useSystemColorMode: false,
};

export const theme = extendTheme({
  config,
  fonts: {
    heading: "'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    body: "'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
  },
  styles: {
    global: {
      "html, body": {
        backgroundColor: "gray.900",
      },
    },
  },
  colors: {
    brand: {
      50: "#e4f2ff",
      100: "#bad9ff",
      200: "#90c0ff",
      300: "#66a6ff",
      400: "#3c8dff",
      500: "#2373e6",
      600: "#175ab4",
      700: "#0d4182",
      800: "#042751",
      900: "#000f23",
    },
  },
});
