import sys
import os
import requests
from pyiceberg.catalog import load_catalog
from dotenv import load_dotenv

load_dotenv()

# Add the parent directory to sys.path so we can import our app module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.polaris_client import PolarisApiClient

print("⚙️ Automating Polaris RBAC Setup...")

try:
    # 1. Authenticate as Admin via API Client
    client = PolarisApiClient(
        base_url="http://localhost:8181/api/management/v1",
        token_url="http://localhost:8181/api/catalog/v1/oauth/tokens",
        client_id=os.environ.get("POLARIS_ADMIN_CLIENT_ID", "admin"),
        client_secret=os.environ.get("POLARIS_ADMIN_CLIENT_SECRET", "password")
    )
    client.authenticate()
    print("✅ Authenticated as Polaris Admin")

    # 2. Create Principal
    principal_name = os.environ.get("POLARIS_USER_NAME", "sankeerth")
    try:
        client.create_principal(principal_name)
        print(f"✅ Created Principal '{principal_name}'")
    except Exception as e:
        print(f"⚠️ Principal '{principal_name}' may already exist: {e}")

    # 3. Create Principal Role
    principal_role = "polaris_warehouse_analyst"
    try:
        client.create_principal_role(principal_role)
        print(f"✅ Created Principal Role '{principal_role}'")
    except Exception as e:
        print(f"⚠️ Principal Role '{principal_role}' may already exist: {e}")

    # 4. Create Catalog Role
    catalog_name = "warehouse"
    catalog_role = "warehouse_read"
    try:
        client.create_catalog_role(catalog_name, catalog_role)
        print(f"✅ Created Catalog Role '{catalog_role}' in '{catalog_name}'")
    except Exception as e:
        print(f"⚠️ Catalog Role '{catalog_role}' may already exist: {e}")

    # 5. Map Principal to Principal Role
    try:
        client.assign_role_to_principal(principal_name, principal_role)
        print(f"✅ Assigned '{principal_name}' -> '{principal_role}'")
    except Exception as e:
        print(f"⚠️ Principal mapping may already exist: {e}")

    # 6. Map Principal Role to Catalog Role
    try:
        client.assign_catalog_role_to_principal_role(principal_role, catalog_name, catalog_role)
        print(f"✅ Assigned '{principal_role}' -> '{catalog_role}'")
    except Exception as e:
        print(f"⚠️ Catalog Role mapping may already exist: {e}")

    # 7. Grant CATALOG_MANAGE_CONTENT to Catalog Role
    grant_data = {
        "type": "catalog",
        "privilege": "CATALOG_MANAGE_CONTENT"
    }
    try:
        client.add_grant_to_catalog_role(catalog_name, catalog_role, grant_data)
        print(f"✅ Granted 'CATALOG_MANAGE_CONTENT' to '{catalog_role}'")
    except Exception as e:
        print(f"⚠️ Grant may already exist: {e}")

    print("\n🧪 Starting Polaris Access Verification for user 'sankeerth'...")

    # 8. Fetch sankeerth's OIDC access token from Keycloak
    print("🔑 Authenticating 'sankeerth' with Keycloak OIDC...")
    token_resp = requests.post(
        "http://localhost:8080/realms/polaris-realm/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": "polaris-client",
            "client_secret": os.environ.get("KEYCLOAK_CLIENT_SECRET", "sBbUvTG7qWGbmgwgxKmnEuzqpuE3uGAu"),
            "username": os.environ.get("POLARIS_USER_NAME", "sankeerth"),
            "password": os.environ.get("POLARIS_USER_PASSWORD", "nagapuri"),
            "scope": "openid profile"
        },
        timeout=10
    )
    if token_resp.status_code != 200:
        print(f"Keycloak Error: {token_resp.text}")
    token_resp.raise_for_status()
    access_token = token_resp.json()["access_token"]
    print("✅ Authenticated with Keycloak!")

    import json
    import base64
    parts = access_token.split('.')
    if len(parts) >= 2:
        payload = json.loads(base64.urlsafe_b64decode(parts[1] + "====").decode('utf-8'))
        print(f"🔍 JWT Payload: {json.dumps(payload, indent=2)}")

    # 9. Connect to Polaris using the retrieved token
    print("🔗 Connecting to Polaris catalog as 'sankeerth'...")
    catalog = load_catalog(
        "warehouse",
        type="rest",
        uri="http://localhost:8181/api/catalog",
        warehouse="warehouse",
        token=access_token,
        **{
            "header.X-Iceberg-Access-Delegation": "none",
            "s3.endpoint": "http://localhost:9000",
            "s3.access-key-id": "admin",
            "s3.secret-access-key": "password",
            "s3.path-style-access": "true",
            "s3.region": "us-east-1",
        }
    )
    
    # List the namespaces (equivalent to schemas)
    namespaces = catalog.list_namespaces()
    print("\n✅ SUCCESS: Successfully authenticated and accessed the 'warehouse' catalog!")
    print(f"📂 Available Namespaces (Schemas): {namespaces}")
    
except Exception as e:
    print(f"\n❌ ERROR: Script failed. Details: {e}")
    sys.exit(1)
