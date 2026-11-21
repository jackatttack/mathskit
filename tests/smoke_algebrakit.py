"""Smoke test: equations read and solve, and a board page builds.

    RUN projects/algebrakit/tests/smoke_board.py

The move engine itself is JS; its tests are tests/engine_test.js (node).
"""
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
sys.path.insert(0, PROJECT)
for name in list(sys.modules):
    if name == 'algebrakit' or name.startswith('algebrakit.'):
        del sys.modules[name]


from algebrakit import equations, page  # noqa: E402

failures = []


def check(ok, what):
    print(('ok   ' if ok else 'FAIL ') + what)
    if not ok:
        failures.append(what)


# Reading
shape = equations.read('3x + 4 = 19')
check(shape == {'left': [equations.term(3, 'x'), equations.term(4)],
                'right': [equations.term(19)]}, 'read 3x + 4 = 19')
check(equations.text(shape) == '3x + 4 = 19', 'text round trip')
check(equations.answer(shape) == 5, 'answer 5')
check(equations.text(equations.read('5 - x = 2x \u2212 7')) == '5 - x = 2x - 7', 'read minus signs')
for refused in ('(x + 1)(x + 2)(x + 3)', 'x(x + 1)(x + 2) = 0', '2(3(x)) = 1', '(x + 1)4 = 2',
                'x/0 = 3', 'x/y = 2', '3y = 6', 'x = 1 = 2', '3x + = 4', '= 4', 'x^ = 2'):
    check(equations.read(refused) is None, 'refuses %r' % refused)

# Over a number (wave 3): written as taught, solved by multiplying both sides
for over, value in (('x/2 = 3', 6), ('x/5 - 6 = -5', 5), ('(3x - 6)/2 = 12', 10),
                    ('(x + 5)/2 = (x + 10)/3', 5)):
    shape = equations.read(over)
    check(shape is not None and equations.text(shape) == over and equations.answer(shape) == value,
          'reads %s, x = %d' % (over, value))

# Brackets (wave 2)
three = equations.read('3(x + 4) = 21')
check(three == {'left': [equations.bracket(3, [equations.term(1, 'x'), equations.term(4)])],
                'right': [equations.term(21)]}, 'read 3(x + 4) = 21')
check(equations.answer(three) == 3, 'answer through a bracket')
check(equations.text(equations.read('-(x+2) = 2(x - 1)')) == '-(x + 2) = 2(x - 1)', 'bracket text')

# Powers, two brackets, expressions (wave 2b)
quad = equations.read('x\u00b2 + 5x + 6')
check(quad['right'] is None and quad['left'][0] == equations.term(1, 'x', p=2), 'read x\u00b2 + 5x + 6 as an expression')
two = equations.read('(x + 2)(x - 5)')
check(equations.text(two) == '(x + 2)(x - 5)', 'read two brackets')
check(equations.polynomial(two['left']) == {2: 1, 1: -3, 0: -10}, 'polynomial of (x + 2)(x - 5)')
check(equations.text(equations.read('3x(x + 2)')) == '3x(x + 2)', 'read 3x(x + 2)')
check(equations.text(equations.read('-2(x+1)(x+3)')) == '-2(x + 1)(x + 3)', 'read -2(x + 1)(x + 3)')
shapes = random.Random(11)
for form in equations.EXPAND_FORMS + equations.FACTORISE_FORMS:
    good = True
    for _ in range(200):
        made = equations.random_expression(shapes, form)
        poly = equations.polynomial(made['left'])
        back = equations.read(equations.text(made))
        if len(poly) < 2 or back is None or equations.polynomial(back['left']) != poly:
            check(False, '%s made %s' % (form, equations.text(made)))
            good = False
            break
    if good:
        check(True, '%s: 200 expressions read back with the same value' % form)

# More than one letter in a term (wave 3)
ab = equations.read('3ab + 2ba - 4a', letters='ab')
check(ab is not None and ab['left'][0] == equations.term(3, letters={'a': 1, 'b': 1}) and
      ab['left'][0] == {'n': 3, 'd': 1, 'l': {'a': 1, 'b': 1}}, 'read 3ab as letters')
check(equations.text(ab) == '3ab + 2ab - 4a', 'ba written ab')
check(equations.read('3ab = 6') is None, 'ab refused without letters=')
check(equations.read('2a', letters='ab')['left'][0] == equations.term(2, 'a'), 'one letter keeps v and p')
check(equations.text(equations.read('aab + x^2y', letters='abxy')) == 'a\u00b2b + x\u00b2y', 'aab is a\u00b2b')
lettered = equations.read('2a(3b - c)', letters='abc')
check(equations.text(lettered) == '2a(3b - c)' and
      equations.expanded(lettered['left']) == {(('a', 1), ('b', 1)): 6, (('a', 1), ('c', 1)): -2},
      'read 2a(3b - c), expands to 6ab - 2ac')
