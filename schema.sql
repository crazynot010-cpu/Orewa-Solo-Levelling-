CREATE TABLE IF NOT EXISTS hunters (
    user_id BIGINT PRIMARY KEY,
    rank TEXT DEFAULT 'E',
    level INT DEFAULT 0,
    xp INT DEFAULT 0,
    str INT DEFAULT 5,
    agi INT DEFAULT 5,
    int_stat INT DEFAULT 5,
    vit INT DEFAULT 5,
    gold INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS shadows (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE,
    drop_rate INT,
    catch_rate INT,
    health INT,
    damage INT,
    rarity TEXT,
    image_url TEXT
);

CREATE TABLE IF NOT EXISTS hunter_shadows (
    id SERIAL PRIMARY KEY,
    user_id BIGINT,
    shadow_id INT REFERENCES shadows(id),
    level INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS guild_settings (
    guild_id BIGINT PRIMARY KEY,
    spawn_channel_id BIGINT,
    ping_role_id BIGINT,
    message_counter INT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS active_spawns (
    guild_id BIGINT PRIMARY KEY,
    shadow_id INT,
    claimed_by BIGINT,
    spawned_at TIMESTAMP DEFAULT NOW()
);
