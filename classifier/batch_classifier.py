"""
Batch processing script for cycling ride classifier.
Reads CSV files from folders and gets FTP from PostgreSQL database.
"""

import os
from datetime import datetime
from classifier import CyclingRideClassifier
import psycopg2


def connect_database(host, database, user, password, port=5432):
    """Connect to PostgreSQL database."""
    try:
        connection = psycopg2.connect(
            host=host,
            database=database,
            user=user,
            password=password,
            port=port
        )
        print("Connected to database successfully.")
        return connection
    except Exception as e:
        print(f"ERROR: Could not connect to database: {e}")
        return None


def create_results_table(connection):
    """Create table to store classification results."""
    try:
        cursor = connection.cursor()
        
        query = """
            CREATE TABLE IF NOT EXISTS ride_classifications (
                activity_date TIMESTAMP PRIMARY KEY,
                type VARCHAR(100) NOT NULL
            )
        """
        
        cursor.execute(query)
        connection.commit()
        cursor.close()
        print("Results table ready.")
        
    except Exception as e:
        print(f"ERROR: Could not create table: {e}")
        connection.rollback()


def get_date_from_filename(filename):
    """Convert filename like '2017_01_31_18_36_44.csv' to datetime."""
    try:
        name = filename.replace('.csv', '')
        date = datetime.strptime(name, '%Y_%m_%d_%H_%M_%S')
        return date
    except:
        return None


def get_ftp_from_database(connection, date):
    """Get FTP value for a date from database."""
    try:
        connection.rollback()
        cursor = connection.cursor()
        
        query = """
            SELECT ftp 
            FROM cycling_activities 
            WHERE activity_date <= %s 
            ORDER BY activity_date DESC 
            LIMIT 1
        """
        
        cursor.execute(query, (date,))
        result = cursor.fetchone()
        cursor.close()
        
        if result:
            return float(result[0])
        else:
            return None
            
    except Exception as e:
        connection.rollback()
        return None


def save_to_database(connection, date, ride_type):
    """Save classification result to database."""
    try:
        cursor = connection.cursor()
        
        query = """
            INSERT INTO ride_classifications (activity_date, type)
            VALUES (%s, %s)
            ON CONFLICT (activity_date) 
            DO UPDATE SET type = EXCLUDED.type
        """
        
        cursor.execute(query, (date, ride_type))
        connection.commit()
        cursor.close()
        
    except Exception as e:
        connection.rollback()


def get_all_csv_files(folder_path):
    """Get all CSV files from folder and subfolders."""
    csv_files = []
    
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith('.csv'):
                full_path = os.path.join(root, file)
                csv_files.append((file, full_path))
    
    return csv_files


def process_all_rides(folder_path, connection):
    """Process all CSV files."""
    
    csv_files = get_all_csv_files(folder_path)
    print(f"\nFound {len(csv_files)} CSV files.\n")
    
    results = []
    successful = 0
    failed = 0
    
    for i, (filename, file_path) in enumerate(csv_files, 1):
        print(f"File {i}/{len(csv_files)}: {filename}")
        
        date = get_date_from_filename(filename)
        if not date:
            failed += 1
            continue
        
        ftp = get_ftp_from_database(connection, date)
        if not ftp:
            failed += 1
            continue
        
        try:
            classifier = CyclingRideClassifier(threshold_power=ftp)
            result = classifier.classify_ride_from_csv(file_path)
            
            result['filename'] = filename
            result['date'] = date
            result['ftp'] = ftp
            
            print(f"  {result['ride_type']} - {result['duration_minutes']:.1f} min - {result['average_power']:.1f}W")
            
            save_to_database(connection, date, result['ride_type'])
            
            results.append(result)
            successful += 1
            
        except Exception as e:
            print(f"  ERROR: {e}")
            failed += 1
    
    print(f"\nProcessing complete: {successful} successful, {failed} failed")
    return results


def print_summary(results):
    """Print summary of all processed rides."""
    if len(results) == 0:
        print("\nNo rides processed.")
        return
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"\nTotal Rides: {len(results)}")
    
    type_counts = {}
    for result in results:
        ride_type = result['ride_type']
        if ride_type not in type_counts:
            type_counts[ride_type] = 0
        type_counts[ride_type] += 1
    
    print("\nRide Types:")
    for ride_type, count in sorted(type_counts.items()):
        print(f"  {ride_type}: {count}")
    
    print("="*60)


def save_results_file(results, output_file):
    """Save results to text file."""
    with open(output_file, 'w') as f:
        f.write("RIDE CLASSIFICATION RESULTS\n")
        f.write("="*60 + "\n\n")
        
        for result in results:
            f.write(f"{result['date'].strftime('%Y-%m-%d %H:%M:%S')} - {result['ride_type']}\n")
    
    print(f"\nResults saved to: {output_file}")


# Main program
if __name__ == "__main__":
    
    # Configuration
    DB_HOST = 'localhost'
    DB_NAME = 'training_data'
    DB_USER = 'postgres'
    DB_PASSWORD = '********'
    DB_PORT = 5432
    
    CSV_FOLDER = r'C:\Users\Ray\opendatastorage\data\00b8b415-0abd-42d6-ac3e-0d122ba63fc3'
    OUTPUT_FILE = 'results.txt'
    
    print("="*60)
    print("BATCH RIDE CLASSIFIER")
    print("="*60)
    
    # Connect to database
    connection = connect_database(DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT)
    if not connection:
        print("Cannot continue without database connection.")
        exit()
    
    # Create results table
    create_results_table(connection)
    
    # Process all rides
    results = process_all_rides(CSV_FOLDER, connection)
    
    # Close database
    connection.close()
    
    # Print summary
    print_summary(results)
    
    # Save results to file
    if len(results) > 0:
        save_results_file(results, OUTPUT_FILE)
    
    print(f"\nComplete! Processed {len(results)} rides.")