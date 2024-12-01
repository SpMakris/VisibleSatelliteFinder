
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime

def plot_az_el_pass(data, sat_name=""):
        """
        Plots the Azimuth (Az) vs Elevation (El) graph for satellite pass data and an Az-El diagram.

        Parameters:
        data (list): List of tuples containing timestamp (str), azimuth (float), and elevation (float)
        """
        # Extract timestamps, azimuths, and elevations from the data
        timestamps = [datetime.strptime(item[0], "%Y-%m-%dT%H:%M:%SZ") for item in data]
        azimuths = [item[1] for item in data]
        elevations = [item[2] for item in data]

        # Create the figure and axis for plotting
        fig, (ax1, ax3) = plt.subplots(1, 2, figsize=(15, 6))  # Create a side-by-side plot

        # --- Time-series plot ---
        # Plot Azimuth data
        ax1.set_xlabel("Time (UTC)")
        ax1.set_ylabel("Azimuth (°)", color="tab:blue")
        ax1.plot(timestamps, azimuths, color="tab:blue", label="Azimuth")
        ax1.tick_params(axis='y', labelcolor="tab:blue")
        
        # Create a second y-axis for the Elevation
        ax2 = ax1.twinx()
        ax2.set_ylabel("Elevation (°)", color="tab:green")
        ax2.plot(timestamps, elevations, color="tab:green", label="Elevation")
        ax2.tick_params(axis='y', labelcolor="tab:green")

        # Format the x-axis to show time nicely
        ax1.xaxis.set_major_locator(mdates.MinuteLocator(interval=1))
        ax1.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))
        plt.xticks(rotation=45)

        ax1.set_title(f"{sat_name} Pass Azimuth and Elevation")
        ax1.legend(loc='upper left')
        
        # --- Az-El Diagram ---
        # Create the polar plot for Az-El diagram
        ax3 = fig.add_subplot(122, projection='polar')  # Create a polar subplot for the Az-El diagram
        
        # Convert azimuth and elevation to numpy arrays for plotting
        azimuths_rad = np.radians(azimuths)  # Convert azimuths to radians for polar plotting
        elevations_rad = 90 - np.array(elevations)  # Invert elevation for radial distance (90° at center)
        
        # Plot elevation as circles with azimuth as angle and elevation as radius
        for i, az in enumerate(azimuths_rad):
            # Plot the point on the polar plot (azimuth as theta, inverted elevation as radius)
            ax3.plot(az, elevations_rad[i], 'o', color="tab:green")

        # Set the radius limits (elevation range from 0° to 90°)
        ax3.set_rmax(90)  # Maximum radius (elevation) is 90 degrees at the center
        ax3.set_rticks([10, 20, 30, 40, 50, 60, 70, 80, 90])  # Elevation tick marks from center to outer edge

        # Invert the radial axis
        ax3.set_yticklabels([str(90 - tick) for tick in ax3.get_yticks()])  # Convert radial ticks to proper elevation

        ax3.set_rlabel_position(-22.5)  # Place labels around the plot
        ax3.set_theta_zero_location("N")  # Set 0° azimuth to be at the top of the plot
        ax3.set_theta_direction(-1)  # Make azimuth grow counterclockwise

        # Set title for the Az-El diagram
        ax3.set_title(f"{sat_name} Az-El Diagram")

        # Show the plot
        plt.tight_layout()
        plt.show()