FROM postgres:16-alpine

# Copy initialization scripts (auto-executed alphabetically on first start)
COPY init/ /docker-entrypoint-initdb.d/

# Defaults (override via docker-compose or -e flags)
# PRODUCTION: Always override POSTGRES_PASSWORD in docker-compose.production.yml or env; do not use cspulse_dev on AWS.
ENV POSTGRES_DB=cs_pulse
ENV POSTGRES_USER=cspulse
ENV POSTGRES_PASSWORD=cspulse_dev

EXPOSE 5432
VOLUME /var/lib/postgresql/data
