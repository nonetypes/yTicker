# γTicker interdependent classes
# Ticker, TickerRow, TickerAPIProperties

import tkinter as tk
from threading import Thread
from os import system, path, getcwd
# from os import system, path, getcwd, startfile
from pyperclip import copy as pyperclip_copy
from classes_others import TickerAPI, TickerPreferences, Tooltip
from alarms import TickerAlarm, AlarmNotification
from functions import is_float, reorder_rows, manage_urls, print_thread, TimerThread
from settings import settings
from util import dir_path


class Ticker:
    """γTicker main tkinter window object.

    A list of TickerRow objects are created here by calling Ticker.create_rows().
    create_rows(), update(), and window.mainloop() are called upon initialiazation.
    """
    def __init__(self):
        self.ticker_rows = []
        self.ticker_preferences = None
        self.api_properties = None

        # Main tkinter window
        self.window = tk.Tk()
        self.window.title('γTicker')
        # Call a function when main window is closed.
        self.window.protocol('WM_DELETE_WINDOW', self.on_close)
        # Geometry & Padding
        try:
            self.geometry = settings.dictionary['global']['geometry']
            self.window.geometry(self.geometry)
        except Exception as error:
            print_thread(f'Error -- Invalid geometry from settings: {error}')
            self.geometry = '285x310'
            self.window.geometry(self.geometry)
            settings.dictionary['global']['geometry'] = self.geometry
            settings.save()
        self.padx = 2
        self.pady = 0

        # Canvas for the buttons at the top.
        self.menu_canvas = tk.Canvas(self.window)
        self.menu_canvas.pack(side="top", fill="both")

        # Add API Button
        self.add_img = tk.PhotoImage(file=dir_path("assets/add.png"))
        self.add_button = tk.Button(self.menu_canvas, image=self.add_img, command=self.new_api)
        self.add_button.grid(row=0, column=0, padx=(8, 4), pady=(8, 4))
        Tooltip(self.add_button, 'Add New API')

        # Refresh Button
        self.refresh_img = tk.PhotoImage(file=dir_path("assets/refresh.png"))
        self.refresh_button = tk.Button(self.menu_canvas, image=self.refresh_img, command=self.update)
        self.refresh_button.grid(row=0, column=1, padx=4, pady=(8, 4))
        Tooltip(self.refresh_button, 'Refresh All APIs')

        # Prefrences Button
        self.settings_img = tk.PhotoImage(file=dir_path("assets/settings.png"))
        self.settings_button = tk.Button(self.menu_canvas, image=self.settings_img,
                                         command=self.preferences)
        self.settings_button.grid(row=0, column=2, padx=4, pady=(8, 4))
        Tooltip(self.settings_button, 'Preferences')

        # Frame for scrollbar and api_canvas -- There's another frame nested in the canvas which is nested here.
        # Got a lot of help with the scrollbar from https://stackoverflow.com/a/3092341
        self.scroll_frame = tk.Frame(self.window)
        self.scroll_frame.pack(side="top", fill="both", expand=True)
        self.scroll_frame.bind('<Configure>', self.frame_configure)

        # Scrollbar for TickerRow objects
        self.scrollbar = tk.Scrollbar(self.scroll_frame, orient='vertical')
        self.scrollbar.pack(side="right", fill="y")

        # API Canvas
        self.api_canvas = tk.Canvas(self.scroll_frame, yscrollcommand=self.scrollbar.set)
        self.api_canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.configure(command=self.api_canvas.yview)

        # API Frame -- TickerRow objects are put here.
        # For the scrollbar to function properly with a canvas, api_frame cannot be packed or gridded. I don't know why.
        self.api_frame = tk.Frame(self.api_canvas)
        self.api_canvas.create_window((0, 0), window=self.api_frame, anchor='nw')
        try:
            self.window.iconbitmap(dir_path("assets/yTicker.ico"))
        except Exception as error:
            print_thread(f'Error -- yTicker.ico not found: {error}')

        self.foreground()
        self.create_rows()
        self.update()
        self.window.mainloop()

    def on_close(self):
        """Called when main window is closed.

        Cancel all outstanding threaded timers.
        Save current window geometry to settings.
        """
        for row in self.ticker_rows:
            row.update_cancel()
        settings.dictionary['global']['geometry'] = f'{self.window.winfo_width()}x{self.window.winfo_height()}'
        settings.save()
        self.window.destroy()

    def frame_configure(self, event):
        """"Reset the scroll region to encompass the inner frame."
        https://stackoverflow.com/a/3092341
        """
        self.api_canvas.config(scrollregion=self.api_canvas.bbox('all'))

    def create_rows(self):
        """Create a list of TickerRow objects with nested TickerAPI objects.

        Data is fetched from settings file.
        """
        for api in settings.dictionary['apis']:
            name = api['name']
            url = api['url']
            refresh = api['refresh']
            term = api['term']
            decimals = api['decimals']
            sequence = api['sequence']
            log = api['log']
            try:
                api_object = TickerAPI(name, url, term, decimals, log)
                self.ticker_rows.append(TickerRow(self, api_object, sequence, refresh))
            except Exception as error:
                print_thread('Error -- Failed to Load API Data From settings file. Check settings integrity.')
                print_thread(f'Error: {error}')
        manage_urls(self.ticker_rows)

    def update(self):
        """Update API information in all TickerRow objects.

        Called when the refresh button is pressed.
        """
        print_thread('Requesting all API URLs...')
        for row in self.ticker_rows:
            # update_idletasks() will cause values in rows to update as they come,
            # instead of all at once at the end.
            # self.window.update_idletasks()
            if row.refresh and row.api_object and not row.api_object.minion:
                Thread(target=row.update).start()

    def new_api(self):
        """Create TickerAPIProperties to add a new API to monitor.
        Prevent mulitple windows from being opened at once.

        https://stackoverflow.com/a/59338433
        """
        def on_close():
            self.api_properties.properties_window.destroy()
            self.api_properties = None

        if self.api_properties is None:
            self.api_properties = TickerAPIProperties(self, self.ticker_rows, new=True)
            self.api_properties.properties_window.protocol('WM_DELETE_WINDOW', on_close)

    def preferences(self):
        """Create TickerPreferences.
        Prevent mulitple windows from being opened at once.

        https://stackoverflow.com/a/59338433
        """
        def on_close():
            self.ticker_preferences.preferences_window.destroy()
            self.ticker_preferences = None

        if self.ticker_preferences is None:
            self.ticker_preferences = TickerPreferences(self, self.ticker_rows)
            self.ticker_preferences.preferences_window.protocol('WM_DELETE_WINDOW', on_close)

    def foreground(self):
        """Keeps γTicker in the foreground if settings indicates it.
        """
        if settings.dictionary['global']['foreground']:
            self.window.attributes('-topmost', True)
        else:
            self.window.attributes('-topmost', False)


