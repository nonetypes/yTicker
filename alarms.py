# γTicker alarm objects for classes.py
# TickerAlarm, AlarmRow, AlarmNotification

import tkinter as tk
from tkinter import ttk
from functions import is_float, print_thread
from settings import settings


class TickerAlarm:
    """Alarm window for γTicker.

    Load, add, enable/disable, display alarms for a TickerRow object.
    """
    def __init__(self, TickerRow):
        self.ticker_row = TickerRow
        self.alarm_properties = None
        self.alarm_rows = []
        self.padx = 4
        self.pady = 4

        # Set position of alarm_window relative to ticker_row window.
        x, y = self.ticker_row.window.winfo_rootx(), self.ticker_row.window.winfo_rooty()
        geometry = (f'+{x}+{y}')

        # Child Window
        self.alarm_window = tk.Toplevel(self.ticker_row.window)
        self.alarm_window.title(f'{self.ticker_row.name} Alarms')
        if settings.dictionary['global']['foreground']:
            self.alarm_window.attributes('-topmost', True)
        self.alarm_window.geometry(geometry)
        # Make window active so bound keys will register.
        self.alarm_window.focus_set()

        # Add Alarm Canvas
        self.add_canvas = tk.Canvas(self.alarm_window, borderwidth=0, highlightthickness=0,)
        self.add_canvas.grid(row=0, column=0, padx=self.padx, pady=self.pady, sticky='nw')

        # Add Alarm Button
        self.add_button = tk.Button(self.add_canvas, text='+', command=self.new_alarm)
        self.add_button.grid(row=0, column=0, padx=self.padx, pady=self.pady, sticky='w')

        # Used to prevent any text from being entered into inequality_drop combobox.
        # https://stackoverflow.com/questions/8959815/restricting-the-value-in-tkinter-entry-widget
        vcmd_none = (self.alarm_window.register(self.no_input))

        # Entry Boxes
        # Inequality
        self.inequality_drop = ttk.Combobox(self.add_canvas, values=['>', '<'],
                                            validate='key', validatecommand=vcmd_none, width=4)
        self.inequality_drop.grid(row=0, column=1, padx=self.padx, pady=self.pady, sticky='w')
        self.inequality_drop.current(0)
        # Value
        self.value_entry = tk.Entry(self.add_canvas, width=12)
        self.value_entry.grid(row=0, column=2, padx=self.padx, pady=self.pady, sticky='w')

        # Alarms Frame
        self.alarm_frame = tk.Frame(self.alarm_window)
        self.alarm_frame.grid(row=1, column=0, padx=self.padx, pady=self.pady, sticky='we')

        try:
            self.alarm_window.iconbitmap('yTicker.ico')
        except Exception as error:
            print_thread(f'Error -- yTicker.ico not found: {error}')

        self.create_alarms()

    def create_alarms(self):
        """Load all alarms for a TickerRow API by creating AlarmRow objects.
        """
        alarms = settings.dictionary['apis'][self.ticker_row.sequence]['alarms']
        row = 0
        for alarm in alarms:
            self.alarm_rows.append(AlarmRow(self, self.alarm_frame, row, alarm['enabled'],
                                            alarm['inequality'], alarm['value']))
            row += 1

    def new_alarm(self):
        """Create a new alarm for yTicker

        Creates an AlarmRow for TickerAlarm and adds entry to settings file.
        """
        entries = {}
        entries['enabled'] = True
        entries['inequality'] = self.inequality_drop.get()
        entries['value'] = self.value_entry.get()

        if len(str(entries['value'])) > 20:
            entries['value'] = str(entries['value'])[:20]
        if is_float(entries['value']):
            if float(entries['value']) >= 0:
                entries['value'] = float(entries['value'])
                # Don't create duplicate alarms.
                if entries not in settings.dictionary['apis'][self.ticker_row.sequence]['alarms']:
                    self.alarm_rows.append(AlarmRow(self, self.alarm_frame, len(self.alarm_rows),
                                                    entries['enabled'], entries['inequality'], entries['value']))
                    settings.dictionary['apis'][self.ticker_row.sequence]['alarms'].append(entries)
                    settings.save()

    def no_input(self):
        """Prevent any input into a tkinter entry or combobox.
        """
        return False


