"""Equations and expressions for boards: make them, read them, write them.
Pure Python.

A shape is what a board starts from:

    {'left': [item, ...], 'right': [item, ...]}        an equation
    {'left': [item, ...], 'right': None, 'goal': 'expand' | 'factorise'}
                                                       an expression

    term    = {'n': 3, 'd': 1, 'v': 'x', 'p': 1}       3x  (x^2 has p 2;
                                                       a number has v '' and p 0)
            = {'n': 3, 'd': 1, 'l': {'a': 1, 'b': 1}}  3ab: more than one letter
    bracket = {'k': 3, 'kd': 1, 'kv': '', 'kp': 0, 'terms': [term, ...]}
                                                       3(x + 4); kv 'x' makes x(x + 4)
                                                       (kl {'a': 1, 'b': 1} makes ab(...))
            + 'under': [term, ...]                     all over a bracket: (x + a)/(x + b)

One letter is always written v and p, more than one always l, so each
value has one shape.
    pair    = {'k': 1, 'kd': 1, 'factors': [bracket, bracket]}
                                                       (x + 2)(x + 3)

    read('3x + 4 = 19')            # a shape, or None if a board cannot play it yet
    read('(x + 2)(x - 5)')         # no = makes an expression
    read('3ab + 6a', letters='ab') # terms in any of the letters given
    text(shape)                    # '3x + 4 = 19'
    answer(shape)                  # Fraction(5), for linear equations
    polynomial(items)              # {power: Fraction} for checking a side in one letter
    expanded(items)                # {letters: Fraction} for checking any side
    random_equation(rng, form)     # FORMS and BRACKET_FORMS
    random_expression(rng, form)   # EXPAND_FORMS and FACTORISE_FORMS
    random_lettered(rng, form)     # LETTER_FORMS: collect, expand, factorise with ab
    random_subject(rng, formula)   # FORMULAS: a formula and a letter to make the subject

Over a number reads as written: x/3 and (x + 5)/2 (wave 3), and terms can
carry several letters: 3ab, x^2y, and letters underneath: d/t, (v - u)/a
(wave 3, with letters=; a letter underneath has a negative power). A shape
can carry 'subject': the letter to make the subject (goal 'subject'). Brackets inside
brackets, three brackets, letters other than those allowed and letters on
the bottom of a fraction are for later waves: read() returns None for them,
so a caller (a mathskit lesson) can quietly leave the board out.
"""
import random
import re
from fractions import Fraction

# --- What to practise (editable) ------------------------------------------------
COEFFICIENTS = range(2, 10)          # the number in front of x
ANSWERS = [n for n in range(-10, 13) if n != 0]
CONSTANTS = [n for n in range(-15, 16) if n != 0]
SMALL = [n for n in range(-9, 10) if n != 0]
FORMS = ('ax+b=c', 'b+ax=c', 'ax+b=cx+d', 'c=ax+b', 'b-ax=c')
BRACKET_FORMS = ('a(x+b)=c', 'a(x+b)=cx+d', 'a(x+b)+e=c', 'a(x+b)=c(x+d)')
EXPAND_FORMS = ('(x+a)(x+b)', '(x+a)(x-a)', '(ax+b)(x+c)', 'x(x+a)', 'k(x+a)(x+b)')
FACTORISE_FORMS = ('x^2+bx+c', 'x^2-a^2', 'ax^2+bx', 'a(x+b)', 'ax^2+bx+c')
LETTER_FORMS = ('pab+qa+rab+sb', 'ka(mb+nc)', 'kab+ka')    # in the letters a, b, c
# Formulas to rearrange (editable). Any letter that appears once, in a term
# on top, and is not already alone on its side can be asked for. Letters in
# a term are always written in alphabetical order, so F = ma would show as
# F = am: leave such formulas out for now.
FORMULAS = ('v = u + at', 'y = mx + c', 'P = 2l + 2w', 'A = bh/2', 'V = IR',
            'd = st', 'E = Pt', 'y = 3x - 4', 'T = 5n + 2', 'M = (a + b)/2', 'k = 2(h + 3)',
            'A = lw', 'C = 2r + 5',
            # the subject twice: gather it, factorise it out, divide by the bracket
            'ax + b = cx + d', 'xy = x + 4', 'ab + c = ad', 'a(x + 2) = bx',
            'y = (x + a)/(x + b)', 'y = (2x + 1)/(x - 3)')
