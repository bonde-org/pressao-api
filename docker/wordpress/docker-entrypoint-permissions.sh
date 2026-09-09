#!/bin/bash
set -e

UPLOADS_DIR="/var/www/html/wp-content/uploads"

mkdir -p "$UPLOADS_DIR"
chown -R www-data:www-data "$UPLOADS_DIR" 2>/dev/null || true
chmod -R ug+rwX "$UPLOADS_DIR" 2>/dev/null || true

exec docker-entrypoint.sh "$@"
