"""Statistics arithmetic for the Charts page: counts, classes, quartiles,
nice axes and lines of best fit, done the GCSE way.

Role: clean · Part of: mathskit/charts · Pure

Every function takes plain numbers or lists and returns plain numbers,
lists or tuples, so tests check them headless (tests/smoke_charts.py).

Conventions (GCSE, so the page agrees with the textbook):
- Classes are a <= x < b, written "a ≤ x < b".
- The median is the (n + 1)/2 th value; the lower and upper quartiles the
  (n + 1)/4 th and 3(n + 1)/4 th, reading between neighbours when the
  position is not whole.
"""
import math
from fractions import Fraction

# ---- Counting ---------------------------------------------------------------


def counts(values):
    """{value: how many times} in first-seen order."""
    found = {}
    for value in values:
        found[value] = found.get(value, 0) + 1
    return found


def top_counts(values, keep):
    """The keep most common values as [(value, count)], most common first,
    ties broken alphabetically so the same data always gives the same chart."""
    ranked = sorted(counts(values).items(), key=lambda pair: (-pair[1], str(pair[0])))
    return ranked[:keep]


def merge_small(pairs, keep, other='Other'):
    """[(label, count)] cut to keep labels: the rest add up into 'Other'."""
    ranked = sorted(pairs, key=lambda pair: (-pair[1], str(pair[0])))
    if len(ranked) <= keep:
        return ranked
    kept = ranked[:keep - 1]
    rest = sum(count for _, count in ranked[keep - 1:])
    return kept + [(other, rest)]


# ---- Classes ------------------------------------------------------------------


def class_edges(values, width, start=None):
    """Edges [a, a+w, ..., b] covering every value with classes a <= x < b.
    start defaults to the multiple of width at or below the smallest value."""
    low = min(values) if start is None else start
    first = math.floor(low / width) * width if start is None else start
    last = (math.floor(max(values) / width) + 1) * width
    edges = []
    edge = first
    while edge < last + width * 1e-9:
        edges.append(round(edge, 9))
        edge += width
    return edges


def class_counts(values, edges):
    """How many values fall in each class edges[i] <= x < edges[i+1]."""
    found = [0] * (len(edges) - 1)
    for value in values:
        for index in range(len(edges) - 1):
            if edges[index] <= value < edges[index + 1]:
                found[index] += 1
                break
    return found


def running_totals(numbers):
    total = 0
    out = []
    for number in numbers:
        total += number
        out.append(total)
    return out


# ---- Averages and spread ----------------------------------------------------------


def value_at(sorted_values, position):
    """The position-th value (1 is the first), reading between neighbours."""
    if not sorted_values:
        raise ValueError('No values to read a position from.')
    position = min(max(position, 1), len(sorted_values))
    below = int(math.floor(position))
    part = position - below
    low = sorted_values[below - 1]
    if part == 0 or below >= len(sorted_values):
        return low
    return low + (sorted_values[below] - low) * part


def five_numbers(values):
    """(lowest, lower quartile, median, upper quartile, highest)."""
    ordered = sorted(values)
    size = len(ordered)
    return (ordered[0],
            value_at(ordered, (size + 1) / 4),
            value_at(ordered, (size + 1) / 2),
            value_at(ordered, 3 * (size + 1) / 4),
            ordered[-1])


def mean(values):
    return sum(values) / len(values)


# ---- Reading a cumulative frequency graph --------------------------------------------


def read_across(points, height):
    """The x where the joined-up cumulative frequency points reach height:
    the way you read across from the cumulative frequency axis and down.
    points are [(x, cumulative)] with cumulative never falling."""
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if y0 <= height <= y1:
            if y1 == y0:
                return x0
            return x0 + (x1 - x0) * (height - y0) / (y1 - y0)
    return points[-1][0] if height > points[-1][1] else points[0][0]


def read_up(points, x):
    """The cumulative frequency at x on the joined-up points."""
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if x0 <= x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0) if x1 != x0 else y1
    return points[-1][1] if x > points[-1][0] else points[0][1]


# ---- Scatter graphs -------------------------------------------------------------------


def best_fit(points):
    """(gradient, intercept) of the least-squares line through [(x, y)]."""
    size = len(points)
    mean_x = sum(x for x, _ in points) / size
    mean_y = sum(y for _, y in points) / size
    spread = sum((x - mean_x) ** 2 for x, _ in points)
    if spread == 0:
        return 0.0, mean_y
    gradient = sum((x - mean_x) * (y - mean_y) for x, y in points) / spread
    return gradient, mean_y - gradient * mean_x


def correlation(points):
    """Pearson's r for [(x, y)], 0 when either spread is zero."""
    size = len(points)
    mean_x = sum(x for x, _ in points) / size
    mean_y = sum(y for _, y in points) / size
    sxy = sum((x - mean_x) * (y - mean_y) for x, y in points)
    sxx = sum((x - mean_x) ** 2 for x, _ in points)
    syy = sum((y - mean_y) ** 2 for _, y in points)
    if sxx == 0 or syy == 0:
        return 0.0
    return sxy / math.sqrt(sxx * syy)


def correlation_word(r):
    """'positive', 'negative' or 'none' when the pattern is clear, else None
    (a borderline pattern makes an unfair question)."""
    if r >= 0.55:
        return 'positive'
    if r <= -0.55:
        return 'negative'
    if abs(r) <= 0.25:
        return 'none'
    return None


# ---- Axes ---------------------------------------------------------------------------


def nice_step(span, lines=6):
    """A 1, 2 or 5 times a power of ten step giving about lines gridlines."""
    if span <= 0:
        return 1
    raw = span / max(1, lines)
    power = 10 ** math.floor(math.log10(raw))
    for unit in (1, 2, 5, 10):
        if raw <= unit * power * 1.0000001:
            return unit * power
    return 10 * power


def nice_axis(low, high, lines=6, from_zero=False):
    """(start, end, step) with whole steps covering low..high."""
    if from_zero:
        low = min(0, low)
    step = nice_step(high - low if high > low else max(abs(high), 1), lines)
    start = math.floor(low / step) * step
    end = math.ceil(high / step) * step
    if end <= start:
        end = start + step
    return tidy(start), tidy(end), tidy(step)


def minor_step(step):
    """The small squares of graph paper for a gridline step: a fifth of it
    when that is a 1 or 2 times a power of ten (10 -> 2, 5 -> 1), else half."""
    fifth = step / 5
    power = 10 ** math.floor(math.log10(fifth))
    if round(fifth / power, 6) in (1, 2):
        return tidy(fifth)
    return tidy(step / 2)


def tidy(number):
    """A float without binary dust: 0.30000000000000004 -> 0.3, 4.0 -> 4."""
    number = round(number, 9)
    return int(number) if number == int(number) else number


# ---- Fractions and words ---------------------------------------------------------------


def fraction_text(part, whole):
    """'3/12' simplified, as '1/4'."""
    value = Fraction(part, whole)
    return '%d/%d' % (value.numerator, value.denominator)


def number_text(number):
    """A number for a question: whole numbers plainly, others to 1 d.p."""
    number = tidy(number)
    if isinstance(number, int):
        return '{:,}'.format(number)
    return '{:,.1f}'.format(number)
