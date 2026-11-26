"""Statistical charts to teach from: a dataset in, a chart with questions out.

Role: clean, contracts · Part of: mathskit/charts · Pure

    from mathskit import charts, datasets
    deal = charts.deal(datasets.load('pokemon'), kind='bar', scope='g1',
                       measure='type1', mode='look', rng=random.Random())

A Deal is a plain dict (so it goes to the page as JSON):

    kind        'bar', 'pie', 'histogram', 'cumulative', 'box' or 'scatter'
    mode        'look' (read it and answer) or 'complete' (finish drawing it)
    title       what the chart shows, in words
    note        one line under the title: where the data came from
    task        complete mode only: what to do, in a few words
    chart       the drawing spec chart_page's script reads (CHART SPECS below)
    table       {'headers': [...], 'rows': [[...], ...]} or None
    values      box plot complete mode: the data values to read, else None
    questions   [{'ask': str, 'options': [str], 'answer': index, 'why': str}]

CHART SPECS (every number already worked out here; the page only draws):

    bar         labels, values, y [start, end, step], hidden [bar indices],
                x_label, y_label
    histogram   variants [{width, edges, counts, y}], current (variant index),
                hidden [bar indices, current variant], x_label, y_label
    pie         labels, values, angles (degrees, sum 360), hidden [boundary
                indices: boundary i sits between sector i-1 and sector i]
    cumulative  points [[x, cf], ...] starting at cf 0, total, x and y axes,
                hidden [point indices], x_label, y_label
    box         groups [{name, five: [min, lq, median, uq, max]}], x axis,
                complete (true: group 0's five markers are dragged), snap
    scatter     points [{x, y, name}], hidden [point indices], x and y axes,
                snap [x, y], fit [gradient, intercept] or None, x_label, y_label

Raises NotEnoughData when a scope has too little data for the chart.
GCSE Foundation first: small samples, friendly totals (pie teams of 12, 18,
24 or 36), equal class widths. tests/smoke_charts.py deals every
combination at many seeds and checks each answer is among its options.
"""
import math

from . import stats

KINDS = (('bar', 'Bar chart'), ('pie', 'Pie chart'), ('histogram', 'Histogram'),
         ('cumulative', 'Cumulative frequency'), ('box', 'Box plot'), ('scatter', 'Scatter graph'))
MODES = (('look', 'Read it'), ('complete', 'Draw it'))

# ---- Settings (editable) ---------------------------------------------------------

# Scopes: (key, chip label, what it keeps). Pokémon keep generations;
# countries keep a continent (None keeps everything).
SCOPES = {
    'pokemon': (('g1', 'Gen 1', {1}), ('g2', 'Gen 2', {2}), ('g3', 'Gen 3', {3}),
                ('g4', 'Gen 4', {4}), ('g13', 'Gen 1–3', {1, 2, 3}), ('all', 'All', None)),
    'countries': (('world', 'World', None), ('Africa', 'Africa', 'Africa'), ('Asia', 'Asia', 'Asia'),
                  ('Europe', 'Europe', 'Europe'), ('North America', 'N America', 'North America'),
                  ('South America', 'S America', 'South America'), ('Oceania', 'Oceania', 'Oceania')),
}

# Numbers a chart can use: key -> (axis label, short name, column, divide by).
NUMBERS = {
    'pokemon': {
        'speed': ('Speed', 'speed', 'speed', 1),
        'attack': ('Attack', 'attack', 'attack', 1),
        'hp': ('HP', 'HP', 'hp', 1),
        'defence': ('Defence', 'defence', 'defence', 1),
        'height_m': ('Height (m)', 'height', 'height_m', 1),
        'weight_kg': ('Weight (kg)', 'weight', 'weight_kg', 1),
    },
    'countries': {
        'life_expectancy': ('Life expectancy (years)', 'life expectancy', 'life_expectancy', 1),
        'urban_percent': ('Living in towns and cities (%)', 'percentage in towns', 'urban_percent', 1),
        'gdp_thousands': ('Income per person ($ thousands)', 'income per person', 'gdp_per_person_usd', 1000),
        'population_millions': ('Population (millions)', 'population', 'population', 1000000),
    },
}

