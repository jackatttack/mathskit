"""Smoke test for the Charts page: every chart, scope, measure and mode deals.

Role: check · Part of: mathskit/charts · Pure

Builds a made-up Pokémon and countries dataset (so it runs anywhere, with
or without library/datasets), then deals every combination at SEEDS seeds
and checks the contract: JSON-ready, each answer among its options, hidden
items in range, pie angles adding to 360, cumulative totals rising to the
sample size, and the stats helpers against hand-worked GCSE examples.
Also deals from the real datasets when they are found.
"""
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
for name in list(sys.modules):
    if name.split('.')[0] == 'mathskit':
        del sys.modules[name]

from mathskit import chart_page, charts, datasets, stats  # noqa: E402

SEEDS = 25
TYPES = ['Water', 'Normal', 'Grass', 'Fire', 'Bug', 'Poison', 'Electric', 'Rock', 'Psychic', 'Ground']
COLOURS = ['Blue', 'Red', 'Green', 'Brown', 'Yellow', 'Purple', 'Pink', 'Grey', 'White', 'Black']
CONTINENTS = {'Africa': ['Western Africa', 'Eastern Africa', 'Northern Africa', 'Southern Africa'],
              'Asia': ['Southern Asia', 'Eastern Asia', 'Western Asia', 'South-Eastern Asia'],
              'Europe': ['Northern Europe', 'Western Europe', 'Southern Europe', 'Eastern Europe'],
              'North America': ['Caribbean', 'Central America', 'North America'],
              'South America': ['South America'],
              'Oceania': ['Polynesia', 'Melanesia', 'Australia and New Zealand']}
SIZES = {'Africa': 54, 'Asia': 48, 'Europe': 44, 'North America': 23, 'South America': 12, 'Oceania': 14}


def made_up_pokemon(rng):
    rows = []
    for number in range(1, 494):
        generation = 1 if number <= 151 else 2 if number <= 251 else 3 if number <= 386 else 4
        height = round(rng.uniform(0.2, 3.0), 1)
        rows.append({'number': number, 'name': 'Mon%d' % number, 'generation': generation,
                     'type1': rng.choice(TYPES), 'type2': '', 'colour': rng.choice(COLOURS),
                     'height_m': height, 'weight_kg': round(height * rng.uniform(15, 45), 1),
                     'hp': rng.randint(20, 150), 'attack': rng.randint(10, 160), 'defence': rng.randint(10, 180),
                     'sp_attack': rng.randint(10, 150), 'sp_defence': rng.randint(10, 150),
                     'speed': rng.randint(5, 160), 'total': 0, 'legendary': 'no'})
    return datasets.Source('pokemon', rows)


def made_up_countries(rng):
    rows = []
    for continent, size in SIZES.items():
        for index in range(size):
            gdp = int(rng.lognormvariate(8.8, 1.1))
            urban = round(rng.uniform(15, 98), 1)
            life = round(min(86, 50 + 6 * (gdp ** 0.15) + rng.uniform(-6, 6)), 1)
            rows.append({'code': '%s%d' % (continent[:2].upper(), index), 'name': '%s %d' % (continent, index),
                         'continent': continent, 'subregion': rng.choice(CONTINENTS[continent]),
                         'population': int(rng.lognormvariate(16, 1.6)), 'area_km2': rng.randint(300, 900000),
                         'life_expectancy': life if rng.random() > 0.05 else None,
                         'gdp_per_person_usd': gdp, 'urban_percent': urban, 'population_year': '2023'})
    return datasets.Source('countries', rows)


def check_deal(made, label):
    json.dumps(made)
    chart = made['chart']
    kind = made['kind']
    for item in made['questions']:
        assert 0 <= item['answer'] < len(item['options']), (label, item)
        assert len(set(item['options'])) == len(item['options']), (label, 'repeated option', item)
        assert len(item['options']) >= 2, (label, item)
    if kind == 'bar':
        assert len(chart['labels']) == len(chart['values'])
        assert chart['y'][1] >= max(chart['values'])
        assert all(0 <= index < len(chart['values']) for index in chart['hidden'])
    if kind == 'pie':
        assert abs(sum(chart['angles']) - 360) < 1e-6, label
        for boundary in chart['hidden']:
            assert 1 <= boundary < len(chart['angles'])
    if kind == 'histogram':
        for variant in chart['variants']:
            assert len(variant['edges']) == len(variant['counts']) + 1
            assert variant['y'][1] >= max(variant['counts'])
    if kind == 'cumulative':
        heights = [cf for _, cf in chart['points']]
        assert heights == sorted(heights) and heights[0] == 0 and heights[-1] == chart['total'], label
        assert all(1 <= index < len(heights) for index in chart['hidden'])
    if kind == 'box':
        for group in chart['groups']:
            five = group['five']
            assert five == sorted(five), (label, five)
            assert chart['x'][0] <= five[0] and five[4] <= chart['x'][1], (label, five, chart['x'])
    if kind == 'scatter':
        for point in chart['points']:
            assert chart['x'][0] <= point['x'] <= chart['x'][1], (label, point, chart['x'])
            assert chart['y'][0] <= point['y'] <= chart['y'][1], (label, point, chart['y'])
    html = chart_page.html(made)
    assert 'ch-chart' in html


def deal_everything(sources):
    dealt = skipped = 0
    for source in sources:
        for kind, _ in charts.KINDS:
            for measure, _ in charts.recipes_for(source.key, kind):
                for scope, _ in charts.scopes_for(source.key):
                    for mode, _ in charts.MODES:
                        for seed in range(SEEDS):
                            label = (source.key, kind, measure, scope, mode, seed)
                            try:
                                made = charts.deal(source, kind, scope, measure, mode, random.Random(seed))
                            except charts.NotEnoughData:
                                skipped += 1
                                continue
                            check_deal(made, label)
                            dealt += 1
    return dealt, skipped


def check_stats():
    assert stats.five_numbers([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]) == (1, 3, 6, 9, 11)
    assert stats.five_numbers([2, 4, 6, 8]) == (2, 2.5, 5, 7.5, 8)
    assert stats.class_edges([3, 19, 20, 41], 20) == [0, 20, 40, 60]
    assert stats.class_counts([3, 19, 20, 41], [0, 20, 40, 60]) == [2, 1, 1]
    assert stats.read_across([[0, 0], [10, 10], [20, 30]], 20) == 15
    assert stats.nice_axis(0, 28, from_zero=True) == (0, 30, 5)
    assert stats.fraction_text(6, 24) == '1/4'
    gradient, intercept = stats.best_fit([(0, 1), (1, 3), (2, 5)])
    assert abs(gradient - 2) < 1e-9 and abs(intercept - 1) < 1e-9
    assert stats.correlation_word(0.9) == 'positive' and stats.correlation_word(0.4) is None


def main():
    check_stats()
    rng = random.Random(7)
    dealt, skipped = deal_everything([made_up_pokemon(rng), made_up_countries(rng)])
    print('made-up data: %d charts dealt, %d skipped for too little data' % (dealt, skipped))
    real = []
    for key in datasets.available():
        real.append(datasets.load(key))
    if real:
        dealt, skipped = deal_everything(real)
        print('real data (%s): %d charts dealt, %d skipped' % (', '.join(s.key for s in real), dealt, skipped))
    else:
        print('real data: none found (fine off device)')
    print('smoke_charts: all good')


if __name__ == '__main__':
    main()
