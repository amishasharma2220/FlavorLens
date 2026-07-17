-- FlavorLens schema — v1 (Bangalore, by locality)
-- Two tables: one row per unique restaurant, one row per (restaurant, cuisine) pair.
-- Cuisines are split out rather than stored as a comma-separated string so that
-- SQL can actually GROUP BY cuisine correctly.

CREATE TABLE IF NOT EXISTS restaurants (
    restaurant_id       SERIAL PRIMARY KEY,
    name                TEXT NOT NULL,
    address             TEXT,
    location            TEXT,               -- locality, e.g. "BTM", "Indiranagar"
    rest_type           TEXT,
    approx_cost_for_two NUMERIC,
    rating              NUMERIC,             -- parsed from "4.1/5" -> 4.1; NULL if unrated/"NEW"
    votes               INTEGER,
    online_order        BOOLEAN,
    book_table          BOOLEAN
);

CREATE TABLE IF NOT EXISTS restaurant_cuisines (
    restaurant_id INTEGER REFERENCES restaurants(restaurant_id),
    cuisine       TEXT NOT NULL,
    PRIMARY KEY (restaurant_id, cuisine)
);

CREATE INDEX IF NOT EXISTS idx_restaurants_location ON restaurants(location);
CREATE INDEX IF NOT EXISTS idx_restaurant_cuisines_cuisine ON restaurant_cuisines(cuisine);