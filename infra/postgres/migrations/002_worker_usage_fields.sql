ALTER TABLE measurement.worker_invocation
    ADD COLUMN IF NOT EXISTS
    reasoning_output_tokens BIGINT;


DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE
            conname =
                'worker_invocation_reasoning_tokens_nonnegative'
            AND conrelid =
                'measurement.worker_invocation'::regclass
    ) THEN
        ALTER TABLE measurement.worker_invocation
            ADD CONSTRAINT
            worker_invocation_reasoning_tokens_nonnegative
            CHECK (
                reasoning_output_tokens IS NULL
                OR reasoning_output_tokens >= 0
            );
    END IF;
END
$$;
