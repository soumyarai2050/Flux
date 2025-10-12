# Template Web UI

This is a template React application built with [Vite](https://vitejs.dev/) for fast development and optimized production builds.

## Available Scripts

In the project directory, you can run:

### `npm start` or `npm run dev`

Runs the app in development mode with Vite's fast HMR (Hot Module Replacement).

The dev server typically starts in under 2 seconds. The page will update instantly when you make changes without losing component state.

### `npm test`

Launches the test runner in interactive watch mode (if tests are configured).

### `npm run build`

Builds the app for production to the `build` folder.

It correctly bundles React in production mode and optimizes the build for the best performance. The build is minified and filenames include content hashes for optimal caching.

### `npm run preview`

Previews the production build locally. Run `npm run build` first, then use this command to serve the built application.

## Configuration

### Vite Configuration

The project uses `vite.config.js` for build configuration. Key features:

- **Fast dev server**: ESM-based dev server with instant HMR
- **Optimized builds**: Rollup-based production builds
- **JSX support**: Automatic JSX transformation for `.js` and `.jsx` files
- **Modern output**: Generates optimized bundles for modern browsers

### Port Configuration

The dev server port is configured in `vite.config.js`:

```javascript
export default defineConfig({
  server: {
    port: 3000, // Default port (customize as needed)
  },
  // ... other config
})
```

### ESLint Configuration

ESLint is configured via `.eslintrc.js` in the project root.

## Project Structure

```
template_web-ui/
├── index.html          # Entry HTML file (root level for Vite)
├── vite.config.js      # Vite configuration
├── .eslintrc.js        # ESLint configuration
├── public/             # Static assets served as-is
│   ├── favicon.ico
│   ├── manifest.json
│   └── robots.txt
└── src/
    ├── index.jsx       # Application entry point
    ├── components/     # React components
    ├── containers/     # Container components
    ├── hooks/          # Custom React hooks
    └── services/       # API services and utilities
```

## Key Features

### Web Workers

The template includes optimized web worker support with Vite's module-based workers:

```javascript
const worker = new Worker(
  new URL('./worker.js', import.meta.url),
  { type: 'module' }
);
```

### Performance

- **Dev server**: Starts in <2 seconds
- **HMR**: Instant updates without full page reload
- **Production builds**: Optimized bundle sizes with tree-shaking and code splitting

## Learn More

- [Vite Documentation](https://vitejs.dev/)
- [React Documentation](https://react.dev/)
- [Vite Plugin React](https://github.com/vitejs/vite-plugin-react)
