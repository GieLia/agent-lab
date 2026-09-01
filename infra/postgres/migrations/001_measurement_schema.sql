CREATE SCHEMA IF NOT EXISTS measurement;


CREATE TABLE IF NOT EXISTS measurement.evaluation_case (
    case_id TEXT NOT NULL,
    case_version INTEGER NOT NULL,
    case_sha256 CHAR(64),

    title TEXT,
    objective TEXT,

    raw_case JSONB,

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (
        case_id,
        case_version
    ),

    CHECK (
        case_version > 0
    ),

    CHECK (
        case_sha256 IS NULL
        OR case_sha256 ~ '^[0-9a-f]{64}$'
    )
);


CREATE TABLE IF NOT EXISTS measurement.evaluation_run (
    run_id UUID PRIMARY KEY,

    case_id TEXT NOT NULL,
    case_version INTEGER NOT NULL,

    run_type TEXT NOT NULL,

    git_sha TEXT,
    config_hash CHAR(64),

    orchestration TEXT,

    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ,

    status TEXT NOT NULL,

    raw_metadata JSONB,

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (
        case_id,
        case_version
    )
    REFERENCES measurement.evaluation_case (
        case_id,
        case_version
    ),

    CHECK (
        finished_at IS NULL
        OR finished_at >= started_at
    ),

    CHECK (
        config_hash IS NULL
        OR config_hash ~ '^[0-9a-f]{64}$'
    )
);


CREATE TABLE IF NOT EXISTS measurement.worker_invocation (
    invocation_id TEXT PRIMARY KEY,

    run_id UUID NOT NULL
        REFERENCES measurement.evaluation_run(run_id)
        ON DELETE CASCADE,

    worker_id TEXT NOT NULL,
    role TEXT NOT NULL,

    provider TEXT NOT NULL,
    account TEXT,
    model TEXT,

    request_id TEXT,
    session_id TEXT,

    skill_ids TEXT[] NOT NULL
        DEFAULT '{}',

    tool_profile TEXT,

    tools_exposed_count INTEGER,

    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ,

    duration_ms BIGINT,

    status TEXT NOT NULL,

    input_tokens BIGINT,
    output_tokens BIGINT,

    cache_read_tokens BIGINT,
    cache_write_tokens BIGINT,

    reported_cost_usd NUMERIC(18,8),
    cost_source TEXT,

    raw_result JSONB,

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CHECK (
        tools_exposed_count IS NULL
        OR tools_exposed_count >= 0
    ),

    CHECK (
        duration_ms IS NULL
        OR duration_ms >= 0
    ),

    CHECK (
        input_tokens IS NULL
        OR input_tokens >= 0
    ),

    CHECK (
        output_tokens IS NULL
        OR output_tokens >= 0
    ),

    CHECK (
        cache_read_tokens IS NULL
        OR cache_read_tokens >= 0
    ),

    CHECK (
        cache_write_tokens IS NULL
        OR cache_write_tokens >= 0
    ),

    CHECK (
        reported_cost_usd IS NULL
        OR reported_cost_usd >= 0
    ),

    CHECK (
        finished_at IS NULL
        OR finished_at >= started_at
    )
);


CREATE TABLE IF NOT EXISTS measurement.tool_invocation (
    tool_invocation_id TEXT PRIMARY KEY,

    run_id UUID NOT NULL
        REFERENCES measurement.evaluation_run(run_id)
        ON DELETE CASCADE,

    worker_invocation_id TEXT
        REFERENCES measurement.worker_invocation(invocation_id)
        ON DELETE CASCADE,

    capability TEXT NOT NULL,

    tool_name TEXT NOT NULL,

    tool_kind TEXT NOT NULL,

    tool_profile TEXT,

    mcp_server TEXT,
    mcp_server_version TEXT,

    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ,

    duration_ms BIGINT,

    status TEXT NOT NULL,
    error_code TEXT,

    human_approval_required BOOLEAN
        NOT NULL DEFAULT FALSE,

    human_approval_granted BOOLEAN,

    metadata JSONB,

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CHECK (
        tool_kind IN (
            'native',
            'cli',
            'python',
            'http',
            'mcp'
        )
    ),

    CHECK (
        duration_ms IS NULL
        OR duration_ms >= 0
    ),

    CHECK (
        finished_at IS NULL
        OR finished_at >= started_at
    ),

    CHECK (
        human_approval_required
        OR human_approval_granted IS NULL
    ),

    CHECK (
        tool_kind = 'mcp'
        OR (
            mcp_server IS NULL
            AND mcp_server_version IS NULL
        )
    )
);


