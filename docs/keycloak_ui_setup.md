# Keycloak Manual UI Setup Guide

If you are not using the automated `setup_keycloak.py` script, you must manually configure Keycloak via its Admin Console UI. 

Below are the exact steps required to replicate the automated setup, specifically focusing on the "Group Mapper" that injects role names into the JWT token.

## 1. Create the Realm
1. Log in to the Keycloak Admin Console (e.g., `http://localhost:8080/admin`).
2. Click the Realm dropdown in the top left and select **Create Realm**.
3. Set the **Realm name** to `polaris-realm`.
4. Click **Create**.

## 2. Create the Client
1. Ensure you are in the `polaris-realm`.
2. Go to **Clients** in the left menu and click **Create client**.
3. Set **Client ID** to `polaris-client` and click Next.
4. Enable **Client authentication** (this makes it a confidential client instead of public).
5. Enable **Direct access grants** and **Service accounts roles**.
6. Click **Save**.
7. Go to the **Credentials** tab of your new client and copy the **Client Secret**.
8. Go to the **Settings** tab and add your **Valid redirect URIs** (e.g., `http://localhost:8501/*`).

## 3. Configure the Group Mapper
By default, Keycloak does *not* include a user's groups in their JWT token. You must add a protocol mapper to explicitly inject them.

1. Go to **Clients** -> `polaris-client`.
2. Click on the **Client Scopes** tab.
3. Click on the `<client-id>-dedicated` scope (e.g., `polaris-client-dedicated`).
4. Click **Add mapper** -> **By configuration**.
5. Select **Group Membership** from the list.
6. Configure the mapper exactly as follows:
   - **Name:** `groups-mapper` (or any descriptive name)
   - **Token Claim Name:** `groups` *(This must exactly match `quarkus.oidc.roles.role-claim-path` in your Polaris properties)*
   - **Full group path:** Turn this **OFF**. *(If left ON, it will output `/polaris_warehouse_analyst` instead of `polaris_warehouse_analyst`)*
   - **Add to ID token:** ON
   - **Add to access token:** ON
   - **Add to userinfo:** ON
7. Click **Save**.

## 4. Create the Group
1. Go to **Groups** in the left menu.
2. Click **Create group**.
3. Name it `polaris_warehouse_analyst` (or whichever Principal Role you are mapping).
4. Click **Create**.

## 5. Create the User and Assign Group
1. Go to **Users** in the left menu.
2. Click **Add user**.
3. Set **Username** to `sankeerth` (and fill out email/name). Click **Create**.
4. Go to the **Credentials** tab for the user, click **Set password**, enter the password, and turn **Temporary** OFF. Click Save.
5. Go to the **Groups** tab for the user.
6. Click **Join Group**.
7. Select `polaris_warehouse_analyst` and click **Join**.

---

### Verification
If configured correctly, the JWT payload generated for the user will now include:
```json
"groups": [
  "polaris_warehouse_analyst"
]

```
_you can run `test_lakehouse.py` script which prints the JWT payload_

Polaris will intercept this `groups` array and use it to intersect against the user's assigned roles in the Polaris database.
