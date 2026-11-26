"""How a statistics chart looks and behaves on a page: HTML, CSS and script.

Role: present · Part of: mathskit/charts · Pure

html(deal) turns a charts.deal() dict into the Charts page's body: title,
the job to do (Draw it), the table, the chart, its tool buttons and the
questions. typeset.PAGE_PARTS carries CSS and SCRIPT into every page.

Everything after the draw happens in the page, with no trip to Python:

    tap a bar, slice, box or point     says what it is and its value
    Draw it: drag a dashed bar, dot,   sets it, snapped to the axis; Check
      slice edge or marker               colours each one right or wrong,
                                         Show me puts every one in place
    Draw it scatter: tap the grid      places a cross; tap it again to remove
    Cumulative frequency: tap the      reads across to the line and down;
      graph, Median, Quartiles           the buttons read at n/2, n/4, 3n/4
    Histogram: class width chips       switch between widths Python worked out
    Scatter: Line of best fit          shows the least-squares line
    Box plot values                    tap to tick one off; Put in order sorts
    Questions                          one at a time; a right answer goes
                                         green and explains why, a wrong one
                                         shakes and can be tried again

The script only draws what the spec says (charts.py works out every number)
and checks drags against the spec's own values. Labels with a meaning
colour (a Pokédex colour, a type, a continent) are drawn in it (COLOURS).
Touch is editorkit's window.ekTouch (editorkit.web.touch, 0.6.0 or later):
what a finger landed on, never where clientX/Y says it is.
"""
import html as html_module
import json

# ---- Words on the page (editable) --------------------------------------------------

CHECK_LABEL = 'Check'
SHOW_LABEL = 'Show me'
TABLE_LABEL = 'Table'
ORDER_LABEL = 'Put in order'
MEDIAN_LABEL = 'Median'
QUARTILES_LABEL = 'Quartiles'
FIT_LABEL = 'Line of best fit'
NEXT_LABEL = 'Next question ▶'
AGAIN_LABEL = 'Start the questions again'
DONE_LABEL = 'All done ✔'
LOOK_HINT = 'Tap the chart to read it.'
DRAW_HINT = 'Drag the dashed parts. Then tap Check.'
SCATTER_DRAW_HINT = 'Tap the grid to plot. Then tap Check.'


# Colours that mean something: a Pokédex colour drawn in that colour, a
# Pokémon type in its game colour, each continent always the same. A chart
# uses them only when every label has one; otherwise the page's palette.
COLOURS = {
    # Pokédex colours (PokeAPI spells grey 'Gray')
    'Black': '#3a3a3a', 'Blue': '#3b82f6', 'Brown': '#9a6a3a', 'Gray': '#9ca3af', 'Grey': '#9ca3af',
    'Green': '#22c55e', 'Pink': '#f472b6', 'Purple': '#a855f7', 'Red': '#ef4444', 'White': '#f4f4f4',
    'Yellow': '#facc15',
    # Pokémon types
    'Normal': '#a8a77a', 'Fire': '#ee8130', 'Water': '#6390f0', 'Electric': '#f7d02c', 'Grass': '#7ac74c',
    'Ice': '#96d9d6', 'Fighting': '#c22e28', 'Poison': '#a33ea1', 'Ground': '#e2bf65', 'Flying': '#a98ff3',
    'Psychic': '#f95587', 'Bug': '#a6b91a', 'Rock': '#b6a136', 'Ghost': '#735797', 'Dragon': '#6f35fc',
    'Dark': '#705746', 'Steel': '#b7b7ce', 'Fairy': '#d685ad',
    # Continents
    'Africa': '#f0883e', 'Asia': '#ff7b72', 'Europe': '#58a6ff', 'North America': '#3fb950',
    'South America': '#39c5cf', 'Oceania': '#bc8cff',
    'Other': '#8b949e',
}


def colours_for(labels):
    """The meaning colours for labels ('Fire type' counts as 'Fire'), or
    None when any label has none."""
    found = []
    for label in labels:
        key = str(label)
        if key.endswith(' type'):
            key = key[:-5]
        if key not in COLOURS:
            return None
        found.append(COLOURS[key])
    return found


def with_colours(kind, chart):
    """The chart spec, plus colours when its labels have meaning colours."""
    if kind in ('bar', 'pie'):
        labels = chart.get('labels', [])
    elif kind == 'box':
        labels = [group['name'] for group in chart.get('groups', [])]
    else:
        return chart
    colours = colours_for(labels)
    if colours is None:
        return chart
    return dict(chart, colours=colours)


def escape(words):
    return html_module.escape(str(words), quote=True)


def button(label, action, lit=False):
    return '<span class="ch-btn%s" data-ch="%s">%s</span>' % (' ch-lit' if lit else '', escape(action),
                                                               escape(label))


def html(deal):
    """The Charts page body for one deal (see charts.py for its fields)."""
    kind, mode = deal['kind'], deal['mode']
    parts = ['<div class="ch-deal" data-kind="%s" data-mode="%s">' % (escape(kind), escape(mode)),
             '<div class="ch-title">%s</div>' % escape(deal['title'])]
    if deal.get('note'):
        parts.append('<div class="ch-note">%s</div>' % escape(deal['note']))
    if deal.get('task'):
        parts.append('<div class="ch-task">%s</div>' % escape(deal['task']))
    if deal.get('values'):
        parts.append(values_html(deal['values']))
    if deal.get('table'):
        parts.append(table_html(deal['table'], shown=mode == 'complete'))
    chart = with_colours(kind, deal['chart'])
    parts.append('<div class="ch-chart" data-chart="%s"></div>' % escape(json.dumps(chart)))
    parts.append(tools_html(deal))
    parts.append(questions_html(deal['questions']))
    parts.append('</div>')
    return ''.join(parts)


def values_html(values):
    chips = ''.join('<span class="ch-value" data-ch="value" data-v="%s">%s</span>' % (escape(value), escape(value))
                    for value in values)
    return ('<div class="ch-values-wrap"><div class="ch-values">%s</div>'
            '<div class="ch-tools">%s</div></div>' % (chips, button(ORDER_LABEL, 'order')))


def table_html(table, shown):
    head = ''.join('<th>%s</th>' % escape(cell) for cell in table['headers'])
    body = ''.join('<tr>%s</tr>' % ''.join('<td%s>%s</td>' % (' class="ch-ask"' if cell == '?' else '',
                                                               escape(cell)) for cell in row)
                   for row in table['rows'])
    toggle = '' if shown else '<div class="ch-tools">%s</div>' % button(TABLE_LABEL, 'table')
    return ('%s<div class="ch-table-wrap%s"><table class="ch-table"><tr>%s</tr>%s</table></div>'
            % (toggle, '' if shown else ' ch-hidden', head, body))


