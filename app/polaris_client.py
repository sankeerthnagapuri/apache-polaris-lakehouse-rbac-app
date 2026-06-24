import requests
import json
import urllib.parse
import base64

"""
Apache Polaris API Client

This module provides a Python wrapper around the Apache Polaris Management API.
It handles authentication and API requests for managing catalogs, principals,
principal roles, catalog roles, and grants.
"""

def decode_token(token):
    """
    Decodes a JWT token without verifying the signature.
    
    Args:
        token (str): The JWT string.
        
    Returns:
        dict: The decoded payload, or an empty dict if decoding fails.
    """
    if not token:
        return {}
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return {}
        payload_b64 = parts[1]
        # Add base64 padding if needed
        rem = len(payload_b64) % 4
        if rem > 0:
            payload_b64 += "=" * (4 - rem)
        decoded = base64.urlsafe_b64decode(payload_b64).decode("utf-8")
        return json.loads(decoded)
    except Exception:
        return {}

# ----------------------------------------------------
# 1. API CLIENT IMPLEMENTATION
# ----------------------------------------------------
class PolarisApiClient:
    """
    Client for interacting with the Apache Polaris Management REST API.
    """

    def __init__(self, base_url, token_url, client_id, client_secret, token=None):
        """
        Initialize the Polaris API Client.

        Args:
            base_url (str): The base URL for the Polaris Management API.
            token_url (str): The OAuth2 token URL for authentication.
            client_id (str): The Polaris client ID.
            client_secret (str): The Polaris client secret.
            token (str, optional): An existing access token to use.
        """
        self.base_url = base_url.rstrip('/')
        self.token_url = token_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = token
        if token:
            self.headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        else:
            self.headers = {}

    def authenticate(self):
        """
        Authenticate with the Polaris API using client credentials.
        
        Returns:
            tuple: (success (bool), message (str))
        """
        if self.token:
            return True, "Authenticated via pre-existing OIDC token"
        try:
            resp = requests.post(
                self.token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "scope": "PRINCIPAL_ROLE:ALL"
                },
                timeout=10
            )
            if resp.status_code == 200:
                self.token = resp.json().get("access_token")
                self.headers = {
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json"
                }
                return True, "Authenticated successfully"
            else:
                return False, f"Authentication failed: {resp.text}"
        except Exception as e:
            return False, f"Error authenticating: {str(e)}"

    def _request(self, method, path, **kwargs):
        if not self.token:
            return False, "Not authenticated. Please connect first."
        url = f"{self.base_url}{path}"
        try:
            resp = requests.request(method, url, headers=self.headers, timeout=15, **kwargs)
            if resp.status_code in [200, 201]:
                try:
                    return True, resp.json() if resp.text else None
                except Exception:
                    return True, None
            elif resp.status_code == 204:
                return True, None
            else:
                try:
                    err_msg = resp.json()
                except Exception:
                    err_msg = resp.text
                return False, f"Error {resp.status_code}: {err_msg}"
        except Exception as e:
            return False, f"Request failed: {str(e)}"

    # --- Catalogs ---
    def list_catalogs(self):
        return self._request("GET", "/catalogs")

    def create_catalog(self, catalog_data):
        return self._request("POST", "/catalogs", json={"catalog": catalog_data})

    def get_catalog(self, name):
        return self._request("GET", f"/catalogs/{urllib.parse.quote(name)}")

    def update_catalog(self, name, catalog_data):
        return self._request("PUT", f"/catalogs/{urllib.parse.quote(name)}", json=catalog_data)

    def delete_catalog(self, name):
        return self._request("DELETE", f"/catalogs/{urllib.parse.quote(name)}")

    # --- Principals ---
    def list_principals(self):
        return self._request("GET", "/principals")

    def create_principal(self, principal_data, credential_rotation_required=False):
        payload = {
            "principal": principal_data,
            "credentialRotationRequired": credential_rotation_required
        }
        return self._request("POST", "/principals", json=payload)

    def get_principal(self, name):
        return self._request("GET", f"/principals/{urllib.parse.quote(name)}")

    def update_principal(self, name, principal_data):
        return self._request("PUT", f"/principals/{urllib.parse.quote(name)}", json=principal_data)

    def delete_principal(self, name):
        return self._request("DELETE", f"/principals/{urllib.parse.quote(name)}")

    def rotate_credentials(self, name):
        return self._request("POST", f"/principals/{urllib.parse.quote(name)}/rotate")

    def reset_credentials(self, name, client_id=None, client_secret=None):
        payload = {}
        if client_id:
            payload["clientId"] = client_id
        if client_secret:
            payload["clientSecret"] = client_secret
        return self._request("POST", f"/principals/{urllib.parse.quote(name)}/reset", json=payload)

    # --- Principal Roles ---
    def list_principal_roles(self):
        return self._request("GET", "/principal-roles")

    def create_principal_role(self, role_data):
        return self._request("POST", "/principal-roles", json={"principalRole": role_data})

    def get_principal_role(self, name):
        return self._request("GET", f"/principal-roles/{urllib.parse.quote(name)}")

    def delete_principal_role(self, name):
        return self._request("DELETE", f"/principal-roles/{urllib.parse.quote(name)}")

    # --- Assignments (Principal <-> Principal Role) ---
    def list_roles_assigned_to_principal(self, principal_name):
        return self._request("GET", f"/principals/{urllib.parse.quote(principal_name)}/principal-roles")

    def assign_role_to_principal(self, principal_name, role_name):
        return self._request("PUT", f"/principals/{urllib.parse.quote(principal_name)}/principal-roles", json={"principalRole": {"name": role_name}})

    def revoke_role_from_principal(self, principal_name, role_name):
        return self._request("DELETE", f"/principals/{urllib.parse.quote(principal_name)}/principal-roles/{urllib.parse.quote(role_name)}")

    def list_principals_assigned_to_role(self, role_name):
        return self._request("GET", f"/principal-roles/{urllib.parse.quote(role_name)}/principals")

    # --- Catalog Roles ---
    def list_catalog_roles(self, catalog_name):
        return self._request("GET", f"/catalogs/{urllib.parse.quote(catalog_name)}/catalog-roles")

    def create_catalog_role(self, catalog_name, role_data):
        return self._request("POST", f"/catalogs/{urllib.parse.quote(catalog_name)}/catalog-roles", json={"catalogRole": role_data})

    def get_catalog_role(self, catalog_name, role_name):
        return self._request("GET", f"/catalogs/{urllib.parse.quote(catalog_name)}/catalog-roles/{urllib.parse.quote(role_name)}")

    def delete_catalog_role(self, catalog_name, role_name):
        return self._request("DELETE", f"/catalogs/{urllib.parse.quote(catalog_name)}/catalog-roles/{urllib.parse.quote(role_name)}")

    # --- Assignments (Principal Role <-> Catalog Role) ---
    def list_catalog_roles_for_principal_role(self, principal_role_name, catalog_name):
        return self._request("GET", f"/principal-roles/{urllib.parse.quote(principal_role_name)}/catalog-roles/{urllib.parse.quote(catalog_name)}")

    def assign_catalog_role_to_principal_role(self, principal_role_name, catalog_name, catalog_role_name):
        return self._request("PUT", f"/principal-roles/{urllib.parse.quote(principal_role_name)}/catalog-roles/{urllib.parse.quote(catalog_name)}", json={"catalogRole": {"name": catalog_role_name}})

    def revoke_catalog_role_from_principal_role(self, principal_role_name, catalog_name, catalog_role_name):
        return self._request("DELETE", f"/principal-roles/{urllib.parse.quote(principal_role_name)}/catalog-roles/{urllib.parse.quote(catalog_name)}/{urllib.parse.quote(catalog_role_name)}")

    def list_principal_roles_for_catalog_role(self, catalog_name, catalog_role_name):
        return self._request("GET", f"/catalogs/{urllib.parse.quote(catalog_name)}/catalog-roles/{urllib.parse.quote(catalog_role_name)}/principal-roles")

    # --- Grants ---
    def list_grants_for_catalog_role(self, catalog_name, catalog_role_name):
        return self._request("GET", f"/catalogs/{urllib.parse.quote(catalog_name)}/catalog-roles/{urllib.parse.quote(catalog_role_name)}/grants")

    def add_grant_to_catalog_role(self, catalog_name, catalog_role_name, grant_data):
        return self._request("PUT", f"/catalogs/{urllib.parse.quote(catalog_name)}/catalog-roles/{urllib.parse.quote(catalog_role_name)}/grants", json={"grant": grant_data})

    def revoke_grant_from_catalog_role(self, catalog_name, catalog_role_name, grant_data, cascade=False):
        path = f"/catalogs/{urllib.parse.quote(catalog_name)}/catalog-roles/{urllib.parse.quote(catalog_role_name)}/grants"
        if cascade:
            path += "?cascade=true"
        return self._request("POST", path, json={"grant": grant_data})

