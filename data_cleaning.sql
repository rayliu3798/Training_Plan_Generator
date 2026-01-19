-- Remove rows where sport is not 'Bike' or 'VirtualRide'
DELETE FROM cycling_activities
WHERE (sport NOT IN ('Bike', 'VirtualRide') OR sport IS NULL);

-- Remove rows containing any NULL values in the key columns
DELETE FROM cycling_activities
WHERE critical_power_10s IS NULL
   OR critical_power_5m IS NULL
   OR critical_power_20m IS NULL
   OR coggan_if IS NULL
   OR coggan_tss IS NULL;


-- Need to remove athletes with few data points, as they won't be sufficient for training.
-- Check how many athletes have fewer than 50 activities
SELECT 
    athlete_id,
    COUNT(*) as activity_count
FROM cycling_activities
GROUP BY athlete_id
HAVING COUNT(*) < 50
ORDER BY activity_count DESC;

-- Count total rows that will be deleted
SELECT COUNT(*) as rows_to_delete
FROM cycling_activities
WHERE athlete_id IN (
    SELECT athlete_id
    FROM cycling_activities
    GROUP BY athlete_id
    HAVING COUNT(*) < 50
);

-- Delete all data for athletes with fewer than 50 activities
DELETE FROM cycling_activities
WHERE athlete_id IN (
    SELECT athlete_id
    FROM cycling_activities
    GROUP BY athlete_id
    HAVING COUNT(*) < 50
);

-- Verify remaining athletes and their activity counts
SELECT 
    athlete_id,
    COUNT(*) as activity_count,
    MIN(activity_date) as first_activity,
    MAX(activity_date) as last_activity
FROM cycling_activities
GROUP BY athlete_id
ORDER BY activity_count DESC;
