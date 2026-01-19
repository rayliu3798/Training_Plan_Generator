# Cycling Training Data Analysis & Recommendation System

A data pipeline and machine learning system for analyzing cycling power data and generating personalized training recommendations.

## Overview

This project processes raw cycling power data from the [GoldenCheetah OpenData](https://github.com/GoldenCheetah/OpenData/tree/master) to derive performance metrics, classify workout types, and recommend optimized training plans using machine learning.

### Data Pipeline
- Ingests raw cycling power data from the GoldenCheetah OpenData API
- Processes and transforms raw data into structured formats
- Calculates Functional Threshold Power (FTP) metrics for cyclists
- Updates database with derived metrics and processed data

### Workout Classification
- Custom algorithm to automatically classify workout types including:
  - Interval training sessions
  - Endurance rides
  - Recovery workouts
  - Race or group rides
- Analyzes power distribution and patterns to determine workout categories

### Training Recommendation System (Work in Progress)
- LSTM-based neural network trained on historical training sequences
- Generates personalized, optimized cycling training plans
- Adapts recommendations based on individual performance history

## Roadmap

- [x] ETL pipeline for data ingestion
- [x] FTP calculation algorithm
- [x] Workout type classification
- [ ] Complete LSTM model training


# Cycling Data Analysis Pipeline

This part of the project imports cycling activity data from JSON files into PostgreSQL and calculates FTP (Functional Threshold Power) with progressive logic.

The pipeline consists of:
1. **SQL scripts** - Create database tables and clean data
2. **Python script** - Calculate and update FTP values with progressive logic

## Files

- `create_table.sql` - SQL commands for table creation and data cleaning
- `performance_tracking.py` - Python script to calculate FTP with progressive logic
- `db_config.py` - Database configuration file

## Prerequisites

- PostgreSQL installed and running
- Python 3.x
- Python package: `psycopg2`

Python dependencies:
```bash
pip install psycopg2 matplotlib
```

## Setup Instructions

### Step 1: Create the Database

Open PostgreSQL (psql or pgAdmin) and create a new database:

```sql
CREATE DATABASE training_data;
```

### Step 2: Create the Table

Run the SQL commands to create the `cycling_activities` table:

```sql
CREATE TABLE IF NOT EXISTS cycling_activities (
    athlete_id UUID NOT NULL,
    activity_date TIMESTAMP NOT NULL,
    sport VARCHAR(50),
    critical_power_10s DECIMAL(10,5),
    critical_power_5m DECIMAL(10,5),
    critical_power_20m DECIMAL(10,5),
    coggan_if DECIMAL(10,5),
    coggan_tss DECIMAL(10,5),
    ftp DECIMAL(10,5),
    PRIMARY KEY (athlete_id, activity_date)
);

CREATE INDEX idx_athlete_date ON cycling_activities(athlete_id, activity_date);
CREATE INDEX idx_activity_date ON cycling_activities(activity_date);
```

### Step 3: Load Your Data

Load the cycling data from metadata of OpenData database into the table. 
```bash
python load_data.py
```

### Step 4: Clean the Data

- Athletes with fewer than 50 activities are excluded from analysis
- Only 'Bike' and 'VirtualRide' activities are included

Run these SQL commands to remove unwanted data:

```sql
-- Remove non-cycling activities and rows with NULL values
DELETE FROM cycling_activities
WHERE (sport NOT IN ('Bike', 'VirtualRide') OR sport IS NULL)
   OR critical_power_10s IS NULL
   OR critical_power_5m IS NULL
   OR critical_power_20m IS NULL
   OR coggan_if IS NULL
   OR coggan_tss IS NULL;

-- Remove athletes with fewer than 50 activities
DELETE FROM cycling_activities
WHERE athlete_id IN (
    SELECT athlete_id
    FROM cycling_activities
    GROUP BY athlete_id
    HAVING COUNT(*) < 50
);
```

### Step 5: Configure Database Connection

Create `db_config.py` with your database credentials:

```python
# Database configuration
db_name = 'training_data'
db_user = 'postgres'
db_password = 'YOUR_PASSWORD_HERE' 
db_host = 'localhost'
db_port = 5432
```

### Step 6: Calculate FTP

Run the Python script to calculate FTP:

```bash
python performance_tracking.py
```

This will:
- Create a FTP column
- Calculate FTP for all activities using progressive logic
- Display sample results

## FTP Calculation Logic

The FTP (Functional Threshold Power) of each activity of a cyclist is calculated using the following progressive logic, due to the fact that cyclist would only perform FTP tests typically every 45 days:

1. **Base FTP**: Maximum 20-minute critical power in the prior 45 days
2. **FTP Increases**: Always allowed when 30-day max exceeds previous FTP
3. **FTP Decreases**: Only allowed when maximum power in prior 90 days falls below previous FTP (indicates real detraining), FTP is updated to 90-day maximum power.
4. **FTP Maintained**: When 45-day max is lower but 90-day max is still above previous FTP

### Example

```
Day 1:  Power = 200W → FTP = 200W
Day 20: Power = 220W → FTP = 220W (increased)
Day 40: Power = 205W → FTP = 220W (maintained, not real detraining)
Day 100: 90-day max = 205W → FTP = 205W (decreased, detraining confirmed)
```

## Database Schema

### Table: `cycling_activities`

| Column | Type | Description |
|--------|------|-------------|
| `athlete_id` | UUID | Unique identifier for athlete |
| `activity_date` | TIMESTAMP | Date and time of activity |
| `sport` | VARCHAR(50) | Activity type (Bike or VirtualRide) |
| `critical_power_10s` | DECIMAL(10,5) | 10-second critical power |
| `critical_power_5m` | DECIMAL(10,5) | 5-minute critical power |
| `critical_power_20m` | DECIMAL(10,5) | 20-minute critical power |
| `coggan_if` | DECIMAL(10,5) | Intensity Factor |
| `coggan_tss` | DECIMAL(10,5) | Training Stress Score |
| `ftp` | DECIMAL(10,5) | Calculated FTP (progressive) |


## Data Flow

```
JSON Files → PostgreSQL Table → Data Cleaning → FTP Calculation
     ↓              ↓                  ↓              ↓
  Parse JSON   Create Table    Remove Invalid   Progressive Logic
  Extract      Load Data        Remove < 50      Update FTP Column
  Metrics                       activities
```

# Cycling Ride Classifier

Automatically classify cycling training rides from power data into different workout types.

## What It Does

Analyzes power data from cycling rides and classifies them into:
- **Zone 3 Interval Training** - Tempo intervals (76-90% FTP)
- **Zone 4 Interval Training** - Threshold intervals (91-105% FTP)
- **Zone 5 Interval Training** - VO2max intervals (106-120% FTP)
- **Zone 6 Interval Training** - Anaerobic intervals (>120% FTP)
- **Recovery Ride** - Easy, low intensity rides
- **Endurance Ride** - Long, steady aerobic rides
- **Race or Group Ride** - High intensity, unpredictable efforts

## Files

- `classifier.py` - Main classification algorithm
- `batch_classifier.py` - Process multiple files and save to database
- `test_classifier.py` - Test single file with visualization

## Run
```python
from classifier import CyclingRideClassifier

classifier = CyclingRideClassifier(threshold_power=250)
result = classifier.classify_ride_from_csv('my_ride.csv')

print(result['ride_type'])
```

### Batch Processing

**Configure `batch_classifier.py`:**
```python
DB_NAME = 'training_data'
DB_USER = 'postgres'
DB_PASSWORD = 'your_password'
CSV_FOLDER = r'path\to\your\csv\files'
```

**Run:**
```bash
python batch_classifier.py
```

## CSV File Format

Required columns: `secs, km, power, hr, cad, alt`

Filename format: `YYYY_MM_DD_HH_MM_SS.csv`

Example: `2017_02_04_13_45_56.csv`

```csv
secs,km,power,hr,cad,alt
0,0.0,150,120,85,100
1,0.03,152,121,86,100
2,0.06,148,122,84,101
```

## How It Works

### Power Zones (Based on FTP)

| Zone | % FTP | Type |
|------|-------|------|
| 1 | 0-55% | Recovery |
| 2 | 56-75% | Endurance |
| 3 | 76-90% | Tempo |
| 4 | 91-105% | Threshold |
| 5 | 106-120% | VO2max |
| 6 | 121%+ | Anaerobic |

### Interval Detection

1. Smooth power data (30-second rolling average)
2. Find efforts above Zone 3 (76% FTP)
3. Merge intervals separated by <60 seconds
4. Keep intervals >2 minutes with 60%+ time above threshold
5. Classify interval zone based on average power

### Ride Classification

**Interval Training:**
- 3+ consistent intervals detected
- Duration within 30% of each other
- Power within 15% of each other
- Classified by zone (Zone 3, 4, 5, or 6)

**Recovery Ride:**
- Average power <55% FTP
- Duration <90 minutes
- 70%+ time in recovery zone

**Endurance Ride:**
- Duration >60 minutes
- Low power variability (<0.25)
- 60%+ time in endurance/tempo zones
- <3 intervals

**Race or Group Ride:**
- High power variability (>0.3) OR
- 30%+ time in high-intensity zones OR
- Average power above tempo zone

## Customization

### Adjust Zone Thresholds

In `classifier.py`:
```python
self.zone_tempo_min = 0.76 * self.ftp  # Change from 76%
self.zone_threshold_min = 0.91 * self.ftp  # Change from 91%
```

### Adjust Interval Detection

In `find_intervals()`:
```python
window_size = 30  # Smoothing window (seconds)
gap_seconds > 60  # Merge threshold (seconds)
duration_seconds > 120  # Minimum interval length
percent_above > 60  # Minimum time above threshold (%)
```

### Adjust Classification Rules

In `determine_ride_type()`:
```python
duration_consistency < 0.3  # Interval duration consistency
power_consistency < 0.15    # Interval power consistency
variability > 0.3           # Race/group ride variability
```

## Output

### Batch Processing

**Console:**
```
Found 399 CSV files.

File 1/399: 2017_01_31_18_36_44.csv
  Zone 4 Interval Training - 65.3 min - 195.2W

File 2/399: 2017_02_04_13_45_56.csv
  Endurance Ride - 120.0 min - 180.5W

Processing complete: 395 successful, 4 failed

SUMMARY
============================================================
Total Rides: 395

Ride Types:
  Endurance Ride: 150
  Recovery Ride: 80
  Zone 3 Interval Training: 45
  Zone 4 Interval Training: 90
  Zone 5 Interval Training: 25
  Race or Group Ride: 5
============================================================
```

**Database:**
```sql
SELECT type, COUNT(*) 
FROM ride_classifications 
GROUP BY type;
```

**Text File (results.txt):**
```
2017-01-31 18:36:44 - Zone 4 Interval Training
2017-02-04 13:45:56 - Endurance Ride
2017-02-15 10:20:30 - Recovery Ride
```

