"""Maths: a Toolbox tool for teaching maths, one lesson at a time.

Pages:
    Lessons   every lesson (mathskit.lessons); Open teaches it
    Lesson    the lesson as a ladder of stages: the idea, a worked example,
              Question, and Your move where it fits
    Facts     the lesson's key facts and formulae, tap Show to reveal
    Bank      mathsgen's question bank, for anything no lesson covers yet
    Charts    statistical charts from Pokémon and countries data: read them,
              finish drawing them, answer questions (mathskit.charts)
    Algebra   an algebrakit board on its own: equations, brackets, expand,
              factorise, letters, change the subject (when algebrakit is found)

Built for a shared screen: a teacher and a student look at it together, so
answers stay hidden until revealed. Opened from the hub through
Toolbox/tools/maths.json, or run this file by hand.
"""
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
# While mathskit is young: always load the latest edit of it.
for name in list(sys.modules):
    if name.split('.')[0] in ('mathskit', 'algebrakit'):
        del sys.modules[name]

import editorkit as ek  # noqa: E402
from editorkit.web import cards, prose  # noqa: E402
from editorkit.web import tiles as web_tiles  # noqa: E402

from mathskit import (blocks, boards, chart_page, charts, datasets, explore, graph, joins,  # noqa: E402
                      lessons, questions, typeset)

# algebrakit's question maker for the Algebra page. boards has already put
# algebrakit on the path when it can be found; without it there is no page.
try:
    from algebrakit import equations as algebra_equations  # noqa: E402
except ImportError:
    algebra_equations = None

TITLE = 'Maths'
EMOJI = '\U0001f9ee'
WINDOW_KEY = 'mathskit'
FIRST_PAGE = 'Lesson'
AREA_ORDER = ('Number', 'Algebra', 'Graphs', 'Geometry', 'Probability', 'Statistics')
AREA_COLOURS = {'Number': '#f0883e', 'Algebra': '#58a6ff', 'Graphs': '#3fb950',
                'Geometry': '#bc8cff', 'Probability': '#e3b341', 'Statistics': '#ff7b72'}
OTHER_COLOUR = '#8b949e'
SEARCH_BOX = ('<input class="mk-search" type="search" placeholder="Search lessons" '
              'autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false" '
              'style="width:100%;box-sizing:border-box;font-size:17px;padding:10px 12px;'
              'border-radius:10px;border:1px solid rgba(128,128,128,0.4);'
              'background:transparent;color:inherit;margin:4px 0 8px">')


def button_row(go, buttons, scroll=False):
    """A row of page buttons. buttons are (label, item, highlighted); each
    tap comes back to the page's on_pick as item. scroll brings the row
    into view after a redraw."""
    spans = ['<span class="mk-btn%s" %s>%s</span>'
             % (' mk-go' if highlighted else '', go(item), blocks.escape(label))
             for label, item, highlighted in buttons]
    mark = ' data-mk-scroll="1"' if scroll else ''
    return '<div class="mk-controls"%s>%s</div>' % (mark, ''.join(spans))


def figure_html(figure):
    """A problem's figure: inline SVG, or a lesson.Plot drawn as a graph."""
    if figure is None:
        return ''
    if isinstance(figure, str):
        return '<div class="mk-fact-figure" style="margin:10px 0">%s</div>' % figure
    drawn = graph.Graph(**figure.window())
    for curve in figure.curves:
        drawn.curve(curve)
    return blocks.graph(drawn)


def diagram_html(figure):
    """An SVG diagram belongs to the question: shown before the working."""
    return figure_html(figure) if isinstance(figure, str) else ''


def plot_html(figure):
    """A plotted graph is part of the answer: shown after the working."""
    return figure_html(figure) if figure is not None and not isinstance(figure, str) else ''


def tint(colour, alpha):
    """'#58a6ff' at alpha, as rgba()."""
    red, green, blue = (int(colour[index:index + 2], 16) for index in (1, 3, 5))
    return 'rgba(%d,%d,%d,%.2f)' % (red, green, blue, alpha)


def area_heading(area):
    colour = AREA_COLOURS.get(area, OTHER_COLOUR)
    return ('<div style="display:flex;align-items:center;gap:10px;margin:22px 0 4px">'
            '<span style="width:12px;height:12px;border-radius:50%%;background:%s"></span>'
            '<span style="font-size:23px;font-weight:700;color:%s">%s</span></div>'
            % (colour, colour, blocks.escape(area)))


