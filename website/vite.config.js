import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
    root: './',
    build: {
        rollupOptions: {
            input: {
                main: resolve(__dirname, 'index.html'),
                docs: resolve(__dirname, 'docs.html'),
                pricing: resolve(__dirname, 'pricing.html'),
                contact: resolve(__dirname, 'contact.html'),
            },
        },
    },
});
