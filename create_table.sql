-- Create the cycling activities table
CREATE TABLE IF NOT EXISTS cycling_activities (
    athlete_id UUID NOT NULL,
    activity_date TIMESTAMP NOT NULL,
    sport VARCHAR(50),
    critical_power_10s DECIMAL(10,5),
    critical_power_5m DECIMAL(10,5),
    critical_power_20m DECIMAL(10,5),
    coggan_if DECIMAL(10,5),
    coggan_tss DECIMAL(10,5),
    PRIMARY KEY (athlete_id, activity_date)
);

-- Create index for faster queries
CREATE INDEX idx_athlete_date ON cycling_activities(athlete_id, activity_date);
CREATE INDEX idx_activity_date ON cycling_activities(activity_date);

