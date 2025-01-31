CREATE TYPE BELT_T AS ENUM('White', 'Yellow', 'Orange', 'Green', 'Blue', 'Purple', 'Brown', 'Red', 'Black');

CREATE TABLE authenticated_users
(
    discord_id VARCHAR(63) PRIMARY KEY
);

CREATE TABLE mod_profiles (
    discord_id VARCHAR(63) UNIQUE NOT NULL REFERENCES authenticated_users (discord_id) ON DELETE CASCADE,
    awarded_belt BELT_T
);

CREATE TABLE chesscom_profiles
(
    chesscom_username VARCHAR(255) PRIMARY KEY,
    discord_id VARCHAR(63) UNIQUE NOT NULL REFERENCES authenticated_users (discord_id) ON DELETE CASCADE,
    last_chesscom_elo SMALLINT,
    previous_chesscom_elo SMALLINT,
    chesscom_belt BELT_T
);

CREATE TABLE lichess_profiles (
    lichess_username VARCHAR(255) PRIMARY KEY,
    discord_id VARCHAR(63) UNIQUE NOT NULL REFERENCES authenticated_users (discord_id) ON DELETE CASCADE,
    last_lichess_elo SMALLINT,
    previous_lichess_elo SMALLINT,
    lichess_belt BELT_T
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

SELECT discord_id AS discord, GREATEST(awarded_belt, chesscom_belt, lichess_belt) AS belt,
    chesscom_username, last_chesscom_elo AS chesscom_elo, lichess_username, last_lichess_elo,
       chesscom_username, lichess_username

        AS lichess_elo FROM authenticated_users
    NATURAL LEFT JOIN chesscom_profiles
    NATURAL LEFT JOIN lichess_profiles
    NATURAL LEFT JOIN mod_profiles;