Auth schema/bootstrap
--------------------
Run these SQL statements to enable auth and audit fields:

1) Users table
CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

2) table_rows audit FKs
ALTER TABLE table_rows
  ALTER COLUMN created_by TYPE INTEGER USING created_by::integer,
  ALTER COLUMN updated_by TYPE INTEGER USING updated_by::integer;

ALTER TABLE table_rows
  ADD CONSTRAINT table_rows_created_by_fkey FOREIGN KEY (created_by) REFERENCES users(id),
  ADD CONSTRAINT table_rows_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES users(id);

3) Seed a first user (example)
INSERT INTO users (email, name, password_hash) VALUES ('admin@example.com', 'Admin', '$2b$12$changemehash');
Replace password_hash with an actual bcrypt hash (or call /auth/register after backend is running).

Env
----
Set AUTH_SECRET_KEY in .env for JWT signing (default is a weak dev value). Optionally override ACCESS_TOKEN_EXPIRE_MINUTES.

Tables schema for month switching
---------------------------------
ALTER TABLE tables ADD COLUMN IF NOT EXISTS period_start DATE;
ALTER TABLE tables ADD CONSTRAINT tables_template_period_unique UNIQUE (template_id, period_start);

-- Optional: add admin flag for create-month endpoint
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE;