# --- Lessons ------------------------------------------------------------------

class LessonsPage:
    """The Lessons page: every lesson with its ladder of stages. Open hands
    the lesson to on_open, which teaches it on the Lesson and Facts pages."""

    def __init__(self, window, extras, on_open):
        self.tile = web_tiles.Cards(window, on_pick=self.picked,
                                    zoom_key='mathskit-lessons', extra_css=extras)
        self.on_open = on_open

    def picked(self, item):
        """('open', lesson) from a title, ('open', lesson, stage) from a pill."""
        if isinstance(item, tuple) and item[0] == 'open':
            stage = item[2] if len(item) > 2 else None
            self.on_open(lessons.find(item[1]), stage)

    def show(self, teaching):
        page = cards.Page()
        parts = [prose.heading('Lessons', 1), SEARCH_BOX]
        areas = []
        for lesson in lessons.ALL:
            if (lesson.area or 'Other') not in areas:
                areas.append(lesson.area or 'Other')
        areas.sort(key=lambda area: AREA_ORDER.index(area) if area in AREA_ORDER
                   else len(AREA_ORDER))
        for area in areas:
            area_cards = [self.card(page, lesson, lesson is teaching)
                          for lesson in lessons.ALL if (lesson.area or 'Other') == area]
            parts.append('<div class="mk-area">%s%s</div>'
                         % (area_heading(area), ''.join(area_cards)))
        page.prose(*parts)
        self.tile.show(page)

    def card(self, page, lesson, now):
        """One lesson as a card in its area's colour: the title (tap to open
        at the first stage) and its stages as pills (tap to open at that
        stage). data-search holds every word the search box matches. The
        lesson being taught has a full coloured border and a mark."""
        colour = AREA_COLOURS.get(lesson.area, OTHER_COLOUR)
        words = [lesson.title, lesson.area] + list(lesson.keywords)
        words += [stage.title for stage in lesson.stages]
        pills = ''.join('<span %s style="display:inline-block;font-size:14px;padding:5px 11px;'
                        'margin:5px 6px 0 0;border-radius:999px;background:%s;color:%s">%s</span>'
                        % (page.go(('open', lesson.key, stage.key)), tint(colour, 0.16), colour,
                           blocks.escape(stage.title))
                        for stage in lesson.stages)
        border = ('2px solid %s' % colour) if now else ('1px solid %s' % tint(colour, 0.35))
        mark = ('<span style="font-size:12px;font-weight:600;color:%s;margin-left:8px">'
                '\u25cf teaching</span>' % colour) if now else ''
        return ('<div class="mk-lesson" data-search="%s" style="border:%s;border-left:6px solid %s;'
                'border-radius:14px;background:%s;padding:12px 14px 13px;margin:10px 0">'
                '<div %s style="font-size:19px;font-weight:650">%s%s</div>'
                '<div>%s</div></div>'
                % (blocks.escape(' '.join(words).lower()), border, colour, tint(colour, 0.06),
                   page.go(('open', lesson.key)), blocks.escape(lesson.title), mark, pills))


# --- Lesson -------------------------------------------------------------------

