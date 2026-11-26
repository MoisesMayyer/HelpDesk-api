import { defineConfig } from "vite";

const proxy = {
  "/api": {
    target: process.env.HELPDESK_API_ALVO || "http://127.0.0.1:8000",
    rewrite: (caminho) => caminho.replace(/^\/api(?=\/|$)/, ""),
  },
};

export default defineConfig({ base: "./", server: { proxy }, preview: { proxy } });