class TickerRow:
    """An object of a row containing API data to be displayed within γTicker.

    Contains the TickerAPI object.
    """
    def __init__(self, Ticker, TickerAPI, sequence, refresh_in_seconds):
        self.ticker_object = Ticker
        self.api_object = TickerAPI
        self.ticker_rows = self.ticker_object.ticker_rows
        self.window = self.ticker_object.window
        self.frame = self.ticker_object.api_frame
        self.sequence = sequence
        self.refresh = refresh_in_seconds
        self.name = str(self.api_object.name)
        self.labels = []
        self.padx = 0
        self.pady = 0
        self.truncated = False
        self.tooltip_val = None
        self.auto_update = None
        self.api_properties = None
        self.alarm_window = None
        self.delete_window = None

        # Truncate long names.
        if len(self.name) > 24:
            self.name = self.api_object.name[:22].strip()+'...'
            self.truncated = True

        # Name Label
        self.name_label = tk.Label(self.frame, text=self.name, anchor='w')
        self.name_label.grid(row=self.sequence, column=0, padx=self.padx, pady=self.pady, sticky='we')
        self.labels.append(self.name_label)
        if self.truncated:
            Tooltip(self.name_label, self.api_object.name, .2)

        # Value Label
        self.value_label = tk.Label(self.frame, anchor='w')
        self.value_label.grid(row=self.sequence, column=1, padx=self.padx, pady=self.pady, sticky='we')
        self.labels.append(self.value_label)

        # Up/Down/Neutral Arrow Image -- Indicates whether the value has risen/fallen/stayed the same.
        self.arrow_side_img = tk.PhotoImage(dir_path("assets/arrow_side.png"))
        self.arrow_up_img = tk.PhotoImage(dir_path("assets/arrow_up.png"))
        self.arrow_down_img = tk.PhotoImage(dir_path("assets/arrow_down.png"))
        self.arrow = tk.Label(self.frame, anchor='w')
        self.arrow.grid(row=self.sequence, column=2, padx=self.padx, pady=self.pady, sticky='we')
        self.labels.append(self.arrow)

        # Time Label
        self.time_label = tk.Label(self.frame, anchor='w')
        self.time_label.grid(row=self.sequence, column=3, padx=self.padx, pady=self.pady, sticky='we')
        self.labels.append(self.time_label)

        # Right-click Menu
        # Got help from https://www.geeksforgeeks.org/right-click-menu-using-tkinter/
        self.menu = tk.Menu(self.frame, tearoff=0)
        self.menu.add_command(label='Refresh', command=lambda: Thread(target=self.update).start())
        self.menu.add_command(label='Open Log', command=self.open_log)
        self.menu.add_command(label='Alarms', command=self.open_alarms)
        self.menu.add_separator()
        self.menu.add_command(label='Copy', command=self.copy)
        self.menu.add_command(label='Delete', command=self.open_delete)
        self.menu.add_separator()
        self.menu.add_command(label='Properties', command=self.open_properties)

        # Bind the right-click popup menu to all items in the row.
        self.name_label.bind('<Button-3>', self.rclick_menu)
        self.value_label.bind('<Button-3>', self.rclick_menu)
        self.arrow.bind('<Button-3>', self.rclick_menu)
        self.time_label.bind('<Button-3>', self.rclick_menu)

        # Bind properties menu to doubleclicking.
        self.name_label.bind('<Double-Button-1>', self.open_properties)
        self.value_label.bind('<Double-Button-1>', self.open_properties)
        self.arrow.bind('<Double-Button-1>', self.open_properties)
        self.time_label.bind('<Double-Button-1>', self.open_properties)

        self.change_font()

    def rclick_menu(self, event):
        """Bound popup menu to right click which brings up a menu at the position of the mouse cursor.
        """
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def open_log(self):
        """Attempt to open the associated log file in the default text editor.

        Tries for Windows, OSX, Linux.
        """
        # Construct log name and try to read it to test if log exists.
        log_name = self.api_object.name.replace(' ', '_')
        for char in ['\\', '/', ':', '"', '*', '?', '<', '>', '|']:
            log_name = log_name.replace(char, "")
        try:
            open(f'logs/{log_name}.txt', 'r').read()
        except FileNotFoundError:
            print_thread(f'{self.name}: No Log to Open')
        # Log exists:
        else:
            print_thread(f'{self.name}: Opening Log')
            # Try windows:
            try:
                startfile(f'{path.join(getcwd(), "logs", log_name+".txt")}')
            # Try Linux:
            except Exception:
                try:
                    system(f'gedit {path.join(getcwd(), "logs", log_name+".txt")}')
                except Exception:
                    print_thread(f'Error: Failed to open log for {self.name}.')

    def open_alarms(self):
        """Create TickerAlarms window.
        Called through right-click menu.

        Prevent mulitple windows from being opened at once.

        https://stackoverflow.com/a/59338433
        """
        def on_close(event=True):
            self.alarm_window.alarm_window.destroy()
            self.alarm_window = None

        if self.alarm_window is None:
            print_thread(f'{self.name}: Opening Alarms')
            self.alarm_window = TickerAlarm(self)
            self.alarm_window.alarm_window.bind('<Escape>', on_close)
            self.alarm_window.alarm_window.protocol('WM_DELETE_WINDOW', on_close)

    def copy(self):
        """Copy the formatted, untruncated value from a row to the clipboard using pyperclip.copy()

        Called when "Copy" is selected from right-click menu.
        """
        if self.api_object.truncated:
            clipboard = str(self.api_object.value)
        else:
            clipboard = str(self.api_object.value_formatted)
        pyperclip_copy(clipboard)

    def open_delete(self):
        """Open a delete confirmation window.
        Called when delete is selected from right-click menu.

        Prevent mulitple windows from being opened at once.

        https://stackoverflow.com/a/59338433
        """
        def on_close():
            self.delete_window.destroy()
            self.delete_window = None

        if self.delete_window is None:
            self.delete()
            self.delete_window.protocol('WM_DELETE_WINDOW', on_close)

    def open_properties(self, event=True):
        """Create TickerProperties window.
        Called when double-clicking or through right-click menu.

        Prevent mulitple windows from being opened at once.

        https://stackoverflow.com/a/59338433
        """
        def on_close():
            self.api_properties.properties_window.destroy()
            self.api_properties = None

        if self.api_properties is None:
            self.api_properties = TickerAPIProperties(self, self.ticker_rows)
            self.api_properties.properties_window.protocol('WM_DELETE_WINDOW', on_close)

    def update(self):
        """Send request, check alarm triggers, and update value, arrow, and time.

        Auto-updated with a threaded timer if there is a refresh value;
        Individual refresh rates are determined by values in settings.
        """
        # Commence auto-update.
        if self.refresh and not self.api_object.minion:
            self.update_cancel()
            self.auto_update = TimerThread(self.refresh, self.update)
            self.auto_update.start()

        # Send Request, Match Values
        self.api_object.scrape_api()
        self.api_object.match_value()

        # Alarms
        self.alarm_check()

        # Update Labels
        self.update_labels()

    def update_cancel(self):
        """Cancel auto-updating.
        """
        if self.auto_update:
            self.auto_update.cancel()
            self.auto_update = None

    def update_labels(self):
        """Update value, arrow, and time labels.

        Called after a TickerAPI scrape and when a TickerAPI
        is acting as a "master" to other objects with the same URL.
        """
        # Update Value
        self.value_label.configure(text=self.api_object.value_formatted)

        # Display very long values which have been truncated in tooltip dialogue.
        if self.api_object.truncated:
            Tooltip(self.value_label, str(self.api_object.value), .2)
        else:
            self.value_label.unbind('<Enter>')

        # Update up/down arrow
        if self.api_object.change == 'up':
            self.arrow.configure(image=self.arrow_up_img)
        elif self.api_object.change == 'down':
            self.arrow.configure(image=self.arrow_down_img)
        elif self.api_object.change == 'same':
            self.arrow.configure(image=self.arrow_side_img)

        # Update time -- Time is gotten just before api scrape.
        self.time_label.configure(text=self.api_object.time)

    def alarm_check(self):
        """Check if an alarm has been triggered, called in update()

        Create an AlarmNotification window and disable alarm when triggered.
        """
        try:
            alarms = settings.dictionary['apis'][self.sequence]['alarms']
            if alarms and is_float(self.api_object.value):
                for i in range(len(alarms)):
                    if alarms[i]['enabled']:
                        inequality_str = f"{self.api_object.value} {alarms[i]['inequality']+'='} {alarms[i]['value']}"
                        if eval(inequality_str):
                            text = f'{self.name}: {inequality_str}'
                            print_thread(f'ALARM: {text}')
                            print_thread(f'Disabing {self.name} Alarm')
                            # Alarm Notification Window
                            AlarmNotification(self.window, text)
                            # Turn alarm off.
                            settings.dictionary['apis'][self.sequence]['alarms'][i]['enabled'] = False
                            settings.save()
        except Exception as error:
            print_thread(f'Alarm Error: {error}')

    def delete(self):
        """Delete a row within γTicker and remove corresponding entry from settings file.
        Reorder all rows within Ticker.ticker_rows by calling reorder_rows(ticker_rows)

        Ask confirmation from a new window.
        """
        def confirm(event=True):
            """Delete relevant data.

            Called after confirmation button is pressed. Bound to enter key.
            """
            print_thread(f'Delete Confirmed: Deleting {self.name}')
            # Stop auto-updating.
            self.update_cancel()
            # Remove self from tkinter Ticker.canvas
            for item in self.frame.grid_slaves():
                if int(item.grid_info()['row']) == self.sequence:
                    item.grid_forget()
            # Delete api_object and reorder rows to delete self from settings and ticker_rows.
            self.api_object = None
            reorder_rows(self.ticker_rows)
            # If there are other rows with the same URL, begin updating one if it isn't already.
            manage_urls(self.ticker_rows, update=True)
            close()

        def close(event=True):
            """Close window, and, critically, allow more delete windows to be opened in the future.

            Called when cancel or ok are pressed. Bound to escape key.
            """
            self.delete_window.destroy()
            self.delete_window = None

        # Set position of delete_window relative to parent_object.
        x, y = self.window.winfo_rootx(), self.window.winfo_rooty()
        geometry = (f'+{x}+{y}')

        # Child Window
        self.delete_window = tk.Toplevel(self.window)
        self.delete_window.title('Delete?')
        self.delete_window.geometry(geometry)
        # Make window active so bound keys will register.
        self.delete_window.focus_set()

        if settings.dictionary['global']['foreground']:
            self.delete_window.attributes('-topmost', True)

        # Delete Confirmation Label
        self.delete_label = tk.Label(self.delete_window, text=f'Do you really want to delete {self.name}?')
        self.delete_label.grid(row=0, columnspan=2)

        # Delete Button
        self.delete_button = tk.Button(self.delete_window, text='Delete', width=10, command=confirm)
        self.delete_button.grid(row=1, column=0, padx=4, pady=4, sticky='e')
        self.delete_window.bind('<Return>', confirm)

        # Cancel Button
        self.cancel_button = tk.Button(self.delete_window, text='Cancel', width=10, command=close)
        self.cancel_button.grid(row=1, column=1, padx=4, pady=4, sticky='w')
        self.delete_window.bind('<Escape>', close)

        print_thread(f'Delete {self.name}?')

    def change_font(self):
        """Changes font size within row based on global settings:

        Small = 9, Medium = 12, Large = 16

        Called at the end of initialization and from TickerPreferences with Ticker.ticker_rows list.
        """
        size = settings.dictionary['global']['text']
        font = 'TkDefaultFont'
        if size == 'Large':
            row_font = (font, 16)
        elif size == 'Medium':
            row_font = (font, 12)
        else:
            row_font = (font, 9)

        self.name_label.configure(font=row_font)
        self.value_label.configure(font=row_font)
        self.time_label.configure(font=row_font)


