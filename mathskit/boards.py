"""Touch boards from algebrakit inside mathskit pages.

    from mathskit import boards
    boards.available()                         # algebrakit found
    boards.expression(terms, 'simplify')       # a shape from algebra.Terms, or None
    boards.bracket(outside, inside)            # 3(x + 4) as one board item, or None
    boards.equation('3(x + 2) = 2x - 5')       # a shape, or None (fractions: not yet)
    boards.html(shape)                         # the board for a page

A lesson Problem carries board=shape; the Lesson page shows it as Your
move. CSS and SCRIPT ride in every page's extras (typeset.PAGE_PARTS), so
a board needs no Python call once drawn: the engine runs in the page.

algebrakit is a sibling project (projects/algebrakit). When it cannot be
found, every builder returns None and lessons fall back to the button
explorer, so mathskit never needs it.
"""
import os
import sys

# projects/mathskit/mathskit/boards.py -> projects/algebrakit
SIBLING = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), 'algebrakit')


def _load():
    try:
        from algebrakit import equations, page
        return equations, page
    except ImportError:
        pass
    if os.path.isdir(SIBLING) and SIBLING not in sys.path:
        sys.path.append(SIBLING)
    try:
        from algebrakit import equations, page
        return equations, page
    except ImportError:
        return None, None


_equations, _page = _load()

if _page is not None:
    CSS, SCRIPT = _page.board_assets()
else:
    CSS, SCRIPT = '', ''


def available():
    return _page is not None


# --- From mathskit's algebra ----------------------------------------------------

def term(t):
    """An algebra.Term as a board term, or None (two letters, like ab, are
    for a later wave)."""
    if len(t.monomial) > 1:
        return None
    if not t.monomial:
        return {'n': t.coefficient, 'd': 1, 'v': '', 'p': 0}
    letter, power = t.monomial[0]
    return {'n': t.coefficient, 'd': 1, 'v': letter, 'p': power}


def bracket(outside, inside):
    """outside(inside...) as one board item: 3(x + 4), x(2x - 1), or None."""
    k = term(outside)
    terms = [term(t) for t in inside]
    if k is None or None in terms:
        return None
    return {'k': k['n'], 'kd': 1, 'kv': k['v'], 'kp': k['p'], 'terms': terms}


def pair(first, second):
    """(first)(second) as one board item: two brackets of algebra.Terms,
    or None. A square goes in as the same bracket twice."""
    made = [[term(t) for t in terms] for terms in (first, second)]
    if any(None in terms for terms in made):
        return None
    return {'k': 1, 'kd': 1,
            'factors': [{'k': 1, 'kd': 1, 'kv': '', 'kp': 0, 'terms': terms} for terms in made]}


def expression(items, goal):
    """An expression board with a goal ('simplify', 'expand', 'factorise').
    items are algebra.Terms or board items already made; None when any of
    them cannot go on a board yet."""
    if not available():
        return None
    made = [term(item) if hasattr(item, 'monomial') else item for item in items]
    if not made or None in made:
        return None
    return {'left': made, 'right': None, 'goal': goal}


def equation(text):
    """A linear equation board from text, or None when a board cannot play
    it yet."""
    if not available():
        return None
    return _equations.read(text)


def html(shape):
    return _page.board_html(shape)