# What each chart can show, first is the default: (measure key, chip label).
RECIPES = {
    'pokemon': {
        'bar': (('type1', 'Type'), ('colour', 'Colour')),
        'pie': (('colour', 'Colour'), ('type1', 'Type')),
        'histogram': (('speed', 'Speed'), ('attack', 'Attack'), ('hp', 'HP')),
        'cumulative': (('speed', 'Speed'), ('attack', 'Attack'), ('hp', 'HP')),
        'box': (('speed', 'Speed'), ('attack', 'Attack'), ('hp', 'HP')),
        'scatter': (('height_m:weight_kg', 'Height & weight'), ('attack:defence', 'Attack & defence'),
                    ('speed:weight_kg', 'Speed & weight')),
    },
    'countries': {
        'bar': (('place', 'Countries per place'), ('life_expectancy', 'Life expectancy'),
                ('population_millions', 'Population')),
        'pie': (('place', 'Where they are'),),
        'histogram': (('life_expectancy', 'Life expectancy'), ('urban_percent', 'Towns and cities'),
                      ('gdp_thousands', 'Income')),
        'cumulative': (('life_expectancy', 'Life expectancy'), ('urban_percent', 'Towns and cities')),
        'box': (('life_expectancy', 'Life expectancy'), ('urban_percent', 'Towns and cities')),
        'scatter': (('gdp_thousands:life_expectancy', 'Income & life'),
                    ('urban_percent:life_expectancy', 'Towns & life'),
                    ('population_millions:life_expectancy', 'Population & life')),
    },
}

# Histogram and cumulative frequency class widths: the first is the default.
CLASS_WIDTHS = {'speed': (20, 10, 40), 'attack': (20, 10, 40), 'hp': (20, 10, 40),
                'life_expectancy': (5, 2, 10), 'urban_percent': (10, 20, 5),
                'gdp_thousands': (10, 20, 5)}

BAR_COUNT = 6                    # bars on a bar chart
PIE_TEAMS = (12, 18, 24, 36)     # pie sample sizes: 360 divides each nicely
PIE_SECTORS = 5                  # most sectors before the rest join 'Other'
CUMULATIVE_SAMPLE = 40           # values behind a cumulative frequency graph
BOX_SAMPLE = 11                  # Draw it box plots: quartiles land on values 3, 6 and 9
BOX_SMALLEST_GROUP = 8           # a box plot group needs this many values
SCATTER_SAMPLE = 15              # points on a scatter graph
SCATTER_HIDDEN = 4               # points to plot in Draw it
SCATTER_LIMITS = {'weight_kg': 150, 'height_m': 2.5, 'population_millions': 150}   # leave out giants

# Words for each dataset's things.
THING = {'pokemon': ('Pokémon', 'Pokémon'), 'countries': ('country', 'countries')}
SOURCE_NOTES = {'pokemon': 'Base stats from PokeAPI.',
                'countries': 'World Bank figures, most recent year.'}

# ---- Contracts -----------------------------------------------------------------------


class NotEnoughData(ValueError):
    """The chosen scope has too little data for this chart."""


def question(ask, options, answer, why):
    """One tap-to-answer question. answer is the index of the right option."""
    return {'ask': ask, 'options': [str(option) for option in options], 'answer': answer, 'why': why}


def recipes_for(source_key, kind):
    return RECIPES[source_key][kind]


def scopes_for(source_key):
    return [(key, label) for key, label, _ in SCOPES[source_key]]


# ---- The entry point -------------------------------------------------------------------


def deal(source, kind, scope=None, measure=None, mode='look', rng=None):
    """A fresh chart of kind from source (a datasets.Source) with questions."""
    import random
    rng = rng or random.Random()
    builders = {'bar': bar_chart, 'pie': pie_chart, 'histogram': histogram,
                'cumulative': cumulative, 'box': box_plot, 'scatter': scatter}
    scope = scope or SCOPES[source.key][0][0]
    measure = measure or recipes_for(source.key, kind)[0][0]
    rows = rows_in_scope(source, scope)
    made = builders[kind](source, rows, scope, measure, mode, rng)
    made.setdefault('note', SOURCE_NOTES.get(source.key, ''))
    made.setdefault('table', None)
    made.setdefault('values', None)
    made.setdefault('task', '')
    made['kind'] = kind
    made['mode'] = mode
    return made


# ---- Picking data ----------------------------------------------------------------------


def rows_in_scope(source, scope):
    for key, _, keep in SCOPES[source.key]:
        if key == scope:
            break
    else:
        raise KeyError('No scope %r for %s' % (scope, source.key))
    if keep is None:
        return list(source.rows)
    if source.key == 'pokemon':
        return [row for row in source.rows if row['generation'] in keep]
    return [row for row in source.rows if row['continent'] == keep]


def scope_words(source, scope):
    for key, label, keep in SCOPES[source.key]:
        if key == scope:
            if source.key == 'pokemon':
                return 'every generation' if keep is None else label
            return 'the world' if keep is None else keep
    return scope


def plain_number(source, row, measure):
    """A row's value of measure in the chart's units, or None when blank."""
    _, _, column, divide = NUMBERS[source.key][measure]
    value = row.get(column)
    return None if value is None else value / divide


def axis_label(source, measure):
    return NUMBERS[source.key][measure][0]


