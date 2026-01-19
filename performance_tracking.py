import psycopg2
from datetime import timedelta
from db_config import db_name, db_user, db_password, db_host

print("Connecting to database...")
conn = psycopg2.connect(
    dbname=db_name,
    user=db_user,
    password=db_password,
    host=db_host
)
cur = conn.cursor()
print("Connected!\n")


# Add new FTP column
cur.execute("ALTER TABLE cycling_activities ADD COLUMN ftp DECIMAL(10,5)")
conn.commit()

# Load all activities
cur.execute("""
    SELECT athlete_id, activity_date, critical_power_20m
    FROM cycling_activities
    ORDER BY athlete_id, activity_date
""")
all_activities = cur.fetchall()
print(f"  Loaded {len(all_activities)} activities\n")

# Group by athlete
print("Step 4: Grouping by athlete...")
athletes = {}
for row in all_activities:
    athlete_id = row[0]
    if athlete_id not in athletes:
        athletes[athlete_id] = []
    athletes[athlete_id].append(row)
print(f"  Found {len(athletes)} athletes\n")

# Calculate FTP for each athlete
total_activities = 0

for athlete_id, activities in athletes.items():
    
    previous_ftp = 0
    
    for i in range(len(activities)):
        athlete_id_db = activities[i][0]
        activity_date = activities[i][1]
        power_20m = activities[i][2]
        
        # Calculate max 20m power in last 45 days
        date_45_ago = activity_date - timedelta(days=45)
        max_power_45 = 0
        
        for j in range(i + 1):
            past_date = activities[j][1]
            past_power = activities[j][2]
            if past_date >= date_45_ago and past_power is not None:
                if past_power > max_power_45:
                    max_power_45 = past_power
        
        # Calculate max 20m power in last 90 days
        date_90_ago = activity_date - timedelta(days=90)
        max_power_90 = 0
        
        for j in range(i + 1):
            past_date = activities[j][1]
            past_power = activities[j][2]
            if past_date >= date_90_ago and past_power is not None:
                if past_power > max_power_90:
                    max_power_90 = past_power
        
        # Apply progressive FTP logic
        if i == 0:
            # First activity - use 45 day max
            new_ftp = max_power_45
        elif max_power_45 > previous_ftp:
            # FTP increasing - use 45 day max
            new_ftp = max_power_45
        elif max_power_45 < previous_ftp:
            # FTP would decrease - check 90 day rule
            if max_power_90 < previous_ftp:
                # Real detraining - allow decrease to 90 day max
                new_ftp = max_power_90
            else:
                # Not real detraining - keep previous FTP
                new_ftp = previous_ftp
        else:
            # FTP same
            new_ftp = max_power_45
        
        # Update database
        cur.execute("""
            UPDATE cycling_activities
            SET ftp = %s
            WHERE athlete_id = %s AND activity_date = %s
        """, (new_ftp, athlete_id_db, activity_date))
        
        previous_ftp = new_ftp
        total_activities += 1
    
    conn.commit()

print(f" Calculated FTP for {total_activities} total activities")

cur.close()
conn.close()
print("\nDatabase closed")