# How hard a rearrangement is (see subject_level).
LEVELS = {1: 'one step or two', 2: 'fractions and brackets', 3: 'the subject twice'}


def term(n, v='', d=1, p=None, letters=None):
    """3x is term(3, 'x'); 3ab is term(3, letters={'a': 1, 'b': 1})."""
    if letters is not None:
        letters = {name: power for name, power in letters.items() if power}
        if len(letters) > 1:
            return {'n': n, 'd': d, 'l': dict(sorted(letters.items()))}
        v, p = next(iter(letters.items())) if letters else ('', 0)
    return {'n': n, 'd': d, 'v': v, 'p': (p if p is not None else 1) if v else 0}


def bracket(k, terms, kd=1, kv='', kp=0, kl=None, under=None):
    """3(x + 4) is bracket(3, terms); ab(...) is bracket(1, terms, kl={'a': 1, 'b': 1});
    (x + a)/(x + b) is bracket(1, top terms, under=bottom terms)."""
    if kl is not None:
        kl = {name: power for name, power in kl.items() if power}
        if len(kl) > 1:
            made = {'k': k, 'kd': kd, 'kl': dict(sorted(kl.items())), 'terms': terms}
            if under:
                made['under'] = under
            return made
        kv, kp = next(iter(kl.items())) if kl else ('', 0)
    made = {'k': k, 'kd': kd, 'kv': kv, 'kp': kp if kv else 0, 'terms': terms}
    if under:
        made['under'] = under
    return made


def letters_of(item, prefix=''):
    """A term's letters (prefix 'k': a bracket's factor's) as {letter: power}."""
    if prefix + 'l' in item:
        return dict(item[prefix + 'l'])
    v = item.get(prefix + 'v', '')
    return {v: item.get(prefix + 'p', 1) or 1} if v else {}


def pair(first, second, k=1, kd=1):
    return {'k': k, 'kd': kd, 'factors': [first, second]}


def is_bracket(item):
    return 'terms' in item


def is_pair(item):
    return 'factors' in item


# --- Reading --------------------------------------------------------------------

class Unreadable(ValueError):
    """Text a board cannot play yet."""


def read(source, letter='x', letters=None):
    """Text -> a shape, or None when a board cannot play it yet. With one =
    it is an equation; with none, an expression (goal left for the caller).
    letters (say 'ab') allows terms in any of those letters; otherwise only
    letter."""
    allowed = letters or letter
    source = (source.replace('\u2212', '-').replace('\u00b2', '^2').replace(' ', '')
              .replace('*', ''))
    if source.count('=') > 1 or not re.fullmatch(r'[0-9%s+\-=()^/]+' % re.escape(allowed), source):
        return None
    try:
        parts = [Reader(part, allowed).side() for part in source.split('=')]
    except Unreadable:
        return None
    if len(parts) == 1:
        return {'left': parts[0], 'right': None, 'goal': None}
    return {'left': parts[0], 'right': parts[1]}


