"""
Ephemeris Generator using JPL Horizons API
Generates predicted positions for small bodies
"""

import requests
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import re


class EphemerisGenerator:
    """Generate ephemerides using JPL Horizons API"""
    
    HORIZONS_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"
    
    def __init__(self, cache_dir: str = 'cache'):
        self.cache_dir = cache_dir
    
    def generate(self, 
                 designation: str,
                 start_date: str,
                 end_date: str,
                 step: str = '1d',
                 observer: str = '500') -> List[Dict]:
        """
        Generate ephemeris for an object
        
        Args:
            designation: Object designation (e.g., '433', '2023 DW', 'Ceres')
            start_date: Start date 'YYYY-MM-DD'
            end_date: End date 'YYYY-MM-DD'
            step: Time step ('1h', '3h', '6h', '12h', '1d', '1w')
            observer: Observer location code ('500' = geocenter, '@399' = Earth center)
        
        Returns:
            List of ephemeris points with {time, ra, dec, vmag, rate, uncertainty}
        """
        # Build Horizons API parameters
        params = {
            'format': 'text',  # text format is easier to parse
            'COMMAND': f"'{designation}'",  # Must be quoted
            'OBJ_DATA': 'YES',
            'MAKE_EPHEM': 'YES',
            'EPHEM_TYPE': 'OBSERVER',
            'CENTER': observer,
            'START_TIME': start_date,
            'STOP_TIME': end_date,
            'STEP_SIZE': step,
            'QUANTITIES': "'1,9,20,23,24'",  # RA, DEC, Vmag, rate, uncertainty
            'CAL_FORMAT': 'CAL',
            'TIME_DIGITS': 'MINUTES',
            'ANG_FORMAT': 'DEG',
            'APPARENT': 'AIRLESS',
            'RANGE_UNITS': 'AU',
            'SUPPRESS_RANGE_RATE': 'NO',
            'SKIP_DAYLT': 'NO',
            'EXTRA_PREC': 'NO',
            'R_T_S_ONLY': 'NO',
            'REF_SYSTEM': 'ICRF',
            'CSV_FORMAT': 'NO'
        }
        
        try:
            print(f"Querying JPL Horizons for {designation}...")
            response = requests.get(self.HORIZONS_URL, params=params, timeout=60)
            
            if response.status_code == 200:
                # Check if Horizons returned an error in the response
                if 'No matches found' in response.text or 'Cannot find' in response.text:
                    print(f"Horizons could not find object: {designation}")
                    print(f"Try alternate designations or numeric ID")
                    return []
                
                result = self._parse_horizons_response(response.text)
                
                if not result:
                    print(f"Warning: No ephemeris data parsed from Horizons response")
                    print(f"Response preview: {response.text[:500]}")
                
                return result
            else:
                print(f"Horizons API error: Status {response.status_code}")
                print(f"Response: {response.text[:500]}")
                return []
                
        except requests.exceptions.Timeout:
            print(f"Horizons API timeout after 60 seconds")
            return []
        except requests.exceptions.RequestException as e:
            print(f"Network error querying Horizons: {e}")
            return []
        except Exception as e:
            print(f"Error generating ephemeris: {e}")
            import traceback
            print(traceback.format_exc())
            return []
    
    def _parse_horizons_response(self, text: str) -> List[Dict]:
        """
        Parse Horizons text output into structured data
        
        Args:
            text: Raw Horizons API response text
        
        Returns:
            List of ephemeris dictionaries
        """
        ephemeris = []
        
        # Find the ephemeris data section between $$SOE and $$EOE markers
        lines = text.split('\n')
        in_data = False
        
        for line in lines:
            # Start of ephemeris
            if '$$SOE' in line:
                in_data = True
                continue
            
            # End of ephemeris
            elif '$$EOE' in line:
                break
            
            # Parse data lines
            elif in_data and line.strip():
                try:
                    point = self._parse_ephemeris_line(line)
                    if point:
                        ephemeris.append(point)
                except Exception as e:
                    # Skip malformed lines
                    continue
        
        print(f"Parsed {len(ephemeris)} ephemeris points")
        return ephemeris
    
    def _parse_ephemeris_line(self, line: str) -> Optional[Dict]:
        """
        Parse single ephemeris line
        
        Horizons format with ANG_FORMAT='DEG' and QUANTITIES='1,9,20,23,24':
        Date      Time       RA(deg)   Dec(deg)  APmag   S-brt   delta      deldot    S-O-T  /r   S-T-O
        2015-Jun-01 00:00    70.88016  26.77557  12.762  2.943  2.212376...  -3.438...  5.3430 /T  4.4883
        """
        # Split line by whitespace
        parts = line.split()
        
        if len(parts) < 5:
            return None
        
        try:
            # Extract date and time (first two parts)
            # Format: "2015-Jun-01 00:00"
            date_str = parts[0]
            time_str = parts[1] if len(parts) > 1 else "00:00"
            datetime_str = f"{date_str} {time_str}"
            
            # RA and Dec are already in decimal degrees (ANG_FORMAT='DEG')
            # Column 2: RA in degrees
            # Column 3: Dec in degrees
            ra_deg = float(parts[2])
            dec_deg = float(parts[3])
            
            # Extract apparent magnitude (column 4)
            vmag_str = parts[4] if len(parts) > 4 else 'n.a.'
            vmag = float(vmag_str) if vmag_str != 'n.a.' and vmag_str.replace('.','').replace('-','').isdigit() else None
            
            # Extract delta (distance) column 6
            delta = float(parts[6]) if len(parts) > 6 else None
            
            # Extract deldot (rate) column 7
            rate = float(parts[7]) if len(parts) > 7 else None
            
            return {
                'time': datetime_str,
                'ra': ra_deg,
                'dec': dec_deg,
                'vmag': vmag,
                'delta': delta,
                'rate': rate,
                'uncertainty': None  # Not in this output format
            }
            
        except Exception as e:
            # Silently skip malformed lines
            return None
    
    def _parse_ra_to_degrees(self, ra_str: str) -> float:
        """Convert RA string (HH MM SS.ss) to decimal degrees"""
        try:
            parts = ra_str.split()
            hours = float(parts[0])
            minutes = float(parts[1])
            seconds = float(parts[2])
            return (hours + minutes/60 + seconds/3600) * 15.0
        except:
            return 0.0
    
    def _parse_dec_to_degrees(self, dec_str: str) -> float:
        """Convert Dec string (+DD MM SS.s) to decimal degrees"""
        try:
            parts = dec_str.split()
            sign = -1 if parts[0].startswith('-') else 1
            degrees = abs(float(parts[0]))
            minutes = float(parts[1])
            seconds = float(parts[2])
            return sign * (degrees + minutes/60 + seconds/3600)
        except:
            return 0.0
    
    def generate_for_survey(self, 
                           designation: str, 
                           survey_years: tuple,
                           step: str = '1d') -> List[Dict]:
        """
        Generate ephemeris for specific survey timeframe
        
        Args:
            designation: Object designation
            survey_years: (start_year, end_year)
            step: Time step
        
        Returns:
            Ephemeris list
        """
        start_date = f"{survey_years[0]}-01-01"
        end_date = f"{survey_years[1]}-12-31"
        
        return self.generate(designation, start_date, end_date, step)
