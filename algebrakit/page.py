"""The page side of algebrakit: what an editorkit.web page needs for boards.

    tile = tiles.Cards(window, extra_css=page.page_extras())
    page.prose(page_module.board_html(shape))

The page shell (editorkit.web.codeview.page_html) only takes extra_css
inside its style tag, so page_extras() is KaTeX's stylesheet plus the
board CSS, then it closes the style tag, adds KaTeX and the board scripts,
and opens an empty style tag for the shell to close (the same trick as
mathskit.typeset). The page loads from a string, so KaTeX's fonts go in as
data URIs. Built once per run and cached (about 0.8 MB).

The board script finds every data-ak-board element by itself, so Python
only ever sends HTML.

Pure Python: no editorkit import here, so tests run anywhere.
"""
import base64
import html
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, 'web')

# The board's own files, in load order: the engine first, the board uses it.
SCRIPTS = ('engine.js', 'board.js')
STYLES = ('board.css',)

# KaTeX: bundled beside the project in a release (katex/), else the shared
# library copy (library/katex) while developing.
KATEX_CANDIDATES = (
    os.path.join(os.path.dirname(HERE), 'katex'),
    os.path.join(os.path.expanduser('~'), 'Documents', 'library', 'katex'))

FONT_URL = re.compile(r'url\((["\']?)fonts/([^)"\']+?\.woff2)\1\)')

_cached = None


class MissingKatex(RuntimeError):
    """KaTeX is not in any of KATEX_CANDIDATES."""


def find_katex():
    for folder in KATEX_CANDIDATES:
        if os.path.isfile(os.path.join(folder, 'katex.min.js')):
            return folder
    raise MissingKatex('KaTeX not found in: ' + ', '.join(KATEX_CANDIDATES))


def page_extras():
    """extra_css for a page that shows boards (cached)."""
    global _cached
    if _cached is None:
        _cached = build_extras(find_katex())
    return _cached


def build_extras(katex_folder):
    css = read_text(katex_folder, 'katex.min.css')
    css = FONT_URL.sub(lambda match: font_data_url(katex_folder, match), css)
    styles = '\n'.join(read_text(WEB, name) for name in STYLES)
    scripts = [read_text(katex_folder, 'katex.min.js')]
    scripts += [read_text(WEB, name) for name in SCRIPTS]
    script = '\n;\n'.join(safe_script(part) for part in scripts)
    return '%s\n%s\n</style><script>%s</script><style>' % (css, styles, script)


def board_assets():
    """(css, js) for boards on a page that already has KaTeX (mathskit's
    pages do): the board's own styles and scripts, nothing else."""
    css = '\n'.join(read_text(WEB, name) for name in STYLES)
    js = '\n;\n'.join(safe_script(read_text(WEB, name)) for name in SCRIPTS)
    return css, js


def board_html(shape):
    """A board for one equation. shape is {left: [term], right: [term]} with
    each term {n, d, v} (see equations.py)."""
    return '<div class="ak-board" data-ak-board="%s"></div>' % html.escape(
        json.dumps(shape), quote=True)


def read_text(folder, name):
    with open(os.path.join(folder, name), encoding='utf-8') as handle:
        return handle.read()


def font_data_url(folder, match):
    """A font as a data URI. A font the KaTeX copy lacks (library/katex is
    trimmed: no Caligraphic-Bold, for one) keeps its URL and simply never
    loads; boards never use those faces."""
    path = os.path.join(folder, 'fonts', match.group(2))
    if not os.path.isfile(path):
        return match.group(0)
    with open(path, 'rb') as handle:
        data = base64.b64encode(handle.read()).decode('ascii')
    return 'url(data:font/woff2;base64,%s)' % data


def safe_script(text):
    """A script inside an inline <script> tag must never close it early."""
    return text.replace('</script', '<\\/script')
