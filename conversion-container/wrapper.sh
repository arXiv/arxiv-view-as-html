#!/bin/sh
/cloudsql/cloud-sql-proxy arxiv-production:us-central1:latexml-db -c credentials/html-conversion-prod-key.json -u /cloudsql &
/cloudsql/cloud-sql-proxy arxiv-production:us-east4:arxiv-production-rep4 -c credentials/arxiv-browse-cloud-run-prod-key.json -u /cloudsql &

gunicorn --bind 0.0.0.0:8000 -t 600 -w 16 --threads 1 entry_point:app
