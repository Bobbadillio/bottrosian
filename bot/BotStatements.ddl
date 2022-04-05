CREATE TABLE authenticated_users
(
    discord_id VARCHAR(63) PRIMARY KEY,
    dojo_belt        BELT_T,
    mod_awarded_belt BELT_T
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


 SELECT
   table_name,
  column_name,
  data_type
 FROM
   information_schema.columns
 WHERE
  table_name = 'authenticated_users';

CREATE TYPE BELT_T AS ENUM('White', 'Yellow', 'Orange', 'Green', 'Blue', 'Purple', 'Brown', 'Red', 'Black');