
.PHONY: up up-local build pull clean clean-local clean-all rebuild \
        setup-issuer update-issuer clean-issuer \
        client client-local client-build client-shell help

DIRS := db_data logs

# =============================================================================
# SciToken Issuer Configuration
# =============================================================================
ISSUER_REPO     := git@git.ligo.org:computing/gracedb/kafka-e2e/local-issuer.git
ISSUER_BRANCH   := main
ISSUER_DIR      := ./local-issuer
ISSUER_HTDOCS   := ./issuer-htdocs
ISSUER_HOSTNAME := gracedb-scitokens-issuer
ISSUER_PORT     := 8443
ISSUER_URL      := https://$(ISSUER_HOSTNAME):$(ISSUER_PORT)

# =============================================================================
# Main Targets
# =============================================================================

help:
	@echo "GraceDB Local Development Environment"
	@echo ""
	@echo "Basic Commands (standalone mode, no SciTokens):"
	@echo "  make up              - Pull and run GraceDB from registry (DJANGO_PRIMARY_FQDN=localhost)"
	@echo "  make up-local        - Build and run GraceDB locally (DJANGO_PRIMARY_FQDN=localhost)"
	@echo "  make clean           - Stop containers and remove registry image"
	@echo "  make clean-all       - Remove all containers, volumes, and local data (full reset)"
	@echo ""
	@echo "SciToken Issuer Commands:"
	@echo "  make setup-issuer    - Clone issuer repo and generate certs/keys"
	@echo "  make update-issuer   - Pull latest issuer code and regenerate"
	@echo "  make clean-issuer    - Remove issuer repo and generated files"
	@echo ""
	@echo "Client Commands (with SciTokens):"
	@echo "  make client          - Start issuer + gracedb (registry) + client with SciToken auth"
	@echo "  make client-local    - Start issuer + gracedb (local build) + client with SciToken auth"
	@echo "  make client-build    - Build the client container image"
	@echo "  make client-shell    - Get a shell in a running client container"
	@echo ""
	@echo "Example workflows:"
	@echo "  Standalone (legacy):  make up -d              # GraceDB without SciTokens"
	@echo "  With SciTokens:       make client             # Full stack with auth (registry image)"
	@echo "  Testing local changes: make client-local      # Full stack with auth (local build)"
	@echo ""
	@echo "Notes:"
	@echo "  - Standalone mode uses DJANGO_PRIMARY_FQDN=localhost (no issuer)"
	@echo "  - Client mode uses DJANGO_PRIMARY_FQDN=gracedb (with issuer)"
	@echo "  - Inside client container, GraceDB is at: http://gracedb/api/"
	@echo "  - Client is pre-configured with GRACEDB_SERVICE_URL and BEARER_TOKEN_FILE"

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

# Complete cleanup: remove all containers, volumes, and local data
clean-all:
	@echo "Removing all containers, volumes, and local data..."
	@docker compose down -v --remove-orphans
	@docker compose -f docker-compose.yml -f docker-compose.build.yml down -v --remove-orphans 2>/dev/null || true
	@rm -rf db_data logs
	@echo "Clean complete. Ready for fresh start."

# Rebuild local image
rebuild: clean-local build

# =============================================================================
# SciToken Issuer Setup
# =============================================================================

# Clone issuer repo and generate all necessary files
setup-issuer: $(ISSUER_DIR) $(ISSUER_DIR)/certs/server.crt $(ISSUER_DIR)/keys/scitoken_private.pem $(ISSUER_HTDOCS)/.well-known/scitoken.jwks

# Clone the local-issuer repository
$(ISSUER_DIR):
	@echo "Cloning local-issuer repository..."
	@git clone -b $(ISSUER_BRANCH) $(ISSUER_REPO) $(ISSUER_DIR)

