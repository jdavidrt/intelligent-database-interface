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
--  EC-07: monthly_listeners_cached is ~5% above raw play_events.
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
--    The counts here are ~5% lower than daily_artist_metrics.
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
--  EC-07: stream_count is intentionally ~5% above play_events.
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


SET FOREIGN_KEY_CHECKS = 1;