def short_name(source, measure):
    return NUMBERS[source.key][measure][1]


def label_of(row):
    return row.get('name', '?')


def category(source, row, measure, scope):
    """The group a row falls in for a bar or pie chart."""
    if measure == 'place':
        return row['continent'] if scope == 'world' else (row['subregion'] or row['continent'])
    return row.get(measure) or 'None'


def place_word(scope):
    return 'continent' if scope == 'world' else 'region'


# ---- Options ---------------------------------------------------------------------------


def number_options(rng, answer, spread, count=4, low=0, whole=True):
    """(options as text, index of answer): answer and count-1 nearby numbers,
    at least spread apart, none below low, in order smallest first."""
    spread = max(spread, 1 if whole else spread)
    if whole:
        answer = int(round(answer))
        spread = max(1, int(round(spread)))
    found = {answer}
    # Near misses first (one or two steps away), further ones only if needed.
    near = [-2, -1, 1, 2]
    far = [step for step in range(-count * 2, count * 2 + 1) if abs(step) > 2]
    rng.shuffle(near)
    rng.shuffle(far)
    for offset in near + far:
        if len(found) == count:
            break
        candidate = answer + offset * spread
        if candidate >= low:
            found.add(stats.tidy(candidate) if not whole else candidate)
    ordered = sorted(found)
    return [stats.number_text(value) for value in ordered], ordered.index(answer)


def word_options(rng, answer, others, count=4):
    """(options, index of answer): the answer and up to count-1 others, shuffled."""
    choices = [other for other in dict.fromkeys(others) if other != answer]
    rng.shuffle(choices)
    picked = choices[:count - 1] + [answer]
    rng.shuffle(picked)
    return picked, picked.index(answer)


def ask_number(rng, ask, answer, spread, why, low=0, whole=True):
    options, index = number_options(rng, answer, spread, low=low, whole=whole)
    return question(ask, options, index, why)


def ask_word(rng, ask, answer, others, why):
    options, index = word_options(rng, answer, others)
    return question(ask, options, index, why)


def unique_top(pairs, highest=True):
    """The label with the single biggest (or smallest) count, or None on a tie."""
    ordered = sorted(pairs, key=lambda pair: pair[1], reverse=highest)
    if len(ordered) > 1 and ordered[0][1] == ordered[1][1]:
        return None
    return ordered[0][0]


def hide_some(rng, size, how_many, first=0):
    """how_many indices from first..size-1, sorted."""
    pool = list(range(first, size))
    rng.shuffle(pool)
    return sorted(pool[:min(how_many, len(pool))])


# ---- Bar charts --------------------------------------------------------------------------


def bar_chart(source, rows, scope, measure, mode, rng):
    one, many = THING[source.key]
    if measure in ('type1', 'colour', 'place'):
        values = [category(source, row, measure, scope) for row in rows]
        pairs = stats.top_counts(values, BAR_COUNT)
        if len(pairs) < 3:
            raise NotEnoughData('Too few groups for a bar chart here.')
        pairs.sort(key=lambda pair: str(pair[0]))
        word = {'type1': 'type', 'colour': 'colour', 'place': place_word(scope)}[measure]
        title = 'Number of %s by %s in %s' % (many, word, scope_words(source, scope))
        if len(stats.counts(values)) > BAR_COUNT:
            title += ' (the %d most common)' % BAR_COUNT
        y_label = 'Number of %s' % many
        counting = True
    else:
        usable = [row for row in rows if plain_number(source, row, measure) is not None]
        if len(usable) < 4:
            raise NotEnoughData('Too few %s with that figure here.' % many)
        if measure == 'population_millions':
            usable.sort(key=lambda row: -row['population'])
            chosen = usable[:BAR_COUNT]
            title = 'The %d biggest populations in %s' % (len(chosen), scope_words(source, scope))
        else:
            chosen = rng.sample(usable, min(BAR_COUNT, len(usable)))
            title = '%s of %d %s' % (axis_label(source, measure).split(' (')[0], len(chosen), many)
        pairs = [(label_of(row), int(round(plain_number(source, row, measure)))) for row in chosen]
        word = short_name(source, measure)
        y_label = axis_label(source, measure)
        counting = False
    labels = [label for label, _ in pairs]
    values = [value for _, value in pairs]
    start, end, step = stats.nice_axis(0, max(values), lines=6, from_zero=True)
    hidden = hide_some(rng, len(values), 2) if mode == 'complete' else []
    spec = {'labels': labels, 'values': values, 'y': [start, end, step], 'hidden': hidden,
            'x_label': word.capitalize() if counting else '', 'y_label': y_label, 'snap': 1}
    made = {'title': title, 'chart': spec, 'questions': bar_questions(rng, pairs, counting, many, word)}
    if mode == 'complete':
        made['task'] = 'Drag the dashed bars up to the right height. The table has the numbers.'
    if mode == 'complete' or counting:
        heading = 'Frequency' if counting else y_label
        made['table'] = {'headers': [word.capitalize() if counting else one.capitalize(), heading],
                         'rows': [[label, stats.number_text(value)] for label, value in pairs]}
    return made