class LessonPage:
    """The Lesson page: one lesson as a ladder of stages (mathskit.lessons).

    Pick a stage, read its idea, step through a worked example, and grab a
    question at the same stage any time. A question shows only its first
    line until Next or Show all, so the answer stays hidden until you
    choose. Your move opens under a question when the stage allows it.
    Every example and question is a fresh draw from the stage's generator.
    """

    def __init__(self, window, extras, lesson):
        self.tile = web_tiles.Cards(window, on_pick=self.picked,
                                    zoom_key='mathskit-lesson', extra_css=extras)
        self.rng = random.Random()
        self.lesson = None
        self.stage = None
        self.example = None
        self.question = None
        self.game = None           # Your move on the question, while open
        self.board_open = False    # Your move as a touch board (algebrakit), while open
        self.question_figure = False   # the question's graph, once asked for
        self.set_lesson(lesson)

    # --- What the buttons do --------------------------------------------------

    def set_lesson(self, lesson, stage_key=None):
        self.lesson = lesson
        self.go_to(lesson.stage(stage_key) if stage_key else lesson.stages[0])

    def go_to(self, stage):
        self.stage = stage
        self.question = None
        self.game = None
        self.board_open = False
        self.new_example()

    def new_example(self):
        self.example = self.stage.problem(rng=self.rng)
        self.show()

    def new_question(self):
        self.question = self.stage.problem(rng=self.rng)
        self.game = None
        self.board_open = False
        self.question_figure = False
        self.show(scroll_to_question=True)

    def toggle_your_move(self):
        """Your move: the touch board when the question has one (algebrakit),
        else the button explorer. A second tap closes either."""
        was_open = self.game is not None or self.board_open
        self.game = None
        self.board_open = False
        if not was_open and self.question is not None:
            if self.question.board:
                self.board_open = True
            elif self.question.equation:
                self.game = explore.Explorer(self.question.equation)
        self.show(scroll_to_question=True)

    def picked(self, item):
        if isinstance(item, tuple) and item[0] == 'stage':
            self.go_to(self.lesson.stage(item[1]))
        elif item == 'easier':
            self.go_to(self.lesson.easier(self.stage))
        elif item == 'harder':
            self.go_to(self.lesson.harder(self.stage))
        elif item == 'example':
            self.new_example()
        elif item == 'question':
            self.new_question()
        elif item == 'your_move':
            self.toggle_your_move()
        elif item == 'figure':
            self.question_figure = not self.question_figure
            self.show(scroll_to_question=True)
        elif isinstance(item, tuple) and item[0] == 'move' and self.game is not None:
            self.show(fresh=self.game.play(item[1]), keep_bottom=True)
        elif item in ('undo', 'restart') and self.game is not None:
            getattr(self.game, item)()
            self.show(keep_bottom=True)

    # --- The page -------------------------------------------------------------

    def show(self, fresh=False, scroll_to_question=False, keep_bottom=False):
        page = cards.Page()
        stage_buttons = [(stage.title, ('stage', stage.key), stage is self.stage)
                         for stage in self.lesson.stages]
        parts = [prose.heading(self.lesson.title, 1),
                 button_row(page.go, stage_buttons),
                 prose.heading(self.stage.title, 2),
                 blocks.text(self.stage.idea),
                 blocks.text('**Worked example**'),
                 diagram_html(self.example.figure),
                 blocks.steps(self.example.solution),
                 plot_html(self.example.figure)]
        # The question is the point of the screen, so the example carries one
        # way on: Question. Once a question shows, its own New question draws
        # the next, and the stage pills at the top change the level.
        if self.question is None:
            parts.append(button_row(page.go, [('Question \u25b6', 'question', True)]))
        else:
            parts += self.question_parts(page, fresh, scroll_to_question)
        if keep_bottom:
            parts.append('<div data-mk-bottom="1"></div>')
        page.prose(*parts)
        self.tile.show(page)

    def question_parts(self, page, fresh, scroll):
        """The question under the worked example.

        With a board (algebrakit), the board is the question: it opens ready
        to touch, with no written copy above it and no Your move to tap, so
        the maths sits centre stage. Without one, the question steps through
        like the example and Your move opens the button explorer where it
        fits.
        """
        buttons = [('New question', 'question', False)]
        if self.question.figure is not None and not isinstance(self.question.figure, str):
            buttons.append(('Hide graph' if self.question_figure else 'Show graph',
                            'figure', False))
        landing = '<div data-mk-land="1"></div>' if scroll and not fresh else ''
        if self.question.board:
            return [landing + prose.heading('Question', 2),
                    diagram_html(self.question.figure),
                    boards.html(self.question.board),
                    plot_html(self.question.figure) if self.question_figure else '',
                    button_row(page.go, buttons)]
        if self.question.equation:
            showing = self.game is not None
            buttons.append(('Close Your move' if showing else 'Your move',
                            'your_move', not showing))
        parts = [landing + prose.heading('Question', 2),
                 diagram_html(self.question.figure),
                 blocks.steps(self.question.solution),
                 plot_html(self.question.figure) if self.question_figure else '',
                 button_row(page.go, buttons)]
        if self.game is not None:
            parts.append(blocks.explore(self.game, page.go, fresh=fresh, offer_new=False))
        return parts


# --- Facts --------------------------------------------------------------------

