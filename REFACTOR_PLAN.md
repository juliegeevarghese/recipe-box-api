# Refactor Plan

## 1. Responsibilities currently in app.py
- Creates the Flask app object
- Runs the development server
- Handles SQLite database access
- Defines authentication routes (POST /login, POST /register)
- Defines recipe routes (e.g. GET /recipes)
- Creates and verifies JWT tokens for authentication

**Total responsibilities:** 6


## 2. Acceptance list (current API behavior)

1) POST /register
   - curl:
     curl -i -X POST http://127.0.0.1:5000/register \
       -H "Content-Type: application/json" \
       -d '{"username": "testuser1", "email": "test1@example.com", "password": "test-pass-123"}'
   - expect:
     status: 201
     body: JSON with:
       - "id": <new user id, e.g. 5>
       - "username": "testuser1"
       - "email": "test1@example.com"

2) POST /login
   - curl:
     curl -i -X POST http://127.0.0.1:5000/login \
       -H "Content-Type: application/json" \
       -d '{"username": "testuser1", "password": "test-pass-123"}'
   - expect:
     status: 200
     body: JSON with:
       - "token": "<JWT string>"

3) POST /recipes (as julie)
   - curl:
     curl -i -X POST http://127.0.0.1:5000/recipes \
       -H "Content-Type: application/json" \
       -H "Authorization: Bearer JULIE_TOKEN_HERE" \
       -d '{"title": "Julie Recipe 1", "ingredients": "stuff", "instructions": "Do something", "is_public": 1}'
   - expect:
     status: 201
     body: JSON with:
       - "id" (some number)
       - "title": "Julie Recipe 1"

4) GET /recipes (as julie)
   - curl:
     curl -i -X GET http://127.0.0.1:5000/recipes \
       -H "Authorization: Bearer JULIE_TOKEN_HERE"
   - expect:
     status: 200
     body: JSON list that includes a recipe with:
       - "title": "Julie Recipe 1"

5) GET /recipes/<id> (as julie)
   - curl:
     curl -i -X GET http://127.0.0.1:5000/recipes/1 \
       -H "Authorization: Bearer JULIE_TOKEN_HERE"
   - expect:
     status: 200
     body: JSON with:
       - "id": 1
       - "title": "Julie Recipe 1"   (if recipe 1 is that one)

6) PATCH /recipes/<id> (as julie)
   - curl:
     curl -i -X PATCH http://127.0.0.1:5000/recipes/1 \
       -H "Content-Type: application/json" \
       -H "Authorization: Bearer JULIE_TOKEN_HERE" \
       -d '{"title": "Updated Julie Recipe 1"}'
   - expect:
     status: 200
     body: JSON with:
       - "id": 1
       - "title": "Updated Julie Recipe 1"

7) DELETE /recipes/<id> (as julie)
   - curl:
     curl -i -X DELETE http://127.0.0.1:5000/recipes/1 \
       -H "Authorization: Bearer JULIE_TOKEN_HERE"
   - expect:
     status: 204 or 200

# THE_TOKEN_FROM_LOGIN = the real token string you get when you run your login curl.

____________________________________________________
## NOTES: To run those curls with no error codes:
Use a valid token from /login for:
-admin / secret123 → admin can do all of them.
-or julie / secret123 → can fully manage recipes that julie created.
-or testuser1 / test-pass-123 → can fully manage recipes that testuser1 created.
# The safest for your acceptance list is:
-Log in as one user (e.g. testuser1),
-Use that one token for all your POST/GET/PATCH/DELETE recipe curls,
-Make sure the recipe id you PATCH/DELETE was created by that same user.
____________________________________________________

**Total acceptance items:** 7


## 3. Target package layout (planned)

```markdown
recipe_api/
  __init__.py          # will create the Flask app (factory) later
  config.py            # configuration classes (dev, test, prod)

  auth/
    __init__.py
    routes.py          # register, login routes
    services.py        # auth logic (create user, verify password)
    repository.py      # DB queries for users

  recipes/
    __init__.py
    routes.py          # recipe CRUD routes (list, create, update, delete)
    services.py        # recipe business logic
    repository.py      # DB queries for recipes

  db/
    __init__.py
    connection.py      # open DB connection, helpers

No middleware/ needed right now.
```

## 4.  Refactor boundary

- Public contract (must NOT change):
  - All endpoint paths (URLs) stay the same.
  - All HTTP methods (GET, POST, PATCH, DELETE) stay the same.
  - Request JSON fields stay the same.
  - Response JSON shape and status codes stay the same.
  - Auth rules (who can do what) stay the same.

- Internal structure (MAY change):
  - File and folder layout.
  - Which functions live in which module.
  - How the Flask app is created inside the package.
  - How routes call services and repositories.