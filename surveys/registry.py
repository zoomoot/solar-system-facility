"""
Survey Registry
Central registry of all available sky surveys
"""

from typing import Dict, List, Optional
from .panstarrs import PanSTARRSClient


SURVEY_REGISTRY = {
    'panstarrs': {
        'name': 'Pan-STARRS DR2',
        'client_class': PanSTARRSClient,
        'years': (2009, 2024),
        'depth_mag': 24.0,
        'bands': ['g', 'r', 'i', 'z', 'y'],
        'coverage': '3π sr (δ > -30°)',
        'priority': 5,
        'status': 'active',
        'docs': 'https://outerspace.stsci.edu/display/PANSTARRS',
        'description': 'Deep survey of 3/4 of the sky from Haleakala, Hawaii'
    },
    # Placeholder for future surveys
    'ztf': {
        'name': 'Zwicky Transient Facility',
        'client_class': None,  # To be implemented
        'years': (2018, 2024),
        'depth_mag': 20.5,
        'bands': ['g', 'r', 'i'],
        'coverage': 'Northern sky (δ > -30°)',
        'priority': 4,
        'status': 'planned',
        'docs': 'https://www.ztf.caltech.edu/',
        'description': 'All-sky transient survey from Palomar Observatory'
    },
    'sdss': {
        'name': 'Sloan Digital Sky Survey',
        'client_class': None,  # To be implemented
        'years': (2000, 2009),
        'depth_mag': 22.5,
        'bands': ['u', 'g', 'r', 'i', 'z'],
        'coverage': '35% of sky',
        'priority': 3,
        'status': 'planned',
        'docs': 'https://www.sdss.org/',
        'description': 'Legacy survey covering 11,000 square degrees'
    },
    'neowise': {
        'name': 'NEOWISE',
        'client_class': None,  # To be implemented
        'years': (2010, 2024),
        'depth_mag': 17.0,  # W1 band
        'bands': ['W1', 'W2'],
        'coverage': 'All-sky',
        'priority': 4,
        'status': 'planned',
        'docs': 'https://neowise.ipac.caltech.edu/',
        'description': 'Infrared all-sky survey for asteroids and NEOs'
    },
}


def get_survey_client(survey_id: str):
    """
    Get survey client instance
    
    Args:
        survey_id: Survey identifier (e.g., 'panstarrs')
    
    Returns:
        Survey client instance or None
    """
    if survey_id not in SURVEY_REGISTRY:
        return None
    
    survey_info = SURVEY_REGISTRY[survey_id]
    client_class = survey_info.get('client_class')
    
    if client_class is None:
        return None
    
    return client_class()


def get_available_surveys() -> List[Dict]:
    """
    Get list of all available (implemented) surveys
    
    Returns:
        List of survey info dicts
    """
    available = []
    
    for survey_id, info in SURVEY_REGISTRY.items():
        if info['client_class'] is not None:
            available.append({
                'id': survey_id,
                'name': info['name'],
                'years': info['years'],
                'priority': info['priority'],
                'bands': info['bands'],
                'status': info['status']
            })
    
    return available


def get_survey_info(survey_id: str) -> Optional[Dict]:
    """Get detailed info for a survey"""
    return SURVEY_REGISTRY.get(survey_id)
