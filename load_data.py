#Python script to process all JSON files and insert into PostgreSQL:

import json
import psycopg2
from pathlib import Path

# Database connection
conn = psycopg2.connect(
    dbname="training_data",
    user="postgres",
    password="********",
    host="localhost"
)
cur = conn.cursor()

# Process all JSON files
data_dir = Path(r'C:\Users\Ray\opendatastorage\metadata')
for json_file in data_dir.glob('*.json'):
    with open(json_file, 'r') as f:
        data = json.load(f)
        athlete_id = data['ATHLETE']['id']
        
        for ride in data['RIDES']:
            metrics = ride['METRICS']
            
            # Extract values, handling array format [value, sample_count]
            def get_value(key):
                val = metrics.get(key)
                if isinstance(val, list):
                    return float(val[0])
                elif isinstance(val, str):
                    return float(val)
                return None
            
            cur.execute("""
                INSERT INTO cycling_activities VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (athlete_id, activity_date) DO NOTHING
            """, (
                athlete_id,
                ride['date'],
                ride['sport'],
                get_value('10s_critical_power'),
                get_value('5m_critical_power'),
                get_value('20m_critical_power'),
                get_value('coggan_if'),
                get_value('coggan_tss')
            ))

conn.commit()
cur.close()
conn.close()
