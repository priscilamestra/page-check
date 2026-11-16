-- PAGE CHECK: Anonymous 24-hour recovery, not user history.
-- Database must have a private owner role. Never put the connection URL in Streamlit output.
CREATE TABLE IF NOT EXISTS pagecheck_temporary_audits (
    token_digest BYTEA PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    report JSONB NOT NULL,
    CONSTRAINT pagecheck_token_digest_size CHECK (octet_length(token_digest) = 32),
    CONSTRAINT pagecheck_expiry_after_creation CHECK (expires_at > created_at)
);
CREATE INDEX IF NOT EXISTS idx_pagecheck_temporary_expiry
    ON pagecheck_temporary_audits (expires_at);
CREATE TABLE IF NOT EXISTS pagecheck_temporary_screenshots (
    token_digest BYTEA NOT NULL REFERENCES pagecheck_temporary_audits(token_digest) ON DELETE CASCADE,
    viewport TEXT NOT NULL CHECK (viewport IN ('desktop', 'mobile')),
    kind TEXT NOT NULL CHECK (kind IN ('initial', 'after_scroll', 'annotated')),
    png BYTEA NOT NULL CHECK (octet_length(png) BETWEEN 8 AND 2097152),
    PRIMARY KEY (token_digest, viewport, kind)
);