class Reader:
    """Reads one side: items joined by + and -. An item is a term (3x^2,
    2ab), a bracket with an optional factor (3(x + 4), x(x - 1)) or two
    brackets multiplied ((x + 2)(x + 3)). Inside a bracket only terms.
    letters is the string of letters a term may use."""

    def __init__(self, text, letters):
        self.text = text
        self.at = 0
        self.letters = letters

    def peek(self):
        return self.text[self.at] if self.at < len(self.text) else ''

    def take(self, char):
        if self.peek() != char:
            raise Unreadable(self.text)
        self.at += 1

    def number(self):
        start = self.at
        while self.peek().isdigit():
            self.at += 1
        return int(self.text[start:self.at]) if self.at > start else None

    def sign(self, first):
        if self.peek() in '+-':
            negative = self.peek() == '-'
            self.at += 1
            return -1 if negative else 1
        if not first:
            raise Unreadable(self.text)       # 3(x + 1)4 or a missing sign
        return 1

    def monomial(self):
        """[digits][letter[^digits]]... -> (n, {letter: power}), or raises
        when there is neither. A letter written twice multiplies: aab is
        a^2b."""
        n = self.number()
        letters = {}
        while self.peek() and self.peek() in self.letters:
            name = self.peek()
            self.at += 1
            p = 1
            if self.peek() == '^':
                self.at += 1
                p = self.number()
                if not p:
                    raise Unreadable(self.text)
            letters[name] = letters.get(name, 0) + p
        if n is None and not letters:
            raise Unreadable(self.text)
        return (1 if n is None else n), letters

    def terms(self):
        found = []
        while self.peek() and self.peek() != ')':
            sign = self.sign(not found)
            n, letters = self.monomial()
            found.append(term(sign * n, letters=letters))
        if not found:
            raise Unreadable(self.text)
        return found

    def inside(self):
        self.take('(')
        found = self.terms()
        self.take(')')
        return found

    def over(self):
        """A /d after a term or bracket: x/3, (x + 5)/2, d/t, (v - u)/2a ->
        (d, {letter: power underneath}, None), or a bracket underneath:
        4/(y - 1), (x + a)/(x + b) -> (1, {}, [term, ...]). The fraction stays
        as written; the board decides when it simplifies."""
        if self.peek() != '/':
            return 1, {}, None
        self.at += 1
        if self.peek() == '(':
            return 1, {}, self.inside()
        n, letters = self.monomial()
        if not n or self.peek() == '(':
            raise Unreadable(self.text)       # x/0, x/2(y + 1)
        return n, letters, None

    @staticmethod
    def under(letters, bottom):
        """letters on top with bottom's letters underneath (negative powers)."""
        out = dict(letters)
        for name, power in bottom.items():
            out[name] = out.get(name, 0) - power
        return out

    def item(self, first):
        sign = self.sign(first)
        if self.peek() == '(':
            first_bracket = self.inside()
            if self.peek() == '(':
                return pair(bracket(1, first_bracket), bracket(1, self.inside()), k=sign)
            d, bottom, below = self.over()
            return bracket(sign, first_bracket, kd=d, kl=self.under({}, bottom), under=below)
        n, letters = self.monomial()
        if self.peek() == '(':
            inside = self.inside()
            if self.peek() == '(':
                if letters:
                    raise Unreadable(self.text)   # x(x + 1)(x + 2): not yet
                return pair(bracket(1, inside), bracket(1, self.inside()), k=sign * n)
            d, bottom, below = self.over()
            return bracket(sign * n, inside, kd=d, kl=self.under(letters, bottom), under=below)
        d, bottom, below = self.over()
        if below:                                 # 4/(y - 1): the term over a bracket
            return bracket(sign, [term(n, letters=letters)], under=below)
        return term(sign * n, d=d, letters=self.under(letters, bottom))

    def side(self):
        items = []
        while self.at < len(self.text):
            items.append(self.item(not items))
        if not items:
            raise Unreadable(self.text)
        return items


# --- Writing ----------------------------------------------------------------------

SQUARES = {2: '\u00b2', 3: '\u00b3'}


def powers_text(letters):
    """{letter: power} (positive powers) -> ab, x\u00b2y, in alphabetical order."""
    return ''.join(name + ('' if power == 1 else SQUARES.get(power, '^%d' % power))
                   for name, power in sorted(letters.items()))