class FactsPage:
    """The Facts page: the lesson's key facts and formulae (lesson.Fact).
    Show reveals a card in the page and Show all reveals every card, with
    no Python round trip, so the page stays where it is."""

    def __init__(self, window, extras):
        self.tile = web_tiles.Cards(window, zoom_key='mathskit-facts', extra_css=extras)

    def show(self, lesson):
        page = cards.Page()
        parts = [prose.heading(lesson.title, 1), blocks.text('**Key facts**')]
        if not lesson.facts:
            parts.append(blocks.text('No facts written for this lesson yet.'))
        else:
            parts.append('<div class="mk-controls">'
                         '<span class="mk-btn" data-mk="flip_all">Show all</span></div>')
            parts += [blocks.fact(item) for item in lesson.facts]
        page.prose(*parts)
        self.tile.show(page)


# --- Bank ---------------------------------------------------------------------

class Questions:
    """The Bank page: a mathsgen question card. Each button comes back
    through picked(), moves the deck on, and shows the card again."""

    def __init__(self, window, extras):
        self.tile = web_tiles.Cards(window, on_pick=self.picked,
                                    zoom_key='mathskit-questions', extra_css=extras)
        self.deck = questions.Deck()
        self.extra = None          # 'solve' or 'graph' while one is open under the card
        self.game = None           # the Your move game for Solve it here
        self.joined = (None, None, None)   # (question id, solvable text, graph) for the card
        self.show()

    def joins(self):
        """(solvable text, graph) for the question showing, worked out once."""
        question = self.deck.question
        key = question.id if question is not None else None
        if self.joined[0] != key:
            text = joins.solvable(question) if question is not None else None
            figure = joins.graph_for(question) if question is not None else None
            self.joined = (key, text, figure)
        return self.joined[1], self.joined[2]

    def open_extra(self, kind):
        if self.extra == kind:
            self.extra = None
            return
        text, figure = self.joins()
        if kind == 'solve' and text:
            self.game = explore.Explorer(text)
            self.extra = 'solve'
        elif kind == 'graph' and figure is not None:
            self.extra = 'graph'

    def picked(self, item):
        deck = self.deck
        moves = {'another': deck.another, 'harder': deck.harder, 'easier': deck.easier,
                 'random': deck.random}
        menu = {'all': deck.clear, 'all_grades': deck.clear_bands}
        if item in moves:
            moves[item]()
            self.extra = None
            self.show()
        elif item in ('solve', 'graph'):
            self.open_extra(item)
            self.show()
        elif isinstance(item, tuple) and item[0] == 'move' and self.game is not None:
            self.show(fresh=self.game.play(item[1]))
        elif item in ('undo', 'restart') and self.game is not None:
            getattr(self.game, item)()
            self.show()
        elif item in menu:
            menu[item]()
            self.pool_changed()
        elif isinstance(item, tuple) and item[0] == 'toggle':
            deck.toggle(item[1])
            self.pool_changed()
        elif isinstance(item, tuple) and item[0] == 'band':
            deck.toggle_band(item[1])
            self.pool_changed()

    def pool_changed(self):
        """The page has already flipped the chip; only the pool line needs
        the new name and count. No redraw, so the page stays where it is."""
        self.tile.run('window.qcPool && qcPool(%s, %d)'
                      % (json.dumps(self.deck.pool_name()), len(self.deck.pool())))

    def show(self, menu_open=False, fresh=False):
        page = cards.Page()
        text, figure = self.joins()
        buttons = []
        if text:
            buttons.append(('Close solver' if self.extra == 'solve' else 'Solve it here', 'solve'))
        if figure is not None:
            buttons.append(('Close graph' if self.extra == 'graph' else 'Graph it', 'graph'))
        below = ''
        if self.extra == 'solve' and self.game is not None:
            below = blocks.explore(self.game, page.go, fresh=fresh, offer_new=False)
        elif self.extra == 'graph' and figure is not None:
            below = blocks.graph(figure)
        page.prose(blocks.question(self.deck, page.go, menu_open, buttons, below))
        self.tile.show(page)


# --- Algebra ------------------------------------------------------------------

ALGEBRA_TASKS = {'expand': 'Expand and simplify', 'factorise': 'Factorise fully',
                 'simplify': 'Simplify'}
ALGEBRA_HOW = ('Drag a term across = or onto a like term. Drag what multiplies a letter '
               'across to divide. Drag a bracket\'s number into it to expand. Tap = to '
               'swap sides.')


