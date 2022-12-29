# γTicker other classes for classes.py
# TickerAPI, TickerPreferences, Tooltip

import tkinter as tk
from tkinter import ttk
from requests import get as requests_get
from json import loads
from os import path, mkdir
from settings import settings
from functions import is_float, dict_search, get_time, print_thread


class TickerAPI:
    """Object to fetch, store, and log values from APIs.
    """
    def __init__(self, name, url, term, decimals, log):
        self.name = name
        self.url = url
        self.term = term
        self.decimals = decimals
        self.log = log
        self.log_name = None
        self.value = None
        self.value_old = None
        self.value_formatted = None
        self.change = None
        self.time = None
        self.date_time = None
        self.truncated = False
        self.api_dict = {}
        self.master_list = []
        self.minion = False

    def get_times(self):
        """Get the time and date+time. Called immediately before an API scrape.
        """
        self.time, self.date_time = get_time(), get_time(date=True)

    def scrape_api(self):
        """Retrieve and store a dictionary from an API URL.

        Scraped with requests library.
        String converted to dictionary with json.loads
        """
        self.get_times()
        print_thread(f'{self.name}: Requesting at {self.time}')
        try:
            request_results = requests_get(self.url)
        except Exception:
            self.value = self.value_formatted = 'Invalid URL'
            print_thread(f'{self.name}: Invalid URL')
        else:
            try:
                self.api_dict = loads(request_results.text)
            except Exception:
                self.value = self.value_formatted = 'Invalid API'
                print_thread(f'{self.name}: Invalid API')

    def match_value(self):
        """Retrieve and store a desired value from an API dictionary.

        Attempt to match a value with a given term, otherwise
        the value will be the entire json object.

        Format and log value.
        Determine if numeric value has changed for self.change (arrow).
        """
        # Reset truncation in the event that a long, truncated value is replaced by a short one
        # so that there will be no tooltip dialogue.
        self.truncated = False

        # Get the old value before new value is retrieved to determine if it has risen/fallen.
        if self.value is not None:
            self.value_old = self.value
        self.value = None

        # Attempt to match the value with the given term.
        if self.term is not None:
            try:
                self.value = dict_search(self.api_dict, self.term, recursion=False)
                if self.value is None:
                    self.value = dict_search(self.api_dict, self.term)
            except Exception as error:
                print_thread(f'Error -- Recursive API Value Matching Failed: {error}')
                self.value = None
        # If there isn't a given term, assign json dictionary to value.
        elif self.term is None and self.api_dict:
            self.value = self.api_dict

        if self.value is not None:
            if is_float(self.value):
                self.value = float(self.value)
                # Format value. Keep original and formatted value separate for precise alarm matching/inequalities.
                if self.decimals is not None:
                    try:
                        self.value_formatted = format(self.value, f'.{self.decimals}f')
                        if len(str(self.value_formatted)) > 32:
                            self.value_formatted = str(self.value_formatted)[:29].strip()+'...'
                            self.truncated = True
                    except Exception as error:
                        print_thread(f'Error -- Value Formatting Failed: {error}')
                        self.value_formatted = str(self.value)
                else:
                    self.value_formatted = str(self.value)
                print_thread(f'{self.name}: {self.value_formatted}')
                # Determine if value has risen/fallen/stayed the same.
                if is_float(self.value_old):
                    try:
                        if self.value > self.value_old:
                            self.change = 'up'
                        elif self.value < self.value_old:
                            self.change = 'down'
                        else:
                            self.change = 'same'
                    except Exception as error:
                        print_thread(f'Error -- Change Arrow Not Determinable: {error}')
            # If the value isn't floatable, format it as a string.
            else:
                self.value_formatted = str(self.value)
                # Truncate long values.
                if len(str(self.value)) > 32:
                    self.value_formatted = str(self.value)[:29].strip()+'...'
                    self.truncated = True
                print_thread(f'{self.name}: {self.value_formatted}')
            # Log data
            if self.log:
                self.logger(self.value)

        # Pass api_dict to other items in master list if there is one.
        if self.master_list:
            self.distribute_api()

    def distribute_api(self):
        """Called when there is a master_list.

        Distribute scraped api_dict to other objects with the same URL.
        Match value, check alarms, and update TickerRow labels.
        """
        for row in self.master_list:
            row.api_object.api_dict = self.api_dict
            row.api_object.time = self.time
            row.api_object.date_time = self.date_time
            row.api_object.match_value()
            row.alarm_check()
            row.update_labels()

    def logger(self, value):
        """Log data as it is retrieved to the log directory.

        Individual values are logged separately from one another and can be separated by days.

        Values are appended to files.
        """
        try:
            if not path.exists('logs'):
                mkdir('logs')
        except Exception as error:
            print_thread(f'{self.name}: log directory could not be created -- {error}')
        finally:
            try:
                # Filename: Replace spaces with underscores and remove problem characters.
                log_name = self.name.replace(' ', '_')
                for char in ['\\', '/', ':', '"', '*', '?', '<', '>', '|']:
                    log_name = log_name.replace(char, "")
                self.log_name = log_name
                # with open(f'logs\\{name}_{date}.txt', 'a') as stream:
                #     stream.write(f'[{time}]\n{value}\n\n')
                with open(f'logs/{log_name}.txt', 'a') as stream:
                    stream.write(f'[{self.date_time}]\n{value}\n\n')
            except Exception as error:
                print_thread(f'{self.name}: Logging Failed -- {error}')
            else:
                print_thread(f'{self.name}: Logging to logs\\{log_name}.txt')


