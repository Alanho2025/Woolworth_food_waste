# FoodFlow platform foundation

This repository is currently an intentionally empty application foundation for the next FoodFlow platform iteration. The previous demo implementation and its feature-specific data, contracts, seed command, local database, and AI integration have been removed.

The foundation contains only:

- a minimal Next.js application;
- a minimal FastAPI application with a health endpoint;
- Docker Compose with PostgreSQL 16;
- a PostgreSQL connection check and empty-database smoke test;
- the local development and CI quality tooling needed to start the next feature.

No business tables, SQLAlchemy models, seed data, migrations, or data migration steps are included yet. `npm run dev:backend` starts PostgreSQL and waits for readiness; it does not create tables or write data.

## Local setup

```bash
cp .env_example .env
npm install
npm --prefix frontend install
uv sync --all-extras
```

Start the services in separate terminals:

```bash
npm run dev:backend
npm run dev:frontend
```

The API health check is available at <http://localhost:8000/health> and the frontend at <http://localhost:3000>.

Useful commands:

```bash
npm run db:up
npm run db:down
npm run backend:test
npm run quality
```

The next implementation phase will define the KiwiHarvest/Woolworths driver workflow, the human-in-the-loop boundaries, the Agent Harness, and the new domain data model. Those product decisions are deliberately not represented in this foundation.