def mono_text(n, d, letters):
    """3ab, x\u00b2y, 2x/3, d/t, 7: a monomial without its sign, as it is
    written. letters is {letter: power}; a negative power goes underneath."""
    size = abs(n)
    top_letters = powers_text({k: p for k, p in letters.items() if p > 0})
    bottom_letters = powers_text({k: -p for k, p in letters.items() if p < 0})
    top = ('' if size == 1 and top_letters else str(size)) + top_letters
    bottom = (str(d) if d != 1 else '') + bottom_letters
    return top + '/' + bottom if bottom else top


def body_text(item):
    if is_bracket(item) and item.get('under'):    # (x + a)/(x + b), 4/(y - 1)
        plain = abs(item['k']) == item.get('kd', 1) and not letters_of(item, 'k')
        inside = side_text(item['terms'])
        if plain:
            top = '(' + inside + ')' if len(item['terms']) > 1 else inside
        else:
            top = mono_text(item['k'], item.get('kd', 1), letters_of(item, 'k')) + '(' + inside + ')'
        return top + '/(' + side_text(item['under']) + ')'
    if is_pair(item):
        size = abs(item['k'])
        front = '' if size == item.get('kd', 1) else mono_text(item['k'], item.get('kd', 1), {})
        return front + ''.join('(' + side_text(f['terms']) + ')' for f in item['factors'])
    factor = letters_of(item, 'k') if is_bracket(item) else {}
    over = item.get('kd', 1) != 1 or any(p < 0 for p in factor.values())
    if is_bracket(item) and over:                 # (x + 5)/2, (v - u)/a, a(x + 2)/x
        on_top = {k: p for k, p in factor.items() if p > 0}
        top = '' if abs(item['k']) == 1 and not on_top else mono_text(item['k'], 1, on_top)
        bottom = (str(item['kd']) if item.get('kd', 1) != 1 else '') + powers_text(
            {k: -p for k, p in factor.items() if p < 0})
        return top + '(' + side_text(item['terms']) + ')/' + bottom
    if is_bracket(item):
        plain = abs(item['k']) == item.get('kd', 1) and not letters_of(item, 'k')
        front = '' if plain else mono_text(item['k'], item.get('kd', 1), letters_of(item, 'k'))
        return front + '(' + side_text(item['terms']) + ')'
    return mono_text(item['n'], item['d'], letters_of(item))


def sign_of(item):
    return item['k'] if (is_bracket(item) or is_pair(item)) else item['n']


def side_text(items):
    words = []
    for index, item in enumerate(items):
        negative = sign_of(item) < 0
        if index == 0:
            words.append(('-' if negative else '') + body_text(item))
        else:
            words.append(('- ' if negative else '+ ') + body_text(item))
    return ' '.join(words) if words else '0'


def text(shape):
    if shape['right'] is None:
        return side_text(shape['left'])
    return '%s = %s' % (side_text(shape['left']), side_text(shape['right']))


# --- Values -----------------------------------------------------------------------

def expanded(items):
    """{letters: Fraction} for a side, brackets multiplied out, where letters
    is a sorted tuple of (letter, power): 3ab - b is {(('a', 1), ('b', 1)): 3,
    (('b', 1),): -1}. For checking any side."""
    total = {}

    def times(*letter_maps):
        out = {}
        for letters in letter_maps:
            for name, power in letters.items():
                out[name] = out.get(name, 0) + power
        return tuple(sorted(out.items()))

    def add(key, value):
        total[key] = total.get(key, Fraction(0)) + value
        if not total[key]:
            del total[key]

    for item in items:
        if is_pair(item):
            k = Fraction(item['k'], item.get('kd', 1))
            first, second = (f['terms'] for f in item['factors'])
            for a in first:
                for b in second:
                    add(times(letters_of(a), letters_of(b)),
                        k * Fraction(a['n'], a['d']) * Fraction(b['n'], b['d']))
        elif is_bracket(item):
            if item.get('under'):
                raise ValueError('a bracket underneath: no expansion')
            k = Fraction(item['k'], item.get('kd', 1))
            for t in item['terms']:
                add(times(letters_of(item, 'k'), letters_of(t)), k * Fraction(t['n'], t['d']))
        else:
            add(times(letters_of(item)), Fraction(item['n'], item['d']))
    return total