def bar_questions(rng, pairs, counting, many, word):
    found = []
    values = dict(pairs)
    labels = [label for label, _ in pairs]
    top = unique_top(pairs)
    if top is not None:
        if counting:
            found.append(ask_word(rng, 'Which %s has the most %s?' % (word, many), top, labels,
                                  'The tallest bar is %s, at %d.' % (top, values[top])))
        else:
            found.append(ask_word(rng, 'Which has the highest %s?' % word, top, labels,
                                  'The tallest bar is %s.' % top))
    low = unique_top(pairs, highest=False)
    if low is not None and counting:
        found.append(ask_word(rng, 'Which %s has the fewest %s?' % (word, many), low, labels,
                              'The shortest bar is %s, at %d.' % (low, values[low])))
    pick = rng.choice(labels)
    spread = max(1, int(round(max(values.values()) / 10)))
    if counting:
        verb = 'are in' if word in ('continent', 'region') else 'are'
        found.append(ask_number(rng, 'How many %s %s %s?' % (many, verb, pick), values[pick], spread,
                                'Read across from the top of the %s bar: %d.' % (pick, values[pick])))
    else:
        found.append(ask_number(rng, 'What is the %s of %s?' % (word, pick), values[pick], spread,
                                'Read across from the top of the %s bar.' % pick))
    first, second = rng.sample(labels, 2)
    if values[first] < values[second]:
        first, second = second, first
    if values[first] != values[second]:
        gap = values[first] - values[second]
        if counting:
            ask = 'How many more %s are %s than %s?' % (many, first, second)
        else:
            ask = 'How much higher is the %s of %s than %s?' % (word, first, second)
        found.append(ask_number(rng, ask, gap, max(1, spread // 2),
                                '%d \u2212 %d = %d.' % (values[first], values[second], gap)))
    if counting:
        total = sum(values.values())
        found.append(ask_number(rng, 'How many %s altogether on this chart?' % many, total,
                                max(2, spread), 'Add every bar: %d.' % total))
    return found


# ---- Pie charts ----------------------------------------------------------------------------


def pie_chart(source, rows, scope, measure, mode, rng):
    one, many = THING[source.key]
    usable = [row for row in rows if category(source, row, measure, scope)]
    teams = [size for size in PIE_TEAMS if size <= len(usable)]
    if not teams:
        raise NotEnoughData('Too few %s here for a pie chart.' % many)
    size = rng.choice(teams)
    team = rng.sample(usable, size)
    pairs = stats.merge_small(stats.counts(category(source, row, measure, scope) for row in team).items(),
                              PIE_SECTORS)
    if len(pairs) < 2:
        raise NotEnoughData('Everything here falls in one group, so there is no pie to cut.')
    each = 360 / size
    labels = [label for label, _ in pairs]
    values = [count for _, count in pairs]
    angles = [count * each for count in values]
    hidden = []
    if mode == 'complete':
        # Boundaries whose neighbours stay fixed, so each handle has a clear range.
        inner = list(range(1, len(pairs)))
        rng.shuffle(inner)
        for boundary in inner:
            if all(abs(boundary - other) > 1 for other in hidden):
                hidden.append(boundary)
            if len(hidden) == 2:
                break
        hidden.sort()
    word = {'colour': 'colour', 'type1': 'type', 'place': place_word(scope)}[measure]
    spec = {'labels': labels, 'values': values, 'angles': angles, 'hidden': hidden, 'total': size}
    made = {'title': '%s of %d %s from %s' % (word.capitalize(), size, many, scope_words(source, scope)),
            'chart': spec, 'questions': pie_questions(rng, pairs, size, many, word)}
    missing = set()
    for boundary in hidden:
        missing.update((boundary - 1, boundary))
    rows_out = []
    for index, (label, count) in enumerate(pairs):
        angle = '?' if index in missing else '%s°' % stats.number_text(count * each)
        rows_out.append([label, str(count), angle])
    rows_out.append(['Total', str(size), '360°'])
    made['table'] = {'headers': [word.capitalize(), 'Frequency', 'Angle'], 'rows': rows_out}
    if mode == 'complete':
        made['task'] = ('Each %s is 360 ÷ %d = %s°. Work out the ? angles, then drag '
                        'the dots round the circle.' % (one, size, stats.number_text(each)))
    return made


def pie_questions(rng, pairs, size, many, word):
    found = []
    values = dict(pairs)
    labels = [label for label, _ in pairs]
    each = 360 / size
    top = unique_top(pairs)
    named = [label for label in labels if label != 'Other'] or labels
    if top is not None and top != 'Other':
        found.append(ask_word(rng, 'Which %s is the biggest slice?' % word, top, labels,
                              '%s has the biggest angle: %s°.' % (top, stats.number_text(values[top] * each))))
    found.append(ask_number(rng, 'There are %d %s. How many degrees is each one?' % (size, many),
                            each, 5, '360 ÷ %d = %s°.' % (size, stats.number_text(each)), low=5))
    pick = rng.choice(named)
    angle = values[pick] * each
    found.append(ask_number(rng, 'The %s slice is %s°. How many %s is that?'
                            % (pick, stats.number_text(angle), many), values[pick], 1,
                            '%s ÷ %s = %d.' % (stats.number_text(angle), stats.number_text(each), values[pick]),
                            low=1))
    other = rng.choice(named)
    found.append(ask_number(rng, 'What angle is the %s slice?' % other, values[other] * each, each,
                            '%d × %s = %s°.' % (values[other], stats.number_text(each),
                                                         stats.number_text(values[other] * each)), low=each))
    part = rng.choice(named)
    answer = stats.fraction_text(values[part], size)
    wrong = {stats.fraction_text(max(1, values[part] + shift), size) for shift in (-2, -1, 1, 2)
             if 0 < values[part] + shift < size}
    wrong.add('%d/%d' % (values[part], 360))
    found.append(ask_word(rng, 'What fraction of the %s are %s? (simplest form)' % (many, part), answer,
                          sorted(wrong), '%d out of %d is %d/%d = %s.' % (values[part], size, values[part],
                                                                          size, answer)))
    return found


# ---- Histograms ------------------------------------------------------------------------------


def class_name(low, high, word):
    return '%s ≤ %s < %s' % (stats.number_text(low), word, stats.number_text(high))


def histogram(source, rows, scope, measure, mode, rng):
    one, many = THING[source.key]
    values = [plain_number(source, row, measure) for row in rows]
    values = [value for value in values if value is not None]
    if len(values) < 12:
        raise NotEnoughData('Too few %s with that figure here.' % many)
    word = short_name(source, measure)
    variants = []
    for width in CLASS_WIDTHS[measure]:
        edges = stats.class_edges(values, width)
        counts = stats.class_counts(values, edges)
        start, end, step = stats.nice_axis(0, max(counts), lines=6, from_zero=True)
        variants.append({'width': width, 'edges': edges, 'counts': counts, 'y': [start, end, step]})
    main = variants[0]
    hidden = hide_some(rng, len(main['counts']), 3) if mode == 'complete' else []
    spec = {'variants': variants if mode == 'look' else [main], 'current': 0, 'hidden': hidden,
            'x_label': axis_label(source, measure), 'y_label': 'Frequency'}
    made = {'title': '%s of %d %s from %s' % (axis_label(source, measure).split(' (')[0], len(values), many,
                                             scope_words(source, scope)),
            'chart': spec,
            'questions': histogram_questions(rng, main['edges'], main['counts'], many, word)}
    made['table'] = {'headers': [axis_label(source, measure), 'Frequency'],
                     'rows': [[class_name(low, high, 'x'), str(count)]
                              for low, high, count in zip(main['edges'], main['edges'][1:], main['counts'])]}
    if mode == 'complete':
        made['task'] = 'The classes are all the same width. Drag the dashed bars to the right height.'
    return made


def histogram_questions(rng, edges, counts, many, word):
    found = []
    names = [class_name(low, high, word) for low, high in zip(edges, edges[1:])]
    pairs = list(zip(names, counts))
    top = unique_top(pairs)
    if top is not None:
        found.append(ask_word(rng, 'Which class has the most %s? (the modal class)' % many, top, names,
                              'The tallest bar is %s.' % top))
    index = rng.randrange(len(counts))
    spread = max(1, int(round(max(counts) / 8)))
    found.append(ask_number(rng, 'How many %s have %s?' % (many, names[index]), counts[index], spread,
                            'Read the height of that bar: %d.' % counts[index]))
    if len(edges) > 3:
        cut = rng.randrange(1, len(edges) - 1)
        above = sum(counts[cut:])
        found.append(ask_number(rng, 'How many %s have a %s of %s or more?' % (many, word, stats.number_text(edges[cut])),
                                above, max(2, spread),
                                'Add the bars from %s up: %d.' % (stats.number_text(edges[cut]), above)))
    total = sum(counts)
    found.append(ask_number(rng, 'How many %s are on the histogram altogether?' % many, total,
                            max(2, spread * 2), 'Add every bar: %d.' % total))
    return found


# ---- Cumulative frequency -------------------------------------------------------------------------


def cumulative(source, rows, scope, measure, mode, rng):
    one, many = THING[source.key]
    usable = [plain_number(source, row, measure) for row in rows]
    usable = [value for value in usable if value is not None]
    if len(usable) < 20:
        raise NotEnoughData('Too few %s with that figure here.' % many)
    values = rng.sample(usable, min(CUMULATIVE_SAMPLE, len(usable)))
    width = CLASS_WIDTHS[measure][0]
    edges = stats.class_edges(values, width)
    counts = stats.class_counts(values, edges)
    totals = stats.running_totals(counts)
    points = [[edges[0], 0]] + [[edge, total] for edge, total in zip(edges[1:], totals)]
    size = len(values)
    x_start, x_end, x_step = edges[0], edges[-1], width
    y_start, y_end, y_step = stats.nice_axis(0, size, lines=8, from_zero=True)
    hidden = hide_some(rng, len(points), 3, first=1) if mode == 'complete' else []
    word = short_name(source, measure)
    spec = {'points': points, 'total': size, 'x': [x_start, x_end, x_step], 'y': [y_start, y_end, y_step],
            'hidden': hidden, 'x_label': axis_label(source, measure), 'y_label': 'Cumulative frequency'}
    made = {'title': '%s of %d %s from %s' % (axis_label(source, measure).split(' (')[0], size, many,
                                             scope_words(source, scope)),
            'chart': spec, 'questions': cumulative_questions(rng, points, size, many, word, width)}
    rows_out = []
    for index, (low, high, count) in enumerate(zip(edges, edges[1:], counts)):
        cf = '?' if index + 1 in hidden else str(totals[index])
        rows_out.append([class_name(low, high, 'x'), str(count), cf])
    made['table'] = {'headers': [axis_label(source, measure), 'Frequency', 'Cumulative frequency'],
                     'rows': rows_out}
    if mode == 'complete':
        made['task'] = ('Add up the frequencies to fill in the ? totals. Then drag each dashed dot '
                        'up to its total, above the end of its class.')
    return made


def cumulative_questions(rng, points, size, many, word, width):
    found = []
    inner = points[1:-1] or points[1:]
    x, cf = rng.choice(inner)
    spread = max(1, int(round(size / 10)))
    found.append(ask_number(rng, 'How many %s have a %s less than %s?' % (many, word, stats.number_text(x)), cf,
                            spread, 'Read up from %s to the line, then across: %d.' % (stats.number_text(x), cf)))
    middle = size / 2
    median = stats.read_across(points, middle)
    found.append(ask_number(rng, 'Estimate the median %s.' % word, median, max(1, width / 2),
                            'Half of %d is %s. Read across from %s to the line, then down: about %s.'
                            % (size, stats.number_text(middle), stats.number_text(middle),
                               stats.number_text(round(median)))))
    x2, cf2 = rng.choice(inner)
    found.append(ask_number(rng, 'How many %s have a %s of %s or more?' % (many, word, stats.number_text(x2)),
                            size - cf2, spread, '%d − %d = %d.' % (size, cf2, size - cf2)))
    lower = stats.read_across(points, size / 4)
    upper = stats.read_across(points, 3 * size / 4)
    spread_answer = upper - lower
    found.append(ask_number(rng, '⭐ Challenge: estimate the interquartile range.', spread_answer,
                            max(1, width / 2),
                            'Read across from %s and %s: about %s and %s. %s − %s ≈ %s.'
                            % (stats.number_text(size / 4), stats.number_text(3 * size / 4),
                               stats.number_text(round(lower)), stats.number_text(round(upper)),
                               stats.number_text(round(upper)), stats.number_text(round(lower)),
                               stats.number_text(round(spread_answer)))))
    return found


# ---- Box plots ---------------------------------------------------------------------------------


def box_groups(source, rows, scope, measure, rng):
    """Two (name, values) groups to compare: two types, or two continents."""
    if source.key == 'pokemon':
        by_type = {}
        for row in rows:
            value = plain_number(source, row, measure)
            if value is not None:
                by_type.setdefault(row['type1'], []).append(value)
        names = sorted(name for name, values in by_type.items() if len(values) >= BOX_SMALLEST_GROUP)
        if len(names) < 2:
            raise NotEnoughData('Too few Pokémon of any two types here.')
        first, second = rng.sample(names, 2)
        return [(first + ' type', by_type[first]), (second + ' type', by_type[second])]
    by_place = {}
    for row in source.rows:
        value = plain_number(source, row, measure)
        if value is not None:
            by_place.setdefault(row['continent'], []).append(value)
    names = sorted(name for name, values in by_place.items() if len(values) >= BOX_SMALLEST_GROUP)
    chosen = [scope] if scope in names else []
    others = [name for name in names if name not in chosen]
    rng.shuffle(others)
    chosen += others[:2 - len(chosen)]
    return [(name, by_place[name]) for name in chosen]


def box_plot(source, rows, scope, measure, mode, rng):
    one, many = THING[source.key]
    word = short_name(source, measure)
    if mode == 'complete':
        usable = [plain_number(source, row, measure) for row in rows]
        usable = [int(round(value)) for value in usable if value is not None]
        if len(usable) < BOX_SAMPLE:
            raise NotEnoughData('Too few %s with that figure here.' % many)
        values = rng.sample(usable, BOX_SAMPLE)
        groups = [('%d %s' % (BOX_SAMPLE, many), values)]
    else:
        groups = box_groups(source, rows, scope, measure, rng)
    fives = [(name, stats.five_numbers(values)) for name, values in groups]
    low = min(five[0] for _, five in fives)
    high = max(five[4] for _, five in fives)
    start, end, step = stats.nice_axis(low, high, lines=8)
    spec = {'groups': [{'name': name, 'five': [stats.tidy(value) for value in five]} for name, five in fives],
            'x': [start, end, step], 'complete': mode == 'complete', 'snap': 1,
            'x_label': axis_label(source, measure)}
    made = {'chart': spec}
    if mode == 'complete':
        made['title'] = '%s of %d %s from %s' % (axis_label(source, measure).split(' (')[0], BOX_SAMPLE,
                                                many, scope_words(source, scope))
        made['values'] = groups[0][1]
        made['task'] = ('Put the values in order. Find the lowest, the lower quartile (3rd value), the median '
                        '(6th), the upper quartile (9th) and the highest. Drag each marker to it.')
        made['questions'] = box_single_questions(rng, fives[0][1], word, step)
    else:
        made['title'] = '%s: %s and %s' % (axis_label(source, measure).split(' (')[0], fives[0][0], fives[1][0])
        made['questions'] = box_compare_questions(rng, fives, word, step, many)
    return made


def box_single_questions(rng, five, word, step):
    lowest, lower, median, upper, highest = five
    return [
        ask_number(rng, 'What is the median %s?' % word, median, max(1, step / 2),
                   'The median is the middle (6th) value: %s.' % stats.number_text(median)),
        ask_number(rng, 'What is the range?', highest - lowest, max(1, step / 2),
                   '%s − %s = %s.' % (stats.number_text(highest), stats.number_text(lowest),
                                          stats.number_text(highest - lowest))),
        ask_number(rng, 'What is the interquartile range?', upper - lower, max(1, step / 2),
                   'Upper quartile − lower quartile: %s − %s = %s.'
                   % (stats.number_text(upper), stats.number_text(lower), stats.number_text(upper - lower))),
    ]


def box_compare_questions(rng, fives, word, step, many):
    (first, a), (second, b) = fives
    names = [first, second]
    found = []
    spread = max(1, step / 2)
    pick, five = rng.choice(fives)
    found.append(ask_number(rng, 'What is the median %s for %s?' % (word, pick), five[2], spread,
                            'The line inside the box: %s.' % stats.number_text(five[2]), whole=False))
    found.append(ask_number(rng, 'What is the range for %s?' % pick, five[4] - five[0], spread,
                            'Highest − lowest: %s − %s = %s.'
                            % (stats.number_text(five[4]), stats.number_text(five[0]),
                               stats.number_text(five[4] - five[0])), whole=False))
    if a[2] != b[2]:
        higher = first if a[2] > b[2] else second
        found.append(ask_word(rng, 'Which group has the higher %s on average?' % word, higher, names,
                              'Compare the medians: %s is higher.' % higher))
    spread_a, spread_b = a[3] - a[1], b[3] - b[1]
    if max(spread_a, spread_b) >= 1.2 * min(spread_a, spread_b) and min(spread_a, spread_b) > 0:
        wider = first if spread_a > spread_b else second
        found.append(ask_word(rng, 'Which group is more spread out? (compare the boxes)', wider, names,
                              'The wider box, the bigger interquartile range, is %s.' % wider))
    if a[4] != b[4]:
        top = first if a[4] > b[4] else second
        found.append(ask_word(rng, 'Which group has the single highest %s?' % word, top, names,
                              'The right-hand whisker reaches furthest for %s.' % top))
    return found


# ---- Scatter graphs ---------------------------------------------------------------------------------


def snap_to(value, step):
    return stats.tidy(round(value / step) * step)


def scatter(source, rows, scope, measure, mode, rng):
    one, many = THING[source.key]
    across, up = measure.split(':')
    usable = []
    for row in rows:
        x, y = plain_number(source, row, across), plain_number(source, row, up)
        if x is None or y is None:
            continue
        if (across in SCATTER_LIMITS and x > SCATTER_LIMITS[across]) or (up in SCATTER_LIMITS and y > SCATTER_LIMITS[up]):
            continue
        usable.append((label_of(row), x, y))
    if len(usable) < 8:
        raise NotEnoughData('Too few %s with both figures here.' % many)
    chosen = rng.sample(usable, min(SCATTER_SAMPLE, len(usable)))
    xs = [x for _, x, _ in chosen]
    ys = [y for _, _, y in chosen]
    x_axis = stats.nice_axis(min(xs), max(xs), lines=6, from_zero=min(xs) >= 0 and min(xs) < (max(xs) - min(xs)))
    y_axis = stats.nice_axis(min(ys), max(ys), lines=6, from_zero=min(ys) >= 0 and min(ys) < (max(ys) - min(ys)))
    snap = [stats.minor_step(x_axis[2]), stats.minor_step(y_axis[2])]
    hidden = hide_some(rng, len(chosen), SCATTER_HIDDEN) if mode == 'complete' else []
    points = []
    for index, (name, x, y) in enumerate(chosen):
        if index in hidden:
            x, y = snap_to(x, snap[0]), snap_to(y, snap[1])
        points.append({'x': stats.tidy(round(x, 3)), 'y': stats.tidy(round(y, 3)), 'name': name})
    pairs = [(point['x'], point['y']) for point in points]
    gradient, intercept = stats.best_fit(pairs)
    spec = {'points': points, 'hidden': hidden, 'x': list(x_axis), 'y': list(y_axis), 'snap': snap,
            'fit': [gradient, intercept], 'x_label': axis_label(source, across),
            'y_label': axis_label(source, up)}
    made = {'title': '%s and %s of %d %s' % (axis_label(source, across).split(' (')[0],
                                             axis_label(source, up).split(' (')[0].lower(), len(points), many),
            'chart': spec,
            'questions': scatter_questions(rng, points, gradient, intercept, source, across, up, x_axis, y_axis,
                                           one, many)}
    if mode == 'complete':
        made['task'] = 'Plot the %d %s in the table: tap the grid to place a cross, tap it again to remove it.' % (
            len(hidden), many)
        made['table'] = {'headers': [one.capitalize(), axis_label(source, across), axis_label(source, up)],
                         'rows': [[points[index]['name'], stats.number_text(points[index]['x']),
                                   stats.number_text(points[index]['y'])] for index in hidden]}
    return made


def scatter_questions(rng, points, gradient, intercept, source, across, up, x_axis, y_axis, one, many):
    found = []
    pairs = [(point['x'], point['y']) for point in points]
    names = [point['name'] for point in points]
    word = stats.correlation_word(stats.correlation(pairs))
    nice = {'positive': 'Positive correlation', 'negative': 'Negative correlation', 'none': 'No correlation'}
    if word is not None:
        meaning = {'positive': 'as one goes up, the other tends to go up',
                   'negative': 'as one goes up, the other tends to go down',
                   'none': 'the points show no pattern'}[word]
        found.append(ask_word(rng, 'What type of correlation does the graph show?', nice[word],
                              list(nice.values()), '%s: %s.' % (nice[word], meaning)))
    top = max(points, key=lambda point: point['y'])
    if sum(1 for point in points if point['y'] == top['y']) == 1:
        found.append(ask_word(rng, 'Which %s has the highest %s?' % (one, short_name(source, up)), top['name'],
                              names, 'The highest point is %s.' % top['name']))
    if word in ('positive', 'negative'):
        x_low, x_high = min(x for x, _ in pairs), max(x for x, _ in pairs)
        x_read = snap_to(x_low + (x_high - x_low) * rng.uniform(0.3, 0.7), x_axis[2] / 2)
        y_read = gradient * x_read + intercept
        found.append(ask_number(rng, 'Use a line of best fit. Estimate the %s when the %s is %s.'
                                % (short_name(source, up), short_name(source, across), stats.number_text(x_read)),
                                y_read, y_axis[2], 'Up from %s to the line, then across: about %s.'
                                % (stats.number_text(x_read), stats.number_text(round(y_read))),
                                low=min(0, y_axis[0]), whole=y_axis[2] >= 1))
        gaps = sorted(((abs(y - (gradient * x + intercept)), name) for (x, y), name in zip(pairs, names)),
                      reverse=True)
        if len(gaps) > 1 and gaps[0][0] >= 1.8 * gaps[1][0]:
            odd = gaps[0][1]
            found.append(ask_word(rng, 'Which %s does not fit the pattern? (an outlier)' % one, odd, names,
                                  '%s is furthest from the line of best fit.' % odd))
    return found
