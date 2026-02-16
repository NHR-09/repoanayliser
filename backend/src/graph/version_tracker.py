import hashlib
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
import logging
import subprocess

logger = logging.getLogger(__name__)

class VersionTracker:
    """SHA-256 based version tracking for repository files"""
    
    def __init__(self, graph_db):
        self.graph_db = graph_db
        self._init_constraints()
    
    def _init_constraints(self):
        """Create Neo4j constraints for data integrity"""
        with self.graph_db.driver.session() as session:
            constraints = [
                "CREATE CONSTRAINT unique_repo IF NOT EXISTS FOR (r:Repository) REQUIRE r.repo_id IS UNIQUE",
                "CREATE CONSTRAINT unique_user IF NOT EXISTS FOR (u:User) REQUIRE u.user_id IS UNIQUE",
                "CREATE CONSTRAINT unique_commit IF NOT EXISTS FOR (c:Commit) REQUIRE (c.repo_id, c.commit_hash) IS UNIQUE"
            ]
            for constraint in constraints:
                try:
                    session.run(constraint)
                except Exception as e:
                    logger.debug(f"Constraint already exists: {e}")
    
    def compute_file_hash(self, filepath: str) -> str:
        """Compute SHA-256 hash of file content"""
        sha = hashlib.sha256()
        try:
            path = Path(filepath)
            if not path.is_file():
                return ""
            with open(filepath, 'rb') as f:
                while chunk := f.read(8192):
                    sha.update(chunk)
            return sha.hexdigest()
        except Exception as e:
            logger.debug(f"Skipping {filepath}: {e}")
            return ""
    
    def get_current_commit(self, repo_path: str) -> Optional[Dict]:
        """Get current Git commit info"""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                capture_output=True, text=True, cwd=repo_path, timeout=5
            )
            if result.returncode != 0 or not result.stdout:
                return None
            commit_hash = result.stdout.strip()
            
            result = subprocess.run(
                ['git', 'log', '-1', '--format=%ae|%s|%at|%an'],
                capture_output=True, text=True, cwd=repo_path, timeout=5
            )
            if result.returncode == 0 and result.stdout:
                parts = result.stdout.strip().split('|', 3)
                if len(parts) == 4:
                    return {
                        'commit_hash': commit_hash,
                        'author_email': parts[0],
                        'message': parts[1],
                        'timestamp': int(parts[2]),
                        'author_name': parts[3]
                    }
        except:
            pass
        return None
    
    def create_repository(self, repo_url: str, repo_path: str, user_email: str = "system") -> str:
        """Create or get repository node - reuse snapshot if commit unchanged"""
        repo_id = hashlib.sha256(repo_url.encode()).hexdigest()[:16]
        commit_info = self.get_current_commit(repo_path)
        
        with self.graph_db.driver.session() as session:
            # Check if repo exists
            result = session.run("""
                MATCH (r:Repository {repo_id: $repo_id})
                RETURN r.repo_id as repo_id, r.current_commit as current_commit
                """, repo_id=repo_id)
            record = result.single()
            exists = record is not None
            last_commit = record['current_commit'] if record else None
            
            # Update repository
            session.run("""
                MERGE (r:Repository {repo_id: $repo_id})
                SET r.name = $name,
                    r.url = $url,
                    r.path = $path,
                    r.last_analyzed = datetime(),
                    r.current_commit = $commit_hash
                """,
                repo_id=repo_id,
                name=repo_url.split('/')[-1],
                url=repo_url,
                path=repo_path,
                commit_hash=commit_info['commit_hash'] if commit_info else None
            )
            
            # Check if snapshot exists for this commit (prevent duplicates)
            snapshot_id = None
            if commit_info:
                result = session.run("""
                    MATCH (s:Snapshot {repo_id: $repo_id, commit_hash: $commit_hash})
                    RETURN s.snapshot_id as snapshot_id
                    ORDER BY s.created_at DESC
                    LIMIT 1
                    """,
                    repo_id=repo_id,
                    commit_hash=commit_info['commit_hash']
                )
                record = result.single()
                if record:
                    snapshot_id = record['snapshot_id']
                    logger.info(f"♻️ Reusing snapshot for commit {commit_info['commit_hash'][:8]}")
            
            # Create new snapshot only if none exists for this commit
            if not snapshot_id:
                snapshot_id = hashlib.sha256(f"{repo_id}_{datetime.now().isoformat()}".encode()).hexdigest()[:16]
                session.run("""
                    MATCH (r:Repository {repo_id: $repo_id})
                    CREATE (s:Snapshot {
                        snapshot_id: $snapshot_id,
                        repo_id: $repo_id,
                        created_at: datetime(),
                        commit_hash: $commit_hash
                    })
                    CREATE (r)-[:HAS_SNAPSHOT]->(s)
                    """,
                    repo_id=repo_id,
                    snapshot_id=snapshot_id,
                    commit_hash=commit_info['commit_hash'] if commit_info else None
                )
            
            # Create commit node BEFORE file tracking
            if commit_info:
                session.run("""
                    MATCH (r:Repository {repo_id: $repo_id})
                    MERGE (u:User {user_id: $author_email})
                    SET u.email = $author_email, u.name = $author_name
                    
                    MERGE (c:Commit {
                        repo_id: $repo_id,
                        commit_hash: $commit_hash
                    })
                    SET c.message = $message,
                        c.timestamp = datetime({epochSeconds: $timestamp}),
                        c.author_email = $author_email,
                        c.author_name = $author_name
                    
                    MERGE (r)-[:HAS_COMMIT]->(c)
                    MERGE (c)-[:AUTHORED_BY]->(u)
                    
                    WITH r, c
                    OPTIONAL MATCH (r)-[:HAS_COMMIT]->(prev:Commit {commit_hash: $last_commit})
                    WHERE $last_commit IS NOT NULL AND prev.commit_hash <> $commit_hash
                    FOREACH (_ IN CASE WHEN prev IS NOT NULL THEN [1] ELSE [] END |
                        MERGE (c)-[:PREVIOUS_COMMIT]->(prev)
                    )
                    """,
                    repo_id=repo_id,
                    commit_hash=commit_info['commit_hash'],
                    message=commit_info['message'],
                    timestamp=commit_info['timestamp'],
                    author_email=commit_info['author_email'],
                    author_name=commit_info['author_name'],
                    last_commit=last_commit
                )
                if commit_info['commit_hash'] != last_commit:
                    logger.info(f"📍 New commit tracked: {commit_info['commit_hash'][:8]} - {commit_info['message'][:50]}")
        
        return repo_id, exists, snapshot_id
    
    def track_file_version(self, repo_id: str, file_path: str, repo_path: str) -> Dict:
        """Track file version only if commit changed"""
        current_hash = self.compute_file_hash(file_path)
        if not current_hash:
            return {"status": "error", "message": "Could not hash file"}
        
        commit_info = self.get_current_commit(repo_path)
        if not commit_info:
            return {"status": "error", "message": "Not a git repository"}
        
        with self.graph_db.driver.session() as session:
            # Check if version with same hash exists for this file at this commit
            result = session.run("""
                MATCH (c:Commit {repo_id: $repo_id, commit_hash: $commit_hash})
                OPTIONAL MATCH (v:Version {file_path: $file_path, hash: $hash})-[:VERSION_AT]->(c)
                RETURN v IS NOT NULL as exists
                """,
                repo_id=repo_id,
                file_path=file_path,
                hash=current_hash,
                commit_hash=commit_info['commit_hash']
            )
            record = result.single()
            if record and record['exists']:
                return {"status": "unchanged", "hash": current_hash, "commit": commit_info['commit_hash'][:8]}
            
            # Create version for this commit
            session.run("""
                MATCH (r:Repository {repo_id: $repo_id})
                MATCH (c:Commit {repo_id: $repo_id, commit_hash: $commit_hash})
                MERGE (f:File {file_path: $file_path})
                MERGE (r)-[:CONTAINS]->(f)
                MERGE (u:User {user_id: $author_email})
                SET u.email = $author_email, u.name = $author_name
                
                CREATE (v:Version {
                    hash: $hash,
                    timestamp: datetime(),
                    file_path: $file_path,
                    commit_hash: $commit_hash
                })
                CREATE (f)-[:HAS_VERSION]->(v)
                CREATE (v)-[:VERSION_AT]->(c)
                CREATE (v)-[:CREATED_BY]->(u)
                
                WITH f, v, c
                OPTIONAL MATCH (c)-[:PREVIOUS_COMMIT]->(prev_c:Commit)
                OPTIONAL MATCH (f)-[:HAS_VERSION]->(old:Version)-[:VERSION_AT]->(prev_c)
                WHERE old.hash <> $hash
                FOREACH (_ IN CASE WHEN old IS NOT NULL THEN [1] ELSE [] END |
                    CREATE (v)-[:PREVIOUS_VERSION]->(old)
                )
                """,
                repo_id=repo_id,
                file_path=file_path,
                hash=current_hash,
                commit_hash=commit_info['commit_hash'],
                author_email=commit_info['author_email'],
                author_name=commit_info['author_name']
            )
            
            return {
                "status": "new_version",
                "hash": current_hash,
                "commit": commit_info['commit_hash'][:8]
            }
    
    def _get_git_info(self, file_path: str) -> Optional[Dict]:
        """Extract git commit info for file"""
        try:
            result = subprocess.run(
                ['git', 'log', '-1', '--format=%ae|%s', '--', file_path],
                capture_output=True, text=True, cwd=Path(file_path).parent, timeout=5
            )
            if result.returncode == 0 and result.stdout and result.stdout.strip():
                parts = result.stdout.strip().split('|', 1)
                return {'author': parts[0], 'message': parts[1] if len(parts) > 1 else 'No message'}
        except:
            pass
        return None
    
    def import_git_history(self, repo_id: str, repo_path: str, max_commits: int = 50) -> Dict:
        """Import git commit history to create version lineage"""
        try:
            # Get commit history with file changes
            result = subprocess.run(
                ['git', 'log', f'--max-count={max_commits}', '--pretty=format:%H|%ae|%s|%at', '--name-only'],
                capture_output=True, text=True, cwd=repo_path, timeout=30
            )
            if result.returncode != 0 or not result.stdout:
                return {"status": "error", "message": "Not a git repository"}
            
            # Parse commits
            commits = []
            lines = [l for l in result.stdout.split('\n') if l.strip()]
            i = 0
            while i < len(lines):
                if '|' in lines[i]:
                    parts = lines[i].split('|', 3)
                    if len(parts) == 4:
                        commit_hash, author, message, timestamp = parts
                        i += 1
                        files = []
                        while i < len(lines) and '|' not in lines[i]:
                            files.append(lines[i].strip())
                            i += 1
                        commits.append({
                            'hash': commit_hash,
                            'author': author,
                            'message': message,
                            'timestamp': int(timestamp),
                            'files': files
                        })
                    else:
                        i += 1
                else:
                    i += 1
            
            # Process commits oldest to newest
            versions_created = 0
            for commit in reversed(commits):
                # Create commit node
                with self.graph_db.driver.session() as session:
                    session.run("""
                        MATCH (r:Repository {repo_id: $repo_id})
                        MERGE (u:User {user_id: $author})
                        SET u.email = $author
                        
                        MERGE (c:Commit {
                            repo_id: $repo_id,
                            commit_hash: $commit_hash
                        })
                        SET c.message = $message,
                            c.timestamp = datetime({epochSeconds: $timestamp}),
                            c.author_email = $author
                        
                        MERGE (r)-[:HAS_COMMIT]->(c)
                        MERGE (c)-[:AUTHORED_BY]->(u)
                        """,
                        repo_id=repo_id,
                        commit_hash=commit['hash'],
                        message=commit['message'],
                        timestamp=commit['timestamp'],
                        author=commit['author']
                    )
                
                for file_rel in commit['files']:
                    file_result = subprocess.run(
                        ['git', 'show', f"{commit['hash']}:{file_rel}"],
                        capture_output=True, cwd=repo_path, timeout=5
                    )
                    if file_result.returncode == 0:
                        content_hash = hashlib.sha256(file_result.stdout).hexdigest()
                        file_path = str(Path(repo_path) / file_rel)
                        
                        with self.graph_db.driver.session() as session:
                            session.run("""
                                MATCH (r:Repository {repo_id: $repo_id})
                                MATCH (c:Commit {repo_id: $repo_id, commit_hash: $commit_hash})
                                MERGE (u:User {user_id: $author})
                                SET u.email = $author
                                MERGE (f:File {file_path: $file_path})
                                MERGE (r)-[:CONTAINS]->(f)
                                
                                CREATE (v:Version {
                                    hash: $hash,
                                    timestamp: datetime({epochSeconds: $timestamp}),
                                    file_path: $file_path,
                                    commit_hash: $commit_hash
                                })
                                CREATE (f)-[:HAS_VERSION]->(v)
                                CREATE (v)-[:VERSION_AT]->(c)
                                CREATE (v)-[:CREATED_BY]->(u)
                                """,
                                repo_id=repo_id,
                                file_path=file_path,
                                hash=content_hash,
                                commit_hash=commit['hash'],
                                timestamp=commit['timestamp'],
                                author=commit['author']
                            )
                            versions_created += 1
            
            # Link commit chain and version chain
            with self.graph_db.driver.session() as session:
                session.run("""
                    MATCH (r:Repository {repo_id: $repo_id})-[:HAS_COMMIT]->(c:Commit)
                    WITH c ORDER BY c.timestamp
                    WITH collect(c) as commits
                    UNWIND range(0, size(commits)-2) as i
                    WITH commits[i+1] as newer, commits[i] as older
                    MERGE (newer)-[:PREVIOUS_COMMIT]->(older)
                    """,
                    repo_id=repo_id
                )
                
                # Link version chains per file
                session.run("""
                    MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)
                    MATCH (f)-[:HAS_VERSION]->(v:Version)
                    WITH f, v ORDER BY v.timestamp
                    WITH f, collect(v) as versions
                    UNWIND range(0, size(versions)-2) as i
                    WITH versions[i+1] as newer, versions[i] as older
                    MERGE (newer)-[:PREVIOUS_VERSION]->(older)
                    """,
                    repo_id=repo_id
                )
            
            return {"status": "success", "commits_processed": len(commits), "versions_created": versions_created}
        except Exception as e:
            logger.error(f"Git history import failed: {e}")
            return {"status": "error", "message": str(e)}
    
    def get_developer_contributions(self, repo_id: str) -> List[Dict]:
        """Track developer contributions"""
        with self.graph_db.driver.session() as session:
            result = session.run("""
                MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)
                MATCH (f)-[:HAS_VERSION]->(v:Version)-[:CREATED_BY]->(u:User)
                WITH u, COUNT(DISTINCT f) as files_modified, COUNT(v) as total_versions
                RETURN u.email as developer,
                       files_modified,
                       total_versions
                ORDER BY total_versions DESC
                """,
                repo_id=repo_id
            )
            return [dict(record) for record in result]
    
    def get_file_history(self, repo_id: str, file_path: str) -> List[Dict]:
        """Get complete version history of a file"""
        with self.graph_db.driver.session() as session:
            result = session.run("""
                MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File {file_path: $file_path})
                MATCH (f)-[:HAS_VERSION]->(v:Version)
                OPTIONAL MATCH (v)-[:CREATED_BY]->(u:User)
                OPTIONAL MATCH (v)-[:PREVIOUS_VERSION]->(prev:Version)
                RETURN v.hash as hash,
                       toString(v.timestamp) as timestamp,
                       v.message as message,
                       u.email as author,
                       prev.hash as previous_hash
                ORDER BY v.timestamp DESC
                """,
                repo_id=repo_id,
                file_path=file_path
            )
            return [dict(record) for record in result]
    
    def get_repository_versions(self, repo_id: str) -> List[Dict]:
        """Get all versions across repository"""
        with self.graph_db.driver.session() as session:
            result = session.run("""
                MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)
                MATCH (f)-[:HAS_VERSION]->(v:Version)
                OPTIONAL MATCH (v)-[:CREATED_BY]->(u:User)
                RETURN f.file_path as file,
                       v.hash as hash,
                       toString(v.timestamp) as timestamp,
                       v.message as message,
                       u.email as author
                ORDER BY v.timestamp DESC
                LIMIT 100
                """,
                repo_id=repo_id
            )
            return [dict(record) for record in result]
    
    def list_repositories(self) -> List[Dict]:
        """List all analyzed repositories with snapshot count"""
        with self.graph_db.driver.session() as session:
            result = session.run("""
                MATCH (r:Repository)
                OPTIONAL MATCH (r)-[:CONTAINS]->(f:File)
                WITH r, COUNT(DISTINCT f) as file_count
                OPTIONAL MATCH (r)-[:HAS_SNAPSHOT]->(s:Snapshot)
                WITH r, file_count, COUNT(DISTINCT s) as snapshot_count
                RETURN r.repo_id as repo_id,
                       r.name as name,
                       r.url as url,
                       r.path as path,
                       r.current_commit as current_commit,
                       toString(r.last_analyzed) as last_analyzed,
                       file_count,
                       snapshot_count as version_count
                ORDER BY r.last_analyzed DESC
                """)
            return [dict(record) for record in result]
    
    def detect_file_tampering(self, repo_id: str, file_path: str) -> Dict:
        """Detect if file was modified outside system"""
        with self.graph_db.driver.session() as session:
            result = session.run("""
                MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File {file_path: $file_path})
                MATCH (f)-[:HAS_VERSION]->(v:Version)
                WITH v ORDER BY v.timestamp DESC LIMIT 1
                RETURN v.hash as stored_hash
                """,
                repo_id=repo_id,
                file_path=file_path
            )
            record = result.single()
            if not record:
                return {"status": "not_tracked"}
            
            stored_hash = record["stored_hash"]
            current_hash = self.compute_file_hash(file_path)
            
            if stored_hash != current_hash:
                return {
                    "status": "tampered",
                    "stored_hash": stored_hash,
                    "current_hash": current_hash,
                    "message": "File modified outside system"
                }
            
            return {"status": "intact", "hash": stored_hash}
    
    def delete_repository(self, repo_id: str) -> Dict:
        """Delete repository and all its data"""
        with self.graph_db.driver.session() as session:
            result = session.run("""
                MATCH (r:Repository {repo_id: $repo_id})
                OPTIONAL MATCH (r)-[:CONTAINS]->(f:File)
                OPTIONAL MATCH (f)-[:HAS_VERSION]->(v:Version)
                OPTIONAL MATCH (f)-[:CONTAINS]->(c)
                DETACH DELETE r, f, v, c
                RETURN COUNT(r) as deleted
                """, repo_id=repo_id)
            record = result.single()
            if record and record['deleted'] > 0:
                return {"status": "success", "message": "Repository deleted"}
            return {"status": "error", "message": "Repository not found"}
