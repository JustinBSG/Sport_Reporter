# Sport Reporter

Sport Reporter has a Discord bot, a FastAPI backend, and PostgreSQL storage for
sports matches. The backend is the API service between the bot and the database.

Start with the [Railway setup guide](docs/railway-setup.md). It explains how to
create the Discord application and deploy the three services. It also covers
environment variables, database migrations, demo data, checks, backups, and
troubleshooting.

- [Backend setup and API reference](backend/README.md)
- [Discord bot setup and commands](dc_bot/README.md)
- [PostgreSQL database schema](backend/app/migrations/001_matches.sql)

The current application uses fictional demo matches to check the connection from
Discord through the API to PostgreSQL. Demo records have `is_demo=true`.

The application does not collect live sports data or send scheduled
notifications. These features require more development.
