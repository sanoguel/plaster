from datetime import datetime

def get_astronomical_season():
    # Get current date as an integer MMDD (e.g., 0714 for July 14)
    now = datetime.now()
    md = now.month * 100 + now.day

    # Northern Hemisphere ranges (approximate astronomical dates)
    if 321 <= md <= 620:
        return "Spring"
    elif 621 <= md <= 922:
        return "Summer"
    elif 923 <= md <= 1220:
        return "Autumn"
    else:
        return "Winter"
