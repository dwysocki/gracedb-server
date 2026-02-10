# GraceDB Systemd Deployment

This directory contains files for deploying GraceDB as a systemd-managed Docker Compose service.

## Directory Contents

| File | Description |
|------|-------------|
| `docker-compose.yml` | Production Docker Compose configuration |
| `gracedb.env.example` | Template environment file (copy to `gracedb.env`) |
| `gracedb.service` | Systemd unit file |
| `README.md` | This documentation |

## Prerequisites

- Docker Engine 20.10+
- Docker Compose plugin (`docker compose` command)
- systemd
- Root or sudo access

### Verify Prerequisites

```bash
docker --version
docker compose version
systemctl --version
```

## Installation

### 1. Create Deployment Directory

```bash
sudo mkdir -p /opt/gracedb
```

### 2. Copy Deployment Files

```bash
sudo cp docker-compose.yml /opt/gracedb/
sudo cp gracedb.env.example /opt/gracedb/gracedb.env
```

### 3. Configure Environment

Edit the environment file with your deployment-specific values:

```bash
sudo vim /opt/gracedb/gracedb.env
```

**Required changes:**

| Variable | Description |
|----------|-------------|
| `DJANGO_PRIMARY_FQDN` | Your server's fully qualified domain name |
| `DJANGO_SECRET_KEY` | Unique secret key (generate with command below) |
| `POSTGRES_PASSWORD` | Strong database password |
| `DJANGO_DB_PASSWORD` | Same as `POSTGRES_PASSWORD` |
| `CONFIG_NAME` | Instance identifier (e.g., "GraceDB CIT") |

Generate a secret key:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

### 4. Install Systemd Service

```bash
sudo cp gracedb.service /etc/systemd/system/
sudo systemctl daemon-reload
```

### 5. Enable and Start Service

```bash
sudo systemctl enable gracedb
sudo systemctl start gracedb
```

## Management Commands

### Check Service Status

```bash
sudo systemctl status gracedb
```

### View Logs

```bash
# Follow systemd journal
sudo journalctl -u gracedb -f

# View container logs directly
cd /opt/gracedb && sudo docker compose logs -f
```

### Stop Service

```bash
sudo systemctl stop gracedb
```

### Restart Service

```bash
sudo systemctl restart gracedb
```

## Update Procedure

### Standard Update (Same Tag)

If using `latest` or the same tag, restart pulls the newest image:

```bash
sudo systemctl restart gracedb
```

### Update to Specific Version

1. Edit the environment file:

```bash
sudo vim /opt/gracedb/gracedb.env
# Add or modify: GRACEDB_TAG=v1.2.3
```

2. Restart the service:

```bash
sudo systemctl restart gracedb
```

### Manual Update with Downtime Control

For more control over the update process:

```bash
cd /opt/gracedb

# Stop the service
sudo systemctl stop gracedb

# Pull new images
sudo docker compose pull

# Start the service
sudo systemctl start gracedb
```

## Data Persistence

The following Docker volumes store persistent data:

| Volume | Purpose |
|--------|---------|
| `postgres_data` | PostgreSQL database |
| `gracedb_storage` | GraceDB file storage |
| `gracedb_logs` | Application logs |
| `static_files` | Static web assets |

### Backup

```bash
# Stop service before backup
sudo systemctl stop gracedb

# Backup volumes (example using tar)
sudo docker run --rm \
  -v deployment_postgres_data:/data \
  -v /backup:/backup \
  alpine tar czf /backup/postgres_data_$(date +%Y%m%d).tar.gz /data

# Restart service
sudo systemctl start gracedb
```

### View Volume Data

```bash
docker volume ls | grep deployment
docker volume inspect deployment_postgres_data
```

### Manual Steps After Container is Deployed

Before logging in on the web, enter the GraceDB container and sync against
the ldap.

1. Assuming that the LDAP's keytab is base64-encoded and has been copied and in your clipboard:

```bash
source /user/local/bin/entrypoint
echo "<pasted content>" | base64 -d > /app/db_data/ldap_keytab
chmod 600 /app/db_data/ldap_keytab
kinit ldap/gracedb.ligo.org@LIGO.ORG -k -t /app/db_data/ldap_keytab
```

2. Then hit the ldap:

```bash
source /usr/local/bin/cleanup
```

3. Upstream, make sure to create the required `igwn-alert` topics:

```
burst_cwb
burst_gwak
burst_mly
cbc_aframe
cbc_gstlal
cbc_mbta
cbc_pycbc
cbc_sgnl
cbc_spiir
external_fermi
external_snews
external_svom
external_swift
mdc_superevent
superevent
```

## Troubleshooting

### Service Fails to Start

1. Check systemd logs:

```bash
sudo journalctl -u gracedb -n 50 --no-pager
```

2. Check Docker Compose directly:

```bash
cd /opt/gracedb
sudo docker compose config  # Validate configuration
sudo docker compose up      # Run interactively to see errors
```

3. Verify environment file exists:

```bash
ls -la /opt/gracedb/gracedb.env
```

### Database Connection Issues

1. Check PostgreSQL health:

```bash
cd /opt/gracedb
sudo docker compose ps
sudo docker compose logs postgres
```

2. Verify database credentials match between `POSTGRES_*` and `DJANGO_DB_*` variables.

### Container Keeps Restarting

1. Check container logs:

```bash
cd /opt/gracedb
sudo docker compose logs gracedb
```

2. Verify all required environment variables are set.

### Port Already in Use

1. Check what's using the port:

```bash
sudo ss -tlnp | grep :80
```

2. Change `SERVICE_PORT` in `gracedb.env` to use a different port.

### Image Pull Failures

1. Verify network connectivity to container registry:

```bash
curl -I https://containers.ligo.org/v2/
```

2. Check Docker login if authentication is required:

```bash
docker login containers.ligo.org
```

## Security Considerations

- Keep `gracedb.env` file permissions restrictive: `chmod 600 /opt/gracedb/gracedb.env`
- Never commit `gracedb.env` to version control
- Use strong, unique passwords for database and Django secret key
- Consider running behind a reverse proxy with TLS termination
- Regularly update the Docker images for security patches

## Architecture

```
                    ┌─────────────────────────────────────────┐
                    │              systemd                     │
                    │         (gracedb.service)                │
                    └───────────────┬─────────────────────────┘
                                    │
                                    ▼
                    ┌─────────────────────────────────────────┐
                    │          Docker Compose                  │
                    └───────────────┬─────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
                    ▼                               ▼
        ┌───────────────────┐           ┌───────────────────┐
        │     gracedb       │           │     postgres      │
        │   (application)   │──────────▶│    (database)     │
        │                   │           │                   │
        │  Port: 80         │           │  Port: 5432       │
        │  (configurable)   │           │  (internal only)  │
        └───────────────────┘           └───────────────────┘
                    │                               │
                    ▼                               ▼
        ┌───────────────────┐           ┌───────────────────┐
        │  Docker Volumes   │           │  Docker Volumes   │
        │  - gracedb_storage│           │  - postgres_data  │
        │  - gracedb_logs   │           │                   │
        │  - static_files   │           │                   │
        └───────────────────┘           └───────────────────┘
```
