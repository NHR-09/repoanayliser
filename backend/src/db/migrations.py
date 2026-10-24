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

MIGRATION_002_SQL = """
-- 1. User Resumes
CREATE TABLE IF NOT EXISTS user_resumes (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    mime_type TEXT NOT NULL,
    raw_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_resumes_user ON user_resumes(user_id);

-- 2. User Skills (Reviewed skills with provenance)
CREATE TABLE IF NOT EXISTS user_skills (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    skill_name TEXT NOT NULL,
    category TEXT NOT NULL CHECK(category IN ('LANGUAGE', 'FRAMEWORK', 'DATABASE', 'TOOL', 'ARCHITECTURE', 'AI_ML', 'OTHER')),
    source TEXT NOT NULL CHECK(source IN ('RESUME', 'MANUAL')),
    evidence_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, skill_name)
);

CREATE INDEX IF NOT EXISTS idx_user_skills_user ON user_skills(user_id);

-- 3. Skill-to-Repository Evidence Mappings
CREATE TABLE IF NOT EXISTS skill_evidence (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    skill_name TEXT NOT NULL,
    repository_id TEXT NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    neo4j_repo_id TEXT NOT NULL,
    analysis_version TEXT,
    evidence_status TEXT NOT NULL CHECK(evidence_status IN ('CLAIMED_ONLY', 'CODE_EVIDENCE_FOUND', 'ASSESSMENT_EVIDENCE_FOUND', 'INSUFFICIENT_EVIDENCE')),
    file_path TEXT,
    entity_type TEXT,
    entity_name TEXT,
    line_number INTEGER,
    evidence_description TEXT,
    confidence_score REAL DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_skill_evidence_user ON skill_evidence(user_id);
CREATE INDEX IF NOT EXISTS idx_skill_evidence_repo ON skill_evidence(repository_id);
CREATE INDEX IF NOT EXISTS idx_skill_evidence_skill ON skill_evidence(user_id, skill_name);

-- 4. Repositories table additions for analysis status tracking
ALTER TABLE repositories ADD COLUMN analysis_status TEXT DEFAULT 'PENDING';
ALTER TABLE repositories ADD COLUMN last_analyzed_commit TEXT;
ALTER TABLE repositories ADD COLUMN last_analyzed_at TIMESTAMP;
ALTER TABLE repositories ADD COLUMN analysis_error TEXT;

-- 5. Candidate Practice Quizzes
CREATE TABLE IF NOT EXISTS practice_quizzes (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    mode TEXT NOT NULL CHECK(mode IN ('SKILL_BASED', 'REPOSITORY_BASED')),
    skill_name TEXT,
    repository_id TEXT REFERENCES repositories(id) ON DELETE SET NULL,
    neo4j_repo_id TEXT,
    difficulty TEXT NOT NULL CHECK(difficulty IN ('BEGINNER', 'INTERMEDIATE', 'ADVANCED')),
    competencies TEXT NOT NULL, -- JSON array of strings
    question_count INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'IN_PROGRESS' CHECK(status IN ('IN_PROGRESS', 'COMPLETED', 'ABANDONED')),
    total_score REAL DEFAULT 0.0,
    max_score REAL DEFAULT 0.0,
    percentage_score REAL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_practice_quizzes_user ON practice_quizzes(user_id);

-- 6. Practice Quiz Questions
CREATE TABLE IF NOT EXISTS practice_quiz_questions (
    quiz_id TEXT NOT NULL REFERENCES practice_quizzes(id) ON DELETE CASCADE,
    question_id TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    order_index INTEGER DEFAULT 0,
    PRIMARY KEY(quiz_id, question_id)
);

-- 7. Practice Answers & Detailed Grading
CREATE TABLE IF NOT EXISTS practice_answers (
    id TEXT PRIMARY KEY,
    quiz_id TEXT NOT NULL REFERENCES practice_quizzes(id) ON DELETE CASCADE,
    question_id TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    selected_options TEXT NOT NULL, -- JSON array of selected IDs (e.g. ["A", "C"])
    is_correct INTEGER NOT NULL,
    awarded_points REAL DEFAULT 0.0,
    max_points REAL DEFAULT 1.0,
    explanation TEXT,
    answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(quiz_id, question_id)
);

CREATE INDEX IF NOT EXISTS idx_practice_answers_quiz ON practice_answers(quiz_id);
CREATE INDEX IF NOT EXISTS idx_practice_answers_user ON practice_answers(user_id);
"""

MIGRATION_003_SQL = """
-- 1. Validation status and review lifecycle fields for questions
ALTER TABLE questions ADD COLUMN validation_status TEXT DEFAULT 'PENDING';
ALTER TABLE questions ADD COLUMN reviewed_by TEXT;
ALTER TABLE questions ADD COLUMN reviewed_at TIMESTAMP;
ALTER TABLE questions ADD COLUMN reviewer_notes TEXT;
ALTER TABLE questions ADD COLUMN parent_question_id TEXT;

-- 2. Question Versions (Immutable version tracking for publication & review)
CREATE TABLE IF NOT EXISTS question_versions (
    id TEXT PRIMARY KEY,
    question_id TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    organization_id TEXT REFERENCES organizations(id) ON DELETE SET NULL,
    author_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    reviewed_by TEXT REFERENCES users(id) ON DELETE SET NULL,
    source_type TEXT NOT NULL,
    repository_id TEXT,
    neo4j_repo_id TEXT,
    analysis_version TEXT,
    skill_tags TEXT NOT NULL,
    competency TEXT NOT NULL,
    response_format TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    question_text TEXT NOT NULL,
    options TEXT NOT NULL,
    answer_key TEXT NOT NULL,
    explanation TEXT NOT NULL,
    evidence_references TEXT,
    validation_status TEXT NOT NULL,
    review_status TEXT NOT NULL,
    reviewer_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(question_id, version)
);

CREATE INDEX IF NOT EXISTS idx_qv_question ON question_versions(question_id);
CREATE INDEX IF NOT EXISTS idx_qv_org ON question_versions(organization_id);

-- 3. Add HR repository library fields to repositories table
ALTER TABLE repositories ADD COLUMN description TEXT;
ALTER TABLE repositories ADD COLUMN approval_status TEXT DEFAULT 'REGISTERED';
ALTER TABLE repositories ADD COLUMN approved_by TEXT;
ALTER TABLE repositories ADD COLUMN approved_at TIMESTAMP;
ALTER TABLE repositories ADD COLUMN intended_evaluations TEXT;
ALTER TABLE repositories ADD COLUMN is_archived INTEGER DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_repositories_approval ON repositories(approval_status);
"""

ALL_MIGRATIONS = [
    ("001_initial_schema", MIGRATION_001_SQL),
    ("002_candidate_practice_schema", MIGRATION_002_SQL),
    ("003_hr_question_bank_and_repo_library", MIGRATION_003_SQL)
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
