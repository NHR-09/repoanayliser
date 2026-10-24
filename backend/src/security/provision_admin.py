import argparse
import sys
import uuid
import re
from typing import Dict, Any

from ..db.connection import get_db_connection, init_db
from ..security.passwords import hash_password, validate_password_strength

def slugify(text: str) -> str:
    """Generate a clean URL-friendly slug."""
    text = re.sub(r"[^\w\s-]", "", text.lower().strip())
    return re.sub(r"[-\s]+", "-", text) or "org"

def provision_initial_admin(
    email: str,
    password: str,
    full_name: str,
    organization_name: str,
    db_path: str = None
) -> Dict[str, Any]:
    """
    One-time administrative provisioning mechanism.
    Only succeeds if no HR or ADMIN user exists in the system yet.
    Creates the root Organization, assigns the user as HR Owner/Admin.
    """
    init_db(db_path)
    
    email_clean = email.strip().lower()
    if "@" not in email_clean or "." not in email_clean:
        raise ValueError("Invalid email format.")
        
    pw_error = validate_password_strength(password)
    if pw_error:
        raise ValueError(pw_error)
        
    with get_db_connection(db_path) as conn:
        # Check if an HR or ADMIN user already exists
        count_row = conn.execute(
            "SELECT count(*) as c FROM users WHERE role IN ('HR', 'ADMIN')"
        ).fetchone()
        
        if count_row and count_row["c"] > 0:
            raise PermissionError("Initial administrative provisioning is closed: an administrative account already exists.")
            
        # Check if email is taken
        existing = conn.execute("SELECT id FROM users WHERE email = ?", (email_clean,)).fetchone()
        if existing:
            raise ValueError("An account with this email already exists.")
            
        org_id = str(uuid.uuid4())
        org_name = organization_name.strip()
        org_slug = f"{slugify(org_name)}-{org_id[:6]}"
        
        conn.execute(
            "INSERT INTO organizations (id, name, slug) VALUES (?, ?, ?)",
            (org_id, org_name, org_slug)
        )
        
        user_id = str(uuid.uuid4())
        pw_hash = hash_password(password)
        
        conn.execute(
            """
            INSERT INTO users (id, email, password_hash, full_name, role, is_active)
            VALUES (?, ?, ?, ?, 'HR', 1)
            """,
            (user_id, email_clean, pw_hash, full_name.strip())
        )
        
        conn.execute(
            """
            INSERT INTO organization_memberships (id, organization_id, user_id, org_role)
            VALUES (?, ?, ?, 'OWNER')
            """,
            (str(uuid.uuid4()), org_id, user_id)
        )
        
    return {
        "status": "success",
        "user_id": user_id,
        "email": email_clean,
        "role": "HR",
        "organization_id": org_id,
        "organization_name": org_name,
        "organization_slug": org_slug,
        "org_role": "OWNER"
    }

def main():
    parser = argparse.ArgumentParser(description="ARCHITECH One-Time Admin & Organization Provisioning")
    parser.add_argument("--email", required=True, help="Administrator email")
    parser.add_argument("--password", required=True, help="Strong administrator password")
    parser.add_argument("--name", required=True, help="Administrator full name")
    parser.add_argument("--org-name", required=True, help="Primary Organization name")
    
    args = parser.parse_args()
    try:
        result = provision_initial_admin(
            email=args.email,
            password=args.password,
            full_name=args.name,
            organization_name=args.org_name
        )
        print("\n✅ Initial Administrator successfully provisioned:")
        print(f"   User ID: {result['user_id']}")
        print(f"   Email:   {result['email']}")
        print(f"   Role:    {result['role']} (Org: {result['organization_name']})")
    except Exception as e:
        print(f"\n❌ Provisioning failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
