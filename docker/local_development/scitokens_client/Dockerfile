# GraceDB SciToken Client Container
#
# A lightweight Python container for testing GraceDB with SciToken authentication.
# Includes ligo-gracedb and igwn-alert packages.
#
# Build: docker build -t gracedb-scitokens-client -f Dockerfile .
# Run:   docker run -it --rm gracedb-scitokens-client

FROM python:3.13-slim

LABEL maintainer="LIGO Computing"
LABEL description="GraceDB client with SciToken authentication for testing"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
# - ligo-gracedb: GraceDB client library
# - igwn-alert: IGWN alert system client
# - cryptography: for token signing (already a dependency, but ensure it's there)
RUN pip install --no-cache-dir \
    ligo-gracedb \
    igwn-alert \
    cryptography

# Create directories
RUN mkdir -p /app /tokens /issuer

# Copy the token generation script
COPY generate-token.py /app/generate-token.py
RUN chmod +x /app/generate-token.py

# Copy the entrypoint script
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Set working directory
WORKDIR /app

# Environment variables (can be overridden at runtime)
# BEARER_TOKEN_FILE follows WLCG Bearer Token Discovery specification
ENV BEARER_TOKEN_FILE=/tmp/bt_u0
ENV GRACEDB_SERVICE_URL=http://gracedb/api/
ENV TOKEN_ISSUER=https://gracedb-scitokens-issuer:8443
ENV TOKEN_SUBJECT=test_user
ENV TOKEN_SCOPE=gracedb.read
ENV TOKEN_AUDIENCE=ANY
ENV TOKEN_LIFETIME=3600

# The entrypoint generates a fresh token and then runs the command
ENTRYPOINT ["/app/entrypoint.sh"]

# Default command: interactive shell
CMD ["/bin/bash"]