class TickerPreferences:
    """Global prefrences menu for γTicker.

    Display and edit the values for the "global" key in the settings dictionary.

    Called when cog button is pressed.
    """
    def __init__(self, parent_object, ticker_rows):
        self.parent_object = parent_object
        self.window = parent_object.window
        self.ticker_rows = ticker_rows
        self.text_sizes = ['Small', 'Medium', 'Large']

        # Geometry and Padding
        padx = 4
        pady = 2
        x, y = self.window.winfo_rootx(), self.window.winfo_rooty()
        geometry = (f'+{x}+{y}')

        # Child Window
        self.preferences_window = tk.Toplevel(self.window)
        self.preferences_window.geometry(geometry)
        self.preferences_window.title('γTicker Preferences')
        # Make window active so bound keys will register.
        self.preferences_window.focus_set()

        # Canvas for all entry labels/boxes
        self.entry_canvas = tk.Canvas(self.preferences_window, highlightthickness=0)
        self.entry_canvas.grid(row=0, column=0, columnspan=3, sticky='w')

        # Text Size
        self.text_label = tk.Label(self.entry_canvas, text='Text Size')
        self.text_label.grid(row=0, column=0, padx=padx, pady=pady, sticky='w')
        # Used to prevent any text from being entered into text_drop combobox
        vcmd = (self.preferences_window.register(self.no_input))
        self.text_drop = ttk.Combobox(self.entry_canvas, values=self.text_sizes, validate='key', validatecommand=vcmd)
        self.text_drop.grid(row=0, column=1, padx=padx, pady=pady, sticky='w')

        # Foreground
        self.fore_var = tk.BooleanVar()
        self.foreground_check = tk.Checkbutton(self.preferences_window, text='Keep γTicker in the foreground',
                                               command=self.toggle_fore, variable=self.fore_var)
        self.foreground_check.grid(row=1, column=0, padx=padx, pady=pady, columnspan=2, sticky='w')

        # OK Button -- Save settings and close window
        self.ok_button = tk.Button(self.preferences_window, text='OK', width=8, command=self.save_close)
        self.ok_button.grid(row=3, column=0, padx=padx, pady=pady, sticky='e')
        # Bind to enter key.
        self.preferences_window.bind('<Return>', self.save_close)

        # Cancel Button -- Close window without saving
        self.cancel_button = tk.Button(self.preferences_window, text='Cancel', width=8, command=self.close)
        self.cancel_button.grid(row=3, column=1, padx=padx, pady=pady, sticky='w')
        # Bind to escape key.
        self.preferences_window.bind('<Escape>', self.close)

        try:
            self.preferences_window.iconbitmap('yTicker.ico')
        except Exception as error:
            print_thread(f'Error -- yTicker.ico not found: {error}')

        self.load_settings()

    # The reason why I'm doing this: I don't like the way tk.Buttonmenu looks,
    # so I'm creating its nearly funcional equivalent out of tk.Combobox.
    def no_input(self):
        """Prevent any input into a tktinter entry or combobox.
        """
        return False

    def toggle_fore(self):
        """Print state of fore_var when foreground_check is pressed.
        """
        print_thread(f'Preferences: Foreground checkbox set to {self.fore_var.get()}')

    def save_close(self, event=True):
        """Called when "ok" is pressed. Bound to enter key.

        Call save() and close()
        """
        self.save()
        self.close()

    def close(self, event=True):
        """Close window, and, critically, allow more preferences windows to be opened in the future.

        Called when cancel or ok are pressed. Bound to escape key.
        """
        self.parent_object.ticker_preferences = None
        self.preferences_window.destroy()

    def load_settings(self):
        """Load values from the settings file and apply them to entries/boxes in the window.

        Called at the end of initialization.
        """
        print_thread('Opening Global γTicker Preferences')
        try:
            self.text_drop.current(self.text_sizes.index(settings.dictionary['global']['text']))
            if settings.dictionary['global']['foreground']:
                self.preferences_window.attributes('-topmost', True)
                self.fore_var.set(True)
        except Exception as error:
            print_thread(f'Error -- Failed to Load Global Preferences: {error}')

    def save(self):
        """Save changes made to yTicker preferences to settings file and apply where relevant.

        Save current window geometry.
        """
        entries = {}
        entries['text'] = self.text_drop.get()
        entries['foreground'] = self.fore_var.get()

        # Modify settings file.
        for key in entries.keys():
            settings.dictionary['global'][key] = entries[key]
        settings.save()

        # Call Ticker.foreground() in the event foreground option was toggled.
        self.parent_object.foreground()

        # Change text size in each row.
        for row in self.ticker_rows:
            row.change_font()


