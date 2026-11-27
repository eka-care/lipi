-- design.md §4: sessions, sources, chunks (phase 1).
-- CHECKs only on closed lists (protocol D6); source kind is an open list.

CREATE TABLE sessions (
    id                 text PRIMARY KEY,
    client_session_id  text CHECK (char_length(client_session_id) <= 50),
    status             text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'archived')),
    metadata           jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at         timestamptz NOT NULL DEFAULT now(),
    updated_at         timestamptz NOT NULL DEFAULT now(),
    archived_at        timestamptz
);

-- decision 25: not unique; the phase 3 lookup returns every match
CREATE INDEX sessions_client_session_id_idx ON sessions (client_session_id) WHERE client_session_id IS NOT NULL;

CREATE TABLE sources (
    id                      text PRIMARY KEY,
    session_id              text NOT NULL REFERENCES sessions (id) ON DELETE CASCADE,
    kind                    text NOT NULL,
    status                  text NOT NULL CHECK (status IN
                                ('ready', 'failed', 'created', 'recording', 'processing', 'success', 'cancelled')),
    created_at              timestamptz NOT NULL DEFAULT now(),
    input                   text CHECK (input IN ('chunked', 'file')),
    format                  text,
    language_hints          text[] NOT NULL DEFAULT '{}',
    stt_model               text,
    recording_started_at    timestamptz,
    recording_ended_at      timestamptz,
    completed_at            timestamptz,
    chunks_expected         integer,
    warnings                jsonb NOT NULL DEFAULT '[]'::jsonb,
    failure                 jsonb,
    cancel_reason           text CHECK (cancel_reason IN ('client', 'no_audio')),
    transcript_language     text,
    transcript_duration_ms  integer,
    transcript_created_at   timestamptz
);

CREATE INDEX sources_session_id_created_at_idx ON sources (session_id, created_at);

CREATE TABLE chunks (
    source_id    text NOT NULL REFERENCES sources (id) ON DELETE CASCADE,
    index        integer NOT NULL,
    status       text NOT NULL CHECK (status IN ('queued', 'success', 'failed')),
    received_at  timestamptz NOT NULL DEFAULT now(),
    recorded_at  timestamptz,
    duration_ms  integer,
    size_bytes   integer NOT NULL,
    PRIMARY KEY (source_id, index)
);
