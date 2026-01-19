import csv

class CyclingRideClassifier:
    def __init__(self, threshold_power):
        """
        Create a classifier with the rider's threshold power (FTP).
        
        Args:
            threshold_power: Functional Threshold Power in watts
        """
        self.ftp = threshold_power
        
        # Define power zones as percentages of FTP
        self.zone_recovery_max = 0.55 * self.ftp
        self.zone_endurance_min = 0.56 * self.ftp
        self.zone_endurance_max = 0.75 * self.ftp
        self.zone_tempo_min = 0.76 * self.ftp
        self.zone_tempo_max = 0.90 * self.ftp
        self.zone_threshold_min = 0.91 * self.ftp
        self.zone_threshold_max = 1.05 * self.ftp
        self.zone_vo2max_min = 1.06 * self.ftp
        self.zone_vo2max_max = 1.20 * self.ftp
        self.zone_anaerobic_min = 1.21 * self.ftp
    
    def read_csv_file(self, filename):
        """
        Read cycling data from CSV file.
        
        Args:
            filename: Path to CSV file with columns: secs, km, power, hr, cad, alt
            
        Returns:
            Dictionary with lists of data from each column
        """
        time_data = []
        power_data = []
        hr_data = []
        distance_data = []
        cadence_data = []
        altitude_data = []
        
        with open(filename, 'r') as file:
            csv_reader = csv.DictReader(file)
            
            for row in csv_reader:
                # Read each column and convert to numbers
                time_data.append(float(row['secs']))
                power_data.append(float(row['power']))
                hr_data.append(float(row['hr']) if row['hr'] else 0)
                distance_data.append(float(row['km']))
                cadence_data.append(float(row['cad']) if row['cad'] else 0)
                altitude_data.append(float(row['alt']) if row['alt'] else 0)
        
        return {
            'time': time_data,
            'power': power_data,
            'heart_rate': hr_data,
            'distance': distance_data,
            'cadence': cadence_data,
            'altitude': altitude_data
        }
    
    def classify_ride_from_csv(self, filename):
        """
        Read CSV file and classify the ride.
        
        Args:
            filename: Path to CSV file
            
        Returns:
            Dictionary with ride type and details
        """
        # Read the CSV file
        data = self.read_csv_file(filename)
        
        # Classify using the power and time data
        return self.classify_ride(data['power'], data['time'])
    
    def classify_ride(self, power_data, time_data):
        """
        Figure out what type of ride this is.
        
        Args:
            power_data: List of power values in watts
            time_data: List of time values in seconds
            
        Returns:
            Dictionary with ride type and details
        """
        power = power_data
        time = time_data
        
        total_duration = time[-1] - time[0]
        duration_minutes = total_duration / 60
        
        # Calculate average power (ignore zeros)
        power_without_zeros = [p for p in power if p > 0]
        avg_power = sum(power_without_zeros) / len(power_without_zeros)
        
        # Find intervals
        intervals = self.find_intervals(power, time)
        
        # Calculate time in each zone
        time_in_zones = self.calculate_time_in_zones(power, time)
        
        # Calculate how much power varies
        variability = self.calculate_variability(power)
        
        # Decide what type of ride it is
        ride_type = self.determine_ride_type(
            duration_minutes, avg_power, variability, 
            intervals, time_in_zones, total_duration
        )
        
        return {
            'ride_type': ride_type,
            'duration_minutes': duration_minutes,
            'average_power': avg_power,
            'variability': variability,
            'intervals_detected': len(intervals),
            'intervals': intervals,
            'time_in_zones': time_in_zones
        }
    
    def find_intervals(self, power, time):
        """Find interval efforts in the ride."""
        intervals = []
        
        # Anything above Zone 3 (tempo) is considered an interval
        interval_threshold = self.zone_tempo_min
        
        # Smooth out the power data to reduce noise
        smoothed_power = self.smooth_power_data(power, window_size=30)
        
        # Mark each second as high or low intensity
        is_high = []
        for p in smoothed_power:
            if p > interval_threshold:
                is_high.append(True)
            else:
                is_high.append(False)
        
        # Find where intervals start and stop
        interval_starts = []
        interval_ends = []
        
        in_interval = False
        for i in range(len(is_high)):
            if is_high[i] and not in_interval:
                # Starting a new interval
                interval_starts.append(i)
                in_interval = True
            elif not is_high[i] and in_interval:
                # Ending an interval
                interval_ends.append(i)
                in_interval = False
        
        # If still in interval at the end
        if in_interval:
            interval_ends.append(len(is_high) - 1)
        
        # Merge intervals that are close together (less than 60 seconds apart)
        merged_starts = []
        merged_ends = []
        
        if len(interval_starts) > 0:
            merged_starts.append(interval_starts[0])
            
            for i in range(len(interval_starts) - 1):
                current_end = interval_ends[i]
                next_start = interval_starts[i + 1]
                
                # Calculate gap between this interval and next
                gap_seconds = time[next_start] - time[current_end]
                
                if gap_seconds > 60:
                    # Gap is big, treat as separate intervals
                    merged_ends.append(current_end)
                    merged_starts.append(next_start)
                # If gap is small, don't add to lists (merging happens automatically)
            
            merged_ends.append(interval_ends[-1])
        
        # Check each interval and save if it's valid
        for start_idx, end_idx in zip(merged_starts, merged_ends):
            duration_seconds = time[end_idx] - time[start_idx]
            
            # Get power values for this interval
            interval_power = power[start_idx:end_idx + 1]
            avg_interval_power = sum(interval_power) / len(interval_power)
            max_interval_power = max(interval_power)
            
            # Count how many seconds were above threshold
            seconds_above = 0
            for p in interval_power:
                if p > interval_threshold:
                    seconds_above += 1
            
            percent_above = (seconds_above / len(interval_power)) * 100
            
            # Keep this interval if:
            # - It's longer than 2 minutes
            # - Average power is high enough
            # - At least 60% of time was above threshold
            if (duration_seconds > 120 and 
                avg_interval_power > interval_threshold and 
                percent_above > 60):
                
                # Figure out what zone this interval is in
                zone = self.get_zone_name(avg_interval_power)
                
                intervals.append({
                    'start_time': time[start_idx],
                    'duration': duration_seconds,
                    'avg_power': avg_interval_power,
                    'peak_power': max_interval_power,
                    'percent_above_threshold': percent_above,
                    'zone': zone
                })
        
        return intervals
    
    def smooth_power_data(self, power, window_size):
        """Smooth power data using a moving average."""
        smoothed = []
        
        for i in range(len(power)):
            # Get values in the window
            start = max(0, i - window_size // 2)
            end = min(len(power), i + window_size // 2)
            window = power[start:end]
            
            # Calculate average of window
            avg = sum(window) / len(window)
            smoothed.append(avg)
        
        return smoothed
    
    def get_zone_name(self, power):
        """Get the training zone name for a power value."""
        if power >= self.zone_anaerobic_min:
            return 'Zone 6 (Anaerobic)'
        elif power >= self.zone_vo2max_min:
            return 'Zone 5 (VO2max)'
        elif power >= self.zone_threshold_min:
            return 'Zone 4 (Threshold)'
        elif power >= self.zone_tempo_min:
            return 'Zone 3 (Tempo)'
        elif power >= self.zone_endurance_min:
            return 'Zone 2 (Endurance)'
        else:
            return 'Zone 1 (Recovery)'
    
    def calculate_time_in_zones(self, power, time):
        """Calculate how much time was spent in each zone."""
        time_in_recovery = 0
        time_in_endurance = 0
        time_in_tempo = 0
        time_in_threshold = 0
        time_in_vo2max = 0
        time_in_anaerobic = 0
        
        for i in range(len(power)):
            # Each data point represents 1 second (approximately)
            if i > 0:
                time_diff = time[i] - time[i-1]
            else:
                time_diff = 1
            
            p = power[i]
            
            if p < self.zone_recovery_max:
                time_in_recovery += time_diff
            elif p < self.zone_endurance_max:
                time_in_endurance += time_diff
            elif p < self.zone_tempo_max:
                time_in_tempo += time_diff
            elif p < self.zone_threshold_max:
                time_in_threshold += time_diff
            elif p < self.zone_vo2max_max:
                time_in_vo2max += time_diff
            else:
                time_in_anaerobic += time_diff
        
        return {
            'recovery': time_in_recovery,
            'endurance': time_in_endurance,
            'tempo': time_in_tempo,
            'threshold': time_in_threshold,
            'vo2max': time_in_vo2max,
            'anaerobic': time_in_anaerobic
        }
    
    def calculate_variability(self, power):
        """Calculate how much power varies (coefficient of variation)."""
        power_without_zeros = [p for p in power if p > 0]
        
        if len(power_without_zeros) == 0:
            return 0
        
        avg = sum(power_without_zeros) / len(power_without_zeros)
        
        # Calculate standard deviation
        squared_diffs = [(p - avg) ** 2 for p in power_without_zeros]
        variance = sum(squared_diffs) / len(squared_diffs)
        std_dev = variance ** 0.5
        
        # Coefficient of variation = std_dev / mean
        return std_dev / avg
    
    def determine_ride_type(self, duration_minutes, avg_power, variability, 
                           intervals, time_in_zones, total_time):
        """Decide what type of ride this is."""
        
        # Type 1: Interval Training - Check first for structured intervals
        if len(intervals) >= 3:
            # Check if intervals are similar (structured workout)
            durations = [interval['duration'] for interval in intervals]
            powers = [interval['avg_power'] for interval in intervals]
            
            # Calculate how consistent the intervals are
            avg_duration = sum(durations) / len(durations)
            duration_differences = [abs(d - avg_duration) for d in durations]
            avg_duration_diff = sum(duration_differences) / len(duration_differences)
            duration_consistency = avg_duration_diff / avg_duration
            
            avg_interval_power = sum(powers) / len(powers)
            power_differences = [abs(p - avg_interval_power) for p in powers]
            avg_power_diff = sum(power_differences) / len(power_differences)
            power_consistency = avg_power_diff / avg_interval_power
            
            # If intervals are consistent, it's structured interval training
            if duration_consistency < 0.3 and power_consistency < 0.15:
                # Find most common zone
                zones = [interval['zone'] for interval in intervals]
                zone_counts = {}
                for zone in zones:
                    if zone not in zone_counts:
                        zone_counts[zone] = 0
                    zone_counts[zone] += 1
                
                most_common_zone = max(zone_counts, key=zone_counts.get)
                
                # Extract just the zone name (e.g., "Zone 3 (Tempo)" -> "Zone 3")
                zone_short = most_common_zone.split('(')[0].strip()
                
                # Return zone-specific interval training types
                return f"{zone_short} Interval Training"
        
        # Type 2: Recovery Ride
        recovery_time = time_in_zones['recovery']
        total = sum(time_in_zones.values())
        recovery_percentage = recovery_time / total if total > 0 else 0
        
        if (avg_power < self.zone_recovery_max * 1.1 and 
            duration_minutes < 90 and
            recovery_percentage > 0.7):
            return "Recovery Ride"
        
        # Type 3: Endurance Ride
        endurance_time = time_in_zones['endurance']
        tempo_time = time_in_zones['tempo']
        endurance_percentage = (endurance_time + tempo_time) / total if total > 0 else 0
        
        if (duration_minutes > 60 and 
            variability < 0.25 and
            endurance_percentage > 0.6 and
            len(intervals) < 3):
            return "Endurance Ride"
        
        # Type 4: Race or Group Ride
        high_intensity_time = (time_in_zones['threshold'] + 
                              time_in_zones['vo2max'] + 
                              time_in_zones['anaerobic'])
        high_intensity_percentage = high_intensity_time / total if total > 0 else 0
        
        if (variability > 0.3 or 
            high_intensity_percentage > 0.3 or
            avg_power > self.zone_tempo_max):
            return "Race or Group Ride"
        
        # Default: guess based on duration
        if duration_minutes > 60:
            return "Endurance Ride"
        else:
            return "Recovery Ride"


