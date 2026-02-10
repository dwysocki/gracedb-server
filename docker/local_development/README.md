# GraceDB Local Development Environment

This directory contains Docker Compose configurations and a Makefile to manage your local GraceDB development environment.

## Overview

The setup supports two primary workflows:

1. **Standalone Mode**: GraceDB + Postgres only (no SciToken authentication)
   - Suitable for basic development and testing
   - Uses `DJANGO_PRIMARY_FQDN=localhost`
   - No issuer container required

2. **Client Mode**: Full stack with SciToken authentication
   - GraceDB + Postgres + Local SciToken Issuer + Client container
   - Uses `DJANGO_PRIMARY_FQDN=gracedb` for proper hostname resolution
   - Client container pre-configured with SciToken authentication
   - Automatically updates Site domain when DJANGO_PRIMARY_FQDN changes

For each workflow, you can choose between:
- **Registry Mode**: Pull pre-built GraceDB images from `containers.ligo.org`
- **Local Build Mode**: Build GraceDB from source for testing unreleased changes

## Quick Start

### Standalone Mode (No SciTokens)

```bash
# Pull and run from registry
make up

# Or build and run locally
make up-local
```

Access GraceDB at http://localhost

### Client Mode (With SciTokens)

```bash
# Pull and run from registry
make client

# Or build and run locally (for testing unreleased changes)
make client-local
```

Inside the client container, test the connection:
```bash
gracedb ping
gracedb credentials client
gracedb credentials server
```

## Available Commands

Run `make help` to see all available commands.

### Basic Commands (Standalone Mode)

| Command | Description |
|---------|-------------|
| `make up` | Pull and run GraceDB from registry (DJANGO_PRIMARY_FQDN=localhost) |
| `make up-local` | Build and run GraceDB locally (DJANGO_PRIMARY_FQDN=localhost) |
| `make build` | Build the local GraceDB Docker image |
| `make pull` | Pull the pre-built GraceDB image from registry |
| `make clean` | Stop containers and remove registry image |
| `make clean-local` | Stop containers and remove local image |
| `make clean-all` | Remove all containers, volumes, and local data (full reset) |
| `make rebuild` | Clean and rebuild the local image |

### SciToken Issuer Commands

| Command | Description |
|---------|-------------|
| `make setup-issuer` | Clone issuer repo and generate certs/keys |
| `make update-issuer` | Pull latest issuer code and regenerate |
| `make clean-issuer` | Remove issuer repo and generated files |

The issuer setup is required for client mode. It:
- Clones the local-issuer repository
- Generates SSL certificates for `gracedb-scitokens-issuer`
- Generates RSA signing keys for SciTokens
- Creates JWKS and OpenID configuration files

### Client Commands (With SciTokens)

| Command | Description |
|---------|-------------|
| `make client` | Start full stack with registry GraceDB image |
| `make client-local` | Start full stack with locally built GraceDB image |
| `make client-build` | Build the client container image |
| `make client-shell` | Get a shell in a running client container |

Client mode automatically:
- Starts the local SciToken issuer
- Configures GraceDB with `DJANGO_PRIMARY_FQDN=gracedb`
- Generates a fresh SciToken with `audience=ANY` on startup
- Configures the client with `GRACEDB_SERVICE_URL=http://gracedb/api/`

## Deployment Modes Explained

### Registry Mode vs Local Build Mode

**Registry Mode** (default for `make up` and `make client`):
- Pulls pre-built images from `containers.ligo.org/computing/gracedb/server`
- Source code is baked into the image
- Does not mount local source code
- Use `GRACEDB_TAG` environment variable to specify version:
  ```bash
  GRACEDB_TAG=gracedb-2.34.0 make up
  ```

**Local Build Mode** (`make up-local` and `make client-local`):
- Builds Docker image locally from source
- Mounts project root (`../../`) as `/app/gracedb_project/` for live development
- Changes to source code are immediately reflected
- Ideal for testing unreleased changes

### Standalone Mode vs Client Mode

**Standalone Mode** (`make up` / `make up-local`):
- Starts only GraceDB and Postgres containers
- No SciToken issuer
- Uses `DJANGO_PRIMARY_FQDN=localhost`
- Suitable for basic development without authentication testing

**Client Mode** (`make client` / `make client-local`):
- Starts GraceDB + Postgres + SciToken Issuer + Client container
- Uses `DJANGO_PRIMARY_FQDN=gracedb` for proper hostname resolution
- Client container automatically generates fresh SciTokens
- Required for testing SciToken authentication workflows

## Architecture Details

### Docker Compose Configuration

- **docker-compose.yml**: Base configuration
  - Defines gracedb, postgres, gracedb-scitokens-issuer (client profile), and gracedb-scitokens-client (client profile) services
  - Issuer and client use the `client` profile and only start when `--profile client` is specified

- **docker-compose.build.yml**: Local build overrides
  - Overrides gracedb image with local build (`gracedb-local`)
  - Mounts source code for live development

### Volumes

Both modes use Docker named volumes for persistent data:

| Volume | Mount Point | Purpose |
|--------|-------------|---------|
| `postgres_data` | `/var/lib/postgresql/data` | Postgres database files |
| `gracedb_storage` | `/app/db_data` | GraceDB file storage |
| `gracedb_logs` | `/app/logs` | Application logs |
| `static_files` | `/app/gracedb_project/static_root` | Django static files |
| `issuer_certs` | `/app/certs` (gracedb), `/shared/certs` (issuer) | Shared SSL certificates for SciToken validation |

