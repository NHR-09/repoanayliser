import os
from pathlib import Path
from typing import Dict, List
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RepositoryLoader:
    def __init__(self, workspace_dir: str = "./workspace"):
        self.workspace_dir = Path(workspace_dir)
        self.workspace_dir.mkdir(exist_ok=True)
        
    def clone_repository(self, repo_url: str) -> Path:
        repo_name = repo_url.rstrip('/').split('/')[-1].replace('.git', '')
        target_path = self.workspace_dir / repo_name
        
        logger.info(f"🔄 Starting repository clone: {repo_url}")
        logger.info(f"📁 Target directory: {target_path}")
        
        if target_path.exists():
            logger.info(f"⚠️  Directory exists, removing: {target_path}")
            import shutil
            import stat
            import time
            
            def remove_readonly(func, path, _):
                os.chmod(path, stat.S_IWRITE)
                func(path)
            
            try:
                shutil.rmtree(target_path, onerror=remove_readonly)
                time.sleep(0.5)  # Wait for filesystem
            except Exception as e:
                logger.warning(f"Failed to remove directory: {e}")
                # Try alternative cleanup
                import subprocess
                try:
                    subprocess.run(['rmdir', '/S', '/Q', str(target_path)], shell=True, check=False)
                    time.sleep(0.5)
                except:
                    pass
        
        logger.info("📥 Cloning repository (this may take a few minutes)...")
        import git
        git.Repo.clone_from(repo_url, target_path, depth=1)  # Shallow clone
        logger.info(f"✅ Repository cloned successfully to: {target_path}")
        
        return target_path
    
    def scan_files(self, repo_path: Path, extensions: List[str]) -> List[Dict]:
        logger.info(f"🔍 Scanning repository for files with extensions: {extensions}")
        files = []
        for ext in extensions:
            for file_path in repo_path.rglob(f"*{ext}"):
                if self._should_include(file_path):
                    files.append({
                        "path": str(file_path),
                        "relative_path": str(file_path.relative_to(repo_path)),
                        "language": self._detect_language(ext)
                    })
        logger.info(f"✅ Found {len(files)} files to analyze")
        return files
    
    def _should_include(self, path: Path) -> bool:
        exclude = {'node_modules', 'venv', '__pycache__', '.git', 'dist', 'build'}
        return not any(part in exclude for part in path.parts)
    
    def _detect_language(self, ext: str) -> str:
        mapping = {'.py': 'python', '.js': 'javascript', '.java': 'java'}
        return mapping.get(ext, 'unknown')
