DROP TABLE IF EXISTS alien_weapon_specials;
CREATE TABLE alien_weapon_specials (type INT NOT NULL PRIMARY KEY, specials varchar(255) NOT NULL);
INSERT INTO alien_weapon_specials (type, specials) VALUES (1, 'Fling shot');
INSERT INTO alien_weapon_specials (type, specials) VALUES (2, 'Aimed Shot');
INSERT INTO alien_weapon_specials (type, specials) VALUES (4, 'Burst');
INSERT INTO alien_weapon_specials (type, specials) VALUES (3, 'Fling Shot and Aimed Shot');
INSERT INTO alien_weapon_specials (type, specials) VALUES (5, 'Fling Shot and Burst');
INSERT INTO alien_weapon_specials (type, specials) VALUES (12, 'Burst and Full Auto');
INSERT INTO alien_weapon_specials (type, specials) VALUES (13, 'Burst, Fling Shot and Full Auto');
INSERT INTO alien_weapon_specials (type, specials) VALUES (48, 'Brawl and Dimach');
INSERT INTO alien_weapon_specials (type, specials) VALUES (76, 'Brawl and Fast Attack');
INSERT INTO alien_weapon_specials (type, specials) VALUES (112, 'Brawl, Dimach and Fast Attack');
INSERT INTO alien_weapon_specials (type, specials) VALUES (240, 'Brawl, Dimach, Fast Attack and Sneak Attack');
INSERT INTO alien_weapon_specials (type, specials) VALUES (880, 'Dimach, Fast Attack, Parry and Riposte');
INSERT INTO alien_weapon_specials (type, specials) VALUES (992, 'Dimach, Fast Attack, Sneak Attack, Parry and Riposte');

DROP TABLE IF EXISTS alien_weapons;
CREATE TABLE alien_weapons (type INT NOT NULL, name VARCHAR(255) NOT NULL);
INSERT INTO alien_weapons (type, name) VALUES (1, 'Kyr''Ozch Grenade Gun - Type 1');
INSERT INTO alien_weapons (type, name) VALUES (1, 'Kyr''Ozch Pistol - Type 1');
INSERT INTO alien_weapons (type, name) VALUES (1, 'Kyr''Ozch Shotgun - Type 1');
INSERT INTO alien_weapons (type, name) VALUES (2, 'Kyr''Ozch Crossbow - Type 2');
INSERT INTO alien_weapons (type, name) VALUES (2, 'Kyr''Ozch Rifle - Type 2');
INSERT INTO alien_weapons (type, name) VALUES (3, 'Kyr''Ozch Crossbow - Type 3');
INSERT INTO alien_weapons (type, name) VALUES (3, 'Kyr''Ozch Energy Carbine - Type 3');
INSERT INTO alien_weapons (type, name) VALUES (3, 'Kyr''Ozch Rifle - Type 3');
INSERT INTO alien_weapons (type, name) VALUES (4, 'Kyr''Ozch Machine Pistol - Type 4');
INSERT INTO alien_weapons (type, name) VALUES (4, 'Kyr''Ozch Pistol - Type 4');
INSERT INTO alien_weapons (type, name) VALUES (4, 'Kyr''Ozch Submachine Gun - Type 4');
INSERT INTO alien_weapons (type, name) VALUES (5, 'Kyr''Ozch Carbine - Type 5');
INSERT INTO alien_weapons (type, name) VALUES (5, 'Kyr''Ozch Energy Carbine - Type 5');
INSERT INTO alien_weapons (type, name) VALUES (5, 'Kyr''Ozch Energy Pistol - Type 5');
INSERT INTO alien_weapons (type, name) VALUES (5, 'Kyr''Ozch Machine Pistol - Type 5');
INSERT INTO alien_weapons (type, name) VALUES (5, 'Kyr''Ozch Submachine Gun - Type 5');
INSERT INTO alien_weapons (type, name) VALUES (12, 'Kyr''Ozch Carbine - Type 12');
INSERT INTO alien_weapons (type, name) VALUES (12, 'Kyr''Ozch Submachine Gun - Type 12');
INSERT INTO alien_weapons (type, name) VALUES (13, 'Kyr''Ozch Carbine - Type 13');
INSERT INTO alien_weapons (type, name) VALUES (48, 'Kyr''Ozch Nunchacko - Type 48');
INSERT INTO alien_weapons (type, name) VALUES (76, 'Kyr''Ozch Energy Sword - Type 76');
INSERT INTO alien_weapons (type, name) VALUES (76, 'Kyr''Ozch Sledgehammer - Type 76');
INSERT INTO alien_weapons (type, name) VALUES (112, 'Kyr''Ozch Energy Hammer - Type 112');
INSERT INTO alien_weapons (type, name) VALUES (112, 'Kyr''Ozch Hammer - Type 112');
INSERT INTO alien_weapons (type, name) VALUES (112, 'Kyr''Ozch Spear - Type 112');
INSERT INTO alien_weapons (type, name) VALUES (112, 'Kyr''Ozch Sword - Type 112');
INSERT INTO alien_weapons (type, name) VALUES (240, 'Kyr''Ozch Axe - Type 240');
INSERT INTO alien_weapons (type, name) VALUES (880, 'Kyr''Ozch Sword - Type 880');
INSERT INTO alien_weapons (type, name) VALUES (992, 'Kyr''Ozch Energy Rapier - Type 992');