class AlgebraPage:
    """The Algebra page: one algebrakit board at a time, for practice outside
    any lesson (the same boards as algebrakit's lab). Each button deals a
    fresh board of its kind; tapping the lit one deals another. The board
    plays entirely in the page, so Python only redraws for a new one."""

    KINDS = (('equation', 'Equation'), ('brackets', 'Brackets'), ('expand', 'Expand'),
             ('factorise', 'Factorise'), ('letters', 'Letters'), ('subject', 'Subject'),
             ('twice', 'Subject twice'))

    def __init__(self, window, extras):
        self.tile = web_tiles.Cards(window, on_pick=self.picked,
                                    zoom_key='mathskit-algebra', extra_css=extras)
        self.rng = random.Random()
        self.kind = 'equation'
        self.shape = self.deal(self.kind)
        self.show()

    def deal(self, kind):
        """A fresh board shape of one kind, from algebrakit.equations."""
        make = algebra_equations
        if kind == 'brackets':
            return make.random_equation(self.rng, self.rng.choice(make.BRACKET_FORMS))
        if kind in ('expand', 'factorise'):
            forms = make.EXPAND_FORMS if kind == 'expand' else make.FACTORISE_FORMS
            return make.random_expression(self.rng, self.rng.choice(forms))
        if kind == 'letters':
            return make.random_lettered(self.rng)
        if kind == 'subject':
            return make.random_subject(self.rng, level=self.rng.choice((1, 2)))
        if kind == 'twice':
            return make.random_subject(self.rng, level=3)
        return make.random_equation(self.rng)

    def picked(self, item):
        if item in dict(self.KINDS):
            self.kind = item
            self.shape = self.deal(item)
            self.show()

    def task(self):
        if self.shape.get('subject'):
            return 'Make %s the subject' % self.shape['subject']
        return ALGEBRA_TASKS.get(self.shape.get('goal'), '')

    def show(self):
        page = cards.Page()
        buttons = [(label, kind, kind == self.kind) for kind, label in self.KINDS]
        task = self.task()
        page.prose(prose.heading('Algebra', 1),
                   button_row(page.go, buttons),
                   '<p style="color:var(--muted);margin:2px 0 6px">%s</p>'
                   % blocks.escape(ALGEBRA_HOW),
                   ('<p style="font-size:19px;font-weight:650;margin:10px 0 0">%s</p>'
                    % blocks.escape(task)) if task else '',
                   boards.html(self.shape))
        self.tile.show(page)


# --- Charts -------------------------------------------------------------------

class ChartsPage:
    """The Charts page: statistical charts from real data (Pokémon and
    countries) to read, finish drawing and answer questions on.

    Chips across the top choose the data, the chart, the part of the data
    (a generation, a continent), what is measured, and Read it or Draw it.
    Each chip deals a fresh chart from mathskit.charts; New data deals
    another of the same. Everything after that (taps, drags, Check,
    questions) happens in the page (chart_page.py), so nothing jumps.
    """

    def __init__(self, window, extras):
        self.tile = web_tiles.Cards(window, on_pick=self.picked, zoom_key='mathskit-charts',
                                    extra_css=extras, extra_js=typeset.page_js())
        self.rng = random.Random()
        found = datasets.available()
        self.source_key = found[0] if found else 'pokemon'
        self.kind = 'bar'
        self.mode = 'look'
        self.scope = None
        self.measure = None
        self.deal()

    def deal(self):
        """A fresh chart for the current chips, or a message saying why not."""
        self.made = None
        self.problem = None
        try:
            source = datasets.load(self.source_key)
            self.made = charts.deal(source, self.kind, self.scope, self.measure, self.mode, self.rng)
        except (datasets.MissingData, charts.NotEnoughData) as error:
            self.problem = str(error)
        self.show()

    def picked(self, item):
        if item == 'new':
            return self.deal()
        if not isinstance(item, tuple):
            return
        what, value = item
        if what == 'source':
            self.source_key, self.scope, self.measure = value, None, None
        elif what == 'kind':
            self.kind, self.measure = value, None
        elif what == 'scope':
            self.scope = value
        elif what == 'measure':
            self.measure = value
        elif what == 'mode':
            self.mode = value
        self.deal()

    def show(self):
        page = cards.Page()
        scopes = charts.scopes_for(self.source_key)
        recipes = charts.recipes_for(self.source_key, self.kind)
        scope = self.scope or scopes[0][0]
        measure = self.measure or recipes[0][0]
        rows = [
            [(datasets.TITLES[key], ('source', key), key == self.source_key) for key in datasets.FILES],
            [(label, ('kind', kind), kind == self.kind) for kind, label in charts.KINDS],
            [(label, ('scope', key), key == scope) for key, label in scopes],
        ]
        if len(recipes) > 1:
            rows.append([(label, ('measure', key), key == measure) for key, label in recipes])
        rows.append([(label, ('mode', key), key == self.mode) for key, label in charts.MODES]
                    + [('New data ▶', 'new', False)])
        parts = [prose.heading('Charts', 1)] + [button_row(page.go, row) for row in rows]
        if self.made is not None:
            sprites = datasets.sprites(chart_page.sprite_numbers(self.made))
            parts.append(chart_page.html(self.made, sprites))
        else:
            parts.append(blocks.text(self.problem or 'Nothing to show.'))
        page.prose(*parts)
        self.tile.show(page)
