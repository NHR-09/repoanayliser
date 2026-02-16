"""
Database Cleanup Script - Remove Orphaned Functions

This script removes Function nodes that are not connected to any File node
via the CONTAINS relationship. This can happen if:
1. Analysis was interrupted
2. File was deleted but functions weren't cleaned up
3. Previous bugs in the code

Run this after fixing the function graph code to clean up existing data.
"""

from src.graph.graph_db import GraphDB
from src.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def cleanup_orphaned_functions():
    """Remove orphaned Function nodes from Neo4j"""
    
    graph_db = GraphDB(
        settings.neo4j_uri,
        settings.neo4j_user,
        settings.neo4j_password
    )
    
    try:
        with graph_db.driver.session() as session:
            # Find orphaned functions
            result = session.run("""
                MATCH (fn:Function)
                WHERE NOT (fn)<-[:CONTAINS]-(:File)
                RETURN count(fn) as orphan_count
            """)
            record = result.single()
            orphan_count = record['orphan_count'] if record else 0
            
            if orphan_count == 0:
                logger.info("✅ No orphaned functions found!")
                return
            
            logger.warning(f"⚠️ Found {orphan_count} orphaned functions")
            
            # Delete orphaned functions
            result = session.run("""
                MATCH (fn:Function)
                WHERE NOT (fn)<-[:CONTAINS]-(:File)
                DETACH DELETE fn
                RETURN count(*) as deleted
            """)
            record = result.single()
            deleted = record['deleted'] if record else 0
            
            logger.info(f"🗑️ Deleted {deleted} orphaned functions")
            
            # Verify cleanup
            result = session.run("""
                MATCH (fn:Function)
                WHERE NOT (fn)<-[:CONTAINS]-(:File)
                RETURN count(fn) as remaining
            """)
            record = result.single()
            remaining = record['remaining'] if record else 0
            
            if remaining == 0:
                logger.info("✅ Cleanup successful! All orphaned functions removed.")
            else:
                logger.error(f"❌ Cleanup incomplete. {remaining} orphaned functions still exist.")
    
    finally:
        graph_db.close()

def cleanup_orphaned_classes():
    """Remove orphaned Class nodes from Neo4j"""
    
    graph_db = GraphDB(
        settings.neo4j_uri,
        settings.neo4j_user,
        settings.neo4j_password
    )
    
    try:
        with graph_db.driver.session() as session:
            # Find orphaned classes
            result = session.run("""
                MATCH (c:Class)
                WHERE NOT (c)<-[:CONTAINS]-(:File)
                RETURN count(c) as orphan_count
            """)
            record = result.single()
            orphan_count = record['orphan_count'] if record else 0
            
            if orphan_count == 0:
                logger.info("✅ No orphaned classes found!")
                return
            
            logger.warning(f"⚠️ Found {orphan_count} orphaned classes")
            
            # Delete orphaned classes
            result = session.run("""
                MATCH (c:Class)
                WHERE NOT (c)<-[:CONTAINS]-(:File)
                DETACH DELETE c
                RETURN count(*) as deleted
            """)
            record = result.single()
            deleted = record['deleted'] if record else 0
            
            logger.info(f"🗑️ Deleted {deleted} orphaned classes")
    
    finally:
        graph_db.close()

def verify_data_integrity():
    """Verify database integrity after cleanup"""
    
    graph_db = GraphDB(
        settings.neo4j_uri,
        settings.neo4j_user,
        settings.neo4j_password
    )
    
    try:
        with graph_db.driver.session() as session:
            # Count all nodes
            result = session.run("""
                MATCH (f:File)
                OPTIONAL MATCH (f)-[:CONTAINS]->(fn:Function)
                OPTIONAL MATCH (f)-[:CONTAINS]->(c:Class)
                RETURN count(DISTINCT f) as files,
                       count(DISTINCT fn) as functions,
                       count(DISTINCT c) as classes
            """)
            record = result.single()
            
            logger.info("\n📊 Database Statistics:")
            logger.info(f"   Files: {record['files']}")
            logger.info(f"   Functions: {record['functions']}")
            logger.info(f"   Classes: {record['classes']}")
            
            # Check for orphans
            result = session.run("""
                MATCH (fn:Function)
                WHERE NOT (fn)<-[:CONTAINS]-(:File)
                RETURN count(fn) as orphan_functions
            """)
            record = result.single()
            orphan_functions = record['orphan_functions']
            
            result = session.run("""
                MATCH (c:Class)
                WHERE NOT (c)<-[:CONTAINS]-(:File)
                RETURN count(c) as orphan_classes
            """)
            record = result.single()
            orphan_classes = record['orphan_classes']
            
            logger.info(f"\n🔍 Integrity Check:")
            logger.info(f"   Orphaned Functions: {orphan_functions}")
            logger.info(f"   Orphaned Classes: {orphan_classes}")
            
            if orphan_functions == 0 and orphan_classes == 0:
                logger.info("   ✅ Database integrity verified!")
            else:
                logger.warning("   ⚠️ Orphaned nodes still exist!")
    
    finally:
        graph_db.close()

if __name__ == "__main__":
    logger.info("🧹 Starting database cleanup...")
    logger.info("="*60)
    
    # Cleanup orphaned functions
    logger.info("\n1️⃣ Cleaning up orphaned functions...")
    cleanup_orphaned_functions()
    
    # Cleanup orphaned classes
    logger.info("\n2️⃣ Cleaning up orphaned classes...")
    cleanup_orphaned_classes()
    
    # Verify integrity
    logger.info("\n3️⃣ Verifying database integrity...")
    verify_data_integrity()
    
    logger.info("\n" + "="*60)
    logger.info("✅ Cleanup complete!")
