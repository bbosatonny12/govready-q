#!/bin/bash

# This script is activated by the Procfile, which is the main
# starting point for the container that runs the application.

set -euf -o pipefail # abort script on error

# Create src/local/environment.json using environment variables
# providing runtime settings. This file is read by our settings.py.
python save_environment_json_file.py

cd src

# Run database maintenance but only on "instance zero", so that
# if we scale up to multiple instances we don't execute this
# concurrently on each container. TODO: If there are any migrations,
# then we should probably not do a zero-downtime-deployment which
# would keep old code running after the database schema becomes
# inconsistent with the running code.
if [ "$CF_INSTANCE_INDEX" == "0" ]; then
	python manage.py migrate --no-input
	python manage.py load_modules
fi

# Prepare static assets. TODO: This should probably be done so
# that the output is shared across containers, rather than repeated
# on each container. The output maybe can be different? We're
# using the ManifestStaticFilesStorage which rewrites static file
# names with hashes. Hopefully each container generates the same
# hash.
python manage.py collectstatic --noinput

# Check that everything looks OK.
python manage.py check --deploy

# On instance zero, run send_notification_emails in the background.
if [ "$CF_INSTANCE_INDEX" == "0" ]; then
	nohup python manage.py send_notification_emails forever &
fi

# Start Django.
gunicorn siteapp.wsgi --access-logfile -