class TickerAPIProperties:
    """Create/edit an API's properties for γTicker to monitor.

    Opens a new window for the user to input and select properties.

    Called when the + button is pressed,
    or when rightclicking an API row and selecting "Properties",
    or when doubleclicking on an API row.

    Set new=True when adding a new API.
    """
    def __init__(self, parent_object, ticker_rows, new=False):
        self.parent_object = parent_object
        self.ticker_rows = ticker_rows
        self.new = new
        if not self.new:
            self.api_object = parent_object.api_object
            self.sequence = parent_object.sequence

        # Child Window
        self.properties_window = tk.Toplevel(parent_object.window)
        # Make window active so bound keys will register.
        self.properties_window.focus_set()

        # Set position of properties_window relative to parent_object.
        x, y = parent_object.window.winfo_rootx(), parent_object.window.winfo_rooty()
        self.properties_window.geometry(f'+{x}+{y}')
        if self.new:
            self.properties_window.title('Adding API')
        else:
            self.properties_window.title(f'{self.api_object.name} Properties')
        padx = 4
        pady = 2

        # This will be used to restrict certain entry boxes to receive numbers with validatecommand.
        # https://stackoverflow.com/questions/8959815/restricting-the-value-in-tkinter-entry-widget
        vcmd = (self.properties_window.register(self.validate_digit))

        # Canvas for all entry labels/boxes
        self.entry_canvas = tk.Canvas(self.properties_window, highlightthickness=0)
        self.entry_canvas.grid(row=0, column=0, columnspan=3, sticky='w')

        # Name
        self.name_label = tk.Label(self.entry_canvas, text='Name')
        self.name_label.grid(row=0, column=0, padx=padx, pady=pady, sticky='w')
        self.name_entry = tk.Entry(self.entry_canvas)
        self.name_entry.grid(row=0, column=1, padx=padx, pady=pady, columnspan=2, sticky='w')

        # API URL
        self.url_label = tk.Label(self.entry_canvas, text='API URL')
        self.url_label.grid(row=1, column=0, padx=padx, pady=pady, sticky='w')
        self.url_entry = tk.Entry(self.entry_canvas)
        self.url_entry.grid(row=1, column=1, padx=padx, pady=pady, columnspan=2, sticky='w')

        # Refresh Rate -- With Validation
        self.refresh_label = tk.Label(self.entry_canvas, text='Refresh Rate')
        self.refresh_label.grid(row=2, column=0, padx=padx, pady=pady, sticky='w')
        self.refresh_entry = tk.Entry(self.entry_canvas, validate='key', validatecommand=(vcmd, '%P'))
        self.refresh_entry.grid(row=2, column=1, padx=padx, pady=pady, columnspan=2, sticky='w')
        Tooltip(self.refresh_label, 'In Seconds')

        # Term (the thing which is monitored from API)
        self.term_label = tk.Label(self.entry_canvas, text='Match Term')
        self.term_label.grid(row=3, column=0, padx=padx, pady=pady, sticky='w')
        self.term_entry = tk.Entry(self.entry_canvas)
        self.term_entry.grid(row=3, column=1, padx=padx, pady=pady, columnspan=2, sticky='w')
        Tooltip(self.term_label, 'The Desired Value From the API')

        # Decimal Places (for formatting) -- With Validation
        self.decimals_label = tk.Label(self.entry_canvas, text='Decimal Places')
        self.decimals_label.grid(row=4, column=0, padx=padx, pady=pady, sticky='w')
        self.decimals_entry = tk.Entry(self.entry_canvas, validate='key', validatecommand=(vcmd, '%P'))
        self.decimals_entry.grid(row=4, column=1, padx=padx, pady=pady, columnspan=2, sticky='w')
        Tooltip(self.decimals_label, 'For Formatting Numerical Values')

        # Sequence (order of the row) -- With Validation
        self.sequence_label = tk.Label(self.entry_canvas, text='Order Number')
        self.sequence_label.grid(row=5, column=0, padx=padx, pady=pady, sticky='w')
        self.sequence_entry = tk.Entry(self.entry_canvas, validate='key', validatecommand=(vcmd, '%P'))
        self.sequence_entry.grid(row=5, column=1, padx=padx, pady=pady, columnspan=2, sticky='w')
        Tooltip(self.sequence_label, 'Display Order')

        # Logging
        self.log_var = tk.BooleanVar()
        self.log_check = tk.Checkbutton(self.properties_window, text='Save data to log',
                                        command=self.toggle_log, variable=self.log_var, onvalue=True, offvalue=False)
        self.log_check.grid(row=1, column=0, padx=padx, pady=pady, columnspan=3, sticky='w')

        # OK Button -- Save settings and close window
        self.ok_button = tk.Button(self.properties_window, text='OK', width=8, command=self.save_close)
        self.ok_button.grid(row=3, column=0, padx=padx, pady=pady)
        # Bind to enter key.
        self.properties_window.bind('<Return>', self.save_close)

        # Apply Button -- Save settings
        self.cancel_button = tk.Button(self.properties_window, text='Apply', width=8, command=self.save)
        self.cancel_button.grid(row=3, column=1, padx=padx, pady=pady)

        # Cancel Button -- Close window without saving
        self.cancel_button = tk.Button(self.properties_window, text='Cancel', width=8, command=self.close)
        self.cancel_button.grid(row=3, column=2, padx=padx, pady=pady)
        # Bind to escape key.
        self.properties_window.bind('<Escape>', self.close)

        try:
            self.properties_window.iconbitmap(dir_path("assets/yTicker.ico"))
        except Exception as error:
            print_thread(f'Error -- yTicker.ico not found: {error}')

        self.load_settings()

    def validate_digit(self, entry):
        """Digit validation for tkinter entry boxes.
        """
        if str(entry).isdigit() or entry == "":
            return True
        else:
            return False

    def toggle_log(self):
        """Print state of log_var when log checkbox is clicked.
        """
        if self.new:
            print_thread(f'New API: Log checkbox set to {self.log_var.get()}')
        else:
            print_thread(f'{self.api_object.name}: Log checkbox set to {self.log_var.get()}')

    def save_close(self, event=True):
        """Called when "ok" is pressed. Bound to enter key.

        Call save() and close()
        """
        self.save()
        self.close()

    def close(self, event=True):
        """Close window, and, critically, allow more properties windows to be opened in the future.

        Called when cancel or ok are pressed.
        """
        self.parent_object.api_properties = None
        self.properties_window.destroy()

    def load_settings(self):
        """Load settings from settings file and apply them to entry boxes.
        """
        # Apply global settings.
        if settings.dictionary['global']['foreground']:
            self.properties_window.attributes('-topmost', True)

        # When creating a new API to monitor, set entry boxes to these defaults.
        if self.new:
            print_thread('Adding New API')
            self.sequence_entry.insert(0, len(self.ticker_rows)+1)
        # When altering existing API properties, collect values from settings file and set the entry boxes accordingly.
        else:
            print_thread(f'{self.parent_object.name}: Opening Properties')
            properties = settings.dictionary['apis'][self.sequence]
            self.name_entry.insert(0, str(properties['name']))
            if properties['url'] is not None:
                self.url_entry.insert(0, str(properties['url']))
            self.refresh_entry.insert(0, str(properties['refresh']))
            self.decimals_entry.insert(0, str(properties['decimals']))
            self.sequence_entry.insert(0, str(properties['sequence']+1))
            if properties['term'] is not None:
                self.term_entry.insert(0, str(properties['term']))
            if properties['log']:
                self.log_var.set(True)

    def save(self):
        """Save the entered properties to the settings file.

        Update api_object attributes if editing properties.

        Create a TickerAPI nested in a TickerRow object if a new row is being created.

        Called when "OK" or "Apply" buttons are pressed.
        """
        # Get all entries.
        entries = {}
        entries['name'] = self.name_entry.get()
        entries['url'] = self.url_entry.get()
        entries['refresh'] = self.refresh_entry.get()
        entries['term'] = self.term_entry.get()
        entries['decimals'] = self.decimals_entry.get()
        entries['sequence'] = self.sequence_entry.get()
        entries['log'] = self.log_var.get()

        # Modify Entries
        for key, val in entries.items():
            # If the sequence entry was empty, make sequence the length of ticker_rows.
            if key == 'sequence' and val == "":
                entries[key] = len(self.ticker_rows)
            # If the entry box was empty, make the value None.
            elif val == "":
                entries[key] = None
            # Typecasting and character/digit limitations.
            elif key == 'name' and val is not None and len(val) > 80:
                entries[key] = entries[key][:80]
            elif key == 'url' and val is not None and len(val) > 2048:
                entries[key] = entries[key][:2048]
            elif key == 'term' and val is not None and len(val) > 30:
                entries[key] = entries[key][:30]
            elif key == 'refresh' and val == '0':
                entries[key] = None
            elif key == 'refresh' and val is not None and len(val) > 7:
                entries[key] = int(val[:7])
            elif key == 'decimals' and val is not None and len(val) > 2:
                entries[key] = int(val[:2])
            elif key in ['refresh', 'decimals'] and val is not None:
                entries[key] = int(val)
            elif key == 'sequence' and val is not None and int(val) > 0 and int(val) < 1000:
                entries[key] = int(val)-1
            elif key == 'sequence' and val is not None and len(val) > 3 or key == 'sequence' and val is None:
                entries[key] = len(self.ticker_rows)
            elif key == 'sequence' and val == '0':
                entries[key] = int(val)

        if self.new:
            # Create new api entry in settings file.
            entries['alarms'] = []
            settings.dictionary['apis'].append({})
            for key in entries.keys():
                settings.dictionary['apis'][-1][key] = entries[key]
            # Create new TickerAPI object
            new_api_object = TickerAPI(entries['name'], entries['url'], entries['term'],
                                       entries['decimals'], entries['log'])
            # Create new TickerRow object and append it to ticker_rows
            new_row_object = TickerRow(self.parent_object, new_api_object, entries['sequence'], entries['refresh'])
            self.ticker_rows.append(new_row_object)
            # Determine if a URL is shared between rows.
            manage_urls(self.ticker_rows)
            # Commence auto-updating if there is a refresh rate and its not a minion.
            if new_row_object.refresh and not new_row_object.api_object.minion:
                new_row_object.update()

        # When altering existing properties:
        else:
            # Modify settings file.
            for key in entries.keys():
                settings.dictionary['apis'][self.sequence][key] = entries[key]

            # Modify the TickerAPI object.
            self.api_object.name = str(entries['name'])
            self.api_object.url = entries['url']
            self.api_object.term = entries['term']
            self.api_object.decimals = entries['decimals']
            self.api_object.log = entries['log']

            # Modify the TickerRow object.
            # Truncate long names
            if len(str(entries['name'])) > 24:
                entries['name'] = entries['name'][:22].strip()+'...'
                Tooltip(self.parent_object.name_label, self.api_object.name, .2)
            else:
                self.parent_object.name_label.unbind('<Enter>')
            self.parent_object.name_label.configure(text=str(entries['name']))
            self.parent_object.sequence = entries['sequence']

            # If the refresh rate has changed, call TickerRow.update() at the end.
            old_refresh = self.parent_object.refresh
            if is_float(entries['refresh']):
                self.parent_object.refresh = entries['refresh']
            # Cancel auto-updating if refresh was changed to 0 or left blank.
            else:
                self.parent_object.refresh = None
                self.parent_object.update_cancel()
                # If there is another object with the same URL and it has a refresh rate, start updating it.
                manage_urls(self.ticker_rows, update=True)
            # Sort master and minons for objects that share a URL.
            manage_urls(self.ticker_rows)
            # print(self.parent_object.api_object.minion)
            # If refresh has changed, update object if it is not a URL minion.
            if (old_refresh != self.parent_object.refresh and self.parent_object.refresh is not None
                    and not self.parent_object.api_object.minion):
                Thread(target=self.parent_object.update).start()
            # If it is a minion, check if another object has the same URL and start updating it.
            elif self.parent_object.api_object.minion:
                manage_urls(self.ticker_rows, update=True)
            # Else try to match a new value and update labels.
            else:
                self.parent_object.api_object.match_value()
                self.parent_object.update_labels()

        # settings.save() is not needed as it will occur at the end of reorder_rows()
        reorder_rows(self.ticker_rows)
