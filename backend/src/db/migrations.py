import sqlite3
import logging
from typing import Optional
from .connection import get_db_connection

logger = logging.getLogger(__name__)

MIGRATION_001_SQL = """
-- 1. Schema migration tracker
CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Organizations (Multi-Tenancy)
CREATE TABLE IF NOT EXISTS organizations (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Users (Server-controlled role: 'USER' for candidates, 'HR' for recruiters, 'ADMIN' for system)
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('USER', 'HR', 'ADMIN')),
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- 4. Organization Memberships (Enforces organization membership for HR users)
CREATE TABLE IF NOT EXISTS organization_memberships (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    org_role TEXT NOT NULL CHECK(org_role IN ('OWNER', 'ADMIN', 'RECRUITER')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(organization_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_org_members_user ON organization_memberships(user_id);
CREATE INDEX IF NOT EXISTS idx_org_members_org ON organization_memberships(organization_id);

-- 5. HR Invitations & Provisioning Tokens (Single-use, expiring)
CREATE TABLE IF NOT EXISTS hr_invitations (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    email TEXT NOT NULL COLLATE NOCASE,
    invitation_code_hash TEXT UNIQUE NOT NULL,
    org_role TEXT NOT NULL DEFAULT 'RECRUITER' CHECK(org_role IN ('OWNER', 'ADMIN', 'RECRUITER')),
    created_by TEXT REFERENCES users(id) ON DELETE SET NULL,
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_hr_invitations_code_hash ON hr_invitations(invitation_code_hash);

-- 6. Auth Sessions (Stores SHA-256 hash of opaque bearer token)
CREATE TABLE IF NOT EXISTS auth_sessions (
    id TEXT PRIMARY KEY,
    token_hash TEXT UNIQUE NOT NULL,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    csrf_token_hash TEXT,
    expires_at TIMESTAMP NOT NULL,
    revoked_at TIMESTAMP,
    user_agent TEXT,
    ip_address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_auth_sessions_token_hash ON auth_sessions(token_hash);
CREATE INDEX IF NOT EXISTS idx_auth_sessions_user_id ON auth_sessions(user_id);

-- 7. Repositories (Relational Metadata & Bridge to Neo4j)
CREATE TABLE IF NOT EXISTS repositories (
    id TEXT PRIMARY KEY,
    neo4j_repo_id TEXT NOT NULL,
    owner_user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    organization_id TEXT REFERENCES organizations(id) ON DELETE SET NULL,
    display_name TEXT NOT NULL,
    repo_url TEXT NOT NULL,
    default_branch TEXT DEFAULT 'main',
    is_public INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_repositories_neo4j ON repositories(neo4j_repo_id);
CREATE INDEX IF NOT EXISTS idx_repositories_org ON repositories(organization_id);
CREATE INDEX IF NOT EXISTS idx_repositories_owner ON repositories(owner_user_id);

-- 8. Repository Access Grants
-- Constraint: must be granted either to a user OR to an organization, never ambiguous!
CREATE TABLE IF NOT EXISTS repository_access_grants (
    id TEXT PRIMARY KEY,
    repository_id TEXT NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
    organization_id TEXT REFERENCES organizations(id) ON DELETE CASCADE,
    permission TEXT NOT NULL CHECK(permission IN ('READ', 'ANALYZE', 'ASSESS', 'ADMIN')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_grant_target CHECK (
        (user_id IS NOT NULL AND organization_id IS NULL) OR
        (user_id IS NULL AND organization_id IS NOT NULL)
    )
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_repo_user_grant 
    ON repository_access_grants(repository_id, user_id) 
    WHERE user_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_repo_org_grant 
    ON repository_access_grants(repository_id, organization_id) 
    WHERE organization_id IS NOT NULL;

-- 9. Question Bank (Decoupled response_format and competency)
CREATE TABLE IF NOT EXISTS questions (
    id TEXT PRIMARY KEY,
    organization_id TEXT REFERENCES organizations(id) ON DELETE SET NULL,
    created_by TEXT REFERENCES users(id) ON DELETE SET NULL,
    source_type TEXT NOT NULL CHECK(source_type IN ('SKILL_BASED', 'REPOSITORY_BASED')),
    repository_id TEXT REFERENCES repositories(id) ON DELETE SET NULL,
    neo4j_repo_id TEXT,
    analysis_version TEXT,
    skill_tags TEXT NOT NULL, -- JSON array of strings
    competency TEXT NOT NULL CHECK(competency IN (
        'CODE_COMPREHENSION', 'DEPENDENCY_TRACING', 'ARCHITECTURE_REASONING', 'DEBUGGING', 'CHANGE_IMPACT'
    )),
    response_format TEXT NOT NULL CHECK(response_format IN (
        'SINGLE_SELECT', 'MULTI_SELECT', 'TRUE_FALSE', 'TEXT', 'CODE_TASK'
    )),
    difficulty TEXT NOT NULL CHECK(difficulty IN ('BEGINNER', 'INTERMEDIATE', 'ADVANCED')),
    question_text TEXT NOT NULL,
    options TEXT NOT NULL, -- JSON array
    answer_key TEXT NOT NULL, -- JSON structure (protected from candidates)
    explanation TEXT NOT NULL,
    evidence_references TEXT, -- JSON array of references
    review_status TEXT NOT NULL DEFAULT 'NEEDS_REVIEW' CHECK(review_status IN (
        'NEEDS_REVIEW', 'APPROVED', 'PUBLISHED', 'ARCHIVED'
    )),
    version INTEGER DEFAULT 1,
    is_archived INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_questions_org ON questions(organization_id);
CREATE INDEX IF NOT EXISTS idx_questions_competency ON questions(competency);
CREATE INDEX IF NOT EXISTS idx_questions_response_format ON questions(response_format);
CREATE INDEX IF NOT EXISTS idx_questions_review_status ON questions(review_status);

-- 10. Assessments
CREATE TABLE IF NOT EXISTS assessments (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    title TEXT NOT NULL,
    description TEXT,
    job_role TEXT,
    repository_id TEXT REFERENCES repositories(id) ON DELETE RESTRICT,
    mode TEXT NOT NULL CHECK(mode IN ('CURATED', 'RANDOMIZED')),
    blueprint_config TEXT, -- JSON configuration
    duration_minutes INTEGER NOT NULL DEFAULT 60,
    passing_score_pct REAL DEFAULT 70.0,
    status TEXT NOT NULL DEFAULT 'DRAFT' CHECK(status IN ('DRAFT', 'PUBLISHED', 'ARCHIVED')),
    version INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_assessments_org ON assessments(organization_id);

-- 11. Assessment Assignments
CREATE TABLE IF NOT EXISTS assessment_assignments (
    id TEXT PRIMARY KEY,
    assessment_id TEXT NOT NULL REFERENCES assessments(id) ON DELETE RESTRICT,
    candidate_id TEXT REFERENCES users(id) ON DELETE RESTRICT,
    candidate_email TEXT NOT NULL COLLATE NOCASE,
    invitation_token_hash TEXT UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    max_attempts INTEGER DEFAULT 1,
    attempts_used INTEGER DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'PENDING' CHECK(status IN ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'EXPIRED')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_assignments_token_hash ON assessment_assignments(invitation_token_hash);
CREATE INDEX IF NOT EXISTS idx_assignments_candidate ON assessment_assignments(candidate_email);

-- 12. Assessment Attempts (Immutable Question Snapshot)
CREATE TABLE IF NOT EXISTS assessment_attempts (
    id TEXT PRIMARY KEY,
    assignment_id TEXT REFERENCES assessment_assignments(id) ON DELETE RESTRICT,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    assessment_id TEXT REFERENCES assessments(id) ON DELETE RESTRICT,
    is_practice INTEGER DEFAULT 0,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deadline_at TIMESTAMP NOT NULL,
    submitted_at TIMESTAMP,
    snapshot_questions TEXT NOT NULL, -- Immutable JSON array of complete questions
    total_score REAL DEFAULT 0.0,
    max_possible_score REAL DEFAULT 0.0,
    percentage_score REAL DEFAULT 0.0,
    passed INTEGER DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'IN_PROGRESS' CHECK(status IN ('IN_PROGRESS', 'SUBMITTED', 'EXPIRED', 'GRADED')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_attempts_user ON assessment_attempts(user_id);
CREATE INDEX IF NOT EXISTS idx_attempts_assessment ON assessment_attempts(assessment_id);

-- 13. Attempt Answers
CREATE TABLE IF NOT EXISTS attempt_answers (
    id TEXT PRIMARY KEY,
    attempt_id TEXT NOT NULL REFERENCES assessment_attempts(id) ON DELETE RESTRICT,
    question_id TEXT NOT NULL,
    candidate_response TEXT, -- JSON answer
    is_correct INTEGER,
    partial_score REAL DEFAULT 0.0,
    max_score REAL DEFAULT 1.0,
    feedback TEXT,
    answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(attempt_id, question_id)
);

-- 14. Attempt Events (Audit Trail for assessment actions)
CREATE TABLE IF NOT EXISTS attempt_events (
    id TEXT PRIMARY KEY,
    attempt_id TEXT NOT NULL REFERENCES assessment_attempts(id) ON DELETE RESTRICT,
    event_type TEXT NOT NULL, -- 'START', 'AUTOSAVE', 'NAVIGATION', 'SUBMIT', 'TIMEOUT'
    event_payload TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 15. Audit Logs
CREATE TABLE IF NOT EXISTS audit_logs (
    id TEXT PRIMARY KEY,
    organization_id TEXT,
    user_id TEXT,
    action TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id TEXT,
    details TEXT,
    ip_address TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

ALL_MIGRATIONS = [
    ("001_initial_schema", MIGRATION_001_SQL)
]

def run_migrations(custom_path: Optional[str] = None):
    """Run all unapplied migrations in chronological order."""
    with get_db_connection(custom_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        applied_rows = conn.execute("SELECT version FROM schema_migrations").fetchall()
        applied_versions = {row["version"] for row in applied_rows}
        
        for version, script in ALL_MIGRATIONS:
            if version not in applied_versions:
                logger.info(f"Applying migration: {version}")
                conn.executescript(script)
                conn.execute("INSERT INTO schema_migrations (version) VALUES (?)", (version,))
                logger.info(f"Successfully applied migration: {version}")
