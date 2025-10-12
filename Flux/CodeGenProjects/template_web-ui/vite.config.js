import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig(({ mode }) => {
  return {
    plugins: [react()],

    esbuild: {
      loader: 'jsx',
      include: /src\/.*\.jsx?$/,
      exclude: [],
    },

    server: {
      port: 3020,  // Default port - should be overridden per project
      open: false,
      cors: true,
    },

    build: {
      outDir: 'build',
      sourcemap: mode === 'development',
      rollupOptions: {
        output: {
          manualChunks: {
            'vendor-react': ['react', 'react-dom', 'react-redux'],
            'vendor-mui': ['@mui/material', '@mui/icons-material'],
            'vendor-charts': ['echarts', 'plotly.js'],
          }
        }
      },
      worker: {
        format: 'es',
      }
    },

    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
        '@components': path.resolve(__dirname, './src/components'),
        '@utils': path.resolve(__dirname, './src/utils'),
        '@hooks': path.resolve(__dirname, './src/hooks'),
        '@workers': path.resolve(__dirname, './src/workers'),
      }
    },

    optimizeDeps: {
      esbuildOptions: {
        loader: {
          '.js': 'jsx',
        },
      },
      include: [
        'react',
        'react-dom',
        'react-redux',
        '@reduxjs/toolkit',
        '@mui/material',
        'echarts',
        'lodash',
      ]
    }
  };
});
