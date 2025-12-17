
.PHONY: up up-local build pull clean clean-local rebuild

DIRS := db_data logs

# Pull pre-built image and run
up: $(DIRS)
	@docker compose pull gracedb
	@docker compose up

# Build locally and run
up-local: $(DIRS)
	@docker compose -f docker-compose.yml -f docker-compose.build.yml up

$(DIRS):
	@mkdir -p $@

# Build local image
build:
	@docker compose -f docker-compose.yml -f docker-compose.build.yml build

# Pull pre-built image from registry
pull:
	@docker compose pull gracedb

# Clean up containers and registry image
clean:
	@docker compose down
	@docker rmi -f containers.ligo.org/computing/gracedb/server:$${GRACEDB_TAG:-latest} 2>/dev/null || true

# Clean up containers and local image
clean-local:
	@docker compose -f docker-compose.yml -f docker-compose.build.yml down
	@docker rmi -f gracedb-local 2>/dev/null || true

# Rebuild local image
rebuild: clean-local build
