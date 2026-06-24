import json
import time

import requests
from pyiceberg.catalog import load_catalog
from pyiceberg.exceptions import NoSuchTableError

# Fixed configuration for this quickstart setup.
POLARIS_MANAGEMENT = "http://localhost:8181/api/management/v1"
POLARIS_CATALOG_URI = "http://localhost:8181/api/catalog"
AUTH_URL = "http://localhost:8181/api/catalog/v1/oauth/tokens"

WAREHOUSE_NAME = "warehouse"
NAMESPACE_NAME = "schema_1"
TABLE_NAME = "table_1"
MINIO_ENDPOINT = "http://minio:9000"      # used by Polaris / catalog storage config
LOCAL_S3_ENDPOINT = "http://localhost:9000"  # used by the local Python process for writes

CLIENT_ID = "admin"
CLIENT_SECRET = "password"
S3_ACCESS_KEY_ID = "admin"
S3_SECRET_ACCESS_KEY = "password"
AWS_REGION = "us-east-1"

MAX_RETRIES = 20
RETRY_DELAY = 3


def use_local_s3_io(table):
    """Force the table IO layer to use the host-accessible MinIO endpoint."""
    io = getattr(table, "io", None) or getattr(table, "_io", None)
    if io is None:
        return table

    props = getattr(io, "properties", None)
    if props is None:
        return table

    props.update(
        {
            "s3.endpoint": LOCAL_S3_ENDPOINT,
            "s3.access-key-id": S3_ACCESS_KEY_ID,
            "s3.secret-access-key": S3_SECRET_ACCESS_KEY,
            "s3.path-style-access": "true",
            "s3.region": AWS_REGION,
        }
    )

    fs_cache = getattr(io, "fs_by_scheme", None)
    if fs_cache is not None and hasattr(fs_cache, "cache_clear"):
        fs_cache.cache_clear()

    if hasattr(io, "_filesystem"):
        io._filesystem = None

    return table


# 1) Get a token from Polaris (with retry logic).
print("🔑 Authenticating with Polaris...")
token = None
for attempt in range(MAX_RETRIES):
    try:
        resp = requests.post(
            AUTH_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "scope": "PRINCIPAL_ROLE:ALL",
            },
            timeout=30,
        )
        resp.raise_for_status()
        token = resp.json()["access_token"]
        print("✅ Authenticated with Polaris")
        break
    except requests.exceptions.RequestException as e:
        print(f"⚠️  Attempt {attempt + 1}/{MAX_RETRIES}: Failed to connect - {e}")
        if attempt < MAX_RETRIES - 1:
            time.sleep(RETRY_DELAY)
        else:
            raise Exception("Failed to authenticate with Polaris after multiple attempts.")

headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# 2) Create warehouse if it doesn't exist
print(f"\n📦 Checking/Creating warehouse '{WAREHOUSE_NAME}'...")
resp = requests.get(f"{POLARIS_MANAGEMENT}/catalogs/{WAREHOUSE_NAME}", headers=headers)
if resp.status_code == 200:
    print(f"✅ Warehouse '{WAREHOUSE_NAME}' already exists")
else:
    print(f"📝 Creating warehouse '{WAREHOUSE_NAME}' with endpoint '{MINIO_ENDPOINT}'...")
    body = {
        "catalog": {
            "name": WAREHOUSE_NAME,
            "type": "INTERNAL",
            "properties": {"default-base-location": f"s3://{WAREHOUSE_NAME}"},
            "storageConfigInfo": {
                "storageType": "S3",
                "allowedLocations": [f"s3://{WAREHOUSE_NAME}/*"],
                "region": AWS_REGION,
                "endpoint": MINIO_ENDPOINT,
                "pathStyleAccess": True,
                "stsUnavailable": True,
            },
        }
    }
    resp = requests.post(f"{POLARIS_MANAGEMENT}/catalogs", headers=headers, data=json.dumps(body))
    if resp.status_code in [200, 201]:
        print(f"✅ Warehouse '{WAREHOUSE_NAME}' created")
    elif resp.status_code == 409:
        print(f"✅ Warehouse '{WAREHOUSE_NAME}' already exists (409)")
    else:
        print(f"❌ Failed to create warehouse: {resp.text}")
        raise Exception(f"Warehouse creation failed: {resp.text}")

# 3) Open the Polaris catalog as an Iceberg REST catalog
print(f"\n🔗 Connecting to Polaris catalog (warehouse: {WAREHOUSE_NAME})...")
try:
    # Polaris currently rejects the default delegated write path for this setup.
    # Disable Iceberg access delegation so table creation uses the bearer token directly.
    catalog = load_catalog(
        "polaris",
        type="rest",
        uri=POLARIS_CATALOG_URI,
        warehouse=WAREHOUSE_NAME,
        token=token,
        **{
            "header.X-Iceberg-Access-Delegation": "none",
            "s3.endpoint": LOCAL_S3_ENDPOINT,
            "s3.access-key-id": S3_ACCESS_KEY_ID,
            "s3.secret-access-key": S3_SECRET_ACCESS_KEY,
            "s3.path-style-access": "true",
            "s3.region": AWS_REGION,
        },
    )
    print("✅ Connected to Polaris catalog")
except Exception as e:
    print(f"❌ Error loading catalog: {e}")
    raise

# 4) Ensure the namespace exists before using it
print(f"\n🗂️ Checking/Creating namespace '{NAMESPACE_NAME}'...")
try:
    namespaces = catalog.list_namespaces()
    namespace_exists = any(
        ns == (NAMESPACE_NAME,) or ns == NAMESPACE_NAME or ns[0] == NAMESPACE_NAME
        for ns in namespaces
    )

    if namespace_exists:
        print(f"✅ Namespace '{NAMESPACE_NAME}' already exists")
    else:
        catalog.create_namespace(NAMESPACE_NAME)
        print(f"✅ Namespace '{NAMESPACE_NAME}' created")
except Exception as e:
    print(f"❌ Error ensuring namespace '{NAMESPACE_NAME}': {e}")
    raise

# 5) List namespaces and tables
print(f"\n📋 Listing namespaces:")
print(f"   Namespaces: {catalog.list_namespaces()}")

print(f"\n📋 Listing tables in '{NAMESPACE_NAME}':")
try:
    tables = catalog.list_tables(NAMESPACE_NAME)
    print(f"   Tables: {tables}")
except Exception as e:
    print(f"   (No tables in namespace '{NAMESPACE_NAME}' yet: {e})")


# 6) Create or load the table and append data.

import pyarrow as pa

# Create a small dummy table since the local data folder was removed
data = {
    'id': [1, 2, 3],
    'name': ['Alice', 'Bob', 'Charlie']
}
df = pa.Table.from_pydict(data)
table_identifier = f"{NAMESPACE_NAME}.{TABLE_NAME}"

try:
    table = catalog.load_table(table_identifier)
    print(f"✅ Table '{table_identifier}' already exists; appending data")
except NoSuchTableError:
    table = catalog.create_table(
        table_identifier,
        schema=df.schema,
    )
    print(f"✅ Created table '{table_identifier}'")

use_local_s3_io(table)

try:
    table.append(df)
    print(f"✅ Appended rows: {len(table.scan().to_arrow())}")
except Exception as e:
    print(f"❌ Append failed: {e}")
    raise