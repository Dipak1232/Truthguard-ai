import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    include: ["server/truthguard.test.ts"],
    environment: "node",
    coverage: {
      provider: "v8",
      reporter: ["text", "json-summary"],
      reportsDirectory: "coverage",
      include: ["server/pythonTestRunner.ts"],
    },
  },
});
