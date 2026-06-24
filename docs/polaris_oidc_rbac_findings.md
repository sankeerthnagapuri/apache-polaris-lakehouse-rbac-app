# Apache Polaris 1.5.0 OIDC & RBAC Findings

This document summarizes the discoveries made while integrating Keycloak OIDC with Apache Polaris 1.5.0, specifically focusing on Role-Based Access Control (RBAC), token mapping, and federated roles.

## 1. The Intersection Model

Polaris does **not** dynamically provision roles or grants solely based on the claims in an external JWT token. Instead, it uses an **Intersection Model** (also known as session scoping).

The effective roles activated for a user session are defined by:
`Activated Roles = (Roles assigned to the user in Polaris DB) ∩ (Roles requested in the Keycloak Token)`

* **Polaris Database:** Dictates what the user is *allowed* to do. The user, the principal role, and the assignment must exist in Polaris.
* **Keycloak Token:** Acts as a *filter* to dictate what subset of allowed roles the user is requesting for the current session (Least Privilege).

## 2. The "Invalid Token" Fallback Loophole

A critical behavior was observed in the Polaris `DefaultAuthenticator`:

If the Keycloak token provides no valid roles (either because the `groups` claim is missing, or the groups provided do not match any existing roles in the Polaris database), Polaris **bypasses the intersection entirely**.

When the token provides zero valid roles, the authenticator assumes the session is unscoped. As a fallback, it automatically activates **all** of the user's default database role assignments. 

**Why this matters:**
If your OIDC mapper configuration is broken (e.g., prefixing roles with `PRINCIPAL_ROLE:` when the DB doesn't use that prefix), the token's roles are treated as invalid. Polaris will silently fallback to activating all DB roles, making it *appear* as though OIDC mapping is working or being ignored. When the configuration is fixed, the intersection begins working, and the session is strictly scoped.

## 3. The `polaris.oidc.principal-roles-mapper` Configuration

The official documentation provides an example configuration using a replacement string:
```properties
polaris.oidc.principal-roles-mapper.mappings[0].replacement=PRINCIPAL_ROLE:$0
```

**Finding:** This prefix breaks the intersection. Unless you actually name your roles `PRINCIPAL_ROLE:polaris_warehouse_analyst` in the Polaris database, this prefix will cause the token roles to not match the DB roles. 

**The Fix:** Use a straight pass-through:
```properties
polaris.oidc.principal-roles-mapper.mappings[0].replacement=$0
```

## 4. "Federated" Principal Roles

The Polaris API and UI allow you to create Principal Roles with a `federated` flag set to `true`.

**Finding:** True federated identity (where roles do not need to exist in the Polaris database at all) is **not supported** in Polaris 1.5.0. 

* The `DefaultAuthenticator` source code explicitly states: *"For now, it does not support federated principals that are not managed by Polaris."*
* The API actively prevents you from manually assigning a principal to a federated role.
* Because the intersection model requires DB assignment, and the API blocks DB assignment for federated roles, it is impossible to activate a federated role.

**Conclusion:** Use standard (non-federated) Principal Roles for now. "Detached principals" are planned for a future Apache Polaris release.

## 5. Keycloak Setup Requirements

To successfully pass roles to Polaris, Keycloak must be explicitly configured to inject group memberships into the JWT.

1. A "Protocol Mapper" (OIDC Group Membership Mapper) must be added to the Keycloak Client.
2. `Full group path` should be disabled so it passes `polaris_warehouse_analyst` instead of `/polaris_warehouse_analyst`.
3. The token claim name should match the `quarkus.oidc.roles.role-claim-path` in `application.properties` (e.g., `groups`).