check(equations.text(equations.read('ab(a + 2)', letters='ab')) == 'ab(a + 2)', 'read ab(a + 2)')
for form in equations.LETTER_FORMS:
    good = True
    for _ in range(200):
        made = equations.random_lettered(shapes, form)
        back = equations.read(equations.text(made), letters='abc')
        if back is None or equations.expanded(back['left']) != equations.expanded(made['left']):
            check(False, '%s made %s' % (form, equations.text(made)))
            good = False
            break
    if good:
        check(True, '%s: 200 expressions read back with the same value' % form)

# Changing the subject (wave 3): letters underneath, formulas, a subject
for written in ('s = d/t', '(v - u)/a = t', 'v/a - u/a = t', '2A/b = h', 'A = bh/2', 'x = (y + 4)/3'):
    shape = equations.read(written, letters=equations.letters_in(written))
    check(shape is not None and equations.text(shape) == written, 'reads %s' % written)
check(equations.read('s = d/t', letters='dst')['right'][0]['l'] == {'d': 1, 't': -1}, 'd/t has t to the power -1')
for formula in equations.FORMULAS:
    shape = equations.read(formula, letters=equations.letters_in(formula))
    check(shape is not None and equations.text(shape) == formula and equations.subject_choices(shape),
          'formula %s reads back, subjects %s' % (formula, shape and ''.join(equations.subject_choices(shape))))
check(equations.subject_choices(equations.read('v = u + at', letters='atuv')) == ['a', 't', 'u'],
      'v = u + at: a, t or u (v is already alone)')
picked = set()
for _ in range(200):
    made = equations.random_subject(shapes)
    picked.add(made['subject'])
    if made['goal'] != 'subject' or made['subject'] not in equations.subject_choices(made):
        check(False, 'random_subject gave %s for %s' % (made['subject'], equations.text(made)))
        break
else:
    check(len(picked) > 5, 'random_subject: 200 formulas, %d different subjects' % len(picked))

# The subject twice (stage 2): brackets underneath, levels
for written in ('x = 4/(y - 1)', 'y = (x + a)/(x + b)', 'x = (d - b)/(a - c)', 'b = a(x + 2)/x'):
    shape = equations.read(written, letters=equations.letters_in(written))
    check(shape is not None and equations.text(shape) == written, 'reads %s' % written)
check(equations.read('y = (x + a)/(x + b)', letters='abxy')['right'][0]['under'] ==
      [equations.term(1, 'x'), equations.term(1, 'b')], '(x + a)/(x + b) has (x + b) under')
check(equations.read('x/2(y + 1) = 3', letters='xy') is None, 'x/2(y + 1) refused')
for level in (1, 2, 3):
    pairs = equations.subject_pairs(level)
    made = equations.random_subject(shapes, level=level)
    check(pairs and made['level'] == level and (equations.text(made), made['subject']) in
          [(f, l) for f, l in pairs], 'level %d: %d formula/letter pairs' % (level, len(pairs)))
twice = equations.read('ax + b = cx + d', letters='abcdx')
check(equations.subject_level(twice, 'x') == 3 and equations.subject_level(twice, 'b') == 1,
      'ax + b = cx + d: x is level 3, b is level 1')

# Random equations: every form, whole-number answers, no x cancelling
rng = random.Random(7)
for form in equations.FORMS + equations.BRACKET_FORMS:
    for _ in range(200):
        made = equations.random_equation(rng, form)
        value = equations.answer(made)
        if value.denominator != 1 or value == 0:
            check(False, '%s gave %s for %s' % (form, value, equations.text(made)))
            break
        if equations.read(equations.text(made)) != made and '0' not in equations.text(made):
            check(False, 'text/read round trip for %s' % equations.text(made))
            break
    else:
        check(True, '%s: 200 equations, whole answers' % form)

# The page
html = page.board_html(shape)
check('data-ak-board=' in html and '&quot;' in html, 'board html carries escaped JSON')
for name in page.SCRIPTS + page.STYLES:
    check(os.path.isfile(os.path.join(page.WEB, name)), 'ships web/' + name)
try:
    extras = page.page_extras()
    check('AlgebraEngine' in extras and 'data-ak-board' in extras, 'extras carry engine and board')
    check('</style><script>' in extras and extras.endswith('</script><style>'), 'style tag trick')
    check('KaTeX_Main-Regular.woff2' not in extras, 'main fonts inlined')
    css, js = page.board_assets()
    check('AlgebraEngine' in js and 'katex.render' in js and 'ak-board' in css and css in extras,
          'board assets for pages that bring their own KaTeX')
except page.MissingKatex as error:
    check(False, str(error))

print('%d failed' % len(failures) if failures else 'all passed')
if failures:
    raise SystemExit(1)
