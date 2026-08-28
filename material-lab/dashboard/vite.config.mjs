import { fileURLToPath, URL } from "node:url";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: {
    outDir: fileURLToPath(
      new URL("../src/printpilot_material_lab/dashboard_dist", import.meta.url),
    ),
    emptyOutDir: true,
    sourcemap: false,
  },
});
