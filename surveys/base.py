"""
Base class for all survey clients
Defines interface that all survey modules must implement
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Tuple, Optional
from datetime import datetime


class SurveyClient(ABC):
    """Abstract base class for sky survey clients"""
    
    def __init__(self):
        self.name = "Generic Survey"
        self.years = (2000, 2024)
        self.limiting_magnitude = 20.0
        self.bands = ['V']
        self.priority = 1
    
    @abstractmethod
    def check_coverage(self, ra: float, dec: float, date: Optional[str] = None) -> bool:
        """
        Check if position is within survey footprint
        
        Args:
            ra: Right Ascension (degrees)
            dec: Declination (degrees)
            date: Optional date to check temporal coverage (YYYY-MM-DD)
        
        Returns:
            True if position is covered by survey
        """
        pass
    
    @abstractmethod
    def get_cutout(self, 
                   ra: float, 
                   dec: float, 
                   size: float = 60.0,
                   date: Optional[str] = None,
                   band: Optional[str] = None) -> Optional[Dict]:
        """
        Get image cutout for position
        
        Args:
            ra: Right Ascension (degrees)
            dec: Declination (degrees)
            size: Cutout size in arcseconds
            date: Optional observation date (YYYY-MM-DD)
            band: Optional filter/band
        
        Returns:
            Dict with image URL and metadata, or None if not available
        """
        pass
    
    def search_ephemeris(self, 
                        ephemeris: List[Dict],
                        sample_rate: int = 1) -> List[Dict]:
        """
        Search for object across ephemeris positions
        
        Args:
            ephemeris: List of {time, ra, dec, vmag, uncertainty}
            sample_rate: Sample every Nth position (1 = all positions)
        
        Returns:
            List of found image metadata
        """
        results = []
        
        for i, position in enumerate(ephemeris[::sample_rate]):
            # Check if position is in survey coverage
            if self.check_coverage(position['ra'], position['dec'], position.get('time')):
                # Check if object is bright enough
                vmag = position.get('vmag')
                if vmag is not None and vmag > self.limiting_magnitude:
                    continue  # Too faint for this survey
                
                # Try to get cutout
                cutout = self.get_cutout(
                    position['ra'],
                    position['dec'],
                    date=position.get('time')
                )
                
                if cutout:
                    cutout['ephemeris_index'] = i * sample_rate
                    cutout['predicted_vmag'] = vmag
                    results.append(cutout)
        
        return results
    
    def get_info(self) -> Dict:
        """Get survey information"""
        return {
            'name': self.name,
            'years': self.years,
            'limiting_magnitude': self.limiting_magnitude,
            'bands': self.bands,
            'priority': self.priority
        }
