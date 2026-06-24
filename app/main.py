# pyrefly: ignore [missing-import]
import streamlit as st
from polaris_client import PolarisApiClient, decode_token
import os
from dotenv import load_dotenv

load_dotenv()

"""
Apache Polaris RBAC Manager Streamlit Application.

This module provides a visual dashboard to interact with the Apache Polaris Management API.
It allows users to configure Catalogs, Principals, Roles, Grants, and explore data
via an integrated Iceberg REST client.
"""

# Set page configuration
st.set_page_config(
    page_title="Apache Polaris RBAC Manager",
    page_icon="🔒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ----------------------------------------------------
# 2. STREAMLIT UI SETUP & SESSION STATE
# ----------------------------------------------------
if "auth_status" not in st.session_state:
    st.session_state.auth_status = None
if "api_client" not in st.session_state:
    st.session_state.api_client = None
if "auth_user" not in st.session_state:
    st.session_state.auth_user = None

# Sidebar Authentication panel
st.sidebar.title("🔐 Apache Polaris Connection")

base_url_input = st.sidebar.text_input("Management API Base URL", value="http://localhost:8181/api/management/v1")
token_url_input = st.sidebar.text_input("OAuth2 Token URL", value="http://localhost:8181/api/catalog/v1/oauth/tokens")

# Connection Status & Logout
if st.session_state.auth_status == "Connected":
    st.sidebar.markdown(f'<span style="color:green; font-weight:bold;">● Status: Connected ({st.session_state.auth_user})</span>', unsafe_allow_html=True)
    if st.sidebar.button("🔌 Logout", use_container_width=True, key="logout_btn"):
        st.session_state.auth_status = None
        st.session_state.api_client = None
        st.session_state.auth_user = None
        st.rerun()
else:
    st.sidebar.markdown('<span style="color:red; font-weight:bold;">● Status: Disconnected</span>', unsafe_allow_html=True)

# Main Application Title
st.title("🔒 Apache Polaris RBAC Management Dashboard")
st.markdown("Easily configure users, catalogs, roles, mapping relationships, and access privileges according to the Polaris Management API.")

if st.session_state.auth_status != "Connected":
    st.info("💡 **Welcome!** Please choose an authentication method below to connect to the Apache Polaris server.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🔑 Option A: Local Admin Credentials")
        st.caption("Authenticate using standard bootstrap admin client credentials.")
        
        client_id_input = st.text_input("Admin Client ID", value=os.environ.get("POLARIS_ADMIN_CLIENT_ID", "admin"), key="admin_client_id_main")
        client_secret_input = st.text_input("Admin Client Secret", value=os.environ.get("POLARIS_ADMIN_CLIENT_SECRET", "password"), type="password", key="admin_client_secret_main")
        
        if st.button("🔌 Connect with Credentials", use_container_width=True, key="admin_connect_btn_main"):
            client = PolarisApiClient(base_url_input, token_url_input, client_id_input, client_secret_input)
            success, msg = client.authenticate()
            if success:
                st.session_state.api_client = client
                st.session_state.auth_status = "Connected"
                st.session_state.auth_user = "admin"
                st.success("✅ Authenticated!")
                st.rerun()
            else:
                st.error(f"❌ {msg}")
                
    with col2:
        st.markdown("### 🌐 Option B: Keycloak SSO (OIDC)")
        st.caption("Sign in with centralized Single Sign-On powered by Keycloak.")
        
        # Initialize session state for SSO config if not present
        if "sso_client_id" not in st.session_state:
            st.session_state.sso_client_id = os.environ.get("KEYCLOAK_CLIENT_ID", "polaris-client")
        if "sso_client_secret" not in st.session_state:
            st.session_state.sso_client_secret = os.environ.get("KEYCLOAK_CLIENT_SECRET", "sBbUvTG7qWGbmgwgxKmnEuzqpuE3uGAu")
        if "sso_auth_url" not in st.session_state:
            st.session_state.sso_auth_url = os.environ.get("KEYCLOAK_AUTH_URL", "http://localhost:8080/realms/polaris-realm/protocol/openid-connect/auth")
        if "sso_token_url" not in st.session_state:
            st.session_state.sso_token_url = os.environ.get("KEYCLOAK_TOKEN_URL", "http://localhost:8080/realms/polaris-realm/protocol/openid-connect/token")
        if "sso_redirect_uri" not in st.session_state:
            st.session_state.sso_redirect_uri = os.environ.get("KEYCLOAK_REDIRECT_URI", "http://localhost:8501/")

        try:
            from streamlit_oauth import OAuth2Component
            oauth2 = OAuth2Component(
                st.session_state.sso_client_id, 
                st.session_state.sso_client_secret, 
                st.session_state.sso_auth_url, 
                st.session_state.sso_token_url, 
                "", ""
            )
            
            # Use a persistent static key for the custom component to guarantee rendering
            result = oauth2.authorize_button("Sign in with Keycloak", redirect_uri=st.session_state.sso_redirect_uri, scope="openid profile", key="keycloak_auth_btn")
            if result:
                access_token = result.get("token", {}).get("access_token")
                if access_token:
                    client = PolarisApiClient(base_url_input, token_url_input, None, None, token=access_token)
                    st.session_state.api_client = client
                    st.session_state.auth_status = "Connected"
                    
                    # Try to decode username from token
                    token_info = decode_token(access_token) or {}
                    user_name = token_info.get("preferred_username") or token_info.get("sub") or "OIDC User"
                    st.session_state.auth_user = user_name
                    st.success("✅ Authenticated via SSO!")
                    st.rerun()
        except ImportError:
            st.warning("⚠️ 'streamlit-oauth' is not installed. Please run 'pip install streamlit-oauth' in your terminal.")

        # Show advanced configurations in a nested expander for optional overrides
        with st.expander("⚙️ Advanced SSO Settings", expanded=False):
            new_client_id = st.text_input("SSO Client ID", value=st.session_state.sso_client_id, key="sso_client_id_main")
            new_client_secret = st.text_input("SSO Client Secret", value=st.session_state.sso_client_secret, type="password", key="sso_client_secret_main")
            new_auth_url = st.text_input("SSO Authorize URL", value=st.session_state.sso_auth_url, key="sso_auth_url_main")
            new_token_url = st.text_input("SSO Token URL", value=st.session_state.sso_token_url, key="sso_token_url_main")
            new_redirect_uri = st.text_input("SSO Redirect URI", value=st.session_state.sso_redirect_uri, key="sso_redirect_uri_main")
            
            # If the user edits any field, update the session state and rerun to apply
            if (new_client_id != st.session_state.sso_client_id or 
                new_client_secret != st.session_state.sso_client_secret or 
                new_auth_url != st.session_state.sso_auth_url or 
                new_token_url != st.session_state.sso_token_url or 
                new_redirect_uri != st.session_state.sso_redirect_uri):
                st.session_state.sso_client_id = new_client_id
                st.session_state.sso_client_secret = new_client_secret
                st.session_state.sso_auth_url = new_auth_url
                st.session_state.sso_token_url = new_token_url
                st.session_state.sso_redirect_uri = new_redirect_uri
                st.rerun()
    st.stop()

client = st.session_state.api_client

# Define the tabs
tab_catalogs, tab_principals, tab_principal_roles, tab_catalog_roles, tab_assignments, tab_grants, tab_explorer = st.tabs([
    "📂 Catalogs", "👤 Principals (Users)", "🎫 Principal Roles", "🏷️ Catalog Roles", "🔗 RBAC Mapping", "🎯 Grants & Privileges", "📊 Data Explorer"
])

# ----------------------------------------------------
# HELPER FUNCTIONS FOR RENDERING
# ----------------------------------------------------
def parse_properties_input(properties_str):
    """Parse comma-separated key=value string into a dict"""
    if not properties_str.strip():
        return {}
    props = {}
    for item in properties_str.split(','):
        if '=' in item:
            k, v = item.split('=', 1)
            props[k.strip()] = v.strip()
    return props

def format_properties(props_dict):
    """Format property dict to comma-separated string"""
    if not props_dict:
        return ""
    return ", ".join([f"{k}={v}" for k, v in props_dict.items()])

# ----------------------------------------------------
# TAB 1: CATALOGS MANAGEMENT
# ----------------------------------------------------
with tab_catalogs:
    st.header("📂 Catalog Management")
    
    col1, col2 = st.columns([1, 1])
    
    success_list, catalogs_data = client.list_catalogs()
    catalogs_list = catalogs_data.get("catalogs", []) if success_list else []
    
    with col1:
        st.subheader("Existing Catalogs")
        if catalogs_list:
            catalog_names = [cat["name"] for cat in catalogs_list]
            selected_cat_name = st.selectbox("Select a catalog to inspect/delete", catalog_names, key="select_cat")
            
            # Find selected catalog details
            selected_cat = next(cat for cat in catalogs_list if cat["name"] == selected_cat_name)
            
            st.markdown(f"**Catalog Name:** `{selected_cat['name']}`")
            st.markdown(f"**Type:** `{selected_cat['type']}`")
            st.markdown(f"**Entity Version:** `{selected_cat.get('entityVersion', '')}`")
            
            # Storage Config details
            st.write("---")
            st.subheader("Storage Configuration")
            storage_info = selected_cat.get("storageConfigInfo", {})
            st.write(storage_info)
            
            # Properties
            st.write("---")
            st.subheader("Properties")
            st.write(selected_cat.get("properties", {}))
            
            if st.button("🗑️ Delete Catalog", key="del_cat_btn"):
                ok, err = client.delete_catalog(selected_cat_name)
                if ok:
                    st.success(f"Deleted catalog '{selected_cat_name}' successfully!")
                    st.rerun()
                else:
                    st.error(f"Failed to delete catalog: {err}")
        else:
            st.info("No catalogs found.")

    with col2:
        st.subheader("🆕 Create New Catalog")
        
        with st.form("create_catalog_form"):
            cat_name = st.text_input("Catalog Name", placeholder="e.g. staging_warehouse")
            cat_type = st.selectbox("Catalog Type", ["INTERNAL", "EXTERNAL"])
            
            st.markdown("**Storage Configuration Details**")
            storage_type = st.selectbox("Storage Type", ["S3", "GCS", "AZURE", "FILE"])
            allowed_locations_str = st.text_area("Allowed Locations (comma separated)", placeholder="s3://bucket/path/*")
            
            # Additional storage settings based on storage type
            role_arn = ""
            region = ""
            endpoint = ""
            path_style = False
            sts_unavailable = False
            
            if storage_type == "S3":
                role_arn = st.text_input("IAM Role ARN (optional)", placeholder="arn:aws:iam::123456789:role/polaris-role")
                region = st.text_input("Region", value="us-east-1")
                endpoint = st.text_input("S3 Endpoint (optional, e.g. for MinIO)", placeholder="http://localhost:9000")
                path_style = st.checkbox("Path Style Access", value=True)
                sts_unavailable = st.checkbox("STS Unavailable (vends access-keys directly, useful for MinIO)", value=True)
            elif storage_type == "AZURE":
                tenant_id = st.text_input("Tenant ID")
            
            default_base_location = st.text_input("Default Base Location (properties)", placeholder="s3://bucket/path")
            properties_str = st.text_input("Extra Properties (comma-separated key=val)", placeholder="prop1=val1,prop2=val2")
            
            submitted = st.form_submit_button("Create Catalog")
            if submitted:
                if not cat_name:
                    st.error("Catalog Name is required.")
                else:
                    # Construct Catalog request object
                    allowed_locations = [loc.strip() for loc in allowed_locations_str.split(',') if loc.strip()]
                    
                    storage_config = {
                        "storageType": storage_type,
                        "allowedLocations": allowed_locations
                    }
                    
                    if storage_type == "S3":
                        if role_arn:
                            storage_config["roleArn"] = role_arn
                        storage_config["region"] = region
                        if endpoint:
                            storage_config["endpoint"] = endpoint
                        storage_config["pathStyleAccess"] = path_style
                        storage_config["stsUnavailable"] = sts_unavailable
                    elif storage_type == "AZURE":
                        storage_config["tenantId"] = tenant_id
                    
                    properties = parse_properties_input(properties_str)
                    if default_base_location:
                        properties["default-base-location"] = default_base_location
                    
                    catalog_payload = {
                        "name": cat_name,
                        "type": cat_type,
                        "storageConfigInfo": storage_config,
                        "properties": properties
                    }
                    
                    ok, res = client.create_catalog(catalog_payload)
                    if ok:
                        st.success(f"Catalog '{cat_name}' created successfully!")
                        st.rerun()
                    else:
                        st.error(f"Failed to create catalog: {res}")

# ----------------------------------------------------
# TAB 2: PRINCIPALS (USERS) MANAGEMENT
# ----------------------------------------------------
with tab_principals:
    st.header("👤 Principal (User) Management")
    
    col1, col2 = st.columns([1, 1])
    
    success_pr, principals_data = client.list_principals()
    principals_list = principals_data.get("principals", []) if success_pr else []
    
    with col1:
        st.subheader("Existing Principals")
        if principals_list:
            principal_names = [p["name"] for p in principals_list]
            selected_pr_name = st.selectbox("Select a principal to inspect/manage", principal_names, key="select_pr")
            
            selected_pr = next(p for p in principals_list if p["name"] == selected_pr_name)
            
            st.markdown(f"**Principal Name:** `{selected_pr['name']}`")
            st.markdown(f"**Client ID:** `{selected_pr.get('clientId', 'N/A')}`")
            st.markdown(f"**Entity Version:** `{selected_pr.get('entityVersion', '')}`")
            
            st.write("---")
            st.subheader("Properties")
            st.write(selected_pr.get("properties", {}))
            
            st.write("---")
            st.subheader("Credentials & Actions")
            
            col_rot, col_del = st.columns(2)
            with col_rot:
                if st.button("🔄 Rotate Credentials", use_container_width=True, key="rot_cred_btn"):
                    ok, res = client.rotate_credentials(selected_pr_name)
                    if ok:
                        st.success("Credentials rotated successfully!")
                        creds = res.get("credentials", {})
                        st.warning("⚠️ Write down the rotated credentials now; they cannot be retrieved again!")
                        st.code(f"Client ID: {creds.get('clientId')}\nClient Secret: {creds.get('clientSecret')}")
                    else:
                        st.error(f"Failed to rotate credentials: {res}")
                        
                if st.button("🔑 Reset Credentials", use_container_width=True, key="reset_cred_btn"):
                    ok, res = client.reset_credentials(selected_pr_name)
                    if ok:
                        st.success("Credentials reset successfully!")
                        creds = res.get("credentials", {})
                        st.warning("⚠️ Write down the reset credentials now; they cannot be retrieved again!")
                        st.code(f"Client ID: {creds.get('clientId')}\nClient Secret: {creds.get('clientSecret')}")
                    else:
                        st.error(f"Failed to reset credentials: {res}")
            
            with col_del:
                if st.button("🗑️ Delete Principal", use_container_width=True, key="del_pr_btn"):
                    ok, err = client.delete_principal(selected_pr_name)
                    if ok:
                        st.success(f"Deleted principal '{selected_pr_name}' successfully!")
                        st.rerun()
                    else:
                        st.error(f"Failed to delete principal: {err}")
        else:
            st.info("No principals found.")

    with col2:
        st.subheader("🆕 Create New Principal")
        with st.form("create_principal_form"):
            pr_name = st.text_input("Principal Name", placeholder="e.g. analyst_bob")
            properties_str = st.text_input("Properties (comma-separated key=val)", placeholder="department=analytics,env=production")
            rotation_req = st.checkbox("Require Credential Rotation on First Login", value=False)
            
            submitted = st.form_submit_button("Create Principal")
            if submitted:
                if not pr_name:
                    st.error("Principal Name is required.")
                else:
                    properties = parse_properties_input(properties_str)
                    principal_payload = {
                        "name": pr_name,
                        "properties": properties
                    }
                    ok, res = client.create_principal(principal_payload, rotation_req)
                    if ok:
                        st.success(f"Principal '{pr_name}' created successfully!")
                        creds = res.get("credentials", {})
                        st.warning("⚠️ Write down the credentials now; they cannot be retrieved again!")
                        st.code(f"Client ID: {creds.get('clientId')}\nClient Secret: {creds.get('clientSecret')}")
                        # Refresh lists
                        st.rerun()
                    else:
                        st.error(f"Failed to create principal: {res}")

# ----------------------------------------------------
# TAB 3: PRINCIPAL ROLES MANAGEMENT
# ----------------------------------------------------
with tab_principal_roles:
    st.header("🎫 Principal Role Management")
    
    col1, col2 = st.columns([1, 1])
    
    success_pr_roles, pr_roles_data = client.list_principal_roles()
    pr_roles_list = pr_roles_data.get("roles", []) if success_pr_roles else []
    
    with col1:
        st.subheader("Existing Principal Roles")
        if pr_roles_list:
            pr_role_names = [role["name"] for role in pr_roles_list]
            selected_pr_role = st.selectbox("Select a principal role to inspect/delete", pr_role_names, key="select_pr_role")
            
            selected_role = next(role for role in pr_roles_list if role["name"] == selected_pr_role)
            
            st.markdown(f"**Principal Role Name:** `{selected_role['name']}`")
            st.markdown(f"**Federated:** `{selected_role.get('federated', False)}`")
            st.markdown(f"**Entity Version:** `{selected_role.get('entityVersion', '')}`")
            
            st.write("---")
            st.subheader("Properties")
            st.write(selected_role.get("properties", {}))
            
            if st.button("🗑️ Delete Principal Role", key="del_pr_role_btn"):
                ok, err = client.delete_principal_role(selected_pr_role)
                if ok:
                    st.success(f"Deleted principal role '{selected_pr_role}' successfully!")
                    st.rerun()
                else:
                    st.error(f"Failed to delete principal role: {err}")
        else:
            st.info("No principal roles found.")

    with col2:
        st.subheader("🆕 Create New Principal Role")
        with st.form("create_principal_role_form"):
            role_name = st.text_input("Principal Role Name", placeholder="e.g. data_analyst")
            federated = st.checkbox("Federated Role (Managed by External Identity Provider)", value=False)
            properties_str = st.text_input("Properties (comma-separated key=val)", placeholder="managed_by=okta")
            
            submitted = st.form_submit_button("Create Principal Role")
            if submitted:
                if not role_name:
                    st.error("Principal Role Name is required.")
                else:
                    properties = parse_properties_input(properties_str)
                    role_payload = {
                        "name": role_name,
                        "federated": federated,
                        "properties": properties
                    }
                    ok, res = client.create_principal_role(role_payload)
                    if ok:
                        st.success(f"Principal Role '{role_name}' created successfully!")
                        st.rerun()
                    else:
                        st.error(f"Failed to create principal role: {res}")

# ----------------------------------------------------
# TAB 4: CATALOG ROLES MANAGEMENT
# ----------------------------------------------------
with tab_catalog_roles:
    st.header("🏷️ Catalog Role Management")
    
    if not catalogs_list:
        st.warning("⚠️ Please create a Catalog first in the 'Catalogs' tab.")
    else:
        selected_catalog = st.selectbox("Select Catalog to view/manage roles", [cat["name"] for cat in catalogs_list], key="cat_roles_selector")
        
        col1, col2 = st.columns([1, 1])
        
        success_cat_roles, cat_roles_data = client.list_catalog_roles(selected_catalog)
        cat_roles_list = cat_roles_data.get("roles", []) if success_cat_roles else []
        
        with col1:
            st.subheader(f"Catalog Roles in '{selected_catalog}'")
            if cat_roles_list:
                cat_role_names = [role["name"] for role in cat_roles_list]
                selected_cat_role = st.selectbox("Select a catalog role to inspect/delete", cat_role_names, key="select_cat_role")
                
                selected_role = next(role for role in cat_roles_list if role["name"] == selected_cat_role)
                
                st.markdown(f"**Catalog Role Name:** `{selected_role['name']}`")
                st.markdown(f"**Entity Version:** `{selected_role.get('entityVersion', '')}`")
                
                st.write("---")
                st.subheader("Properties")
                st.write(selected_role.get("properties", {}))
                
                if st.button("🗑️ Delete Catalog Role", key="del_cat_role_btn"):
                    ok, err = client.delete_catalog_role(selected_catalog, selected_cat_role)
                    if ok:
                        st.success(f"Deleted catalog role '{selected_cat_role}' from catalog '{selected_catalog}'!")
                        st.rerun()
                    else:
                        st.error(f"Failed to delete catalog role: {err}")
            else:
                st.info(f"No catalog roles found in '{selected_catalog}'.")
                
        with col2:
            st.subheader("🆕 Create New Catalog Role")
            with st.form("create_catalog_role_form"):
                catalog_role_name = st.text_input("Catalog Role Name", placeholder="e.g. read_only_role")
                properties_str = st.text_input("Properties (comma-separated key=val)", placeholder="purpose=testing")
                
                submitted = st.form_submit_button("Create Catalog Role")
                if submitted:
                    if not catalog_role_name:
                        st.error("Catalog Role Name is required.")
                    else:
                        properties = parse_properties_input(properties_str)
                        role_payload = {
                            "name": catalog_role_name,
                            "properties": properties
                        }
                        ok, res = client.create_catalog_role(selected_catalog, role_payload)
                        if ok:
                            st.success(f"Catalog Role '{catalog_role_name}' created in catalog '{selected_catalog}'!")
                            st.rerun()
                        else:
                            st.error(f"Failed to create catalog role: {res}")

# ----------------------------------------------------
# TAB 5: RBAC MAPPING (ASSIGNMENTS)
# ----------------------------------------------------
with tab_assignments:
    st.header("🔗 RBAC Assignments Mapping")
    st.markdown("Establish the mapping chain: **Principals 🔀 Principal Roles 🔀 Catalog Roles**")
    
    subtab_user_role, subtab_role_cat = st.tabs(["👤 Principal ↔️ Principal Role", "🎫 Principal Role ↔️ Catalog Role"])
    
    with subtab_user_role:
        st.subheader("Map Principals (Users) to Principal Roles")
        if not principals_list:
            st.warning("Please create at least one Principal first.")
        elif not pr_roles_list:
            st.warning("Please create at least one Principal Role first.")
        else:
            col_usr, col_act = st.columns([1, 1])
            with col_usr:
                selected_user = st.selectbox("Select Principal", [p["name"] for p in principals_list], key="assign_user_sel")
                
                # Fetch currently assigned principal roles for this user
                ok_assigned, assigned_roles_data = client.list_roles_assigned_to_principal(selected_user)
                assigned_roles = assigned_roles_data.get("roles", []) if ok_assigned else []
                assigned_names = [role["name"] for role in assigned_roles]
                
                st.markdown(f"**Currently Assigned Roles for `{selected_user}`:**")
                if assigned_names:
                    for role_name in assigned_names:
                        c_left, c_right = st.columns([3, 1])
                        c_left.write(f"- `{role_name}`")
                        if c_right.button("Revoke", key=f"rev_pr_{selected_user}_{role_name}"):
                            ok, err = client.revoke_role_from_principal(selected_user, role_name)
                            if ok:
                                st.success(f"Revoked `{role_name}` from `{selected_user}`!")
                                st.rerun()
                            else:
                                st.error(f"Failed to revoke role: {err}")
                else:
                    st.info("No roles assigned to this principal.")
            
            with col_act:
                st.markdown("**Assign Role to Principal**")
                # Exclude already assigned roles
                available_roles = [r["name"] for r in pr_roles_list if r["name"] not in assigned_names]
                if available_roles:
                    selected_role_to_assign = st.selectbox("Select Role to Assign", available_roles, key="assign_role_sel")
                    if st.button("🔗 Assign Role", key="assign_role_btn"):
                        ok, err = client.assign_role_to_principal(selected_user, selected_role_to_assign)
                        if ok:
                            st.success(f"Assigned role `{selected_role_to_assign}` to user `{selected_user}`!")
                            st.rerun()
                        else:
                            st.error(f"Failed to assign role: {err}")
                else:
                    st.info("All available principal roles are already assigned to this user.")

    with subtab_role_cat:
        st.subheader("Map Principal Roles to Catalog Roles")
        if not pr_roles_list:
            st.warning("Please create at least one Principal Role first.")
        elif not catalogs_list:
            st.warning("Please create at least one Catalog first.")
        else:
            col_pr_role, col_cat_role = st.columns([1, 1])
            with col_pr_role:
                selected_pr_role_map = st.selectbox("Select Principal Role", [r["name"] for r in pr_roles_list], key="map_pr_role_sel")
                selected_catalog_map = st.selectbox("Select Target Catalog", [c["name"] for c in catalogs_list], key="map_catalog_sel")
                
                # Fetch currently assigned catalog roles for this principal role under this catalog
                ok_assigned, assigned_cat_roles_data = client.list_catalog_roles_for_principal_role(selected_pr_role_map, selected_catalog_map)
                assigned_cat_roles = assigned_cat_roles_data.get("roles", []) if ok_assigned else []
                assigned_cat_names = [role["name"] for role in assigned_cat_roles]
                
                st.markdown(f"**Assigned Catalog Roles (in `{selected_catalog_map}`) for `{selected_pr_role_map}`:**")
                if assigned_cat_names:
                    for cat_role_name in assigned_cat_names:
                        c_left, c_right = st.columns([3, 1])
                        c_left.write(f"- `{cat_role_name}`")
                        if c_right.button("Revoke", key=f"rev_cat_{selected_pr_role_map}_{selected_catalog_map}_{cat_role_name}"):
                            ok, err = client.revoke_catalog_role_from_principal_role(selected_pr_role_map, selected_catalog_map, cat_role_name)
                            if ok:
                                st.success(f"Revoked `{cat_role_name}` from `{selected_pr_role_map}`!")
                                st.rerun()
                            else:
                                st.error(f"Failed to revoke catalog role: {err}")
                else:
                    st.info(f"No catalog roles in `{selected_catalog_map}` are assigned to `{selected_pr_role_map}`.")
            
            with col_cat_role:
                st.markdown("**Assign Catalog Role**")
                # Fetch all catalog roles for this catalog
                ok_cat_roles, all_cat_roles_data = client.list_catalog_roles(selected_catalog_map)
                all_cat_roles = all_cat_roles_data.get("roles", []) if ok_cat_roles else []
                
                # Exclude already assigned catalog roles
                available_cat_roles = [r["name"] for r in all_cat_roles if r["name"] not in assigned_cat_names]
                if available_cat_roles:
                    selected_cat_role_to_assign = st.selectbox("Select Catalog Role to Map", available_cat_roles, key="assign_cat_role_sel")
                    if st.button("🔗 Map Catalog Role", key="map_cat_role_btn"):
                        ok, err = client.assign_catalog_role_to_principal_role(selected_pr_role_map, selected_catalog_map, selected_cat_role_to_assign)
                        if ok:
                            st.success(f"Mapped catalog role `{selected_cat_role_to_assign}` to principal role `{selected_pr_role_map}`!")
                            st.rerun()
                        else:
                            st.error(f"Failed to map catalog role: {err}")
                else:
                    st.info(f"No further catalog roles available in `{selected_catalog_map}` to assign.")

# ----------------------------------------------------
# TAB 6: GRANTS & PRIVILEGES MANAGEMENT
# ----------------------------------------------------
with tab_grants:
    st.header("🎯 Grants & Privileges Management")
    st.markdown("Grant specific permissions to **Catalog Roles** on target objects (Catalog, Namespace, Table, etc.)")
    
    if not catalogs_list:
        st.warning("⚠️ Please create a Catalog first.")
    else:
        col_select, col_actions = st.columns([1, 1])
        
        with col_select:
            selected_catalog_grant = st.selectbox("Select Catalog", [c["name"] for c in catalogs_list], key="grant_catalog_sel")
            
            # Fetch catalog roles for the selected catalog
            ok_cat_roles, catalog_roles_data = client.list_catalog_roles(selected_catalog_grant)
            catalog_roles_in_grant = catalog_roles_data.get("roles", []) if ok_cat_roles else []
            
            if not catalog_roles_in_grant:
                st.warning(f"No catalog roles exist in catalog '{selected_catalog_grant}'. Go to 'Catalog Roles' tab to create one.")
                selected_cat_role_grant = None
            else:
                selected_cat_role_grant = st.selectbox("Select Catalog Role", [r["name"] for r in catalog_roles_in_grant], key="grant_role_sel")
                
                # Fetch current grants for the selected catalog role
                if selected_cat_role_grant:
                    ok_grants, grants_data = client.list_grants_for_catalog_role(selected_catalog_grant, selected_cat_role_grant)
                    grants_list = grants_data.get("grants", []) if ok_grants else []
                    
                    st.subheader("Current Grants")
                    if grants_list:
                        # Display grants in a list/table with Revoke actions
                        cascade_chk = st.checkbox("Cascade revocation to subresources", value=False, key="cascade_revoke")
                        
                        for i, grant in enumerate(grants_list):
                            g_type = grant.get("type", "unknown")
                            g_priv = grant.get("privilege", "unknown")
                            
                            # Build text description based on type
                            desc = f"**Type:** `{g_type}` | **Privilege:** `{g_priv}`"
                            if g_type == "namespace":
                                desc += f" | **Namespace:** `{'.'.join(grant.get('namespace', []))}`"
                            elif g_type == "table":
                                desc += f" | **Table:** `{'.'.join(grant.get('namespace', []))}.{grant.get('tableName', '')}`"
                            elif g_type == "view":
                                desc += f" | **View:** `{'.'.join(grant.get('namespace', []))}.{grant.get('viewName', '')}`"
                            elif g_type == "policy":
                                desc += f" | **Policy:** `{'.'.join(grant.get('namespace', []))}.{grant.get('policyName', '')}`"
                                
                            g_col_text, g_col_btn = st.columns([4, 1])
                            g_col_text.markdown(f"- {desc}")
                            if g_col_btn.button("Revoke", key=f"rev_grant_{i}"):
                                ok, err = client.revoke_grant_from_catalog_role(
                                    selected_catalog_grant, selected_cat_role_grant, grant, cascade=cascade_chk
                                )
                                if ok:
                                    st.success("Successfully revoked grant!")
                                    st.rerun()
                                else:
                                    st.error(f"Failed to revoke grant: {err}")
                    else:
                        st.info(f"Catalog role '{selected_cat_role_grant}' has no grants currently.")
                        
        with col_actions:
            if selected_cat_role_grant:
                st.subheader("🆕 Add New Grant")
                
                with st.form("add_grant_form"):
                    resource_type = st.selectbox("Resource Type", ["catalog", "namespace", "table", "view", "policy"], key="grant_res_type")
                    
                    # Dynamically list privileges based on selected resource type
                    privileges_map = {
                        "catalog": [
                            "CATALOG_MANAGE_ACCESS", "CATALOG_MANAGE_CONTENT", "CATALOG_MANAGE_METADATA",
                            "CATALOG_READ_PROPERTIES", "CATALOG_WRITE_PROPERTIES", "NAMESPACE_CREATE",
                            "TABLE_CREATE", "VIEW_CREATE", "NAMESPACE_DROP", "TABLE_DROP", "VIEW_DROP",
                            "NAMESPACE_LIST", "TABLE_LIST", "VIEW_LIST", "NAMESPACE_READ_PROPERTIES",
                            "TABLE_READ_PROPERTIES", "VIEW_READ_PROPERTIES", "NAMESPACE_WRITE_PROPERTIES",
                            "TABLE_WRITE_PROPERTIES", "VIEW_WRITE_PROPERTIES", "TABLE_READ_DATA", "TABLE_WRITE_DATA"
                        ],
                        "namespace": [
                            "CATALOG_MANAGE_ACCESS", "CATALOG_MANAGE_CONTENT", "CATALOG_MANAGE_METADATA",
                            "NAMESPACE_CREATE", "TABLE_CREATE", "VIEW_CREATE", "NAMESPACE_DROP", "TABLE_DROP",
                            "VIEW_DROP", "NAMESPACE_LIST", "TABLE_LIST", "VIEW_LIST", "NAMESPACE_READ_PROPERTIES",
                            "TABLE_READ_PROPERTIES", "VIEW_READ_PROPERTIES", "NAMESPACE_WRITE_PROPERTIES",
                            "TABLE_WRITE_PROPERTIES", "VIEW_WRITE_PROPERTIES", "TABLE_READ_DATA", "TABLE_WRITE_DATA",
                            "NAMESPACE_FULL_METADATA", "TABLE_FULL_METADATA", "VIEW_FULL_METADATA"
                        ],
                        "table": [
                            "CATALOG_MANAGE_ACCESS", "TABLE_DROP", "TABLE_LIST", "TABLE_READ_PROPERTIES",
                            "TABLE_WRITE_PROPERTIES", "TABLE_READ_DATA", "TABLE_WRITE_DATA", "TABLE_FULL_METADATA",
                            "TABLE_UPGRADE_FORMAT_VERSION", "TABLE_ADD_SCHEMA", "TABLE_SET_CURRENT_SCHEMA"
                        ],
                        "view": [
                            "CATALOG_MANAGE_ACCESS", "VIEW_DROP", "VIEW_LIST", "VIEW_READ_PROPERTIES",
                            "VIEW_WRITE_PROPERTIES", "VIEW_FULL_METADATA"
                        ],
                        "policy": [
                            "CATALOG_MANAGE_ACCESS", "POLICY_READ", "POLICY_DROP", "POLICY_WRITE",
                            "POLICY_LIST", "POLICY_FULL_METADATA", "POLICY_ATTACH", "POLICY_DETACH"
                        ]
                    }
                    
                    selected_privilege = st.selectbox("Privilege", privileges_map[resource_type], key="grant_priv_sel")
                    
                    # Target spec fields
                    st.markdown("**Target Resource Identifiers**")
                    target_namespace = st.text_input("Namespace (dot separated, e.g. schema_1.schema_2)", placeholder="schema_1", disabled=(resource_type == "catalog"))
                    target_name = st.text_input("Target Object Name (Table / View / Policy Name)", placeholder="table_1", disabled=(resource_type in ["catalog", "namespace"]))
                    
                    submitted = st.form_submit_button("Add Grant")
                    if submitted:
                        # Construct target payload
                        grant_payload = {
                            "type": resource_type,
                            "privilege": selected_privilege
                        }
                        
                        # Add target identifiers based on type
                        if resource_type != "catalog":
                            if not target_namespace:
                                st.error("Namespace is required for non-catalog resources.")
                                st.stop()
                            ns_parts = [p.strip() for p in target_namespace.split('.') if p.strip()]
                            grant_payload["namespace"] = ns_parts
                            
                        if resource_type == "table":
                            if not target_name:
                                st.error("Table Name is required.")
                                st.stop()
                            grant_payload["tableName"] = target_name
                        elif resource_type == "view":
                            if not target_name:
                                st.error("View Name is required.")
                                st.stop()
                            grant_payload["viewName"] = target_name
                        elif resource_type == "policy":
                            if not target_name:
                                st.error("Policy Name is required.")
                                st.stop()
                            grant_payload["policyName"] = target_name
                            
                        ok, err = client.add_grant_to_catalog_role(selected_catalog_grant, selected_cat_role_grant, grant_payload)
                        if ok:
                            st.success(f"Granted privilege '{selected_privilege}' successfully!")
                            st.rerun()
                        else:
                            st.error(f"Failed to add grant: {err}")

# ----------------------------------------------------
# TAB 7: DATA EXPLORER (For Analysts)
# ----------------------------------------------------
with tab_explorer:
    st.header("📊 Data Explorer")
    st.markdown("Use your current authentication token to explore data using the Iceberg REST Catalog API. This view is restricted by your assigned roles (e.g., `warehouse_read`).")
    
    explorer_cat = st.text_input("Enter Catalog Name to Explore", value="warehouse")
    
    if st.button("Connect & Explore", key="btn_explore"):
        if not explorer_cat:
            st.error("Please enter a catalog name.")
        else:
            try:
                from pyiceberg.catalog import load_catalog
                with st.spinner(f"Connecting to Iceberg Catalog '{explorer_cat}'..."):
                    iceberg_catalog = load_catalog(
                        explorer_cat,
                        type="rest",
                        uri="http://localhost:8181/api/catalog",
                        warehouse=explorer_cat,
                        token=client.token,
                        **{
                            "header.X-Iceberg-Access-Delegation": "none",
                            "s3.endpoint": "http://localhost:9000",
                            "s3.access-key-id": "admin",
                            "s3.secret-access-key": "password",
                            "s3.path-style-access": "true",
                            "s3.region": "us-east-1",
                        }
                    )
                    
                    namespaces = iceberg_catalog.list_namespaces()
                    
                st.success(f"✅ Successfully authenticated and accessed '{explorer_cat}'!")
                st.session_state["explorer_namespaces"] = namespaces
                st.session_state["explorer_cat"] = explorer_cat
                st.session_state["iceberg_catalog"] = iceberg_catalog
            except Exception as e:
                st.error(f"❌ Failed to access catalog '{explorer_cat}'. Details: {e}")

    # If already connected to a catalog in this session, show the explorer UI
    if st.session_state.get("iceberg_catalog") and st.session_state.get("explorer_cat") == explorer_cat:
        iceberg_catalog = st.session_state["iceberg_catalog"]
        namespaces = st.session_state.get("explorer_namespaces", [])
        
        st.write("---")
        if not namespaces:
            st.info("No namespaces (schemas) found in this catalog.")
        else:
            ns_list = [".".join(n) for n in namespaces]
            selected_ns = st.selectbox("📂 Select Namespace", ns_list)
            
            if selected_ns:
                with st.spinner("Loading tables..."):
                    try:
                        tables = iceberg_catalog.list_tables(selected_ns)
                    except Exception as e:
                        st.error(f"Failed to list tables: {e}")
                        tables = []
                
                if not tables:
                    st.info("No tables found in this namespace.")
                else:
                    table_names = [t[1] if len(t) > 1 else t[0] for t in tables]
                    selected_table = st.selectbox("📄 Select Table", table_names)
                    
                    if selected_table:
                        st.subheader(f"Table: {selected_ns}.{selected_table}")
                        try:
                            table = iceberg_catalog.load_table(f"{selected_ns}.{selected_table}")
                            
                            col_schema, col_preview = st.columns([1, 1])
                            
                            with col_schema:
                                st.markdown("**Table Schema:**")
                                st.code(str(table.schema()), language="text")
                                
                            with col_preview:
                                st.markdown("**Data Preview:**")
                                if st.button("Load Top 10 Rows"):
                                    with st.spinner("Scanning table data..."):
                                        try:
                                            df = table.scan(limit=10).to_pandas()
                                            st.dataframe(df)
                                        except Exception as e:
                                            st.error(f"Error loading data: {e}")
                                            st.info("Ensure the S3 storage properties are correctly mapped for the internal container data.")
                        except Exception as e:
                            st.error(f"Failed to load table details: {e}")

