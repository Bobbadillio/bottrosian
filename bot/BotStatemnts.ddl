CREATE TABLE authenticated_users
(
    discord_id VARCHAR(63) PRIMARY KEY,
    dojo_belt        VARCHAR(15),
    mod_awarded_belt VARCHAR(15)
);

CREATE TABLE chesscom_profiles
(
    username VARCHAR(255) PRIMARY KEY,
    discord_id VARCHAR(63) REFERENCES authenticated_users (discord_id),
    last_elo SMALLINT,
    previous_elo SMALLINT
);


CREATE TABLE lichess_profiles (
    username VARCHAR(255) PRIMARY KEY,
    discord_id VARCHAR(63) NOT NULL REFERENCES authenticated_users (discord_id),
    last_elo SMALLINT,
    previous_elo SMALLINT
);

select * from information_schema.tables;

