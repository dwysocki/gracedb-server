#! /usr/bin/env bash
set -e

# Ensure required environment variables are present
if [[ -z "${LVALERT_USER}" ]]; then
    echo "The environment variable \$LVALERT_USER must be set."
    exit 1
fi
if [[ -z "${LVALERT_PASSWORD}" ]]; then
    echo "The environment variable \$LVALERT_PASSWORD must be set."
    exit 1
fi
if [[ -z "${LVALERT_SERVER}" ]]; then
    echo "The environment variable \$LVALERT_SERVER must be set."
    exit 1
fi
if [[ -z "${LVALERT_OVERSEER_PORT}" ]]; then
    echo "The environment variable \$LVALERT_OVERSEER_PORT must be set."
    exit 1
fi

# Get directory for logs
LOG_DIR=$(dirname $(readlink -f "$0"))/../../logs

# Run LVAlert Overseer
lvalert_overseer --username="${LVALERT_USER}" \
    --password="${LVALERT_PASSWORD}" \
    --server="${LVALERT_SERVER}" \
    --port="${LVALERT_OVERSEER_PORT}" \
    --audit-filename="${LOG_DIR}/overseer_audit.log" \
    --error-filename="${LOG_DIR}/overseer_error.log"

#Send script to Tom with info about overseer stuff
#fix lvalert failover to use - do we need .netrc file still? or can use env vars?
#is the way in which the failover gets the credentials going to be any different from the way that the overseer script will?