class AlarmRow:
    """An object to contain tkinter objects in a single row within TickerAlarm.
    """
    def __init__(self, TickerAlarm, tk_frame, row, enabled, inequality, value):
        self.ticker_alarm = TickerAlarm
        self.ticker_sequence = self.ticker_alarm.ticker_row.sequence
        self.row = row
        self.frame = tk_frame
        self.enabled = enabled
        self.inequality = inequality
        self.value = value
        # Used to change grid rows when an item is deleted.
        self.tk_objects = []

        self.padx = 4
        self.pady = 4

        # Enabled Checkbox -- to indicate whether the alarm is enabled/disabled
        self.enabled_var = tk.BooleanVar()
        self.enabled_check = tk.Checkbutton(self.frame, command=self.toggle_enabled,
                                            variable=self.enabled_var, onvalue=True, offvalue=False)
        self.enabled_check.grid(row=row, column=0, padx=self.padx, pady=self.pady, sticky='w')
        self.tk_objects.append(self.enabled_check)

        # Inequality Label -- > or <
        self.inequality_label = tk.Label(self.frame, text=inequality)
        self.inequality_label.grid(row=row, column=1, padx=self.padx, pady=self.pady, sticky='w')
        self.tk_objects.append(self.inequality_label)

        # Value Label
        self.value_label = tk.Label(self.frame, text=value)
        self.value_label.grid(row=row, column=2, padx=self.padx, pady=self.pady, sticky='w')
        self.tk_objects.append(self.value_label)

        # Delete Button
        self.delete_button = tk.Button(self.frame, text='x', command=self.delete)
        self.delete_button.grid(row=row, column=3, padx=self.padx, pady=self.pady, sticky='e')
        self.tk_objects.append(self.delete_button)

        if self.enabled:
            self.enabled_var.set(True)

    def toggle_enabled(self):
        """Print state of enabled_var when enabled checkbox is clicked.

        Save change to settings.
        """
        enabled_state = self.enabled_var.get()
        print_thread(f'Alarm checkbox set to {enabled_state}')
        settings.dictionary['apis'][self.ticker_sequence]['alarms'][self.row]['enabled'] = enabled_state
        settings.save()

    def delete(self):
        """Delete an alarm. Adjust all AlarmRows. Save settings.
        """
        # Remove from tkinter frame.
        for item in self.frame.grid_slaves():
            if int(item.grid_info()['row']) == self.row:
                item.grid_forget()

        self.ticker_alarm.alarm_rows.pop(self.row)

        # Adjust all rows.
        for i in range(len(self.ticker_alarm.alarm_rows)):
            self.ticker_alarm.alarm_rows[i].row = i
            for obj in self.ticker_alarm.alarm_rows[i].tk_objects:
                obj.grid(row=i)

        settings.dictionary['apis'][self.ticker_sequence]['alarms'].pop(self.row)
        settings.save()


class AlarmNotification:
    """A tkinter window to be displayed when an alarm is triggered.
    """
    def __init__(self, parent_window, text):
        self.parent_window = parent_window
        self.text = text
        self.text = f'An alarm has been triggered and disabled.\n{self.text}'

        # Set position of alarm_window relative to ticker_row window.
        x, y = self.parent_window.winfo_rootx(), self.parent_window.winfo_rooty()
        geometry = (f'+{x}+{y}')
        padx = 4
        pady = 4

        # Child Window
        self.alarm_window = tk.Toplevel(self.parent_window)
        self.alarm_window.title('Alarm')
        if settings.dictionary['global']['foreground']:
            self.alarm_window.attributes('-topmost', True)
        self.alarm_window.geometry(geometry)

        # Notification Label
        self.text_label = tk.Label(self.alarm_window, text=self.text)
        self.text_label.grid(row=0, column=0, padx=padx, pady=pady, sticky='w')

        # OK Button -- Close window
        self.ok_button = tk.Button(self.alarm_window, text='OK', width=8,
                                   command=lambda: self.alarm_window.destroy())
        self.ok_button.grid(row=1, column=0, padx=padx, pady=pady)

        try:
            self.alarm_window.iconbitmap('yTicker.ico')
        except Exception as error:
            print_thread(f'Error -- yTicker.ico not found: {error}')
