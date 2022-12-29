# γTicker Settings object used in classes.py, classes_other.py, alarms.py, and functions.py

from json import loads, dumps
from util import dir_path



class Settings:
    """Create/edit/manage the settings dictionary containing global settings and API data,
    saved/retrieved to/from settings file within directory.
    """
    def __init__(self):
        self.dictionary = {'global': {'text': 'Medium', 'foreground': False, 'geometry': '285x310'}, 'apis': []}
        self.get()

    def get(self):
        """Attempt to retrieve settings dictionary from settings file and
        convert it to a python dictionary with json.loads()

        Stored as Settings.settings
        """
        try:
            dictionary = open(dir_path('settings'), 'r').read()
            self.dictionary = loads(dictionary)
        except Exception:
            print_thread('No settings file found. Saving new one.')
            self.save()

    def save(self):
        """Attempt to write Settings.settings to settings file using json.dumps()
        """
        try:
            with open(dir_path('settings'), 'w') as stream:
                stream.write(dumps(self.dictionary))
        except Exception as error:
            print_thread(f'Settings not saved: {error}')
        else:
            print_thread('Settings saved successfully.')


def print_thread(string):
    """Force strings to be printed on separate lines when multithreading.

    https://stackoverflow.com/a/33071625
    """
    print(str(string)+"\n", end="")


settings = Settings()
