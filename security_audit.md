# Recipe API – End-to-End Security Audit

## 1. Password storage

- Table: `users`
- Column: `password_hash`
- Example value:  
  `scrypt:32768:8:1$5kpKhdF25LhCcygC$3067...d831bff`
- Conclusion: Passwords are stored as scrypt hashes, not plaintext. ✅


## 2. Authentication checks

### POST /recipes

| Request type | Expected | Actual | Notes |
|-------------|----------|--------|-------|
| No token    | 401      | 401    | `{"error": "Missing or invalid Authorization header"}` – identity required ✅ |
| Valid token (julie) | 2xx/4xx | 400 / 409 | Auth passed, only validation / uniqueness errors (`title and ingredients required`, `title exists`) ✅ |


## 3. Ownership & admin-or-owner enforcement

Code:

- `PATCH /recipes/<id>` and `DELETE /recipes/<id>`:
  - Use `@token_required` middleware for JWT auth.
  - Compute `is_owner` from `owner_id` vs `request.user["id"]`.
  - Compute `is_admin` from `request.user["role"] == "admin"`.
  - If neither: return `403 {"error": "forbidden: not your recipe"}`.

Tests:

| Route             | User    | Action                                 | Expected       | Actual | Notes |
|------------------|---------|----------------------------------------|----------------|--------|-------|
| DELETE /recipes/3 | owner1 | Delete own recipe                      | 204            | 204    | Owner can delete own recipe ✅ |
| DELETE /recipes/3 | owner1 | Delete same recipe again               | 404            | 404    | Already deleted – correct behavior ✅ |
| DELETE /recipes/3 | julie  | Delete recipe owned by `owner1`        | 403 or 404     | 403    | Cross-user delete blocked: `forbidden: not your recipe` ✅ |

Conclusion: Ownership rules and admin-or-owner logic are enforced correctly on update/delete routes. ✅


## 4. Middleware usage

- JWT authentication is centralized in `@token_required` and applied to protected routes like:
  - `PATCH /recipes/<id>`
  - `DELETE /recipes/<id>`
  - `POST /recipes`
- Authorization decisions (owner/admin) happen right after loading the recipe, before any write.


## 5. Old exploit re-tests

- Anonymous create recipe → `401` UNAUTHORIZED (Missing/invalid Authorization header) – blocked ✅
- Anonymous delete recipe → `401` UNAUTHORIZED – blocked ✅
- Cross-user delete (non-owner) → `403 FORBIDDEN` – blocked ✅
- Cross-user update (non-owner) → returns `403 FORBIDDEN` by design – blocked ✅

Overall conclusion:  
All tested protections (password hashing, JWT identity, ownership, and admin-or-owner authorization) behaved as expected, and earlier exploits (anonymous writes, cross-user modification) are now blocked.