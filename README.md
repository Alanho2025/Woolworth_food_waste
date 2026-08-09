# FoodFlow platform foundation

This repository is the PostgreSQL-backed foundation for the KiwiHarvest FoodFlow platform. The previous demo implementation and its feature-specific data, contracts, seed command, local database, and AI integration have been removed.

The foundation contains only:

- a minimal Next.js application;
- a minimal FastAPI application with a health endpoint;
- Docker Compose with PostgreSQL 16;
- SQLAlchemy models for the current Phase 1–8 relational schema;
- Alembic migrations and PostgreSQL migration verification tests;
- the local development and CI quality tooling needed to start the next feature.

The repository does not include seed data, API workflow services, or AI integration yet. `npm run dev:backend` starts PostgreSQL and waits for readiness; it does not run migrations automatically or write data.

## Documentation

- [Database design research](docs/database-design-research.md)：KiwiHarvest / FoodFlow 的 database boundary、research evidence 和 first-slice design decisions。
- [Python database foundation](docs/python-database-foundation.md)：用 Python、SQLAlchemy 和 Alembic 建立 PostgreSQL schema 的讀法，包含 model、migration、connection、session 和驗證命令。
- [Database testing interview notes](docs/database-testing-interview-notes.md)：database testing 的面試複習版，包含測試面向、原因、分層、代表案例和常見追問。
- [Evidence-backed ETL plan（XML-tagged）](docs/evidence-backed-etl-plan-xml.md)：先 ETL 公開真實資料，再以有 evidence、rule、range、confidence 和 deterministic seed 的 simulation 補足 local realistic demo 所缺的 operational facts。

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
npm run db:migrate
npm run db:migrate:check
npm run backend:test
npm run quality
```

Migration commands can also be run directly:

```bash
uv run alembic upgrade head
uv run alembic downgrade base
uv run alembic check
```

The next implementation phase will define the KiwiHarvest/Woolworths driver workflow, the human-in-the-loop boundaries, the Agent Harness, and the new domain data model. Those product decisions are deliberately not represented in this foundation.
