from skyfield.api import load, wgs84, utc, EarthSatellite
from datetime import datetime, timedelta
import pytz
import requests
import os

def azimuth_to_direction(azimuth):
    """
    Converts an azimuth angle to a compass direction.
    Azimuth is expected in degrees, where 0° is North, 90° is East, 180° is South, and 270° is West.
    """
    if azimuth >= 337.5 or azimuth < 22.5:
        return "N"
    elif azimuth >= 22.5 and azimuth < 67.5:
        return "NE"
    elif azimuth >= 67.5 and azimuth < 112.5:
        return "E"
    elif azimuth >= 112.5 and azimuth < 157.5:
        return "SE"
    elif azimuth >= 157.5 and azimuth < 202.5:
        return "S"
    elif azimuth >= 202.5 and azimuth < 247.5:
        return "SW"
    elif azimuth >= 247.5 and azimuth < 292.5:
        return "W"
    elif azimuth >= 292.5 and azimuth < 337.5:
        return "NW"


class satellite_db:
    def __init__(self, tle_file_path='assets/satellite_tles.txt'):     
        
        self.tle_file_path = tle_file_path
        #open file and remove empty lines
        with open(self.tle_file_path, 'r') as file:
            lines = file.readlines()
            lines = [line for line in lines if line.strip()]
        with open(self.tle_file_path, 'w') as file:
            file.writelines(lines)


        self.satellite_tle_dict = {}

        # Try to download the TLE file and save it locally
        try:
            self._fetch_and_save_tle_file()
        except Exception as e:
            print(f"Error fetching TLE file: {e}")
            # Try to use the local file if downloading failed
            try:
                self._load_local_tle_file()
            except Exception as e:
                raise Exception("Failed to fetch or load TLE file.")
            
        self.satellites = load.tle_file(tle_file_path)
        self.eph = load("de421.bsp")
        self.ts = load.timescale()
        self.sun = self.eph["sun"]
        print(f"Loaded {len(self.satellites)} satellites")

    def generate_azel_data(self, satellite,observer, t0, t1):
        """
        Generate azimuth and elevation data for a satellite between two times.

        Parameters:
            satellite_name (str): The name of the satellite.
            t0 (datetime): The start time as a timezone-aware datetime object.
            t1 (datetime): The end time as a timezone-aware datetime object.

        Returns:
            list: A list of tuples containing (time, azimuth, elevation) data points.
        """
        # satellite = self.satellites[satellite_name]
        observer = wgs84.latlon(observer[0], observer[1])
        difference = satellite - observer
        t_start = self.ts.utc(
            t0.year, t0.month, t0.day, t0.hour, t0.minute, t0.second
        )

        # Calculate the end time (t1) by adding the timeframe in hours directly to the time
        t_stop = self.ts.utc(
            t1.year,
            t1.month,
            t1.day,
            t1.hour,
            t1.minute,
            t1.second,
        )
        t_now = t_start
        azel_data = []
        while t_now < t_stop:
            topocentric = difference.at(t_now)
            alt, az, distance = topocentric.altaz()
            azel_data.append((t_now.utc_iso(), az.degrees, alt.degrees))
            t_now = t_now.utc_datetime() + timedelta(seconds=10)
            t_now = self.ts.utc(t_now.year, t_now.month, t_now.day, t_now.hour, t_now.minute, t_now.second)
        # topocentric = difference.at(t)
        # alt, az, distance = topocentric.altaz()
        return azel_data





    def _fetch_and_save_tle_file(self):
        """
        Fetches the TLE file from the internet and saves it locally.
        """
        try:
            url = "http://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle"
            response = requests.get(url)
            # Save the fetched TLE file locally
            if(response.text.__contains__("<!DOCTYPE")):
                raise Exception("Failed to fetch TLE file.")
            with open(self.tle_file_path, 'w') as f:
                f.write(response.text)
            print(f"TLE file downloaded and saved to {self.tle_file_path}")
            self._process_tle_file(response.text)
        except Exception as e:
            print(f"Failed to fetch TLE file: {e}")
            print("Failed to fetch TLE file, using local copy.")
            raise Exception("Failed to fetch TLE file.")

    def _load_local_tle_file(self):
        """
        Loads the TLE file from a local file.
        """
        if not os.path.exists(self.tle_file_path):
            raise Exception(f"Local TLE file '{self.tle_file_path}' not found.")

        with open(self.tle_file_path, 'r') as f:
            tle_data = f.read()
        print(f"Loaded TLE file from local file {self.tle_file_path}")
        self._process_tle_file(tle_data)

    def _process_tle_file(self, tle_data):
        """
        Processes the raw TLE data and populates the satellite_tle_dict.
        """
        tle_data = tle_data.strip().split('\n')

        for i in range(0, len(tle_data)-2, 3):
            name = tle_data[i].strip()  # Satellite name (the first line)
            tle_line_1 = tle_data[i + 1].strip()  # First TLE line (line 1)
            tle_line_2 = tle_data[i + 2].strip()  # Second TLE line (line 2)
            
            # Store TLE lines as a tuple in the dictionary
            tle_string = (tle_line_1, tle_line_2)
            
            # Add the satellite name and TLE string to the dictionary
            self.satellite_tle_dict[name] = tle_string
        

    def get_tle(self, satellite_name):
        """
        Retrieve the TLE string for a given satellite name.

        Parameters:
            satellite_name (str): The name of the satellite.

        Returns:
            str: A string containing the TLE lines, or None if the satellite is not found.
        """
        return self.satellite_tle_dict.get(satellite_name, None)

        print(self.satellite_tle_dict)

    def find_visible_satellites(
        self,
        location,
        time,
        sma_range,
        altitude_degrees=1.0,
        min_peak_altitude=30.0,
        timeframe_hours=2,
        min_duration=30,
        include_starlink=False,
    ):
        """
        Finds visible satellites from a given location and time that are illuminated by the Sun.

        Parameters:
            location (tuple): Tuple of latitude and longitude in degrees (lat, lon).
            time (datetime): The observation time as a timezone-aware datetime object.
            sma_range (tuple): Tuple of minimum and maximum semimajor axis values in kilometers (min_sma, max_sma).
            altitude_degrees (float): Minimum altitude above the horizon for visibility.

        Returns:
            list: A list of visible satellites with name, event times, and states (in sunlight or shadow).
        """
        # Load the satellite TLE data and ephemeris
        print("location", location)
        print("time", time)
        print("sma_range", sma_range)
        print("altitude_degrees", altitude_degrees)
        print("min_peak_altitude", min_peak_altitude)
        print("timeframe_hours", timeframe_hours)
        print("min_duration", min_duration)
        print("include_starlink", include_starlink)

        # Define the observer's location and time range
        observer = wgs84.latlon(location[0], location[1])
        # Get the start time (t0) from the input time
        t0 = self.ts.utc(
            time.year, time.month, time.day, time.hour, time.minute, time.second
        )

        # Calculate the end time (t1) by adding the timeframe in hours directly to the time
        t1 = self.ts.utc(
            time.year,
            time.month,
            time.day,
            time.hour + int(timeframe_hours),
            time.minute,
            time.second,
        )

        print(f"Searching for visible satellites from {t0.utc_iso()} to {t1.utc_iso()}")
        visible_satellites = []
        for satellite in self.satellites:
            if not include_starlink and "STARLINK" in satellite.name:
                continue
            geocentric = satellite.at(t0)
            height = wgs84.height_of(geocentric)
            if height.km < sma_range[0] or height.km > sma_range[1]:
                continue
            t, events = satellite.find_events(observer, t0, t1, altitude_degrees)
            # print(events)
            if len(events) <= 3:
                continue
            else:
                i = 0
                while events[i] != 0:
                    i += 1
                while i + 2 < len(events - 1):

                    t_peak = t[i + 1]
                    duration = t[i + 2] - t[i + 0]
                    t_start = t[i + 0]
                    t_end = t[i + 2]
                    # print(duration*24*3600)
                    i += 3
                    if duration * 24 * 3600 < min_duration:
                        continue
                    difference = satellite - observer
                    topocentric = difference.at(t_peak)
                    peak_alt, az, d = topocentric.altaz()
                    # print(peak_alt.degrees)
                    if peak_alt.degrees < min_peak_altitude:
                        continue
                    _, start_az, _ = difference.at(t_start).altaz()
                    _, end_az, _ = difference.at(t_end).altaz()

                    sunlit = satellite.at(t_peak).is_sunlit(self.eph)
                    # print(sunlit)
                    if sunlit:
                        visible_satellites.append(
                            [
                                satellite,
                                t_start,
                                t_peak,
                                t_end,
                                azimuth_to_direction(start_az.degrees),
                                azimuth_to_direction(end_az.degrees),
                                peak_alt.degrees,
                                duration,
                            ]
                        )

            # Sort the visible satellites by the start time (t_start) in position [1]
        visible_satellites.sort(key=lambda x: x[1])
        print("search complete")
        return visible_satellites


# Example usage
if __name__ == "__main__":
    location = (38.045887, 23.864028)
    # Ensure the datetime is timezone-aware and set to UTC
    # time = datetime.now()
    sat_db = satellite_db()
    today = datetime.today()

    # Set a custom time (e.g., 15:30:00)
    time = today.replace(hour=18 - 2, minute=00, second=0, microsecond=0)
    sma_range = (500, 600)  # SMA range in kilometers

    visible = sat_db.find_visible_satellites(location, time, sma_range)
    print(f"Found {len(visible)} visible satellites.")
    gmt_plus_2 = pytz.timezone("Etc/GMT-2")

    # Output:
    for sat in visible:
        print(
            sat[0].name,
            sat[1].utc_datetime().astimezone(gmt_plus_2).strftime("%H:%M:%S"),
            sat[2].utc_datetime().astimezone(gmt_plus_2).strftime("%H:%M:%S"),
            sat[3].utc_datetime().astimezone(gmt_plus_2).strftime("%H:%M:%S"),
            (sat[4]),
            (sat[5]),
            round(sat[6]),
            round(sat[7] * 24 * 3600),
        )
