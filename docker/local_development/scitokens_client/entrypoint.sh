#!/bin/bash
#
# Entrypoint for GraceDB SciToken Client Container
#
# Generates a fresh SciToken on container start, then executes the provided command.
#

set -e

echo "========================================"
echo "GraceDB SciToken Client Container"
echo "========================================"

# Generate a fresh SciToken
# BEARER_TOKEN_FILE follows WLCG Bearer Token Discovery specification
echo "Generating SciToken..."
python3 /app/generate-token.py \
    --issuer "${TOKEN_ISSUER}" \
    --subject "${TOKEN_SUBJECT}" \
    --scope "${TOKEN_SCOPE}" \
    --audience "${TOKEN_AUDIENCE}" \
    --lifetime "${TOKEN_LIFETIME}" \
    --key /issuer/keys/scitoken_private.pem \
    --jwks /issuer/keys/scitoken_public.jwks \
    --output "${BEARER_TOKEN_FILE}"

# Export BEARER_TOKEN_FILE so child processes can find it
export BEARER_TOKEN_FILE="${BEARER_TOKEN_FILE}"

# Trust the issuer's certificate
if [ -f /issuer/certs/server.crt ]; then
    export SSL_CERT_FILE=/issuer/certs/server.crt
    export REQUESTS_CA_BUNDLE=/issuer/certs/server.crt
    echo "Trusting issuer certificate: /issuer/certs/server.crt"
fi

echo ""
echo "Environment configured:"
echo "  BEARER_TOKEN_FILE=${BEARER_TOKEN_FILE}"
echo "  GRACEDB_SERVICE_URL=${GRACEDB_SERVICE_URL}"
echo "  SSL_CERT_FILE=${SSL_CERT_FILE:-not set}"
echo ""
echo "Quick test commands:"
echo "  gracedb ping"
echo "  gracedb credentials client"
echo "  gracedb credentials server"
echo ""
echo "========================================"
echo ""

# Execute the provided command (or default to bash)
exec "$@"
