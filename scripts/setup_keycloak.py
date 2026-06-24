import requests
import time
import os
from dotenv import load_dotenv

load_dotenv()

def setup_keycloak():
    print("Authenticating with Keycloak admin...")
    token_url = "http://localhost:8080/realms/master/protocol/openid-connect/token"
    token_resp = requests.post(token_url, data={
        "client_id": "admin-cli",
        "username": os.environ.get("KEYCLOAK_ADMIN_USER", "admin"),
        "password": os.environ.get("KEYCLOAK_ADMIN_PASSWORD", "password"),
        "grant_type": "password"
    }).json()
    
    if "access_token" not in token_resp:
        print("Failed to authenticate with Keycloak. Is it running?")
        print(token_resp)
        return
        
    token = token_resp["access_token"]
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # Create realm
    print("Creating polaris-realm...")
    resp = requests.post("http://localhost:8080/admin/realms", headers=headers, json={
        "realm": "polaris-realm",
        "enabled": True
    })
    if resp.status_code == 201:
        print("Realm created.")
    elif resp.status_code == 409:
        print("Realm already exists.")
    else:
        print(f"Error creating realm: {resp.text}")
    
    # Create client
    print("Creating polaris-client...")
    resp = requests.post("http://localhost:8080/admin/realms/polaris-realm/clients", headers=headers, json={
        "clientId": "polaris-client",
        "enabled": True,
        "publicClient": False,
        "directAccessGrantsEnabled": True,
        "serviceAccountsEnabled": True,
        "secret": os.environ.get("KEYCLOAK_CLIENT_SECRET", "sBbUvTG7qWGbmgwgxKmnEuzqpuE3uGAu"),
        "redirectUris": [
            "http://localhost:8501/",
            "http://localhost:8502/",
            "https://oauth.pstmn.io/v1/callback"
        ],
        "protocolMappers": [
            {
                "name": "groups-mapper",
                "protocol": "openid-connect",
                "protocolMapper": "oidc-group-membership-mapper",
                "consentRequired": False,
                "config": {
                    "full.path": "false",
                    "id.token.claim": "true",
                    "access.token.claim": "true",
                    "claim.name": "groups",
                    "userinfo.token.claim": "true"
                }
            }
        ]
    })
    if resp.status_code == 201:
        print("Client created.")
    elif resp.status_code == 409:
        print("Client already exists.")
    else:
        print(f"Error creating client: {resp.text}")
    
    # Create group
    print("Creating group polaris_warehouse_analyst...")
    resp = requests.post("http://localhost:8080/admin/realms/polaris-realm/groups", headers=headers, json={
        "name": "polaris_warehouse_analyst"
    })
    if resp.status_code == 201:
        print("Group created.")
    elif resp.status_code == 409:
        print("Group already exists.")
    else:
        print(f"Error creating group: {resp.text}")

    # Get group ID
    resp = requests.get("http://localhost:8080/admin/realms/polaris-realm/groups?search=polaris_warehouse_analyst", headers=headers)
    group_id = resp.json()[0]["id"]
    
    # Create user
    user_name = os.environ.get("POLARIS_USER_NAME", "sankeerth")
    user_pass = os.environ.get("POLARIS_USER_PASSWORD", "nagapuri")
    
    print(f"Creating user {user_name}...")
    resp = requests.post("http://localhost:8080/admin/realms/polaris-realm/users", headers=headers, json={
        "username": user_name,
        "enabled": True,
        "firstName": "Sankeerth",
        "lastName": "User",
        "email": f"{user_name}@example.com",
        "emailVerified": True,
        "requiredActions": [],
        "credentials": [{"type": "password", "value": user_pass, "temporary": False}]
    })
    if resp.status_code == 201:
        print("User created.")
    elif resp.status_code == 409:
        print("User already exists.")
    else:
        print(f"Error creating user: {resp.text}")

    # Get user ID
    resp = requests.get(f"http://localhost:8080/admin/realms/polaris-realm/users?username={user_name}", headers=headers)
    user_id = resp.json()[0]["id"]

    # Assign user to group
    print("Assigning user to group...")
    resp = requests.put(f"http://localhost:8080/admin/realms/polaris-realm/users/{user_id}/groups/{group_id}", headers=headers)
    if resp.status_code == 204:
        print("User assigned to group.")
    else:
        print(f"Error assigning user to group: {resp.text}")

if __name__ == "__main__":
    setup_keycloak()
    print("Keycloak setup complete!")
