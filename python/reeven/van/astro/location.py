from astropy.coordinates import Longitude, Latitude
from astropy import units as u


class Location:
    def __init__(self,):
        # Variables holding the site information
        self.longitude = Longitude("-071:14:12.5 degrees")
        self.latitude = Latitude("-29:56:29.7 degrees")
        self.height = 110.0 * u.meter
        self.observing_location_name = "La_Serena"
        self.utc_offset = 4