def tools_html(deal):
    kind, mode = deal['kind'], deal['mode']
    chart = deal['chart']
    buttons = []
    if mode == 'complete':
        buttons += [button(CHECK_LABEL, 'check', lit=True), button(SHOW_LABEL, 'show')]
    if kind == 'histogram' and len(chart.get('variants', [])) > 1:
        buttons += [button('Width %s' % format_number(variant['width']), 'width:%d' % index, lit=index == 0)
                    for index, variant in enumerate(chart['variants'])]
    if kind == 'cumulative':
        buttons += [button(MEDIAN_LABEL, 'median'), button(QUARTILES_LABEL, 'quartiles')]
    if kind == 'scatter':
        buttons.append(button(FIT_LABEL, 'fit'))
    if mode == 'complete':
        hint = SCATTER_DRAW_HINT if kind == 'scatter' else DRAW_HINT
    else:
        hint = LOOK_HINT
    return ('<div class="ch-readout">%s</div><div class="ch-tools">%s</div>'
            % (escape(hint), ''.join(buttons)))


def questions_html(questions):
    if not questions:
        return ''
    blocks = []
    for number, item in enumerate(questions):
        options = ''.join('<span class="ch-opt" data-ch="opt" data-right="%d">%s</span>'
                          % (1 if index == item['answer'] else 0, escape(option))
                          for index, option in enumerate(item['options']))
        last = number == len(questions) - 1
        after = button(AGAIN_LABEL, 'again') if last else button(NEXT_LABEL, 'next', lit=True)
        blocks.append('<div class="ch-q%s"><div class="ch-qcount">Question %d of %d</div>'
                      '<div class="ch-ask-text">%s</div><div class="ch-opts">%s</div>'
                      '<div class="ch-why">%s%s<div class="ch-tools">%s</div></div></div>'
                      % ('' if number == 0 else ' ch-hidden', number + 1, len(questions),
                         escape(item['ask']), options,
                         ('<b>%s</b> ' % escape(DONE_LABEL)) if last else '✔ ', escape(item['why']),
                         after))
    return '<div class="ch-questions">%s</div>' % ''.join(blocks)


def format_number(value):
    return ('%g' % value)


CSS = """
.ch-deal { margin: 6px 0 24px; }
.ch-title { font: 650 19px -apple-system, sans-serif; margin: 10px 0 2px; }
.ch-note { color: var(--muted); font-size: 13px; margin-bottom: 8px; }
.ch-task { background: var(--wash); border-left: 4px solid var(--accent); border-radius: 10px;
    padding: 10px 12px; margin: 8px 0; font-size: 16px; line-height: 1.4; }
.ch-hidden { display: none !important; }
.ch-tools { display: flex; flex-wrap: wrap; gap: 8px; margin: 8px 0; }
.ch-btn, .ch-opt, .ch-value { cursor: pointer; -webkit-user-select: none; user-select: none;
    -webkit-tap-highlight-color: transparent; }
.ch-btn { display: inline-block; font-size: 16px; padding: 9px 15px; border-radius: 999px;
    background: var(--wash-strong); color: var(--text); }
.ch-btn.ch-lit { background: var(--accent); color: #fff; }
.ch-table-wrap { overflow-x: auto; margin: 6px 0 10px; }
.ch-table { border-collapse: collapse; font-size: 15px; min-width: 60%; }
.ch-table th, .ch-table td { border: 1px solid var(--line); padding: 6px 10px; text-align: center; }
.ch-table td:first-child { white-space: nowrap; }
.ch-table th { background: var(--wash); font-weight: 600; }
.ch-table td.ch-ask { color: var(--accent); font-weight: 700; }
.ch-values { display: flex; flex-wrap: wrap; gap: 8px; margin: 8px 0 2px; }
.ch-value { font: 600 18px Menlo, monospace; padding: 8px 11px; border-radius: 10px;
    background: var(--wash-strong); min-width: 28px; text-align: center; }
.ch-value.ch-on { background: var(--accent); color: #fff; }
.ch-chart { margin: 8px 0 0; color: var(--text); position: relative; }
.ch-chart svg { display: block; width: 100%; height: auto; font-family: -apple-system, sans-serif;
    -webkit-user-select: none; user-select: none; -webkit-touch-callout: none; }
.ch-chart svg.ch-base { border-radius: 12px; background: var(--wash); }
/* Only marked shapes take touches: lines and words never steal a tap. */
.ch-chart svg.ch-base * { pointer-events: none; }
.ch-chart svg.ch-base [data-t] { pointer-events: auto; }
.ch-chart svg.ch-over { position: absolute; left: 0; top: 0; width: 100%; height: 100%;
    pointer-events: none; overflow: visible; }
.ch-chart svg.ch-over g { pointer-events: auto; }
.ch-chart svg.ch-over text { pointer-events: none; }
.ch-chart .ch-bar { stroke: var(--muted); stroke-width: 1; }
.ch-chart .ch-slice { stroke: var(--card); stroke-width: 2; }
.ch-chart text { fill: var(--text); }
.ch-chart .ch-faint { fill: var(--muted); }
.ch-chart .ch-grid { stroke: var(--line); stroke-width: 1; }
.ch-chart .ch-axis { stroke: var(--muted); stroke-width: 1.5; }
.ch-chart .ch-read { stroke: var(--accent); stroke-width: 2; stroke-dasharray: 6 4; fill: none; }
.ch-chart .ch-handle { fill: var(--accent); stroke: #fff; stroke-width: 2.5; }
.ch-chart .ch-good { fill: #3fb950; }
.ch-chart .ch-bad { fill: #f85149; }
.ch-chart .ch-cross { fill: none; stroke: var(--accent); stroke-width: 4; stroke-linecap: round; }
.ch-chart .ch-cross.ch-good { stroke: #3fb950; }
.ch-chart .ch-cross.ch-bad { stroke: #f85149; }
.ch-chart .ch-good-line { stroke: #3fb950; }
.ch-chart .ch-bad-line { stroke: #f85149; }
.ch-win svg { animation: ch-pop 0.5s ease; box-shadow: 0 0 0 3px #3fb950; }
@keyframes ch-pop { 0% { transform: scale(1); } 40% { transform: scale(1.03); } 100% { transform: scale(1); } }
.ch-readout { min-height: 24px; margin: 6px 2px 0; font-size: 16px; color: var(--muted); }
.ch-readout.ch-said { color: var(--text); font-weight: 600; }
.ch-questions { margin-top: 14px; }
.ch-q { background: var(--wash); border-radius: 14px; padding: 12px 14px; margin: 8px 0; }
.ch-qcount { font-size: 13px; color: var(--muted); }
.ch-ask-text { font-size: 18px; font-weight: 600; margin: 4px 0 10px; line-height: 1.35; }
.ch-opts { display: flex; flex-wrap: wrap; gap: 10px; }
.ch-opt { font-size: 18px; padding: 12px 18px; border-radius: 14px; background: var(--card);
    border: 2px solid var(--line); min-width: 54px; text-align: center; }
.ch-opt.ch-right { background: #3fb950; border-color: #3fb950; color: #fff; }
.ch-opt.ch-wrong { border-color: #f85149; color: var(--muted); text-decoration: line-through;
    animation: ch-shake 0.4s; }
.ch-opt.ch-off { opacity: 0.45; }
@keyframes ch-shake { 0%, 100% { transform: translateX(0); } 25% { transform: translateX(-6px); }
    75% { transform: translateX(6px); } }
.ch-why { display: none; margin-top: 10px; font-size: 16px; line-height: 1.4; }
.ch-q.ch-solved .ch-why { display: block; }
"""


