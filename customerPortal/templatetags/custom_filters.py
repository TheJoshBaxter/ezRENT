from django import template
import re

register = template.Library()

@register.filter
def format_phone(value):
    """Format a 10-digit phone number as (XXX)-XXX-XXXX"""
    digits = re.sub(r'\D', '', value)  # Remove non-numeric characters
    if len(digits) == 10:
        return f"({digits[:3]})-{digits[3:6]}-{digits[6:]}"
    return value  # Return as is if not 10 digits

