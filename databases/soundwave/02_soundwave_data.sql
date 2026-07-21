-- ============================================================
--  SOUNDWAVE DB  |  Data Population
--  NL2SQL Test Database for IDI Project
--  Universidad Nacional de Colombia  |  2026
-- ============================================================
--
--  Run AFTER: 01_soundwave_schema.sql
--
--  Insert order respects the FK dependency graph:
--    subscription_plans -> pricing_history
--    genres (roots first, then children)
--    artists -> albums -> tracks
--    users (organic batch first, referred batch second)
--    playlists (originals first, forks second)
--    bridge tables: track_artists, artist_genres, track_genres,
--                   playlist_tracks, user_follows_artists, user_liked_tracks
--    subscriptions -> subscription_periods -> payments
--    play_events
--    daily_artist_metrics
--
-- ============================================================

USE soundwave_db;
SET FOREIGN_KEY_CHECKS = 0;


-- ============================================================
--  1. subscription_plans
--  EC-02: plan_type is an integer code, not a display string.
--         1=free, 2=student, 3=individual, 4=family
-- ============================================================
INSERT INTO subscription_plans
    (plan_id, name, plan_type, monthly_price, max_devices, has_downloads, has_hifi)
VALUES
    (1, 'Free',       1,  0.00, 1, 0, 0),
    (2, 'Student',    2,  5.49, 1, 1, 0),
    (3, 'Individual', 3,  9.99, 1, 1, 1),
    (4, 'Family',     4, 15.99, 6, 1, 1);


-- ============================================================
--  2. pricing_history
--  EC-06: effective_to IS NULL = currently active price.
--  Prices were raised in 2024 for all paid plans.
--  Temporal queries must use date-overlap logic.
-- ============================================================
INSERT INTO pricing_history
    (plan_id, monthly_price, effective_from, effective_to, changed_reason)
VALUES
    -- Free plan: always 0
    (1,  0.00, '2022-01-01', NULL,         'Launch price'),
    -- Student plan: raised Jan 2024
    (2,  4.99, '2022-01-01', '2023-12-31', 'Launch price'),
    (2,  5.49, '2024-01-01', NULL,         'Annual increase'),
    -- Individual plan: raised twice
    (3,  8.99, '2022-01-01', '2022-12-31', 'Launch price'),
    (3,  9.49, '2023-01-01', '2023-12-31', 'Inflation adjustment'),
    (3,  9.99, '2024-01-01', NULL,         'Annual increase'),
    -- Family plan: raised Jan 2024
    (4, 14.99, '2022-01-01', '2023-12-31', 'Launch price'),
    (4, 15.99, '2024-01-01', NULL,         'Annual increase');


-- ============================================================
--  3. genres
--  EC-04: parent_genre_id IS NULL = root genre (self-referential).
--  EC-01: 'name' column also in artists, users, subscription_plans.
--  Root genres inserted first to satisfy the self-ref FK.
-- ============================================================

-- Root genres (parent_genre_id = NULL)
INSERT INTO genres (genre_id, name, parent_genre_id) VALUES
    (1,  'Pop',        NULL),
    (2,  'Rock',       NULL),
    (3,  'Hip-Hop',    NULL),
    (4,  'Latin',      NULL),
    (5,  'R&B',        NULL),
    (6,  'Electronic', NULL),
    (7,  'Jazz',       NULL),
    (8,  'Classical',  NULL);

-- Sub-genres (parent_genre_id set)
INSERT INTO genres (genre_id, name, parent_genre_id) VALUES
    ( 9, 'K-Pop',       1),   -- Pop  -> K-Pop
    (10, 'Indie Pop',   1),   -- Pop  -> Indie Pop
    (11, 'Indie Rock',  2),   -- Rock -> Indie Rock
    (12, 'Alternative', 2),   -- Rock -> Alternative
    (13, 'Trap',        3),   -- Hip-Hop -> Trap
    (14, 'Drill',       3),   -- Hip-Hop -> Drill
    (15, 'Reggaeton',   4),   -- Latin -> Reggaeton
    (16, 'Salsa',       4),   -- Latin -> Salsa
    (17, 'Neo Soul',    5),   -- R&B  -> Neo Soul
    (18, 'House',       6);   -- Electronic -> House


-- ============================================================
--  4. artists
--  EC-01: 'name' also in users/genres/plans; 'country' also in users.
--  EC-07: monthly_listeners_cached is seeded at production scale (tens of
--         millions) while play_events is a ~1,000-row sample, so it exceeds
--         the raw distinct-listener count by 2.4M x - 9.1M x. The "~5%" this
--         line claimed until 2026-07-21 was the intent, never the output.
-- ============================================================
INSERT INTO artists
    (artist_id, name, country, verified, monthly_listeners_cached, debut_year, label)
VALUES
    ( 1, 'The Weeknd',     'CA', 1, 112000000, 2011, 'Republic Records'),
    ( 2, 'Taylor Swift',   'US', 1, 100000000, 2006, 'Republic Records'),
    ( 3, 'Bad Bunny',      'PR', 1,  95000000, 2016, 'Rimas Entertainment'),
    ( 4, 'Drake',          'CA', 1,  88000000, 2006, 'Young Money / Cash Money'),
    ( 5, 'Billie Eilish',  'US', 1,  78000000, 2015, 'Interscope Records'),
    ( 6, 'Kendrick Lamar', 'US', 1,  72000000, 2003, 'PGLang / Interscope'),
    ( 7, 'Dua Lipa',       'GB', 1,  85000000, 2014, 'Warner Records'),
    ( 8, 'BTS',            'KR', 1,  68000000, 2013, 'HYBE Labels'),
    ( 9, 'Ed Sheeran',     'GB', 1,  91000000, 2004, 'Asylum Records'),
    (10, 'Olivia Rodrigo', 'US', 1,  71000000, 2019, 'Geffen Records'),
    (11, 'Arctic Monkeys', 'GB', 1,  45000000, 2002, 'Domino Records'),
    (12, 'Karol G',        'CO', 1,  81000000, 2010, 'Universal Music Latino');


-- ============================================================
--  5. albums
--  EC-01: 'title' also in tracks; 'release_date' also in tracks.
-- ============================================================
INSERT INTO albums
    (album_id, title, artist_id, release_date, album_type, label, total_tracks)
VALUES
    ( 1, 'After Hours',                   1,  '2020-03-20', 'album', 'Republic Records',       14),
    ( 2, 'Dawn FM',                        2,  '2022-01-07', 'album', 'Republic Records',       16),
    ( 3, 'Midnights',                      2,  '2022-10-21', 'album', 'Republic Records',       13),
    ( 4, 'Folklore',                       2,  '2020-07-24', 'album', 'Republic Records',       16),
    ( 5, 'Un Verano Sin Ti',               3,  '2022-05-06', 'album', 'Rimas Entertainment',    23),
    ( 6, 'Certified Lover Boy',            4,  '2021-09-03', 'album', 'Young Money',            21),
    ( 7, 'Hit Me Hard and Soft',           5,  '2024-05-17', 'album', 'Interscope Records',     10),
    ( 8, 'Mr. Morale & The Big Steppers',  6,  '2022-05-13', 'album', 'PGLang',                 18),
    ( 9, 'Future Nostalgia',               7,  '2020-03-27', 'album', 'Warner Records',         11),
    (10, 'Map of the Soul: 7',             8,  '2020-02-21', 'album', 'HYBE Labels',            20),
    (11, 'SOUR',                           10, '2021-05-21', 'album', 'Geffen Records',         11),
    (12, 'The Car',                        11, '2022-10-21', 'album', 'Domino Records',         10),
    (13, 'Mañana Será Bonito',             12, '2023-02-24', 'album', 'Universal Music Latino', 18),
    (14, 'Subtract',                        9, '2023-05-05', 'album', 'Asylum Records',         14),
    (15, 'GNX',                             6, '2024-11-22', 'album', 'PGLang / Interscope',    12);


-- ============================================================
--  6. tracks
--  EC-01: 'title' and 'release_date' mirrored from albums.
--  EC-03: album_id IS NULL for standalone singles (tracks 26–30).
--  EC-05: trk_dur_ms (abbreviated), is_exp (abbreviated).
--  EC-07: total_plays is cached and may diverge from raw events.
--
--  NOTE: album_id = 2 is 'Dawn FM' by The Weeknd, not Taylor Swift.
--        The original combined file had a mapping error; corrected here.
-- ============================================================
INSERT INTO tracks
    (track_id, title, album_id, trk_dur_ms, release_date, is_exp, isrc, track_number, total_plays)
VALUES
    -- The Weeknd — After Hours (album 1)
    ( 1, 'Blinding Lights',                     1, 200040, '2020-03-20', 0, 'USRC11902691',  7, 3800000000),
    ( 2, 'Save Your Tears',                     1, 215373, '2020-03-20', 0, 'USRC12001181',  8, 2100000000),
    ( 3, 'In Your Eyes',                        1, 237418, '2020-03-20', 0, 'USRC12001182',  9, 1900000000),
    -- The Weeknd — Dawn FM (album 2)
    ( 4, 'Sacrifice',                           2, 190426, '2022-01-07', 0, 'USRC12201234',  6,  890000000),
    ( 5, 'Take My Breath',                      2, 205125, '2022-01-07', 0, 'USRC12201235',  2,  780000000),
    -- Taylor Swift — Midnights (album 3)
    ( 6, 'Anti-Hero',                           3, 200691, '2022-10-21', 0, 'USUG12205616',  1, 2500000000),
    ( 7, 'Lavender Haze',                       3, 201945, '2022-10-21', 0, 'USUG12205617',  2, 1600000000),
    -- Taylor Swift — Folklore (album 4)
    ( 8, 'Marjorie',                            4, 253347, '2020-07-24', 0, 'USUG12101234', 13,  950000000),
    -- Bad Bunny — Un Verano Sin Ti (album 5)
    ( 9, 'Tití Me Preguntó',                    5, 248881, '2022-05-06', 1, 'PRA1G2200001',  5, 1700000000),
    (10, 'Me Porto Bonito',                     5, 192574, '2022-05-06', 1, 'PRA1G2200002',  3, 1500000000),  -- 2 artists [EC-15]
    (11, 'Después de la Playa',                 5, 278892, '2022-05-06', 1, 'PRA1G2200003',  7,  980000000),
    -- Drake — Certified Lover Boy (album 6)
    (12, 'Way 2 Sexy',                          6, 224946, '2021-09-03', 1, 'USRC12101456', 10, 1200000000),
    (13, 'Champagne Poetry',                    6, 341306, '2021-09-03', 1, 'USRC12101457',  1,  780000000),
    -- Billie Eilish — Hit Me Hard and Soft (album 7)
    (14, 'BIRDS OF A FEATHER',                  7, 210519, '2024-05-17', 0, 'USUM72404001',  2, 1100000000),
    (15, 'LUNCH',                               7, 154666, '2024-05-17', 1, 'USUM72404002',  1,  890000000),
    -- Kendrick Lamar — Mr. Morale (album 8)
    (16, 'N95',                                 8, 207688, '2022-05-13', 1, 'USGF12200001',  2,  680000000),
    (17, 'The Heart Part 5',                    8, 338693, '2022-05-13', 1, 'USGF12200002',  1,  590000000),
    -- Dua Lipa — Future Nostalgia (album 9)
    (18, 'Levitating',                          9, 203064, '2020-03-27', 0, 'GBAYK2000007',  6, 2300000000),
    (19, 'Don\'t Start Now',                    9, 183290, '2020-03-27', 0, 'GBAYK2000001',  1, 2000000000),
    -- BTS — Map of the Soul: 7 (album 10)
    (20, 'ON',                                 10, 232600, '2020-02-21', 0, 'KRA381901121',  9, 1400000000),
    (21, 'Black Swan',                         10, 220746, '2020-02-21', 0, 'KRA381901122',  4, 1100000000),
    -- Olivia Rodrigo — SOUR (album 11)
    (22, 'drivers license',                    11, 242014, '2021-05-21', 0, 'USUM72100007',  1, 2800000000),
    (23, 'good 4 u',                           11, 178455, '2021-05-21', 1, 'USUM72100008',  7, 2600000000),
    -- Arctic Monkeys — The Car (album 12)
    (24, 'There\'d Better Be a Mirrorball',    12, 225773, '2022-10-21', 0, 'GBAFL2200001',  1,  480000000),
    -- Karol G — Mañana Será Bonito (album 13)
    (25, 'CAIRO',                              13, 218026, '2023-02-24', 1, 'COA4Q2300001',  1,  750000000),
    -- Standalone singles (album_id IS NULL) [EC-03 critical NULL test]
    (26, 'One Dance',    NULL, 173885, '2016-04-05', 0, 'USRC11600890', NULL, 2200000000),  -- Drake
    (27, 'Shape of You', NULL, 233713, '2017-01-06', 0, 'GBAHS1700001', NULL, 3100000000),  -- Ed Sheeran
    (28, 'Tusa',         NULL, 200924, '2019-11-07', 1, 'COA4Q1900001', NULL, 1800000000),  -- Karol G ft Nicki
    (29, 'Beso',         NULL, 174000, '2023-08-18', 0, 'USRC12300999', NULL,  920000000),  -- Karol G featured
    (30, 'Cruel Summer', NULL, 178427, '2019-08-23', 0, 'USUG11901234', NULL, 3400000000);  -- Taylor Swift


-- ============================================================
--  7. users
--  EC-01: 'name', 'country', 'status' shared with other tables.
--  EC-02: status (0=inactive, 1=active, 2=banned); usr_acq_src (1-4).
--  EC-03: referred_by_user_id IS NULL = organic signup.
--  EC-04: self-referential referral chain.
--  Organic batch (no referrer) inserted first for FK integrity.
-- ============================================================

-- Batch 1: Organic users (referred_by_user_id = NULL)
INSERT INTO users
    (user_id, name, display_name, email, country, birth_date, status, usr_acq_src,
     referred_by_user_id, joined_at, last_login)
VALUES
    ( 1, 'Sophia Carter',    'sophc',    'sophia@email.com',   'US', '1995-03-12', 1, 1, NULL, '2022-01-15 09:30:00', '2025-01-20 14:22:00'),
    ( 2, 'James Nguyen',     'jnguyen',  'james@email.com',    'US', '1990-07-22', 1, 1, NULL, '2022-02-01 11:00:00', '2025-01-18 20:00:00'),
    ( 3, 'Maria Lopez',      'mariaL',   'maria@email.com',    'CO', '1998-11-05', 1, 1, NULL, '2022-03-10 08:15:00', '2025-01-19 17:45:00'),
    ( 4, 'Luca Rossi',       'lucar',    'luca@email.com',     'IT', '1993-04-18', 1, 2, NULL, '2022-04-05 16:00:00', '2025-01-17 10:30:00'),
    ( 5, 'Aisha Patel',      'aishah',   'aisha@email.com',    'GB', '2000-09-30', 1, 2, NULL, '2022-05-20 14:30:00', '2025-01-15 12:00:00'),
    ( 6, 'Carlos Mendez',    'carlosm',  'carlos@email.com',   'MX', '1987-01-25', 1, 1, NULL, '2022-06-01 10:00:00', '2025-01-10 08:00:00'),
    -- User 7: status=0 (inactive); has play events but NEVER for Kendrick [EC-14 anti-join]
    ( 7, 'Nina Kowalski',    'ninak',    'nina@email.com',     'PL', '2001-06-14', 0, 3, NULL, '2022-07-12 19:00:00', '2024-12-01 11:00:00'),
    -- User 8: status=0 (inactive); ZERO play events [EC-14]
    ( 8, 'Omar Hassan',      'omarh',    'omar@email.com',     'EG', '1994-08-03', 0, 1, NULL, '2022-08-22 07:30:00', '2023-11-15 09:00:00'),
    ( 9, 'Yuki Tanaka',      'yukit',    'yuki@email.com',     'JP', '1997-12-11', 1, 1, NULL, '2022-09-05 13:00:00', '2025-01-21 06:00:00'),
    (10, 'Elena Volkov',     'elenav',   'elena@email.com',    'RU', '1992-02-28', 1, 4, NULL, '2022-10-18 20:00:00', '2025-01-20 22:00:00'),
    (11, 'David Kim',        'davidk',   'david@email.com',    'KR', '1989-05-17', 1, 2, NULL, '2022-11-01 15:00:00', '2025-01-16 18:00:00'),
    -- User 12: status=2 (banned); ZERO play events [EC-14]
    (12, 'Fatima Al-Rashid', 'fatimar',  'fatima@email.com',   'SA', '2003-10-20', 2, 4, NULL, '2023-01-10 09:00:00', '2024-06-15 14:00:00'),
    (13, 'Lucas Silva',      'lucass',   'lucas@email.com',    'BR', '1996-07-08', 1, 1, NULL, '2023-02-14 12:00:00', '2025-01-19 21:30:00'),
    (14, 'Emma Wilson',      'emmaw',    'emma@email.com',     'AU', '2002-03-25', 1, 2, NULL, '2023-03-01 08:00:00', '2025-01-18 15:00:00'),
    (15, 'Santiago Ruiz',    'sanr',     'santiago@email.com', 'CO', '1991-09-14', 1, 1, NULL, '2023-04-20 17:00:00', '2025-01-21 10:00:00');

-- Batch 2: Referred users [EC-04 referral chain]
INSERT INTO users
    (user_id, name, display_name, email, country, birth_date, status, usr_acq_src,
     referred_by_user_id, joined_at, last_login)
VALUES
    (16, 'Priya Sharma',   'priyas',   'priya@email.com',    'IN', '1999-04-02', 1, 3,  1, '2023-05-15 11:00:00', '2025-01-20 19:00:00'),  -- by Sophia
    (17, 'Tom Müller',     'tomm',     'tom@email.com',      'DE', '1995-11-30', 1, 3,  3, '2023-06-08 16:00:00', '2025-01-17 14:00:00'),  -- by Maria
    (18, 'Isabela Costa',  'isabelac', 'isabela@email.com',  'BR', '2000-08-17', 1, 3, 13, '2023-07-22 09:30:00', '2025-01-19 20:00:00'),  -- by Lucas
    (19, 'Alex Turner',    'alext',    'alex@email.com',     'GB', '1997-06-22', 1, 3,  5, '2023-08-11 14:00:00', '2025-01-21 08:00:00'),  -- by Aisha
    (20, 'Camila Torres',  'camilat',  'camila@email.com',   'CO', '2001-01-09', 1, 3, 15, '2023-09-03 10:00:00', '2025-01-20 16:00:00');  -- by Santiago


-- ============================================================
--  8. playlists
--  EC-01: 'name' shared with artists, users, genres.
--  EC-02: playlist_type enum ('user'/'curated'/'algorithmic').
--  EC-04: forked_from_id self-referential. Original playlists first.
-- ============================================================

-- Original playlists (forked_from_id = NULL)
INSERT INTO playlists
    (playlist_id, name, user_id, playlist_type, is_public, forked_from_id, created_at, follower_count)
VALUES
    ( 1, 'Top Global Hits',    1,  'curated',     1, NULL, '2022-01-20 10:00:00', 245000),
    ( 2, 'Discover Weekly',    2,  'algorithmic', 1, NULL, '2022-02-05 10:00:00',  12000),
    ( 3, 'Latin Fever',        3,  'curated',     1, NULL, '2022-03-15 10:00:00', 189000),
    ( 4, 'Chill Vibes',        4,  'user',        1, NULL, '2022-04-10 10:00:00',   3400),
    ( 5, 'Workout Bangers',    2,  'user',        1, NULL, '2022-05-25 10:00:00',   7800),
    ( 6, 'K-Pop Essentials',  11,  'curated',     1, NULL, '2022-06-01 10:00:00', 320000),
    ( 7, 'Hip-Hop Hits',       1,  'curated',     1, NULL, '2022-07-14 10:00:00', 430000),
    ( 8, 'Indie Afternoon',    4,  'user',        1, NULL, '2022-08-20 10:00:00',   1200),
    ( 9, 'Evening Jazz',       9,  'user',        0, NULL, '2022-09-01 10:00:00',    450),  -- private
    (10, 'My Daily Mix',       5,  'algorithmic', 1, NULL, '2022-10-10 10:00:00',    890),
    (11, 'Electronic Nights', 10,  'user',        1, NULL, '2022-11-05 10:00:00',   5600),
    (12, 'New Releases 2024',  1,  'curated',     1, NULL, '2024-01-01 00:00:00',  98000),
    (13, 'Throwbacks',         6,  'user',        1, NULL, '2023-01-20 10:00:00',   2100),
    (14, 'Reggaeton Mix',      3,  'user',        1, NULL, '2023-02-28 10:00:00',  15000),
    (15, 'Sad Hours',          5,  'user',        0, NULL, '2023-03-14 10:00:00',      0);  -- private, 0 followers

-- Forked playlists [EC-04 self-ref]
INSERT INTO playlists
    (playlist_id, name, user_id, playlist_type, is_public, forked_from_id, created_at, follower_count)
VALUES
    (16, 'Latin Fever (My Version)',  15, 'user', 1,  3, '2023-05-01 10:00:00',  340),  -- forked from #3
    (17, 'Global Hits Remix',         16, 'user', 1,  1, '2023-06-15 10:00:00',  120),  -- forked from #1
    (18, 'Hip-Hop Hits Extended',     20, 'user', 1,  7, '2023-09-10 10:00:00',  670);  -- forked from #7


-- ============================================================
--  9. track_artists  (bridge: tracks <-> artists)
--  EC-05: is_prim abbreviated for is_primary.
--  EC-15: track 10 has 2 artists (Bad Bunny + Karol G) ->
--         COUNT(*) vs COUNT(DISTINCT artist_id) difference.
-- ============================================================
INSERT INTO track_artists (track_id, artist_id, is_prim, role) VALUES
    -- The Weeknd tracks
    ( 1, 1, 1, 'main'), ( 2, 1, 1, 'main'), ( 3, 1, 1, 'main'),
    ( 4, 1, 1, 'main'), ( 5, 1, 1, 'main'),
    -- Taylor Swift tracks
    ( 6, 2, 1, 'main'), ( 7, 2, 1, 'main'), ( 8, 2, 1, 'main'),
    -- Bad Bunny tracks (track 10: Bad Bunny + Karol G [EC-15])
    ( 9, 3, 1, 'main'),
    (10, 3, 1, 'main'), (10, 12, 0, 'featured'),
    (11, 3, 1, 'main'),
    -- Drake tracks
    (12, 4, 1, 'main'), (13, 4, 1, 'main'),
    -- Billie Eilish tracks
    (14, 5, 1, 'main'), (15, 5, 1, 'main'),
    -- Kendrick Lamar tracks
    (16, 6, 1, 'main'), (17, 6, 1, 'main'),
    -- Dua Lipa tracks
    (18, 7, 1, 'main'), (19, 7, 1, 'main'),
    -- BTS tracks
    (20, 8, 1, 'main'), (21, 8, 1, 'main'),
    -- Ed Sheeran single
    (27, 9, 1, 'main'),
    -- Olivia Rodrigo tracks
    (22, 10, 1, 'main'), (23, 10, 1, 'main'),
    -- Arctic Monkeys tracks
    (24, 11, 1, 'main'),
    -- Karol G tracks
    (25, 12, 1, 'main'),
    (28, 12, 1, 'main'),
    (29, 12, 0, 'featured'),  -- Karol G is featured on Beso
    -- Standalone singles
    (26, 4,  1, 'main'),      -- One Dance: Drake
    (30, 2,  1, 'main');      -- Cruel Summer: Taylor Swift


-- ============================================================
--  10. artist_genres  (bridge: artists <-> genres)
--  EC-05: is_prim abbreviated. is_prim = 1 = primary genre.
-- ============================================================
INSERT INTO artist_genres (artist_id, genre_id, is_prim) VALUES
    ( 1,  5, 1), ( 1,  6, 0), ( 1,  1, 0),   -- The Weeknd: R&B (primary), Electronic, Pop
    ( 2,  1, 1), ( 2,  2, 0),                 -- Taylor Swift: Pop (primary), Rock
    ( 3,  4, 1), ( 3, 15, 0), ( 3, 13, 0),   -- Bad Bunny: Latin (primary), Reggaeton, Trap
    ( 4,  3, 1), ( 4, 13, 0),                 -- Drake: Hip-Hop (primary), Trap
    ( 5,  1, 1), ( 5, 10, 0),                 -- Billie Eilish: Pop (primary), Indie Pop
    ( 6,  3, 1), ( 6, 14, 0),                 -- Kendrick Lamar: Hip-Hop (primary), Drill
    ( 7,  1, 1), ( 7,  6, 0),                 -- Dua Lipa: Pop (primary), Electronic
    ( 8,  9, 1), ( 8,  1, 0),                 -- BTS: K-Pop (primary), Pop
    ( 9,  1, 1), ( 9,  2, 0),                 -- Ed Sheeran: Pop (primary), Rock
    (10,  1, 1), (10, 10, 0),                 -- Olivia Rodrigo: Pop (primary), Indie Pop
    (11,  2, 1), (11, 11, 0), (11, 12, 0),   -- Arctic Monkeys: Rock (primary), Indie Rock, Alternative
    (12,  4, 1), (12, 15, 0);                 -- Karol G: Latin (primary), Reggaeton


-- ============================================================
--  11. track_genres  (bridge: tracks <-> genres)
--  EC-01: Separate from artist_genres — intentional ambiguity.
--  "What genre is this track?" != "What genre is this artist?"
-- ============================================================
INSERT INTO track_genres (track_id, genre_id) VALUES
    ( 1, 1), ( 1,  5),   -- Blinding Lights:  Pop, R&B
    ( 2, 1), ( 2,  5),   -- Save Your Tears:  Pop, R&B
    ( 3, 5), ( 3,  6),   -- In Your Eyes:     R&B, Electronic
    ( 4, 6), ( 4,  1),   -- Sacrifice:        Electronic, Pop
    ( 5, 6), ( 5,  5),   -- Take My Breath:   Electronic, R&B
    ( 6, 1),              -- Anti-Hero:        Pop
    ( 7, 1),              -- Lavender Haze:    Pop
    ( 8, 1), ( 8, 10),   -- Marjorie:         Pop, Indie Pop
    ( 9, 4), ( 9, 15),   -- Tití Me Preguntó: Latin, Reggaeton
    (10, 4), (10, 15),   -- Me Porto Bonito:  Latin, Reggaeton
    (11, 4), (11, 15),   -- Después de la Playa: Latin, Reggaeton
    (12, 3), (12, 13),   -- Way 2 Sexy:       Hip-Hop, Trap
    (13, 3),              -- Champagne Poetry: Hip-Hop
    (14, 1), (14, 10),   -- BIRDS OF A FEATHER: Pop, Indie Pop
    (15, 1),              -- LUNCH:            Pop
    (16, 3), (16, 13),   -- N95:              Hip-Hop, Trap
    (17, 3),              -- The Heart Part 5: Hip-Hop
    (18, 1), (18,  6),   -- Levitating:       Pop, Electronic
    (19, 1), (19,  6),   -- Don't Start Now:  Pop, Electronic
    (20, 9), (20,  1),   -- ON:               K-Pop, Pop
    (21, 9),              -- Black Swan:       K-Pop
    (22, 1), (22, 10),   -- drivers license:  Pop, Indie Pop
    (23, 1),              -- good 4 u:         Pop
    (24, 2), (24, 11),   -- Mirrorball:       Rock, Indie Rock
    (25, 4), (25, 15),   -- CAIRO:            Latin, Reggaeton
    (26, 3), (26,  5),   -- One Dance:        Hip-Hop, R&B
    (27, 1), (27,  2),   -- Shape of You:     Pop, Rock
    (28, 4), (28, 15),   -- Tusa:             Latin, Reggaeton
    (29, 4), (29, 15),   -- Beso:             Latin, Reggaeton
    (30, 1), (30,  2);   -- Cruel Summer:     Pop, Rock


