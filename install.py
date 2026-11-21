"""Install or update Maths (mathskit) from its public GitHub snapshot.

Run it through the bootstrap script in the README. Running the bootstrap
again at any time updates to the current GitHub release:

- the previous install is kept as a dated backup, and only the newest
  KEEP_BACKUPS backups are kept;
- if the installed version already matches GitHub, nothing is changed;
- with Toolbox installed (github.com/jackatttack/editorkit), a Maths card is
  written into Toolbox's tools, so Maths opens from the hub.

    main()                                  install or update from GitHub
    main(documents=folder, source=folder)   the same from a local copy (tests)
"""
import io
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import sys
import tempfile
from datetime import datetime
from urllib.request import urlopen
from zipfile import ZipFile


# ------------------------------------------------------------ editable settings

ARCHIVE_URL = "https://github.com/jackatttack/mathskit/archive/refs/heads/main.zip"
ARCHIVE_FOLDER = "mathskit-main"          # the one folder inside GitHub's zip
INSTALL_NAME = "Mathskit"
VERSION_FILE = "RELEASE_VERSION.txt"
KEEP_BACKUPS = 2
# User data carried from the old install into the new one (none yet).
USER_FOLDERS = ()
USER_FILES = ()
# The Toolbox card. Written only when Documents/Toolbox exists.
TOOLBOX_TOOLS = ("Toolbox", "tools")
CARD_FILE = "mathskit.json"
CARD = {
    "name": "Maths",
    "emoji": "\U0001f9ee",
    "what": "lessons, questions and key facts",
    "module": "maths_tool",
    "function": "main",
    "about": ("Lessons to teach from: worked examples you step through, questions "
              "with touch algebra boards, key facts, and a question bank."),
}
# The card older MathsGen installs wrote for the copy of Maths they carried.
OLD_CARD_FILE = "mathsgen_maths.json"
OLD_CARD_FOLDER = os.path.join("mathsgen", "mathskit")
# Files a release must hold.
REQUIRED = (
    "maths_tool.py",
    "mathskit/lesson.py",
    "algebrakit/equations.py",
    "algebrakit/web/engine.js",
    "mathsgen/mathsgen/catalogue.py",
    "katex/katex.min.js",
    "README.md",
    VERSION_FILE,
)

# ------------------------------------------------------------ safety limits

MAX_DOWNLOAD_BYTES = 32 * 1024 * 1024
MAX_UNPACKED_BYTES = 80 * 1024 * 1024
MAX_FILE_BYTES = 12 * 1024 * 1024
BACKUP_PREFIX = INSTALL_NAME + "_backup_"
SKIP_NAMES = ("__pycache__", ".DS_Store")


def pythonista_documents():
    """Locate local Documents from the script running this installer."""
    script = Path(__file__).resolve()
    for directory in script.parents:
        if directory.name == "Documents":
            return directory
    raise RuntimeError(
        "Save and run the bootstrap script inside Pythonista's local Documents folder."
    )


def download_archive():
    """Bound the download so a mistaken response cannot fill device storage."""
    with urlopen(ARCHIVE_URL, timeout=60) as response:
        payload = response.read(MAX_DOWNLOAD_BYTES + 1)
    if len(payload) > MAX_DOWNLOAD_BYTES:
        raise RuntimeError("Download exceeds the expected size.")
    return ZipFile(io.BytesIO(payload))


def unpack_archive(archive, destination):
    """Validate archive members, then copy regular files into a fresh folder."""
    members = [item for item in archive.infolist() if not item.is_dir()]
    prefixes = {item.filename.split("/", 1)[0] for item in members}
    if prefixes != {ARCHIVE_FOLDER}:
        raise RuntimeError("Unexpected repository archive layout: " + repr(prefixes))
    total = 0
    for item in members:
        parts = PurePosixPath(item.filename).parts
        if len(parts) < 2 or any(part in ("", ".", "..") for part in parts):
            raise RuntimeError("Unsafe path in repository archive.")
        if stat.S_ISLNK(item.external_attr >> 16):
            raise RuntimeError("Repository archive contains a symbolic link.")
        if item.file_size > MAX_FILE_BYTES:
            raise RuntimeError("A repository file exceeds the expected size.")
        total += item.file_size
        if total > MAX_UNPACKED_BYTES:
            raise RuntimeError("Repository archive exceeds the expected size.")
        target = destination.joinpath(*parts[1:])
        target.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(item) as source, target.open("wb") as output:
            shutil.copyfileobj(source, output)
    return len(members)


def unpack_folder(source, destination):
    """A local copy of the release (the stage tool's install test)."""
    shutil.copytree(str(source), str(destination), dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns(*SKIP_NAMES))
    return sum(len(names) for _, _, names in os.walk(str(destination)))


def check_release(folder):
    """Every required file is there and every Python file compiles."""
    missing = [name for name in REQUIRED if not (folder / name).is_file()]
    if missing:
        raise RuntimeError("The release is incomplete: " + ", ".join(missing))
    for path in folder.rglob("*.py"):
        compile(path.read_bytes(), str(path), "exec")


