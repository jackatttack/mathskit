"""Smoke test: lessons hand algebrakit boards to Your move where they can.

    RUN projects/mathskit/tests/smoke_boards.py

Draws 30 problems from every stage of the lessons that use boards and
counts how many carry one. Every board must be well formed: equations
have an answer, expressions have a goal. Prints a table per stage.
"""
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
for name in list(sys.modules):
    if name.split('.')[0] in ('mathskit', 'algebrakit'):
        del sys.modules[name]

from mathskit import boards, lessons  # noqa: E402

SEEDS = 30
USING = ('linear', 'like_terms', 'brackets')
failures = []


def check(ok, what):
    print(('ok   ' if ok else 'FAIL ') + what)
    if not ok:
        failures.append(what)


check(boards.available(), 'algebrakit found beside mathskit')
check('AlgebraEngine' in boards.SCRIPT and 'ak-board' in boards.CSS, 'board script and styles ready')

from algebrakit import equations  # noqa: E402  (found by boards)

for key in USING:
    lesson = lessons.find(key)
    with_board = 0
    for stage in lesson.stages:
        count = 0
        missed = []     # equations the board turned down: what the next wave must read
        for seed in range(SEEDS):
            problem = stage.problem(rng=random.Random(seed))
            shape = getattr(problem, 'board', None)
            if not shape:
                if problem.equation and len(missed) < 3:
                    missed.append(problem.equation)
                continue
            count += 1
            if shape['right'] is None:
                if shape.get('goal') not in ('simplify', 'expand', 'factorise'):
                    check(False, '%s/%s seed %d: expression without a goal' % (key, stage.key, seed))
            else:
                try:
                    equations.answer(shape)
                except ValueError as error:
                    check(False, '%s/%s seed %d: %s' % (key, stage.key, seed, error))
            if '<div class="ak-board"' not in boards.html(shape):
                check(False, '%s/%s: no board html' % (key, stage.key))
        print('     %-12s %-22s %2d/%d with a board' % (key, stage.key, count, SEEDS))
        for text in missed:
            print('         no board: %s' % text)
        with_board += count
    check(with_board > 0, '%s: boards on offer' % key)

print('%d failed' % len(failures) if failures else 'all passed')
if failures:
    raise SystemExit(1)
