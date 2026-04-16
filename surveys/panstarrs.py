"""
Pan-STARRS Sky Survey Client
Coverage: 3π steradians (3/4 of sky), δ > -30°
Years: 2009-2024
Limiting Magnitude: ~24 (stacked)
"""

import requests
from typing import List, Dict, Optional
from io import BytesIO
from PIL import Image, ImageDraw
import math
from .base import SurveyClient


class PanSTARRSClient(SurveyClient):
    """Client for Pan-STARRS image cutout service"""
    
    BASE_URL = "https://ps1images.stsci.edu/cgi-bin/fitscut.cgi"
    INFO_URL = "https://ps1images.stsci.edu/cgi-bin/ps1filenames.py"
    
    def __init__(self):
        super().__init__()
        self.name = "Pan-STARRS DR2"
        self.years = (2009, 2024)
        self.limiting_magnitude = 24.0  # g-band, stacked
        self.bands = ['g', 'r', 'i', 'z', 'y']
        self.priority = 5  # Highest priority (excellent coverage & depth)
    
    def check_coverage(self, ra: float, dec: float, date: Optional[str] = None) -> bool:
        """
        Check if position is in Pan-STARRS footprint
        
        Pan-STARRS DR2 covers 3π steradians (3/4 of sky)
        Excludes: Dec < -30°, Galactic plane in some regions
        """
        # Basic declination check
        if dec < -30.0:
            return False
        
        # Pan-STARRS covers most of northern sky
        # More sophisticated footprint checking could use HEALPix maps
        return True
    
    def get_file_list(self, ra: float, dec: float, image_type: str = 'stack') -> List[Dict]:
        """
        Query what PS1 files exist for a position
        
        Args:
            ra: Right Ascension
            dec: Declination
            image_type: 'stack' for stacked images, 'warp' for individual exposures
        
        Returns list of available images with metadata
        """
        params = {
            'ra': ra,
            'dec': dec,
            'filters': 'grizy',
            'type': image_type
        }
        
        try:
            response = requests.get(self.INFO_URL, params=params, timeout=10)
            if response.status_code == 200:
                # Parse the response (space-separated table)
                lines = response.text.strip().split('\n')
                if len(lines) < 2:
                    return []
                
                # First line is header
                # Subsequent lines are data
                files = []
                for line in lines[1:]:  # Skip header
                    parts = line.split()
                    if len(parts) >= 6:
                        files.append({
                            'projcell': parts[0],
                            'subcell': parts[1],
                            'filter': parts[4],
                            'mjd': float(parts[5]),
                            'type': parts[6],
                            'filename': parts[7],
                            'shortname': parts[8] if len(parts) > 8 else parts[7]
                        })
                return files
        except Exception as e:
            print(f"Error checking PS1 files: {e}")
        
        return []
    
    def get_cutout(self, 
                   ra: float, 
                   dec: float, 
                   size: float = 60.0,
                   date: Optional[str] = None,
                   band: Optional[str] = 'r',
                   filename: Optional[str] = None,
                   add_indicator: bool = True) -> Optional[Dict]:
        """
        Get Pan-STARRS image cutout
        
        Args:
            ra: Right Ascension (degrees)
            dec: Declination (degrees)  
            size: Cutout size in arcseconds (default 60")
            date: Not used for PS1 (uses stacked images)
            band: Filter (g, r, i, z, y) - default r
            filename: Specific FITS filename to use (for individual warp images)
            add_indicator: Add red circle indicator (default True)
        
        Returns:
            Dict with image URL and metadata
        """
        # Ensure band is valid
        if band not in self.bands:
            band = 'r'
        
        # If no specific filename provided, get stacked image
        if not filename:
            file_list = self.get_file_list(ra, dec, image_type='stack')
            if not file_list:
                print(f"No Pan-STARRS images found at RA={ra:.4f}, Dec={dec:.4f}")
                return None
            
            # Find the file for the requested band
            band_file = None
            for file_info in file_list:
                if file_info.get('filter') == band:
                    band_file = file_info.get('filename')
                    break
            
            if not band_file:
                print(f"No {band}-band image found at this position")
                return None
            
            filename = band_file
        
        # Step 2: Request cutout using the actual file path
        size_pixels = int(size / 0.25)  # Convert to pixels
        
        params = {
            'ra': ra,
            'dec': dec,
            'size': size_pixels,
            'format': 'jpg',
            'output_size': size_pixels,
            'red': filename  # Use actual file path for single-band image
        }
        
        try:
            response = requests.get(self.BASE_URL, params=params, timeout=30)
            
            if response.status_code == 200 and response.headers.get('Content-Type', '').startswith('image'):
                # Validate image
                try:
                    img = Image.open(BytesIO(response.content))
                    img.verify()
                    img = Image.open(BytesIO(response.content))  # Re-open after verify
                    
                    # Optionally add target indicator (red dashed circle at center)
                    if add_indicator:
                        img = self._add_target_indicator(img)
                    
                    # Save annotated version for download
                    img_bytes = BytesIO()
                    img.save(img_bytes, format='JPEG', quality=95)
                    annotated_data = img_bytes.getvalue()
                    
                    return {
                        'survey': self.name,
                        'filter': band,
                        'ra': ra,
                        'dec': dec,
                        'size_arcsec': size,
                        'image_url': response.url,
                        'image_pil': img,
                        'image_data': annotated_data,
                        'format': 'jpg',
                        'pixel_scale': 0.25,
                        'success': True,
                        'filename': filename
                    }
                except Exception as img_err:
                    print(f"Invalid image data: {img_err}")
                    return None
        
        except Exception as e:
            print(f"Error fetching cutout: {e}")
        
        return None
    
    def _add_target_indicator(self, img: Image.Image, circle_radius: int = 40) -> Image.Image:
        """
        Add a red dashed circle at the center of the image to indicate target location
        
        Args:
            img: PIL Image object
            circle_radius: Radius of the indicator circle in pixels (default 40)
        
        Returns:
            Image with target indicator overlay
        """
        # Convert to RGB if needed (for drawing colored overlay)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Create a copy to draw on
        img_copy = img.copy()
        draw = ImageDraw.Draw(img_copy)
        
        # Get center coordinates
        width, height = img.size
        center_x, center_y = width // 2, height // 2
        
        # Use bright red that stands out on dark backgrounds
        color = (255, 0, 0)  # Pure red
        line_width = 2
        
        # Draw dashed circle ONLY - no center markers to avoid obscuring the object
        num_dashes = 24  # Number of dashes around the circle
        dash_length = 15  # degrees per dash
        gap_length = 15   # degrees per gap
        
        for i in range(num_dashes):
            start_angle = i * (dash_length + gap_length)
            end_angle = start_angle + dash_length
            
            # Draw arc
            bbox = [
                center_x - circle_radius,
                center_y - circle_radius,
                center_x + circle_radius,
                center_y + circle_radius
            ]
            draw.arc(bbox, start=start_angle, end=end_angle, fill=color, width=line_width)
        
        return img_copy
    
    def get_multiband_cutouts(self, 
                             ra: float, 
                             dec: float,
                             size: float = 60.0,
                             bands: Optional[List[str]] = None) -> List[Dict]:
        """
        Get cutouts in multiple bands
        
        Args:
            ra: Right Ascension (degrees)
            dec: Declination (degrees)
            size: Cutout size in arcseconds  
            bands: List of bands to retrieve (default: all)
        
        Returns:
            List of cutout dicts
        """
        if bands is None:
            bands = self.bands
        
        results = []
        for band in bands:
            cutout = self.get_cutout(ra, dec, size, band=band)
            if cutout:
                results.append(cutout)
        
        return results
