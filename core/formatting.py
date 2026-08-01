def format_display_time(value):
    if not value or not hasattr(value, "strftime"):
        return value or ""
    return value.strftime("%I:%M %p").lstrip("0").lower()
