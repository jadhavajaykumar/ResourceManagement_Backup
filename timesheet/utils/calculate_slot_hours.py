from datetime import datetime, timedelta

def calculate_slot_hours(time_from_str, time_to_str):
    """
    Calculate hours for a time slot from strings in HH:MM format
    Handles overnight slots properly
    """
    # Parse time strings
    time_from = datetime.strptime(time_from_str, '%H:%M').time()
    time_to = datetime.strptime(time_to_str, '%H:%M').time()
    
    # Create datetime objects on a common date
    base_date = datetime(2020, 1, 1)  # Arbitrary date
    start_dt = datetime.combine(base_date, time_from)
    end_dt = datetime.combine(base_date, time_to)
    
    # Handle overnight slots (end time earlier than start time)
    if time_to < time_from:
        end_dt += timedelta(days=1)
    
    # Calculate duration in hours
    duration = end_dt - start_dt
    return round(duration.total_seconds() / 3600, 2)