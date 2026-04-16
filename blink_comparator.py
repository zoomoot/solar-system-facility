"""
TRUE Blink Comparator - Using Real Multi-Epoch Observations

This creates authentic blink comparator animations using individual Pan-STARRS
warp (single-epoch) images, showing the actual asteroid moving through real
observations taken on different nights.

NOT synthetic markers - REAL observations!
"""

from PIL import Image, ImageDraw, ImageFont
import io
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from surveys.panstarrs import PanSTARRSClient
from ephemeris_generator import EphemerisGenerator


def mjd_to_datetime(mjd: float) -> datetime:
    """Convert Modified Julian Date to datetime"""
    mjd_epoch = datetime(1858, 11, 17)
    return mjd_epoch + timedelta(days=mjd)


class BlinkComparator:
    """Create TRUE blink comparator animations from real multi-epoch observations"""
    
    def __init__(self):
        self.survey_client = PanSTARRSClient()
        self.ephem_gen = EphemerisGenerator()
    
    def create_true_blink_animation(self,
                                   designation: str,
                                   start_date: str,
                                   num_frames: int = 10,
                                   band: str = 'i',
                                   size: float = 240.0) -> Optional[bytes]:
        """
        Create TRUE blink comparator using FIXED star field with REAL multi-epoch observations
        
        Uses a FIXED sky position (from first date) and fetches REAL warp images from 
        different epochs. The star field stays constant, asteroid moves naturally.
        
        Args:
            designation: Object designation (e.g., '1', 'Ceres')
            start_date: Reference date for fixed position (YYYY-MM-DD)
            num_frames: Number of frames to fetch (up to 10)
            band: Filter band (default 'i')
            size: Image size in arcseconds
        
        Returns:
            Animated GIF bytes or None
        """
        print(f"\n{'='*70}")
        print(f"CREATING TRUE BLINK COMPARATOR FOR {designation}")
        print(f"Using FIXED star field with multi-epoch observations")
        print(f"{'='*70}\n")
        
        # Step 1: Get asteroid position at reference date for FIXED position
        print(f"Step 1: Getting reference position at {start_date}...")
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = start_dt + timedelta(days=1)
        
        ephem = self.ephem_gen.generate(
            designation=designation,
            start_date=start_date,
            end_date=end_dt.strftime('%Y-%m-%d'),
            step='1d'
        )
        
        if not ephem or len(ephem) == 0:
            print(f"✗ Could not get ephemeris for {designation}")
            return None
        
        # This is our FIXED position for ALL frames
        fixed_ra = ephem[0]['ra']
        fixed_dec = ephem[0]['dec']
        print(f"✓ Fixed star field position: RA={fixed_ra:.4f}°, Dec={fixed_dec:.4f}°")
        
        # Step 2: Query ALL warp images at this FIXED position
        print(f"\nStep 2: Querying all warp images at this fixed position...")
        warp_files = self.survey_client.get_file_list(
            ra=fixed_ra,
            dec=fixed_dec,
            image_type='warp'
        )
        
        if not warp_files:
            print(f"✗ No Pan-STARRS warp images found at this position")
            return None
        
        # Filter for requested band
        band_warps = [w for w in warp_files if w['filter'] == band]
        if not band_warps:
            print(f"✗ No {band}-band warp images found")
            return None
        
        # Sort chronologically
        band_warps.sort(key=lambda x: x['mjd'])
        
        print(f"✓ Found {len(band_warps)} {band}-band exposures at this position")
        print(f"  Date range: {mjd_to_datetime(band_warps[0]['mjd']).strftime('%Y-%m-%d')} to {mjd_to_datetime(band_warps[-1]['mjd']).strftime('%Y-%m-%d')}")
        
        # Step 3: Select frames - prefer same skycell to minimize grid artifacts
        # Group by skycell (extract from filename like 'rings.v3.skycell.1864.063...')
        from collections import defaultdict
        skycell_groups = defaultdict(list)
        for warp in band_warps:
            # Extract skycell ID from filename
            filename = warp.get('shortname', warp.get('filename', ''))
            if 'skycell' in filename:
                parts = filename.split('.')
                if len(parts) >= 5:
                    skycell_id = f"{parts[3]}.{parts[4]}"  # e.g., "1864.063"
                    skycell_groups[skycell_id].append(warp)
        
        # Find the skycell with most observations
        if skycell_groups:
            best_skycell = max(skycell_groups.keys(), key=lambda k: len(skycell_groups[k]))
            candidate_warps = skycell_groups[best_skycell]
            print(f"  • Using skycell {best_skycell} ({len(candidate_warps)} observations) to minimize grid artifacts")
        else:
            candidate_warps = band_warps
        
        # Select frames from this group
        if len(candidate_warps) <= num_frames:
            selected_warps = candidate_warps
        else:
            # Spread evenly across available observations in this skycell
            indices = [int(i * (len(candidate_warps) - 1) / (num_frames - 1)) for i in range(num_frames)]
            selected_warps = [candidate_warps[i] for i in indices]
        
        print(f"\nStep 3: Fetching {len(selected_warps)} images from FIXED position...")
        
        # Step 4: Fetch each warp image
        frames = []
        frame_info = []
        
        for idx, warp in enumerate(selected_warps):
            mjd = warp['mjd']
            obs_date = mjd_to_datetime(mjd)
            filename = warp['filename']
            
            print(f"  Frame {idx+1}/{len(selected_warps)}: {obs_date.strftime('%Y-%m-%d %H:%M')} (MJD {mjd:.2f})")
            
            # Fetch this specific warp image at FIXED position
            cutout = self.survey_client.get_cutout(
                ra=fixed_ra,
                dec=fixed_dec,
                size=size,
                band=band,
                filename=filename,
                add_indicator=False  # No synthetic markers
            )
            
            if cutout and 'image_pil' in cutout:
                img = cutout['image_pil']
                
                # Add date label
                img_labeled = self._add_date_label(img, obs_date, idx+1, len(selected_warps))
                frames.append(img_labeled)
                frame_info.append({
                    'date': obs_date,
                    'mjd': mjd,
                    'filename': filename
                })
                print(f"    ✓ Image retrieved")
            else:
                print(f"    ✗ Failed to get image")
        
        if len(frames) < 2:
            print(f"\n✗ Not enough frames ({len(frames)}) for blink comparator")
            return None
        
        # Step 5: Create animated GIF
        print(f"\nStep 4: Creating animated GIF with {len(frames)} REAL observations...")
        gif_bytes = self._create_gif(frames, duration=500)
        
        if gif_bytes:
            print(f"\n{'='*70}")
            print(f"✓ SUCCESS! TRUE BLINK COMPARATOR CREATED")
            print(f"{'='*70}")
            print(f"\nAnimation details:")
            print(f"  • Frames: {len(frames)} REAL multi-epoch observations")
            print(f"  • Band: {band}")
            print(f"  • Field size: {size}\"")
            print(f"  • FIXED position: RA={fixed_ra:.4f}°, Dec={fixed_dec:.4f}°")
            print(f"  • Observation dates: {frame_info[0]['date'].strftime('%Y-%m-%d')} to {frame_info[-1]['date'].strftime('%Y-%m-%d')}")
            print(f"\n💡 Watch for the asteroid MOVING through FIXED star field!")
            print(f"   Stars stay in place, asteroid changes position naturally")
        
        return gif_bytes
    
    def _add_date_label(self, img: Image.Image, obs_date: datetime, 
                       frame_num: int, total_frames: int) -> Image.Image:
        """
        Add date label to frame
        
        Args:
            img: PIL Image
            obs_date: Observation datetime
            frame_num: Current frame number
            total_frames: Total number of frames
        
        Returns:
            Labeled image
        """
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        img_copy = img.copy()
        draw = ImageDraw.Draw(img_copy)
        
        # Try to load a font
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
        except:
            font = ImageFont.load_default()
        
        # Format date
        date_str = obs_date.strftime('%Y-%m-%d %H:%M UT')
        
        # Draw label with background
        text_bbox = draw.textbbox((0, 0), date_str, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        # Semi-transparent black background
        padding = 5
        draw.rectangle(
            [5, 5, 5 + text_width + 2*padding, 5 + text_height + 2*padding],
            fill=(0, 0, 0, 180)
        )
        
        # White text
        draw.text((5 + padding, 5 + padding), date_str, fill=(255, 255, 255), font=font)
        
        # Frame counter in bottom-right
        frame_text = f"{frame_num}/{total_frames}"
        counter_bbox = draw.textbbox((0, 0), frame_text, font=font)
        counter_width = counter_bbox[2] - counter_bbox[0]
        counter_height = counter_bbox[3] - counter_bbox[1]
        
        img_width, img_height = img.size
        draw.rectangle(
            [img_width - counter_width - 2*padding - 5, img_height - counter_height - 2*padding - 5,
             img_width - 5, img_height - 5],
            fill=(0, 0, 0, 180)
        )
        draw.text(
            (img_width - counter_width - padding - 5, img_height - counter_height - padding - 5),
            frame_text, fill=(255, 255, 255), font=font
        )
        
        return img_copy
    
    def _create_gif(self, frames: List[Image.Image], duration: int = 500) -> Optional[bytes]:
        """
        Create animated GIF from list of PIL Images
        
        Args:
            frames: List of PIL Image objects
            duration: Duration per frame in milliseconds
        
        Returns:
            GIF as bytes or None
        """
        if not frames:
            return None
        
        output = io.BytesIO()
        
        frames[0].save(
            output,
            format='GIF',
            save_all=True,
            append_images=frames[1:],
            duration=duration,
            loop=0  # Loop forever
        )
        
        return output.getvalue()


if __name__ == '__main__':
    # Test the TRUE blink comparator
    blink = BlinkComparator()
    
    print("\n" + "="*70)
    print("TESTING TRUE BLINK COMPARATOR")
    print("="*70)
    
    # Test with Ceres
    gif_bytes = blink.create_true_blink_animation(
        designation='1',
        start_date='2015-06-01',
        num_frames=10,
        band='i',
        size=240.0
    )
    
    if gif_bytes:
        output_path = '/tmp/ceres_true_blink.gif'
        with open(output_path, 'wb') as f:
            f.write(gif_bytes)
        print(f"\n✓ Saved to {output_path}")
        print(f"  Size: {len(gif_bytes):,} bytes")
    else:
        print("\n✗ Failed to create animation")
