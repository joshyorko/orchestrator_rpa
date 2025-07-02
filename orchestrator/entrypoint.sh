#!/bin/sh

# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate

# Start the main process
exec "$@"
