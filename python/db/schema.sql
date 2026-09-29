-- FlavorLens schema — v2 (multi-city: Bangalore, New Delhi, Gurgaon, Noida)
--
-- KEY CHANGE FROM v1: added a `city` column. This matters because locality
-- names are NOT globally unique — "Sector 15" exists in Noida, Gurgaon, and
-- Faridabad; "MG Road" exists in a dozen Indian cities. Without a city
-- dimension, combining multiple cities' data would silently merge unrelated
-- localities into one fake combined entity, corrupting every COI number
-- for that locality. City + locality together form the real geographic key.

CREATE TABLE IF NOT EXISTS restaurants (
    restaurant_id       SERIAL PRIMARY KEY,
    name                TEXT NOT NULL,
    address             TEXT,
    city                TEXT NOT NULL,       -- e.g. "Bangalore", "New Delhi", "Gurgaon", "Noida"
    location            TEXT,                -- locality within the city, e.g. "Indiranagar", "Sector 62"
    rest_type           TEXT,                -- NULL for cities sourced from the global JSON dataset,
                                              -- which doesn't include this field — disclosed, not faked
    approx_cost_for_two NUMERIC,
    rating              NUMERIC,
    votes               INTEGER,
    online_order        BOOLEAN,
    book_table          BOOLEAN
);

CREATE TABLE IF NOT EXISTS restaurant_cuisines (
    restaurant_id INTEGER REFERENCES restaurants(restaurant_id),
    cuisine       TEXT NOT NULL,
    PRIMARY KEY (restaurant_id, cuisine)
);

-- Composite index: nearly every query filters/groups by (city, location)
-- together, not location alone.
CREATE INDEX IF NOT EXISTS idx_restaurants_city_location ON restaurants(city, location);
CREATE INDEX IF NOT EXISTS idx_restaurant_cuisines_cuisine ON restaurant_cuisines(cuisine);