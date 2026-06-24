-- Install required DuckDB extensions
INSTALL httpfs;
INSTALL iceberg;
LOAD httpfs;
LOAD iceberg;

-- Configure credentials for Apache Polaris Catalog
CREATE OR REPLACE SECRET iceberg_secret (
    TYPE iceberg,
    CLIENT_ID 'admin',
    CLIENT_SECRET 'password',
    OAUTH2_SERVER_URI 'http://localhost:8181/api/catalog/v1/oauth/tokens'
);

-- Configure credentials for MinIO storage
CREATE OR REPLACE SECRET minio_s3_secret (
    TYPE s3,
    KEY_ID 'admin',
    SECRET 'password',
    REGION 'us-east-1',
    ENDPOINT 'localhost:9000',
    URL_STYLE 'path',
    USE_SSL false
);

-- Connect to the 'warehouse' catalog
ATTACH 'warehouse' AS polaris_catalog (
    TYPE iceberg,
    SECRET iceberg_secret,
    ENDPOINT 'http://localhost:8181/api/catalog',
    ACCESS_DELEGATION_MODE 'none'
);

USE polaris_catalog;
CREATE SCHEMA IF NOT EXISTS polaris_catalog.duckdb;
SHOW SCHEMAS;
SHOW TABLES FROM polaris_catalog.duckdb;

USE polaris_catalog.duckdb;

-- Create a table using NYC Taxi data parquet file
CREATE TABLE polaris_catalog.duckdb.taxi7 AS
SELECT * FROM read_parquet(
  'https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2025-01.parquet'
);

SELECT * FROM polaris_catalog.duckdb.taxi7 LIMIT 10;
