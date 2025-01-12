
SELECT
    c.name,
    c.id,
    max(l.average_item_level) as ilvl,
    bool_or(l.pinnacle_quest_done) as pinnacle,
    bool_or(profession_1_quest_done) as prof_1,
    bool_or(profession_2_quest_done) as prof_2,
    sum(delves_completed) as delves_completed
FROM progress_log as l
LEFT JOIN wow_character as c
    ON l.character_id = c.id
WHERE 1=1
  AND (false
    OR c.level = 80
    OR c.level is NULL
  )
  AND l.record_date >= '2024-12-31'
  --date_trunc('week', current_date - interval '1 week') + interval '2 day'
GROUP BY c.name, c.id;

SELECT
    character_id,
    max(record_date)
FROM progress_log
GROUP BY 1
ORDER BY 1;

UPDATE progress_log
SET profession_1_quest_done = true,
    profession_2_quest_done = true
WHERE character_level = 80