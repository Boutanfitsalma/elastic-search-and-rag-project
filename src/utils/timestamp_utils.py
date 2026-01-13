"""
==============================================================================
TIMESTAMP UTILS - Conversion des timestamps
==============================================================================
Gère les 3 formats de timestamps trouvés dans les logs Mozilla CI
==============================================================================
"""

from datetime import datetime
import re


def parse_timestamp(timestamp_str):
    """
    Parse un timestamp dans n'importe quel format trouvé dans les logs
    
    Formats supportés:
    - Unix timestamp: 1527851240.94
    - Format court: 05:43:46
    - Format complet: 2018-06-01 04:07:20
    
    Args:
        timestamp_str: String du timestamp
    
    Returns:
        dict: {
            'original': timestamp original,
            'unix': timestamp unix (float),
            'iso': format ISO 8601,
            'datetime': objet datetime
        }
        ou None si parsing échoue
    """
    if not timestamp_str:
        return None
    
    timestamp_str = str(timestamp_str).strip()
    
    try:
        # FORMAT 1: Unix timestamp (1527851240.94)
        if re.match(r'^\d{10}\.\d+$', timestamp_str):
            unix_ts = float(timestamp_str)
            dt = datetime.fromtimestamp(unix_ts)
            return {
                'original': timestamp_str,
                'unix': unix_ts,
                'iso': dt.isoformat(),
                'datetime': dt
            }
        
        # FORMAT 2: Format complet (2018-06-01 04:07:20)
        if re.match(r'^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}', timestamp_str):
            dt = datetime.strptime(timestamp_str[:19], '%Y-%m-%d %H:%M:%S')
            return {
                'original': timestamp_str,
                'unix': dt.timestamp(),
                'iso': dt.isoformat(),
                'datetime': dt
            }
        
        # FORMAT 3: Format court (05:43:46)
        # Note: On ne peut pas convertir en date absolue sans contexte
        if re.match(r'^\d{2}:\d{2}:\d{2}$', timestamp_str):
            return {
                'original': timestamp_str,
                'unix': None,
                'iso': None,
                'datetime': None,
                'time_only': timestamp_str
            }
        
        # Aucun format reconnu
        return None
    
    except Exception:
        return None


def convert_to_iso(timestamp_str):
    """
    Convertit un timestamp en format ISO 8601
    
    Args:
        timestamp_str: String du timestamp
    
    Returns:
        str: Timestamp au format ISO ou None
    """
    parsed = parse_timestamp(timestamp_str)
    return parsed['iso'] if parsed and 'iso' in parsed else None


def convert_to_unix(timestamp_str):
    """
    Convertit un timestamp en Unix timestamp
    
    Args:
        timestamp_str: String du timestamp
    
    Returns:
        float: Unix timestamp ou None
    """
    parsed = parse_timestamp(timestamp_str)
    return parsed['unix'] if parsed and 'unix' in parsed else None