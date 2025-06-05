from datetime import datetime, timedelta


def generate_time_slots(shift_start, shift_end, date):
    slots = []
    slot_duration = timedelta(hours=2)  # You can make this configurable

    start_dt = datetime.combine(date, shift_start)
    end_dt = datetime.combine(date, shift_end)

    if end_dt <= start_dt:
        end_dt += timedelta(days=1)  # Handle overnight shift

    current = start_dt
    while current < end_dt:
        next_slot = min(current + slot_duration, end_dt)
        duration = (next_slot - current).total_seconds() / 3600

        slots.append({
            'from_time': current.time(),
            'to_time': next_slot.time(),
            'hours': duration
        })
        current = next_slot

    return slots