# Generate SSL certificates with Docker hostname
$(ISSUER_DIR)/certs/server.crt: $(ISSUER_DIR)
	@echo "Generating SSL certificates for $(ISSUER_HOSTNAME)..."
	@mkdir -p $(ISSUER_DIR)/certs
	@openssl req -x509 -newkey rsa:2048 \
		-keyout $(ISSUER_DIR)/certs/server.key \
		-out $(ISSUER_DIR)/certs/server.crt \
		-days 365 -nodes \
		-subj "/CN=$(ISSUER_HOSTNAME)" 2>/dev/null
	@echo "Certificate generated with CN=$(ISSUER_HOSTNAME)"

# Generate signing keys
$(ISSUER_DIR)/keys/scitoken_private.pem: $(ISSUER_DIR)
	@echo "Generating signing keys..."
	@cd $(ISSUER_DIR) && make keys

# Create docker-specific htdocs with correct issuer URL
$(ISSUER_HTDOCS)/.well-known/scitoken.jwks: $(ISSUER_DIR)/keys/scitoken_private.pem
	@echo "Creating docker-specific htdocs..."
	@mkdir -p $(ISSUER_HTDOCS)/.well-known
	@cp $(ISSUER_DIR)/htdocs/index.html $(ISSUER_HTDOCS)/ 2>/dev/null || true
	@cd $(ISSUER_DIR) && make jwks
	@cp $(ISSUER_DIR)/keys/scitoken_public.jwks $(ISSUER_HTDOCS)/.well-known/scitoken.jwks
	@echo '{"issuer":"$(ISSUER_URL)","jwks_uri":"$(ISSUER_URL)/.well-known/scitoken.jwks","token_endpoint":"$(ISSUER_URL)/token","response_types_supported":["token"],"subject_types_supported":["public"],"id_token_signing_alg_values_supported":["RS256"]}' | python3 -m json.tool > $(ISSUER_HTDOCS)/.well-known/openid-configuration

# Update issuer repo and regenerate files
update-issuer:
	@if [ -d "$(ISSUER_DIR)" ]; then \
		echo "Updating local-issuer repository..."; \
		cd $(ISSUER_DIR) && git pull origin $(ISSUER_BRANCH); \
	else \
		echo "Issuer not set up. Run 'make setup-issuer' first."; \
		exit 1; \
	fi
	@rm -f $(ISSUER_HTDOCS)/.well-known/scitoken.jwks
	@$(MAKE) $(ISSUER_HTDOCS)/.well-known/scitoken.jwks

# Clean up issuer files
clean-issuer:
	@echo "Removing issuer files..."
	@rm -rf $(ISSUER_DIR) $(ISSUER_HTDOCS)

# =============================================================================
# SciToken Client
# =============================================================================

# Build the client container image
client-build: setup-issuer
	@echo "Building client container..."
	@docker compose --profile client build gracedb-scitokens-client

# Run interactive client with fresh SciToken (uses registry image)
# This will start gracedb, issuer, and client together
client: setup-issuer client-build
	@echo "Starting client environment (gracedb + issuer + client)..."
	@DJANGO_PRIMARY_FQDN=gracedb SSL_CERT_FILE=/app/certs/issuer.crt REQUESTS_CA_BUNDLE=/app/certs/issuer.crt \
		docker compose --profile client up -d gracedb postgres gracedb-scitokens-issuer
	@echo "Waiting for services to be ready..."
	@sleep 3
	@docker compose --profile client run --rm gracedb-scitokens-client

# Run interactive client with locally built gracedb (for testing unreleased changes)
client-local: setup-issuer client-build
	@echo "Starting client environment with locally built gracedb..."
	@DJANGO_PRIMARY_FQDN=gracedb SSL_CERT_FILE=/app/certs/issuer.crt REQUESTS_CA_BUNDLE=/app/certs/issuer.crt \
		docker compose -f docker-compose.yml -f docker-compose.build.yml --profile client up -d gracedb postgres gracedb-scitokens-issuer
	@echo "Waiting for services to be ready..."
	@sleep 3
	@docker compose --profile client run --rm gracedb-scitokens-client

# Get a shell in a running client container
client-shell:
	@docker compose --profile client exec gracedb-scitokens-client /bin/bash
