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
                en_main: resolve(__dirname, 'en/index.html'),
                en_docs: resolve(__dirname, 'en/docs.html'),
                en_pricing: resolve(__dirname, 'en/pricing.html'),
                en_contact: resolve(__dirname, 'en/contact.html'),
            },
        },
    },
});
