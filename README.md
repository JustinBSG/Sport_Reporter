# Sport Reporter

Discord bot, FastAPI backend, and PostgreSQL match storage.

Start with the [detailed Railway setup tutorial](docs/railway-setup.md). It covers
Discord application creation, the three Railway services, environment variables,
SQL migrations, demo seeding, validation, backups, and troubleshooting.

- [Backend code and local setup](backend/README.md)
- [Discord bot code and local setup](dc_bot/README.md)
- [PostgreSQL schema](backend/app/migrations/001_matches.sql)

The starter verifies the full Discord → API → PostgreSQL connection using
explicitly fictional fixtures. Live sports extraction and automatic scheduled
notifications remain future work.
