# Recipe API – End-to-End Security Audit

## 1. Password storage

- Table: `users`
- Column: `password_hash`
- Example value from the DB:  
  `scrypt:32768:8:1$5kpKhdF25LhCcygC$306787d73f519f278620bfd282426b893ceb83111c63b15cc4959a9c083dca8056000359b735789711fa2167642bf6eae82d412404eae44fd4ebfed0f02adaaa`
- Conclusion: Passwords are stored as **scrypt hashes**, not plaintext. ✅


## 2. Authentication – POST /recipes

Tests run with `http://localhost:5000/recipes`:

| Request type | Expected | Actual | Notes |
|-------------|----------|--------|-------|
| No token    | 401      | **401 UNAUTHORIZED** | Response: `{"error": "Missing or invalid Authorization header"}` – identity required before creating recipes ✅ |
| Valid token (user `julie`) | 2xx/4xx | **400 / 409** | Auth passed; app only returned validation errors (`"title and ingredients are required"`) or uniqueness error (`"a recipe with that title already exists"`). No 401/403 once token is valid. ✅ |


## 3. Ownership & admin-or-owner – DELETE /recipes/<id>

Relevant code (from `app.py`):

- Both `PATCH /recipes/<int:recipe_id>` and `DELETE /recipes/<int:recipe_id>`:
  - Use `@token_required` middleware for JWT authentication.
  - Load the recipe from the DB first.
  - Compute:

    - `is_owner = str(row["owner_id"]) == request.user["id"]`
    - `is_admin = request.user.get("role") == "admin"`

  - If **not** owner and **not** admin:

    - Return `403` with `{"error": "forbidden: not your recipe"}`

### Tests

Recipes created and deleted via real requests:

| Route               | User    | Action                                  | Expected        | Actual                          | Notes |
|--------------------|---------|-----------------------------------------|-----------------|---------------------------------|-------|
| DELETE /recipes/3  | owner1 | Delete own recipe (first delete)        | 204             | **204 NO CONTENT**             | Owner can delete own recipe ✅ |
| DELETE /recipes/3  | owner1 | Delete same recipe again                 | 404             | **404 NOT FOUND** (`"recipe not found"`) | Already deleted – correct behavior ✅ |
| DELETE /recipes/3  | julie  | Delete recipe owned by `owner1`          | 403 or 404      | **403 FORBIDDEN** (`"forbidden: not your recipe"`) | Cross-user delete correctly blocked ✅ |

Conclusion: ownership checks and admin-or-owner logic are enforced on delete and (by code structure) on update.


## 4. Middleware usage

- JWT authentication is **centralized** in `@token_required`.
- `@token_required` is applied to protected routes such as:
  - `PATCH /recipes/<int:recipe_id>`
  - `DELETE /recipes/<int:recipe_id>`
  - (and other write routes like `POST /recipes` in the app)
- Authorization (owner/admin check) happens immediately after loading the recipe and **before** performing any update/delete.


## 5. Old exploit re-tests

The following earlier attack ideas were re-run against the final API:

- Anonymous create recipe (`POST /recipes` without Authorization header)  
  - Result: **401 UNAUTHORIZED** with `"Missing or invalid Authorization header"` → blocked ✅
- Anonymous delete recipe (DELETE without token)  
  - Result: 401 UNAUTHORIZED (enforced by `@token_required`) → blocked ✅
- Cross-user delete (non-owner)  
  - Result: **403 FORBIDDEN** with `"forbidden: not your recipe"` → blocked ✅
- Cross-user update (non-owner)  
  - By design, would hit the same admin-or-owner check and return `403 FORBIDDEN` when user is not owner or admin.

**Overall conclusion:**  
The API stores passwords securely (hashed), requires valid JWT identity for protected writes, and enforces ownership/admin checks on recipe modification. Previous exploits (anonymous writes, cross-user modifications) are now blocked with appropriate `401`, `403`, or `404` responses.