CREATE TABLE IF NOT EXISTS measurement.run_metric (
    metric_id BIGINT GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,

    run_id UUID NOT NULL
        REFERENCES measurement.evaluation_run(run_id)
        ON DELETE CASCADE,

    worker_invocation_id TEXT
        REFERENCES measurement.worker_invocation(invocation_id)
        ON DELETE CASCADE,

    metric_name TEXT NOT NULL,

    numeric_value NUMERIC,
    text_value TEXT,

    unit TEXT,

    metadata JSONB,

    recorded_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CHECK (
        (numeric_value IS NOT NULL)::INTEGER
        +
        (text_value IS NOT NULL)::INTEGER
        = 1
    )
);


CREATE TABLE IF NOT EXISTS measurement.gate_result (
    gate_result_id BIGINT GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,

    run_id UUID NOT NULL
        REFERENCES measurement.evaluation_run(run_id)
        ON DELETE CASCADE,

    gate_name TEXT NOT NULL,

    evaluator_type TEXT NOT NULL,

    verdict TEXT NOT NULL,

    passed BOOLEAN,

    score NUMERIC,

    findings JSONB,

    evaluated_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS measurement.artifact_reference (
    artifact_id BIGINT GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,

    run_id UUID NOT NULL
        REFERENCES measurement.evaluation_run(run_id)
        ON DELETE CASCADE,

    worker_invocation_id TEXT
        REFERENCES measurement.worker_invocation(invocation_id)
        ON DELETE CASCADE,

    artifact_type TEXT NOT NULL,

    artifact_uri TEXT NOT NULL,

    sha256 CHAR(64),

    media_type TEXT,

    metadata JSONB,

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CHECK (
        sha256 IS NULL
        OR sha256 ~ '^[0-9a-f]{64}$'
    )
);


CREATE INDEX IF NOT EXISTS idx_evaluation_run_case
    ON measurement.evaluation_run (
        case_id,
        case_version
    );


CREATE INDEX IF NOT EXISTS idx_evaluation_run_type
    ON measurement.evaluation_run (
        run_type
    );


CREATE INDEX IF NOT EXISTS idx_evaluation_run_started
    ON measurement.evaluation_run (
        started_at DESC
    );


CREATE INDEX IF NOT EXISTS idx_worker_invocation_run
    ON measurement.worker_invocation (
        run_id
    );


CREATE INDEX IF NOT EXISTS idx_worker_invocation_provider
    ON measurement.worker_invocation (
        provider,
        account,
        model
    );


CREATE INDEX IF NOT EXISTS idx_tool_invocation_run
    ON measurement.tool_invocation (
        run_id
    );


CREATE INDEX IF NOT EXISTS idx_tool_invocation_worker
    ON measurement.tool_invocation (
        worker_invocation_id
    );


CREATE INDEX IF NOT EXISTS idx_tool_invocation_capability
    ON measurement.tool_invocation (
        capability
    );


CREATE INDEX IF NOT EXISTS idx_tool_invocation_kind
    ON measurement.tool_invocation (
        tool_kind
    );


CREATE INDEX IF NOT EXISTS idx_run_metric_run
    ON measurement.run_metric (
        run_id,
        metric_name
    );


CREATE INDEX IF NOT EXISTS idx_gate_result_run
    ON measurement.gate_result (
        run_id
    );


CREATE INDEX IF NOT EXISTS idx_artifact_reference_run
    ON measurement.artifact_reference (
        run_id
    );