class Tooltip:
    """For displaying hover text within Ticker tkinter window.

    https://stackoverflow.com/a/56749167
    """
    def __init__(self, tk_object, text, delay=0.5, display=True):
        self.tk_object = tk_object
        self.text = text
        self.tooltip_window = None
        self.text
        self.delay = int(delay*1000)
        self.after_id = None

        self.tooltip()

    def tooltip(self):
        """The bound events tied to hovering over/leaving a tkinter object/label.

        Called at the end of Tooltip object initialization.
        """
        def enter(event):
            # Convert text to a list to insert newlines every 50 characters.
            text = list(self.text)
            new_lines = int(len(text)/50)
            if int(len(text) % 50):
                new_lines += 1
            while new_lines:
                text.insert(50*(new_lines), '\n')
                new_lines -= 1
            text = ''.join(text).strip()

            # The delay is applied with tk.after.
            # ID must be stored so it can be canceled when mouse leaves the tk_object.
            self.after_id = self.tk_object.after(self.delay, lambda: self.show_tooltip(text))

        def leave(event):
            self.hide_tooltip()

        self.tk_object.bind('<Enter>', enter)
        self.tk_object.bind('<Leave>', leave)

    def show_tooltip(self, text):
        """Display text in tooltip window.
        """
        self.tooltip_window = tk.Toplevel(self.tk_object)

        if settings.dictionary['global']['foreground']:
            self.tooltip_window.attributes('-topmost', True)

        # This will turn a traditional window into one without a border or minimize, maximize, and close buttons.
        self.tooltip_window.wm_overrideredirect(1)

        # Geometery: Will put tooltip 16 pixels to the right and 16 pixels below mouse pointer,
        # i.e. to the bottom right of a standard mouse cursor.
        x, y = self.tk_object.winfo_pointerx() + 16, self.tk_object.winfo_pointery() + 16
        self.tooltip_window.geometry(f'+{x}+{y}')
        self.tooltip_label = tk.Label(self.tooltip_window, text=text, relief='solid', borderwidth=1, justify='left')
        self.tooltip_label.grid()

        # To solve a bug, tootlip will destroy itself after 6 seconds.
        # Bug: when text is displaying from tooltip at the moment of a value refreshing,
        # the tooltip window will persist, hovering forever, until the main γTicker is closed.
        self.tooltip_window.after(6000, self.tooltip_window.destroy)

    def hide_tooltip(self):
        """Close tooltip window. Cancel delayed display of tooltip.

        Bound to the mouse leaving the tkinter object.
        """
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None
        if self.after_id:
            self.tk_object.after_cancel(self.after_id)
            self.after_id = None
