create_character_table_sql = """
CREATE TABLE IF NOT EXISTS "public"."wow_character" (
    "key" character varying
        NOT NULL,
    "region" character varying(2)
        NOT NULL
        CONSTRAINT "wow_region_constraint" CHECK region in ('us', 'eu', 'kr', 'tw'),
    "name" character varying(30) 
        NOT NULL,
    "realm" character varying(30)
        NOT NULL,
    "level" integer
        NOT NULL,
    
    CONSTRAINT "ix_wow_character_key"
        UNIQUE ("key"),
    CONSTRAINT "wow_character_pkey"
        PRIMARY KEY ("key")
);
"""

list_character_sql = """
SELECT
    key,
    name,
    level
FROM wow_character;
"""

get_character_sql = """
SELECT
    name,
    region,
    realm,
    level
FROM wow_characters
WHERE id = :id;
"""

insert_character_sql = """
INSERT INTO wow_character (
    key,
    region,
    realm,
    name,
    level
)
VALUES (
    :key,
    :region,
    :realm,
    :name,
    :level
)
ON CONFLICT (key) DO UPDATE SET (
    region,
    realm,
    name,
    level
) = (
    :region,
    :realm,
    :name,
    :level
) WHERE (
    wow_character.key = 'test'
);
"""

update_character_sql = """
UPDATE wow_character SET (
    region,
    realm,
    name,
    level
) = (
    :region,
    :realm,
    :name,
    :level
) WHERE (
    wow_character.key = :key
);
"""

delete_character_sql = """
DELETE FROM wow_character
WHERE wow_character.key = :key;
"""
