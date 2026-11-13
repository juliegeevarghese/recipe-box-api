"""Create and seed recipes.db. Run once after cloning: python init_db.py"""

import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS recipes (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL UNIQUE,
    ingredients TEXT NOT NULL,
    instructions TEXT NOT NULL DEFAULT '',
    is_public INTEGER NOT NULL DEFAULT 1,
    owner_id INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user'
);
"""

SEED = [
    (
        "Shakshuka",
        "eggs, tomatoes, peppers, onion, cumin, paprika",
        "Simmer the sauce, crack in the eggs, cover until just set.",
        1,
        1, # owner_id for the seeded recipes
    ),
    (
        "Overnight oats",
        "rolled oats, milk, yogurt, chia seeds, honey",
        "Stir everything together and refrigerate overnight.",
        1,
        1, # owner_id for the seeded recipes
    ),
    (
        "Secret family hot sauce",
        "habaneros, garlic, vinegar, a secret ingredient",
        "If we wrote it down here, it wouldn't be a secret.",
        0,
        1, # owner_id for the seeded recipes
    ),
]

connection = sqlite3.connect("recipes.db")
connection.executescript(SCHEMA)

# insert admin user
connection.execute(
    "INSERT OR IGNORE INTO users (id, username, email, password_hash, role) "
    "VALUES (?, ?, ?, ?, ?)",
    (
        1,
        "admin",
        "admin@example.com",
        "scrypt:32768:8:1$9AorjlWBnWigappN$5d39b20fee21eeb719be08dedfb2c2170527964cb3f1407ba7c76f183a86c262dcf7cc3248343c3a906b1f27233a77ecca6adb6e67494e3c7b3df4de44967c04",
        "admin",
    ),
)

# normal user with role 'user'
connection.execute(
    "INSERT OR IGNORE INTO users (username, email, password_hash, role) "
    "VALUES (?, ?, ?, ?)",
    (
        "julie",
        "julie@example.com",
        # hash for password "secret123"
        "scrypt:32768:8:1$5kpKhdF25LhCcygC$306787d73f519f278620bfd282426b893ceb83111c63b15cc4959a9c083dca8056000359b735789711fa2167642bf6eae82d412404eae44fd4ebfed0f02adaaa",
        "user",
    ),
)

existing = connection.execute("SELECT COUNT(*) FROM recipes").fetchone()[0]
if existing == 0:
    connection.executemany(
        "INSERT INTO recipes (title, ingredients, instructions, is_public, owner_id)"
        " VALUES (?, ?, ?, ?, ?)",
        SEED,
    )
    connection.commit()
    print(f"Created recipes.db and seeded {len(SEED)} recipes.")
else:
    print(f"recipes.db already has {existing} recipes - nothing to do.")
connection.close() 