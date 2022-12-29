# γTicker functions used in classes.py, classes_others.py, and alarms.py
# TimerThread, print_thread, is_float, dict_search, get_time, reorder_rows, manage_urls

from time import localtime, time, sleep
from threading import Thread, Event
from settings import settings

class TimerThread(Thread):
    """Threaded timer very similar to threading.Timer

    The difference is how it waits before calling the given function in an effort to prevent
    it from getting out of sync. Whole seconds only.

    Call a function after a specified number of seconds:

        t = TimerThread(60, function)     # Call function after 60 seconds.
        t.start()                         # Start timer.
        t.cancel()                        # Cancel the timer's action if it's still waiting.
    """
    def __init__(self, seconds, function, args=None, kwargs=None):
        Thread.__init__(self)
        self.seconds = int(seconds)
        self.function = function
        self.args = args if args is not None else []
        self.kwargs = kwargs if kwargs is not None else {}
        self.finished = Event()

    def run(self):
        self.wait()
        if not self.finished.is_set():
            self.function(*self.args, **self.kwargs)
        self.finished.set()

    def cancel(self):
        """Stop the timer if it hasn't finished yet.
        """
        self.finished.set()

    def wait(self):
        """Will sleep up until the final two seconds before the function is called.

        In the final two seconds, sleep in 0.4 second intervals until the expected time is reached.
        """
        wake_up = int(time() + self.seconds)
        while wake_up > int(time()):
            if wake_up == int(time() + self.seconds) and (self.seconds-2) > 0:
                sleep(self.seconds-2)
            else:
                sleep(.4)


def print_thread(string):
    """Force strings to be printed on separate lines when multithreading.

    https://stackoverflow.com/a/33071625
    """
    print(str(string)+"\n", end="")


def is_float(inputs):
    """Test whether a given value can be a float.

    return True/False
    """
    inputs = str(inputs)
    try:
        float(inputs)
    except ValueError:
        return False
    else:
        return True


def dict_search(dictionary, desired_key, return_list=False, exact_match=False, recursion=True):
    """Recursively search a nested dictionary for a key and return the first instance of its value.
    If lists occur in nested dictionaries, each item will be recusively called.

    return_list=True will yield the full list of matched values;
    exact_match=True will test desired_key against keys precisely;
    exact_match=False will detect a partial match, e.g. "price" in "prices"
    """
    dict_search.desired_value = []

    def nested_dict_search(dictionary, desired_key):
        if isinstance(dictionary, dict):
            for key, val in dictionary.items():
                if exact_match:
                    if desired_key == key:
                        dict_search.desired_value.append(val)
                else:
                    if desired_key in key:
                        dict_search.desired_value.append(val)
                if isinstance(val, dict):
                    nested_dict_search(val, desired_key)
                elif isinstance(val, list):
                    for item in val:
                        nested_dict_search(item, desired_key)
        elif isinstance(dictionary, list):
            for item in dictionary:
                nested_dict_search(item, desired_key)

    if recursion:
        nested_dict_search(dictionary, desired_key)
    else:
        return dictionary.get(desired_key)

    if dict_search.desired_value:
        if return_list:
            return dict_search.desired_value
        else:
            return dict_search.desired_value[0]
    else:
        return None


def get_time(seconds=True, time=True, date=False):
    """Return the current time as a string in format '14:01:12'

    Uses time.localtime

    seconds=False -> '14:01'
    date=True -> '12-02-2020'
    date=True, time=True -> '12-02-2020 14:01:12'
    """
    current_time = ''
    # time.localtime() values must be formatted to have leading zeros
    current_time += str(localtime().tm_hour).zfill(2)
    current_time += f':{str(localtime().tm_min).zfill(2)}'
    if seconds:
        current_time += f':{str(localtime().tm_sec).zfill(2)}'
    if date:
        current_date = ''
        current_date += str(localtime().tm_mon).zfill(2)
        current_date += f'-{str(localtime().tm_mday).zfill(2)}'
        current_date += f'-{str(localtime().tm_year)}'
    if date and time:
        return f'{current_date} {current_time}'
    elif date:
        return current_date
    return current_time