def polynomial(items):
    """{power: Fraction} for a side in one letter, brackets multiplied out.
    For checking. Raises ValueError for a term in more than one letter
    (use expanded() for those)."""
    total = {}
    for key, value in expanded(items).items():
        if len(key) > 1:
            raise ValueError('more than one letter in a term: use expanded()')
        power = key[0][1] if key else 0
        total[power] = total.get(power, Fraction(0)) + value
        if not total[power]:
            del total[power]
    return total


def answer(shape):
    """The value of x as a Fraction, for a linear equation (raises
    ValueError when there is no single answer or x is squared)."""
    left, right = polynomial(shape['left']), polynomial(shape['right'])
    if any(power > 1 for power in list(left) + list(right)):
        raise ValueError('not a linear equation')
    left_x, right_x = left.get(1, Fraction(0)), right.get(1, Fraction(0))
    if left_x == right_x:
        raise ValueError('no single answer: the x terms cancel')
    return (right.get(0, Fraction(0)) - left.get(0, Fraction(0))) / (left_x - right_x)


# --- Making equations -------------------------------------------------------------

def random_equation(rng=None, form=None):
    """A linear equation with a whole-number answer, in one of FORMS (or
    BRACKET_FORMS, when named)."""
    rng = rng or random.Random()
    form = form or rng.choice(FORMS)
    if form in BRACKET_FORMS:
        return bracket_equation(rng, form)
    x = rng.choice(ANSWERS)
    a = rng.choice(COEFFICIENTS)
    b = rng.choice(CONSTANTS)
    if form == 'ax+b=c':
        return {'left': [term(a, 'x'), term(b)], 'right': [term(a * x + b)]}
    if form == 'b+ax=c':
        return {'left': [term(b), term(a, 'x')], 'right': [term(a * x + b)]}
    if form == 'c=ax+b':
        return {'left': [term(a * x + b)], 'right': [term(a, 'x'), term(b)]}
    if form == 'b-ax=c':
        return {'left': [term(b), term(-a, 'x')], 'right': [term(b - a * x)]}
    # ax + b = cx + d, with a different c and d chosen so x is the answer.
    c = rng.choice([value for value in COEFFICIENTS if value != a])
    d = a * x + b - c * x
    right = [term(c, 'x')] + ([term(d)] if d else [])
    return {'left': [term(a, 'x'), term(b)], 'right': right}


