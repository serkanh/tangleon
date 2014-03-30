import re
import datetime

MONTHS = ['JAN', 'FEB', 'MAR', 
          'APR', 'MAY', 'JUN',
          'JUL', 'AUG', 'SEP',
          'OCT', 'NOV', 'DEC']

def parse_to_utc_date(date_str):    
    """u'Thu, 15 Dec 2011 00:41:06 -0800'"""
    
    date_pattern = re.compile(r'\w+\,\s+(\d+)\s+(\w+)\s+(\d+)\s+(\d+)\:(\d+)\:(\d+)\s+(\+|\-\d{2})(\d{2})')
    day, month, year, hour, minute, second, offsethours, offsetminutes = date_pattern.search(date_str).groups()
    month = MONTHS.index(month.upper()) + 1

    offset = datetime.timedelta(hours=int(offsethours), minutes=int(offsetminutes))
    date = datetime.datetime(int(year), month, int(day), int(hour), int(minute), int(second))
    return date - offset
