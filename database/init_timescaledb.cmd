docker exec -it fermento-postgress psql -U fermento -d fermento -f /docker-entrypoint-initdb.d/001_timescale.sql
