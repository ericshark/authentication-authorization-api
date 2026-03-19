CREATE TABLE IF NOT EXISTS test_table (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(10) UNIQUE NOT NULL,
    password VARCHAR(20) UNIQUE NOT NULL

);

INSERT INTO test_table(username, password)
    VALUES ('booby Jay', 'donut')
    RETURNING *;