def reorder_rows(ticker_rows):
    """Fix order of TickerRow objects within ticker_rows list and settings and update label.grid rows.

    Should be called when a TickerRow object is created, deleted, or is reassigned to a new row.
    """
    # Remove rows that have None for api_object. (Flag for TickerRow deletion)
    for i in range(len(ticker_rows)):
        if ticker_rows[i].api_object is None:
            ticker_rows.pop(i)
            settings.dictionary['apis'].pop(i)
            # After a row is deleted, change the sequence in following rows.
            for row in ticker_rows[i:]:
                row.sequence = i
                settings.dictionary['apis'][i]['sequence'] = i
                i += 1
            break

    # If a TickerRow's sequence is out of order within ticker_rows, change its position within settings and ticker_rows.
    sequence = 0
    for row in ticker_rows:
        if row.sequence != sequence:
            # Change position in settings.
            api_dict = settings.dictionary['apis'][sequence]
            settings.dictionary['apis'].remove(api_dict)
            settings.dictionary['apis'].insert(row.sequence, api_dict)
            # Change position in ticker_rows
            ticker_obj = row
            ticker_rows.remove(row)
            ticker_rows.insert(row.sequence, ticker_obj)
            break
        sequence += 1

    # Update sequence number in each row and in settings.
    sequence = 0
    for row in ticker_rows:
        row.sequence = sequence
        settings.dictionary['apis'][sequence]['sequence'] = sequence
        sequence += 1

    # Update row number to new sequence in all labels.
    for i in range(len(ticker_rows)):
        for label in ticker_rows[i].labels:
            label.grid(row=i)

    settings.save()


def manage_urls(ticker_rows, update=False):
    """Determine whether there are TickerAPI objects with the same URL to prevent unnecessary requests.

    Give the TickerAPI object with the lowest associated refresh rate a master_list with all other
    TickerRow objects with the same URL. The object with this list will feed the api_dict
    to the other objects and update their time and value labels.

    Called after ticker_rows are created during initialization in Ticker.create_rows(),
    when TickerAPIProperties.save() is called, or after a TickerRow is deleted.
    """
    # For sorting by refresh rate.
    def refresh(row):
        return row['refresh']

    # Create a dictionary with {url: [{'row': TickerRow, 'refresh': TickerRow.refresh}]}
    url_dict = {}
    for row in ticker_rows:
        # Reset all minions to False in the event that a master was deleted.
        row.api_object.minion = False
        url_dict[row.api_object.url] = []
    for row in ticker_rows:
        # Force None refreshes to be last for sorting.
        if row.refresh is None:
            url_dict[row.api_object.url].append({'row': row, 'refresh': 99999999})
        else:
            url_dict[row.api_object.url].append({'row': row, 'refresh': row.refresh})

    # Sort by refresh rate and for cases where there are shared URLs give the first one the master_list.
    # master_list: a list of all other TickerRow objects with the same url.
    for val in url_dict.values():
        val.sort(key=refresh)
        if len(val) > 1 and not val[0]['row'].api_object.master_list:
            master_list = []
            # Turn slower items into minions which can't be auto-updated and append them to list.
            for item in val[1:]:
                item['row'].update_cancel()
                item['row'].api_object.minion = True
                item['row'].api_object.master_list = []
                master_list.append(item['row'])
            # Give the TickerAPI with the lowest refresh the master_list.
            val[0]['row'].api_object.master_list = master_list
            val[0]['row'].api_object.minion = False
            # Start updating if update argument is true and it isn't already auto-updating.
            if update:
                if val[0]['row'].auto_update is None and val[0]['row'].refresh is not None:
                    Thread(target=val[0]['row'].update).start()
        # For cases where there were previously shared URLs but not anymore due to row deletions.
        elif len(val) == 1:
            val[0]['row'].api_object.master_list = []
            val[0]['row'].api_object.minion = False
