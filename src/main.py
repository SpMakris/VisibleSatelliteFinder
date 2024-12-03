import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
from datetime import datetime
from satellite_finder import satellite_db
import pytz
from datetime import datetime
from pass_plotter import plot_az_el_pass


class SatellitePassTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Satellite Pass Tracker")
        self.config_data = self.load_config()
        self.sat_db = satellite_db()
        self.create_widgets()
        self.last_results = []

    def create_widgets(self):
        def add_label_entry(row, label, default_value):
            ttk.Label(self.root, text=label).grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
            entry = ttk.Entry(self.root)
            entry.insert(0, default_value)
            entry.grid(row=row, column=1, padx=5, pady=5)
            return entry

        # Input Fields
        self.date_entry = add_label_entry(0, "Date (YYYY-MM-DD):", datetime.now().strftime("%Y-%m-%d"))
        self.time_entry = add_label_entry(1, "Time (HH:MM:SS):", datetime.now().strftime("%H:%M:%S"))
        self.location_entry = add_label_entry(2, "Location (Lat, Long):", self.config_data.get("location", "0.0, 0.0"))
        self.hours_window_entry = add_label_entry(3, "Search Window (hours):", self.config_data.get("window_hours", 0))
        self.min_altitude_entry = add_label_entry(5, "Min Highest Point (Altitude in degrees):", self.config_data.get("min_altitude", 0))
        self.min_sma_entry = add_label_entry(6, "Height (Min):", self.config_data.get("min_sma", 0))
        self.max_sma_entry = add_label_entry(7, "Height (Max):", self.config_data.get("max_sma", 0))

        # Starlink Dropdown
        ttk.Label(self.root, text="Include Starlink:").grid(row=8, column=0, sticky=tk.W, padx=5, pady=5)
        self.include_starlink = ttk.Combobox(self.root, values=["False", "True"], state="readonly")
        self.include_starlink.set("False")
        self.include_starlink.grid(row=8, column=1, padx=5, pady=5)

        # Search Button
        ttk.Button(self.root, text="Search for Visible Passes", command=self.on_search).grid(row=9, column=0, columnspan=2, pady=10)
        ttk.Button(self.root, text="Reload TLE", command=self.sat_db.reload_tle).grid(row=9, column=1, columnspan=2, pady=10)

        # Results Frame and Treeview
        self.results_frame = ttk.Frame(self.root)
        self.results_frame.grid(row=10, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")

        self.columns = ("#", "Satellite", "Start Time", "Peak Time", "End Time", "Start Azimuth", "End Azimuth", "Peak Altitude", "Duration", "Sunlit Pass Start", "Sunlit Pass End")
        self.treeview = ttk.Treeview(self.results_frame, columns=self.columns, show="headings", height=10)
        self.treeview.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(self.results_frame, orient="vertical", command=self.treeview.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.treeview.configure(yscrollcommand=scrollbar.set)
        # Configure column widths
        self.treeview.column("#", width=5)  # About 3 characters wide
        self.treeview.column("Satellite", width=120)
        self.treeview.column("Start Time", width=40)
        self.treeview.column("Peak Time", width=40)
        self.treeview.column("End Time", width=40)
        self.treeview.column("Start Azimuth", width=40)
        self.treeview.column("End Azimuth", width=40)
        self.treeview.column("Peak Altitude", width=40)
        self.treeview.column("Duration", width=25)
        self.treeview.column("Sunlit Pass Start", width=40)
        self.treeview.column("Sunlit Pass End", width=40)
        for col in self.columns:
            self.treeview.heading(col, text=col)

        # Context Menu
        self.context_menu = tk.Menu(self.root, tearoff=0)
        for label, command in [("Copy TLE Line 1", self.copy_tle_line1),
                            ("Copy TLE Line 2", self.copy_tle_line2),
                            ("Show Pass Graph", self.show_pass_graph)]:
            self.context_menu.add_command(label=label, command=command)
        self.treeview.bind("<Button-3>", self.show_context_menu)

        # Total Results Label
        self.total_results_label = ttk.Label(self.root, text="Total Results: 0")
        self.total_results_label.grid(row=11, column=0, columnspan=2, pady=5)

        # Resizing Configuration
        self.root.grid_rowconfigure(10, weight=1)
        self.root.grid_columnconfigure((0, 1), weight=1)
        self.results_frame.grid_rowconfigure(0, weight=1)
        self.results_frame.grid_columnconfigure(0, weight=1)


    def load_config(self):
        config_file = "assets/config.json"
        if os.path.exists(config_file):
            with open(config_file, "r") as file:
                return json.load(file)
        else:
            return {}

    def on_search(self):
        try:
            date = self.date_entry.get()
            time = self.time_entry.get()
            location = self.location_entry.get()
            hours_window = float(self.hours_window_entry.get())
            min_altitude = float(self.min_altitude_entry.get())
            min_sma = float(self.min_sma_entry.get())
            max_sma = float(self.max_sma_entry.get())
            include_starlink = self.include_starlink.get() == "True"  # Convert to boolean

            if hours_window < 0 or min_sma < 0 or max_sma < 0:
                raise ValueError("Timeframe and semimajor axis range must be non-negative.")

            if min_sma > max_sma:
                raise ValueError("Minimum semimajor axis cannot be greater than the maximum.")

            # Call the actual function to search for visible passes
            results = self.search_visible_passes(
                date, time, location, hours_window, min_altitude, min_sma, max_sma, include_starlink
            )
            formated_results, self.last_results = results
            # Clear previous results from the Treeview
            for item in self.treeview.get_children():
                self.treeview.delete(item)

            # Insert new results into the Treeview
            if formated_results:
                for result in formated_results:
                    self.treeview.insert("", tk.END, values=result)
                # Update the total results label
                self.total_results_label.config(text=f"Total Results: {len(formated_results)}")
            else:
                messagebox.showinfo("No Results", "No visible passes found.")

        except ValueError as e:
            messagebox.showerror("Input Error", str(e))

    def search_visible_passes(self, date, time, location, hours_window, min_altitude, min_sma, max_sma, include_starlink):
        # Existing logic for searching passes
        local_tz = pytz.timezone("Etc/GMT-2")
        time = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M:%S")
        time = local_tz.localize(time)

        results = self.sat_db.find_visible_satellites(
            location=tuple(map(float, location.split(","))),
            time=time.astimezone(pytz.utc),
            sma_range=(min_sma, max_sma),
            altitude_degrees=10,
            min_peak_altitude=min_altitude,
            timeframe_hours=hours_window,
            min_duration=30,
            include_starlink=include_starlink
        )


        formatted_results = []
        i=0
        for sat in results:
            i=i+1
            formatted_results.append((
                i, 
                sat[0].name,
                sat[1].utc_datetime().astimezone(local_tz).strftime("%H:%M:%S"),
                sat[2].utc_datetime().astimezone(local_tz).strftime("%H:%M:%S"),
                sat[3].utc_datetime().astimezone(local_tz).strftime("%H:%M:%S"),
                sat[4],
                sat[5],
                f"{round(sat[6], 1)}°",
                f"{round(sat[7])}s",
                sat[8].astimezone(local_tz).strftime("%H:%M:%S"),
                sat[9].astimezone(local_tz).strftime("%H:%M:%S")
            ))

        return formatted_results, results

    def show_context_menu(self, event):
        item_id = self.treeview.identify_row(event.y)
        if item_id:
            self.treeview.selection_set(item_id)
            self.context_menu.post(event.x_root, event.y_root)

    def copy_tle_line(self, line_index):
        selected_item = self.treeview.selection()
        if selected_item:
            # Get the satellite name from the selected row
            sat_name = self.treeview.item(selected_item, "values")[1]
            line1, line2 = self.sat_db.get_tle(sat_name)
            print(line1, line2)
            # Copy the specified TLE line to clipboard
            tle_line = line1 if line_index == 1 else line2
            self.root.clipboard_clear()
            self.root.clipboard_append(tle_line)
            self.root.update()  # Required to update the clipboard content

    def copy_tle_line1(self):
        self.copy_tle_line(1)

    def copy_tle_line2(self):
        self.copy_tle_line(2)


    def show_pass_graph(self):
        selected_item = self.treeview.selection()
        if selected_item:
            # Get the satellite name from the selected row
            sat_id = self.treeview.item(selected_item, "values")[0]
            sat = self.last_results[int(sat_id)-1][0]
            t_start = self.last_results[int(sat_id)-1][1].utc_datetime()
            t_stop = self.last_results[int(sat_id)-1][3].utc_datetime()
            location = self.location_entry.get()
            observer = tuple(map(float, location.split(",")))
            # Generate the pass graph
            data = self.sat_db.generate_azel_data(sat, observer, t_start, t_stop )
            # print(data)
            plot_az_el_pass(data, sat.name)


    
    
    


if __name__ == "__main__":
    root = tk.Tk()
    app = SatellitePassTrackerApp(root)
    root.mainloop()
