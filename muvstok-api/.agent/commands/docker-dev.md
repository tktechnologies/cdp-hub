# Docker Development Commands

## Start Local Stack

```bash
docker compose -f docker/docker-compose.yml up --build
```

Services:

- API on port `8000`
- Worker container
- Redis on port `6379`
- PostgreSQL on port `5432`

Local Docker is for development feedback. It does not replace Azure-hosted validation.