Additionally, the `db_data` and `logs` directories are created in this directory for volume mount points.

### SciToken Client Container

The client container (`gracedb-scitokens-client`) is built from `./scitokens_client/Dockerfile` and includes:
- Python 3.13 with ligo-gracedb and igwn-alert packages
- Entrypoint script that generates a fresh SciToken on startup
- Pre-configured environment variables:
  - `TOKEN_ISSUER=https://gracedb-scitokens-issuer:8443`
  - `TOKEN_AUDIENCE=ANY`
  - `TOKEN_SCOPE=gracedb.read`
  - `GRACEDB_SERVICE_URL=http://gracedb/api/`

### DJANGO_PRIMARY_FQDN and Site Domain Sync

GraceDB uses Django's Sites framework, which stores the site domain in the database. The domain is set during the initial migration based on `DJANGO_PRIMARY_FQDN`.

To handle switching between standalone mode (`DJANGO_PRIMARY_FQDN=localhost`) and client mode (`DJANGO_PRIMARY_FQDN=gracedb`), the entrypoint script runs a management command that updates the Site domain to match the environment variable:

```bash
python3 manage.py update_site_domain
```

This ensures the database stays in sync with the container configuration.

## Example Workflows

### Basic Development (No SciTokens)

```bash
# Start the environment
make up -d

# Check logs
docker logs local_development-gracedb-1

# Access GraceDB at http://localhost
# Default credentials from django.env

# Stop when done
docker compose down
```

### Testing SciToken Authentication

```bash
# Clean start
make clean-all

# Start with client mode
make client

# Inside the client container:
gracedb ping
gracedb credentials client
gracedb credentials server

# Exit client container
exit

# Stop everything
docker compose --profile client down
```

### Testing Local Code Changes

```bash
# Make changes to gracedb source code

# Clean previous build
make clean-all

# Build and run with client mode
make client-local

# Test inside client container
gracedb ping
# ... run tests ...

# Exit and iterate
exit
make clean-all
# ... make more changes ...
make client-local
```

### Switching Between Modes

```bash
# Start in standalone mode
make up -d

# Verify Site domain is "localhost"
docker exec local_development-gracedb-1 \
  python3 manage.py shell -c "from django.contrib.sites.models import Site; print(Site.objects.get(id=1).domain)"

# Stop and switch to client mode
docker compose down -v  # -v removes volumes for clean slate
make client

# Inside client, verify Site domain is now "gracedb"
# The update_site_domain command handles this automatically
```

## Troubleshooting

### Cleaning Up

If you encounter issues, try a complete cleanup:

```bash
make clean-all
```

This removes:
- All containers
- All named volumes (database, logs, static files, certs)
- Local directories (`db_data`, `logs`)

### Checking Logs

```bash
# GraceDB logs
docker logs local_development-gracedb-1

# Postgres logs
docker logs local_development-postgres-1

# Issuer logs (when running client mode)
docker logs local_development-gracedb-scitokens-issuer-1

# Client logs (when running client mode)
docker logs local_development-gracedb-scitokens-client-1
```

### Verifying SciToken Setup

```bash
# Check if issuer is running
docker ps | grep issuer

# Verify issuer certificate exists
docker exec local_development-gracedb-scitokens-issuer-1 \
  cat /shared/certs/issuer.crt

# Check if gracedb has the certificate
docker exec local_development-gracedb-1 \
  ls -la /app/certs/

# Test token generation in client
docker exec -it local_development-gracedb-scitokens-client-1 \
  cat $BEARER_TOKEN_FILE
```

### Database Connection Issues

If you change Postgres credentials in `docker-compose.yml`, remove the volume:

```bash
docker compose down -v
```

### Site Domain Mismatch

If the Site domain doesn't match `DJANGO_PRIMARY_FQDN`, manually run:

```bash
docker exec local_development-gracedb-1 \
  python3 manage.py update_site_domain
```

Note: This only works when `LOCAL_BUILD=true` as a safety measure.

## Environment Variables

Key environment variables in `docker-compose.yml`:

| Variable | Default | Description |
|----------|---------|-------------|
| `GRACEDB_TAG` | `latest` | Tag for registry image |
| `DJANGO_PRIMARY_FQDN` | `localhost` (standalone), `gracedb` (client) | Primary FQDN for Django Sites |
| `LOCAL_BUILD` | `true` | Enables local development features |
| `TOKEN_AUDIENCE` | `ANY` | SciToken audience claim |
| `TOKEN_SUBJECT` | `test_user` | SciToken subject claim |
| `TOKEN_SCOPE` | `gracedb.read` | SciToken scope claim |

See `django.env` for additional Django configuration.

## Notes

- The issuer uses self-signed certificates suitable for development only
- Client container generates unsigned JWTs for local testing (not for production)
- Static files are collected automatically on container startup
- In local build mode, an empty `static_root/` directory is created in the project root as a mount point (gitignored)
- The `--profile client` flag controls whether issuer and client containers start

## Further Reading

- [SciToken Authentication Documentation](../../docs/scitokens.md) (if available)
- [Docker Compose Profiles](https://docs.docker.com/compose/profiles/)
- [Django Sites Framework](https://docs.djangoproject.com/en/stable/ref/contrib/sites/)
