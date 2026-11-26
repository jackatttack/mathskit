"""The statistics datasets the Charts page draws from: Pokémon and countries.

Role: gather · Part of: mathskit/charts

Pure Python, except that on Pythonista it asks iOS (objc_util) for the
iCloud folder; elsewhere it looks in Documents/library only.

    from mathskit import datasets
    pokemon = datasets.load('pokemon')       # a Source, or raises MissingData
    pokemon.rows[0]['name']                  # 'Bulbasaur'

The tidy CSVs are built by tools/build_datasets.py into library/datasets/.
They are personal teaching data, so they never ship inside the mathskit
release. The shared copy lives in Pythonista's iCloud Drive folder,
library/datasets; library/copy_to_this_device.py (kept beside it in
iCloud) copies it onto a device's own Documents/library, which load()
reads first. Only when there is no local copy does load() read iCloud
(the folder is asked of iOS, never written in).

Never waits on iCloud (2026-11-26: waiting for downloads and reading
sprites from iCloud inside the tool froze Pythonista on the iPad). A file
iCloud has not downloaded counts as missing, and the message says to run
copy_to_this_device.py.

Numbers come back as int or float, blanks as None.
"""
import csv
import os

# ---- Settings (editable) -----------------------------------------------------

# The folder inside each library the tidy files sit in.
DATA_FOLDER = ('library', 'datasets')
# The script that copies the iCloud library onto a device (it lives in iCloud's library/).
COPY_SCRIPT = 'library/copy_to_this_device.py'

FILES = {'pokemon': 'pokemon.csv', 'countries': 'countries.csv'}
TITLES = {'pokemon': 'Pokémon', 'countries': 'Countries'}

# Columns kept as text; every other column is read as a number.
TEXT_COLUMNS = {'name', 'type1', 'type2', 'colour', 'legendary', 'code', 'iso2', 'continent', 'subregion',
                'population_year'}

# Pokémon sprites (tools/fetch_sprites.py): library/datasets/sprites/<number>.png.
SPRITE_FOLDER = 'sprites'
# Most sprites one chart carries (each about 1 KB inside the page).
SPRITE_LIMIT = 300

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


def find(name, search=None):
    """The first path to name in search (default folders()), or None. Never
    waits: a file iCloud has not downloaded yet is not found."""
    search = folders() if search is None else search
    for folder in search:
        path = os.path.join(folder, name)
        if os.path.isfile(path):
            return path
    return None


def waiting_in_icloud(name, search=None):
    """True when iCloud holds name but has not downloaded it to this device."""
    search = folders() if search is None else search
    return any(os.path.exists(placeholder(folder, name)) for folder in search)


def load(key, search=None):
    """The dataset key ('pokemon' or 'countries'), read once per run."""
    if key in _loaded:
        return _loaded[key]
    path = find(FILES[key], search)
    if path is None:
        if waiting_in_icloud(FILES[key], search):
            raise MissingData(
                '%s is in iCloud but not on this device yet. Run %s (in iCloud Drive, '
                'Pythonista 3) once with a connection, then open Maths again.' % (FILES[key], COPY_SCRIPT))
        raise MissingData(
            'No %s yet. Put it in library/datasets in Pythonista\'s iCloud Drive folder '
            '(projects/mathskit/tools/build_datasets.py builds it), then run %s on each device.'
            % (FILES[key], COPY_SCRIPT))
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


_sprites = {}


def sprites(numbers, search=None, limit=SPRITE_LIMIT):
    """{number: 'data:image/png;base64,...'} for the Pokédex numbers whose
    sprite is on this device; none when there are more than limit (a chart
    of every Pokémon shows names only). Reads only files already here: a
    sprite iCloud has not downloaded is skipped, never waited on."""
    import base64
    numbers = sorted({int(number) for number in numbers if number})
    if not numbers or len(numbers) > limit:
        return {}
    search = folders() if search is None else search
    homes = [os.path.join(folder, SPRITE_FOLDER) for folder in search]
    homes = [home for home in homes if os.path.isdir(home)]
    found = {}
    for number in numbers:
        if number in _sprites:
            found[number] = _sprites[number]
            continue
        name = '%d.png' % number
        for home in homes:
            path = os.path.join(home, name)
            if os.path.isfile(path):
                with open(path, 'rb') as handle:
                    _sprites[number] = 'data:image/png;base64,' + base64.b64encode(handle.read()).decode('ascii')
                found[number] = _sprites[number]
                break
    return found


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
