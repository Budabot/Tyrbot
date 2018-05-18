DROP TABLE IF EXISTS trickle;
CREATE TABLE trickle ( id INT NOT NULL PRIMARY KEY, group_name VARCHAR(20) NOT NULL, name VARCHAR(30) NOT NULL, amount_agility DECIMAL(3,1) NOT NULL, amount_intelligence DECIMAL(3,1) NOT NULL, amount_psychic DECIMAL(3,1) NOT NULL, amount_stamina DECIMAL(3,1) NOT NULL, amount_strength DECIMAL(3,1) NOT NULL, amount_sense DECIMAL(3,1) NOT NULL );

INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (1, 'Body & Defense', 'Body Dev.', 0, 0, 0, 1, 0, 0);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (2, 'Body & Defense', 'Nano Pool', 0, .1, .7, .1, 0, .1);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (3, 'Body & Defense', 'Evade-ClsC', .5, .2, 0, 0, 0, .3);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (4, 'Body & Defense', 'Dodge-Rng', .5, .2, 0, 0, 0, .3);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (5, 'Body & Defense', 'Duck-Exp', .5, .2, 0, 0, 0, .3);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (6, 'Body & Defense', 'Nano Resist', 0, .2, .8, 0, 0, 0);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (7, 'Body & Defense', 'Deflect', .2, 0, 0, 0, .5, .3);

INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (8, 'Melee Weapons', '1h Blunt', .1, 0, 0, .4, .5, 0);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (9, 'Melee Weapons', '1h Edged', .4, 0, 0, .3, .3, 0);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (10, 'Melee Weapons', 'Piercing', .5, 0, 0, .3, .2, 0);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (11, 'Melee Weapons', '2h Blunt', 0, 0, 0, .5, .5, 0);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (12, 'Melee Weapons', '2h Edged', 0, 0, 0, .4, .6, 0);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (13, 'Melee Weapons', 'Melee Ener.', 0, .5, 0, .5, 0, 0);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (14, 'Melee Weapons', 'Martial Arts', .5, 0, .3, 0, .2, 0);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (15, 'Melee Weapons', 'Multi. Melee', .6, 0, 0, .1, .3, 0);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (16, 'Melee Weapons', 'Melee. Init.', .1, .1, .2, 0, 0, .6);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (17, 'Melee Weapons', 'Physic. Init', .1, .1, .2, 0, 0, .6);

INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (18, 'Melee Specials', 'Sneak Atck', .5, .3, 0, 0, 0, .2);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (19, 'Melee Specials', 'Brawling', 0, 0, 0, .4, .6, 0);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (20, 'Melee Specials', 'Fast Attack', .6, 0, 0, 0, 0, .4);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (21, 'Melee Specials', 'Dimach', 0, 0, .2, 0, 0, .8);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (22, 'Melee Specials', 'Riposte', .5, 0, 0, 0, 0, .5);

INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (23, 'Ranged Weapons', 'Pistol', .6, 0, 0, 0, 0, .4);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (24, 'Ranged Weapons', 'Bow', .4, 0, 0, 0, .2, .4);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (25, 'Ranged Weapons', 'MG / SMG', .3, 0, 0, .3, .3, .1);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (26, 'Ranged Weapons', 'Assault Rif', .3, 0, 0, .4, .1, .2);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (27, 'Ranged Weapons', 'Shotgun', .6, 0, 0, 0, .4, 0);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (28, 'Ranged Weapons', 'Rifle', .6, 0, 0, 0, 0, .4);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (29, 'Ranged Weapons', 'Ranged Ener', 0, .2, .4, 0, 0, .4);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (30, 'Ranged Weapons', 'Grenade', .4, .2, 0, 0, 0, .4);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (31, 'Ranged Weapons', 'Heavy Weapons', .6, 0, 0, 0, .4, 0);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (32, 'Ranged Weapons', 'Multi Ranged', .6, .4, 0, 0, 0, 0);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (33, 'Ranged Weapons', 'Ranged. Init.', .1, .1, .2, 0, 0, .6);

INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (34, 'Ranged Specials', 'Fling Shot', 1, 0, 0, 0, 0, 0);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (35, 'Ranged Specials', 'Aimed Shot', 0, 0, 0, 0, 0, 1);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (36, 'Ranged Specials', 'Burst', .5, 0, 0, .2, .3, 0);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (37, 'Ranged Specials', 'Full Auto', 0, 0, 0, .4, .6, 0);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (38, 'Ranged Specials', 'Bow Spc Att', .5, 0, 0, 0, .1, .4);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (39, 'Ranged Specials', 'Sharp Obj', .6, 0, 0, 0, .2, .2);

INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (40, 'Nanos & Casting', 'Matt.Metam', 0, .8, .2, 0, 0, 0);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (41, 'Nanos & Casting', 'Bio Metamor', 0, .8, .2, 0, 0, 0);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (42, 'Nanos & Casting', 'Psycho Modi', 0, .8, 0, 0, 0, .2);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (43, 'Nanos & Casting', 'Sensory Impr', 0, .8, 0, 0, .2, 0);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (44, 'Nanos & Casting', 'Time&Space', .2, .8, 0, 0, 0, 0);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (45, 'Nanos & Casting', 'Matter Crea', 0, .8, 0, .2, 0, 0);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (46, 'Nanos & Casting', 'NanoC. Init.', .4, 0, 0, 0, 0, .6);

INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (47, 'Exploring', 'Vehicle Air', .2, .2, 0, 0, 0, .6);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (48, 'Exploring', 'Vehicle Ground', .2, .2, 0, 0, 0, .6);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (49, 'Exploring', 'Vehicle Water', .2, .2, 0, 0, 0, .6);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (50, 'Exploring', 'Run Speed', .4, 0, 0, .4, .2, 0);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (51, 'Exploring', 'Adventuring', .5, 0, 0, .3, .2, 0);

INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (52, 'Combat & Healing', 'Perception', 0, .3, 0, 0, 0, .7);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (53, 'Combat & Healing', 'Concealment', .3, 0, 0, 0, 0, .7);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (54, 'Combat & Healing', 'Psychology', 0, .5, 0, 0, 0, .5);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (55, 'Combat & Healing', 'Trap Disarm.', .2, .2, 0, 0, 0, .6);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (56, 'Combat & Healing', 'First Aid', .3, .3, 0, 0, 0, .4);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (57, 'Combat & Healing', 'Treatment', .3, .5, 0, 0, 0, .2);

INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (58, 'Trade & Repair', 'Mech. Engi', .5, .5, 0, 0, 0, 0);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (59, 'Trade & Repair', 'Elec. Engi', .3, .5, 0, .2, 0, 0);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (60, 'Trade & Repair', 'Quantum FT', 0, .5, .5, 0, 0, 0);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (61, 'Trade & Repair', 'Chemistry', 0, .5, 0, .5, 0, 0);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (62, 'Trade & Repair', 'Weapon Smt', 0, .5, 0, 0, .5, 0);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (63, 'Trade & Repair', 'Nano Progra', 0, 1, 0, 0, 0, 0);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (64, 'Trade & Repair', 'Tutoring', 0, .7, .1, 0, 0, .2);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (65, 'Trade & Repair', 'Break&Entry', .4, 0, .3, 0, 0, .3);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (66, 'Trade & Repair', 'Comp. Liter', 0, 1, 0, 0, 0, 0);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (67, 'Trade & Repair', 'Pharma Tech', .2, .8, 0, 0, 0, 0);

INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (68, 'Disabled / Legacy', 'Swimming', .2, 0, 0, .6, .2, 0);
INSERT INTO trickle (id, group_name, name, amount_agility, amount_intelligence, amount_psychic, amount_stamina, amount_strength, amount_sense) VALUES (69, 'Disabled / Legacy', 'Map Navig.', 0, .4, .1, 0, 0, .5);