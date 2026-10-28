import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // @suite/* are symlinked from Life and would load Life's own React: pre-bundle
  // them with esbuild, deduping React to this app's single copy.
  resolve: { dedupe: ["react", "react-dom"] },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    deps: {
      optimizer: {
        web: {
          enabled: true,
          include: ["@suite/design-system", "@suite/i18n"],
        },
      },
    },
  },
});
