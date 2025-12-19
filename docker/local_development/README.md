# Local Development Makefile Commands

This directory contains a Makefile to help manage your local GraceDB + Postgres development environment using Docker Compose.

## Deployment Modes

This setup supports two deployment modes:

1. **Registry Mode (default)**: Pull and run a pre-built image from `containers.ligo.org/computing/gracedb/server`
   - The source code is baked into the image
   - Does not mount the local source code directory
   - Default tag is `latest`
   - To use a specific version, set the `GRACEDB_TAG` environment variable:
     ```bash
     GRACEDB_TAG=gracedb-2.34.0 make up
     ```

2. **Local Build Mode**: Build the Docker image locally from source
   - Mounts the project root (`../../` relative to `docker/local_development/`) as `/app/gracedb_project/` for live development
   - Changes to source code are immediately reflected in the running container

## Commands

### Registry Mode (Pull Pre-built Image)

- **make up**
  - Pulls the pre-built image from the registry, creates required directories (`db_data`, `logs`) if missing, then starts the GraceDB and Postgres containers using Docker Compose.

- **make pull**
  - Explicitly pulls the pre-built GraceDB image from the registry without starting containers.

- **make clean**
  - Stops and removes all containers, and deletes the registry image. Does not remove Docker volumes (database data is preserved).

### Local Build Mode

- **make up-local**
  - Builds the Docker image locally from source (if needed), creates required directories, then starts the GraceDB and Postgres containers.

- **make build**
  - Builds and tags the local Docker container for GraceDB using the Dockerfile in the project root.

- **make clean-local**
  - Stops and removes all containers, and deletes the local `gracedb-local` image. Does not remove Docker volumes (database data is preserved).

- **make rebuild**
  - Runs `make clean-local` followed by `make build` to force a full rebuild of the local container image.

## Notes

- **Volume Mounts**:
  - Both modes mount `gracedb_storage`, `gracedb_logs`, and `static_files` for persistent data
  - `static_files` volume is mounted at `/app/gracedb_project/static_root` for Django static files
  - Django's `collectstatic` runs automatically at container startup to populate static files
  - Local build mode additionally mounts the project source code (`../../` = project root) to `/app/gracedb_project/` for development
  - Registry mode does not mount source code since it's already in the image
  - **Note**: In local build mode, an empty `static_root/` directory will be created in the project root as a mount point. This directory is gitignored and can be safely ignored - the actual static files are stored in the Docker volume, not this folder.

- If you change the Postgres credentials or database name in `docker-compose.yml`, you may need to remove the Docker volume to re-initialize the database:
  ```sh
  docker compose down -v
  ```
- To remove all volumes including static files (useful if static files become corrupted):
  ```sh
  docker compose down -v
  ```
  Note: This will delete all persistent data including the database.
- The `db_data` and `logs` directories are created automatically if they do not exist.
- To change the registry image path, update the `image:` line in `docker-compose.yml` and the registry path in the Makefile `clean` target.
- To use a different image tag, set `GRACEDB_TAG` environment variable (e.g., `GRACEDB_TAG=gracedb-2.34.0 make up`).