-- ============================================================
--  12. playlist_tracks  (bridge: playlists <-> tracks)
--  Tracks NOT in any playlist (anti-join targets [EC-14]):
--    track_id: 2, 5, 7, 11, 15, 17, 19, 21, 29
-- ============================================================
INSERT INTO playlist_tracks (playlist_id, track_id, position, added_at) VALUES
    -- Playlist 1: Top Global Hits (curated)
    (1,  1, 1, '2022-01-20 10:00:00'), (1,  6, 2, '2022-01-20 10:00:00'),
    (1, 18, 3, '2022-01-20 10:00:00'), (1, 22, 4, '2022-01-20 10:00:00'),
    (1, 19, 5, '2022-01-20 10:00:00'), (1, 30, 6, '2022-02-01 08:00:00'),
    (1, 27, 7, '2022-02-01 08:00:00'), (1, 26, 8, '2022-02-01 08:00:00'),
    -- Playlist 3: Latin Fever (curated)
    (3,  9, 1, '2022-03-15 10:00:00'), (3, 10, 2, '2022-03-15 10:00:00'),
    (3, 11, 3, '2022-03-15 10:00:00'), (3, 25, 4, '2022-03-15 10:00:00'),
    (3, 28, 5, '2022-03-15 10:00:00'), (3, 29, 6, '2022-04-01 09:00:00'),
    -- Playlist 5: Workout Bangers (user)
    (5,  1, 1, '2022-05-25 10:00:00'), (5, 12, 2, '2022-05-25 10:00:00'),
    (5, 23, 3, '2022-05-25 10:00:00'), (5, 16, 4, '2022-05-25 10:00:00'),
    (5, 20, 5, '2022-05-25 10:00:00'), (5,  6, 6, '2022-06-01 10:00:00'),
    -- Playlist 6: K-Pop Essentials (curated)
    (6, 20, 1, '2022-06-01 10:00:00'), (6, 21, 2, '2022-06-01 10:00:00'),
    -- Playlist 7: Hip-Hop Hits (curated)
    (7, 12, 1, '2022-07-14 10:00:00'), (7, 13, 2, '2022-07-14 10:00:00'),
    (7, 16, 3, '2022-07-14 10:00:00'), (7, 17, 4, '2022-07-14 10:00:00'),
    (7, 26, 5, '2022-07-14 10:00:00'),
    -- Playlist 8: Indie Afternoon (user)
    (8, 24, 1, '2022-08-20 10:00:00'), (8,  8, 2, '2022-08-20 10:00:00'),
    (8, 14, 3, '2022-09-01 10:00:00'),
    -- Playlist 12: New Releases 2024 (curated)
    (12, 14, 1, '2024-01-01 10:00:00'), (12, 15, 2, '2024-01-01 10:00:00'),
    -- Playlist 14: Reggaeton Mix (user)
    (14,  9, 1, '2023-02-28 10:00:00'), (14, 10, 2, '2023-02-28 10:00:00'),
    (14, 25, 3, '2023-02-28 10:00:00'), (14, 28, 4, '2023-02-28 10:00:00'),
    -- Playlist 16: Latin Fever My Version (forked from #3)
    (16,  9, 1, '2023-05-01 10:00:00'), (16, 10, 2, '2023-05-01 10:00:00'),
    (16, 25, 3, '2023-05-01 10:00:00'),
    -- Playlist 18: Hip-Hop Hits Extended (forked from #7)
    (18, 12, 1, '2023-09-10 10:00:00'), (18, 13, 2, '2023-09-10 10:00:00'),
    (18, 26, 3, '2023-09-10 10:00:00'), (18,  4, 4, '2023-09-10 10:00:00');


-- ============================================================
--  13. user_follows_artists
--  EC-14 anti-join seed: User 7 follows artist 6 (Kendrick)
--  but has zero play events for Kendrick tracks.
-- ============================================================
INSERT INTO user_follows_artists (user_id, artist_id, followed_at) VALUES
    ( 1,  1, '2022-01-20 11:00:00'), ( 1,  2, '2022-01-20 11:05:00'), ( 1, 7, '2022-02-01 09:00:00'),
    ( 2,  4, '2022-02-10 14:00:00'), ( 2,  6, '2022-03-01 10:00:00'),
    ( 3,  3, '2022-03-20 16:00:00'), ( 3, 12, '2022-03-20 16:05:00'), ( 3, 4, '2022-05-01 12:00:00'),
    ( 4, 11, '2022-04-15 10:00:00'), ( 4,  5, '2022-07-01 10:00:00'),
    ( 5,  2, '2022-05-25 09:00:00'), ( 5, 10, '2022-06-01 10:00:00'),
    ( 6,  3, '2022-06-10 11:00:00'), ( 6, 12, '2022-08-01 12:00:00'),
    -- User 7 follows Kendrick but plays no Kendrick tracks [EC-14]
    ( 7,  6, '2022-07-20 10:00:00'),
    ( 9,  8, '2022-09-10 07:00:00'), ( 9,  1, '2022-10-01 08:00:00'),
    (11,  8, '2022-11-15 16:00:00'), (11,  9, '2023-01-01 10:00:00'),
    (13,  3, '2023-02-20 13:00:00'), (13, 12, '2023-03-01 14:00:00'),
    (15,  3, '2023-04-25 09:00:00'), (15, 12, '2023-04-25 09:05:00'),
    (16,  7, '2023-05-20 11:00:00'), (16,  2, '2023-06-01 12:00:00'),
    (17, 11, '2023-06-15 10:00:00'),
    (18,  3, '2023-07-25 14:00:00'),
    (19, 11, '2023-08-15 08:00:00'), (19,  5, '2023-09-01 10:00:00'),
    (20,  3, '2023-09-10 15:00:00');


-- ============================================================
--  14. user_liked_tracks
--  EC-17: Overlaps with play_events WHERE event_type = 'save'.
--  "Saved tracks" is ambiguous between these two sources.
-- ============================================================
INSERT INTO user_liked_tracks (user_id, track_id, liked_at) VALUES
    ( 1,  1, '2022-02-01 10:00:00'), ( 1,  6, '2022-03-01 10:00:00'), ( 1, 18, '2022-04-01 10:00:00'),
    ( 2, 22, '2022-03-01 10:00:00'), ( 2, 23, '2022-04-01 10:00:00'),
    ( 3,  9, '2022-04-01 10:00:00'), ( 3, 10, '2022-04-01 10:00:00'), ( 3, 28, '2022-05-01 10:00:00'),
    ( 4, 24, '2022-05-01 10:00:00'), ( 4,  8, '2022-06-01 10:00:00'),
    ( 5,  6, '2022-06-01 10:00:00'), ( 5,  7, '2022-06-01 10:00:00'), ( 5, 30, '2022-07-01 10:00:00'),
    ( 6,  9, '2022-07-01 10:00:00'), ( 6, 25, '2023-03-01 10:00:00'),
    ( 9, 20, '2022-10-01 10:00:00'), ( 9, 21, '2022-10-01 10:00:00'),
    (11, 20, '2022-12-01 10:00:00'), (11, 21, '2022-12-01 10:00:00'),
    (13,  9, '2023-03-01 10:00:00'), (13, 10, '2023-03-01 10:00:00'),
    (15, 25, '2023-05-01 10:00:00'),
    (16, 18, '2023-06-01 10:00:00'), (16,  7, '2023-06-01 10:00:00'),
    (20,  9, '2023-09-15 10:00:00');


-- ============================================================
--  15. subscriptions
--  EC-01: status shared with users.status.
--  EC-02: status coded 0/1/2.
--  EC-03: end_date IS NULL = currently active subscription.
--  EC-06: temporal SCD.
-- ============================================================
INSERT INTO subscriptions
    (subscription_id, user_id, plan_id, status, start_date, end_date, auto_renew)
VALUES
    -- Active (end_date = NULL)
    ( 1,  1, 3, 1, '2022-01-15', NULL,         1),  -- Sophia: Individual
    ( 2,  2, 3, 1, '2022-02-01', NULL,         1),  -- James: Individual
    ( 3,  3, 4, 1, '2022-03-10', NULL,         1),  -- Maria: Family
    ( 4,  4, 2, 1, '2022-04-05', NULL,         1),  -- Luca: Student
    ( 5,  5, 3, 1, '2022-05-20', NULL,         1),  -- Aisha: Individual
    ( 6,  6, 1, 1, '2022-06-01', NULL,         0),  -- Carlos: Free
    ( 7,  9, 3, 1, '2022-09-05', NULL,         1),  -- Yuki: Individual
    ( 8, 10, 4, 1, '2022-10-18', NULL,         1),  -- Elena: Family
    ( 9, 11, 2, 1, '2022-11-01', NULL,         1),  -- David: Student
    (10, 13, 3, 1, '2023-02-14', NULL,         1),  -- Lucas: Individual
    (11, 14, 2, 1, '2023-03-01', NULL,         1),  -- Emma: Student
    (12, 15, 3, 1, '2023-04-20', NULL,         1),  -- Santiago: Individual
    (13, 16, 3, 1, '2023-05-15', NULL,         1),  -- Priya: Individual
    (14, 17, 4, 1, '2023-06-08', NULL,         1),  -- Tom: Family
    (15, 18, 1, 1, '2023-07-22', NULL,         0),  -- Isabela: Free
    (16, 19, 2, 1, '2023-08-11', NULL,         1),  -- Alex: Student
    (17, 20, 4, 1, '2023-09-03', NULL,         1),  -- Camila: Family
    -- Expired (end_date set) [EC-06]
    (18,  7, 3, 0, '2022-07-12', '2023-06-30', 0),  -- Nina: was Individual, now lapsed
    (19,  8, 1, 0, '2022-08-22', '2023-11-14', 0),  -- Omar: was Free, now inactive
    (20, 12, 3, 2, '2023-01-10', '2024-06-14', 0);  -- Fatima: was Individual, suspended


-- ============================================================
--  16. subscription_periods  (SCD)
--  EC-06: period_end IS NULL = currently running.
--  Captures plan upgrades. James, Elena, Tom each have 2 rows.
-- ============================================================
INSERT INTO subscription_periods
    (user_id, plan_id, period_start, period_end, monthly_fee)
VALUES
    -- Single-period users
    ( 1, 3, '2022-01-15', NULL,         9.49),  -- Sophia: always Individual
    ( 3, 4, '2022-03-10', NULL,        14.99),  -- Maria: always Family
    ( 4, 2, '2022-04-05', NULL,         4.99),  -- Luca: always Student
    ( 6, 1, '2022-06-01', NULL,         0.00),  -- Carlos: always Free
    (13, 3, '2023-02-14', NULL,         9.99),  -- Lucas: always Individual
    (18, 1, '2023-07-22', NULL,         0.00),  -- Isabela: always Free
    -- Multi-period users (plan upgrades)
    ( 2, 2, '2022-02-01', '2022-12-31', 4.99),  -- James: Student...
    ( 2, 3, '2023-01-01', NULL,         9.49),  -- ...then Individual
    ( 7, 3, '2022-07-12', '2023-06-30', 8.99),  -- Nina: Individual (lapsed)
    (10, 3, '2022-10-18', '2023-06-30', 9.49),  -- Elena: Individual...
    (10, 4, '2023-07-01', NULL,        14.99),  -- ...then Family
    (17, 3, '2023-06-08', '2023-08-31', 9.99),  -- Tom: Individual...
    (17, 4, '2023-09-01', NULL,        15.99);  -- ...then Family


-- ============================================================
--  17. payments
--  EC-17: payment_status enum tests value filtering.
--         Includes 1 failed, 1 refunded, rest completed.
-- ============================================================
INSERT INTO payments
    (subscription_id, user_id, amount, payment_date, payment_method, payment_status, currency)
VALUES
    -- Sophia (Individual)
    ( 1,  1,  9.49, '2022-02-15', 'card',   'completed', 'USD'),
    ( 1,  1,  9.49, '2022-03-15', 'card',   'completed', 'USD'),
    ( 1,  1,  9.49, '2023-01-15', 'card',   'completed', 'USD'),
    ( 1,  1,  9.99, '2024-02-15', 'card',   'completed', 'USD'),
    -- James (Student -> Individual)
    ( 2,  2,  4.99, '2022-03-01', 'paypal', 'completed', 'USD'),
    ( 2,  2,  9.49, '2023-02-01', 'paypal', 'completed', 'USD'),
    ( 2,  2,  9.99, '2024-02-01', 'paypal', 'completed', 'USD'),
    -- Maria (Family)
    ( 3,  3, 14.99, '2022-04-10', 'card',   'completed', 'USD'),
    ( 3,  3, 14.99, '2023-04-10', 'card',   'completed', 'USD'),
    ( 3,  3, 15.99, '2024-04-10', 'card',   'completed', 'USD'),
    -- Luca (Student, EUR)
    ( 4,  4,  4.99, '2022-05-05', 'card',   'completed', 'EUR'),
    ( 4,  4,  5.49, '2024-05-05', 'card',   'completed', 'EUR'),
    -- Elena (Family)
    ( 8, 10, 14.99, '2022-11-18', 'card',   'completed', 'USD'),
    ( 8, 10, 15.99, '2024-11-18', 'card',   'completed', 'USD'),
    -- Tom (Individual -> Family, EUR)
    (14, 17,  9.99, '2023-07-08', 'card',   'completed', 'EUR'),
    (14, 17, 15.99, '2024-07-08', 'card',   'completed', 'EUR'),
    -- Priya: failed then completed [EC-17 value matching test]
    (13, 16,  9.99, '2024-06-15', 'card',   'failed',    'USD'),
    (13, 16,  9.99, '2024-06-20', 'card',   'completed', 'USD'),
    -- Fatima: refunded [EC-17]
    (20, 12,  9.49, '2023-02-10', 'card',   'refunded',  'USD'),
    -- Santiago
    (12, 15,  9.49, '2023-05-20', 'card',   'completed', 'USD'),
    (12, 15,  9.99, '2024-05-20', 'card',   'completed', 'USD');


-- ============================================================
--  18. play_events
--  Temporal coverage: 2023-01-01 to 2025-01-20 (8+ quarters).
--  EC-02: event_type discriminator ('play'/'skip'/'save'/'share').
--  EC-03: playlist_id IS NULL = outside any playlist.
--  EC-05: trk_position_ms abbreviated.
--
--  Key anti-join seeds:
--    Users 7, 8, 12 have ZERO play_events rows entirely.
--    User 7 follows Kendrick (artist 6) but no events for
--      tracks 16 or 17 anywhere in this table.
--
--  Key EC-07 seed:
--    The counts here are five to six orders of magnitude lower than
--    daily_artist_metrics, not ~5% lower (corrected 2026-07-21).
--
--  Skip events (event_type='skip') are sprinkled across
--  the timeline to enable skip-rate queries [EC-13, EC-25].
-- ============================================================
INSERT INTO play_events
    (user_id, track_id, playlist_id, event_type, played_at,
     trk_position_ms, duration_ms, country_code, device_type)
VALUES
-- ---- 2023 Q1 -----------------------------------------------
( 1,  1,  1,    'play', '2023-01-05 08:00:00',     0, 200040, 'US', 'mobile'),
( 1,  6,  1,    'play', '2023-01-05 08:05:00',     0, 200691, 'US', 'mobile'),
( 2, 22, NULL,  'play', '2023-01-06 14:00:00',     0, 242014, 'US', 'desktop'),
( 2, 23, NULL,  'play', '2023-01-06 14:10:00',     0, 178455, 'US', 'desktop'),
( 3,  9,  3,    'play', '2023-01-10 18:00:00',     0, 248881, 'CO', 'mobile'),
( 3, 10,  3,    'play', '2023-01-10 18:10:00',     0, 192574, 'CO', 'mobile'),
( 3, 11, NULL,  'skip', '2023-01-10 18:22:00', 15000,  15000, 'CO', 'mobile'),
( 4, 24,  8,    'play', '2023-01-15 20:00:00',     0, 225773, 'IT', 'desktop'),
( 5,  6, NULL,  'play', '2023-01-20 10:00:00',     0, 200691, 'GB', 'tablet'),
( 5,  7, NULL,  'play', '2023-01-20 10:05:00',     0, 201945, 'GB', 'tablet'),
( 6,  9,  3,    'play', '2023-02-01 15:00:00',     0, 248881, 'MX', 'mobile'),
( 7, 24,  8,    'play', '2023-02-05 19:00:00',     0, 225773, 'PL', 'desktop'),
( 9, 20,  6,    'play', '2023-02-10 09:00:00',     0, 232600, 'JP', 'mobile'),
( 9, 21,  6,    'play', '2023-02-10 09:15:00',     0, 220746, 'JP', 'mobile'),
(10,  3, NULL,  'play', '2023-02-15 22:00:00',     0, 237418, 'RU', 'smart_tv'),
(11, 20,  6,    'play', '2023-02-20 17:00:00',     0, 232600, 'KR', 'mobile'),
(13,  9,  3,    'play', '2023-03-01 12:00:00',     0, 248881, 'BR', 'mobile'),
(13, 10,  3,    'play', '2023-03-01 12:10:00',     0, 192574, 'BR', 'mobile'),
(15,  9, 14,    'play', '2023-03-10 16:00:00',     0, 248881, 'CO', 'mobile'),
(15, 25, 14,    'play', '2023-03-10 16:15:00',     0, 218026, 'CO', 'mobile'),
-- ---- 2023 Q2 -----------------------------------------------
( 1, 18,  1,    'play', '2023-04-02 08:00:00',     0, 203064, 'US', 'mobile'),
( 1, 19,  1,    'play', '2023-04-02 08:10:00',     0, 183290, 'US', 'mobile'),
( 2, 12,  5,    'play', '2023-04-05 15:00:00',     0, 224946, 'US', 'desktop'),
( 3, 25,  3,    'play', '2023-04-08 18:00:00',     0, 218026, 'CO', 'mobile'),
( 4,  8,  8,    'play', '2023-04-10 20:00:00',     0, 253347, 'IT', 'desktop'),
( 5, 30,  1,    'play', '2023-04-15 10:00:00',     0, 178427, 'GB', 'tablet'),
( 6,  9, NULL,  'save', '2023-04-20 16:00:00',     0,      0, 'MX', 'mobile'),
( 9,  1, NULL,  'play', '2023-05-01 08:00:00',     0, 200040, 'JP', 'mobile'),
(10,  4, NULL,  'play', '2023-05-05 22:00:00',     0, 190426, 'RU', 'smart_tv'),
(11, 21,  6,    'play', '2023-05-10 17:00:00',     0, 220746, 'KR', 'mobile'),
(13, 28, NULL,  'play', '2023-05-15 12:00:00',     0, 200924, 'BR', 'mobile'),
(15, 28, 14,    'play', '2023-05-20 15:00:00',     0, 200924, 'CO', 'mobile'),
(16, 18, NULL,  'play', '2023-06-01 11:00:00',     0, 203064, 'IN', 'mobile'),
(16, 19, NULL,  'play', '2023-06-01 11:10:00',     0, 183290, 'IN', 'mobile'),
(17, 24, NULL,  'play', '2023-06-10 14:00:00',     0, 225773, 'DE', 'desktop'),
(18,  9, NULL,  'play', '2023-06-15 18:00:00',     0, 248881, 'BR', 'mobile'),
(19, 24, NULL,  'play', '2023-06-20 09:00:00',     0, 225773, 'GB', 'desktop'),
(20,  9, 16,    'play', '2023-06-25 17:00:00',     0, 248881, 'CO', 'mobile'),
-- ---- 2023 Q3 -----------------------------------------------
( 1,  1,  1,    'play', '2023-07-01 08:00:00',     0, 200040, 'US', 'mobile'),
( 1,  6,  1,    'skip', '2023-07-01 08:05:00', 25000,  25000, 'US', 'mobile'),
( 2, 26,  7,    'play', '2023-07-05 14:00:00',     0, 173885, 'US', 'desktop'),
( 3,  9, 16,    'play', '2023-07-10 18:00:00',     0, 248881, 'CO', 'mobile'),
( 5, 22, NULL,  'play', '2023-07-15 10:00:00',     0, 242014, 'GB', 'mobile'),
( 5, 22, NULL,  'save', '2023-07-15 10:05:00',     0,      0, 'GB', 'mobile'),
( 6, 10,  3,    'play', '2023-07-20 16:00:00',     0, 192574, 'MX', 'mobile'),
( 9, 20,  6,    'play', '2023-08-01 09:00:00',     0, 232600, 'JP', 'mobile'),
(10,  5, NULL,  'play', '2023-08-05 22:00:00',     0, 205125, 'RU', 'smart_tv'),
(11, 20,  6,    'play', '2023-08-10 17:00:00',     0, 232600, 'KR', 'mobile'),
(13,  9, 14,    'play', '2023-08-15 12:00:00',     0, 248881, 'BR', 'mobile'),
(14,  6,  1,    'play', '2023-08-20 21:00:00',     0, 200691, 'AU', 'tablet'),
(15, 25,  3,    'play', '2023-08-25 16:00:00',     0, 218026, 'CO', 'mobile'),
(16,  7, NULL,  'play', '2023-09-01 11:00:00',     0, 201945, 'IN', 'mobile'),
(17, 11, NULL,  'play', '2023-09-05 14:00:00',     0, 278892, 'DE', 'desktop'),
(18, 10, NULL,  'play', '2023-09-10 18:00:00',     0, 192574, 'BR', 'mobile'),
(19, 24,  8,    'play', '2023-09-15 09:00:00',     0, 225773, 'GB', 'desktop'),
(20,  9, 16,    'play', '2023-09-20 17:00:00',     0, 248881, 'CO', 'mobile'),
-- ---- 2023 Q4 -----------------------------------------------
( 1, 30,  1,    'play', '2023-10-01 08:00:00',     0, 178427, 'US', 'mobile'),
( 2, 12,  5,    'play', '2023-10-05 14:00:00',     0, 224946, 'US', 'desktop'),
( 2, 16,  7,    'play', '2023-10-05 14:15:00',     0, 207688, 'US', 'desktop'),
( 3,  9, 14,    'play', '2023-10-10 18:00:00',     0, 248881, 'CO', 'mobile'),
( 4, 24,  8,    'play', '2023-10-15 20:00:00',     0, 225773, 'IT', 'desktop'),
( 5,  6, NULL,  'play', '2023-10-20 10:00:00',     0, 200691, 'GB', 'tablet'),
( 6,  9,  3,    'play', '2023-11-01 15:00:00',     0, 248881, 'MX', 'mobile'),
( 9,  1, NULL,  'play', '2023-11-05 08:00:00',     0, 200040, 'JP', 'mobile'),
(10,  3, NULL,  'play', '2023-11-10 22:00:00',     0, 237418, 'RU', 'smart_tv'),
(11, 21,  6,    'play', '2023-11-15 17:00:00',     0, 220746, 'KR', 'mobile'),
(13, 25,  3,    'play', '2023-11-20 12:00:00',     0, 218026, 'BR', 'mobile'),
(15, 10, 14,    'play', '2023-11-25 16:00:00',     0, 192574, 'CO', 'mobile'),
(16, 18, NULL,  'play', '2023-12-01 11:00:00',     0, 203064, 'IN', 'mobile'),
(17, 24, NULL,  'skip', '2023-12-05 14:00:00', 20000,  20000, 'DE', 'desktop'),
(18,  9, 16,    'play', '2023-12-10 18:00:00',     0, 248881, 'BR', 'mobile'),
(19, 24, NULL,  'play', '2023-12-15 09:00:00',     0, 225773, 'GB', 'desktop'),
(20, 10, 16,    'play', '2023-12-20 17:00:00',     0, 192574, 'CO', 'mobile'),
-- ---- 2024 Q1 -----------------------------------------------
( 1, 14, 12,    'play', '2024-01-05 08:00:00',     0, 210519, 'US', 'mobile'),
( 1, 15, 12,    'play', '2024-01-05 08:10:00',     0, 154666, 'US', 'mobile'),
( 2, 22, NULL,  'play', '2024-01-06 14:00:00',     0, 242014, 'US', 'desktop'),
( 3,  9, 14,    'play', '2024-01-10 18:00:00',     0, 248881, 'CO', 'mobile'),
( 5, 14, 12,    'play', '2024-01-15 10:00:00',     0, 210519, 'GB', 'tablet'),
( 9, 20,  6,    'play', '2024-01-20 09:00:00',     0, 232600, 'JP', 'mobile'),
(10,  4, NULL,  'play', '2024-01-25 22:00:00',     0, 190426, 'RU', 'smart_tv'),
(11, 20,  6,    'play', '2024-02-01 17:00:00',     0, 232600, 'KR', 'mobile'),
(13,  9, 14,    'play', '2024-02-05 12:00:00',     0, 248881, 'BR', 'mobile'),
(14,  6,  1,    'play', '2024-02-10 21:00:00',     0, 200691, 'AU', 'tablet'),
(15, 25,  3,    'play', '2024-02-15 16:00:00',     0, 218026, 'CO', 'mobile'),
(16,  7, NULL,  'play', '2024-02-20 11:00:00',     0, 201945, 'IN', 'mobile'),
(17, 24, NULL,  'play', '2024-02-25 14:00:00',     0, 225773, 'DE', 'desktop'),
(18,  9, 16,    'play', '2024-03-01 18:00:00',     0, 248881, 'BR', 'mobile'),
(19, 24,  8,    'play', '2024-03-05 09:00:00',     0, 225773, 'GB', 'desktop'),
(20,  9, 16,    'play', '2024-03-10 17:00:00',     0, 248881, 'CO', 'mobile'),
-- ---- 2024 Q2 -----------------------------------------------
( 1,  1,  1,    'play', '2024-04-01 08:00:00',     0, 200040, 'US', 'mobile'),
( 2, 26,  7,    'play', '2024-04-05 14:00:00',     0, 173885, 'US', 'desktop'),
( 3, 25, 14,    'play', '2024-04-10 18:00:00',     0, 218026, 'CO', 'mobile'),
( 4, 24,  8,    'play', '2024-04-15 20:00:00',     0, 225773, 'IT', 'desktop'),
( 5, 30,  1,    'play', '2024-04-20 10:00:00',     0, 178427, 'GB', 'tablet'),
( 6,  9,  3,    'play', '2024-04-25 16:00:00',     0, 248881, 'MX', 'mobile'),
( 9, 20, NULL,  'play', '2024-05-01 09:00:00',     0, 232600, 'JP', 'mobile'),
(10,  3, NULL,  'play', '2024-05-05 22:00:00',     0, 237418, 'RU', 'smart_tv'),
(11, 21,  6,    'play', '2024-05-10 17:00:00',     0, 220746, 'KR', 'mobile'),
(13, 28, NULL,  'play', '2024-05-15 12:00:00',     0, 200924, 'BR', 'mobile'),
(15,  9,  3,    'play', '2024-05-20 16:00:00',     0, 248881, 'CO', 'mobile'),
(16, 18, NULL,  'play', '2024-05-25 11:00:00',     0, 203064, 'IN', 'mobile'),
(17, 24, NULL,  'play', '2024-06-01 14:00:00',     0, 225773, 'DE', 'desktop'),
(18, 10, 16,    'play', '2024-06-05 18:00:00',     0, 192574, 'BR', 'mobile'),
(19, 24,  8,    'play', '2024-06-10 09:00:00',     0, 225773, 'GB', 'desktop'),
(20,  9, 16,    'play', '2024-06-15 17:00:00',     0, 248881, 'CO', 'mobile'),
-- ---- 2024 Q3  (Billie Eilish album launch spike) -----------
( 1, 14, 12,    'play', '2024-07-01 08:00:00',     0, 210519, 'US', 'mobile'),
( 2, 14, 12,    'play', '2024-07-02 14:00:00',     0, 210519, 'US', 'desktop'),
( 5, 14, 12,    'play', '2024-07-03 10:00:00',     0, 210519, 'GB', 'tablet'),
( 5, 15, 12,    'play', '2024-07-03 10:15:00',     0, 154666, 'GB', 'tablet'),
(14, 14, 12,    'play', '2024-07-05 21:00:00',     0, 210519, 'AU', 'mobile'),
(16, 14, 12,    'play', '2024-07-10 11:00:00',     0, 210519, 'IN', 'mobile'),
(19, 14, NULL,  'play', '2024-07-15 09:00:00',     0, 210519, 'GB', 'mobile'),
( 1, 15, NULL,  'save', '2024-07-15 08:10:00',     0,      0, 'US', 'mobile'),
( 3,  9, 14,    'play', '2024-07-20 18:00:00',     0, 248881, 'CO', 'mobile'),
( 6,  9, NULL, 'share', '2024-07-25 16:00:00',     0,      0, 'MX', 'mobile'),
( 9, 20,  6,    'play', '2024-08-01 09:00:00',     0, 232600, 'JP', 'mobile'),
(10,  5, NULL,  'play', '2024-08-05 22:00:00',     0, 205125, 'RU', 'smart_tv'),
(11, 20,  6,    'play', '2024-08-10 17:00:00',     0, 232600, 'KR', 'mobile'),
(13,  9, 14,    'play', '2024-08-15 12:00:00',     0, 248881, 'BR', 'mobile'),
(15, 25,  3,    'play', '2024-08-20 16:00:00',     0, 218026, 'CO', 'mobile'),
(17, 11, NULL,  'play', '2024-08-25 14:00:00',     0, 278892, 'DE', 'desktop'),
(18,  9, 16,    'play', '2024-09-01 18:00:00',     0, 248881, 'BR', 'mobile'),
(20,  9, 16,    'play', '2024-09-05 17:00:00',     0, 248881, 'CO', 'mobile'),
-- ---- 2024 Q4 -----------------------------------------------
( 1,  1,  1,    'play', '2024-10-01 08:00:00',     0, 200040, 'US', 'mobile'),
( 2, 22, NULL,  'play', '2024-10-05 14:00:00',     0, 242014, 'US', 'desktop'),
( 3,  9,  3,    'play', '2024-10-10 18:00:00',     0, 248881, 'CO', 'mobile'),
( 4, 24,  8,    'play', '2024-10-15 20:00:00',     0, 225773, 'IT', 'desktop'),
( 5,  7, NULL,  'play', '2024-10-20 10:00:00',     0, 201945, 'GB', 'tablet'),
( 6, 10,  3,    'play', '2024-10-25 16:00:00',     0, 192574, 'MX', 'mobile'),
( 9,  1, NULL,  'play', '2024-11-01 08:00:00',     0, 200040, 'JP', 'mobile'),
(10,  3, NULL,  'play', '2024-11-05 22:00:00',     0, 237418, 'RU', 'smart_tv'),
(11, 20,  6,    'play', '2024-11-10 17:00:00',     0, 232600, 'KR', 'mobile'),
(13,  9, 14,    'play', '2024-11-15 12:00:00',     0, 248881, 'BR', 'mobile'),
(14, 18,  1,    'play', '2024-11-20 21:00:00',     0, 203064, 'AU', 'tablet'),
(15,  9, 14,    'play', '2024-11-25 16:00:00',     0, 248881, 'CO', 'mobile'),
(16, 18, NULL,  'play', '2024-12-01 11:00:00',     0, 203064, 'IN', 'mobile'),
(17, 24, NULL,  'play', '2024-12-05 14:00:00',     0, 225773, 'DE', 'desktop'),
(18,  9, 16,    'play', '2024-12-10 18:00:00',     0, 248881, 'BR', 'mobile'),
(19, 24,  8,    'play', '2024-12-15 09:00:00',     0, 225773, 'GB', 'desktop'),
(20,  9, 16,    'play', '2024-12-20 17:00:00',     0, 248881, 'CO', 'mobile'),
-- ---- 2025 Q1 (partial) -------------------------------------
( 1,  1,  1,    'play', '2025-01-05 08:00:00',     0, 200040, 'US', 'mobile'),
( 2, 22, NULL,  'play', '2025-01-06 14:00:00',     0, 242014, 'US', 'desktop'),
( 3,  9, 14,    'play', '2025-01-10 18:00:00',     0, 248881, 'CO', 'mobile'),
( 5, 14, 12,    'play', '2025-01-15 10:00:00',     0, 210519, 'GB', 'tablet'),
( 9, 20,  6,    'play', '2025-01-20 09:00:00',     0, 232600, 'JP', 'mobile');


-- ============================================================
--  19. daily_artist_metrics
--  EC-07: stream_count is intentionally above play_events — by 290,000x to
--         1,070,000x as actually seeded (corrected 2026-07-21; "~5%" was intent).
--  EC-16: composite PK (artist_id, metric_date, country_code).
--  Using this table AND play_events for the same aggregate
--  causes double-counting — the ambiguity is by design.
-- ============================================================
INSERT INTO daily_artist_metrics
    (artist_id, metric_date, country_code,
     stream_count, skip_count, save_count, unique_listeners, avg_listen_pct)
VALUES
    -- The Weeknd
    (1, '2023-01-05', 'US', 3150000, 210000,  45000, 2900000, 87.50),
    (1, '2023-04-02', 'US', 2800000, 180000,  38000, 2600000, 89.20),
    (1, '2023-07-01', 'US', 3400000, 250000,  52000, 3100000, 86.80),
    (1, '2023-10-01', 'US', 2950000, 195000,  41000, 2750000, 88.30),
    (1, '2024-01-05', 'US', 3200000, 220000,  48000, 2950000, 87.10),
    (1, '2024-04-01', 'US', 3050000, 205000,  44000, 2800000, 88.60),
    (1, '2024-10-01', 'US', 3300000, 230000,  50000, 3050000, 87.40),
    -- Taylor Swift
    (2, '2023-01-06', 'US', 4200000, 180000,  95000, 3900000, 91.20),
    (2, '2023-04-15', 'GB', 1800000,  75000,  42000, 1650000, 90.80),
    (2, '2024-01-06', 'US', 4500000, 195000, 102000, 4150000, 91.70),
    (2, '2024-04-20', 'GB', 1950000,  82000,  46000, 1800000, 91.30),
    -- Bad Bunny
    (3, '2023-01-10', 'CO', 5100000, 320000,  88000, 4800000, 88.90),
    (3, '2023-01-10', 'MX', 6200000, 410000, 105000, 5900000, 89.40),
    (3, '2023-04-08', 'CO', 5300000, 340000,  91000, 5000000, 89.10),
    (3, '2024-01-10', 'CO', 5600000, 360000,  97000, 5300000, 89.80),
    (3, '2024-04-10', 'CO', 5250000, 335000,  92000, 4950000, 89.20),
    -- Billie Eilish (album spike visible in Q3 2024)
    (5, '2023-01-20', 'GB',  980000,  65000,  28000,  920000, 86.50),
    (5, '2024-01-15', 'GB', 1050000,  70000,  30000,  980000, 87.20),
    (5, '2024-07-03', 'GB', 3800000, 180000,  95000, 3600000, 91.40),  -- launch spike
    (5, '2024-07-10', 'IN', 1200000,  55000,  38000, 1150000, 90.80),
    -- Dua Lipa
    (7, '2023-04-02', 'US', 2100000, 120000,  55000, 1950000, 89.60),
    (7, '2023-06-01', 'IN', 1400000,  80000,  38000, 1300000, 88.90),
    (7, '2024-02-20', 'IN', 1500000,  85000,  41000, 1400000, 89.30),
    -- BTS
    (8, '2023-02-10', 'JP', 3200000,  95000,  88000, 3050000, 93.20),
    (8, '2023-02-20', 'KR', 4800000, 145000, 132000, 4600000, 94.10),
    (8, '2024-01-20', 'JP', 3050000,  88000,  84000, 2900000, 93.50),
    (8, '2024-05-10', 'KR', 4600000, 138000, 126000, 4400000, 93.80),
    -- Karol G
    (12, '2023-03-10', 'CO', 7200000, 480000, 145000, 6900000, 90.10),
    (12, '2023-06-15', 'US', 4100000, 275000,  82000, 3900000, 89.60),
    (12, '2024-02-15', 'CO', 7800000, 520000, 158000, 7500000, 90.70),
    (12, '2024-05-20', 'CO', 7500000, 498000, 151000, 7200000, 90.30);


-- ===== EXTENSION 2025-01-21 .. 2026-07-17 (generated) =====

-- Generated by scripts/extend_seed_data.py  seed=20260721
-- Window: 2025-01-21 .. 2026-07-17
-- Regenerate with: python databases/soundwave/scripts/extend_seed_data.py
-- Preserves EC-02/03/04/06/07/17. See the module docstring.

-- 1. new users [EC-03 organic NULL, EC-04 referral chain]

INSERT INTO users
    (user_id, name, display_name, email, country, birth_date, status, usr_acq_src,
     referred_by_user_id, joined_at, last_login)
VALUES
    (21, 'Hannah Brooks', 'hannahb', 'hannahb@email.com', 'US', '2002-01-07', 1, 4, NULL, '2025-01-30 11:45:00', '2026-02-14 11:45:00'),
    (22, 'Mateo Duarte', 'mateod', 'mateod@email.com', 'CO', '2005-06-10', 1, 4, NULL, '2025-01-28 10:15:00', '2025-10-07 10:15:00'),
    (23, 'Sofia Ricci', 'sofiar', 'sofiar@email.com', 'IT', '1993-07-14', 1, 2, NULL, '2025-02-01 22:15:00', '2025-02-08 22:15:00'),
    (24, 'Liam O''Connor', 'liamoc', 'liamoc@email.com', 'IE', '2005-05-12', 1, 2, NULL, '2025-03-20 12:30:00', '2026-02-24 12:30:00'),
    (25, 'Amara Okafor', 'amarao', 'amarao@email.com', 'NG', '1989-06-25', 1, 3, 9, '2025-04-12 19:45:00', '2025-12-08 19:45:00'),
    (26, 'Kenji Sato', 'kenjis', 'kenjis@email.com', 'JP', '1988-04-13', 1, 3, 1, '2025-05-27 07:15:00', '2026-03-19 07:15:00'),
    (27, 'Chloe Dubois', 'chloed', 'chloed@email.com', 'FR', '2001-10-28', 1, 3, 1, '2025-06-01 08:30:00', '2026-04-15 08:30:00'),
    (28, 'Diego Herrera', 'diegoh', 'diegoh@email.com', 'MX', '1989-08-26', 1, 2, NULL, '2025-07-13 11:00:00', '2026-04-21 11:00:00'),
    (29, 'Ingrid Larsen', 'ingridl', 'ingridl@email.com', 'NO', '1995-08-12', 2, 4, NULL, '2025-08-14 19:00:00', '2026-03-21 19:00:00'),
    (30, 'Rahul Mehta', 'rahulm', 'rahulm@email.com', 'IN', '1992-11-10', 1, 1, NULL, '2025-09-26 07:00:00', '2026-07-14 07:00:00'),
    (31, 'Beatriz Costa', 'beatrizc', 'beatrizc@email.com', 'BR', '1995-09-16', 1, 3, 4, '2025-10-16 20:45:00', '2025-11-24 20:45:00'),
    (32, 'Jonas Weber', 'jonasw', 'jonasw@email.com', 'DE', '1997-01-18', 1, 3, 17, '2025-11-05 15:45:00', '2026-02-19 15:45:00'),
    (33, 'Mia Thompson', 'miat', 'miat@email.com', 'AU', '1998-12-19', 1, 3, 5, '2025-12-06 19:00:00', '2026-06-22 19:00:00'),
    (34, 'Ali Hassan', 'alih', 'alih@email.com', 'EG', '2004-03-07', 1, 4, NULL, '2026-01-20 07:30:00', '2026-07-17 07:00:00'),
    (35, 'Nora Lindqvist', 'noral', 'noral@email.com', 'SE', '1993-08-23', 1, 3, 14, '2026-02-15 13:30:00', '2026-07-17 22:00:00'),
    (36, 'Pablo Ramos', 'pablor', 'pablor@email.com', 'ES', '2003-07-06', 1, 2, NULL, '2026-03-06 19:45:00', '2026-07-17 21:00:00'),
    (37, 'Grace Kim', 'gracek', 'gracek@email.com', 'KR', '1995-05-26', 1, 1, NULL, '2026-04-11 12:30:00', '2026-07-17 08:00:00'),
    (38, 'Tomas Novak', 'tomasn', 'tomasn@email.com', 'CZ', '2000-02-17', 1, 1, NULL, '2026-05-04 23:45:00', '2026-05-08 23:45:00'),
    (39, 'Valentina Cruz', 'valentinac', 'valentinac@email.com', 'AR', '1995-09-27', 1, 2, NULL, '2026-06-18 10:45:00', '2026-07-17 18:00:00'),
    (40, 'Owen Baker', 'owenb', 'owenb@email.com', 'GB', '2002-05-25', 1, 1, NULL, '2026-07-08 19:15:00', '2026-07-17 18:00:00');


-- 2. new releases [EC-03 standalone singles keep album_id NULL]

INSERT INTO albums
    (album_id, title, artist_id, release_date, album_type, label, total_tracks)
VALUES
    (16, 'Midnight Reverie', 1, '2025-03-14', 'album', 'Republic Records', 4),
    (17, 'Neon Season', 7, '2025-07-25', 'album', 'Warner Records', 4),
    (18, 'Cartografía', 12, '2025-11-07', 'album', 'Universal Music Latino', 4),
    (19, 'Static Bloom', 5, '2026-02-20', 'album', 'Interscope Records', 3),
    (20, 'Long Way Home', 9, '2026-05-15', 'ep', 'Asylum Records', 3);

INSERT INTO tracks
    (track_id, title, album_id, trk_dur_ms, release_date, is_exp, track_number, total_plays)
VALUES
    (31, 'Midnight Reverie', 16, 213400, '2025-03-14', 0, 1, 0),
    (32, 'Afterglow Drive', 16, 198750, '2025-03-14', 0, 2, 0),
    (33, 'Cold Static', 16, 226100, '2025-03-14', 1, 3, 0),
    (34, 'Slow Fade', 16, 241300, '2025-03-14', 0, 4, 0),
    (35, 'Neon Season', 17, 187900, '2025-07-25', 0, 1, 0),
    (36, 'Glass Hearts', 17, 202450, '2025-07-25', 0, 2, 0),
    (37, 'Overdrive', 17, 176300, '2025-07-25', 0, 3, 0),
    (38, 'Last Train', 17, 219800, '2025-07-25', 0, 4, 0),
    (39, 'Cartografía', 18, 231600, '2025-11-07', 0, 1, 0),
    (40, 'Mapa del Cielo', 18, 208400, '2025-11-07', 0, 2, 0),
    (41, 'Sin Regreso', 18, 195200, '2025-11-07', 1, 3, 0),
    (42, 'Volver', 18, 244700, '2025-11-07', 0, 4, 0),
    (43, 'Static Bloom', 19, 189300, '2026-02-20', 0, 1, 0),
    (44, 'Paper Thin', 19, 167800, '2026-02-20', 0, 2, 0),
    (45, 'Undertow', 19, 233100, '2026-02-20', 1, 3, 0),
    (46, 'Golden Hour', NULL, 205600, '2025-09-05', 0, NULL, 0),
    (47, 'Ritmo Nuevo', NULL, 191400, '2026-01-16', 0, NULL, 0),
    (48, 'Echoes', NULL, 224900, '2026-06-12', 0, NULL, 0);

INSERT INTO track_artists (track_id, artist_id, is_prim, role) VALUES
    (31, 1, 1, 'main'),
    (32, 1, 1, 'main'),
    (33, 1, 1, 'main'),
    (34, 1, 1, 'main'),
    (35, 7, 1, 'main'),
    (36, 7, 1, 'main'),
    (37, 7, 1, 'main'),
    (38, 7, 1, 'main'),
    (39, 12, 1, 'main'),
    (40, 12, 1, 'main'),
    (41, 12, 1, 'main'),
    (42, 12, 1, 'main'),
    (43, 5, 1, 'main'),
    (44, 5, 1, 'main'),
    (45, 5, 1, 'main'),
    (46, 9, 1, 'main'),
    (47, 3, 1, 'main'),
    (48, 2, 1, 'main');


-- 3. pricing change [EC-06 closes the open SCD row, opens a new one]

UPDATE pricing_history SET effective_to = '2025-08-31', changed_reason = 'Superseded by 2025 adjustment' WHERE effective_to IS NULL AND plan_id IN (2, 3, 4);

INSERT INTO pricing_history
    (plan_id, monthly_price, effective_from, effective_to, changed_reason)
VALUES
    (2, 6.49, '2025-09-01', NULL, '2025 price adjustment'),
    (3, 11.99, '2025-09-01', NULL, '2025 price adjustment'),
    (4, 17.99, '2025-09-01', NULL, '2025 price adjustment');

UPDATE subscription_plans SET monthly_price = 6.49 WHERE plan_id = 2;
UPDATE subscription_plans SET monthly_price = 11.99 WHERE plan_id = 3;
UPDATE subscription_plans SET monthly_price = 17.99 WHERE plan_id = 4;


-- 4. subscriptions, churn and upgrades [EC-06]

UPDATE subscription_periods SET period_end = '2025-09-30' WHERE user_id IN (4, 11) AND period_end IS NULL;
UPDATE subscriptions SET plan_id = 3 WHERE subscription_id IN (4, 9);
INSERT INTO subscriptions
    (subscription_id, user_id, plan_id, status, start_date, end_date, auto_renew)
VALUES
    (21, 21, 3, 1, '2025-05-05', NULL, 1),
    (22, 22, 1, 1, '2026-01-05', NULL, 1),
    (23, 23, 4, 1, '2025-12-04', NULL, 1),
    (24, 24, 1, 0, '2025-10-29', '2026-01-30', 0),
    (25, 25, 2, 1, '2025-08-10', NULL, 1),
    (26, 26, 4, 1, '2026-01-22', NULL, 1),
    (27, 27, 1, 0, '2025-01-27', '2025-06-20', 0),
    (28, 28, 4, 1, '2025-02-19', NULL, 1),
    (29, 29, 4, 1, '2026-02-14', NULL, 1),
    (30, 30, 2, 1, '2025-03-23', NULL, 1),
    (31, 31, 2, 1, '2026-04-14', NULL, 1),
    (32, 32, 2, 1, '2026-04-06', NULL, 1),
    (33, 33, 2, 0, '2025-07-16', '2025-10-23', 0),
    (34, 34, 3, 1, '2025-03-16', NULL, 1),
    (35, 35, 3, 1, '2025-07-31', NULL, 1),
    (36, 36, 3, 1, '2025-10-24', NULL, 1),
    (37, 37, 4, 1, '2025-11-01', NULL, 1),
    (38, 38, 3, 1, '2025-09-24', NULL, 1),
    (39, 39, 3, 1, '2026-01-08', NULL, 1),
    (40, 40, 4, 0, '2025-03-23', '2025-11-07', 0);

INSERT INTO subscription_periods
    (user_id, plan_id, period_start, period_end, monthly_fee)
VALUES
    (21, 3, '2025-05-05', NULL, 11.99),
    (22, 1, '2026-01-05', NULL, 0.0),
    (23, 4, '2025-12-04', NULL, 17.99),
    (24, 1, '2025-10-29', '2026-01-30', 0.0),
    (25, 2, '2025-08-10', NULL, 6.49),
    (26, 4, '2026-01-22', NULL, 17.99),
    (27, 1, '2025-01-27', '2025-06-20', 0.0),
    (28, 4, '2025-02-19', NULL, 17.99),
    (29, 4, '2026-02-14', NULL, 17.99),
    (30, 2, '2025-03-23', NULL, 6.49),
    (31, 2, '2026-04-14', NULL, 6.49),
    (32, 2, '2026-04-06', NULL, 6.49),
    (33, 2, '2025-07-16', '2025-10-23', 6.49),
    (34, 3, '2025-03-16', NULL, 11.99),
    (35, 3, '2025-07-31', NULL, 11.99),
    (36, 3, '2025-10-24', NULL, 11.99),
    (37, 4, '2025-11-01', NULL, 17.99),
    (38, 3, '2025-09-24', NULL, 11.99),
    (39, 3, '2026-01-08', NULL, 11.99),
    (40, 4, '2025-03-23', '2025-11-07', 17.99),
    (4, 3, '2025-10-01', NULL, 11.99),
    (11, 3, '2025-10-01', NULL, 11.99);



-- 5. recurring payments [EC-17 failed/refunded tail]

INSERT INTO payments
    (subscription_id, user_id, amount, payment_date, payment_method, payment_status, currency)
VALUES
    (1, 1, 9.99, '2025-02-15', 'card', 'completed', 'USD'),
    (1, 1, 9.99, '2025-03-15', 'paypal', 'completed', 'USD'),
    (1, 1, 9.99, '2025-04-15', 'card', 'completed', 'USD'),
    (1, 1, 9.99, '2025-05-15', 'card', 'completed', 'USD'),
    (1, 1, 9.99, '2025-06-15', 'card', 'completed', 'USD'),
    (1, 1, 9.99, '2025-07-15', 'crypto', 'completed', 'USD'),
    (1, 1, 9.99, '2025-08-15', 'card', 'completed', 'USD'),
    (1, 1, 11.99, '2025-09-15', 'paypal', 'completed', 'USD'),
    (1, 1, 11.99, '2025-10-15', 'card', 'completed', 'USD'),
    (1, 1, 11.99, '2025-11-15', 'card', 'completed', 'USD'),
    (1, 1, 11.99, '2025-12-15', 'voucher', 'completed', 'USD'),
    (1, 1, 11.99, '2026-01-15', 'card', 'completed', 'USD'),
    (1, 1, 11.99, '2026-02-15', 'card', 'completed', 'USD'),
    (1, 1, 11.99, '2026-03-15', 'card', 'completed', 'USD'),
    (1, 1, 11.99, '2026-04-15', 'card', 'completed', 'USD'),
    (1, 1, 11.99, '2026-05-15', 'card', 'completed', 'USD'),
    (1, 1, 11.99, '2026-06-15', 'card', 'failed', 'USD'),
    (1, 1, 11.99, '2026-07-15', 'card', 'completed', 'USD'),
    (2, 2, 9.99, '2025-02-15', 'card', 'completed', 'USD'),
    (2, 2, 9.99, '2025-03-15', 'card', 'completed', 'USD'),
    (2, 2, 9.99, '2025-04-15', 'crypto', 'completed', 'USD'),
    (2, 2, 9.99, '2025-05-15', 'card', 'failed', 'USD'),
    (2, 2, 9.99, '2025-06-15', 'card', 'completed', 'USD'),
    (2, 2, 9.99, '2025-07-15', 'card', 'completed', 'USD'),
    (2, 2, 9.99, '2025-08-15', 'card', 'completed', 'USD'),
    (2, 2, 11.99, '2025-09-15', 'card', 'completed', 'USD'),
    (2, 2, 11.99, '2025-10-15', 'paypal', 'completed', 'USD'),
    (2, 2, 11.99, '2025-11-15', 'crypto', 'completed', 'USD'),
    (2, 2, 11.99, '2025-12-15', 'card', 'completed', 'USD'),
    (2, 2, 11.99, '2026-01-15', 'paypal', 'completed', 'USD'),
    (2, 2, 11.99, '2026-02-15', 'card', 'completed', 'USD'),
    (2, 2, 11.99, '2026-03-15', 'crypto', 'completed', 'USD'),
    (2, 2, 11.99, '2026-04-15', 'card', 'failed', 'USD'),
    (2, 2, 11.99, '2026-05-15', 'card', 'completed', 'USD'),
    (2, 2, 11.99, '2026-06-15', 'card', 'completed', 'USD'),
    (2, 2, 11.99, '2026-07-15', 'paypal', 'completed', 'USD'),
    (3, 3, 15.99, '2025-02-15', 'paypal', 'completed', 'USD'),
    (3, 3, 15.99, '2025-03-15', 'paypal', 'completed', 'USD'),
    (3, 3, 15.99, '2025-04-15', 'paypal', 'completed', 'USD'),
    (3, 3, 15.99, '2025-05-15', 'paypal', 'completed', 'USD'),
    (3, 3, 15.99, '2025-06-15', 'card', 'completed', 'USD'),
    (3, 3, 15.99, '2025-07-15', 'paypal', 'completed', 'USD'),
    (3, 3, 15.99, '2025-08-15', 'card', 'completed', 'USD'),
    (3, 3, 17.99, '2025-09-15', 'paypal', 'completed', 'USD'),
    (3, 3, 17.99, '2025-10-15', 'card', 'completed', 'USD'),
    (3, 3, 17.99, '2025-11-15', 'paypal', 'completed', 'USD'),
    (3, 3, 17.99, '2025-12-15', 'voucher', 'completed', 'USD'),
    (3, 3, 17.99, '2026-01-15', 'card', 'completed', 'USD'),
    (3, 3, 17.99, '2026-02-15', 'card', 'completed', 'USD'),
    (3, 3, 17.99, '2026-03-15', 'crypto', 'completed', 'USD'),
    (3, 3, 17.99, '2026-04-15', 'card', 'completed', 'USD'),
    (3, 3, 17.99, '2026-05-15', 'paypal', 'completed', 'USD'),
    (3, 3, 17.99, '2026-06-15', 'card', 'completed', 'USD'),
    (3, 3, 17.99, '2026-07-15', 'crypto', 'completed', 'USD'),
    (4, 4, 5.49, '2025-02-15', 'card', 'completed', 'USD'),
    (4, 4, 5.49, '2025-03-15', 'card', 'completed', 'USD'),
    (4, 4, 5.49, '2025-04-15', 'paypal', 'completed', 'USD'),
    (4, 4, 5.49, '2025-05-15', 'card', 'completed', 'USD'),
    (4, 4, 5.49, '2025-06-15', 'paypal', 'completed', 'USD'),
    (4, 4, 5.49, '2025-07-15', 'crypto', 'completed', 'USD'),
    (4, 4, 5.49, '2025-08-15', 'card', 'completed', 'USD'),
    (4, 4, 6.49, '2025-09-15', 'paypal', 'completed', 'USD'),
    (4, 4, 6.49, '2025-10-15', 'card', 'completed', 'USD'),
    (4, 4, 6.49, '2025-11-15', 'card', 'completed', 'USD'),
    (4, 4, 6.49, '2025-12-15', 'card', 'completed', 'USD'),
    (4, 4, 6.49, '2026-01-15', 'crypto', 'completed', 'USD'),
    (4, 4, 6.49, '2026-02-15', 'card', 'completed', 'USD'),
    (4, 4, 6.49, '2026-03-15', 'crypto', 'completed', 'USD'),
    (4, 4, 6.49, '2026-04-15', 'crypto', 'completed', 'USD'),
    (4, 4, 6.49, '2026-05-15', 'paypal', 'refunded', 'USD'),
    (4, 4, 6.49, '2026-06-15', 'card', 'completed', 'USD'),
    (4, 4, 6.49, '2026-07-15', 'voucher', 'completed', 'USD'),
    (5, 5, 9.99, '2025-02-15', 'card', 'completed', 'USD'),
    (5, 5, 9.99, '2025-03-15', 'card', 'completed', 'USD'),
    (5, 5, 9.99, '2025-04-15', 'paypal', 'completed', 'USD'),
    (5, 5, 9.99, '2025-05-15', 'card', 'completed', 'USD'),
    (5, 5, 9.99, '2025-06-15', 'paypal', 'completed', 'USD'),
    (5, 5, 9.99, '2025-07-15', 'card', 'completed', 'USD'),
    (5, 5, 9.99, '2025-08-15', 'card', 'completed', 'USD'),
    (5, 5, 11.99, '2025-09-15', 'card', 'completed', 'USD'),
    (5, 5, 11.99, '2025-10-15', 'card', 'completed', 'USD'),
    (5, 5, 11.99, '2025-11-15', 'card', 'completed', 'USD'),
    (5, 5, 11.99, '2025-12-15', 'crypto', 'completed', 'USD'),
    (5, 5, 11.99, '2026-01-15', 'crypto', 'completed', 'USD'),
    (5, 5, 11.99, '2026-02-15', 'card', 'completed', 'USD'),
    (5, 5, 11.99, '2026-03-15', 'card', 'failed', 'USD'),
    (5, 5, 11.99, '2026-04-15', 'card', 'completed', 'USD'),
    (5, 5, 11.99, '2026-05-15', 'card', 'completed', 'USD'),
    (5, 5, 11.99, '2026-06-15', 'card', 'completed', 'USD'),
    (5, 5, 11.99, '2026-07-15', 'paypal', 'completed', 'USD'),
    (7, 9, 9.99, '2025-02-15', 'voucher', 'completed', 'USD'),
    (7, 9, 9.99, '2025-03-15', 'card', 'completed', 'USD'),
    (7, 9, 9.99, '2025-04-15', 'card', 'completed', 'USD'),
    (7, 9, 9.99, '2025-05-15', 'card', 'completed', 'USD'),
    (7, 9, 9.99, '2025-06-15', 'card', 'completed', 'USD'),
    (7, 9, 9.99, '2025-07-15', 'card', 'completed', 'USD'),
    (7, 9, 9.99, '2025-08-15', 'crypto', 'completed', 'USD'),
    (7, 9, 11.99, '2025-09-15', 'card', 'completed', 'USD'),
    (7, 9, 11.99, '2025-10-15', 'crypto', 'completed', 'USD'),
    (7, 9, 11.99, '2025-11-15', 'card', 'failed', 'USD'),
    (7, 9, 11.99, '2025-12-15', 'voucher', 'completed', 'USD'),
    (7, 9, 11.99, '2026-01-15', 'card', 'completed', 'USD'),
    (7, 9, 11.99, '2026-02-15', 'card', 'completed', 'USD'),
    (7, 9, 11.99, '2026-03-15', 'paypal', 'completed', 'USD'),
    (7, 9, 11.99, '2026-04-15', 'card', 'completed', 'USD'),
    (7, 9, 11.99, '2026-05-15', 'paypal', 'completed', 'USD'),
    (7, 9, 11.99, '2026-06-15', 'card', 'completed', 'USD'),
    (7, 9, 11.99, '2026-07-15', 'paypal', 'completed', 'USD'),
    (8, 10, 15.99, '2025-02-15', 'card', 'completed', 'USD'),
    (8, 10, 15.99, '2025-03-15', 'paypal', 'completed', 'USD'),
    (8, 10, 15.99, '2025-04-15', 'card', 'completed', 'USD'),
    (8, 10, 15.99, '2025-05-15', 'paypal', 'completed', 'USD'),
    (8, 10, 15.99, '2025-06-15', 'paypal', 'completed', 'USD'),
    (8, 10, 15.99, '2025-07-15', 'card', 'completed', 'USD'),
    (8, 10, 15.99, '2025-08-15', 'paypal', 'completed', 'USD'),
    (8, 10, 17.99, '2025-09-15', 'crypto', 'completed', 'USD'),
    (8, 10, 17.99, '2025-10-15', 'paypal', 'completed', 'USD'),
    (8, 10, 17.99, '2025-11-15', 'card', 'completed', 'USD'),
    (8, 10, 17.99, '2025-12-15', 'voucher', 'completed', 'USD'),
    (8, 10, 17.99, '2026-01-15', 'paypal', 'completed', 'USD'),
    (8, 10, 17.99, '2026-02-15', 'card', 'completed', 'USD'),
    (8, 10, 17.99, '2026-03-15', 'card', 'completed', 'USD'),
    (8, 10, 17.99, '2026-04-15', 'paypal', 'failed', 'USD'),
    (8, 10, 17.99, '2026-05-15', 'card', 'completed', 'USD'),
    (8, 10, 17.99, '2026-06-15', 'card', 'completed', 'USD'),
    (8, 10, 17.99, '2026-07-15', 'card', 'refunded', 'USD'),
    (9, 11, 5.49, '2025-02-15', 'card', 'completed', 'USD'),
    (9, 11, 5.49, '2025-03-15', 'voucher', 'completed', 'USD'),
    (9, 11, 5.49, '2025-04-15', 'card', 'completed', 'USD'),
    (9, 11, 5.49, '2025-05-15', 'card', 'completed', 'USD'),
    (9, 11, 5.49, '2025-06-15', 'card', 'completed', 'USD'),
    (9, 11, 5.49, '2025-07-15', 'voucher', 'completed', 'USD'),
    (9, 11, 5.49, '2025-08-15', 'crypto', 'completed', 'USD'),
    (9, 11, 6.49, '2025-09-15', 'crypto', 'completed', 'USD'),
    (9, 11, 6.49, '2025-10-15', 'card', 'completed', 'USD'),
    (9, 11, 6.49, '2025-11-15', 'card', 'completed', 'USD'),
    (9, 11, 6.49, '2025-12-15', 'card', 'completed', 'USD'),
    (9, 11, 6.49, '2026-01-15', 'card', 'completed', 'USD'),
    (9, 11, 6.49, '2026-02-15', 'card', 'completed', 'USD'),
    (9, 11, 6.49, '2026-03-15', 'card', 'completed', 'USD'),
    (9, 11, 6.49, '2026-04-15', 'voucher', 'completed', 'USD'),
    (9, 11, 6.49, '2026-05-15', 'card', 'completed', 'USD'),
    (9, 11, 6.49, '2026-06-15', 'card', 'failed', 'USD'),
    (9, 11, 6.49, '2026-07-15', 'paypal', 'completed', 'USD'),
    (10, 13, 9.99, '2025-02-15', 'voucher', 'completed', 'USD'),
    (10, 13, 9.99, '2025-03-15', 'card', 'completed', 'USD'),
    (10, 13, 9.99, '2025-04-15', 'card', 'completed', 'USD'),
    (10, 13, 9.99, '2025-05-15', 'voucher', 'failed', 'USD'),
    (10, 13, 9.99, '2025-06-15', 'voucher', 'completed', 'USD'),
    (10, 13, 9.99, '2025-07-15', 'card', 'completed', 'USD'),
    (10, 13, 9.99, '2025-08-15', 'paypal', 'completed', 'USD'),
    (10, 13, 11.99, '2025-09-15', 'paypal', 'completed', 'USD'),
    (10, 13, 11.99, '2025-10-15', 'paypal', 'completed', 'USD'),
    (10, 13, 11.99, '2025-11-15', 'card', 'completed', 'USD'),
    (10, 13, 11.99, '2025-12-15', 'card', 'completed', 'USD'),
    (10, 13, 11.99, '2026-01-15', 'paypal', 'completed', 'USD'),
    (10, 13, 11.99, '2026-02-15', 'card', 'completed', 'USD'),
    (10, 13, 11.99, '2026-03-15', 'card', 'completed', 'USD'),
    (10, 13, 11.99, '2026-04-15', 'voucher', 'completed', 'USD'),
    (10, 13, 11.99, '2026-05-15', 'paypal', 'completed', 'USD'),
    (10, 13, 11.99, '2026-06-15', 'paypal', 'completed', 'USD'),
    (10, 13, 11.99, '2026-07-15', 'paypal', 'completed', 'USD'),
    (11, 14, 5.49, '2025-02-15', 'crypto', 'completed', 'USD'),
    (11, 14, 5.49, '2025-03-15', 'voucher', 'completed', 'USD'),
    (11, 14, 5.49, '2025-04-15', 'card', 'completed', 'USD'),
    (11, 14, 5.49, '2025-05-15', 'paypal', 'completed', 'USD'),
    (11, 14, 5.49, '2025-06-15', 'crypto', 'completed', 'USD'),
    (11, 14, 5.49, '2025-07-15', 'card', 'completed', 'USD'),
    (11, 14, 5.49, '2025-08-15', 'card', 'completed', 'USD'),
    (11, 14, 6.49, '2025-09-15', 'card', 'completed', 'USD'),
    (11, 14, 6.49, '2025-10-15', 'card', 'completed', 'USD'),
    (11, 14, 6.49, '2025-11-15', 'paypal', 'completed', 'USD'),
    (11, 14, 6.49, '2025-12-15', 'voucher', 'completed', 'USD'),
    (11, 14, 6.49, '2026-01-15', 'paypal', 'completed', 'USD'),
    (11, 14, 6.49, '2026-02-15', 'card', 'completed', 'USD'),
    (11, 14, 6.49, '2026-03-15', 'card', 'completed', 'USD'),
    (11, 14, 6.49, '2026-04-15', 'card', 'completed', 'USD'),
    (11, 14, 6.49, '2026-05-15', 'voucher', 'completed', 'USD'),
    (11, 14, 6.49, '2026-06-15', 'card', 'completed', 'USD'),
    (11, 14, 6.49, '2026-07-15', 'card', 'completed', 'USD'),
    (12, 15, 9.99, '2025-02-15', 'crypto', 'completed', 'USD'),
    (12, 15, 9.99, '2025-03-15', 'card', 'completed', 'USD'),
    (12, 15, 9.99, '2025-04-15', 'paypal', 'completed', 'USD'),
    (12, 15, 9.99, '2025-05-15', 'card', 'completed', 'USD'),
    (12, 15, 9.99, '2025-06-15', 'card', 'completed', 'USD'),
    (12, 15, 9.99, '2025-07-15', 'card', 'completed', 'USD'),
    (12, 15, 9.99, '2025-08-15', 'card', 'completed', 'USD'),
    (12, 15, 11.99, '2025-09-15', 'card', 'completed', 'USD'),
    (12, 15, 11.99, '2025-10-15', 'paypal', 'failed', 'USD'),
    (12, 15, 11.99, '2025-11-15', 'card', 'completed', 'USD'),
    (12, 15, 11.99, '2025-12-15', 'card', 'completed', 'USD'),
    (12, 15, 11.99, '2026-01-15', 'paypal', 'completed', 'USD'),
    (12, 15, 11.99, '2026-02-15', 'card', 'completed', 'USD'),
    (12, 15, 11.99, '2026-03-15', 'card', 'completed', 'USD'),
    (12, 15, 11.99, '2026-04-15', 'card', 'completed', 'USD'),
    (12, 15, 11.99, '2026-05-15', 'card', 'completed', 'USD'),
    (12, 15, 11.99, '2026-06-15', 'paypal', 'completed', 'USD'),
    (12, 15, 11.99, '2026-07-15', 'paypal', 'completed', 'USD'),
    (13, 16, 9.99, '2025-02-15', 'card', 'completed', 'USD'),
    (13, 16, 9.99, '2025-03-15', 'card', 'completed', 'USD'),
    (13, 16, 9.99, '2025-04-15', 'crypto', 'completed', 'USD'),
    (13, 16, 9.99, '2025-05-15', 'paypal', 'completed', 'USD'),
    (13, 16, 9.99, '2025-06-15', 'card', 'completed', 'USD'),
    (13, 16, 9.99, '2025-07-15', 'card', 'completed', 'USD'),
    (13, 16, 9.99, '2025-08-15', 'card', 'completed', 'USD'),
    (13, 16, 11.99, '2025-09-15', 'crypto', 'completed', 'USD'),
    (13, 16, 11.99, '2025-10-15', 'paypal', 'completed', 'USD'),
    (13, 16, 11.99, '2025-11-15', 'card', 'failed', 'USD'),
    (13, 16, 11.99, '2025-12-15', 'card', 'completed', 'USD'),
    (13, 16, 11.99, '2026-01-15', 'card', 'completed', 'USD'),
    (13, 16, 11.99, '2026-02-15', 'paypal', 'completed', 'USD'),
    (13, 16, 11.99, '2026-03-15', 'card', 'completed', 'USD'),
    (13, 16, 11.99, '2026-04-15', 'card', 'completed', 'USD'),
    (13, 16, 11.99, '2026-05-15', 'paypal', 'completed', 'USD'),
    (13, 16, 11.99, '2026-06-15', 'card', 'refunded', 'USD'),
    (13, 16, 11.99, '2026-07-15', 'card', 'completed', 'USD'),
    (14, 17, 15.99, '2025-02-15', 'paypal', 'completed', 'USD'),
    (14, 17, 15.99, '2025-03-15', 'crypto', 'completed', 'USD'),
    (14, 17, 15.99, '2025-04-15', 'paypal', 'completed', 'USD'),
    (14, 17, 15.99, '2025-05-15', 'paypal', 'completed', 'USD'),
    (14, 17, 15.99, '2025-06-15', 'card', 'completed', 'USD'),
    (14, 17, 15.99, '2025-07-15', 'crypto', 'completed', 'USD'),
    (14, 17, 15.99, '2025-08-15', 'card', 'completed', 'USD'),
    (14, 17, 17.99, '2025-09-15', 'card', 'completed', 'USD'),
    (14, 17, 17.99, '2025-10-15', 'card', 'refunded', 'USD'),
    (14, 17, 17.99, '2025-11-15', 'card', 'completed', 'USD'),
    (14, 17, 17.99, '2025-12-15', 'paypal', 'completed', 'USD'),
    (14, 17, 17.99, '2026-01-15', 'card', 'completed', 'USD'),
    (14, 17, 17.99, '2026-02-15', 'card', 'completed', 'USD'),
    (14, 17, 17.99, '2026-03-15', 'card', 'completed', 'USD'),
    (14, 17, 17.99, '2026-04-15', 'card', 'completed', 'USD'),
    (14, 17, 17.99, '2026-05-15', 'crypto', 'completed', 'USD'),
    (14, 17, 17.99, '2026-06-15', 'card', 'completed', 'USD'),
    (14, 17, 17.99, '2026-07-15', 'paypal', 'completed', 'USD'),
    (16, 19, 5.49, '2025-02-15', 'voucher', 'completed', 'USD'),
    (16, 19, 5.49, '2025-03-15', 'card', 'completed', 'USD'),
    (16, 19, 5.49, '2025-04-15', 'crypto', 'completed', 'USD'),
    (16, 19, 5.49, '2025-05-15', 'card', 'completed', 'USD'),
    (16, 19, 5.49, '2025-06-15', 'card', 'completed', 'USD'),
    (16, 19, 5.49, '2025-07-15', 'card', 'completed', 'USD'),
    (16, 19, 5.49, '2025-08-15', 'crypto', 'completed', 'USD'),
    (16, 19, 6.49, '2025-09-15', 'card', 'completed', 'USD'),
    (16, 19, 6.49, '2025-10-15', 'card', 'completed', 'USD'),
    (16, 19, 6.49, '2025-11-15', 'voucher', 'completed', 'USD'),
    (16, 19, 6.49, '2025-12-15', 'card', 'completed', 'USD'),
    (16, 19, 6.49, '2026-01-15', 'crypto', 'completed', 'USD'),
    (16, 19, 6.49, '2026-02-15', 'paypal', 'completed', 'USD'),
    (16, 19, 6.49, '2026-03-15', 'card', 'failed', 'USD'),
    (16, 19, 6.49, '2026-04-15', 'paypal', 'completed', 'USD'),
    (16, 19, 6.49, '2026-05-15', 'card', 'completed', 'USD'),
    (16, 19, 6.49, '2026-06-15', 'card', 'completed', 'USD'),
    (16, 19, 6.49, '2026-07-15', 'voucher', 'completed', 'USD'),
    (17, 20, 15.99, '2025-02-15', 'card', 'completed', 'USD'),
    (17, 20, 15.99, '2025-03-15', 'paypal', 'completed', 'USD'),
    (17, 20, 15.99, '2025-04-15', 'card', 'completed', 'USD'),
    (17, 20, 15.99, '2025-05-15', 'paypal', 'completed', 'USD'),
    (17, 20, 15.99, '2025-06-15', 'card', 'completed', 'USD'),
    (17, 20, 15.99, '2025-07-15', 'card', 'completed', 'USD'),
    (17, 20, 15.99, '2025-08-15', 'card', 'completed', 'USD'),
    (17, 20, 17.99, '2025-09-15', 'paypal', 'completed', 'USD'),
    (17, 20, 17.99, '2025-10-15', 'card', 'completed', 'USD'),
    (17, 20, 17.99, '2025-11-15', 'card', 'completed', 'USD'),
    (17, 20, 17.99, '2025-12-15', 'card', 'completed', 'USD'),
    (17, 20, 17.99, '2026-01-15', 'card', 'completed', 'USD'),
    (17, 20, 17.99, '2026-02-15', 'card', 'completed', 'USD'),
    (17, 20, 17.99, '2026-03-15', 'paypal', 'completed', 'USD'),
    (17, 20, 17.99, '2026-04-15', 'crypto', 'completed', 'USD'),
    (17, 20, 17.99, '2026-05-15', 'card', 'completed', 'USD'),
    (17, 20, 17.99, '2026-06-15', 'paypal', 'completed', 'USD'),
    (17, 20, 17.99, '2026-07-15', 'card', 'completed', 'USD'),
    (21, 21, 11.99, '2025-05-05', 'crypto', 'completed', 'USD'),
    (21, 21, 11.99, '2025-06-05', 'card', 'completed', 'USD'),
    (21, 21, 11.99, '2025-07-05', 'paypal', 'completed', 'USD'),
    (21, 21, 11.99, '2025-08-05', 'card', 'completed', 'USD'),
    (21, 21, 11.99, '2025-09-05', 'paypal', 'completed', 'USD'),
    (21, 21, 11.99, '2025-10-05', 'voucher', 'completed', 'USD'),
    (21, 21, 11.99, '2025-11-05', 'card', 'refunded', 'USD'),
    (21, 21, 11.99, '2025-12-05', 'crypto', 'completed', 'USD'),
    (21, 21, 11.99, '2026-01-05', 'card', 'completed', 'USD'),
    (21, 21, 11.99, '2026-02-05', 'paypal', 'completed', 'USD'),
    (21, 21, 11.99, '2026-03-05', 'voucher', 'completed', 'USD'),
    (21, 21, 11.99, '2026-04-05', 'card', 'completed', 'USD'),
    (21, 21, 11.99, '2026-05-05', 'card', 'completed', 'USD'),
    (21, 21, 11.99, '2026-06-05', 'card', 'completed', 'USD'),
    (21, 21, 11.99, '2026-07-05', 'crypto', 'completed', 'USD'),
    (23, 23, 17.99, '2025-12-04', 'card', 'completed', 'USD'),
    (23, 23, 17.99, '2026-01-04', 'voucher', 'completed', 'USD'),
    (23, 23, 17.99, '2026-02-04', 'voucher', 'completed', 'USD'),
    (23, 23, 17.99, '2026-03-04', 'paypal', 'completed', 'USD'),
    (23, 23, 17.99, '2026-04-04', 'card', 'completed', 'USD'),
    (23, 23, 17.99, '2026-05-04', 'card', 'completed', 'USD'),
    (23, 23, 17.99, '2026-06-04', 'card', 'completed', 'USD'),
    (23, 23, 17.99, '2026-07-04', 'card', 'completed', 'USD'),
    (25, 25, 6.49, '2025-08-10', 'crypto', 'completed', 'USD'),
    (25, 25, 6.49, '2025-09-10', 'crypto', 'completed', 'USD'),
    (25, 25, 6.49, '2025-10-10', 'crypto', 'completed', 'USD'),
    (25, 25, 6.49, '2025-11-10', 'card', 'refunded', 'USD'),
    (25, 25, 6.49, '2025-12-10', 'card', 'completed', 'USD'),
    (25, 25, 6.49, '2026-01-10', 'card', 'completed', 'USD'),
    (25, 25, 6.49, '2026-02-10', 'card', 'completed', 'USD'),
    (25, 25, 6.49, '2026-03-10', 'paypal', 'completed', 'USD'),
    (25, 25, 6.49, '2026-04-10', 'voucher', 'completed', 'USD'),
    (25, 25, 6.49, '2026-05-10', 'card', 'completed', 'USD'),
    (25, 25, 6.49, '2026-06-10', 'paypal', 'completed', 'USD'),
    (25, 25, 6.49, '2026-07-10', 'paypal', 'completed', 'USD'),
    (26, 26, 17.99, '2026-01-22', 'card', 'completed', 'USD'),
    (26, 26, 17.99, '2026-02-22', 'voucher', 'completed', 'USD'),
    (26, 26, 17.99, '2026-03-22', 'card', 'completed', 'USD'),
    (26, 26, 17.99, '2026-04-22', 'card', 'completed', 'USD'),
    (26, 26, 17.99, '2026-05-22', 'paypal', 'completed', 'USD'),
    (26, 26, 17.99, '2026-06-22', 'card', 'completed', 'USD'),
    (28, 28, 17.99, '2025-02-19', 'card', 'completed', 'USD'),
    (28, 28, 17.99, '2025-03-19', 'card', 'completed', 'USD'),
    (28, 28, 17.99, '2025-04-19', 'crypto', 'completed', 'USD'),
    (28, 28, 17.99, '2025-05-19', 'card', 'completed', 'USD'),
    (28, 28, 17.99, '2025-06-19', 'paypal', 'completed', 'USD'),
    (28, 28, 17.99, '2025-07-19', 'paypal', 'completed', 'USD'),
    (28, 28, 17.99, '2025-08-19', 'card', 'completed', 'USD'),
    (28, 28, 17.99, '2025-09-19', 'card', 'completed', 'USD'),
    (28, 28, 17.99, '2025-10-19', 'card', 'completed', 'USD'),
    (28, 28, 17.99, '2025-11-19', 'crypto', 'completed', 'USD'),
    (28, 28, 17.99, '2025-12-19', 'card', 'completed', 'USD'),
    (28, 28, 17.99, '2026-01-19', 'crypto', 'completed', 'USD'),
    (28, 28, 17.99, '2026-02-19', 'card', 'completed', 'USD'),
    (28, 28, 17.99, '2026-03-19', 'card', 'completed', 'USD'),
    (28, 28, 17.99, '2026-04-19', 'card', 'completed', 'USD'),
    (28, 28, 17.99, '2026-05-19', 'card', 'completed', 'USD'),
    (28, 28, 17.99, '2026-06-19', 'crypto', 'completed', 'USD'),
    (29, 29, 17.99, '2026-02-14', 'card', 'completed', 'USD'),
    (29, 29, 17.99, '2026-03-14', 'card', 'completed', 'USD'),
    (29, 29, 17.99, '2026-04-14', 'paypal', 'completed', 'USD'),
    (29, 29, 17.99, '2026-05-14', 'crypto', 'completed', 'USD'),
    (29, 29, 17.99, '2026-06-14', 'crypto', 'completed', 'USD'),
    (29, 29, 17.99, '2026-07-14', 'card', 'completed', 'USD'),
    (30, 30, 6.49, '2025-03-23', 'card', 'completed', 'USD'),
    (30, 30, 6.49, '2025-04-23', 'card', 'completed', 'USD'),
    (30, 30, 6.49, '2025-05-23', 'card', 'completed', 'USD'),
    (30, 30, 6.49, '2025-06-23', 'crypto', 'completed', 'USD'),
    (30, 30, 6.49, '2025-07-23', 'card', 'completed', 'USD'),
    (30, 30, 6.49, '2025-08-23', 'paypal', 'completed', 'USD'),
    (30, 30, 6.49, '2025-09-23', 'paypal', 'completed', 'USD'),
    (30, 30, 6.49, '2025-10-23', 'card', 'completed', 'USD'),
    (30, 30, 6.49, '2025-11-23', 'crypto', 'failed', 'USD'),
    (30, 30, 6.49, '2025-12-23', 'card', 'completed', 'USD'),
    (30, 30, 6.49, '2026-01-23', 'card', 'completed', 'USD'),
    (30, 30, 6.49, '2026-02-23', 'card', 'completed', 'USD'),
    (30, 30, 6.49, '2026-03-23', 'card', 'completed', 'USD'),
    (30, 30, 6.49, '2026-04-23', 'voucher', 'completed', 'USD'),
    (30, 30, 6.49, '2026-05-23', 'card', 'completed', 'USD'),
    (30, 30, 6.49, '2026-06-23', 'crypto', 'completed', 'USD'),
    (31, 31, 6.49, '2026-04-14', 'card', 'completed', 'USD'),
    (31, 31, 6.49, '2026-05-14', 'crypto', 'completed', 'USD'),
    (31, 31, 6.49, '2026-06-14', 'card', 'completed', 'USD'),
    (31, 31, 6.49, '2026-07-14', 'card', 'completed', 'USD'),
    (32, 32, 6.49, '2026-04-06', 'card', 'completed', 'USD'),
    (32, 32, 6.49, '2026-05-06', 'card', 'completed', 'USD'),
    (32, 32, 6.49, '2026-06-06', 'card', 'completed', 'USD'),
    (32, 32, 6.49, '2026-07-06', 'card', 'completed', 'USD'),
    (34, 34, 11.99, '2025-03-16', 'card', 'completed', 'USD'),
    (34, 34, 11.99, '2025-04-16', 'paypal', 'completed', 'USD'),
    (34, 34, 11.99, '2025-05-16', 'paypal', 'completed', 'USD'),
    (34, 34, 11.99, '2025-06-16', 'paypal', 'completed', 'USD'),
    (34, 34, 11.99, '2025-07-16', 'card', 'completed', 'USD'),
    (34, 34, 11.99, '2025-08-16', 'card', 'completed', 'USD'),
    (34, 34, 11.99, '2025-09-16', 'paypal', 'completed', 'USD'),
    (34, 34, 11.99, '2025-10-16', 'card', 'failed', 'USD'),
    (34, 34, 11.99, '2025-11-16', 'card', 'completed', 'USD'),
    (34, 34, 11.99, '2025-12-16', 'card', 'completed', 'USD'),
    (34, 34, 11.99, '2026-01-16', 'card', 'completed', 'USD'),
    (34, 34, 11.99, '2026-02-16', 'card', 'completed', 'USD'),
    (34, 34, 11.99, '2026-03-16', 'paypal', 'completed', 'USD'),
    (34, 34, 11.99, '2026-04-16', 'voucher', 'completed', 'USD'),
    (34, 34, 11.99, '2026-05-16', 'voucher', 'completed', 'USD'),
    (34, 34, 11.99, '2026-06-16', 'card', 'completed', 'USD'),
    (34, 34, 11.99, '2026-07-16', 'card', 'completed', 'USD'),
    (35, 35, 11.99, '2025-08-28', 'crypto', 'completed', 'USD'),
    (35, 35, 11.99, '2025-09-28', 'card', 'completed', 'USD'),
    (35, 35, 11.99, '2025-10-28', 'card', 'completed', 'USD'),
    (35, 35, 11.99, '2025-11-28', 'card', 'completed', 'USD'),
    (35, 35, 11.99, '2025-12-28', 'paypal', 'completed', 'USD'),
    (35, 35, 11.99, '2026-01-28', 'card', 'completed', 'USD'),
    (35, 35, 11.99, '2026-02-28', 'card', 'completed', 'USD'),
    (35, 35, 11.99, '2026-03-28', 'paypal', 'completed', 'USD'),
    (35, 35, 11.99, '2026-04-28', 'card', 'completed', 'USD'),
    (35, 35, 11.99, '2026-05-28', 'card', 'completed', 'USD'),
    (35, 35, 11.99, '2026-06-28', 'card', 'completed', 'USD'),
    (36, 36, 11.99, '2025-10-24', 'paypal', 'completed', 'USD'),
    (36, 36, 11.99, '2025-11-24', 'card', 'completed', 'USD'),
    (36, 36, 11.99, '2025-12-24', 'card', 'completed', 'USD'),
    (36, 36, 11.99, '2026-01-24', 'card', 'completed', 'USD'),
    (36, 36, 11.99, '2026-02-24', 'card', 'completed', 'USD'),
    (36, 36, 11.99, '2026-03-24', 'voucher', 'completed', 'USD'),
    (36, 36, 11.99, '2026-04-24', 'card', 'completed', 'USD'),
    (36, 36, 11.99, '2026-05-24', 'card', 'completed', 'USD'),
    (36, 36, 11.99, '2026-06-24', 'card', 'completed', 'USD'),
    (37, 37, 17.99, '2025-11-01', 'card', 'completed', 'USD'),
    (37, 37, 17.99, '2025-12-01', 'card', 'completed', 'USD'),
    (37, 37, 17.99, '2026-01-01', 'card', 'completed', 'USD'),
    (37, 37, 17.99, '2026-02-01', 'card', 'completed', 'USD'),
    (37, 37, 17.99, '2026-03-01', 'card', 'completed', 'USD'),
    (37, 37, 17.99, '2026-04-01', 'card', 'completed', 'USD'),
    (37, 37, 17.99, '2026-05-01', 'voucher', 'completed', 'USD'),
    (37, 37, 17.99, '2026-06-01', 'paypal', 'completed', 'USD'),
    (37, 37, 17.99, '2026-07-01', 'card', 'completed', 'USD'),
    (38, 38, 11.99, '2025-09-24', 'card', 'completed', 'USD'),
    (38, 38, 11.99, '2025-10-24', 'paypal', 'refunded', 'USD'),
    (38, 38, 11.99, '2025-11-24', 'paypal', 'completed', 'USD'),
    (38, 38, 11.99, '2025-12-24', 'card', 'completed', 'USD'),
    (38, 38, 11.99, '2026-01-24', 'card', 'completed', 'USD'),
    (38, 38, 11.99, '2026-02-24', 'voucher', 'completed', 'USD'),
    (38, 38, 11.99, '2026-03-24', 'crypto', 'completed', 'USD'),
    (38, 38, 11.99, '2026-04-24', 'card', 'completed', 'USD'),
    (38, 38, 11.99, '2026-05-24', 'crypto', 'completed', 'USD'),
    (38, 38, 11.99, '2026-06-24', 'card', 'completed', 'USD'),
    (39, 39, 11.99, '2026-01-08', 'voucher', 'completed', 'USD'),
    (39, 39, 11.99, '2026-02-08', 'card', 'completed', 'USD'),
    (39, 39, 11.99, '2026-03-08', 'voucher', 'completed', 'USD'),
    (39, 39, 11.99, '2026-04-08', 'card', 'completed', 'USD'),
    (39, 39, 11.99, '2026-05-08', 'card', 'completed', 'USD'),
    (39, 39, 11.99, '2026-06-08', 'card', 'completed', 'USD'),
    (39, 39, 11.99, '2026-07-08', 'paypal', 'completed', 'USD');


-- 6. play events [EC-02 event_type, EC-03 playlist_id NULL]

INSERT INTO play_events
    (user_id, track_id, playlist_id, event_type, played_at,
     trk_position_ms, duration_ms, country_code, device_type)
VALUES
    (21, 8, 11, 'skip', '2025-01-30 14:45:00', 5487, 5487, 'ES', 'mobile'),
    (3, 19, 1, 'play', '2025-01-29 13:00:00', 0, 143432, 'MX', 'mobile'),
    (23, 9, 16, 'save', '2025-01-22 18:45:00', 0, 226012, 'BR', 'mobile'),
    (37, 22, NULL, 'play', '2025-01-29 20:45:00', 0, 136042, 'JP', 'mobile'),
    (18, 5, 16, 'play', '2025-01-29 16:15:00', 0, 129429, 'MX', 'mobile'),
    (29, 28, 7, 'play', '2025-01-27 21:00:00', 0, 136286, 'ES', 'mobile'),
    (6, 28, NULL, 'play', '2025-01-27 17:30:00', 0, 137414, 'US', 'desktop'),
    (26, 15, 5, 'play', '2025-01-25 09:45:00', 0, 151942, 'GB', 'mobile'),
    (19, 13, 11, 'play', '2025-01-23 22:45:00', 0, 207915, 'BR', 'smart_tv'),
    (16, 1, 6, 'play', '2025-01-26 21:15:00', 0, 186858, 'AU', 'mobile'),
    (26, 4, 16, 'play', '2025-01-28 10:15:00', 0, 156421, 'MX', 'desktop'),
    (19, 24, 1, 'share', '2025-01-28 19:45:00', 0, 134330, 'GB', 'desktop'),
    (39, 2, 12, 'save', '2025-01-24 23:00:00', 0, 124800, 'US', 'desktop'),
    (36, 19, 6, 'skip', '2025-01-27 20:00:00', 15373, 15373, 'KR', 'mobile'),
    (20, 10, NULL, 'play', '2025-01-22 07:30:00', 0, 164773, 'US', 'other'),
    (2, 5, NULL, 'play', '2025-01-30 18:00:00', 0, 136384, 'JP', 'desktop'),
    (26, 1, 4, 'save', '2025-01-26 20:30:00', 0, 171937, 'MX', 'desktop'),
    (25, 13, 12, 'skip', '2025-01-28 21:45:00', 25640, 25640, 'CO', 'mobile'),
    (29, 6, NULL, 'play', '2025-01-25 13:30:00', 0, 133666, 'KR', 'tablet'),
    (34, 21, NULL, 'play', '2025-01-21 18:15:00', 0, 138556, 'CA', 'mobile'),
    (25, 5, NULL, 'play', '2025-01-23 20:30:00', 0, 202489, 'GB', 'mobile'),
    (13, 1, 13, 'save', '2025-01-22 08:00:00', 0, 171609, 'MX', 'mobile'),
    (15, 18, NULL, 'play', '2025-01-26 17:30:00', 0, 142182, 'BR', 'mobile'),
    (32, 20, NULL, 'play', '2025-01-30 16:15:00', 0, 128026, 'KR', 'tablet'),
    (28, 4, 8, 'play', '2025-01-23 13:00:00', 0, 167634, 'KR', 'mobile'),
    (33, 20, 2, 'play', '2025-01-29 15:15:00', 0, 208106, 'JP', 'mobile'),
    (4, 14, 18, 'save', '2025-01-28 10:00:00', 0, 134865, 'GB', 'desktop'),
    (35, 11, 7, 'save', '2025-01-28 16:45:00', 0, 233794, 'KR', 'other'),
    (32, 3, 15, 'skip', '2025-01-22 14:45:00', 3720, 3720, 'CO', 'mobile'),
    (28, 27, 17, 'play', '2025-01-29 19:00:00', 0, 176168, 'GB', 'desktop'),
    (32, 29, NULL, 'skip', '2025-01-29 22:15:00', 20291, 20291, 'CO', 'tablet'),
    (24, 19, NULL, 'play', '2025-01-21 08:00:00', 0, 158526, 'JP', 'desktop'),
    (14, 4, 1, 'play', '2025-01-25 06:15:00', 0, 146184, 'IT', 'desktop'),
    (38, 8, 6, 'play', '2025-01-24 16:00:00', 0, 207979, 'US', 'other'),
    (31, 26, 12, 'play', '2025-01-25 08:15:00', 0, 165635, 'US', 'smart_tv'),
    (11, 28, 6, 'play', '2025-01-30 16:00:00', 0, 195807, 'ES', 'mobile'),
    (28, 13, 10, 'play', '2025-01-31 11:00:00', 0, 214061, 'KR', 'tablet'),
    (36, 25, 10, 'play', '2025-01-27 10:15:00', 0, 136458, 'AU', 'tablet'),
    (3, 13, NULL, 'play', '2025-01-31 10:15:00', 0, 298595, 'GB', 'tablet'),
    (35, 12, NULL, 'play', '2025-02-02 07:00:00', 0, 173941, 'IT', 'mobile'),
    (5, 8, 6, 'share', '2025-02-16 13:15:00', 0, 197197, 'US', 'other'),
    (17, 10, NULL, 'play', '2025-02-03 07:30:00', 0, 130762, 'KR', 'other'),
    (23, 29, 9, 'play', '2025-02-20 19:00:00', 0, 160785, 'CO', 'mobile'),
    (28, 20, NULL, 'play', '2025-02-23 17:00:00', 0, 217626, 'AU', 'desktop'),
    (3, 9, 12, 'play', '2025-02-13 15:00:00', 0, 180945, 'ES', 'mobile'),
    (40, 11, 13, 'play', '2025-02-22 19:45:00', 0, 161950, 'US', 'other'),
    (25, 19, 6, 'play', '2025-02-20 21:30:00', 0, 114688, 'GB', 'desktop'),
    (22, 19, 16, 'save', '2025-02-02 19:00:00', 0, 123113, 'CO', 'mobile'),
    (9, 10, 13, 'play', '2025-02-20 19:00:00', 0, 121663, 'ES', 'mobile'),
    (37, 17, 1, 'play', '2025-02-10 21:15:00', 0, 312863, 'ES', 'desktop'),
    (20, 29, 15, 'share', '2025-02-23 15:15:00', 0, 104349, 'IT', 'other'),
    (2, 15, 5, 'play', '2025-02-09 16:15:00', 0, 146010, 'US', 'desktop'),
    (30, 15, 18, 'play', '2025-02-08 11:15:00', 0, 120383, 'BR', 'smart_tv'),
    (3, 2, 11, 'share', '2025-02-02 15:45:00', 0, 205597, 'US', 'tablet'),
    (38, 22, NULL, 'play', '2025-02-07 18:00:00', 0, 203244, 'US', 'mobile'),
    (39, 1, 3, 'play', '2025-02-07 15:00:00', 0, 121175, 'GB', 'desktop'),
    (29, 5, 18, 'skip', '2025-02-27 09:30:00', 8618, 8618, 'CA', 'mobile'),
    (27, 25, NULL, 'play', '2025-02-11 13:15:00', 0, 216420, 'IT', 'mobile'),
    (3, 8, 15, 'skip', '2025-02-02 10:00:00', 26909, 26909, 'KR', 'other'),
    (32, 19, 14, 'play', '2025-02-25 07:30:00', 0, 122159, 'KR', 'mobile'),
    (27, 4, 6, 'play', '2025-02-01 13:45:00', 0, 144480, 'ES', 'mobile'),
    (40, 14, 6, 'play', '2025-02-25 14:30:00', 0, 165665, 'KR', 'mobile'),
    (31, 8, 18, 'play', '2025-02-17 21:00:00', 0, 217172, 'CO', 'other'),
    (6, 11, 9, 'play', '2025-02-04 06:15:00', 0, 217857, 'BR', 'tablet'),
    (10, 6, 11, 'play', '2025-02-06 22:00:00', 0, 139896, 'CO', 'mobile'),
    (3, 12, 1, 'play', '2025-02-04 15:15:00', 0, 150770, 'JP', 'desktop'),
    (23, 29, 16, 'share', '2025-02-08 22:30:00', 0, 137626, 'ES', 'tablet'),
    (15, 11, NULL, 'play', '2025-02-20 12:45:00', 0, 176094, 'US', 'tablet'),
    (14, 18, 7, 'play', '2025-02-18 14:45:00', 0, 172510, 'KR', 'smart_tv'),
    (16, 7, 14, 'play', '2025-02-13 22:45:00', 0, 140761, 'US', 'mobile'),
    (10, 16, NULL, 'play', '2025-02-07 12:15:00', 0, 184042, 'CA', 'desktop'),
    (21, 4, 16, 'play', '2025-02-11 13:15:00', 0, 125518, 'BR', 'desktop'),
    (9, 8, 17, 'skip', '2025-02-28 12:00:00', 10923, 10923, 'IT', 'tablet'),
    (37, 30, 11, 'play', '2025-02-27 12:00:00', 0, 103619, 'US', 'mobile'),
    (25, 19, 17, 'play', '2025-02-23 12:00:00', 0, 129666, 'CO', 'smart_tv'),
    (1, 2, 8, 'play', '2025-02-26 16:45:00', 0, 173758, 'US', 'other'),
    (4, 26, NULL, 'skip', '2025-02-15 22:30:00', 3108, 3108, 'CA', 'tablet'),
    (24, 21, 18, 'play', '2025-02-18 09:30:00', 0, 137185, 'AU', 'mobile'),
    (28, 4, 17, 'share', '2025-02-13 15:30:00', 0, 171510, 'IT', 'tablet'),
    (36, 30, 11, 'play', '2025-02-26 23:15:00', 0, 141691, 'KR', 'desktop'),
    (3, 4, 1, 'play', '2025-02-06 08:30:00', 0, 160356, 'US', 'tablet'),
    (18, 20, 10, 'play', '2025-03-05 20:45:00', 0, 128867, 'US', 'mobile'),
    (37, 27, 15, 'play', '2025-03-02 11:00:00', 0, 185928, 'KR', 'mobile'),
    (19, 23, 18, 'play', '2025-03-29 19:00:00', 0, 113424, 'MX', 'mobile'),
    (4, 6, 3, 'play', '2025-03-10 13:00:00', 0, 171548, 'CO', 'mobile'),
    (30, 1, 3, 'play', '2025-03-16 08:45:00', 0, 137618, 'KR', 'smart_tv'),
    (15, 32, 18, 'skip', '2025-03-21 21:45:00', 21062, 21062, 'AU', 'desktop'),
    (11, 27, 9, 'play', '2025-03-08 19:00:00', 0, 177118, 'GB', 'smart_tv'),
    (1, 17, 4, 'save', '2025-03-23 21:45:00', 0, 203602, 'US', 'smart_tv'),
    (20, 10, 12, 'play', '2025-03-10 11:30:00', 0, 154476, 'US', 'other'),
    (26, 19, 10, 'play', '2025-03-15 06:30:00', 0, 175465, 'GB', 'mobile'),
    (28, 2, NULL, 'play', '2025-03-01 22:00:00', 0, 180049, 'AU', 'mobile'),
    (37, 34, NULL, 'share', '2025-03-15 16:15:00', 0, 181788, 'KR', 'other'),
    (36, 17, 11, 'play', '2025-03-06 21:00:00', 0, 315349, 'BR', 'other'),
    (11, 19, 17, 'play', '2025-03-05 07:45:00', 0, 114963, 'JP', 'mobile'),
    (34, 10, NULL, 'play', '2025-03-07 11:15:00', 0, 110949, 'KR', 'mobile'),
    (27, 15, 12, 'play', '2025-03-11 20:15:00', 0, 130086, 'US', 'other'),
    (37, 33, 13, 'play', '2025-03-30 23:30:00', 0, 142322, 'ES', 'mobile'),
    (35, 9, 12, 'play', '2025-03-12 08:45:00', 0, 191020, 'ES', 'mobile'),
    (38, 30, 1, 'skip', '2025-03-19 15:45:00', 21897, 21897, 'ES', 'tablet'),
    (39, 2, 10, 'play', '2025-03-04 06:45:00', 0, 161084, 'KR', 'mobile'),
    (34, 10, 15, 'skip', '2025-03-31 23:00:00', 15955, 15955, 'CO', 'tablet'),
    (2, 1, NULL, 'play', '2025-03-30 17:00:00', 0, 169333, 'ES', 'mobile'),
    (30, 18, 5, 'play', '2025-03-10 10:45:00', 0, 115841, 'US', 'tablet'),
    (37, 1, NULL, 'play', '2025-03-01 17:30:00', 0, 137001, 'US', 'mobile'),
    (40, 13, 12, 'share', '2025-03-07 22:00:00', 0, 202881, 'US', 'mobile'),
    (1, 33, 17, 'share', '2025-03-29 19:15:00', 0, 126756, 'AU', 'smart_tv'),
    (4, 28, 11, 'play', '2025-03-11 08:15:00', 0, 130919, 'BR', 'other'),
    (20, 9, 14, 'share', '2025-03-29 15:15:00', 0, 173609, 'AU', 'mobile'),
    (4, 11, 3, 'play', '2025-03-07 15:30:00', 0, 200986, 'JP', 'mobile'),
    (31, 15, NULL, 'play', '2025-03-09 11:00:00', 0, 118344, 'CO', 'other'),
    (34, 2, 1, 'play', '2025-03-22 15:30:00', 0, 191265, 'ES', 'desktop'),
    (5, 30, 15, 'play', '2025-03-01 19:45:00', 0, 128779, 'US', 'desktop'),
    (29, 32, 8, 'play', '2025-03-15 23:30:00', 0, 182488, 'US', 'other'),
    (2, 16, 12, 'play', '2025-03-23 08:45:00', 0, 205544, 'IT', 'mobile'),
    (15, 29, 8, 'play', '2025-03-15 16:45:00', 0, 172638, 'JP', 'desktop'),
    (24, 21, 16, 'skip', '2025-03-24 20:15:00', 16707, 16707, 'IT', 'mobile'),
    (29, 27, 7, 'play', '2025-03-04 11:30:00', 0, 181298, 'CO', 'smart_tv'),
    (13, 17, 13, 'play', '2025-03-24 16:15:00', 0, 189444, 'MX', 'mobile'),
    (3, 6, 18, 'play', '2025-04-14 10:45:00', 0, 164301, 'CA', 'other'),
    (1, 32, 12, 'play', '2025-04-01 11:15:00', 0, 174051, 'BR', 'mobile'),
    (27, 6, 8, 'play', '2025-04-01 18:45:00', 0, 140569, 'GB', 'smart_tv'),
    (25, 10, NULL, 'play', '2025-04-18 08:45:00', 0, 140636, 'US', 'smart_tv'),
    (13, 32, 15, 'play', '2025-04-06 08:00:00', 0, 190521, 'CA', 'desktop'),
    (16, 12, 18, 'play', '2025-04-30 14:15:00', 0, 126830, 'GB', 'tablet'),
    (17, 1, 16, 'play', '2025-04-10 09:15:00', 0, 179154, 'US', 'mobile'),
    (27, 5, 11, 'play', '2025-04-16 10:15:00', 0, 116891, 'AU', 'smart_tv'),
    (11, 7, 16, 'play', '2025-04-03 17:45:00', 0, 165181, 'JP', 'mobile'),
    (13, 7, 1, 'skip', '2025-04-26 13:15:00', 20539, 20539, 'US', 'mobile'),
    (21, 26, NULL, 'play', '2025-04-05 15:15:00', 0, 115655, 'AU', 'mobile'),
    (19, 14, NULL, 'play', '2025-04-09 23:45:00', 0, 144905, 'GB', 'other'),
    (36, 33, 3, 'skip', '2025-04-11 17:30:00', 7639, 7639, 'GB', 'smart_tv'),
    (21, 16, NULL, 'save', '2025-04-25 21:15:00', 0, 207049, 'US', 'mobile'),
    (32, 34, 8, 'play', '2025-04-11 10:00:00', 0, 206116, 'US', 'other'),
    (27, 1, 4, 'play', '2025-04-17 21:45:00', 0, 184258, 'CO', 'desktop'),
    (14, 2, NULL, 'play', '2025-04-26 23:30:00', 0, 201118, 'US', 'mobile'),
    (26, 9, 18, 'play', '2025-04-29 13:15:00', 0, 246476, 'JP', 'desktop'),
    (25, 9, 16, 'play', '2025-04-13 20:30:00', 0, 242805, 'IT', 'other'),
    (5, 15, 17, 'play', '2025-04-04 19:15:00', 0, 133524, 'GB', 'mobile'),
    (35, 28, NULL, 'play', '2025-04-20 09:45:00', 0, 188039, 'KR', 'desktop'),
    (10, 14, 11, 'play', '2025-04-08 22:30:00', 0, 164828, 'US', 'smart_tv'),
    (9, 25, 12, 'play', '2025-04-03 09:45:00', 0, 189792, 'IT', 'mobile'),
    (20, 19, 16, 'save', '2025-04-05 16:15:00', 0, 148455, 'IT', 'desktop'),
    (27, 2, 16, 'play', '2025-04-13 07:15:00', 0, 179651, 'GB', 'tablet'),
    (6, 1, NULL, 'skip', '2025-04-18 15:15:00', 24167, 24167, 'CO', 'mobile'),
    (27, 10, NULL, 'share', '2025-04-18 09:00:00', 0, 138841, 'CA', 'other'),
    (1, 26, 3, 'play', '2025-04-25 20:00:00', 0, 98199, 'US', 'desktop'),
    (33, 28, NULL, 'play', '2025-04-25 10:30:00', 0, 115172, 'IT', 'mobile'),
    (10, 26, NULL, 'play', '2025-04-24 18:45:00', 0, 116648, 'GB', 'other'),
    (1, 14, 11, 'skip', '2025-04-28 11:45:00', 23509, 23509, 'ES', 'tablet'),
    (16, 5, 6, 'share', '2025-04-30 09:45:00', 0, 116052, 'MX', 'smart_tv'),
    (33, 20, 9, 'play', '2025-04-23 15:30:00', 0, 188277, 'US', 'mobile'),
    (26, 3, NULL, 'play', '2025-04-27 20:30:00', 0, 186968, 'ES', 'mobile'),
    (34, 18, 14, 'play', '2025-04-24 22:30:00', 0, 139212, 'KR', 'mobile'),
    (21, 27, NULL, 'play', '2025-04-25 23:15:00', 0, 135575, 'US', 'tablet'),
    (30, 23, NULL, 'save', '2025-04-11 13:00:00', 0, 134990, 'JP', 'mobile'),
    (19, 4, 17, 'play', '2025-04-02 20:30:00', 0, 190410, 'ES', 'smart_tv'),
    (4, 32, 9, 'skip', '2025-04-19 12:45:00', 29450, 29450, 'MX', 'mobile'),
    (23, 29, NULL, 'play', '2025-04-09 06:00:00', 0, 105572, 'US', 'tablet'),
    (25, 11, 2, 'play', '2025-04-06 12:30:00', 0, 210731, 'IT', 'tablet'),
    (39, 13, 3, 'skip', '2025-04-09 06:15:00', 18303, 18303, 'ES', 'tablet'),
    (24, 10, 7, 'skip', '2025-05-14 06:30:00', 26351, 26351, 'JP', 'mobile'),
    (40, 13, 6, 'play', '2025-05-23 11:00:00', 0, 225734, 'US', 'mobile'),
    (38, 23, 18, 'play', '2025-05-29 17:45:00', 0, 177392, 'KR', 'mobile'),
    (4, 5, NULL, 'play', '2025-05-08 08:30:00', 0, 171985, 'JP', 'desktop'),
    (23, 3, NULL, 'skip', '2025-05-28 21:15:00', 29062, 29062, 'CA', 'tablet'),
    (33, 30, 12, 'play', '2025-05-05 14:30:00', 0, 119071, 'US', 'mobile'),
    (11, 33, NULL, 'play', '2025-05-14 19:00:00', 0, 202868, 'US', 'other'),
    (10, 14, 7, 'play', '2025-05-12 11:00:00', 0, 158697, 'IT', 'mobile'),
    (16, 32, NULL, 'save', '2025-05-14 13:30:00', 0, 152241, 'JP', 'mobile'),
    (14, 21, NULL, 'play', '2025-05-09 20:00:00', 0, 146939, 'US', 'desktop'),
    (2, 30, 16, 'share', '2025-05-01 23:00:00', 0, 111698, 'US', 'mobile'),
    (21, 1, 9, 'play', '2025-05-18 09:45:00', 0, 117944, 'CO', 'mobile'),
    (29, 7, 15, 'play', '2025-05-21 08:30:00', 0, 191871, 'JP', 'other'),
    (26, 3, NULL, 'play', '2025-05-29 09:00:00', 0, 206271, 'CA', 'desktop'),
    (26, 28, NULL, 'skip', '2025-05-06 08:00:00', 19973, 19973, 'CA', 'mobile'),
    (35, 5, 15, 'share', '2025-05-02 07:15:00', 0, 158433, 'US', 'desktop'),
    (36, 12, NULL, 'play', '2025-05-13 11:15:00', 0, 162374, 'US', 'other'),
    (33, 17, 10, 'play', '2025-05-08 23:30:00', 0, 282220, 'CO', 'tablet'),
    (32, 34, 6, 'play', '2025-05-06 17:15:00', 0, 140486, 'CA', 'mobile'),
    (31, 15, 16, 'play', '2025-05-01 14:30:00', 0, 149040, 'AU', 'mobile'),
    (2, 34, 18, 'play', '2025-05-26 20:15:00', 0, 211107, 'AU', 'tablet'),
    (33, 19, 16, 'skip', '2025-05-28 20:30:00', 12539, 12539, 'ES', 'mobile'),
    (35, 32, NULL, 'play', '2025-05-13 16:00:00', 0, 139815, 'CA', 'tablet'),
    (16, 31, NULL, 'play', '2025-05-30 23:00:00', 0, 208244, 'IT', 'other'),
    (10, 17, 4, 'play', '2025-05-27 15:15:00', 0, 280760, 'MX', 'smart_tv'),
    (3, 1, NULL, 'play', '2025-05-24 22:45:00', 0, 120295, 'GB', 'mobile'),
    (28, 4, NULL, 'share', '2025-05-31 22:30:00', 0, 116493, 'US', 'mobile'),
    (3, 30, NULL, 'play', '2025-05-04 09:30:00', 0, 136668, 'ES', 'tablet'),
    (23, 11, NULL, 'play', '2025-05-28 14:45:00', 0, 211754, 'ES', 'mobile'),
    (34, 10, NULL, 'play', '2025-05-25 23:15:00', 0, 113047, 'IT', 'mobile'),
    (21, 31, 4, 'play', '2025-05-13 14:15:00', 0, 196867, 'BR', 'mobile'),
    (32, 29, 14, 'play', '2025-05-04 08:30:00', 0, 150580, 'BR', 'other'),
    (2, 6, NULL, 'play', '2025-05-04 14:30:00', 0, 153846, 'US', 'smart_tv'),
    (33, 2, 3, 'play', '2025-05-31 19:30:00', 0, 136731, 'JP', 'other'),
    (10, 2, NULL, 'play', '2025-05-16 20:15:00', 0, 152211, 'CO', 'mobile'),
    (13, 19, 2, 'play', '2025-05-27 09:00:00', 0, 129903, 'US', 'smart_tv'),
    (32, 25, 9, 'play', '2025-05-11 11:00:00', 0, 187135, 'MX', 'smart_tv'),
    (40, 9, 1, 'play', '2025-05-19 09:30:00', 0, 220199, 'BR', 'other'),
    (40, 11, 6, 'play', '2025-05-16 19:30:00', 0, 261334, 'AU', 'tablet'),
    (4, 31, NULL, 'play', '2025-05-30 15:45:00', 0, 132794, 'KR', 'tablet'),
    (37, 1, 11, 'skip', '2025-05-03 11:15:00', 29053, 29053, 'US', 'desktop'),
    (17, 8, 14, 'share', '2025-05-29 15:30:00', 0, 203719, 'CO', 'mobile'),
    (14, 29, NULL, 'play', '2025-05-15 08:45:00', 0, 121259, 'CO', 'desktop'),
    (40, 21, NULL, 'skip', '2025-05-22 18:15:00', 21145, 21145, 'CA', 'smart_tv'),
    (33, 10, 16, 'play', '2025-05-24 07:45:00', 0, 130066, 'US', 'desktop'),
    (23, 13, 13, 'play', '2025-05-02 20:45:00', 0, 215943, 'IT', 'other'),
    (38, 25, NULL, 'skip', '2025-06-08 09:30:00', 18498, 18498, 'ES', 'mobile'),
    (25, 32, 11, 'play', '2025-06-23 21:15:00', 0, 148022, 'AU', 'mobile'),
    (36, 21, NULL, 'skip', '2025-06-15 16:15:00', 29892, 29892, 'KR', 'mobile'),
    (35, 13, 9, 'skip', '2025-06-24 10:00:00', 20034, 20034, 'MX', 'desktop'),
    (10, 26, 12, 'skip', '2025-06-30 11:45:00', 26057, 26057, 'AU', 'desktop'),
    (9, 11, 1, 'save', '2025-06-22 15:45:00', 0, 160883, 'AU', 'mobile'),
    (16, 15, NULL, 'play', '2025-06-30 22:45:00', 0, 113987, 'ES', 'other'),
    (38, 30, NULL, 'play', '2025-06-10 17:45:00', 0, 171760, 'CO', 'mobile'),
    (16, 1, 16, 'play', '2025-06-14 19:15:00', 0, 116437, 'BR', 'mobile'),
    (6, 18, NULL, 'play', '2025-06-10 15:45:00', 0, 183814, 'CO', 'tablet'),
    (35, 19, 10, 'play', '2025-06-25 09:30:00', 0, 118643, 'ES', 'desktop'),
    (31, 2, NULL, 'skip', '2025-06-10 23:30:00', 3208, 3208, 'GB', 'other'),
    (38, 1, 1, 'save', '2025-06-22 12:30:00', 0, 175729, 'KR', 'other'),
    (35, 32, NULL, 'play', '2025-06-02 14:00:00', 0, 117486, 'GB', 'desktop'),
    (6, 6, NULL, 'play', '2025-06-04 08:15:00', 0, 120592, 'ES', 'desktop'),
    (35, 17, NULL, 'play', '2025-06-25 14:30:00', 0, 191983, 'IT', 'tablet'),
    (36, 7, 2, 'skip', '2025-06-19 19:45:00', 22174, 22174, 'US', 'mobile'),
    (29, 4, NULL, 'play', '2025-06-15 13:30:00', 0, 125104, 'US', 'desktop'),
    (19, 3, NULL, 'play', '2025-06-25 22:00:00', 0, 132336, 'KR', 'other'),
    (31, 28, 10, 'play', '2025-06-08 16:30:00', 0, 198969, 'US', 'other'),
    (17, 3, 15, 'play', '2025-06-06 16:15:00', 0, 151929, 'IT', 'mobile'),
    (15, 17, 5, 'play', '2025-06-26 19:15:00', 0, 222020, 'KR', 'desktop'),
    (29, 5, 9, 'play', '2025-06-28 07:45:00', 0, 200387, 'IT', 'smart_tv'),
    (25, 21, 8, 'play', '2025-06-01 14:15:00', 0, 195519, 'AU', 'smart_tv'),
    (24, 13, 17, 'play', '2025-06-01 20:45:00', 0, 252846, 'KR', 'smart_tv'),
    (37, 5, 14, 'play', '2025-06-03 23:30:00', 0, 142681, 'AU', 'smart_tv'),
    (38, 2, 2, 'play', '2025-06-23 22:15:00', 0, 169807, 'MX', 'tablet'),
    (25, 8, 10, 'play', '2025-06-16 18:45:00', 0, 146107, 'MX', 'mobile'),
    (38, 7, 7, 'play', '2025-06-04 09:15:00', 0, 147203, 'CA', 'desktop'),
    (16, 33, 7, 'play', '2025-06-21 15:45:00', 0, 128905, 'CA', 'desktop'),
    (32, 21, NULL, 'play', '2025-06-20 21:15:00', 0, 134770, 'CO', 'tablet'),
    (28, 20, 12, 'play', '2025-06-20 06:45:00', 0, 189352, 'US', 'desktop'),
    (17, 19, NULL, 'save', '2025-06-17 17:45:00', 0, 164666, 'AU', 'mobile'),
    (6, 14, NULL, 'save', '2025-06-02 15:15:00', 0, 202019, 'CO', 'other'),
    (6, 19, NULL, 'skip', '2025-06-01 07:15:00', 25361, 25361, 'US', 'mobile'),
    (13, 2, NULL, 'save', '2025-06-24 20:30:00', 0, 181577, 'KR', 'mobile'),
    (20, 14, 8, 'play', '2025-06-19 22:00:00', 0, 121485, 'US', 'desktop'),
    (31, 9, NULL, 'play', '2025-06-05 21:15:00', 0, 184559, 'CO', 'smart_tv'),
    (32, 14, NULL, 'play', '2025-06-21 22:15:00', 0, 171152, 'JP', 'desktop'),
    (29, 3, 4, 'play', '2025-06-01 21:45:00', 0, 218915, 'CA', 'desktop'),
    (15, 16, NULL, 'play', '2025-06-18 11:15:00', 0, 169446, 'KR', 'mobile'),
    (3, 31, NULL, 'play', '2025-06-11 17:30:00', 0, 204961, 'CO', 'desktop'),
    (3, 12, 6, 'play', '2025-06-24 22:45:00', 0, 224166, 'US', 'desktop'),
    (9, 20, NULL, 'play', '2025-06-22 13:15:00', 0, 179275, 'JP', 'other'),
    (36, 3, 9, 'play', '2025-06-15 23:30:00', 0, 197683, 'US', 'desktop'),
    (21, 25, NULL, 'skip', '2025-06-18 20:30:00', 16156, 16156, 'AU', 'other'),
    (23, 4, 6, 'play', '2025-07-11 12:15:00', 0, 151129, 'US', 'mobile'),
    (6, 4, NULL, 'play', '2025-07-05 13:45:00', 0, 153415, 'IT', 'tablet'),
    (31, 32, 4, 'play', '2025-07-11 14:15:00', 0, 116946, 'US', 'desktop'),
    (32, 6, 5, 'skip', '2025-07-15 16:00:00', 6065, 6065, 'ES', 'mobile'),
    (19, 1, 12, 'play', '2025-07-04 18:45:00', 0, 145325, 'CO', 'desktop'),
    (24, 33, 2, 'skip', '2025-07-28 21:30:00', 8439, 8439, 'AU', 'tablet'),
    (40, 13, 3, 'play', '2025-07-26 17:00:00', 0, 205566, 'BR', 'mobile'),
    (18, 30, NULL, 'play', '2025-07-10 10:00:00', 0, 143243, 'MX', 'mobile'),
    (38, 31, NULL, 'play', '2025-07-20 12:45:00', 0, 118160, 'CA', 'mobile'),
    (37, 8, 5, 'skip', '2025-07-12 07:45:00', 20474, 20474, 'US', 'smart_tv'),
    (4, 21, 13, 'play', '2025-07-28 07:30:00', 0, 208056, 'MX', 'desktop'),
    (33, 4, 5, 'play', '2025-07-30 09:30:00', 0, 172364, 'GB', 'mobile'),
    (10, 4, NULL, 'play', '2025-07-06 15:00:00', 0, 107084, 'GB', 'mobile'),
    (29, 36, 5, 'play', '2025-07-31 17:45:00', 0, 187533, 'IT', 'mobile'),
    (16, 3, 6, 'play', '2025-07-12 11:30:00', 0, 168730, 'GB', 'mobile'),
    (15, 6, 5, 'play', '2025-07-25 15:00:00', 0, 151627, 'US', 'mobile'),
    (6, 6, 11, 'play', '2025-07-31 14:30:00', 0, 150248, 'CO', 'mobile'),
    (36, 33, 15, 'share', '2025-07-23 09:15:00', 0, 185510, 'US', 'desktop'),
    (15, 31, 2, 'play', '2025-07-07 16:00:00', 0, 185701, 'MX', 'mobile'),
    (3, 32, NULL, 'share', '2025-07-13 10:30:00', 0, 167282, 'US', 'other'),
    (23, 3, 13, 'play', '2025-07-10 14:00:00', 0, 174382, 'KR', 'smart_tv'),
    (20, 8, 9, 'play', '2025-07-10 18:15:00', 0, 251551, 'BR', 'mobile'),
    (40, 22, 3, 'play', '2025-07-25 19:30:00', 0, 229955, 'GB', 'mobile'),
    (26, 34, NULL, 'play', '2025-07-19 18:30:00', 0, 174194, 'US', 'tablet'),
    (24, 21, 15, 'skip', '2025-07-25 18:45:00', 29393, 29393, 'CO', 'smart_tv'),
    (11, 30, 14, 'play', '2025-07-14 07:45:00', 0, 138774, 'US', 'other'),
    (24, 26, 11, 'play', '2025-07-09 12:00:00', 0, 119029, 'US', 'desktop'),
    (25, 29, NULL, 'play', '2025-07-07 07:45:00', 0, 161643, 'BR', 'smart_tv'),
    (5, 15, 17, 'play', '2025-07-26 08:15:00', 0, 130225, 'JP', 'desktop'),
    (36, 7, NULL, 'play', '2025-07-14 09:30:00', 0, 166484, 'US', 'other'),
    (19, 30, 15, 'play', '2025-07-09 08:45:00', 0, 146009, 'JP', 'other'),
    (28, 4, NULL, 'play', '2025-07-09 20:15:00', 0, 126294, 'ES', 'tablet'),
    (18, 3, 10, 'play', '2025-07-12 20:45:00', 0, 204573, 'CO', 'mobile'),
    (3, 16, NULL, 'play', '2025-07-23 08:15:00', 0, 150190, 'US', 'other'),
    (27, 18, 18, 'play', '2025-07-21 23:15:00', 0, 131174, 'AU', 'tablet'),
    (15, 23, 2, 'play', '2025-07-09 06:15:00', 0, 99609, 'MX', 'mobile'),
    (39, 13, 5, 'play', '2025-07-28 14:45:00', 0, 270971, 'ES', 'tablet'),
    (5, 33, NULL, 'play', '2025-07-19 06:00:00', 0, 142248, 'KR', 'tablet'),
    (18, 26, 10, 'play', '2025-07-18 18:15:00', 0, 172451, 'CA', 'smart_tv'),
    (21, 15, 2, 'save', '2025-07-23 21:00:00', 0, 111024, 'AU', 'other'),
    (27, 25, 7, 'play', '2025-07-25 20:30:00', 0, 123481, 'GB', 'smart_tv'),
    (9, 4, 17, 'play', '2025-07-02 14:30:00', 0, 111344, 'CA', 'other'),
    (16, 8, 7, 'play', '2025-07-17 18:30:00', 0, 249346, 'KR', 'smart_tv'),
    (10, 30, NULL, 'play', '2025-07-04 06:45:00', 0, 104187, 'GB', 'other'),
    (31, 1, 17, 'skip', '2025-07-10 13:30:00', 20468, 20468, 'CA', 'smart_tv'),
    (11, 10, 11, 'play', '2025-07-18 14:30:00', 0, 146785, 'US', 'other'),
    (25, 18, NULL, 'play', '2025-07-31 18:00:00', 0, 165122, 'BR', 'desktop'),
    (3, 18, NULL, 'play', '2025-08-16 20:15:00', 0, 162342, 'CO', 'tablet'),
    (20, 29, 7, 'play', '2025-08-13 09:15:00', 0, 108180, 'MX', 'tablet'),
    (22, 3, 12, 'play', '2025-08-04 12:30:00', 0, 164061, 'MX', 'smart_tv'),
    (21, 9, 11, 'play', '2025-08-16 21:45:00', 0, 145375, 'US', 'mobile'),
    (35, 19, 4, 'play', '2025-08-27 09:15:00', 0, 107771, 'ES', 'tablet'),
    (26, 38, NULL, 'play', '2025-08-23 07:30:00', 0, 196598, 'ES', 'smart_tv'),
    (1, 35, 13, 'play', '2025-08-29 08:30:00', 0, 113039, 'MX', 'other'),
    (14, 13, NULL, 'play', '2025-08-15 17:15:00', 0, 190105, 'JP', 'other'),
    (24, 26, NULL, 'play', '2025-08-30 15:00:00', 0, 131365, 'IT', 'mobile'),
    (28, 11, 8, 'play', '2025-08-12 16:45:00', 0, 270664, 'KR', 'mobile'),
    (1, 32, NULL, 'play', '2025-08-24 23:15:00', 0, 154202, 'ES', 'mobile'),
    (26, 14, NULL, 'save', '2025-08-16 19:30:00', 0, 138832, 'ES', 'other'),
    (11, 27, NULL, 'play', '2025-08-17 12:30:00', 0, 141810, 'KR', 'smart_tv'),
    (4, 10, 2, 'play', '2025-08-02 18:30:00', 0, 108945, 'US', 'desktop'),
    (26, 38, NULL, 'play', '2025-08-14 14:45:00', 0, 126835, 'GB', 'mobile'),
    (38, 17, 10, 'play', '2025-08-24 19:30:00', 0, 258390, 'IT', 'tablet'),
    (20, 31, 4, 'play', '2025-08-26 10:45:00', 0, 125308, 'CO', 'mobile'),
    (23, 25, 15, 'play', '2025-08-20 18:45:00', 0, 158496, 'IT', 'other'),
    (30, 2, 11, 'play', '2025-08-20 20:15:00', 0, 155566, 'GB', 'tablet'),
    (24, 4, 8, 'play', '2025-08-22 14:45:00', 0, 182789, 'GB', 'mobile'),
    (20, 23, 8, 'play', '2025-08-20 07:00:00', 0, 146404, 'BR', 'desktop'),
    (21, 28, NULL, 'save', '2025-08-27 12:45:00', 0, 168527, 'BR', 'smart_tv'),
    (23, 19, NULL, 'play', '2025-08-23 16:15:00', 0, 114046, 'JP', 'mobile'),
    (14, 26, 16, 'play', '2025-08-18 07:00:00', 0, 164146, 'US', 'desktop'),
    (18, 10, 13, 'play', '2025-08-08 23:00:00', 0, 151443, 'JP', 'tablet'),
    (30, 12, 10, 'skip', '2025-08-10 10:30:00', 27978, 27978, 'CA', 'smart_tv'),
    (26, 12, 10, 'save', '2025-08-23 06:15:00', 0, 136140, 'US', 'tablet'),
    (3, 2, 6, 'play', '2025-08-03 17:45:00', 0, 155064, 'JP', 'mobile'),
    (14, 1, NULL, 'skip', '2025-08-05 20:15:00', 5098, 5098, 'KR', 'mobile'),
    (20, 25, NULL, 'play', '2025-08-07 06:30:00', 0, 206273, 'ES', 'smart_tv'),
    (32, 5, NULL, 'play', '2025-08-27 12:15:00', 0, 160608, 'CA', 'desktop'),
    (27, 16, 14, 'play', '2025-08-11 10:30:00', 0, 169991, 'JP', 'mobile'),
    (25, 9, NULL, 'play', '2025-08-29 14:00:00', 0, 210908, 'JP', 'desktop'),
    (30, 28, 9, 'save', '2025-08-05 15:00:00', 0, 194019, 'US', 'other'),
    (30, 31, 14, 'play', '2025-08-16 20:45:00', 0, 188514, 'GB', 'tablet'),
    (35, 7, 5, 'play', '2025-08-20 07:30:00', 0, 162003, 'MX', 'other'),
    (4, 24, 11, 'play', '2025-08-30 11:15:00', 0, 211862, 'KR', 'smart_tv'),
    (3, 3, 4, 'play', '2025-08-11 20:30:00', 0, 201540, 'IT', 'mobile'),
    (13, 1, 16, 'save', '2025-08-03 07:45:00', 0, 123828, 'JP', 'mobile'),
    (6, 30, 12, 'share', '2025-08-17 09:45:00', 0, 163018, 'US', 'smart_tv'),
    (1, 3, 15, 'share', '2025-08-29 22:00:00', 0, 164570, 'GB', 'smart_tv'),
    (16, 32, NULL, 'play', '2025-08-10 10:45:00', 0, 118388, 'US', 'mobile'),
    (28, 15, 16, 'play', '2025-08-19 12:15:00', 0, 124319, 'US', 'mobile'),
    (4, 29, 16, 'play', '2025-08-16 10:00:00', 0, 150334, 'IT', 'mobile'),
    (40, 14, NULL, 'play', '2025-08-01 19:30:00', 0, 143066, 'GB', 'mobile'),
    (40, 20, 5, 'play', '2025-08-08 10:30:00', 0, 165118, 'AU', 'mobile'),
    (38, 2, 15, 'skip', '2025-08-29 19:15:00', 9829, 9829, 'KR', 'other'),
    (17, 22, NULL, 'play', '2025-08-15 16:45:00', 0, 206675, 'CA', 'other'),
    (39, 4, NULL, 'play', '2025-08-23 20:00:00', 0, 177181, 'KR', 'mobile'),
    (36, 33, NULL, 'skip', '2025-08-19 09:15:00', 8623, 8623, 'IT', 'mobile'),
    (18, 15, 16, 'play', '2025-08-15 15:30:00', 0, 152977, 'ES', 'other'),
    (29, 33, 6, 'play', '2025-08-01 14:45:00', 0, 188496, 'MX', 'mobile'),
    (18, 30, 10, 'play', '2025-08-27 23:00:00', 0, 130367, 'ES', 'mobile'),
    (13, 38, 13, 'play', '2025-08-14 08:00:00', 0, 144143, 'GB', 'desktop'),
    (26, 6, 13, 'play', '2025-09-16 18:45:00', 0, 150588, 'ES', 'tablet'),
    (13, 34, 4, 'play', '2025-09-12 16:00:00', 0, 172536, 'CO', 'mobile'),
    (29, 29, 3, 'play', '2025-09-17 06:45:00', 0, 142427, 'IT', 'smart_tv'),
    (14, 10, 16, 'play', '2025-09-04 12:30:00', 0, 173538, 'JP', 'tablet'),
    (34, 32, 8, 'play', '2025-09-25 22:30:00', 0, 139503, 'BR', 'mobile'),
    (35, 46, 5, 'share', '2025-09-15 12:30:00', 0, 137906, 'ES', 'desktop'),
    (35, 8, 1, 'play', '2025-09-01 13:15:00', 0, 185109, 'IT', 'mobile'),
    (37, 5, 18, 'play', '2025-09-02 09:00:00', 0, 131181, 'CA', 'other'),
    (21, 29, NULL, 'play', '2025-09-03 22:45:00', 0, 159484, 'KR', 'mobile'),
    (9, 12, 13, 'skip', '2025-09-04 12:00:00', 16048, 16048, 'CA', 'mobile'),
    (22, 19, NULL, 'play', '2025-09-05 08:00:00', 0, 140771, 'US', 'mobile'),
    (10, 15, 12, 'play', '2025-09-22 07:30:00', 0, 99299, 'US', 'tablet'),
    (37, 33, NULL, 'play', '2025-09-10 13:15:00', 0, 166907, 'KR', 'tablet'),
    (37, 21, 10, 'play', '2025-09-07 06:00:00', 0, 192626, 'AU', 'smart_tv'),
    (31, 9, 5, 'play', '2025-09-07 21:00:00', 0, 198160, 'CA', 'mobile'),
    (3, 6, 5, 'play', '2025-09-12 18:00:00', 0, 185039, 'IT', 'smart_tv'),
    (19, 5, 14, 'play', '2025-09-24 19:00:00', 0, 197629, 'MX', 'mobile'),
    (16, 4, 18, 'play', '2025-09-14 18:15:00', 0, 123433, 'CO', 'smart_tv'),
    (13, 17, NULL, 'play', '2025-09-10 16:45:00', 0, 209109, 'BR', 'mobile'),
    (37, 12, 15, 'play', '2025-09-22 14:30:00', 0, 144756, 'IT', 'smart_tv'),
    (19, 38, NULL, 'skip', '2025-09-13 11:15:00', 18353, 18353, 'CO', 'mobile'),
    (31, 19, 10, 'play', '2025-09-25 15:45:00', 0, 153770, 'MX', 'mobile'),
    (2, 20, 14, 'play', '2025-09-30 22:30:00', 0, 156410, 'US', 'smart_tv'),
    (16, 10, 3, 'share', '2025-09-05 14:15:00', 0, 128010, 'BR', 'tablet'),
    (26, 38, 12, 'play', '2025-09-28 23:30:00', 0, 196036, 'MX', 'mobile'),
    (23, 8, 5, 'play', '2025-09-22 21:45:00', 0, 191171, 'GB', 'desktop'),
    (28, 30, NULL, 'play', '2025-09-08 12:45:00', 0, 143964, 'MX', 'smart_tv'),
    (28, 7, 10, 'play', '2025-09-03 17:00:00', 0, 142919, 'ES', 'smart_tv'),
    (20, 22, 12, 'play', '2025-09-24 13:45:00', 0, 168128, 'CA', 'tablet'),
    (39, 27, 4, 'play', '2025-09-05 19:45:00', 0, 166144, 'GB', 'mobile'),
    (21, 1, NULL, 'play', '2025-09-29 06:45:00', 0, 187957, 'CA', 'other'),
    (11, 20, 12, 'play', '2025-09-30 14:15:00', 0, 179763, 'US', 'mobile'),
    (27, 30, 7, 'play', '2025-09-04 12:00:00', 0, 163637, 'AU', 'tablet'),
    (26, 16, NULL, 'play', '2025-09-22 22:15:00', 0, 160491, 'IT', 'smart_tv'),
    (32, 35, 11, 'skip', '2025-09-11 22:00:00', 18518, 18518, 'AU', 'other'),
    (40, 6, 6, 'share', '2025-09-14 22:45:00', 0, 179486, 'US', 'mobile'),
    (36, 5, 3, 'save', '2025-09-08 06:00:00', 0, 131101, 'AU', 'other'),
    (29, 31, 8, 'play', '2025-09-29 06:30:00', 0, 136323, 'US', 'mobile'),
    (14, 6, NULL, 'play', '2025-09-20 13:45:00', 0, 164358, 'US', 'desktop'),
    (26, 7, 18, 'play', '2025-09-20 19:15:00', 0, 133548, 'MX', 'smart_tv'),
    (31, 36, NULL, 'play', '2025-09-26 08:15:00', 0, 115078, 'GB', 'tablet'),
    (40, 27, 1, 'skip', '2025-09-04 13:30:00', 22876, 22876, 'ES', 'tablet'),
    (3, 20, 14, 'play', '2025-09-22 15:45:00', 0, 141788, 'GB', 'other'),
    (32, 6, 8, 'play', '2025-09-15 06:15:00', 0, 170608, 'CA', 'desktop'),
    (31, 2, 17, 'play', '2025-09-01 08:00:00', 0, 139900, 'US', 'other'),
    (27, 6, 2, 'skip', '2025-09-28 15:30:00', 15218, 15218, 'MX', 'mobile'),
    (37, 11, 6, 'skip', '2025-09-05 12:30:00', 27646, 27646, 'CA', 'other'),
    (6, 33, NULL, 'play', '2025-09-14 16:15:00', 0, 128300, 'MX', 'mobile'),
    (29, 27, NULL, 'play', '2025-09-11 06:45:00', 0, 218954, 'US', 'mobile'),
    (34, 36, 9, 'play', '2025-09-01 19:45:00', 0, 167224, 'AU', 'other'),
    (29, 13, 15, 'play', '2025-09-19 20:00:00', 0, 319229, 'ES', 'tablet'),
    (32, 28, NULL, 'play', '2025-09-12 14:30:00', 0, 170563, 'KR', 'other'),
    (25, 5, 9, 'play', '2025-09-12 15:15:00', 0, 171820, 'KR', 'other'),
    (28, 34, 5, 'play', '2025-09-17 21:45:00', 0, 215757, 'US', 'mobile'),
    (16, 27, NULL, 'play', '2025-09-14 08:45:00', 0, 176851, 'US', 'mobile'),
    (29, 38, NULL, 'play', '2025-09-18 13:15:00', 0, 149976, 'BR', 'mobile'),
    (11, 3, 9, 'play', '2025-10-17 14:00:00', 0, 167889, 'IT', 'mobile'),
    (32, 22, 2, 'play', '2025-10-21 09:00:00', 0, 214768, 'AU', 'tablet'),
    (4, 30, NULL, 'skip', '2025-10-12 22:00:00', 21087, 21087, 'BR', 'other'),
    (15, 4, 8, 'play', '2025-10-01 13:30:00', 0, 164803, 'MX', 'other'),
    (24, 29, 1, 'share', '2025-10-24 06:45:00', 0, 134479, 'JP', 'smart_tv'),
    (2, 10, 17, 'play', '2025-10-05 10:45:00', 0, 143926, 'GB', 'desktop'),
    (20, 5, NULL, 'play', '2025-10-11 13:00:00', 0, 132226, 'MX', 'smart_tv'),
    (16, 7, 11, 'play', '2025-10-09 15:30:00', 0, 199341, 'US', 'mobile'),
    (17, 34, 12, 'share', '2025-10-03 15:30:00', 0, 143998, 'BR', 'tablet'),
    (19, 14, 1, 'play', '2025-10-22 09:30:00', 0, 129615, 'CA', 'mobile'),
    (40, 28, 7, 'play', '2025-10-15 20:45:00', 0, 187538, 'MX', 'mobile'),
    (38, 34, 2, 'share', '2025-10-20 11:30:00', 0, 204507, 'US', 'desktop'),
    (1, 5, 16, 'play', '2025-10-07 06:30:00', 0, 186618, 'US', 'other'),
    (24, 32, NULL, 'play', '2025-10-05 09:45:00', 0, 176435, 'AU', 'desktop'),
    (10, 33, 13, 'play', '2025-10-16 18:15:00', 0, 172737, 'ES', 'mobile'),
    (3, 35, 15, 'skip', '2025-10-03 18:45:00', 20116, 20116, 'BR', 'mobile'),
    (11, 6, 4, 'save', '2025-10-30 07:30:00', 0, 174584, 'CO', 'mobile'),
    (19, 31, 2, 'play', '2025-10-13 16:45:00', 0, 175199, 'JP', 'mobile'),
    (34, 33, NULL, 'play', '2025-10-05 17:15:00', 0, 202327, 'US', 'tablet'),
    (35, 28, 2, 'play', '2025-10-21 10:00:00', 0, 126326, 'CO', 'mobile'),
    (14, 16, 4, 'play', '2025-10-21 17:45:00', 0, 134886, 'AU', 'mobile'),
    (23, 17, NULL, 'skip', '2025-10-14 21:00:00', 23554, 23554, 'CO', 'mobile'),
    (40, 6, 6, 'play', '2025-10-05 21:45:00', 0, 165837, 'GB', 'mobile'),
    (5, 33, 5, 'skip', '2025-10-22 22:15:00', 13760, 13760, 'IT', 'mobile'),
    (39, 14, NULL, 'play', '2025-10-29 13:15:00', 0, 183234, 'US', 'desktop'),
    (37, 37, NULL, 'play', '2025-10-22 17:30:00', 0, 99858, 'ES', 'smart_tv'),
    (1, 36, 17, 'play', '2025-10-16 14:00:00', 0, 133961, 'CO', 'mobile'),
    (26, 20, 8, 'play', '2025-10-22 08:45:00', 0, 191582, 'GB', 'mobile'),
    (9, 9, 3, 'play', '2025-10-13 19:30:00', 0, 227558, 'BR', 'mobile'),
    (38, 33, 2, 'play', '2025-10-06 14:30:00', 0, 175191, 'KR', 'desktop'),
    (6, 1, 18, 'play', '2025-10-11 14:00:00', 0, 184362, 'BR', 'tablet'),
    (39, 9, NULL, 'play', '2025-10-06 20:15:00', 0, 193153, 'ES', 'mobile'),
    (23, 30, NULL, 'play', '2025-10-13 11:15:00', 0, 110316, 'MX', 'mobile'),
    (17, 36, 10, 'play', '2025-10-20 09:45:00', 0, 160740, 'JP', 'mobile'),
    (18, 6, 4, 'share', '2025-10-28 23:30:00', 0, 177059, 'GB', 'other'),
    (4, 5, 8, 'skip', '2025-10-09 11:30:00', 8743, 8743, 'CA', 'mobile'),
    (25, 14, 17, 'play', '2025-10-21 07:45:00', 0, 177142, 'CA', 'mobile'),
    (9, 38, 15, 'play', '2025-10-12 10:15:00', 0, 210991, 'US', 'desktop'),
    (21, 11, NULL, 'play', '2025-10-08 06:30:00', 0, 179086, 'BR', 'smart_tv'),
    (28, 46, 1, 'play', '2025-10-22 08:45:00', 0, 134497, 'ES', 'mobile'),
    (15, 32, 18, 'play', '2025-10-16 06:30:00', 0, 187875, 'US', 'mobile'),
    (25, 29, 6, 'play', '2025-10-16 08:15:00', 0, 103047, 'AU', 'mobile'),
    (18, 38, 9, 'play', '2025-10-20 15:15:00', 0, 134052, 'IT', 'smart_tv'),
    (15, 12, 8, 'play', '2025-10-12 15:45:00', 0, 221928, 'KR', 'desktop'),
    (38, 17, NULL, 'play', '2025-10-03 18:00:00', 0, 217917, 'IT', 'mobile'),
    (35, 38, 4, 'play', '2025-10-31 21:00:00', 0, 150587, 'KR', 'tablet'),
    (13, 3, 18, 'save', '2025-10-26 10:45:00', 0, 164438, 'US', 'mobile'),
    (17, 27, 16, 'play', '2025-10-06 20:15:00', 0, 219488, 'AU', 'mobile'),
    (24, 37, 2, 'play', '2025-10-27 21:15:00', 0, 130929, 'CA', 'mobile'),
    (19, 29, 1, 'play', '2025-10-17 12:15:00', 0, 161251, 'KR', 'mobile'),
    (21, 14, 1, 'play', '2025-10-05 15:30:00', 0, 175094, 'US', 'smart_tv'),
    (25, 21, 14, 'play', '2025-10-07 09:45:00', 0, 164473, 'US', 'smart_tv'),
    (3, 2, 6, 'skip', '2025-10-06 22:15:00', 12658, 12658, 'US', 'mobile'),
    (15, 9, 5, 'play', '2025-10-13 11:30:00', 0, 234014, 'US', 'smart_tv'),
    (32, 19, 10, 'play', '2025-10-01 21:15:00', 0, 141853, 'KR', 'desktop'),
    (22, 3, 12, 'play', '2025-10-11 20:00:00', 0, 232324, 'GB', 'other'),
    (36, 1, NULL, 'skip', '2025-10-23 18:30:00', 23128, 23128, 'KR', 'mobile'),
    (26, 19, 2, 'play', '2025-11-14 08:45:00', 0, 117902, 'US', 'mobile'),
    (40, 15, 4, 'play', '2025-11-29 17:45:00', 0, 116420, 'US', 'mobile'),
    (20, 23, 10, 'play', '2025-11-13 09:00:00', 0, 115170, 'JP', 'other'),
    (21, 30, 9, 'play', '2025-11-12 11:00:00', 0, 98829, 'KR', 'other'),
    (9, 5, 5, 'play', '2025-11-17 06:00:00', 0, 127004, 'GB', 'tablet'),
    (23, 20, 12, 'play', '2025-11-26 16:15:00', 0, 176691, 'JP', 'desktop'),
    (31, 28, 11, 'play', '2025-11-07 08:00:00', 0, 180094, 'CA', 'mobile'),
    (22, 27, 17, 'share', '2025-11-04 07:30:00', 0, 176681, 'CO', 'mobile'),
    (23, 34, NULL, 'play', '2025-11-17 09:30:00', 0, 164091, 'MX', 'tablet'),
    (10, 1, 5, 'play', '2025-11-27 14:15:00', 0, 160209, 'US', 'other'),
    (26, 42, NULL, 'play', '2025-11-16 09:30:00', 0, 217889, 'US', 'tablet'),
    (3, 4, 12, 'share', '2025-11-26 16:45:00', 0, 141247, 'CA', 'smart_tv'),
    (5, 15, 15, 'skip', '2025-11-05 23:00:00', 15191, 15191, 'MX', 'desktop'),
    (6, 32, 10, 'play', '2025-11-04 23:00:00', 0, 175327, 'US', 'other'),
    (21, 6, 17, 'play', '2025-11-28 11:15:00', 0, 192672, 'US', 'tablet'),
    (14, 28, 1, 'play', '2025-11-11 14:45:00', 0, 173707, 'US', 'mobile'),
    (1, 21, 2, 'play', '2025-11-10 14:30:00', 0, 173368, 'IT', 'other'),
    (15, 32, 14, 'play', '2025-11-19 06:45:00', 0, 111905, 'MX', 'mobile'),
    (9, 33, 6, 'play', '2025-11-21 19:00:00', 0, 152669, 'KR', 'mobile'),
    (33, 30, 9, 'play', '2025-11-15 15:30:00', 0, 159325, 'IT', 'mobile'),
    (40, 29, NULL, 'play', '2025-11-29 10:30:00', 0, 162618, 'ES', 'mobile'),
    (13, 25, 4, 'play', '2025-11-23 17:45:00', 0, 189418, 'US', 'tablet'),
    (6, 15, NULL, 'share', '2025-11-07 20:00:00', 0, 120731, 'US', 'mobile'),
    (19, 38, NULL, 'save', '2025-11-02 17:30:00', 0, 149874, 'US', 'other'),
    (32, 9, 11, 'play', '2025-11-14 15:15:00', 0, 237230, 'BR', 'tablet'),
    (29, 46, NULL, 'play', '2025-11-06 09:00:00', 0, 126466, 'GB', 'smart_tv'),
    (23, 8, NULL, 'play', '2025-11-20 20:15:00', 0, 171575, 'KR', 'other'),
    (38, 41, 17, 'play', '2025-11-28 15:45:00', 0, 155993, 'GB', 'mobile'),
    (4, 10, 18, 'skip', '2025-11-13 18:45:00', 5341, 5341, 'IT', 'smart_tv'),
    (25, 41, 2, 'play', '2025-11-29 10:45:00', 0, 168941, 'KR', 'mobile'),
    (25, 26, 9, 'play', '2025-11-03 13:30:00', 0, 116905, 'CA', 'desktop'),
    (6, 22, NULL, 'play', '2025-11-20 11:15:00', 0, 234720, 'US', 'smart_tv'),
    (4, 18, 8, 'play', '2025-11-12 07:15:00', 0, 157005, 'CA', 'other'),
    (39, 33, 13, 'play', '2025-11-14 22:00:00', 0, 146485, 'MX', 'desktop'),
    (14, 27, 8, 'skip', '2025-11-02 09:15:00', 19490, 19490, 'ES', 'mobile'),
    (38, 5, NULL, 'skip', '2025-11-10 16:15:00', 6435, 6435, 'CO', 'smart_tv'),
    (20, 14, 10, 'play', '2025-11-13 12:45:00', 0, 192484, 'BR', 'desktop'),
    (32, 23, 7, 'share', '2025-11-03 10:30:00', 0, 135984, 'AU', 'desktop'),
    (31, 28, NULL, 'skip', '2025-11-26 19:45:00', 18509, 18509, 'KR', 'mobile'),
    (24, 19, NULL, 'play', '2025-11-16 15:00:00', 0, 156827, 'CA', 'smart_tv'),
    (23, 8, 5, 'play', '2025-11-05 16:30:00', 0, 213846, 'US', 'tablet'),
    (33, 17, 2, 'play', '2025-11-22 16:45:00', 0, 258241, 'CO', 'mobile'),
    (3, 42, 17, 'skip', '2025-11-11 06:45:00', 22140, 22140, 'US', 'mobile'),
    (5, 7, 3, 'play', '2025-11-27 20:30:00', 0, 139253, 'MX', 'tablet'),
    (4, 33, 11, 'play', '2025-11-04 16:45:00', 0, 163860, 'GB', 'mobile'),
    (29, 5, NULL, 'play', '2025-11-04 22:00:00', 0, 195324, 'AU', 'mobile'),
    (23, 34, 7, 'skip', '2025-11-30 17:30:00', 8409, 8409, 'CA', 'desktop'),
    (4, 8, 10, 'play', '2025-11-19 23:15:00', 0, 141870, 'BR', 'other'),
    (40, 8, NULL, 'share', '2025-11-01 20:30:00', 0, 244588, 'BR', 'mobile'),
    (20, 21, 11, 'skip', '2025-11-17 13:15:00', 19749, 19749, 'JP', 'mobile'),
    (20, 8, 10, 'play', '2025-11-22 13:45:00', 0, 234542, 'AU', 'smart_tv'),
    (38, 34, 12, 'play', '2025-11-16 10:15:00', 0, 178421, 'MX', 'mobile'),
    (27, 2, 6, 'play', '2025-11-20 20:00:00', 0, 212189, 'BR', 'smart_tv'),
    (25, 18, NULL, 'play', '2025-11-06 23:30:00', 0, 192454, 'AU', 'tablet'),
    (34, 40, NULL, 'skip', '2025-11-23 22:15:00', 21713, 21713, 'BR', 'desktop'),
    (19, 27, 12, 'play', '2025-11-15 20:30:00', 0, 160797, 'CO', 'mobile'),
    (25, 15, NULL, 'play', '2025-12-11 08:00:00', 0, 131715, 'MX', 'mobile'),
    (26, 18, 11, 'play', '2025-12-18 22:30:00', 0, 148169, 'CA', 'other'),
    (27, 5, 12, 'skip', '2025-12-31 17:00:00', 29301, 29301, 'GB', 'other'),
    (22, 14, 2, 'play', '2025-12-19 19:45:00', 0, 138033, 'ES', 'desktop'),
    (20, 23, 9, 'play', '2025-12-31 11:15:00', 0, 106365, 'KR', 'mobile'),
    (19, 4, 3, 'play', '2025-12-05 14:15:00', 0, 140299, 'CA', 'mobile'),
    (35, 4, 16, 'skip', '2025-12-18 14:15:00', 3735, 3735, 'AU', 'mobile'),
    (25, 8, NULL, 'save', '2025-12-15 19:30:00', 0, 216770, 'JP', 'mobile'),
    (30, 2, 5, 'play', '2025-12-12 07:00:00', 0, 144518, 'GB', 'mobile'),
    (35, 46, 18, 'play', '2025-12-25 08:15:00', 0, 184376, 'BR', 'tablet'),
    (40, 26, NULL, 'play', '2025-12-21 12:15:00', 0, 145821, 'CA', 'desktop'),
    (11, 7, NULL, 'play', '2025-12-03 20:00:00', 0, 130224, 'US', 'other'),
    (19, 22, 8, 'play', '2025-12-14 13:30:00', 0, 180010, 'GB', 'smart_tv'),
    (9, 26, NULL, 'play', '2025-12-15 13:30:00', 0, 129195, 'JP', 'mobile'),
    (26, 32, 7, 'play', '2025-12-30 06:15:00', 0, 159645, 'US', 'desktop'),
    (13, 14, 5, 'play', '2025-12-04 16:30:00', 0, 181360, 'US', 'mobile'),
    (40, 6, NULL, 'skip', '2025-12-11 20:30:00', 14329, 14329, 'CA', 'mobile'),
    (15, 10, 13, 'play', '2025-12-10 15:30:00', 0, 182050, 'MX', 'tablet'),
    (21, 17, NULL, 'play', '2025-12-19 17:15:00', 0, 289038, 'KR', 'smart_tv'),
    (5, 6, NULL, 'play', '2025-12-22 11:45:00', 0, 111017, 'AU', 'other'),
    (27, 34, 8, 'play', '2025-12-16 07:45:00', 0, 223193, 'US', 'other'),
    (23, 5, 6, 'play', '2025-12-26 21:45:00', 0, 165317, 'AU', 'mobile'),
    (28, 13, 5, 'share', '2025-12-19 10:00:00', 0, 221232, 'US', 'desktop'),
    (37, 31, 17, 'play', '2025-12-15 18:45:00', 0, 212141, 'IT', 'mobile'),
    (31, 32, 5, 'play', '2025-12-29 12:45:00', 0, 165932, 'IT', 'mobile'),
    (10, 42, 5, 'play', '2025-12-27 09:45:00', 0, 201261, 'MX', 'tablet'),
    (24, 4, 9, 'save', '2025-12-16 21:45:00', 0, 131037, 'IT', 'mobile'),
    (28, 3, 12, 'skip', '2025-12-26 22:15:00', 5278, 5278, 'US', 'desktop'),
    (18, 17, 17, 'play', '2025-12-28 06:00:00', 0, 304785, 'CO', 'mobile'),
    (18, 21, 1, 'play', '2025-12-15 13:30:00', 0, 206860, 'CO', 'mobile'),
    (34, 39, 2, 'play', '2025-12-24 14:15:00', 0, 196758, 'MX', 'mobile'),
    (32, 10, 8, 'play', '2025-12-10 07:15:00', 0, 123672, 'ES', 'mobile'),
    (2, 17, 9, 'play', '2025-12-26 21:00:00', 0, 211539, 'BR', 'mobile'),
    (16, 40, 7, 'play', '2025-12-27 07:45:00', 0, 153942, 'GB', 'tablet'),
    (40, 27, 7, 'play', '2025-12-13 23:30:00', 0, 133116, 'CA', 'mobile'),
    (35, 42, 12, 'save', '2025-12-19 21:30:00', 0, 219698, 'JP', 'other'),
    (14, 40, 5, 'share', '2025-12-15 21:45:00', 0, 142960, 'US', 'other'),
    (3, 10, 4, 'play', '2025-12-14 12:30:00', 0, 140899, 'MX', 'other'),
    (18, 18, 4, 'play', '2025-12-21 18:00:00', 0, 189963, 'US', 'other'),
    (17, 3, 17, 'play', '2025-12-02 08:45:00', 0, 184094, 'BR', 'mobile'),
    (14, 4, 9, 'play', '2025-12-30 10:30:00', 0, 154222, 'US', 'mobile'),
    (25, 41, NULL, 'play', '2025-12-30 13:15:00', 0, 128792, 'MX', 'tablet'),
    (23, 36, 12, 'play', '2025-12-17 22:00:00', 0, 165233, 'IT', 'desktop'),
    (35, 15, 4, 'play', '2025-12-13 06:45:00', 0, 151939, 'GB', 'mobile'),
    (36, 26, 3, 'play', '2025-12-25 15:45:00', 0, 114928, 'JP', 'tablet'),
    (32, 5, NULL, 'skip', '2025-12-18 22:15:00', 27081, 27081, 'JP', 'smart_tv'),
    (34, 23, 4, 'play', '2025-12-01 11:30:00', 0, 121542, 'US', 'other'),
    (39, 46, 4, 'play', '2025-12-17 18:15:00', 0, 143899, 'ES', 'mobile'),
    (27, 15, 12, 'play', '2025-12-21 19:00:00', 0, 94928, 'IT', 'mobile'),
    (23, 29, 8, 'play', '2025-12-30 13:30:00', 0, 155196, 'US', 'mobile'),
    (10, 9, 11, 'skip', '2025-12-21 09:15:00', 11724, 11724, 'GB', 'tablet'),
    (40, 41, 4, 'play', '2025-12-28 10:15:00', 0, 159325, 'ES', 'other'),
    (26, 16, 1, 'share', '2025-12-24 18:00:00', 0, 173831, 'KR', 'other'),
    (31, 7, 15, 'play', '2025-12-24 11:45:00', 0, 190410, 'GB', 'other'),
    (31, 39, 16, 'play', '2025-12-31 23:45:00', 0, 160039, 'JP', 'smart_tv'),
    (17, 24, 17, 'play', '2025-12-13 12:30:00', 0, 135941, 'KR', 'desktop'),
    (20, 10, 3, 'play', '2025-12-25 19:30:00', 0, 188337, 'CO', 'smart_tv'),
    (35, 41, NULL, 'play', '2025-12-22 10:30:00', 0, 123379, 'MX', 'desktop'),
    (29, 22, 14, 'save', '2025-12-29 17:00:00', 0, 144159, 'BR', 'other'),
    (25, 13, 16, 'play', '2025-12-24 06:00:00', 0, 220285, 'IT', 'tablet'),
    (37, 6, 18, 'skip', '2026-01-01 23:45:00', 16572, 16572, 'US', 'mobile'),
    (31, 1, 4, 'skip', '2026-01-01 15:00:00', 25366, 25366, 'ES', 'mobile'),
    (10, 21, 14, 'play', '2026-01-09 12:00:00', 0, 219651, 'ES', 'mobile'),
    (36, 23, NULL, 'play', '2026-01-08 06:45:00', 0, 163037, 'GB', 'desktop'),
    (2, 21, NULL, 'play', '2026-01-15 13:45:00', 0, 138708, 'US', 'other'),
    (17, 36, 11, 'skip', '2026-01-29 10:00:00', 18318, 18318, 'ES', 'other'),
    (13, 35, 5, 'play', '2026-01-24 19:00:00', 0, 178830, 'GB', 'other'),
    (40, 22, 4, 'play', '2026-01-07 09:15:00', 0, 208299, 'JP', 'smart_tv'),
    (11, 24, 15, 'skip', '2026-01-12 22:00:00', 25577, 25577, 'KR', 'other'),
    (40, 9, 16, 'play', '2026-01-25 20:30:00', 0, 217130, 'BR', 'desktop'),
    (36, 16, NULL, 'play', '2026-01-18 07:30:00', 0, 115065, 'IT', 'mobile'),
    (6, 6, 6, 'play', '2026-01-26 20:45:00', 0, 146302, 'MX', 'mobile'),
    (20, 30, 10, 'play', '2026-01-30 15:00:00', 0, 141893, 'CO', 'mobile'),
    (16, 6, 6, 'play', '2026-01-03 10:30:00', 0, 154722, 'ES', 'mobile'),
    (28, 20, NULL, 'play', '2026-01-06 17:30:00', 0, 194765, 'BR', 'mobile'),
    (18, 13, 2, 'play', '2026-01-29 16:00:00', 0, 337215, 'US', 'mobile'),
    (20, 37, 3, 'play', '2026-01-16 10:45:00', 0, 161577, 'US', 'mobile'),
    (19, 24, 13, 'play', '2026-01-22 22:00:00', 0, 227546, 'CA', 'desktop'),
    (15, 46, 10, 'play', '2026-01-13 13:45:00', 0, 161955, 'MX', 'mobile'),
    (32, 42, NULL, 'play', '2026-01-16 06:45:00', 0, 198302, 'US', 'other'),
    (35, 13, 3, 'skip', '2026-01-26 09:45:00', 12655, 12655, 'IT', 'mobile'),
    (36, 19, 3, 'play', '2026-01-06 09:30:00', 0, 113535, 'US', 'tablet'),
    (25, 34, 13, 'play', '2026-01-03 20:30:00', 0, 198033, 'ES', 'mobile'),
    (33, 30, NULL, 'play', '2026-01-07 13:15:00', 0, 174646, 'US', 'desktop'),
    (31, 38, 14, 'play', '2026-01-04 21:00:00', 0, 217463, 'US', 'mobile'),
    (38, 35, NULL, 'play', '2026-01-08 08:00:00', 0, 119145, 'MX', 'desktop'),
    (6, 7, NULL, 'skip', '2026-01-26 10:30:00', 4547, 4547, 'BR', 'other'),
    (16, 14, 7, 'skip', '2026-01-15 12:00:00', 13258, 13258, 'CO', 'mobile'),
    (17, 27, 8, 'play', '2026-01-17 16:45:00', 0, 138489, 'KR', 'desktop'),
    (31, 11, 15, 'skip', '2026-01-07 10:45:00', 10636, 10636, 'KR', 'mobile'),
    (9, 28, NULL, 'play', '2026-01-25 17:30:00', 0, 169283, 'ES', 'mobile'),
    (4, 18, 17, 'play', '2026-01-08 22:30:00', 0, 169237, 'BR', 'mobile'),
    (18, 27, 14, 'skip', '2026-01-26 08:15:00', 10322, 10322, 'US', 'mobile'),
    (34, 22, 12, 'share', '2026-01-12 09:30:00', 0, 147034, 'AU', 'smart_tv'),
    (17, 8, 1, 'play', '2026-01-27 09:15:00', 0, 205560, 'CO', 'desktop'),
    (29, 15, 8, 'play', '2026-01-12 15:00:00', 0, 128866, 'MX', 'desktop'),
    (18, 18, 1, 'play', '2026-01-20 10:30:00', 0, 191275, 'US', 'tablet'),
    (24, 6, NULL, 'play', '2026-01-15 19:15:00', 0, 197960, 'US', 'mobile'),
    (22, 20, 7, 'skip', '2026-01-05 21:00:00', 22067, 22067, 'KR', 'smart_tv'),
    (19, 6, NULL, 'play', '2026-01-08 17:45:00', 0, 141201, 'CO', 'mobile'),
    (25, 40, 8, 'share', '2026-01-27 22:15:00', 0, 124793, 'US', 'mobile'),
    (20, 36, 2, 'skip', '2026-01-02 22:15:00', 15119, 15119, 'BR', 'smart_tv'),
    (36, 33, NULL, 'play', '2026-01-10 06:45:00', 0, 140689, 'US', 'tablet'),
    (17, 19, 13, 'play', '2026-01-06 11:45:00', 0, 136076, 'IT', 'other'),
    (20, 8, 6, 'play', '2026-01-07 12:30:00', 0, 212580, 'CO', 'mobile'),
    (9, 6, 14, 'play', '2026-01-08 07:45:00', 0, 113285, 'US', 'desktop'),
    (17, 10, 15, 'play', '2026-01-22 18:00:00', 0, 123622, 'JP', 'mobile'),
    (36, 1, 17, 'play', '2026-01-25 20:30:00', 0, 196229, 'ES', 'mobile'),
    (2, 41, NULL, 'play', '2026-01-10 19:30:00', 0, 144357, 'MX', 'mobile'),
    (18, 31, 6, 'skip', '2026-01-24 11:15:00', 25744, 25744, 'ES', 'mobile'),
    (21, 38, 5, 'skip', '2026-01-31 09:30:00', 28914, 28914, 'JP', 'mobile'),
    (35, 28, 10, 'play', '2026-01-04 18:30:00', 0, 132563, 'JP', 'desktop'),
    (39, 36, 4, 'play', '2026-01-26 07:30:00', 0, 188725, 'IT', 'mobile'),
    (36, 39, 14, 'play', '2026-01-01 21:15:00', 0, 130809, 'MX', 'mobile'),
    (11, 41, 14, 'play', '2026-01-27 17:15:00', 0, 177477, 'JP', 'other'),
    (5, 27, 16, 'play', '2026-01-21 11:45:00', 0, 159015, 'CO', 'mobile'),
    (22, 19, 1, 'play', '2026-01-14 12:30:00', 0, 172522, 'CO', 'desktop'),
    (6, 22, 6, 'skip', '2026-01-17 11:15:00', 5682, 5682, 'KR', 'other'),
    (26, 26, 8, 'play', '2026-01-14 16:00:00', 0, 169972, 'US', 'other'),
    (33, 46, 12, 'play', '2026-01-27 15:15:00', 0, 145916, 'CO', 'tablet'),
    (1, 3, 9, 'play', '2026-01-05 22:15:00', 0, 220611, 'US', 'tablet'),
    (2, 37, 18, 'play', '2026-01-24 14:00:00', 0, 131264, 'KR', 'desktop'),
    (20, 12, 2, 'play', '2026-01-01 21:30:00', 0, 156491, 'CO', 'mobile'),
    (29, 7, 12, 'play', '2026-01-02 23:30:00', 0, 140722, 'IT', 'desktop'),
    (30, 30, 13, 'play', '2026-01-31 08:30:00', 0, 112851, 'JP', 'other'),
    (20, 14, NULL, 'play', '2026-01-20 21:00:00', 0, 164209, 'US', 'tablet'),
    (5, 19, 1, 'play', '2026-01-31 20:15:00', 0, 166514, 'BR', 'mobile'),
    (40, 23, 17, 'play', '2026-01-27 06:00:00', 0, 156804, 'US', 'mobile'),
    (19, 5, NULL, 'play', '2026-02-04 20:15:00', 0, 138266, 'BR', 'mobile'),
    (1, 38, 1, 'play', '2026-02-17 19:45:00', 0, 151785, 'CO', 'desktop'),
    (34, 11, 4, 'play', '2026-02-21 06:30:00', 0, 186239, 'US', 'desktop'),
    (34, 39, 5, 'play', '2026-02-23 19:45:00', 0, 198191, 'US', 'smart_tv'),
    (33, 46, NULL, 'share', '2026-02-23 07:30:00', 0, 141540, 'MX', 'mobile'),
    (1, 15, 3, 'play', '2026-02-24 13:15:00', 0, 111708, 'IT', 'mobile'),
    (34, 46, NULL, 'play', '2026-02-03 15:00:00', 0, 129927, 'AU', 'desktop'),
    (30, 11, 3, 'skip', '2026-02-24 14:00:00', 6257, 6257, 'KR', 'other'),
    (28, 9, NULL, 'skip', '2026-02-18 15:45:00', 20608, 20608, 'GB', 'desktop'),
    (9, 43, 15, 'play', '2026-02-21 07:45:00', 0, 171193, 'JP', 'other'),
    (13, 31, 15, 'play', '2026-02-20 16:00:00', 0, 163725, 'IT', 'desktop'),
    (5, 14, 18, 'play', '2026-02-23 10:30:00', 0, 188163, 'BR', 'mobile'),
    (25, 31, 12, 'play', '2026-02-07 18:45:00', 0, 198577, 'GB', 'tablet'),
    (10, 47, 9, 'play', '2026-02-17 07:30:00', 0, 189501, 'CA', 'other'),
    (5, 13, 8, 'save', '2026-02-27 07:00:00', 0, 333755, 'ES', 'mobile'),
    (6, 17, NULL, 'skip', '2026-02-13 17:45:00', 11419, 11419, 'US', 'tablet'),
    (29, 40, NULL, 'play', '2026-02-12 21:00:00', 0, 156265, 'IT', 'desktop'),
    (27, 39, NULL, 'play', '2026-02-08 13:00:00', 0, 177661, 'BR', 'mobile'),
    (38, 21, 8, 'save', '2026-02-04 08:30:00', 0, 121876, 'JP', 'mobile'),
    (17, 32, 18, 'play', '2026-02-13 17:45:00', 0, 115259, 'BR', 'mobile'),
    (3, 46, NULL, 'play', '2026-02-15 09:45:00', 0, 173230, 'GB', 'smart_tv'),
    (34, 34, 12, 'play', '2026-02-13 14:00:00', 0, 211312, 'CO', 'desktop'),
    (16, 5, 16, 'skip', '2026-02-24 21:00:00', 9642, 9642, 'IT', 'mobile'),
    (31, 4, 17, 'play', '2026-02-28 11:30:00', 0, 149253, 'MX', 'mobile'),
    (10, 1, NULL, 'play', '2026-02-02 12:30:00', 0, 117119, 'CO', 'smart_tv'),
    (39, 13, 10, 'play', '2026-02-27 21:00:00', 0, 292301, 'US', 'mobile'),
    (14, 33, 17, 'play', '2026-02-10 11:30:00', 0, 153435, 'US', 'mobile'),
    (26, 18, 14, 'play', '2026-02-15 10:45:00', 0, 169571, 'CA', 'mobile'),
    (40, 33, 12, 'play', '2026-02-14 18:00:00', 0, 137669, 'CO', 'other'),
    (17, 7, NULL, 'play', '2026-02-23 20:30:00', 0, 171701, 'KR', 'mobile'),
    (35, 35, NULL, 'play', '2026-02-25 08:15:00', 0, 119290, 'US', 'other'),
    (6, 2, 17, 'play', '2026-02-24 19:15:00', 0, 120449, 'AU', 'desktop'),
    (36, 46, 4, 'play', '2026-02-25 19:00:00', 0, 203443, 'US', 'other'),
    (29, 20, 18, 'play', '2026-02-10 13:45:00', 0, 156355, 'MX', 'mobile'),
    (28, 8, NULL, 'skip', '2026-02-25 07:15:00', 13829, 13829, 'AU', 'tablet'),
    (28, 18, 9, 'play', '2026-02-07 21:45:00', 0, 137066, 'CO', 'smart_tv'),
    (13, 30, NULL, 'play', '2026-02-22 11:15:00', 0, 103202, 'AU', 'mobile'),
    (40, 2, 14, 'play', '2026-02-02 21:45:00', 0, 163231, 'CO', 'desktop'),
    (20, 32, NULL, 'play', '2026-02-03 07:30:00', 0, 151403, 'CA', 'other'),
    (27, 30, NULL, 'play', '2026-02-08 23:45:00', 0, 130066, 'US', 'mobile'),
    (32, 42, 7, 'play', '2026-02-24 21:15:00', 0, 162664, 'CA', 'other'),
    (29, 16, NULL, 'play', '2026-02-08 10:45:00', 0, 195302, 'US', 'desktop'),
    (5, 47, NULL, 'play', '2026-02-22 23:00:00', 0, 138594, 'IT', 'desktop'),
    (19, 8, NULL, 'save', '2026-02-09 14:00:00', 0, 207506, 'ES', 'smart_tv'),
    (3, 18, 13, 'save', '2026-02-17 17:45:00', 0, 147986, 'KR', 'mobile'),
    (3, 31, NULL, 'skip', '2026-02-28 11:15:00', 7780, 7780, 'ES', 'mobile'),
    (32, 41, NULL, 'play', '2026-02-11 08:00:00', 0, 178737, 'CO', 'desktop'),
    (19, 30, 14, 'play', '2026-02-11 13:30:00', 0, 106837, 'ES', 'other'),
    (26, 5, 11, 'play', '2026-02-05 17:00:00', 0, 133584, 'US', 'mobile'),
    (18, 30, 12, 'play', '2026-02-01 20:45:00', 0, 157888, 'KR', 'mobile'),
    (2, 18, NULL, 'play', '2026-02-17 08:00:00', 0, 145437, 'GB', 'desktop'),
    (37, 5, 1, 'skip', '2026-02-02 17:45:00', 28846, 28846, 'CA', 'desktop'),
    (37, 39, NULL, 'save', '2026-02-28 09:00:00', 0, 135135, 'ES', 'mobile'),
    (16, 36, NULL, 'play', '2026-02-16 20:00:00', 0, 114337, 'GB', 'other'),
    (27, 3, 2, 'play', '2026-02-04 19:45:00', 0, 186519, 'KR', 'tablet'),
    (4, 6, 9, 'skip', '2026-02-19 18:30:00', 15146, 15146, 'BR', 'desktop'),
    (29, 35, 2, 'play', '2026-02-15 12:15:00', 0, 132425, 'BR', 'tablet'),
    (15, 39, 9, 'save', '2026-02-03 08:45:00', 0, 167621, 'CO', 'smart_tv'),
    (33, 26, 16, 'play', '2026-02-25 06:45:00', 0, 106990, 'US', 'smart_tv'),
    (15, 34, 4, 'play', '2026-02-27 10:00:00', 0, 218467, 'ES', 'mobile'),
    (11, 17, 3, 'share', '2026-02-04 20:30:00', 0, 309188, 'AU', 'mobile'),
    (30, 35, 14, 'save', '2026-02-27 23:00:00', 0, 110958, 'ES', 'desktop'),
    (32, 38, 18, 'play', '2026-02-15 17:30:00', 0, 161431, 'KR', 'mobile'),
    (10, 35, 4, 'play', '2026-02-17 18:15:00', 0, 148836, 'ES', 'desktop'),
    (32, 1, 18, 'save', '2026-02-16 11:45:00', 0, 182776, 'US', 'mobile'),
    (32, 9, 13, 'play', '2026-02-19 23:30:00', 0, 144174, 'KR', 'tablet'),
    (2, 38, 7, 'play', '2026-02-20 21:15:00', 0, 187435, 'MX', 'mobile'),
    (17, 31, 6, 'share', '2026-02-11 13:15:00', 0, 189660, 'IT', 'mobile'),
    (16, 20, 17, 'play', '2026-03-14 11:45:00', 0, 161510, 'KR', 'tablet'),
    (14, 17, NULL, 'play', '2026-03-27 12:00:00', 0, 328292, 'CA', 'desktop'),
    (16, 2, 10, 'play', '2026-03-29 19:15:00', 0, 172826, 'JP', 'mobile'),
    (3, 42, NULL, 'play', '2026-03-26 16:30:00', 0, 202425, 'GB', 'mobile'),
    (22, 31, NULL, 'play', '2026-03-31 19:45:00', 0, 208083, 'US', 'tablet'),
    (29, 3, 3, 'play', '2026-03-13 10:30:00', 0, 236639, 'CO', 'mobile'),
    (6, 6, NULL, 'play', '2026-03-11 08:45:00', 0, 161917, 'US', 'desktop'),
    (18, 1, 5, 'play', '2026-03-16 09:00:00', 0, 140441, 'IT', 'other'),
    (33, 20, NULL, 'play', '2026-03-16 22:15:00', 0, 140734, 'GB', 'desktop'),
    (28, 8, NULL, 'play', '2026-03-02 21:00:00', 0, 188156, 'ES', 'tablet'),
    (13, 33, 18, 'play', '2026-03-07 10:00:00', 0, 150427, 'CA', 'desktop'),
    (34, 32, 18, 'play', '2026-03-02 19:45:00', 0, 172341, 'CO', 'other'),
    (9, 2, 12, 'play', '2026-03-25 20:45:00', 0, 173525, 'MX', 'mobile'),
    (9, 41, 15, 'play', '2026-03-08 07:00:00', 0, 138143, 'MX', 'mobile'),
    (9, 20, 15, 'play', '2026-03-19 13:30:00', 0, 145251, 'US', 'desktop'),
    (31, 28, NULL, 'share', '2026-03-24 14:45:00', 0, 128240, 'AU', 'tablet'),
    (26, 8, 8, 'skip', '2026-03-03 12:00:00', 4388, 4388, 'MX', 'mobile'),
    (2, 16, NULL, 'play', '2026-03-14 16:00:00', 0, 125359, 'JP', 'mobile'),
    (13, 22, 7, 'play', '2026-03-22 18:30:00', 0, 158233, 'US', 'other'),
    (27, 8, 18, 'play', '2026-03-01 14:30:00', 0, 232899, 'AU', 'mobile'),
    (9, 43, 10, 'play', '2026-03-11 23:45:00', 0, 106237, 'US', 'mobile'),
    (26, 8, 12, 'play', '2026-03-06 07:00:00', 0, 167285, 'CA', 'tablet'),
    (18, 43, 2, 'play', '2026-03-09 09:45:00', 0, 185029, 'CO', 'other'),
    (34, 47, 4, 'save', '2026-03-21 22:45:00', 0, 140715, 'US', 'tablet'),
    (13, 31, 8, 'play', '2026-03-05 09:15:00', 0, 204468, 'US', 'tablet'),
    (5, 29, 10, 'play', '2026-03-29 20:45:00', 0, 136265, 'US', 'tablet'),
    (11, 1, NULL, 'skip', '2026-03-30 12:45:00', 13656, 13656, 'BR', 'mobile'),
    (26, 16, 13, 'play', '2026-03-05 12:30:00', 0, 153303, 'BR', 'mobile'),
    (15, 11, 14, 'play', '2026-03-13 18:15:00', 0, 208836, 'ES', 'mobile'),
    (22, 12, 2, 'play', '2026-03-09 20:00:00', 0, 215027, 'IT', 'tablet'),
    (32, 44, 5, 'skip', '2026-03-07 17:00:00', 11428, 11428, 'MX', 'smart_tv'),
    (36, 34, NULL, 'play', '2026-03-08 07:00:00', 0, 227482, 'US', 'mobile'),
    (26, 30, 18, 'skip', '2026-03-03 08:45:00', 7833, 7833, 'AU', 'mobile'),
    (19, 46, 1, 'play', '2026-03-21 07:30:00', 0, 118777, 'ES', 'mobile'),
    (34, 44, NULL, 'share', '2026-03-18 16:30:00', 0, 121986, 'CA', 'mobile'),
    (2, 16, 2, 'save', '2026-03-04 18:15:00', 0, 166150, 'MX', 'tablet'),
    (39, 27, 6, 'skip', '2026-03-29 14:30:00', 21548, 21548, 'BR', 'smart_tv'),
    (27, 6, 14, 'play', '2026-03-19 23:15:00', 0, 140676, 'CO', 'tablet'),
    (31, 27, 4, 'play', '2026-03-01 11:30:00', 0, 188753, 'JP', 'other'),
    (31, 47, 2, 'play', '2026-03-05 22:00:00', 0, 119283, 'IT', 'tablet'),
    (25, 19, 12, 'play', '2026-03-19 16:00:00', 0, 148090, 'US', 'mobile'),
    (31, 9, 1, 'save', '2026-03-09 18:00:00', 0, 209300, 'AU', 'mobile'),
    (40, 2, 7, 'skip', '2026-03-02 18:45:00', 17398, 17398, 'ES', 'mobile'),
    (40, 41, NULL, 'play', '2026-03-19 18:45:00', 0, 164555, 'AU', 'smart_tv'),
    (26, 1, NULL, 'skip', '2026-03-26 18:30:00', 11262, 11262, 'CO', 'mobile'),
    (14, 47, NULL, 'skip', '2026-03-03 08:45:00', 10232, 10232, 'CA', 'smart_tv'),
    (14, 41, 12, 'play', '2026-03-04 06:30:00', 0, 190729, 'JP', 'smart_tv'),
    (17, 8, 7, 'play', '2026-03-02 20:00:00', 0, 171040, 'CA', 'tablet'),
    (15, 2, 15, 'save', '2026-03-14 12:15:00', 0, 150751, 'CO', 'mobile'),
    (11, 13, NULL, 'play', '2026-03-11 20:45:00', 0, 264297, 'GB', 'smart_tv'),
    (25, 13, NULL, 'play', '2026-03-04 18:15:00', 0, 286581, 'AU', 'other'),
    (36, 15, 5, 'play', '2026-03-27 18:30:00', 0, 140601, 'AU', 'mobile'),
    (2, 3, 10, 'save', '2026-03-23 06:45:00', 0, 171853, 'BR', 'mobile'),
    (19, 45, 18, 'play', '2026-03-04 17:00:00', 0, 228442, 'IT', 'smart_tv'),
    (27, 34, NULL, 'play', '2026-03-08 08:00:00', 0, 164696, 'ES', 'tablet'),
    (6, 15, 9, 'play', '2026-03-20 08:45:00', 0, 131290, 'ES', 'tablet'),
    (36, 19, 13, 'play', '2026-03-12 10:30:00', 0, 154786, 'IT', 'desktop'),
    (6, 12, NULL, 'play', '2026-03-19 18:15:00', 0, 139932, 'US', 'mobile'),
    (20, 13, 17, 'skip', '2026-03-08 17:45:00', 15870, 15870, 'GB', 'other'),
    (33, 41, NULL, 'play', '2026-03-20 22:45:00', 0, 136562, 'US', 'other'),
    (40, 36, 2, 'play', '2026-03-24 20:15:00', 0, 196725, 'GB', 'smart_tv'),
    (30, 7, NULL, 'play', '2026-03-11 19:45:00', 0, 158929, 'JP', 'tablet'),
    (28, 26, 18, 'play', '2026-03-08 11:45:00', 0, 147267, 'US', 'smart_tv'),
    (32, 22, 3, 'play', '2026-03-08 07:00:00', 0, 146710, 'MX', 'tablet'),
    (14, 10, 18, 'save', '2026-03-29 18:30:00', 0, 182905, 'KR', 'mobile'),
    (24, 37, 16, 'play', '2026-03-03 16:00:00', 0, 169419, 'IT', 'mobile'),
    (28, 13, 11, 'play', '2026-03-15 15:30:00', 0, 194769, 'MX', 'other'),
    (16, 2, 15, 'play', '2026-03-12 21:45:00', 0, 123441, 'JP', 'mobile'),
    (19, 26, 17, 'play', '2026-03-31 11:15:00', 0, 100329, 'CA', 'tablet'),
    (16, 46, 2, 'play', '2026-04-23 18:15:00', 0, 180675, 'CA', 'desktop'),
    (16, 31, NULL, 'play', '2026-04-08 06:30:00', 0, 206094, 'US', 'other'),
    (33, 4, 10, 'play', '2026-04-21 21:45:00', 0, 106330, 'US', 'mobile'),
    (26, 3, NULL, 'play', '2026-04-11 16:30:00', 0, 165136, 'JP', 'mobile'),
    (16, 3, NULL, 'play', '2026-04-03 21:15:00', 0, 221353, 'GB', 'mobile'),
    (40, 8, 17, 'play', '2026-04-16 07:30:00', 0, 179255, 'BR', 'other'),
    (21, 19, NULL, 'skip', '2026-04-01 18:45:00', 17636, 17636, 'US', 'mobile'),
    (32, 3, NULL, 'play', '2026-04-17 18:45:00', 0, 207394, 'JP', 'mobile'),
    (16, 41, 1, 'play', '2026-04-28 18:15:00', 0, 158893, 'US', 'desktop'),
    (2, 1, 6, 'play', '2026-04-07 06:15:00', 0, 128813, 'AU', 'smart_tv'),
    (23, 34, 15, 'play', '2026-04-15 08:30:00', 0, 136075, 'ES', 'mobile'),
    (23, 4, 7, 'skip', '2026-04-25 18:45:00', 27475, 27475, 'KR', 'mobile'),
    (11, 17, NULL, 'share', '2026-04-14 08:15:00', 0, 253220, 'GB', 'mobile'),
    (19, 27, 1, 'play', '2026-04-27 16:45:00', 0, 208511, 'ES', 'tablet'),
    (2, 28, NULL, 'play', '2026-04-04 07:15:00', 0, 123187, 'IT', 'mobile'),
    (30, 8, NULL, 'play', '2026-04-26 18:30:00', 0, 210140, 'KR', 'mobile'),
    (32, 37, 6, 'play', '2026-04-10 08:45:00', 0, 159768, 'MX', 'desktop'),
    (22, 40, 6, 'play', '2026-04-27 15:45:00', 0, 198982, 'US', 'desktop'),
    (14, 5, 7, 'play', '2026-04-04 17:30:00', 0, 204290, 'ES', 'other'),
    (9, 47, 12, 'play', '2026-04-18 14:15:00', 0, 154749, 'CO', 'mobile'),
    (14, 47, 16, 'play', '2026-04-14 23:30:00', 0, 164793, 'US', 'other'),
    (19, 6, 8, 'play', '2026-04-13 13:15:00', 0, 184148, 'IT', 'desktop'),
    (28, 37, 18, 'play', '2026-04-29 06:15:00', 0, 101592, 'ES', 'desktop'),
    (10, 28, NULL, 'save', '2026-04-02 21:15:00', 0, 132244, 'KR', 'mobile'),
    (20, 2, NULL, 'play', '2026-04-01 12:45:00', 0, 130675, 'MX', 'mobile'),
    (10, 35, 11, 'play', '2026-04-04 20:15:00', 0, 152800, 'IT', 'other'),
    (27, 25, 17, 'save', '2026-04-10 21:30:00', 0, 174259, 'BR', 'mobile'),
    (40, 13, 16, 'play', '2026-04-07 06:30:00', 0, 337103, 'ES', 'mobile'),
    (18, 47, 6, 'play', '2026-04-24 08:45:00', 0, 170522, 'CO', 'other'),
    (9, 34, 11, 'skip', '2026-04-27 14:00:00', 9329, 9329, 'GB', 'other'),
    (23, 8, 9, 'play', '2026-04-11 12:15:00', 0, 216014, 'GB', 'mobile'),
    (23, 38, 7, 'play', '2026-04-19 21:45:00', 0, 196132, 'JP', 'tablet'),
    (2, 21, NULL, 'save', '2026-04-04 10:45:00', 0, 121752, 'MX', 'mobile'),
    (18, 7, 7, 'play', '2026-04-09 16:00:00', 0, 121218, 'IT', 'other'),
    (18, 27, 16, 'play', '2026-04-30 13:45:00', 0, 183856, 'IT', 'desktop'),
    (5, 8, 12, 'share', '2026-04-26 06:15:00', 0, 240265, 'AU', 'mobile'),
    (34, 45, 4, 'play', '2026-04-19 13:30:00', 0, 210479, 'US', 'mobile'),
    (4, 15, 7, 'share', '2026-04-09 13:30:00', 0, 130909, 'IT', 'tablet'),
    (26, 40, NULL, 'play', '2026-04-28 06:45:00', 0, 116542, 'KR', 'smart_tv'),
    (4, 46, 4, 'play', '2026-04-19 23:00:00', 0, 130347, 'MX', 'smart_tv'),
    (31, 41, 3, 'play', '2026-04-14 08:15:00', 0, 172638, 'AU', 'mobile'),
    (4, 45, NULL, 'play', '2026-04-13 13:15:00', 0, 184064, 'IT', 'desktop'),
    (34, 29, 6, 'share', '2026-04-28 13:00:00', 0, 170610, 'BR', 'tablet'),
    (40, 23, 2, 'skip', '2026-04-06 21:45:00', 16957, 16957, 'KR', 'mobile'),
    (39, 21, 17, 'skip', '2026-04-09 18:15:00', 27337, 27337, 'US', 'mobile'),
    (40, 29, 6, 'play', '2026-04-09 13:15:00', 0, 126899, 'BR', 'desktop'),
    (5, 46, 2, 'play', '2026-04-09 17:15:00', 0, 174912, 'GB', 'mobile'),
    (16, 29, 5, 'play', '2026-04-24 08:45:00', 0, 159524, 'JP', 'desktop'),
    (36, 42, 18, 'play', '2026-04-28 11:00:00', 0, 156891, 'CO', 'mobile'),
    (14, 31, 3, 'play', '2026-04-07 17:15:00', 0, 204356, 'US', 'mobile'),
    (31, 44, 4, 'play', '2026-04-27 22:00:00', 0, 166286, 'MX', 'mobile'),
    (16, 7, 7, 'skip', '2026-04-12 07:45:00', 7024, 7024, 'KR', 'desktop'),
    (28, 18, 17, 'play', '2026-04-01 21:45:00', 0, 145659, 'CO', 'desktop'),
    (40, 26, NULL, 'play', '2026-04-19 20:00:00', 0, 163222, 'GB', 'other'),
    (40, 8, 15, 'play', '2026-04-10 17:15:00', 0, 206908, 'BR', 'mobile'),
    (14, 6, 1, 'play', '2026-04-16 08:45:00', 0, 120967, 'MX', 'other'),
    (40, 10, NULL, 'save', '2026-04-30 18:15:00', 0, 186486, 'MX', 'mobile'),
    (10, 17, 12, 'play', '2026-04-30 11:00:00', 0, 260329, 'GB', 'tablet'),
    (13, 26, NULL, 'play', '2026-04-10 16:15:00', 0, 172146, 'IT', 'smart_tv'),
    (19, 31, 14, 'share', '2026-04-04 22:45:00', 0, 134612, 'IT', 'smart_tv'),
    (34, 13, 3, 'share', '2026-04-25 19:30:00', 0, 234104, 'MX', 'other'),
    (26, 42, 3, 'save', '2026-04-02 06:00:00', 0, 183758, 'AU', 'mobile'),
    (30, 47, 15, 'play', '2026-04-06 11:00:00', 0, 122933, 'KR', 'mobile'),
    (24, 32, NULL, 'play', '2026-04-09 09:45:00', 0, 186826, 'MX', 'mobile'),
    (9, 45, 2, 'save', '2026-04-03 15:00:00', 0, 137018, 'IT', 'mobile'),
    (1, 40, 13, 'play', '2026-04-03 11:15:00', 0, 203512, 'US', 'smart_tv'),
    (38, 9, 3, 'play', '2026-04-10 13:15:00', 0, 211217, 'US', 'desktop'),
    (20, 18, NULL, 'play', '2026-04-02 18:00:00', 0, 175910, 'IT', 'mobile'),
    (26, 2, 17, 'skip', '2026-04-19 20:15:00', 29250, 29250, 'KR', 'mobile'),
    (22, 9, 10, 'play', '2026-04-04 21:45:00', 0, 191397, 'AU', 'other'),
    (33, 12, 14, 'share', '2026-04-05 20:15:00', 0, 170896, 'AU', 'desktop'),
    (16, 3, 7, 'skip', '2026-05-13 18:00:00', 15787, 15787, 'ES', 'desktop'),
    (13, 12, 18, 'play', '2026-05-20 18:15:00', 0, 173361, 'US', 'smart_tv'),
    (34, 25, 16, 'play', '2026-05-20 11:15:00', 0, 193128, 'US', 'other'),
    (32, 16, 18, 'play', '2026-05-21 08:45:00', 0, 201854, 'US', 'mobile'),
    (24, 36, 9, 'play', '2026-05-24 18:00:00', 0, 163659, 'AU', 'mobile'),
    (11, 31, 10, 'play', '2026-05-17 15:45:00', 0, 140486, 'GB', 'mobile'),
    (35, 42, 18, 'play', '2026-05-08 20:15:00', 0, 192765, 'IT', 'desktop'),
    (2, 12, 15, 'play', '2026-05-09 22:30:00', 0, 174067, 'US', 'other'),
    (30, 34, 17, 'play', '2026-05-29 17:30:00', 0, 240865, 'KR', 'other'),
    (35, 6, 13, 'play', '2026-05-24 22:45:00', 0, 164842, 'US', 'desktop'),
    (9, 30, NULL, 'play', '2026-05-06 15:30:00', 0, 118669, 'AU', 'other'),
    (2, 2, NULL, 'play', '2026-05-02 09:45:00', 0, 121168, 'GB', 'desktop'),
    (17, 9, 6, 'play', '2026-05-03 20:30:00', 0, 171773, 'IT', 'mobile'),
    (19, 2, 13, 'play', '2026-05-17 17:45:00', 0, 130686, 'ES', 'desktop'),
    (15, 42, 1, 'skip', '2026-05-07 10:30:00', 3805, 3805, 'BR', 'smart_tv'),
    (17, 26, NULL, 'play', '2026-05-06 14:00:00', 0, 134480, 'BR', 'desktop'),
    (27, 38, 16, 'play', '2026-05-26 20:45:00', 0, 131254, 'BR', 'mobile'),
    (2, 40, NULL, 'play', '2026-05-09 06:15:00', 0, 184277, 'KR', 'desktop'),
    (4, 8, 11, 'play', '2026-05-20 12:45:00', 0, 140499, 'US', 'mobile'),
    (9, 16, NULL, 'play', '2026-05-05 23:00:00', 0, 149626, 'JP', 'mobile'),
    (11, 11, NULL, 'play', '2026-05-30 17:00:00', 0, 275676, 'US', 'other'),
    (26, 19, NULL, 'play', '2026-05-01 17:15:00', 0, 127104, 'ES', 'mobile'),
    (5, 35, 1, 'save', '2026-05-02 22:15:00', 0, 103941, 'MX', 'tablet'),
    (20, 39, 3, 'play', '2026-05-29 12:00:00', 0, 157624, 'KR', 'other'),
    (39, 10, 1, 'play', '2026-05-18 14:45:00', 0, 143453, 'CO', 'smart_tv'),
    (1, 34, 13, 'play', '2026-05-30 14:00:00', 0, 134591, 'IT', 'smart_tv'),
    (22, 20, NULL, 'play', '2026-05-01 16:45:00', 0, 181463, 'AU', 'desktop'),
    (31, 4, 9, 'play', '2026-05-10 18:15:00', 0, 134408, 'US', 'mobile'),
    (28, 34, NULL, 'play', '2026-05-12 07:15:00', 0, 149042, 'US', 'desktop'),
    (26, 6, NULL, 'play', '2026-05-19 22:30:00', 0, 115334, 'CA', 'mobile'),
    (13, 39, NULL, 'play', '2026-05-24 15:30:00', 0, 174491, 'US', 'mobile'),
    (22, 7, 11, 'skip', '2026-05-22 09:00:00', 7167, 7167, 'GB', 'smart_tv'),
    (23, 26, 16, 'play', '2026-05-03 08:45:00', 0, 171340, 'CA', 'mobile'),
    (34, 5, 2, 'skip', '2026-05-21 21:15:00', 17845, 17845, 'US', 'desktop'),
    (9, 33, 13, 'play', '2026-05-26 07:45:00', 0, 184500, 'US', 'desktop'),
    (3, 15, NULL, 'skip', '2026-05-17 20:30:00', 16434, 16434, 'US', 'mobile'),
    (13, 46, 16, 'play', '2026-05-20 06:15:00', 0, 187557, 'KR', 'mobile'),
    (29, 34, NULL, 'play', '2026-05-30 09:45:00', 0, 161512, 'ES', 'other'),
    (19, 29, 17, 'play', '2026-05-22 18:15:00', 0, 147385, 'US', 'mobile'),
    (20, 34, 12, 'play', '2026-05-30 13:00:00', 0, 217087, 'BR', 'mobile'),
    (40, 4, 14, 'share', '2026-05-07 14:00:00', 0, 144832, 'CA', 'mobile'),
    (2, 12, 4, 'play', '2026-05-31 15:45:00', 0, 152788, 'US', 'tablet'),
    (3, 16, 18, 'play', '2026-05-05 19:45:00', 0, 184039, 'US', 'mobile'),
    (37, 30, NULL, 'skip', '2026-05-30 22:15:00', 21303, 21303, 'CA', 'smart_tv'),
    (10, 16, NULL, 'skip', '2026-05-01 12:15:00', 28175, 28175, 'CO', 'mobile'),
    (24, 13, 15, 'play', '2026-05-08 07:45:00', 0, 336273, 'CO', 'tablet'),
    (2, 4, NULL, 'play', '2026-05-14 08:00:00', 0, 172840, 'CO', 'desktop'),
    (16, 1, NULL, 'play', '2026-05-18 17:45:00', 0, 128308, 'ES', 'mobile'),
    (33, 12, 12, 'skip', '2026-05-05 20:45:00', 13684, 13684, 'MX', 'mobile'),
    (34, 7, 9, 'play', '2026-05-23 11:30:00', 0, 167854, 'JP', 'smart_tv'),
    (37, 24, 1, 'play', '2026-05-27 20:00:00', 0, 162051, 'US', 'mobile'),
    (32, 46, 1, 'play', '2026-05-19 22:15:00', 0, 141522, 'AU', 'smart_tv'),
    (27, 4, 16, 'play', '2026-05-28 15:00:00', 0, 147782, 'GB', 'smart_tv'),
    (33, 28, 4, 'play', '2026-05-19 22:30:00', 0, 133467, 'GB', 'desktop'),
    (31, 2, 11, 'skip', '2026-05-23 23:00:00', 11184, 11184, 'US', 'tablet'),
    (2, 47, 4, 'play', '2026-05-15 11:45:00', 0, 115992, 'IT', 'other'),
    (28, 36, 5, 'play', '2026-05-15 21:45:00', 0, 137963, 'IT', 'mobile'),
    (13, 8, 2, 'share', '2026-05-03 16:00:00', 0, 148547, 'US', 'desktop'),
    (11, 28, 7, 'play', '2026-05-09 15:30:00', 0, 115609, 'JP', 'mobile'),
    (26, 41, 11, 'play', '2026-05-16 23:45:00', 0, 130162, 'US', 'desktop'),
    (15, 1, 3, 'play', '2026-05-14 21:00:00', 0, 179355, 'IT', 'mobile'),
    (10, 47, 2, 'play', '2026-05-13 18:00:00', 0, 178945, 'US', 'smart_tv'),
    (2, 43, NULL, 'share', '2026-05-04 20:45:00', 0, 136353, 'GB', 'mobile'),
    (6, 10, 16, 'play', '2026-05-04 17:00:00', 0, 168401, 'JP', 'tablet'),
    (13, 17, 14, 'skip', '2026-05-23 20:45:00', 6804, 6804, 'ES', 'mobile'),
    (22, 28, NULL, 'play', '2026-05-23 17:30:00', 0, 155380, 'CO', 'other'),
    (22, 10, 16, 'play', '2026-05-27 13:45:00', 0, 129847, 'JP', 'other'),
    (20, 9, 14, 'play', '2026-05-11 09:30:00', 0, 146909, 'CA', 'desktop'),
    (24, 22, 16, 'play', '2026-05-23 14:15:00', 0, 164908, 'GB', 'mobile'),
    (9, 17, NULL, 'play', '2026-05-01 06:15:00', 0, 315359, 'GB', 'tablet'),
    (2, 46, NULL, 'play', '2026-05-30 06:00:00', 0, 205280, 'AU', 'mobile'),
    (29, 14, 16, 'play', '2026-06-18 08:45:00', 0, 201224, 'MX', 'mobile'),
    (15, 14, 9, 'skip', '2026-06-23 19:30:00', 23012, 23012, 'ES', 'mobile'),
    (17, 28, 6, 'skip', '2026-06-26 13:30:00', 23519, 23519, 'ES', 'mobile'),
    (19, 29, 2, 'play', '2026-06-02 14:00:00', 0, 129300, 'MX', 'other'),
    (34, 37, 10, 'play', '2026-06-03 22:30:00', 0, 128569, 'MX', 'tablet'),
    (24, 12, 14, 'play', '2026-06-15 19:45:00', 0, 126525, 'IT', 'mobile'),
    (28, 3, 15, 'skip', '2026-06-04 08:00:00', 22660, 22660, 'MX', 'mobile'),
    (26, 9, 17, 'play', '2026-06-25 08:00:00', 0, 238537, 'US', 'smart_tv'),
    (3, 9, NULL, 'play', '2026-06-27 07:15:00', 0, 212207, 'CO', 'mobile'),
    (5, 45, 11, 'play', '2026-06-01 18:00:00', 0, 215257, 'BR', 'other'),
    (37, 15, NULL, 'play', '2026-06-14 22:30:00', 0, 88447, 'CO', 'mobile'),
    (17, 3, NULL, 'save', '2026-06-27 15:00:00', 0, 170384, 'US', 'mobile'),
    (30, 10, 6, 'play', '2026-06-22 09:45:00', 0, 179441, 'IT', 'tablet'),
    (21, 4, 17, 'play', '2026-06-17 08:30:00', 0, 163986, 'CO', 'tablet'),
    (1, 3, NULL, 'play', '2026-06-20 20:00:00', 0, 155663, 'AU', 'smart_tv'),
    (31, 45, NULL, 'play', '2026-06-19 06:45:00', 0, 130561, 'MX', 'mobile'),
    (16, 27, NULL, 'skip', '2026-06-19 09:45:00', 9119, 9119, 'AU', 'mobile'),
    (16, 13, 6, 'play', '2026-06-04 19:00:00', 0, 321651, 'US', 'mobile'),
    (26, 40, 10, 'play', '2026-06-28 13:15:00', 0, 176397, 'US', 'mobile'),
    (33, 4, 6, 'play', '2026-06-25 13:45:00', 0, 130895, 'GB', 'tablet'),
    (3, 23, NULL, 'play', '2026-06-29 19:30:00', 0, 98292, 'KR', 'mobile'),
    (20, 32, 13, 'play', '2026-06-19 14:45:00', 0, 178764, 'GB', 'mobile'),
    (15, 15, NULL, 'play', '2026-06-26 20:15:00', 0, 92914, 'ES', 'mobile'),
    (20, 26, 10, 'play', '2026-06-27 14:45:00', 0, 163925, 'JP', 'smart_tv'),
    (32, 38, 4, 'save', '2026-06-29 22:15:00', 0, 188104, 'US', 'mobile'),
    (31, 18, 12, 'play', '2026-06-03 14:00:00', 0, 134004, 'KR', 'mobile'),
    (33, 3, 11, 'play', '2026-06-15 17:00:00', 0, 213750, 'MX', 'desktop'),
    (1, 33, NULL, 'share', '2026-06-23 17:00:00', 0, 125088, 'IT', 'mobile'),
    (3, 5, 14, 'play', '2026-06-15 14:45:00', 0, 190687, 'ES', 'mobile'),
    (5, 40, 10, 'play', '2026-06-27 09:15:00', 0, 115203, 'US', 'mobile'),
    (13, 48, NULL, 'play', '2026-06-16 10:30:00', 0, 174873, 'US', 'other'),
    (20, 12, 10, 'play', '2026-06-12 15:15:00', 0, 183752, 'IT', 'mobile'),
    (1, 18, 11, 'skip', '2026-06-21 17:30:00', 22665, 22665, 'US', 'tablet'),
    (25, 16, NULL, 'play', '2026-06-06 20:00:00', 0, 159851, 'AU', 'mobile'),
    (29, 15, 13, 'play', '2026-06-26 19:30:00', 0, 146904, 'CO', 'mobile'),
    (27, 4, NULL, 'play', '2026-06-30 14:00:00', 0, 156739, 'KR', 'tablet'),
    (26, 11, NULL, 'play', '2026-06-17 09:00:00', 0, 185223, 'GB', 'smart_tv'),
    (20, 10, 6, 'play', '2026-06-03 13:15:00', 0, 169019, 'MX', 'other'),
    (3, 8, 1, 'play', '2026-06-11 13:15:00', 0, 188674, 'KR', 'mobile'),
    (33, 31, 4, 'play', '2026-06-03 15:00:00', 0, 183140, 'AU', 'desktop'),
    (23, 12, 11, 'play', '2026-06-11 16:15:00', 0, 219813, 'BR', 'desktop'),
    (20, 44, 17, 'play', '2026-06-25 23:15:00', 0, 160984, 'US', 'mobile'),
    (24, 31, 9, 'skip', '2026-06-17 12:45:00', 17821, 17821, 'KR', 'mobile'),
    (3, 27, 17, 'play', '2026-06-13 12:15:00', 0, 214724, 'GB', 'tablet'),
    (26, 9, NULL, 'play', '2026-06-21 10:30:00', 0, 240196, 'KR', 'mobile'),
    (23, 31, NULL, 'skip', '2026-06-03 18:30:00', 22370, 22370, 'ES', 'mobile'),
    (23, 36, 9, 'play', '2026-06-19 17:15:00', 0, 129701, 'US', 'smart_tv'),
    (24, 36, NULL, 'play', '2026-06-13 19:45:00', 0, 153410, 'AU', 'desktop'),
    (29, 32, 11, 'play', '2026-06-30 20:45:00', 0, 164897, 'CO', 'desktop'),
    (22, 26, 10, 'play', '2026-06-05 11:00:00', 0, 95804, 'IT', 'mobile'),
    (3, 14, 8, 'save', '2026-06-10 12:30:00', 0, 137451, 'US', 'tablet'),
    (25, 30, NULL, 'play', '2026-06-13 11:30:00', 0, 134826, 'IT', 'mobile'),
    (14, 23, 1, 'skip', '2026-06-11 19:00:00', 18155, 18155, 'CA', 'smart_tv'),
    (5, 29, 11, 'skip', '2026-06-08 19:00:00', 21881, 21881, 'CA', 'smart_tv'),
    (9, 33, 17, 'share', '2026-06-23 08:45:00', 0, 161925, 'BR', 'mobile'),
    (34, 20, NULL, 'play', '2026-06-04 15:45:00', 0, 203103, 'GB', 'other'),
    (35, 27, 16, 'skip', '2026-06-08 11:00:00', 26831, 26831, 'US', 'mobile'),
    (1, 13, NULL, 'play', '2026-06-16 10:15:00', 0, 271975, 'ES', 'mobile'),
    (24, 36, 9, 'play', '2026-06-13 07:15:00', 0, 183235, 'AU', 'other'),
    (31, 3, 11, 'play', '2026-06-01 18:15:00', 0, 209912, 'GB', 'mobile'),
    (36, 6, 4, 'save', '2026-06-29 13:30:00', 0, 173983, 'IT', 'tablet'),
    (6, 20, 2, 'play', '2026-06-23 18:45:00', 0, 202239, 'ES', 'other'),
    (29, 25, NULL, 'play', '2026-06-18 09:30:00', 0, 157741, 'US', 'mobile'),
    (36, 2, NULL, 'play', '2026-06-29 09:00:00', 0, 155100, 'IT', 'mobile'),
    (11, 35, 18, 'skip', '2026-06-20 20:45:00', 23862, 23862, 'JP', 'tablet'),
    (19, 37, 4, 'skip', '2026-06-03 12:00:00', 4398, 4398, 'JP', 'mobile'),
    (14, 38, 14, 'skip', '2026-06-03 18:00:00', 4133, 4133, 'CO', 'other'),
    (35, 33, NULL, 'play', '2026-06-30 21:30:00', 0, 185190, 'GB', 'smart_tv'),
    (39, 39, 8, 'play', '2026-06-07 20:45:00', 0, 218917, 'CO', 'desktop'),
    (32, 8, NULL, 'play', '2026-06-10 06:45:00', 0, 228976, 'IT', 'smart_tv'),
    (20, 46, NULL, 'skip', '2026-06-01 10:30:00', 29983, 29983, 'IT', 'mobile'),
    (27, 47, 18, 'play', '2026-06-27 06:15:00', 0, 141543, 'MX', 'tablet'),
    (33, 32, 14, 'play', '2026-06-15 10:00:00', 0, 158493, 'GB', 'smart_tv'),
    (4, 41, NULL, 'play', '2026-06-10 16:30:00', 0, 171978, 'US', 'mobile'),
    (38, 22, 11, 'play', '2026-06-12 06:15:00', 0, 160928, 'GB', 'mobile'),
    (21, 22, 2, 'play', '2026-06-04 10:45:00', 0, 178560, 'KR', 'mobile'),
    (3, 15, 11, 'play', '2026-06-19 18:15:00', 0, 102628, 'US', 'smart_tv'),
    (24, 23, 12, 'play', '2026-06-12 12:30:00', 0, 174452, 'BR', 'tablet'),
    (24, 4, 7, 'play', '2026-07-04 21:00:00', 0, 190351, 'KR', 'smart_tv'),
    (40, 3, 18, 'play', '2026-07-07 14:15:00', 0, 193843, 'US', 'other'),
    (20, 22, 11, 'play', '2026-07-03 10:30:00', 0, 140505, 'AU', 'mobile'),
    (17, 30, 10, 'skip', '2026-07-17 12:00:00', 16408, 16408, 'MX', 'mobile'),
    (28, 4, 7, 'play', '2026-07-04 21:15:00', 0, 150243, 'MX', 'mobile'),
    (13, 23, 7, 'play', '2026-07-14 06:00:00', 0, 104468, 'IT', 'smart_tv'),
    (13, 19, NULL, 'skip', '2026-07-11 13:45:00', 23227, 23227, 'MX', 'desktop'),
    (22, 26, 2, 'play', '2026-07-08 06:45:00', 0, 120552, 'ES', 'desktop'),
    (37, 6, 7, 'skip', '2026-07-14 12:30:00', 5347, 5347, 'US', 'tablet'),
    (33, 19, NULL, 'save', '2026-07-04 11:30:00', 0, 137798, 'ES', 'desktop'),
    (21, 32, 14, 'share', '2026-07-13 17:30:00', 0, 160240, 'CO', 'other'),
    (19, 34, 7, 'skip', '2026-07-16 13:45:00', 18874, 18874, 'GB', 'mobile'),
    (10, 4, 11, 'play', '2026-07-08 06:15:00', 0, 109907, 'CA', 'mobile'),
    (17, 35, NULL, 'play', '2026-07-02 06:30:00', 0, 144469, 'AU', 'desktop'),
    (15, 16, 9, 'play', '2026-07-01 23:30:00', 0, 193919, 'IT', 'mobile'),
    (16, 19, NULL, 'play', '2026-07-01 23:30:00', 0, 181544, 'US', 'mobile'),
    (21, 39, 6, 'play', '2026-07-16 18:30:00', 0, 176241, 'BR', 'desktop'),
    (30, 35, 5, 'play', '2026-07-10 15:45:00', 0, 148237, 'US', 'smart_tv'),
    (27, 47, NULL, 'play', '2026-07-11 06:15:00', 0, 128076, 'CO', 'mobile'),
    (14, 31, 12, 'play', '2026-07-05 23:15:00', 0, 137625, 'JP', 'desktop'),
    (37, 40, NULL, 'play', '2026-07-08 22:00:00', 0, 121368, 'CA', 'tablet'),
    (9, 7, 14, 'play', '2026-07-07 12:15:00', 0, 163416, 'US', 'mobile'),
    (22, 35, 4, 'play', '2026-07-17 12:00:00', 0, 124849, 'GB', 'mobile'),
    (5, 39, 2, 'play', '2026-07-08 20:00:00', 0, 154639, 'JP', 'mobile'),
    (20, 37, 14, 'play', '2026-07-06 11:00:00', 0, 141299, 'US', 'mobile'),
    (13, 47, 16, 'play', '2026-07-07 18:00:00', 0, 106231, 'JP', 'mobile'),
    (14, 12, 9, 'play', '2026-07-12 19:15:00', 0, 132480, 'GB', 'mobile'),
    (17, 13, 16, 'skip', '2026-07-01 10:30:00', 4847, 4847, 'ES', 'mobile'),
    (35, 2, NULL, 'play', '2026-07-14 21:00:00', 0, 127085, 'GB', 'mobile'),
    (15, 36, 10, 'share', '2026-07-09 09:00:00', 0, 150871, 'MX', 'desktop'),
    (15, 7, 17, 'play', '2026-07-08 23:15:00', 0, 115098, 'US', 'smart_tv'),
    (18, 44, 18, 'play', '2026-07-11 06:30:00', 0, 100371, 'ES', 'other'),
    (14, 46, 4, 'play', '2026-07-12 10:15:00', 0, 196796, 'CO', 'smart_tv'),
    (1, 30, NULL, 'skip', '2026-07-03 11:15:00', 24159, 24159, 'US', 'mobile'),
    (9, 15, 3, 'save', '2026-07-17 12:00:00', 0, 146814, 'CA', 'mobile'),
    (24, 30, 16, 'play', '2026-07-15 14:15:00', 0, 99230, 'US', 'mobile'),
    (33, 43, 13, 'play', '2026-07-12 11:30:00', 0, 112106, 'JP', 'tablet'),
    (20, 27, 15, 'play', '2026-07-06 21:45:00', 0, 206870, 'US', 'tablet'),
    (15, 14, 17, 'play', '2026-07-02 09:30:00', 0, 143720, 'BR', 'smart_tv'),
    (15, 22, 2, 'play', '2026-07-15 07:45:00', 0, 197841, 'IT', 'tablet'),
    (9, 43, 7, 'play', '2026-07-13 11:15:00', 0, 134431, 'BR', 'other'),
    (1, 27, NULL, 'play', '2026-07-13 15:30:00', 0, 200663, 'US', 'tablet'),
    (31, 37, 14, 'play', '2026-07-01 12:00:00', 0, 112572, 'MX', 'mobile'),
    (15, 43, NULL, 'play', '2026-07-11 19:00:00', 0, 150557, 'MX', 'other'),
    (37, 48, 18, 'play', '2026-07-03 07:30:00', 0, 173736, 'IT', 'mobile'),
    (5, 3, 2, 'play', '2026-07-11 13:15:00', 0, 144892, 'JP', 'other'),
    (32, 3, NULL, 'play', '2026-07-16 11:15:00', 0, 226604, 'US', 'mobile'),
    (28, 3, NULL, 'skip', '2026-07-11 16:15:00', 28455, 28455, 'CA', 'other'),
    (10, 39, 5, 'play', '2026-07-04 06:45:00', 0, 145110, 'US', 'mobile'),
    (32, 30, 2, 'save', '2026-07-15 21:45:00', 0, 125208, 'ES', 'tablet'),
    (22, 8, 5, 'play', '2026-07-08 20:00:00', 0, 210878, 'CO', 'mobile'),
    (11, 46, NULL, 'save', '2026-07-15 23:45:00', 0, 127613, 'CO', 'smart_tv'),
    (22, 21, NULL, 'play', '2026-07-12 06:15:00', 0, 123311, 'CO', 'mobile'),
    (28, 47, NULL, 'skip', '2026-07-03 23:45:00', 3773, 3773, 'JP', 'mobile'),
    (40, 30, 15, 'share', '2026-07-15 18:30:00', 0, 165297, 'US', 'mobile'),
    (35, 30, NULL, 'play', '2026-07-05 13:00:00', 0, 118350, 'CO', 'other'),
    (33, 4, NULL, 'play', '2026-07-03 07:30:00', 0, 189419, 'KR', 'mobile'),
    (23, 36, 5, 'play', '2026-07-15 11:30:00', 0, 177101, 'GB', 'mobile'),
    (31, 1, 17, 'play', '2026-07-05 23:00:00', 0, 185686, 'US', 'mobile'),
    (18, 13, 11, 'skip', '2026-07-06 07:15:00', 20093, 20093, 'US', 'mobile'),
    (6, 33, 2, 'play', '2026-07-14 08:00:00', 0, 144469, 'US', 'mobile'),
    (40, 28, 9, 'play', '2026-07-16 13:00:00', 0, 136731, 'MX', 'mobile'),
    (18, 7, 2, 'play', '2026-07-07 11:30:00', 0, 161196, 'GB', 'mobile'),
    (6, 29, NULL, 'play', '2026-07-13 20:00:00', 0, 142346, 'IT', 'other'),
    (37, 21, 10, 'play', '2026-07-05 11:45:00', 0, 122320, 'BR', 'mobile'),
    (2, 31, 18, 'play', '2026-07-09 06:00:00', 0, 167405, 'AU', 'mobile'),
    (1, 7, NULL, 'play', '2026-07-16 06:00:00', 0, 159305, 'CO', 'desktop'),
    (23, 34, NULL, 'play', '2026-07-01 20:15:00', 0, 174037, 'MX', 'mobile'),
    (18, 11, 8, 'play', '2026-07-07 13:00:00', 0, 194169, 'US', 'desktop'),
    (28, 21, NULL, 'play', '2026-07-01 18:45:00', 0, 165375, 'MX', 'tablet'),
    (31, 45, 9, 'play', '2026-07-11 12:30:00', 0, 220320, 'US', 'mobile'),
    (37, 5, 10, 'play', '2026-07-03 19:00:00', 0, 192766, 'AU', 'tablet'),
    (39, 7, 9, 'save', '2026-07-04 17:45:00', 0, 160168, 'KR', 'tablet'),
    (14, 30, 8, 'play', '2026-07-14 20:30:00', 0, 131724, 'US', 'smart_tv'),
    (10, 26, NULL, 'play', '2026-07-17 12:00:00', 0, 154850, 'ES', 'tablet'),
    (36, 21, 11, 'skip', '2026-07-04 12:30:00', 20310, 20310, 'BR', 'desktop'),
    (13, 30, 8, 'play', '2026-07-10 11:30:00', 0, 158399, 'IT', 'smart_tv');


-- 7. engagement

INSERT INTO user_liked_tracks (user_id, track_id, liked_at) VALUES
    (1, 42, '2026-04-16 11:00:00'),
    (1, 41, '2025-04-15 20:00:00'),
    (2, 32, '2026-01-05 21:00:00'),
    (2, 46, '2026-01-20 21:00:00'),
    (2, 45, '2025-11-19 10:00:00'),
    (2, 44, '2026-05-10 08:00:00'),
    (3, 47, '2025-12-23 09:00:00'),
    (3, 48, '2025-03-03 12:00:00'),
    (3, 33, '2026-02-12 18:00:00'),
    (3, 36, '2026-01-15 20:00:00'),
    (4, 39, '2025-02-21 14:00:00'),
    (5, 45, '2026-03-15 08:00:00'),
    (5, 33, '2025-04-10 15:00:00'),
    (5, 43, '2026-04-21 11:00:00'),
    (5, 39, '2025-04-29 21:00:00'),
    (5, 48, '2025-05-27 19:00:00'),
    (5, 35, '2026-02-04 12:00:00'),
    (6, 41, '2025-06-12 17:00:00'),
    (6, 44, '2026-01-19 08:00:00'),
    (6, 35, '2026-05-08 21:00:00'),
    (6, 31, '2025-07-14 09:00:00'),
    (6, 32, '2025-05-22 10:00:00'),
    (9, 42, '2025-08-29 07:00:00'),
    (9, 33, '2026-04-04 15:00:00'),
    (9, 47, '2026-02-03 14:00:00'),
    (9, 48, '2026-01-15 16:00:00'),
    (10, 39, '2025-04-25 20:00:00'),
    (10, 34, '2026-04-10 15:00:00'),
    (10, 35, '2026-02-20 19:00:00'),
    (11, 39, '2025-12-20 12:00:00'),
    (11, 38, '2026-02-24 19:00:00'),
    (13, 37, '2025-07-01 18:00:00'),
    (13, 45, '2025-11-15 11:00:00'),
    (13, 46, '2025-11-03 08:00:00'),
    (14, 45, '2026-03-09 15:00:00'),
    (15, 48, '2025-07-30 19:00:00'),
    (15, 45, '2025-11-11 17:00:00'),
    (16, 40, '2026-06-05 16:00:00'),
    (16, 42, '2025-09-18 14:00:00'),
    (17, 39, '2026-03-30 13:00:00'),
    (17, 44, '2025-05-11 16:00:00'),
    (17, 43, '2026-01-23 21:00:00'),
    (17, 33, '2026-05-20 17:00:00'),
    (18, 42, '2025-12-04 08:00:00'),
    (18, 35, '2026-05-02 17:00:00'),
    (19, 45, '2026-01-13 19:00:00'),
    (20, 40, '2025-02-11 14:00:00'),
    (20, 42, '2025-08-05 16:00:00'),
    (21, 28, '2025-10-10 11:00:00'),
    (21, 6, '2026-04-14 15:00:00'),
    (21, 41, '2026-03-23 19:00:00'),
    (22, 8, '2026-01-07 11:00:00'),
    (22, 5, '2025-11-11 13:00:00'),
    (22, 2, '2025-03-10 11:00:00'),
    (22, 45, '2026-05-12 09:00:00'),
    (22, 13, '2026-01-02 17:00:00'),
    (23, 2, '2025-09-22 14:00:00'),
    (23, 43, '2025-08-05 13:00:00'),
    (23, 48, '2026-03-05 13:00:00'),
    (23, 17, '2026-03-30 10:00:00'),
    (23, 34, '2025-12-31 15:00:00'),
    (23, 20, '2025-10-27 07:00:00'),
    (24, 6, '2025-05-21 09:00:00'),
    (24, 31, '2025-06-11 07:00:00'),
    (24, 32, '2025-09-08 09:00:00'),
    (24, 40, '2025-08-03 18:00:00'),
    (25, 47, '2025-09-23 16:00:00'),
    (25, 45, '2026-06-04 08:00:00'),
    (25, 11, '2026-06-18 09:00:00'),
    (25, 25, '2026-06-11 14:00:00'),
    (25, 39, '2025-07-16 14:00:00'),
    (25, 3, '2025-06-17 08:00:00'),
    (26, 13, '2025-06-11 20:00:00'),
    (26, 44, '2025-08-05 11:00:00'),
    (26, 3, '2025-06-15 09:00:00'),
    (26, 10, '2025-03-24 20:00:00'),
    (26, 5, '2025-12-18 08:00:00'),
    (27, 29, '2025-03-11 10:00:00'),
    (28, 25, '2025-06-29 22:00:00'),
    (28, 13, '2026-01-19 14:00:00'),
    (28, 48, '2025-11-21 22:00:00'),
    (28, 10, '2025-05-15 13:00:00'),
    (28, 24, '2026-03-05 09:00:00'),
    (28, 46, '2026-02-14 15:00:00'),
    (29, 9, '2025-09-30 13:00:00'),
    (29, 45, '2025-07-31 17:00:00'),
    (29, 21, '2025-10-17 22:00:00'),
    (29, 12, '2025-03-26 08:00:00'),
    (29, 47, '2025-06-30 13:00:00'),
    (30, 34, '2025-01-30 19:00:00'),
    (30, 27, '2025-08-01 16:00:00'),
    (31, 24, '2026-05-30 13:00:00'),
    (31, 11, '2025-12-10 19:00:00'),
    (31, 22, '2026-05-22 16:00:00'),
    (31, 3, '2026-02-28 21:00:00'),
    (32, 42, '2025-11-20 20:00:00'),
    (32, 31, '2026-06-04 22:00:00'),
    (32, 14, '2026-01-14 17:00:00'),
    (33, 2, '2025-05-04 13:00:00'),
    (33, 5, '2025-11-06 10:00:00'),
    (34, 35, '2025-05-17 19:00:00'),
    (35, 12, '2025-12-07 18:00:00'),
    (35, 27, '2025-02-23 09:00:00'),
    (35, 28, '2025-06-21 11:00:00'),
    (35, 45, '2026-04-19 16:00:00'),
    (36, 8, '2026-05-05 14:00:00'),
    (36, 44, '2025-08-19 11:00:00'),
    (36, 40, '2026-03-04 13:00:00'),
    (36, 21, '2025-11-22 17:00:00'),
    (37, 15, '2025-10-31 17:00:00'),
    (37, 46, '2025-06-12 20:00:00'),
    (37, 43, '2026-07-07 09:00:00'),
    (37, 28, '2025-08-14 19:00:00'),
    (37, 40, '2025-01-26 17:00:00'),
    (38, 1, '2025-08-02 10:00:00'),
    (38, 5, '2025-02-15 07:00:00'),
    (38, 42, '2025-09-20 20:00:00'),
    (38, 13, '2025-09-03 20:00:00'),
    (38, 2, '2025-11-23 08:00:00'),
    (38, 40, '2025-05-23 20:00:00'),
    (39, 45, '2025-10-14 14:00:00'),
    (39, 34, '2025-11-12 22:00:00'),
    (39, 32, '2026-03-09 19:00:00'),
    (40, 38, '2025-06-29 12:00:00'),
    (40, 46, '2026-06-26 22:00:00'),
    (40, 4, '2025-04-20 17:00:00');

INSERT INTO user_follows_artists (user_id, artist_id, followed_at) VALUES
    (21, 5, '2025-07-25 07:00:00'),
    (22, 4, '2025-03-28 11:00:00'),
    (22, 3, '2025-07-27 12:00:00'),
    (23, 8, '2025-09-04 13:00:00'),
    (24, 7, '2026-03-06 15:00:00'),
    (24, 4, '2025-02-05 20:00:00'),
    (25, 7, '2025-04-15 21:00:00'),
    (25, 10, '2026-04-20 09:00:00'),
    (25, 11, '2025-12-04 18:00:00'),
    (26, 11, '2025-06-02 19:00:00'),
    (26, 7, '2025-11-30 11:00:00'),
    (26, 5, '2026-02-06 16:00:00'),
    (27, 7, '2025-10-19 22:00:00'),
    (27, 5, '2025-04-26 16:00:00'),
    (27, 12, '2025-01-24 18:00:00'),
    (28, 4, '2026-05-20 08:00:00'),
    (28, 5, '2025-12-02 15:00:00'),
    (29, 5, '2025-03-22 10:00:00'),
    (30, 4, '2025-07-13 17:00:00'),
    (30, 8, '2025-04-02 10:00:00'),
    (30, 6, '2025-02-15 12:00:00'),
    (31, 9, '2025-02-24 08:00:00'),
    (31, 11, '2026-02-10 12:00:00'),
    (31, 8, '2025-12-26 12:00:00'),
    (32, 1, '2026-01-04 12:00:00'),
    (33, 5, '2026-04-28 13:00:00'),
    (34, 3, '2026-03-24 13:00:00'),
    (35, 9, '2025-12-08 13:00:00'),
    (35, 6, '2025-03-21 18:00:00'),
    (35, 1, '2025-03-19 07:00:00'),
    (36, 3, '2026-04-26 12:00:00'),
    (36, 8, '2025-06-02 15:00:00'),
    (37, 8, '2025-04-17 11:00:00'),
    (37, 3, '2025-09-17 20:00:00'),
    (37, 9, '2025-06-26 17:00:00'),
    (37, 5, '2026-06-06 18:00:00'),
    (38, 5, '2026-05-05 14:00:00'),
    (38, 7, '2025-04-21 22:00:00'),
    (38, 12, '2025-07-01 17:00:00'),
    (38, 8, '2026-05-05 12:00:00'),
    (39, 9, '2025-03-19 16:00:00'),
    (39, 1, '2025-06-16 10:00:00'),
    (39, 8, '2025-07-16 12:00:00'),
    (40, 6, '2025-04-29 20:00:00');

INSERT INTO playlist_tracks (playlist_id, track_id, position, added_at) VALUES
    (7, 31, 30, '2025-04-22 11:00:00'),
    (6, 31, 26, '2025-03-17 13:00:00'),
    (4, 31, 14, '2025-04-24 14:00:00'),
    (14, 31, 7, '2025-04-26 13:00:00'),
    (16, 31, 19, '2025-04-12 17:00:00'),
    (15, 32, 4, '2025-05-08 12:00:00'),
    (10, 32, 7, '2025-03-31 19:00:00'),
    (9, 32, 5, '2025-04-23 08:00:00'),
    (18, 33, 7, '2025-03-23 14:00:00'),
    (8, 33, 31, '2025-05-08 15:00:00'),
    (7, 33, 27, '2025-03-19 20:00:00'),
    (12, 33, 6, '2025-04-22 10:00:00'),
    (11, 34, 12, '2025-04-23 17:00:00'),
    (9, 34, 27, '2025-04-27 09:00:00'),
    (16, 34, 21, '2025-05-05 17:00:00'),
    (4, 34, 29, '2025-04-30 09:00:00'),
    (4, 35, 26, '2025-08-30 18:00:00'),
    (12, 35, 35, '2025-08-03 20:00:00'),
    (5, 35, 35, '2025-07-28 09:00:00'),
    (17, 36, 17, '2025-08-31 15:00:00'),
    (15, 36, 11, '2025-08-31 08:00:00'),
    (5, 36, 8, '2025-09-09 16:00:00'),
    (12, 36, 17, '2025-09-08 10:00:00'),
    (14, 36, 32, '2025-09-18 11:00:00'),
    (15, 37, 12, '2025-08-04 19:00:00'),
    (18, 37, 8, '2025-09-10 17:00:00'),
    (1, 37, 12, '2025-07-26 15:00:00'),
    (7, 38, 32, '2025-09-19 08:00:00'),
    (1, 38, 36, '2025-08-31 13:00:00'),
    (6, 38, 6, '2025-08-11 13:00:00'),
    (16, 38, 7, '2025-09-11 08:00:00'),
    (6, 39, 5, '2025-12-22 12:00:00'),
    (9, 39, 34, '2025-12-23 16:00:00'),
    (15, 39, 39, '2025-12-30 19:00:00'),
    (10, 40, 16, '2025-12-24 08:00:00'),
    (4, 40, 7, '2025-12-15 16:00:00'),
    (17, 40, 20, '2025-11-23 17:00:00'),
    (13, 41, 37, '2025-11-27 12:00:00'),
    (16, 41, 21, '2025-12-15 18:00:00'),
    (15, 41, 22, '2025-11-17 10:00:00'),
    (4, 41, 27, '2025-11-19 16:00:00'),
    (9, 41, 35, '2026-01-04 13:00:00'),
    (10, 42, 37, '2025-12-13 11:00:00'),
    (8, 42, 20, '2025-12-06 11:00:00'),
    (14, 43, 2, '2026-04-17 10:00:00'),
    (3, 43, 16, '2026-02-24 19:00:00'),
    (4, 43, 6, '2026-03-28 16:00:00'),
    (5, 43, 33, '2026-03-29 10:00:00'),
    (16, 43, 39, '2026-04-10 08:00:00'),
    (7, 44, 28, '2026-03-07 20:00:00'),
    (1, 44, 36, '2026-04-03 14:00:00'),
    (4, 45, 23, '2026-03-05 14:00:00'),
    (2, 45, 17, '2026-02-22 10:00:00'),
    (12, 45, 2, '2026-04-14 16:00:00'),
    (3, 45, 14, '2026-03-09 16:00:00'),
    (5, 46, 7, '2025-09-20 09:00:00'),
    (6, 46, 29, '2025-09-13 18:00:00'),
    (13, 46, 40, '2025-10-21 15:00:00'),
    (11, 46, 27, '2025-09-23 16:00:00'),
    (2, 47, 38, '2026-01-31 13:00:00'),
    (5, 47, 5, '2026-02-11 11:00:00'),
    (15, 47, 35, '2026-02-13 09:00:00'),
    (1, 47, 9, '2026-02-27 20:00:00'),
    (9, 48, 7, '2026-07-05 08:00:00'),
    (2, 48, 13, '2026-06-23 14:00:00'),
    (1, 48, 34, '2026-06-15 15:00:00');


-- 8. pre-aggregated metrics [EC-07 disagrees with raw events]

INSERT INTO daily_artist_metrics
    (artist_id, metric_date, country_code, stream_count, skip_count, save_count, unique_listeners, avg_listen_pct)
VALUES
    (1, '2025-02-08', 'BR', 4830998, 106540, 107678, 4532565, 86.87),
    (2, '2025-02-03', 'JP', 3987553, 167071, 80312, 3624236, 90.97),
    (6, '2025-02-03', 'GB', 3043069, 111487, 99176, 2881894, 88.88),
    (7, '2025-02-14', 'KR', 4062054, 111250, 68775, 3806769, 87.0),
    (8, '2025-02-22', 'KR', 3218904, 152406, 82483, 3001816, 86.33),
    (9, '2025-02-07', 'KR', 3297087, 143906, 127959, 3118194, 90.02),
    (11, '2025-02-07', 'MX', 1779245, 98863, 52271, 1626893, 95.36),
    (12, '2025-02-10', 'JP', 2850164, 120162, 91241, 2738732, 88.37),
    (1, '2025-03-06', 'BR', 4320117, 187267, 149135, 4108624, 89.89),
    (7, '2025-03-11', 'MX', 4201146, 249196, 82045, 3946445, 86.54),
    (10, '2025-03-03', 'KR', 2530151, 107095, 59293, 2289959, 92.49),
    (11, '2025-03-25', 'KR', 1544439, 82400, 24118, 1391729, 94.04),
    (3, '2025-04-06', 'GB', 3913760, 218276, 129716, 3561112, 91.24),
    (10, '2025-04-09', 'GB', 2298600, 46510, 40824, 2215880, 87.12),
    (3, '2025-05-23', 'GB', 4358498, 109299, 104288, 4091754, 88.76),
    (5, '2025-05-21', 'BR', 3020375, 77001, 62352, 2903800, 95.24),
    (7, '2025-05-09', 'GB', 2952931, 110975, 51049, 2687185, 94.38),
    (8, '2025-05-11', 'KR', 2833905, 150763, 74507, 2704215, 91.55),
    (9, '2025-05-27', 'US', 3994487, 109017, 59925, 3759690, 91.86),
    (1, '2025-06-02', 'GB', 5360017, 296095, 126196, 4986795, 87.02),
    (5, '2025-06-10', 'BR', 3011585, 138013, 55561, 2847401, 89.28),
    (7, '2025-06-13', 'CO', 3443867, 163711, 90689, 3233980, 89.85),
    (9, '2025-06-14', 'JP', 3721023, 219890, 125357, 3487882, 88.37),
    (11, '2025-06-15', 'GB', 1473609, 67182, 44641, 1376475, 87.74),
    (12, '2025-06-02', 'MX', 3604013, 97628, 110598, 3466478, 93.43),
    (4, '2025-07-09', 'CO', 3496106, 206186, 103797, 3284449, 91.42),
    (5, '2025-07-08', 'KR', 2733150, 133450, 93208, 2641312, 92.71),
    (7, '2025-07-11', 'GB', 3105254, 135826, 53500, 2832328, 89.31),
    (8, '2025-07-05', 'US', 2651021, 143169, 38869, 2569155, 88.03),
    (9, '2025-07-12', 'KR', 3074056, 142835, 78590, 2938188, 87.62),
    (11, '2025-07-24', 'CO', 1848944, 49925, 59399, 1731002, 94.41),
    (12, '2025-07-09', 'KR', 2790708, 164133, 33563, 2536630, 89.0),
    (1, '2025-08-05', 'KR', 4786214, 197564, 173586, 4594980, 91.09),
    (2, '2025-08-25', 'GB', 4076451, 176175, 98919, 3801616, 86.41),
    (4, '2025-08-03', 'MX', 3599205, 179011, 120788, 3280258, 91.86),
    (8, '2025-08-08', 'KR', 2430078, 110578, 30294, 2245288, 91.56),
    (9, '2025-08-26', 'GB', 4227673, 145443, 137399, 3925845, 94.45),
    (10, '2025-08-21', 'JP', 2487221, 114468, 91691, 2343933, 93.37),
    (11, '2025-08-24', 'CO', 1574820, 50056, 48274, 1467079, 93.61),
    (12, '2025-08-20', 'CO', 3682913, 187473, 65027, 3474335, 86.65),
    (4, '2025-09-22', 'BR', 4233580, 242864, 139354, 3974439, 94.02),
    (6, '2025-09-06', 'BR', 2986553, 125003, 116515, 2892121, 91.91),
    (7, '2025-09-12', 'GB', 3920801, 99019, 67987, 3734256, 86.97),
    (8, '2025-09-27', 'CO', 2765196, 157993, 80883, 2551822, 93.95),
    (9, '2025-09-16', 'MX', 3509944, 192005, 95633, 3230686, 86.46),
    (10, '2025-09-22', 'BR', 2491497, 63408, 53838, 2265831, 87.17),
    (12, '2025-09-11', 'JP', 3452776, 139905, 96805, 3229887, 90.68),
    (1, '2025-10-04', 'CO', 4641404, 155077, 160644, 4178533, 93.95),
    (2, '2025-10-20', 'KR', 3881159, 178187, 128027, 3608223, 94.01),
    (3, '2025-10-23', 'US', 4152365, 168464, 142930, 3996037, 89.5),
    (4, '2025-10-26', 'KR', 3111869, 176438, 43023, 3006333, 89.64),
    (5, '2025-10-13', 'MX', 3675355, 91398, 74952, 3465483, 88.77),
    (6, '2025-10-01', 'BR', 2708117, 96010, 104107, 2619904, 87.9),
    (7, '2025-10-25', 'BR', 3796156, 225388, 149133, 3444641, 88.4),
    (8, '2025-10-21', 'CO', 2726772, 101014, 65454, 2522931, 91.5),
    (12, '2025-10-14', 'KR', 2847700, 72997, 45548, 2755703, 94.28),
    (2, '2025-11-13', 'KR', 5152308, 253147, 115779, 4913664, 87.64),
    (7, '2025-11-22', 'GB', 2956234, 115460, 91310, 2778150, 90.33),
    (8, '2025-11-19', 'MX', 2291215, 99441, 51622, 2082237, 86.78),
    (9, '2025-11-12', 'US', 2953031, 159153, 75951, 2845383, 92.19),
    (12, '2025-11-14', 'GB', 2765016, 93271, 55875, 2534962, 87.79),
    (2, '2025-12-23', 'CO', 4314295, 226489, 91142, 3887919, 87.0),
    (5, '2025-12-08', 'MX', 3077258, 98959, 39043, 2820557, 88.32),
    (7, '2025-12-25', 'US', 4001116, 131731, 114689, 3860589, 94.61),
    (3, '2026-01-22', 'US', 3562286, 81165, 95012, 3240811, 90.75),
    (5, '2026-01-06', 'GB', 2966700, 129576, 76763, 2794355, 92.45),
    (9, '2026-01-08', 'GB', 3919666, 191887, 60506, 3547299, 93.6),
    (10, '2026-01-22', 'BR', 2434003, 53978, 56644, 2289344, 94.74),
    (1, '2026-02-13', 'KR', 5555040, 212150, 181853, 5055606, 89.85),
    (5, '2026-02-04', 'US', 3325152, 187226, 113692, 3144784, 93.35),
    (6, '2026-02-05', 'US', 2954691, 145304, 44585, 2698274, 86.93),
    (8, '2026-02-27', 'MX', 2458382, 125683, 87299, 2273728, 87.39),
    (9, '2026-02-16', 'GB', 3656716, 82378, 66226, 3309331, 86.83),
    (10, '2026-02-14', 'GB', 2881527, 89936, 70646, 2666653, 88.94),
    (11, '2026-02-09', 'GB', 1766345, 59330, 69332, 1609242, 94.13),
    (1, '2026-03-23', 'GB', 3936446, 90143, 101240, 3672129, 89.69),
    (3, '2026-03-13', 'BR', 4183540, 89664, 93805, 3980598, 89.08),
    (5, '2026-03-18', 'JP', 3438402, 98143, 56559, 3139150, 94.35),
    (6, '2026-03-23', 'CO', 2775913, 59025, 101677, 2618299, 94.08),
    (7, '2026-03-20', 'JP', 4196245, 175405, 98209, 4001871, 92.02),
    (8, '2026-03-06', 'BR', 3018432, 72021, 79473, 2793163, 87.13),
    (10, '2026-03-04', 'GB', 2819617, 85775, 94417, 2554901, 90.48),
    (2, '2026-04-02', 'GB', 4792475, 107800, 57428, 4413519, 92.91),
    (4, '2026-04-24', 'JP', 4142512, 153315, 147021, 3950831, 88.24),
    (6, '2026-04-16', 'US', 2727933, 148037, 82758, 2607348, 93.25),
    (12, '2026-04-02', 'US', 3225563, 126771, 126489, 3031285, 94.79),
    (1, '2026-05-23', 'CO', 5068461, 218717, 91749, 4742402, 93.16),
    (2, '2026-05-22', 'MX', 3746644, 126106, 68102, 3633716, 88.5),
    (3, '2026-05-07', 'MX', 4678684, 149735, 56183, 4325716, 92.12),
    (5, '2026-05-27', 'BR', 2826976, 82328, 31549, 2554367, 92.2),
    (7, '2026-05-03', 'US', 3161444, 170854, 83260, 2866410, 87.18),
    (1, '2026-06-20', 'US', 4966274, 213430, 171012, 4636124, 86.25),
    (2, '2026-06-08', 'GB', 3742788, 181296, 89247, 3427673, 86.58),
    (3, '2026-06-18', 'MX', 3655604, 188551, 143645, 3527816, 88.63),
    (5, '2026-06-20', 'GB', 3275714, 187138, 97052, 3174874, 86.52),
    (6, '2026-06-19', 'KR', 2632771, 143822, 50870, 2386322, 88.63),
    (9, '2026-06-16', 'GB', 3253624, 79093, 102127, 3103128, 88.99),
    (2, '2026-07-05', 'US', 4407150, 166119, 46727, 4137999, 88.14),
    (4, '2026-07-06', 'KR', 3359441, 128655, 132523, 3164075, 88.29),
    (9, '2026-07-13', 'US', 3873573, 174626, 154671, 3726265, 88.09),
    (10, '2026-07-05', 'CO', 2704207, 93079, 36705, 2548927, 93.57),
    (11, '2026-07-02', 'GB', 1860113, 81377, 64574, 1705774, 88.38),
    (12, '2026-07-13', 'MX', 3215230, 65188, 120745, 2917684, 93.72);


-- 9. cached counter drift [EC-07]

UPDATE tracks SET total_plays = total_plays + 64800 WHERE track_id = 1;
UPDATE tracks SET total_plays = total_plays + 76870 WHERE track_id = 2;
UPDATE tracks SET total_plays = total_plays + 63135 WHERE track_id = 3;
UPDATE tracks SET total_plays = total_plays + 15245 WHERE track_id = 4;
UPDATE tracks SET total_plays = total_plays + 35587 WHERE track_id = 5;
UPDATE tracks SET total_plays = total_plays + 37860 WHERE track_id = 6;
UPDATE tracks SET total_plays = total_plays + 82810 WHERE track_id = 7;
UPDATE tracks SET total_plays = total_plays + 53732 WHERE track_id = 8;
UPDATE tracks SET total_plays = total_plays + 87188 WHERE track_id = 9;
UPDATE tracks SET total_plays = total_plays + 41733 WHERE track_id = 10;
UPDATE tracks SET total_plays = total_plays + 62169 WHERE track_id = 11;
UPDATE tracks SET total_plays = total_plays + 19296 WHERE track_id = 12;
UPDATE tracks SET total_plays = total_plays + 46018 WHERE track_id = 13;
UPDATE tracks SET total_plays = total_plays + 38976 WHERE track_id = 14;
UPDATE tracks SET total_plays = total_plays + 14356 WHERE track_id = 15;
UPDATE tracks SET total_plays = total_plays + 14768 WHERE track_id = 16;
UPDATE tracks SET total_plays = total_plays + 44214 WHERE track_id = 17;
UPDATE tracks SET total_plays = total_plays + 31130 WHERE track_id = 18;
UPDATE tracks SET total_plays = total_plays + 49698 WHERE track_id = 19;
UPDATE tracks SET total_plays = total_plays + 12406 WHERE track_id = 20;
UPDATE tracks SET total_plays = total_plays + 15482 WHERE track_id = 21;
UPDATE tracks SET total_plays = total_plays + 10239 WHERE track_id = 22;
UPDATE tracks SET total_plays = total_plays + 31666 WHERE track_id = 23;
UPDATE tracks SET total_plays = total_plays + 21394 WHERE track_id = 24;
UPDATE tracks SET total_plays = total_plays + 86283 WHERE track_id = 25;
UPDATE tracks SET total_plays = total_plays + 84885 WHERE track_id = 26;
UPDATE tracks SET total_plays = total_plays + 3854 WHERE track_id = 27;
UPDATE tracks SET total_plays = total_plays + 47800 WHERE track_id = 28;
UPDATE tracks SET total_plays = total_plays + 18334 WHERE track_id = 29;
UPDATE tracks SET total_plays = total_plays + 41193 WHERE track_id = 30;
UPDATE tracks SET total_plays = total_plays + 56615 WHERE track_id = 31;
UPDATE tracks SET total_plays = total_plays + 21647 WHERE track_id = 32;
UPDATE tracks SET total_plays = total_plays + 32532 WHERE track_id = 33;
UPDATE tracks SET total_plays = total_plays + 35312 WHERE track_id = 34;
UPDATE tracks SET total_plays = total_plays + 53534 WHERE track_id = 35;
UPDATE tracks SET total_plays = total_plays + 84683 WHERE track_id = 36;
UPDATE tracks SET total_plays = total_plays + 23217 WHERE track_id = 37;
UPDATE tracks SET total_plays = total_plays + 47780 WHERE track_id = 38;
UPDATE tracks SET total_plays = total_plays + 12888 WHERE track_id = 39;
UPDATE tracks SET total_plays = total_plays + 63633 WHERE track_id = 40;
UPDATE tracks SET total_plays = total_plays + 25891 WHERE track_id = 41;
UPDATE tracks SET total_plays = total_plays + 49433 WHERE track_id = 42;
UPDATE tracks SET total_plays = total_plays + 27393 WHERE track_id = 43;
UPDATE tracks SET total_plays = total_plays + 28592 WHERE track_id = 44;
UPDATE tracks SET total_plays = total_plays + 80864 WHERE track_id = 45;
UPDATE tracks SET total_plays = total_plays + 8138 WHERE track_id = 46;
UPDATE tracks SET total_plays = total_plays + 22348 WHERE track_id = 47;
UPDATE tracks SET total_plays = total_plays + 62034 WHERE track_id = 48;
UPDATE artists SET monthly_listeners_cached = monthly_listeners_cached + 761593 WHERE artist_id = 1;
UPDATE artists SET monthly_listeners_cached = monthly_listeners_cached + 929811 WHERE artist_id = 2;
UPDATE artists SET monthly_listeners_cached = monthly_listeners_cached + 1201247 WHERE artist_id = 3;
UPDATE artists SET monthly_listeners_cached = monthly_listeners_cached + 1809910 WHERE artist_id = 4;
UPDATE artists SET monthly_listeners_cached = monthly_listeners_cached + 554481 WHERE artist_id = 5;
UPDATE artists SET monthly_listeners_cached = monthly_listeners_cached + 688936 WHERE artist_id = 6;
UPDATE artists SET monthly_listeners_cached = monthly_listeners_cached + 1160044 WHERE artist_id = 7;
UPDATE artists SET monthly_listeners_cached = monthly_listeners_cached + 1548842 WHERE artist_id = 8;
UPDATE artists SET monthly_listeners_cached = monthly_listeners_cached + 2988659 WHERE artist_id = 9;
UPDATE artists SET monthly_listeners_cached = monthly_listeners_cached + 2337928 WHERE artist_id = 10;
UPDATE artists SET monthly_listeners_cached = monthly_listeners_cached + 452788 WHERE artist_id = 11;
UPDATE artists SET monthly_listeners_cached = monthly_listeners_cached + 3849481 WHERE artist_id = 12;


SET FOREIGN_KEY_CHECKS = 1;
