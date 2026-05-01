DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS prenotazioni;

CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  username VARCHAR(50) UNIQUE NOT NULL,
  password TEXT NOT NULL,
  admin INTEGER NOT NULL
);
CREATE TABLE prenotazioni (
  id SERIAL PRIMARY KEY,
  author_id INTEGER NOT NULL,
  n_parcheggio INTEGER NOT NULL,
  dalle_ore INTEGER NOT NULL,
  alle_ore INTEGER NOT NULL,
  giorno TIMESTAMP,
  creation_date TIMESTAMP,
  location VARCHAR(50),
  repeat VARCHAR(50),
  matricola VARCHAR(50),
  rfr INTEGER DEFAULT 0,
  note TEXT
);