# --- Not on a tab: kept to reuse in a graphs lesson ----------------------------

def graphs_page():
    """Graphs to play with: lines, completed square form, stretching, and
    two lines meeting at an equation's answer."""
    lines = graph.Graph(x=(-10, 10), square=True, title='Straight lines')
    lines.curve('m x + c')
    lines.slider('m', -5, 5, value=2, step=0.5)
    lines.slider('c', -10, 10, value=1, step=1)

    vertex = graph.Graph(x=(-6, 6), y=(-8, 10), title='Completed square form')
    vertex.curve('a (x - h)^2 + k')
    vertex.slider('a', -3, 3, value=1, step=0.25)
    vertex.slider('h', -5, 5, value=0, step=0.5)
    vertex.slider('k', -6, 6, value=0, step=0.5)

    waves = graph.Graph(x=(-6.3, 6.3), y=(-4, 4), title='Stretching sin x')
    waves.transform('sin(x)')

    meet = graph.Graph(x=(-8, 4), title='Where the lines meet')
    meet.curve('2x - 24')
    meet.curve('5x - 15')

    page = cards.Page()
    page.prose(
        prose.heading('Graphs', 1),
        blocks.text('Drag a slider and the graph follows. Tap a graph to trace it.'),
        blocks.graph(lines),
        blocks.text('$m$ is the gradient: how far up for one step across. $c$ is where the '
                    'line crosses the $y$ axis.'),
        blocks.graph(vertex),
        blocks.text('The turning point is at $(h, k)$. A negative $a$ turns it upside down.'),
        blocks.graph(waves),
        blocks.text('$a$ stretches it up and down; $b$ squashes it across.'),
        prose.heading('Solving with a graph', 2),
        blocks.text('$2x - 24 = 5x - 15$ is true where the two lines meet. Tap near the '
                    'crossing: it is at $x = -3$.'),
        blocks.graph(meet))
    return page


# --- The window ---------------------------------------------------------------

def main():
    """Open the Maths window over the code (or bring it back)."""
    ek.require('0.7.0', 'Maths')     # the Charts page runs as extra_js
    window = ek.Window(TITLE, emoji=EMOJI, key=WINDOW_KEY)
    extras = typeset.page_extras()
    first = lessons.ALL[0]
    lesson_page = LessonPage(window, extras, first)
    facts_page = FactsPage(window, extras)
    bank = Questions(window, extras)

    def open_lesson(lesson, stage_key=None):
        """Teach lesson (at stage_key, or its first stage): the Lesson and
        Facts pages follow it."""
        lesson_page.set_lesson(lesson, stage_key)
        facts_page.show(lesson)
        lessons_page.show(lesson)
        window.set_page('Lesson')

    lessons_page = LessonsPage(window, extras, open_lesson)
    lessons_page.show(first)
    facts_page.show(first)
    window.add_page('Lessons', lessons_page.tile)
    window.add_page('Lesson', lesson_page.tile)
    window.add_page('Facts', facts_page.tile)
    window.add_page('Bank', bank.tile)
    # Charts only where the datasets are (here or in iCloud): they never ship.
    if datasets.available():
        charts_page = ChartsPage(window, extras)
        window.add_page('Charts', charts_page.tile)
    if algebra_equations is not None:
        algebra = AlgebraPage(window, extras)
        window.add_page('Algebra', algebra.tile)
    window.set_page(FIRST_PAGE)
    window.show()
    return window


if __name__ == '__main__':
    ek.run_tool(main)