def installed_version(folder):
    """The release stamp in a folder, or None if it has none."""
    path = folder / VERSION_FILE
    if path.is_file():
        return path.read_text(encoding="utf-8").strip() or None
    return None


def preserve_user_data(old_install, new_install):
    """Carry user files forward while leaving the old install as a backup."""
    for name in USER_FOLDERS:
        old = old_install / name
        if old.is_dir():
            shutil.copytree(str(old), str(new_install / name), dirs_exist_ok=True)
    for name in USER_FILES:
        old = old_install / name
        if old.is_file():
            shutil.copy2(str(old), str(new_install / name))


def prune_backups(documents):
    """Delete all but the newest KEEP_BACKUPS backups. Returns how many went."""
    backups = sorted(path for path in documents.iterdir()
                     if path.is_dir() and path.name.startswith(BACKUP_PREFIX))
    stale = backups[:-KEEP_BACKUPS] if KEEP_BACKUPS else backups
    for path in stale:
        shutil.rmtree(str(path), ignore_errors=True)
    return len(stale)


def forget_loaded_code():
    """Drop modules from an earlier copy already loaded in this session."""
    for name in list(sys.modules):
        if name.split(".")[0] in ("mathskit", "algebrakit", "mathsgen", "maths_tool"):
            del sys.modules[name]


def add_card(documents, target):
    """Write Toolbox's Maths card when Toolbox is installed, through a temp
    file. Retires the card older MathsGen installs wrote for their copy of
    Maths. Returns True when the card was written."""
    toolbox = documents / TOOLBOX_TOOLS[0]
    if not toolbox.is_dir():
        return False
    folder = documents.joinpath(*TOOLBOX_TOOLS)
    folder.mkdir(parents=True, exist_ok=True)
    card = dict(CARD, folder=str(target))
    temporary = folder / (CARD_FILE + ".tmp")
    temporary.write_text(json.dumps(card, indent=2, ensure_ascii=False) + "\n",
                         encoding="utf-8")
    os.replace(str(temporary), str(folder / CARD_FILE))
    old = folder / OLD_CARD_FILE
    if old.is_file():
        try:
            pointed = json.loads(old.read_text(encoding="utf-8")).get("folder", "")
        except ValueError:
            pointed = ""
        if pointed.rstrip("/").endswith(OLD_CARD_FOLDER):
            old.unlink()
            print("Retired MathsGen's old Maths card: this install replaces it.")
    return True


def main(documents=None, source=None):
    """Install or update. Returns 'installed', 'updated' or 'current'."""
    documents = Path(documents) if documents else pythonista_documents()
    target = documents / INSTALL_NAME
    old_version = installed_version(target) if target.exists() else None
    if source is None:
        print("Checking GitHub for the latest Maths...")
        archive = download_archive()
    else:
        archive = None
    temporary_root = Path(tempfile.mkdtemp(prefix=".mathskit_install_", dir=str(documents)))
    candidate = temporary_root / INSTALL_NAME
    backup = None
    try:
        candidate.mkdir()
        count = (unpack_archive(archive, candidate) if archive is not None
                 else unpack_folder(Path(source), candidate))
        check_release(candidate)
        new_version = installed_version(candidate)
        if target.exists() and new_version and new_version == old_version:
            print("Maths is already up to date ({}).".format(new_version))
            if add_card(documents, target):
                print("Maths is in Toolbox.")
            return "current"
        if target.exists():
            preserve_user_data(target, candidate)
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup = documents / (BACKUP_PREFIX + stamp)
            if backup.exists():
                raise RuntimeError("Backup name already exists; run again in a second.")
            os.replace(str(target), str(backup))
        try:
            os.replace(str(candidate), str(target))
        except Exception:
            if backup is not None:
                os.replace(str(backup), str(target))
            raise
    finally:
        if archive is not None:
            archive.close()
        shutil.rmtree(str(temporary_root), ignore_errors=True)

    removed = prune_backups(documents)
    forget_loaded_code()
    if add_card(documents, target):
        print("Added Maths to Toolbox.")
    else:
        print("Toolbox is not installed: get it from github.com/jackatttack/editorkit,")
        print("then run this installer again to add the Maths card.")
    if backup is None:
        print("Installed Maths {} ({} files) at {}".format(new_version or "", count, target))
    else:
        print("Updated Maths from {} to {}.".format(old_version or "an earlier version",
                                                   new_version or "the latest version"))
        print("Previous install backed up at {}".format(backup.name))
        if removed:
            print("Removed {} older backup{}.".format(removed, "" if removed == 1 else "s"))
    print("Open Maths from Toolbox, or run {}/maths_tool.py.".format(INSTALL_NAME))
    print("If anything still looks old, close Pythonista fully and reopen it.")
    return "installed" if backup is None else "updated"


if __name__ == "__main__":
    main()
