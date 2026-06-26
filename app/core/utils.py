from datetime import datetime
import pytz

def get_mexico_now():
    mexico_tz = pytz.timezone('America/Mexico_City')
    return datetime.now(mexico_tz)