SCRIPT = r"""
/* The Charts page's drawing and touch layer.
   Role: present · Part of: mathskit/charts
   Takes: each .ch-chart's data-chart JSON (the spec charts.py made, plus
   colours from chart_page.py). Gives: nothing back to Python; every tap
   and drag is handled here. Holds no statistics beyond reading the spec.

   Touch is editorkit's (editorkit.web.touch, window.ekTouch, 0.6.0): taps
   act on the element a finger lands on (data-t: a bar, a slice, a grid
   cell to plot in, a band to read across from), never on clientX/Y, which
   drifts in the old UIWebView under page zoom. Handles (data-h) sit on
   their own layer, .ch-over, moved but never rebuilt mid-drag (a removed
   element stops its touch reaching the chart); a drag moves a handle by
   the finger's movement, which ekTouch gives in CSS pixels. */
(function () {
  var PALETTE = ['#58a6ff', '#ff7b72', '#3fb950', '#e3b341', '#bc8cff', '#f0883e', '#39c5cf', '#db61a2'];
  var PIE_TOLERANCE = 2;     // degrees a dragged slice edge may be out
  var HANDLE_SIZE = 12;      // radius of a drawn handle
  var HANDLE_REACH = 26;     // radius a finger can grab it from
  var SVG = 'http://www.w3.org/2000/svg';

  // ---- Small helpers --------------------------------------------------------------

  function esc(text) {
    return String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
                       .replace(/"/g, '&quot;');
  }
  function num(value) {
    var rounded = Math.round(value * 100) / 100;
    if (Math.abs(rounded) >= 1000) { return Math.round(rounded).toLocaleString('en-GB'); }
    return String(rounded);
  }
  function snap(value, step) { return Math.round(Math.round(value / step) * step * 1e6) / 1e6; }
  function clamp(value, low, high) { return Math.max(low, Math.min(high, value)); }
  function ticks(axis) {
    var out = [];
    for (var v = axis[0]; v <= axis[1] + axis[2] * 1e-6; v += axis[2]) { out.push(Math.round(v * 1e6) / 1e6); }
    return out;
  }
  function line(x1, y1, x2, y2, cls, extra) {
    return '<line x1="' + x1 + '" y1="' + y1 + '" x2="' + x2 + '" y2="' + y2 + '" class="' + (cls || '') + '"' +
           (extra || '') + '/>';
  }
  function text(x, y, words, anchor, extra) {
    return '<text x="' + x + '" y="' + y + '" text-anchor="' + (anchor || 'middle') + '"' + (extra || '') + '>' +
           esc(words) + '</text>';
  }
  // An invisible shape a finger can land on: data-t says what it is.
  function hit(x, y, width, height, key) {
    return '<rect x="' + x + '" y="' + y + '" width="' + Math.max(0, width) + '" height="' + Math.max(0, height) +
           '" fill="#000" fill-opacity="0" data-t="' + esc(key) + '"/>';
  }
  function colourOf(state, index) {
    var colours = state.spec.colours;
    return colours && colours[index] ? colours[index] : PALETTE[index % PALETTE.length];
  }
  // Dark words on light colours (a yellow or white slice), white on the rest.
  function inkOn(colour) {
    var hex = colour.replace('#', '');
    if (hex.length !== 6) { return '#fff'; }
    var r = parseInt(hex.slice(0, 2), 16), g = parseInt(hex.slice(2, 4), 16), b = parseInt(hex.slice(4, 6), 16);
    return (0.299 * r + 0.587 * g + 0.114 * b) > 165 ? '#111' : '#fff';
  }
  function deal(el) { return el.closest ? el.closest('.ch-deal') : null; }
  function say(el, words, strong) {
    var box = deal(el);
    var out = box ? box.querySelector('.ch-readout') : null;
    if (!out) { return; }
    out.textContent = words;
    out.className = 'ch-readout' + (strong ? ' ch-said' : '');
  }

  // ---- Frame: size, margins and axes ------------------------------------------------

  function chartWidth(state) { return Math.max(280, Math.round(state.el.clientWidth || 340)); }
  function frame(state, bottom) {
    var width = chartWidth(state);
    var height = Math.round(clamp(width * 0.7, 240, 440));
    return {w: width, h: height, left: 52, right: 16, top: 16, bottom: bottom || 50};
  }
  function scaleX(f, axis) {
    return function (v) { return f.left + (v - axis[0]) / (axis[1] - axis[0]) * (f.w - f.left - f.right); };
  }
  function scaleY(f, axis) {
    return function (v) { return f.h - f.bottom - (v - axis[0]) / (axis[1] - axis[0]) * (f.h - f.top - f.bottom); };
  }
  function unscaleX(f, axis, px) { return axis[0] + (px - f.left) / (f.w - f.left - f.right) * (axis[1] - axis[0]); }
  function unscaleY(f, axis, py) { return axis[0] + (f.h - f.bottom - py) / (f.h - f.top - f.bottom) * (axis[1] - axis[0]); }

  function yAxis(f, axis, sy, label) {
    var out = '';
    var marks = ticks(axis);
    for (var i = 0; i < marks.length; i++) {
      var y = sy(marks[i]);
      out += line(f.left, y, f.w - f.right, y, 'ch-grid');
      out += text(f.left - 6, y + 4, num(marks[i]), 'end', ' font-size="12"');
    }
    out += line(f.left, f.top, f.left, f.h - f.bottom, 'ch-axis');
    if (label) {
      var middle = (f.top + f.h - f.bottom) / 2;
      out += '<text x="13" y="' + middle + '" text-anchor="middle" font-size="12" class="ch-faint" ' +
             'transform="rotate(-90 13 ' + middle + ')">' + esc(label) + '</text>';
    }
    return out;
  }
  function xAxis(f, axis, sx, label, grid) {
    var out = '';
    var marks = ticks(axis);
    for (var i = 0; i < marks.length; i++) {
      var x = sx(marks[i]);
      if (grid) { out += line(x, f.top, x, f.h - f.bottom, 'ch-grid'); }
      out += line(x, f.h - f.bottom, x, f.h - f.bottom + 5, 'ch-axis');
      out += text(x, f.h - f.bottom + 18, num(marks[i]), 'middle', ' font-size="12"');
    }
    out += line(f.left, f.h - f.bottom, f.w - f.right, f.h - f.bottom, 'ch-axis');
    if (label) { out += text((f.left + f.w - f.right) / 2, f.h - 8, label, 'middle', ' font-size="12" class="ch-faint"'); }
    return out;
  }
  function svg(f, body) {
    return '<svg class="ch-base" viewBox="0 0 ' + f.w + ' ' + f.h + '" width="' + f.w + '" height="' + f.h + '">' +
           body + '</svg>';
  }

  // ---- Bar charts and histograms --------------------------------------------------------

  function barSetup(state) {
    var spec = state.spec;
    if (state.kind === 'histogram') {
      var variant = spec.variants[state.variant || 0];
      state.labels = null;
      state.edges = variant.edges;
      state.target = variant.counts;
      state.yaxis = variant.y;
    } else {
      state.labels = spec.labels;
      state.target = spec.values;
      state.yaxis = spec.y;
    }
    state.values = state.target.slice();
    state.hidden = state.variant ? [] : (spec.hidden || []);
    for (var i = 0; i < state.hidden.length; i++) { state.values[state.hidden[i]] = 0; }
    state.marks = {};
  }

  function drawBars(state) {
    var spec = state.spec;
    var rotate = state.labels && state.labels.some(function (label) { return String(label).length > 7; });
    var f = frame(state, rotate ? 84 : 50);
    var sy = scaleY(f, state.yaxis);
    var count = state.values.length;
    var slot = (f.w - f.left - f.right) / count;
    var body = yAxis(f, state.yaxis, sy, spec.y_label);
    state.handles = [];
    for (var i = 0; i < count; i++) {
      var left = state.kind === 'histogram' ? f.left + slot * i : f.left + slot * (i + 0.2);
      var right = state.kind === 'histogram' ? f.left + slot * (i + 1) : f.left + slot * (i + 0.8);
      var top = sy(state.values[i]), base = sy(state.yaxis[0]);
      var hidden = state.hidden.indexOf(i) >= 0;
      var colour = state.kind === 'histogram' ? PALETTE[0] : colourOf(state, i);
      body += hit(f.left + slot * i, f.top, slot, f.h - f.bottom - f.top, 'bar:' + i);
      var style = hidden ? 'fill="' + colour + '" fill-opacity="0.35" stroke="' + colour +
                           '" stroke-width="2" stroke-dasharray="6 4"'
                         : 'fill="' + colour + '" class="ch-bar"';
      body += '<rect x="' + left + '" y="' + Math.min(top, base) + '" width="' + (right - left) + '" height="' +
              Math.abs(base - top) + '" ' + style + ' data-t="bar:' + i + '"' +
              (state.picked === i ? ' stroke="var(--text)" stroke-width="3"' : '') + '/>';
      if (hidden) { state.handles.push({id: i, x: (left + right) / 2, y: top, mark: state.marks[i]}); }
      if (state.labels) {
        var cx = (left + right) / 2, ly = f.h - f.bottom + 16;
        body += rotate ? '<text x="' + cx + '" y="' + ly + '" text-anchor="end" font-size="12" transform="rotate(-38 ' +
                         cx + ' ' + ly + ')">' + esc(state.labels[i]) + '</text>'
                       : text(cx, ly, state.labels[i], 'middle', ' font-size="12"');
      }
    }
    if (state.labels) {
      body += line(f.left, f.h - f.bottom, f.w - f.right, f.h - f.bottom, 'ch-axis');
    } else {
      var edgeAxis = [state.edges[0], state.edges[state.edges.length - 1], state.edges[1] - state.edges[0]];
      body += xAxis(f, edgeAxis, scaleX(f, edgeAxis), spec.x_label, false);
    }
    state.frame = f;
    return svg(f, body);
  }

  function barName(state, index) {
    if (state.labels) { return state.labels[index]; }
    return num(state.edges[index]) + ' ≤ x < ' + num(state.edges[index + 1]);
  }

  function barDrag(state, index, x, y) {
    var value = snap(unscaleY(state.frame, state.yaxis, y), state.spec.snap || 1);
    state.values[index] = clamp(value, state.yaxis[0], state.yaxis[1]);
    delete state.marks[index];
    say(state.el, barName(state, index) + ': ' + num(state.values[index]), true);
  }

  function barTap(state, key) {
    var parts = key.split(':');
    if (parts[0] !== 'bar') { return; }
    var index = +parts[1];
    state.picked = index;
    say(state.el, barName(state, index) + ': ' + num(state.values[index]), true);
  }

  function barCheck(state) {
    var right = 0;
    for (var i = 0; i < state.hidden.length; i++) {
      var index = state.hidden[i];
      state.marks[index] = Math.abs(state.values[index] - state.target[index]) < 1e-6;
      if (state.marks[index]) { right += 1; }
    }
    return [right, state.hidden.length];
  }

  function barShow(state) {
    for (var i = 0; i < state.hidden.length; i++) { state.values[state.hidden[i]] = state.target[state.hidden[i]]; }
  }

  // ---- Pie charts ----------------------------------------------------------------------------

  function pieSetup(state) {
    var angles = state.spec.angles;
    state.edges = [0];
    for (var i = 0; i < angles.length; i++) { state.edges.push(state.edges[i] + angles[i]); }
    state.target = state.edges.slice();
    state.hidden = state.spec.hidden || [];
    for (var j = 0; j < state.hidden.length; j++) {
      var b = state.hidden[j];
      state.edges[b] = Math.round((state.target[b - 1] + state.target[b + 1]) / 2);
    }
    state.marks = {};
  }

  function piePoint(cx, cy, r, degrees) {
    var radians = (degrees - 90) * Math.PI / 180;
    return [cx + r * Math.cos(radians), cy + r * Math.sin(radians)];
  }

  function drawPie(state) {
    var spec = state.spec;
    var width = chartWidth(state);
    var legendRows = Math.ceil(spec.labels.length / 2);
    var r = Math.min(width * 0.36, 150);
    var cx = width / 2, cy = r + 22;
    var f = {w: width, h: Math.round(cy + r + 24 + legendRows * 24), left: 0, right: 0, top: 0, bottom: 0};
    var body = '';
    var complete = state.hidden.length > 0;
    if (complete) {
      for (var t = 0; t < 360; t += 10) {
        var a = piePoint(cx, cy, r + 3, t), b = piePoint(cx, cy, r + (t % 90 === 0 ? 13 : 8), t);
        body += line(a[0], a[1], b[0], b[1], 'ch-axis');
      }
    }
    for (var i = 0; i < spec.labels.length; i++) {
      var start = state.edges[i], end = state.edges[i + 1];
      var colour = colourOf(state, i);
      var lifted = state.picked === i ? 8 : 0;
      var middle = piePoint(0, 0, lifted, (start + end) / 2);
      var ox = cx + middle[0], oy = cy + middle[1];
      if (end - start >= 359.999) {
        body += '<circle cx="' + ox + '" cy="' + oy + '" r="' + r + '" fill="' + colour + '" class="ch-slice" data-t="slice:' + i + '"/>';
      } else if (end - start > 0) {
        var p = piePoint(ox, oy, r, start), q = piePoint(ox, oy, r, end);
        body += '<path d="M' + ox + ' ' + oy + ' L' + p[0] + ' ' + p[1] + ' A' + r + ' ' + r + ' 0 ' +
                (end - start > 180 ? 1 : 0) + ' 1 ' + q[0] + ' ' + q[1] + ' Z" fill="' + colour +
                '" class="ch-slice" data-t="slice:' + i + '"/>';
      }
      if (complete && end - start >= 18) {
        var spot = piePoint(cx, cy, r * 0.62, (start + end) / 2);
        body += text(spot[0], spot[1] + 5, num(end - start) + '°', 'middle',
                     ' font-size="14" font-weight="700" style="fill:' + inkOn(colour) + '"');
      }
    }
    state.handles = [];
    for (var h = 0; h < state.hidden.length; h++) {
      var edge = state.hidden[h];
      var rim = piePoint(cx, cy, r, state.edges[edge]);
      body += line(cx, cy, rim[0], rim[1], '', ' stroke="var(--text)" stroke-width="3" stroke-dasharray="6 4"');
      state.handles.push({id: edge, x: rim[0], y: rim[1], mark: state.marks[edge]});
    }
    var top = cy + r + 30;
    for (var k = 0; k < spec.labels.length; k++) {
      var col = k % 2, row = Math.floor(k / 2);
      var lx = width * (col === 0 ? 0.08 : 0.54), ly = top + row * 24;
      body += '<rect x="' + lx + '" y="' + (ly - 12) + '" width="14" height="14" rx="3" fill="' + colourOf(state, k) +
              '" class="ch-bar"/>';
      body += text(lx + 20, ly, spec.labels[k], 'start', ' font-size="14"');
      body += hit(lx - 4, ly - 18, width * 0.44, 24, 'slice:' + k);
    }
    state.frame = f;
    state.pie = {cx: cx, cy: cy, r: r};
    return svg(f, body);
  }

  function pieDrag(state, edge, x, y) {
    var degrees = Math.atan2(y - state.pie.cy, x - state.pie.cx) * 180 / Math.PI + 90;
    degrees = Math.round((degrees + 360) % 360);
    var low = state.edges[edge - 1] + 1, high = state.edges[edge + 1] - 1;
    if (degrees < low && low - degrees > 180) { degrees += 360; }   // dragged past the top
    state.edges[edge] = clamp(degrees, low, high);
    delete state.marks[edge];
    var labels = state.spec.labels;
    say(state.el, labels[edge - 1] + ' ' + num(state.edges[edge] - state.edges[edge - 1]) + '° · ' +
        labels[edge] + ' ' + num(state.edges[edge + 1] - state.edges[edge]) + '°', true);
  }

  function pieTap(state, key) {
    var parts = key.split(':');
    if (parts[0] !== 'slice') { return; }
    var i = +parts[1];
    state.picked = state.picked === i ? null : i;
    var angle = state.edges[i + 1] - state.edges[i];
    say(state.el, state.spec.labels[i] + ': ' + state.spec.values[i] + ' of ' + state.spec.total +
        ' · ' + num(angle) + '°', true);
  }

  function pieCheck(state) {
    var right = 0;
    for (var i = 0; i < state.hidden.length; i++) {
      var edge = state.hidden[i];
      state.marks[edge] = Math.abs(state.edges[edge] - state.target[edge]) <= PIE_TOLERANCE;
      if (state.marks[edge]) { right += 1; }
    }
    return [right, state.hidden.length];
  }

  function pieShow(state) {
    for (var i = 0; i < state.hidden.length; i++) { state.edges[state.hidden[i]] = state.target[state.hidden[i]]; }
  }

  // ---- Cumulative frequency ----------------------------------------------------------------------

  function cumulativeSetup(state) {
    state.points = state.spec.points.map(function (point) { return [point[0], point[1]]; });
    state.hidden = state.spec.hidden || [];
    // A dot to place starts level with the one before it, so the line stays flat, not zig-zag.
    for (var i = 0; i < state.hidden.length; i++) {
      var index = state.hidden[i];
      state.points[index][1] = state.points[index - 1][1];
    }
    state.marks = {};
    state.reads = [];
  }

  function readAcross(points, height) {
    for (var i = 0; i + 1 < points.length; i++) {
      var a = points[i], b = points[i + 1];
      if (a[1] <= height && height <= b[1]) {
        return b[1] === a[1] ? a[0] : a[0] + (b[0] - a[0]) * (height - a[1]) / (b[1] - a[1]);
      }
    }
    return null;
  }

  function drawCumulative(state) {
    var spec = state.spec;
    var f = frame(state, 50);
    var sx = scaleX(f, spec.x), sy = scaleY(f, spec.y);
    var body = '';
    // One band per whole number up the side: tap at a height to read across from it.
    for (var v = 0; v <= spec.total; v++) {
      body += hit(f.left, sy(v + 0.5), f.w - f.left - f.right, sy(v - 0.5) - sy(v + 0.5), 'cf:' + v);
    }
    body += yAxis(f, spec.y, sy, spec.y_label) + xAxis(f, spec.x, sx, spec.x_label, true);
    var path = '';
    for (var i = 0; i < state.points.length; i++) {
      path += (i ? ' L' : 'M') + sx(state.points[i][0]) + ' ' + sy(state.points[i][1]);
    }
    body += '<path d="' + path + '" fill="none" stroke="' + PALETTE[0] + '" stroke-width="2.5"/>';
    for (var r = 0; r < state.reads.length; r++) {
      var height = state.reads[r];
      var across = readAcross(state.points, height);
      if (across === null) { continue; }
      body += '<path class="ch-read" d="M' + f.left + ' ' + sy(height) + ' L' + sx(across) + ' ' + sy(height) +
              ' L' + sx(across) + ' ' + (f.h - f.bottom) + '"/>';
    }
    state.handles = [];
    for (var j = 0; j < state.points.length; j++) {
      var px = sx(state.points[j][0]), py = sy(state.points[j][1]);
      if (state.hidden.indexOf(j) >= 0) {
        body += line(px, f.top, px, f.h - f.bottom, '', ' stroke="' + PALETTE[0] + '" stroke-opacity="0.45" stroke-dasharray="4 4"');
        state.handles.push({id: j, x: px, y: py, mark: state.marks[j]});
      } else {
        body += '<circle cx="' + px + '" cy="' + py + '" r="4" fill="' + PALETTE[0] + '"/>';
      }
    }
    state.frame = f;
    return svg(f, body);
  }

  function cumulativeDrag(state, index, x, y) {
    var value = clamp(snap(unscaleY(state.frame, state.spec.y, y), 1), 0, state.spec.total);
    state.points[index][1] = value;
    delete state.marks[index];
    say(state.el, 'Less than ' + num(state.points[index][0]) + ': ' + num(value), true);
  }

  function cumulativeRead(state, heights) {
    state.reads = heights;
    var words = heights.map(function (height) {
      var across = readAcross(state.points, height);
      return across === null ? '' : 'across from ' + num(height) + ': about ' + num(Math.round(across * 10) / 10);
    });
    say(state.el, words.join(' · '), true);
  }

  function cumulativeTap(state, key) {
    var parts = key.split(':');
    if (parts[0] === 'cf') { cumulativeRead(state, [+parts[1]]); }
  }

  function cumulativeCheck(state) {
    var right = 0;
    for (var i = 0; i < state.hidden.length; i++) {
      var index = state.hidden[i];
      state.marks[index] = state.points[index][1] === state.spec.points[index][1];
      if (state.marks[index]) { right += 1; }
    }
    return [right, state.hidden.length];
  }

  function cumulativeShow(state) {
    for (var i = 0; i < state.hidden.length; i++) {
      state.points[state.hidden[i]][1] = state.spec.points[state.hidden[i]][1];
    }
  }

  // ---- Box plots -------------------------------------------------------------------------------------

  var BOX_NAMES = ['Lowest', 'Lower quartile', 'Median', 'Upper quartile', 'Highest'];
  var BOX_TAGS = ['L', 'Q1', 'M', 'Q3', 'H'];

  function boxSetup(state) {
    state.groups = state.spec.groups.map(function (group) { return group.five.slice(); });
    state.marks = {};
    state.hidden = [];
    if (state.spec.complete) {
      var axis = state.spec.x;
      state.hidden = [0, 1, 2, 3, 4];
      for (var i = 0; i < 5; i++) {
        state.groups[0][i] = snap(axis[0] + (axis[1] - axis[0]) * (i + 1) / 6, state.spec.snap || 1);
      }
    }
  }

  function drawBox(state) {
    var spec = state.spec;
    var groups = state.groups;
    var band = spec.complete ? 120 : 76;
    var width = chartWidth(state);
    var f = {w: width, h: 30 + band * groups.length + 50, left: 16, right: 18, top: 20, bottom: 50};
    var sx = scaleX(f, spec.x);
    var body = xAxis(f, spec.x, sx, spec.x_label, true);
    state.handles = [];
    for (var g = 0; g < groups.length; g++) {
      var five = groups[g];
      var bandTop = f.top + g * band;
      var top = bandTop + 10 + (spec.complete ? 26 : 18), height = 34, mid = top + height / 2;
      var colour = colourOf(state, g);
      var lo = Math.min.apply(null, five), hi = Math.max.apply(null, five);
      // Tap areas: each of the five values owns the stretch nearest to it.
      var order = [0, 1, 2, 3, 4].sort(function (a, b) { return five[a] - five[b]; });
      for (var o = 0; o < 5; o++) {
        var here = sx(five[order[o]]);
        var from = o === 0 ? f.left : (sx(five[order[o - 1]]) + here) / 2;
        var to = o === 4 ? f.w - f.right : (here + sx(five[order[o + 1]])) / 2;
        body += hit(from, bandTop, to - from, band, 'box:' + g + ':' + order[o]);
      }
      body += text(f.left, top - 8, spec.groups[g].name, 'start', ' font-size="14" font-weight="600"');
      body += line(sx(lo), mid, sx(hi), mid, '', ' stroke="' + colour + '" stroke-width="2.5"');
      body += '<rect x="' + sx(Math.min(five[1], five[3])) + '" y="' + top + '" width="' + Math.abs(sx(five[3]) - sx(five[1])) +
              '" height="' + height + '" fill="' + colour + '" fill-opacity="0.3" stroke="' + colour + '" stroke-width="2.5"/>';
      for (var m = 0; m < 5; m++) {
        var tall = (m === 0 || m === 4) ? height * 0.6 : height;
        body += line(sx(five[m]), mid - tall / 2, sx(five[m]), mid + tall / 2, '',
                     ' stroke="' + colour + '" stroke-width="' + (m === 2 ? 4 : 2.5) + '"');
      }
      if (spec.complete && g === 0) {
        for (var h = 0; h < 5; h++) {
          var hx = sx(five[h]), hy = mid + height / 2 + 18 + (h % 2) * 26;
          body += line(hx, mid + height / 2, hx, hy, '', ' stroke="' + colour + '" stroke-width="1.5" stroke-dasharray="3 3"');
          state.handles.push({id: h, x: hx, y: hy, mark: state.marks[h], tag: BOX_TAGS[h]});
        }
      }
    }
    state.frame = f;
    return svg(f, body);
  }

  function boxDrag(state, index, x, y) {
    var axis = state.spec.x;
    state.groups[0][index] = clamp(snap(unscaleX(state.frame, axis, x), state.spec.snap || 1), axis[0], axis[1]);
    delete state.marks[index];
    say(state.el, BOX_NAMES[index] + ': ' + num(state.groups[0][index]), true);
  }

  function boxTap(state, key) {
    var parts = key.split(':');
    if (parts[0] !== 'box') { return; }
    var g = +parts[1], m = +parts[2];
    say(state.el, state.spec.groups[g].name + ': ' + BOX_NAMES[m].toLowerCase() + ' ' + num(state.groups[g][m]), true);
  }

  function boxCheck(state) {
    var right = 0, step = state.spec.snap || 1;
    for (var i = 0; i < 5; i++) {
      state.marks[i] = Math.abs(state.groups[0][i] - state.spec.groups[0].five[i]) <= step / 2 + 1e-6;
      if (state.marks[i]) { right += 1; }
    }
    return [right, 5];
  }

  function boxShow(state) { state.groups[0] = state.spec.groups[0].five.slice(); }

  // ---- Scatter graphs ---------------------------------------------------------------------------------

  function scatterSetup(state) {
    state.hidden = state.spec.hidden || [];
    state.placed = [];
    state.marks = {};
    state.fit = false;
  }

  function cross(x, y, colour, size, width) {
    return line(x - size, y - size, x + size, y + size, '', ' stroke="' + colour + '" stroke-width="' + width + '"') +
           line(x - size, y + size, x + size, y - size, '', ' stroke="' + colour + '" stroke-width="' + width + '"');
  }

  function drawScatter(state) {
    var spec = state.spec;
    var f = frame(state, 50);
    var sx = scaleX(f, spec.x), sy = scaleY(f, spec.y);
    var body = '';
    if (state.hidden.length) {
      // Graph paper: one cell per place a cross can go; a tap plots in the cell it lands on.
      var stepX = spec.snap[0], stepY = spec.snap[1];
      var cellW = sx(spec.x[0] + stepX) - sx(spec.x[0]), cellH = sy(spec.y[0]) - sy(spec.y[0] + stepY);
      for (var gx = spec.x[0]; gx <= spec.x[1] + 1e-9; gx += stepX) {
        body += line(sx(gx), f.top, sx(gx), f.h - f.bottom, 'ch-grid', ' stroke-opacity="0.35"');
      }
      for (var gy = spec.y[0]; gy <= spec.y[1] + 1e-9; gy += stepY) {
        body += line(f.left, sy(gy), f.w - f.right, sy(gy), 'ch-grid', ' stroke-opacity="0.35"');
      }
      for (var cx = spec.x[0]; cx <= spec.x[1] + 1e-9; cx += stepX) {
        for (var cy = spec.y[0]; cy <= spec.y[1] + 1e-9; cy += stepY) {
          body += hit(sx(cx) - cellW / 2, sy(cy) - cellH / 2, cellW, cellH,
                      'cell:' + snap(cx, stepX) + ':' + snap(cy, stepY));
        }
      }
    }
    body += yAxis(f, spec.y, sy, spec.y_label) + xAxis(f, spec.x, sx, spec.x_label, true);
    if (state.fit && spec.fit) {
      var m = spec.fit[0], c = spec.fit[1];
      var x0 = spec.x[0], x1 = spec.x[1];
      var y0 = clamp(m * x0 + c, spec.y[0], spec.y[1]), y1 = clamp(m * x1 + c, spec.y[0], spec.y[1]);
      if (m !== 0) { x0 = (y0 - c) / m; x1 = (y1 - c) / m; }
      body += line(sx(x0), sy(y0), sx(x1), sy(y1), '', ' stroke="' + PALETTE[1] + '" stroke-width="2.5"');
    }
    for (var i = 0; i < spec.points.length; i++) {
      if (state.hidden.indexOf(i) >= 0) { continue; }
      var point = spec.points[i];
      var picked = state.picked === i;
      body += cross(sx(point.x), sy(point.y), picked ? PALETTE[3] : PALETTE[0], picked ? 7 : 5, picked ? 3.5 : 2.5);
      if (!state.hidden.length) {
        body += '<circle cx="' + sx(point.x) + '" cy="' + sy(point.y) + '" r="15" fill="#000" fill-opacity="0" data-t="pt:' + i + '"/>';
      }
    }
    state.handles = [];
    for (var j = 0; j < state.placed.length; j++) {
      state.handles.push({id: j, x: sx(state.placed[j][0]), y: sy(state.placed[j][1]), mark: state.marks[j], cross: true});
    }
    state.frame = f;
    return svg(f, body);
  }

  function scatterTap(state, key) {
    var parts = key.split(':');
    var spec = state.spec;
    if (parts[0] === 'cell') {
      state.placed.push([+parts[1], +parts[2]]);
      state.marks = {};
      say(state.el, 'Plotted (' + num(+parts[1]) + ', ' + num(+parts[2]) + '). ' + state.placed.length + ' of ' +
          spec.hidden.length + ' plotted. Tap a cross to remove it, or drag it.', true);
    } else if (parts[0] === 'pt') {
      var point = spec.points[+parts[1]];
      state.picked = +parts[1];
      say(state.el, point.name + ': (' + num(point.x) + ', ' + num(point.y) + ')', true);
    }
  }

  // A cross tapped without moving comes off again.
  function scatterHandleTap(state, index) {
    state.placed.splice(index, 1);
    state.marks = {};
    say(state.el, 'Removed. ' + state.placed.length + ' of ' + state.spec.hidden.length + ' plotted.', true);
  }

  function scatterDrag(state, index, x, y) {
    var spec = state.spec, f = state.frame;
    var vx = clamp(snap(unscaleX(f, spec.x, x), spec.snap[0]), spec.x[0], spec.x[1]);
    var vy = clamp(snap(unscaleY(f, spec.y, y), spec.snap[1]), spec.y[0], spec.y[1]);
    state.placed[index] = [vx, vy];
    state.marks = {};
    say(state.el, '(' + num(vx) + ', ' + num(vy) + ')', true);
  }

  function scatterCheck(state) {
    var spec = state.spec;
    var free = spec.hidden.slice();
    var right = 0;
    state.marks = {};
    for (var j = 0; j < state.placed.length; j++) {
      state.marks[j] = false;
      for (var k = 0; k < free.length; k++) {
        var target = spec.points[free[k]];
        if (Math.abs(target.x - state.placed[j][0]) <= spec.snap[0] / 2 + 1e-6 &&
            Math.abs(target.y - state.placed[j][1]) <= spec.snap[1] / 2 + 1e-6) {
          state.marks[j] = true;
          free.splice(k, 1);
          right += 1;
          break;
        }
      }
    }
    return [right, spec.hidden.length];
  }

  function scatterShow(state) {
    state.placed = state.spec.hidden.map(function (index) {
      return [state.spec.points[index].x, state.spec.points[index].y];
    });
  }

  // ---- One chart: setup, draw, touch --------------------------------------------------------------------

  function nothing() {}
  var KINDS = {
    bar: {setup: barSetup, draw: drawBars, drag: barDrag, tap: barTap, check: barCheck, show: barShow},
    histogram: {setup: barSetup, draw: drawBars, drag: barDrag, tap: barTap, check: barCheck, show: barShow},
    pie: {setup: pieSetup, draw: drawPie, drag: pieDrag, tap: pieTap, check: pieCheck, show: pieShow},
    cumulative: {setup: cumulativeSetup, draw: drawCumulative, drag: cumulativeDrag, tap: cumulativeTap,
                 check: cumulativeCheck, show: cumulativeShow},
    box: {setup: boxSetup, draw: drawBox, drag: boxDrag, tap: boxTap, check: boxCheck, show: boxShow},
    scatter: {setup: scatterSetup, draw: drawScatter, drag: scatterDrag, tap: scatterTap, check: scatterCheck,
              show: scatterShow, handleTap: scatterHandleTap}
  };

  // Draw the chart, then move the handles on their own layer (never rebuilt
  // mid-drag: the element under the finger must stay in the page).
  function paint(state) {
    state.base.innerHTML = state.kit.draw(state);
    syncHandles(state);
  }

  function syncHandles(state) {
    var over = state.over, f = state.frame;
    over.setAttribute('viewBox', '0 0 ' + f.w + ' ' + f.h);
    var wanted = {};
    var list = state.handles || [];
    for (var i = 0; i < list.length; i++) {
      var h = list[i];
      wanted[h.id] = true;
      var node = state.handleNodes[h.id];
      if (!node) { node = makeHandle(state, h); }
      node.setAttribute('transform', 'translate(' + h.x + ' ' + h.y + ')');
      var cls = h.mark === true ? 'ch-handle ch-good' : h.mark === false ? 'ch-handle ch-bad' : 'ch-handle';
      node.mkDot.setAttribute('class', h.cross ? cls + ' ch-cross' : cls);
    }
    for (var id in state.handleNodes) {
      if (!wanted[id] && !(state.drag && String(state.drag.id) === String(id))) {
        over.removeChild(state.handleNodes[id]);
        delete state.handleNodes[id];
      }
    }
  }

  function makeHandle(state, h) {
    var group = document.createElementNS(SVG, 'g');
    group.setAttribute('data-h', String(h.id));
    var reach = document.createElementNS(SVG, 'circle');
    reach.setAttribute('r', String(HANDLE_REACH));
    reach.setAttribute('fill', '#000');
    reach.setAttribute('fill-opacity', '0');
    group.appendChild(reach);
    var dot;
    if (h.cross) {
      dot = document.createElementNS(SVG, 'path');
      dot.setAttribute('d', 'M-8 -8 L8 8 M-8 8 L8 -8');
    } else {
      dot = document.createElementNS(SVG, 'circle');
      dot.setAttribute('r', String(HANDLE_SIZE));
    }
    group.appendChild(dot);
    group.mkDot = dot;
    if (h.tag) {
      var label = document.createElementNS(SVG, 'text');
      label.setAttribute('y', '4');
      label.setAttribute('text-anchor', 'middle');
      label.setAttribute('font-size', '10');
      label.setAttribute('font-weight', '700');
      label.setAttribute('style', 'fill:#fff');
      label.textContent = h.tag;
      group.appendChild(label);
    }
    state.over.appendChild(group);
    state.handleNodes[h.id] = group;
    return group;
  }

  function redraw(state) {
    if (state.waiting) { return; }
    state.waiting = true;
    (window.requestAnimationFrame || function (fn) { setTimeout(fn, 16); })(function () {
      state.waiting = false;
      paint(state);
    });
  }

  function findHandle(state, id) {
    var list = state.handles || [];
    for (var i = 0; i < list.length; i++) { if (String(list[i].id) === String(id)) { return list[i]; } }
    return null;
  }

  function start(el) {
    var spec;
    try { spec = JSON.parse(el.getAttribute('data-chart')); } catch (error) { return; }
    var box = deal(el);
    var kind = box ? box.getAttribute('data-kind') : 'bar';
    var kit = KINDS[kind];
    if (!kit) { return; }
    el.innerHTML = '<div class="ch-base-wrap"></div><svg class="ch-over" xmlns="' + SVG + '"></svg>';
    var state = {el: el, spec: spec, kind: kind, kit: kit, picked: null, variant: 0,
                 base: el.firstChild, over: el.lastChild, handleNodes: {}, drag: null};
    el.mkChart = state;
    kit.setup(state);
    paint(state);
    attach(state, 0);
  }

  // Hook the chart to editorkit's touch once the shell's ekTouch is there
  // (this script can load before the shell's own script does).
  function attach(state, tries) {
    var el = state.el;
    if (!window.ekTouch) {
      if (tries < 40) { setTimeout(function () { attach(state, tries + 1); }, 50); return; }
      say(el, 'Update Toolbox (editorkit 0.6.0 or later) to tap and drag this chart.', true);
      return;
    }
    // editorkit's touch: taps by the element landed on (data-t), drags of
    // handles (data-h) by the finger's movement in CSS pixels.
    window.ekTouch.surface(el, {
      grab: function (id) {
        var handle = findHandle(state, id);
        if (!handle) { return false; }
        // Drawing units per CSS pixel: the drawing is as wide as the chart.
        state.drag = {id: handle.id, x: handle.x, y: handle.y,
                      units: state.frame.w / (el.offsetWidth || state.frame.w)};
        return true;
      },
      move: function (id, dx, dy) {
        var drag = state.drag;
        if (!drag) { return; }
        state.kit.drag(state, drag.id, drag.x + dx * drag.units, drag.y + dy * drag.units);
        el.classList.remove('ch-win');
        redraw(state);
      },
      handleTapped: function () {
        if (state.drag && state.kit.handleTap) { state.kit.handleTap(state, state.drag.id); }
      },
      drop: function () { state.drag = null; redraw(state); },
      tapped: function (key) { state.kit.tap(state, key); redraw(state); }
    });
  }

  // ---- Buttons: tools and questions -------------------------------------------------------------------

  function chartOf(button) {
    var box = deal(button);
    var el = box ? box.querySelector('.ch-chart') : null;
    return el && el.mkChart ? el.mkChart : null;
  }

  function act(button) {
    var action = button.getAttribute('data-ch');
    var box = deal(button);
    var state = chartOf(button);
    if (action === 'opt') { return answer(button); }
    if (action === 'next' || action === 'again') { return nextQuestion(button, action === 'again'); }
    if (action === 'table') {
      var wrap = box.querySelector('.ch-table-wrap');
      if (wrap) { wrap.classList.toggle('ch-hidden'); }
      button.classList.toggle('ch-lit');
      return;
    }
    if (action === 'order') { return orderValues(box, button); }
    if (action === 'value') { button.classList.toggle('ch-on'); return; }
    if (!state) { return; }
    if (action === 'check' || action === 'show') {
      if (action === 'show') { state.kit.show(state); }
      var score = state.kit.check(state);
      var all = score[0] === score[1];
      say(state.el, all ? '✔ All correct!' : score[0] + ' of ' + score[1] + ' right. Move the red ones and check again.', true);
      state.el.classList.toggle('ch-win', all);
      redraw(state);
      return;
    }
    if (action.indexOf('width:') === 0) {
      state.variant = parseInt(action.slice(6), 10);
      barSetup(state);
      var chips = box.querySelectorAll('[data-ch^="width:"]');
      for (var i = 0; i < chips.length; i++) { chips[i].classList.toggle('ch-lit', chips[i] === button); }
      say(state.el, 'Class width ' + num(state.spec.variants[state.variant].width), true);
      redraw(state);
      return;
    }
    if (action === 'median') { cumulativeRead(state, [state.spec.total / 2]); redraw(state); return; }
    if (action === 'quartiles') {
      cumulativeRead(state, [state.spec.total / 4, 3 * state.spec.total / 4]);
      redraw(state);
      return;
    }
    if (action === 'fit') {
      state.fit = !state.fit;
      button.classList.toggle('ch-lit', state.fit);
      redraw(state);
    }
  }

  function answer(option) {
    var card = option.closest('.ch-q');
    if (!card || card.classList.contains('ch-solved') || option.classList.contains('ch-wrong')) { return; }
    if (option.getAttribute('data-right') === '1') {
      option.classList.add('ch-right');
      card.classList.add('ch-solved');
      var others = card.querySelectorAll('.ch-opt');
      for (var i = 0; i < others.length; i++) { if (others[i] !== option) { others[i].classList.add('ch-off'); } }
    } else {
      option.classList.remove('ch-wrong');
      void option.offsetWidth;
      option.classList.add('ch-wrong');
    }
  }

  function nextQuestion(button, again) {
    var list = button.closest('.ch-questions');
    var cards = list.querySelectorAll('.ch-q');
    var current = button.closest('.ch-q');
    for (var i = 0; i < cards.length; i++) {
      if (again) {
        cards[i].classList.remove('ch-solved');
        var options = cards[i].querySelectorAll('.ch-opt');
        for (var j = 0; j < options.length; j++) { options[j].className = 'ch-opt'; }
      }
      cards[i].classList.add('ch-hidden');
    }
    var show = again ? cards[0] : current.nextElementSibling;
    if (show) {
      show.classList.remove('ch-hidden');
      if (show.scrollIntoView) { setTimeout(function () { show.scrollIntoView({block: 'nearest'}); }, 30); }
    }
  }

  function orderValues(box, button) {
    var row = box.querySelector('.ch-values');
    if (!row) { return; }
    var chips = Array.prototype.slice.call(row.querySelectorAll('.ch-value'));
    if (!row.mkOriginal) { row.mkOriginal = chips.slice(); }
    var sorted = !button.classList.contains('ch-lit');
    var order = sorted ? chips.slice().sort(function (a, b) {
      return parseFloat(a.getAttribute('data-v')) - parseFloat(b.getAttribute('data-v'));
    }) : row.mkOriginal;
    for (var i = 0; i < order.length; i++) { row.appendChild(order[i]); }
    button.classList.toggle('ch-lit', sorted);
  }

  // Our buttons (data-ch) act on finger-up through editorkit's touch.buttons,
  // registered once the shell's ekTouch is there (this script loads first).
  var buttonsReady = false;
  function readyButtons(tries) {
    if (buttonsReady) { return; }
    if (window.ekTouch) {
      window.ekTouch.buttons('data-ch', act);
      buttonsReady = true;
    } else if ((tries || 0) < 40) {
      setTimeout(function () { readyButtons((tries || 0) + 1); }, 50);
    }
  }

  // ---- Finding charts as pages appear ----------------------------------------------------------------

  function scan() {
    readyButtons();
    var found = document.querySelectorAll('.ch-chart:not([data-ch-done])');
    for (var i = 0; i < found.length; i++) {
      found[i].setAttribute('data-ch-done', '1');
      start(found[i]);
    }
  }
  if (window.MutationObserver) {
    new MutationObserver(scan).observe(document.documentElement, {childList: true, subtree: true});
  }
  scan();
  window.mkCharts = {start: start, kinds: KINDS, paint: paint};   // for tests and probes
})();
"""
