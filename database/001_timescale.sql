CREATE EXTENSION IF NOT EXISTS timescaledb;

DO $$
BEGIN
  IF to_regclass('public.feeding_samples') IS NULL THEN
    RAISE NOTICE 'feeding_samples not found yet, skipping Timescale setup';
    RETURN;
  END IF;

  -- Convert feeding_samples into a hypertable
  PERFORM create_hypertable('feeding_samples', 'timestamp', if_not_exists => TRUE);

  -- Helpful index for common queries
  EXECUTE 'CREATE INDEX IF NOT EXISTS ix_feeding_samples_event_ts
           ON feeding_samples (feeding_event_id, timestamp DESC)';

  -- 5-minute continuous aggregate for dashboards
  EXECUTE $v$
    CREATE MATERIALIZED VIEW IF NOT EXISTS feeding_samples_5m
    WITH (timescaledb.continuous) AS
    SELECT
      feeding_event_id,
      time_bucket('5 minutes', timestamp) AS bucket,
      avg(temperature) AS temperature_avg,
      avg(humidity)    AS humidity_avg,
      avg(co2)         AS co2_avg,
      avg(distance)    AS distance_avg
    FROM feeding_samples
    GROUP BY feeding_event_id, bucket
  $v$;

  -- Auto refresh policy (safe to call repeatedly)
  PERFORM add_continuous_aggregate_policy('feeding_samples_5m',
    start_offset => INTERVAL '30 days',
    end_offset   => INTERVAL '5 minutes',
    schedule_interval => INTERVAL '5 minutes'
  );

END
$$;
