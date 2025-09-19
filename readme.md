# Phelia Frontend

A dark-first, self-hostable media UI inspired by Lampa. Built with React 18, Vite, TailwindCSS, and TanStack Query to browse movies, TV shows, and music served by the Phelia API.

## Features

- Responsive application shell with collapsible sidebar, global search, command palette, and keyboard navigation.
- Hero carousel, infinite catalog grids, rail layouts, and rich detail dialogs for movies, TV shows, and albums.
- Filters with URL state (sort, year, genre, type) and scoped search.
- Continue Watching, Trending, and Music discovery rails on Home.
- Library, Downloads, and Settings (appearance + service status) pages.
- Command palette (`⌘K` / `Ctrl+K`) for navigation and search.
- Custom theme tokens, system theme detection, and accent color variable (`--accent`).
- Docker image for static hosting with SPA routing; `docker-compose` snippet for running beside the API.
- Vitest + Testing Library coverage for critical UI primitives.

## Getting started

### Prerequisites

- Node.js 20+
- npm 10+

### Environment

Create `.env` (or set shell variable) with the API base URL. The frontend only needs one variable:

```bash
export VITE_API_BASE="http://localhost:8000/api/v1"
```

### Install dependencies

From `apps/web`:

```bash
npm install
```

> **Note:** If your environment blocks scoped npm packages (e.g., `@tanstack/*`), configure npm to use a mirror or private registry that exposes these packages before installing.

### Development

```bash
npm run dev
```

Vite serves the app at `http://localhost:5173`.

### Tests & linting

```bash
npm run lint
npm test
```

### Build

```bash
npm run build
npm run preview
```

## Docker

Build a production image:

```bash
docker build -t phelia-web ./apps/web
```

Run with the API (example `docker-compose.yml` excerpt):

```yaml
services:
  web:
    image: phelia-web:latest
    environment:
      VITE_API_BASE: "http://api:8000/api/v1"
    ports:
      - "5173:80"
    depends_on:
      - api
```

The image uses Nginx with SPA fallback.

## Theming

Design tokens live in `src/styles/tokens.css`. Override any CSS variable (e.g., `--accent`) at runtime or inject custom values via host CSS to theme the application.

## Testing strategy

- Component unit tests (Vitest + Testing Library) for `MediaCard`, `FiltersBar`, `GlobalSearch`, and `DetailDialog`.
- Hooks tested individually where appropriate.

## Folder structure

```
apps/web
├── public/              Static assets
├── src/
│   ├── app/
│   │   ├── components/  Reusable UI + layout pieces
│   │   ├── hooks/       Shared hooks (query params, keyboard nav, etc.)
│   │   ├── lib/         API client, types, i18n setup
│   │   └── routes/      Route components
│   └── styles/          Tailwind & global styles
```

## API contract

All data flows through `${VITE_API_BASE}`. See `src/app/lib/api.ts` for the typed client. The frontend does not store API keys; backend services proxy third-party integrations.

