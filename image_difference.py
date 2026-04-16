"""
Image Differencing for Asteroid Detection

Modern asteroid detection technique: subtract two images taken at different times.
Stars cancel out, moving objects appear as bright/dark pairs.

This is how Pan-STARRS, ZTF, and other surveys detect asteroids!
"""

from astropy.io import fits
import numpy as np
from PIL import Image
from io import BytesIO
import requests
from typing import Optional, Dict, Tuple
from datetime import datetime


class ImageDifferencer:
    """Create difference images to detect moving objects"""
    
    def __init__(self):
        self.ps1_base_url = "https://ps1images.stsci.edu/cgi-bin/fitscut.cgi"
        self.ps1_info_url = "https://ps1images.stsci.edu/cgi-bin/ps1filenames.py"
    
    def download_fits_cutout(self, 
                            ra: float, 
                            dec: float, 
                            size: float,
                            filename: str) -> Optional[np.ndarray]:
        """
        Download FITS cutout from Pan-STARRS
        
        Args:
            ra: Right Ascension (degrees)
            dec: Declination (degrees)
            size: Size in arcseconds
            filename: Specific warp filename
        
        Returns:
            2D numpy array or None
        """
        size_pixels = int(size / 0.25)  # Pan-STARRS pixel scale
        
        params = {
            'ra': ra,
            'dec': dec,
            'size': size_pixels,
            'format': 'fits',
            'red': filename
        }
        
        try:
            print(f"  Downloading FITS: {filename}")
            response = requests.get(self.ps1_base_url, params=params, timeout=60)
            
            if response.status_code == 200:
                # Parse FITS data
                fits_data = BytesIO(response.content)
                with fits.open(fits_data) as hdul:
                    image_data = hdul[0].data.astype(float)
                    print(f"    ✓ Downloaded: {image_data.shape} pixels")
                    return image_data
            else:
                print(f"    ✗ Failed: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            print(f"    ✗ Error: {e}")
            return None
    
    def create_difference_image(self,
                               ra: float,
                               dec: float,
                               filename1: str,
                               filename2: str,
                               size: float = 240.0) -> Optional[Dict]:
        """
        Create difference image from two epochs
        
        Args:
            ra: Right Ascension (degrees)
            dec: Declination (degrees)
            filename1: First warp filename (reference)
            filename2: Second warp filename (new)
            size: Size in arcseconds
        
        Returns:
            Dict with difference image and metadata
        """
        print(f"\n{'='*70}")
        print(f"CREATING DIFFERENCE IMAGE")
        print(f"{'='*70}\n")
        print(f"Position: RA={ra:.4f}°, Dec={dec:.4f}°")
        print(f"Size: {size}\" ({int(size/0.25)} pixels)")
        
        # Download both images
        print(f"\nDownloading reference image...")
        im1 = self.download_fits_cutout(ra, dec, size, filename1)
        
        print(f"\nDownloading new image...")
        im2 = self.download_fits_cutout(ra, dec, size, filename2)
        
        if im1 is None or im2 is None:
            print(f"\n✗ Failed to download images")
            return None
        
        # Check shapes match
        if im1.shape != im2.shape:
            print(f"\n✗ Image shapes don't match: {im1.shape} vs {im2.shape}")
            return None
        
        print(f"\n✓ Both images downloaded successfully")
        
        # Handle NaN values before subtraction
        print(f"\nHandling NaN values...")
        nan_mask = np.isnan(im1) | np.isnan(im2)
        print(f"  NaN pixels: {np.sum(nan_mask)} / {im1.size} ({100*np.sum(nan_mask)/im1.size:.1f}%)")
        
        # Replace NaN with median of valid pixels
        im1 = np.nan_to_num(im1, nan=np.nanmedian(im1))
        im2 = np.nan_to_num(im2, nan=np.nanmedian(im2))
        
        # Simple difference: new - reference
        print(f"\nComputing difference (new - reference)...")
        diff = im2 - im1
        
        print(f"  Statistics:")
        print(f"    Mean: {np.mean(diff):.2f}")
        print(f"    Std:  {np.std(diff):.2f}")
        print(f"    Min:  {np.min(diff):.2f}")
        print(f"    Max:  {np.max(diff):.2f}")
        
        # Create visualization
        print(f"\nCreating visualization...")
        
        # Original images as PIL
        im1_vis = self._fits_to_pil(im1, stretch='log')
        im2_vis = self._fits_to_pil(im2, stretch='log')
        
        # Difference image (highlight both positive and negative)
        diff_vis = self._diff_to_pil(diff, stretch='linear')
        
        print(f"✓ Difference image created!")
        print(f"\n💡 Moving objects appear as bright/dark pairs")
        print(f"   Stars cancel out, asteroid stands out!")
        
        return {
            'diff': diff,
            'im1': im1,
            'im2': im2,
            'diff_vis': diff_vis,
            'im1_vis': im1_vis,
            'im2_vis': im2_vis,
            'ra': ra,
            'dec': dec,
            'size': size,
            'filename1': filename1,
            'filename2': filename2
        }
    
    def _fits_to_pil(self, data: np.ndarray, stretch: str = 'log') -> Image.Image:
        """Convert FITS data to PIL Image with scaling"""
        
        # Handle NaN values
        data = np.nan_to_num(data, nan=0.0, posinf=0.0, neginf=0.0)
        
        # Clip extreme values
        vmin, vmax = np.percentile(data, [1, 99])
        data = np.clip(data, vmin, vmax)
        
        # Apply stretch
        if stretch == 'log':
            # Log stretch for astronomical data
            data = data - np.min(data) + 1  # Make positive
            data = np.log10(data)
        
        # Normalize to 0-255
        data = (data - np.min(data)) / (np.max(data) - np.min(data))
        data = (data * 255).astype(np.uint8)
        
        # Convert to PIL Image
        return Image.fromarray(data, mode='L')
    
    def _diff_to_pil(self, diff: np.ndarray, stretch: str = 'linear') -> Image.Image:
        """
        Convert difference image to PIL with special colormap
        Positive differences = bright, negative = dark
        """
        
        # Handle NaN
        diff = np.nan_to_num(diff, nan=0.0, posinf=0.0, neginf=0.0)
        
        # Clip to ±5 sigma
        sigma = np.std(diff)
        vmin, vmax = -5*sigma, 5*sigma
        diff = np.clip(diff, vmin, vmax)
        
        # Normalize to 0-255 (gray = 128 = no change)
        diff_norm = (diff - vmin) / (vmax - vmin)
        diff_scaled = (diff_norm * 255).astype(np.uint8)
        
        # Create RGB image with colormap
        # Blue = negative (object was there), Red = positive (object is there now)
        img_rgb = np.zeros((*diff.shape, 3), dtype=np.uint8)
        
        # Red channel: positive differences
        img_rgb[:, :, 0] = np.where(diff > 0, diff_scaled, 128)
        
        # Green channel: close to zero
        img_rgb[:, :, 1] = 128
        
        # Blue channel: negative differences
        img_rgb[:, :, 2] = np.where(diff < 0, 255 - diff_scaled, 128)
        
        return Image.fromarray(img_rgb, mode='RGB')
    
    def save_fits(self, data: np.ndarray, filename: str):
        """Save numpy array as FITS file"""
        hdu = fits.PrimaryHDU(data)
        hdu.writeto(filename, overwrite=True)
        print(f"✓ Saved: {filename}")


if __name__ == '__main__':
    from surveys.panstarrs import PanSTARRSClient
    
    print("Testing Image Differencing for Asteroid Detection")
    print("="*70)
    
    # Get warp files at a fixed position (Ceres on 2012-06-01)
    ps_client = PanSTARRSClient()
    
    ra = 75.0059
    dec = 23.9419
    
    print(f"\nQuerying warp images at RA={ra:.4f}°, Dec={dec:.4f}°...")
    warp_files = ps_client.get_file_list(ra, dec, image_type='warp')
    
    if warp_files:
        i_band = [w for w in warp_files if w['filter'] == 'i']
        i_band.sort(key=lambda x: x['mjd'])
        
        print(f"✓ Found {len(i_band)} i-band warp images")
        
        if len(i_band) >= 2:
            # Take two images separated in time
            ref_warp = i_band[0]
            new_warp = i_band[len(i_band)//2]  # Middle epoch
            
            from datetime import datetime, timedelta
            mjd_epoch = datetime(1858, 11, 17)
            
            ref_date = (mjd_epoch + timedelta(days=ref_warp['mjd'])).strftime('%Y-%m-%d')
            new_date = (mjd_epoch + timedelta(days=new_warp['mjd'])).strftime('%Y-%m-%d')
            
            print(f"\nSelected images:")
            print(f"  Reference: {ref_date} (MJD {ref_warp['mjd']:.2f})")
            print(f"  New:       {new_date} (MJD {new_warp['mjd']:.2f})")
            print(f"  Separation: {new_warp['mjd'] - ref_warp['mjd']:.1f} days")
            
            # Create difference image
            differ = ImageDifferencer()
            result = differ.create_difference_image(
                ra=ra,
                dec=dec,
                filename1=ref_warp['filename'],
                filename2=new_warp['filename'],
                size=240.0
            )
            
            if result:
                # Save outputs
                differ.save_fits(result['diff'], '/tmp/ps1_diff.fits')
                result['diff_vis'].save('/tmp/ps1_diff.png')
                result['im1_vis'].save('/tmp/ps1_ref.png')
                result['im2_vis'].save('/tmp/ps1_new.png')
                
                print(f"\n✓ Saved difference image to /tmp/ps1_diff.fits")
                print(f"✓ Saved visualization to /tmp/ps1_diff.png")
                print(f"\n💡 The asteroid appears as a bright/dark pair in the difference image!")