def bracket_equation(rng, form):
    """A wave 2 equation: a(x + b) on the left, with a whole-number answer."""
    x = rng.choice(ANSWERS)
    a = rng.choice(COEFFICIENTS)
    b = rng.choice(SMALL)
    left = [bracket(a, [term(1, 'x'), term(b)])]
    value = a * (x + b)
    if form == 'a(x+b)=c':
        return {'left': left, 'right': [term(value)]}
    if form == 'a(x+b)+e=c':
        e = rng.choice(CONSTANTS)
        return {'left': left + [term(e)], 'right': [term(value + e)]}
    others = [c for c in COEFFICIENTS if c != a]
    if form == 'a(x+b)=c(x+d)':
        rng.shuffle(others)
        for c in others:
            if value % c == 0 and value // c - x != 0:
                return {'left': left, 'right': [bracket(c, [term(1, 'x'), term(value // c - x)])]}
    # a(x + b) = cx + d (also the fallback when no c(x + d) fits)
    c = rng.choice(others)
    d = value - c * x
    return {'left': left, 'right': [term(c, 'x')] + ([term(d)] if d else [])}


# --- Making expressions -----------------------------------------------------------

def linear(m, r):
    """mx + r as bracket terms (r may be 0: just mx)."""
    return [term(m, 'x')] + ([term(r)] if r else [])


def from_polynomial(poly):
    """{power: value} -> terms, highest power first."""
    return [term(int(poly[p]), 'x' if p else '', p=p) for p in sorted(poly, reverse=True)]


def random_expression(rng=None, form=None):
    """An expression to expand (EXPAND_FORMS) or to factorise
    (FACTORISE_FORMS), with its goal."""
    rng = rng or random.Random()
    form = form or rng.choice(EXPAND_FORMS + FACTORISE_FORMS)
    a, b = rng.choice(SMALL), rng.choice(SMALL)
    if form == '(x+a)(x+b)':
        made = [pair(bracket(1, linear(1, a)), bracket(1, linear(1, b)))]
    elif form == '(x+a)(x-a)':
        made = [pair(bracket(1, linear(1, abs(a))), bracket(1, linear(1, -abs(a))))]
    elif form == '(ax+b)(x+c)':
        made = [pair(bracket(1, linear(rng.choice([2, 3, 4, 5]), a)), bracket(1, linear(1, b)))]
    elif form == 'x(x+a)':
        made = [bracket(1, linear(1, a), kv='x', kp=1)]
    elif form == 'k(x+a)(x+b)':
        made = [pair(bracket(1, linear(1, a)), bracket(1, linear(1, b)), k=rng.choice(COEFFICIENTS))]
    if form in EXPAND_FORMS:
        return {'left': made, 'right': None, 'goal': 'expand'}
    # Factorising: build the factorised form, then hand over its expansion.
    if form == 'x^2+bx+c':
        source = [pair(bracket(1, linear(1, a)), bracket(1, linear(1, b)))]
    elif form == 'x^2-a^2':
        source = [pair(bracket(1, linear(1, abs(a))), bracket(1, linear(1, -abs(a))))]
    elif form == 'ax^2+bx':
        source = [bracket(rng.choice(COEFFICIENTS), linear(1, a), kv='x', kp=1)]
    elif form == 'a(x+b)':
        source = [bracket(rng.choice(COEFFICIENTS), linear(rng.choice([1, 2, 3]), a))]
    else:
        source = [pair(bracket(1, linear(rng.choice([2, 3]), a)), bracket(1, linear(1, b)))]
    poly = polynomial(source)
    if len(poly) < 2:                       # collapsed to one term: draw again
        return random_expression(rng, form)
    if form == 'ax^2+bx+c' and common_factor(poly) > 1:
        return random_expression(rng, form)   # keep this form about the two brackets
    return {'left': from_polynomial(poly), 'right': None, 'goal': 'factorise'}


def common_factor(poly):
    """The highest common factor of a polynomial's (whole) coefficients."""
    from math import gcd
    result = 0
    for value in poly.values():
        result = gcd(result, int(value))
    return result


# --- Practising with more than one letter ------------------------------------------

AB = {'a': 1, 'b': 1}
LETTER_FACTORS = (1, 2, 3, 4, 5)     # the number in front of a(...) (editable)


def from_expanded(total):
    """{letters: value} (as expanded() gives) -> terms, highest power first,
    then in alphabetical order."""
    def order(key):
        return (-sum(power for _, power in key), key)
    return [term(int(total[key]), letters=dict(key)) for key in sorted(total, key=order)]


def random_lettered(rng=None, form=None):
    """An expression in the letters a, b, c, in one of LETTER_FORMS, with its
    goal: collect like terms (3ab - a + 2ab + 4b), expand (2a(3b - c)) or
    factorise (6ab + 3a, made from 3a(2b + 1)). Read its text back with
    read(text, letters='abc')."""
    rng = rng or random.Random()
    form = form or rng.choice(LETTER_FORMS)
    if form == 'pab+qa+rab+sb':
        p, q, r, s = (rng.choice(SMALL) for _ in range(4))
        if p + r == 0:
            return random_lettered(rng, form)
        made = [term(p, letters=AB), term(q, 'a'), term(r, letters=AB), term(s, 'b')]
        return {'left': made, 'right': None, 'goal': 'simplify'}
    k = rng.choice(LETTER_FACTORS)
    if form == 'ka(mb+nc)':
        inside = [term(rng.choice(SMALL), 'b'), term(rng.choice(SMALL), 'c')]
        return {'left': [bracket(k, inside, kl={'a': 1})], 'right': None, 'goal': 'expand'}
    # kab + ka: build k a(m b + n), then hand over its expansion.
    source = [bracket(k, [term(rng.choice(SMALL), 'b'), term(rng.choice(SMALL))], kl={'a': 1})]
    return {'left': from_expanded(expanded(source)), 'right': None, 'goal': 'factorise'}


# --- Changing the subject -----------------------------------------------------------

def letters_in(text):
    """Every letter a formula uses, as a string for read(letters=)."""
    return ''.join(sorted(set(re.findall('[A-Za-z]', text))))


def appearances(shape, letter):
    """How many times a letter appears (terms, bracket factors, bottoms),
    or None when it is ever squared or underneath a term."""
    count = 0
    for side in ('left', 'right'):
        for item in shape[side]:
            groups = item['factors'] if is_pair(item) else [item] if is_bracket(item) else []
            pieces = [letters_of(item)] if not groups else []
            for group in groups:
                pieces.append(letters_of(group, 'k'))
                pieces += [letters_of(t) for t in group['terms'] + group.get('under', [])]
            for letters in pieces:
                if letter in letters:
                    if letters[letter] != 1:
                        return None              # x\u00b2, d/t: later
                    count += 1
    return count


def is_alone(shape, letter):
    """Is the letter already the whole of one side?"""
    for side in ('left', 'right'):
        items = shape[side]
        if (len(items) == 1 and not is_bracket(items[0]) and not is_pair(items[0]) and
                letters_of(items[0]) == {letter: 1} and items[0]['n'] == items[0]['d']):
            return True
    return False


def subject_choices(shape):
    """The letters a formula can be rearranged for: never squared or under a
    term, and not already alone on a side. Each may appear more than once."""
    letters = sorted(set(re.findall('[A-Za-z]', text(shape))))
    return [name for name in letters if appearances(shape, name) and not is_alone(shape, name)]


def subject_level(shape, letter):
    """1: the subject once, no fractions or brackets on its way (v = u + at
    for t); 2: fractions or brackets (A = bh/2, k = 2(h + 3)); 3: the subject
    more than once, so it must be factorised out (ax + b = cx + d)."""
    if appearances(shape, letter) > 1:
        return 3
    plain = all(not is_bracket(item) and not is_pair(item) and item['d'] == 1 and
                all(p > 0 for p in letters_of(item).values())
                for side in ('left', 'right') for item in shape[side])
    return 1 if plain else 2


def subject_pairs(level=None):
    """Every (formula, letter) in FORMULAS, of one level or all."""
    pairs = []
    for formula in FORMULAS:
        shape = read(formula, letters=letters_in(formula))
        for letter in subject_choices(shape):
            if level is None or subject_level(shape, letter) == level:
                pairs.append((formula, letter))
    return pairs


def random_subject(rng=None, formula=None, level=None):
    """A formula with a letter to make the subject: {'left', 'right',
    'subject', 'goal': 'subject', 'level'}. formula picks one (any of its
    letters), level picks among all of FORMULAS (see subject_level)."""
    rng = rng or random.Random()
    if formula:
        pairs = [(formula, letter) for letter in
                 subject_choices(read(formula, letters=letters_in(formula)))]
    else:
        pairs = subject_pairs(level)
    formula, letter = rng.choice(pairs)
    shape = read(formula, letters=letters_in(formula))
    shape['subject'] = letter
    shape['goal'] = 'subject'
    shape['level'] = subject_level(shape, letter)
    return shape
