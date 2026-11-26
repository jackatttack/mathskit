"""The statistics datasets the Charts page draws from: Pokémon and countries.

Role: gather · Part of: mathskit/charts

Pure Python, except that on Pythonista it asks iOS (objc_util) for the
iCloud folder; elsewhere it looks in Documents/library only.

    from mathskit import datasets
    pokemon = datasets.load('pokemon')       # a Source, or raises MissingData
    pokemon.rows[0]['name']                  # 'Bulbasaur'

The tidy CSVs are built by tools/build_datasets.py into library/datasets/.
They are personal teaching data, so they never ship inside the mathskit
release. Every device finds them in Pythonista's iCloud Drive folder,
library/datasets (the shared data folder: copy a dataset there once and
every device sees it). load() looks in this device's Documents/library
first, then in iCloud; the iCloud folder is asked of iOS, never written
in. When iCloud has only a placeholder for a file (not yet on this
device), load() asks iCloud to download it and waits a moment.

Numbers come back as int or float, blanks as None.
"""
import csv
import os
import time

# ---- Settings (editable) -----------------------------------------------------

# The folder inside each library the tidy files sit in.
DATA_FOLDER = ('library', 'datasets')
# How long load() waits for iCloud to download a file it has only a placeholder for.
ICLOUD_WAIT_SECONDS = 4

FILES = {'pokemon': 'pokemon.csv', 'countries': 'countries.csv'}
TITLES = {'pokemon': 'Pokémon', 'countries': 'Countries'}

# Columns kept as text; every other column is read as a number.
TEXT_COLUMNS = {'name', 'type1', 'type2', 'colour', 'legendary', 'code', 'continent', 'subregion',
                'population_year'}

# ---- Loading -----------------------------------------------------------------


class MissingData(RuntimeError):
    """No copy of a dataset was found in any of FOLDERS."""


class Source:
    """One dataset: its key ('pokemon'), title, rows (list of dicts) and the
    file it came from."""

    def __init__(self, key, rows, path=''):
        self.key = key
        self.title = TITLES.get(key, key)
        self.rows = rows
        self.path = path


_loaded = {}
_icloud_cache = []     # the iCloud Documents folder, once asked ('' when there is none)


def icloud_documents():
    """Pythonista's iCloud Drive Documents folder, asked of iOS (objc_util),
    or '' where there is none (PythonIDE, Juno, a desktop)."""
    if not _icloud_cache:
        found = ''
        try:
            from objc_util import ObjCClass
            container = ObjCClass('NSFileManager').defaultManager().URLForUbiquityContainerIdentifier_(None)
            if container is not None:
                found = os.path.join(str(container.path()), 'Documents')
        except Exception:
            found = ''
        _icloud_cache.append(found if found and os.path.isdir(found) else '')
    return _icloud_cache[0]


def folders():
    """Where the tidy files may be, first found wins: this device's
    Documents/library/datasets, then the same folder in iCloud Drive."""
    found = [os.path.join(os.path.expanduser('~'), 'Documents', *DATA_FOLDER)]
    cloud = icloud_documents()
    if cloud:
        found.append(os.path.join(cloud, *DATA_FOLDER))
    return found


def placeholder(folder, name):
    """iCloud's stand-in for a file not downloaded yet: .name.icloud."""
    return os.path.join(folder, '.%s.icloud' % name)


def request_download(folder, name):
    """Ask iCloud to bring name down to this device. True when asked."""
    try:
        from objc_util import ObjCClass, nsurl
        manager = ObjCClass('NSFileManager').defaultManager()
        return bool(manager.startDownloadingUbiquitousItemAtURL_error_(nsurl(os.path.join(folder, name)), None))
    except Exception:
        return False


def find(name, search=None):
    """The first path to name in search (default folders()), or None. A
    file iCloud has not downloaded yet is asked for, and waited on for up
    to ICLOUD_WAIT_SECONDS."""
    search = folders() if search is None else search
    for folder in search:
        path = os.path.join(folder, name)
        if os.path.isfile(path):
            return path
    for folder in search:
        if os.path.exists(placeholder(folder, name)) and request_download(folder, name):
            path = os.path.join(folder, name)
            deadline = time.time() + ICLOUD_WAIT_SECONDS
            while time.time() < deadline:
                if os.path.isfile(path):
                    return path
                time.sleep(0.25)
    return None


def load(key, search=None):
    """The dataset key ('pokemon' or 'countries'), read once per run."""
    if key in _loaded:
        return _loaded[key]
    path = find(FILES[key], search)
    if path is None:
        raise MissingData(
            'No %s yet. Put it in library/datasets in Pythonista\'s iCloud Drive folder '
            '(projects/mathskit/tools/build_datasets.py builds it). If it is there, iCloud may '
            'still be downloading it: tap New data in a moment.' % FILES[key])
    with open(path, newline='', encoding='utf-8') as handle:
        rows = [to_row(row) for row in csv.DictReader(handle)]
    _loaded[key] = Source(key, rows, path)
    return _loaded[key]


def available(search=None):
    """The keys whose files are here or waiting in iCloud, in FILES order."""
    search = folders() if search is None else search
    return [key for key, name in FILES.items()
            if any(os.path.isfile(os.path.join(folder, name)) or os.path.exists(placeholder(folder, name))
                   for folder in search)]


def to_row(raw):
    """A CSV row with numbers as numbers and blanks as None."""
    row = {}
    for column, text in raw.items():
        text = (text or '').strip()
        if column in TEXT_COLUMNS:
            row[column] = text
        elif text == '':
            row[column] = None
        else:
            number = float(text)
            row[column] = int(number) if number == int(number) and '.' not in text else number
    return row
