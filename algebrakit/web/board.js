/* algebrakit board: draws an equation with KaTeX and lets fingers move it.

A board is any element with data-ak-board holding the starting equation
as JSON ({left: [{n, d, v}], right: [...]}). A MutationObserver finds new
boards, so Python only sends HTML and never calls into the page.

Touch grammar (waves 1 and 2):
    tap a term              select it; its valid moves show as pills
    drag a term across =    move it to the other side (sign changes)
    drag towards a like     collect them: it snaps once you are about a
      term                  third of the way there (likeAhead)
    drag a lone 3x under    divide both sides by 3: a dashed bar shows
      the other side        under the other side while 3x is alone
    drag the number in      the same divide, grabbing just the number
      front of a letter
    tap a fraction          simplify it, showing the working: 27/9 becomes
                            (9 x 3)/(9 x 1), the 9s are struck out, then 3
    tap =                   swap the sides
    drag a bracket's 3      expand: 3(x + 4) shows 3 x x + 3 x 4, then
      into the bracket      3x + 12
    drag a bracket's 3      divide both sides by 3 (when the bracket is
      across =              alone on its side)
    drag a term onto an     factorise the side: 6x + 15 becomes 3(2x + 5)
      unlike term beside it
    drag a bracket by its   move the whole bracket to the other side
      parentheses
    drag the 4 of           into the bracket it lands on:
      4(x - 1)(x + 3)       (4x - 4)(x + 3)
    drag a term onto an     factorise every term from the left up to the
      unlike term           further of the two (factoriseReach)
    drag one bracket of a   each of its terms multiplies the other:
      pair onto the other   (x + 2)(x + 3) -> x(x + 3) + 2(x + 3)
    tap a pair, expand      all four products at once: x x x + x x 3 + ...

An expression board (no =) has a goal, expand or factorise, and says so
when it is reached.

The page owns these touches: touchend calls preventDefault so the shell's
fast tap stands aside. Animation is CSS transitions started from here,
never a Python frame loop.
*/
(function () {
  'use strict';

  // --- Feel (editable) --------------------------------------------------------
  var DRAG_START = 8;           // px a finger moves before a touch becomes a drag
  var FLY_MS = 380;             // pieces flying to their new places
  var SNAP_BACK_MS = 260;       // a refused drop returning home
  var NOTE_MS = 2600;           // how long a refusal reason stays up
  var NEAR_TERM = 34;           // px: a drop this close to a term counts as onto it
  var SNAP_PROGRESS = 0.3;      // collect once the finger is this share of the way to a like term
  var SNAP_DRIFT = 70;          // ...and no further than this (px) off the line towards it
  var UNDER_ZONE = 0.55;        // a drop this far below the line (in line heights) divides
  var CANCEL_STEP_MS = 1100;    // each step of a simplification: factor, then strike out
  var EXPAND_STEP_MS = 1100;    // how long 3 x x + 3 x 4 shows before 3x + 12
  var SMALLEST = 0.55;          // a long line shrinks to fit, but no smaller than this
  var HOME_MARGIN = 6;          // px round a piece's own spot: let go there and nothing happens
  var DEBUG_TOUCH = false;      // true: a red dot where the board measures the finger, and its offset

  // Colours for families of like terms (editable). x and x squared keep
  // theirs everywhere; any other family (a, m, y\u00b2...) takes the next
  // colour in order of first appearance on the board, like mathskit's
  // colouring of like terms. Numbers and brackets are coloured by CSS.
  var FAMILY_FIXED = {x1: 'var(--ak-letter)', x2: 'var(--ak-square)'};
  var FAMILY_PALETTE = ['#3fb950', '#f778ba', '#a5d6ff', '#e3b341', '#ff7b72'];

  var E = window.AlgebraEngine;

  // Draw TeX into the live line, shrinking it to fit the board's width
  // (the working for (x + 2)(x + 3) is four products long).
  function render(el, tex) {
    window.katex.render(tex, el, {displayMode: true, trust: true, strict: false,
                                  throwOnError: false});
    var maths = el.querySelector('.katex');
    if (!maths) { return; }
    maths.style.fontSize = '';
    var room = el.clientWidth - 8, wanted = maths.scrollWidth;
    if (wanted > room && room > 0) {
      var size = parseFloat(window.getComputedStyle(maths).fontSize);
      maths.style.fontSize = (size * Math.max(SMALLEST, room / wanted)) + 'px';
    }
  }

  function rectsOf(root, attr) {
    var out = {};
    var base = root.getBoundingClientRect();
    var els = root.querySelectorAll('[data-' + attr + ']');
    for (var i = 0; i < els.length; i++) {
      var r = els[i].getBoundingClientRect();
      out[els[i].getAttribute('data-' + attr)] = {
        left: r.left - base.left, top: r.top - base.top, width: r.width, height: r.height,
        html: els[i].outerHTML
      };
    }
    return out;
  }

  function Board(el, shape) {
    this.el = el;
    this.start = E.make(shape);
    this.restart();
    this.build();
    this.draw(null);
  }

  // Draw TeX into the live line and colour each family of like terms.
  Board.prototype.show = function (tex) {
    render(this.live, tex);
    this.paint(this.live);
  };

  Board.prototype.paint = function (root) {
    var colours = this.colours || (this.colours = {});
    var used = Object.keys(colours).length;
    var els = root.querySelectorAll('[data-f]');
    for (var i = 0; i < els.length; i++) {
      var family = els[i].getAttribute('data-f');
      if (family === 'n' || family === 'g') { continue; }
      if (!colours[family]) {
        colours[family] = FAMILY_FIXED[family] || FAMILY_PALETTE[used++ % FAMILY_PALETTE.length];
      }
      els[i].style.color = colours[family];
    }
  };

  // --- Surviving a rebuilt web view -------------------------------------------
  //
  // editorkit swaps in a fresh web view when a window grows (it draws right
  // where a resized old one clips). The page is loaded again, so a board
  // would start over. A board therefore registers in window.ekKeepers: the
  // tile asks the old page for keep() before the swap and hands the result
  // to restore() on the new page, so the working survives a resize.

  Board.prototype.keep = function () {
    if (!document.body.contains(this.el)) { return null; }   // replaced: nothing to keep
    return {eq: this.eq, history: this.history, colours: this.colours || {}};
  };

  Board.prototype.restore = function (kept) {
    if (!kept || !kept.eq) { return; }
    this.eq = kept.eq;
    this.history = kept.history || [];
    this.colours = kept.colours || {};
    this.selected = null;
    this.draw(null);
  };

  Board.prototype.restart = function () {
    this.eq = E.copy(this.start);
    this.history = [];          // [{eq, label}] the lines before this one
    this.selected = null;
  };

  // --- The page parts ---------------------------------------------------------

  Board.prototype.build = function () {
    this.el.innerHTML =
      '<div class="ak-trail"></div>' +
      '<div class="ak-stage"><div class="ak-live"></div><div class="ak-ghosts"></div></div>' +
      '<div class="ak-note"></div>' +
      '<div class="ak-pills"></div>' +
      '<div class="ak-tools">' +
      '<span class="ak-tool" data-ak-tool="undo">Undo</span>' +
      '<span class="ak-tool" data-ak-tool="restart">Restart</span></div>';
    this.trail = this.el.querySelector('.ak-trail');
    this.stage = this.el.querySelector('.ak-stage');
    this.live = this.el.querySelector('.ak-live');
    this.ghosts = this.el.querySelector('.ak-ghosts');
    this.note = this.el.querySelector('.ak-note');
    this.pills = this.el.querySelector('.ak-pills');
    this.listen();
  };

  Board.prototype.draw = function (result, overrides) {
    var before = result ? rectsOf(this.stage, 't') : null;
    var factorsBefore = result ? rectsOf(this.stage, 'k') : null;
    this.show(E.tex(this.eq, overrides));
    this.drawTrail();
    this.drawPills();
    this.markSelected();
    var answer = E.solved(this.eq);
    var finished = E.finished(this.eq);
    this.el.classList.toggle('ak-solved', !!(answer || finished));
    if (finished) { this.say(finished, true); }
    if (answer && !answer.flipped) {
      this.say('Solved: ' + answer.letter + ' = ' + answer.value.replace('-', '\u2212'), true);
    } else if (answer) {
      this.say('Tap = to swap the sides and finish.', true);
    }
    if (result) { this.animate(before, result.effects || {}, factorsBefore); }
  };

  Board.prototype.drawTrail = function () {
    var html = '';
    for (var i = 0; i < this.history.length; i++) {
      html += '<div class="ak-line"><span class="ak-line-tex" data-ak-line="' + i + '"></span>' +
              '<span class="ak-line-op">' + this.history[i].label + '</span></div>';
    }
    this.trail.innerHTML = html;
    var spans = this.trail.querySelectorAll('[data-ak-line]');
    for (var j = 0; j < spans.length; j++) {
      window.katex.render(E.plainTex(this.history[j].eq), spans[j],
                          {displayMode: false, trust: true, strict: false, throwOnError: false});
    }
  };

  Board.prototype.drawPills = function () {
    var html = '';
    if (this.selected !== null) {
      var moves = E.available(this.eq, this.selected);
      this.moves = moves;
      for (var i = 0; i < moves.length; i++) {
        html += '<span class="ak-pill" data-ak-move="' + i + '">' + moves[i].label + '</span>';
      }
    }
    this.pills.innerHTML = html;
  };

  Board.prototype.markSelected = function () {
    var els = this.live.querySelectorAll('[data-t]');
    for (var i = 0; i < els.length; i++) {
      els[i].classList.toggle('ak-picked', +els[i].getAttribute('data-t') === this.selected);
    }
  };

  Board.prototype.say = function (text, stay) {
    var note = this.note;
    note.textContent = text;
    note.classList.add('ak-note-on');
    clearTimeout(this.noteTimer);
    if (!stay) {
      this.noteTimer = setTimeout(function () { note.classList.remove('ak-note-on'); }, NOTE_MS);
    }
  };

  Board.prototype.hush = function () {
    clearTimeout(this.noteTimer);
    this.note.classList.remove('ak-note-on');
  };

  // --- Moves ------------------------------------------------------------------

  Board.prototype.play = function (move) {
    if (this.busy) { return false; }
    if (move.kind === 'simplify' && !move.shown) { return this.simplifySlowly(move); }
    if (move.kind === 'expand' || move.kind === 'absorb') { return this.expandSlowly(move); }
    var result = E.play(this.eq, move);
    if (!result.ok) {
      this.say(result.reason);
      return false;
    }
    this.history.push({eq: this.eq, label: result.label});
    this.eq = result.eq;
    this.selected = null;
    this.hush();
    this.draw(result);
    return true;
  };

  // Simplifying shows its working before the answer: the fraction is
  // written as common factor times what is left, the common factors are
  // struck out, then the simplified number flies into place. The board
  // ignores touches until it is done.
  Board.prototype.simplifySlowly = function (move) {
    var steps = E.cancelSteps(this.eq, move.args[0]);
    if (!steps) { return this.play({kind: 'simplify', args: move.args, shown: true}); }
    var self = this;
    this.busy = true;
    this.selected = null;
    this.drawPills();
    this.hush();
    this.show(E.tex(this.eq, steps[0]));
    setTimeout(function () {
      self.show(E.tex(self.eq, steps[1]));
      setTimeout(function () {
        self.busy = false;
        self.play({kind: 'simplify', args: move.args, shown: true});
      }, CANCEL_STEP_MS);
    }, CANCEL_STEP_MS);
    return true;
  };

  // Expanding shows its working: the factor flies into each term as
  // 3 x x + 3 x 4, which then settles to 3x + 12.
  Board.prototype.expandSlowly = function (move) {
    var result = E.play(this.eq, move);
    if (!result.ok) { this.say(result.reason); return false; }
    var working = result.working;
    var self = this;
    this.history.push({eq: this.eq, label: result.label});
    this.eq = result.eq;
    this.selected = null;
    this.hush();
    this.busy = true;
    this.draw(result, working);
    setTimeout(function () {
      self.busy = false;
      self.draw({effects: {}});
    }, EXPAND_STEP_MS);
    return true;
  };

  Board.prototype.undo = function () {
    if (this.busy || !this.history.length) { return; }
    var last = this.history.pop();
    this.eq = last.eq;
    this.selected = null;
    this.hush();
    this.draw(null);
  };

  // --- Animation: pieces fly from where they were (FLIP) ----------------------

  Board.prototype.animate = function (before, effects, factorsBefore) {
    var after = rectsOf(this.stage, 't');
    var self = this;
    var flipped = effects.flipped || [];
    var touched = (effects.scaled || []).concat(effects.simplified || []);
    var els = this.live.querySelectorAll('[data-t]');
    for (var i = 0; i < els.length; i++) {
      var id = els[i].getAttribute('data-t');
      var was = before[id], now = after[id];
      var el = els[i];
      if (was && now) {
        el.style.transition = 'none';
        el.style.transform = 'translate(' + (was.left - now.left) + 'px,' +
                             (was.top - now.top) + 'px)';
      } else {
        el.style.transition = 'none';
        el.style.opacity = '0';
      }
      if (flipped.indexOf(+id) >= 0) { el.classList.add('ak-flip'); }
      if (touched.indexOf(+id) >= 0) { el.classList.add('ak-touched'); }
    }
    // Pieces that left the equation (collected into another) fly as ghosts
    // into the piece that took them, then fade.
    var merged = effects.merged || [];
    for (var m = 0; m < merged.length; m++) {
      var from = before[merged[m][0]];
      var into = after[merged[m][1]] || before[merged[m][1]];
      if (from) { this.ghost(from, into); }
    }
    // A bracket's factor, expanded, flies into every term it multiplies.
    var spread = effects.spread || [];
    for (var p = 0; p < spread.length; p++) {
      // From a bracket's factor (3 in 3(x + 4)) or from a term (the 3 of
      // (x + 3), flying into x times 3 and 2 times 3).
      var factor = (factorsBefore || {})[spread[p][0]] || before[spread[p][0]];
      if (!factor || !factor.width) { continue; }
      for (var q = 0; q < spread[p][1].length; q++) {
        if (after[spread[p][1][q]]) { this.ghost(factor, after[spread[p][1][q]]); }
      }
    }
    this.live.getBoundingClientRect();      // apply the starting positions now
    for (var k = 0; k < els.length; k++) {
      els[k].style.transition = 'transform ' + FLY_MS + 'ms cubic-bezier(.2,.8,.2,1), ' +
                                'opacity ' + FLY_MS + 'ms ease';
      els[k].style.transform = '';
      els[k].style.opacity = '';
    }
    setTimeout(function () {
      var done = self.live.querySelectorAll('.ak-flip, .ak-touched');
      for (var j = 0; j < done.length; j++) {
        done[j].classList.remove('ak-flip');
        done[j].classList.remove('ak-touched');
      }
    }, FLY_MS + 400);
  };

  Board.prototype.ghost = function (from, into) {
    var g = document.createElement('div');
    g.className = 'ak-ghost katex';
    g.innerHTML = from.html;
    g.style.left = from.left + 'px';
    g.style.top = from.top + 'px';
    this.ghosts.appendChild(g);
    g.getBoundingClientRect();
    g.style.transition = 'transform ' + FLY_MS + 'ms cubic-bezier(.2,.8,.2,1), opacity ' +
                         FLY_MS + 'ms ease-in';
    if (into) {
      g.style.transform = 'translate(' + (into.left - from.left) + 'px,' +
                          (into.top - from.top) + 'px) scale(0.6)';
    }
    g.style.opacity = '0';
    setTimeout(function () { if (g.parentNode) { g.parentNode.removeChild(g); } }, FLY_MS + 50);
  };

  // --- Touch ------------------------------------------------------------------

  function closest(el, attr) {
    while (el && el.getAttribute) {
      if (el.hasAttribute(attr)) { return el; }
      el = el.parentNode;
    }
    return null;
  }

  Board.prototype.listen = function () {
    var self = this;
    this.el.addEventListener('touchstart', function (e) { self.down(e); }, {passive: false});
    this.el.addEventListener('touchmove', function (e) { self.moveTo(e); }, {passive: false});
    this.el.addEventListener('touchend', function (e) { self.up(e); }, {passive: false});
    this.el.addEventListener('touchcancel', function () { self.cancel(); });
    // Fallback for a click the browser sends (a touch the page did not see).
    this.el.addEventListener('click', function (e) {
      if (Date.now() - (self.lastTouch || 0) < 700) { return; }
      self.tapAt(e.target);
    });
  };

  // --- Where a finger is, in the page's own measure ---------------------------
  //
  // Drops are judged against getBoundingClientRect. In the old UIWebView a
  // touch's clientX/Y can sit well off those rects (seen after editorkit
  // swaps in a fresh web view: CSS zoom on the page, scrolled back), while
  // two things stay true: WebKit hands the touch to the right element, and
  // the finger's movement (clientX/Y differences) is in the rects' measure
  // (the lifted piece follows the finger). So each touch is anchored where
  // it went down: if clientX/Y lands on the touched element it is used as it
  // is; otherwise the offset from it to the centre of that element (a small
  // KaTeX glyph, so within a few px of the finger) is added to every reading.

  function anchor(touch, target) {
    var r = target && target.getBoundingClientRect ? target.getBoundingClientRect() : null;
    if (!r || !r.width) { return [0, 0]; }
    var x = touch.clientX, y = touch.clientY, slack = 4;
    if (x >= r.left - slack && x <= r.right + slack && y >= r.top - slack && y <= r.bottom + slack) {
      return [0, 0];
    }
    return [r.left + r.width / 2 - x, r.top + r.height / 2 - y];
  }

  function at(touch, offset) {
    offset = offset || [0, 0];
    return [touch.clientX + offset[0], touch.clientY + offset[1]];
  }

  Board.prototype.down = function (e) {
    if (this.busy) { e.preventDefault(); return; }
    if (e.touches.length !== 1) { this.cancel(); return; }
    var touch = e.touches[0];
    // What is underneath a term (data-u: the 3 of x/3) drags like its
    // coefficient (data-c) but multiplies instead of dividing.
    var under = closest(e.target, 'data-u');
    var coefficient = under || closest(e.target, 'data-c');
    var factor = closest(e.target, 'data-k');
    var term = closest(e.target, 'data-t');
    if (factor && !factor.getBoundingClientRect().width) { factor = null; }   // (x + 4): no 3
    // Anything inside a bracket lifts the bracket alone (the (x + 1) of
    // a(x + 1)), unless the term touched has a move of its own in there (a
    // like term, or an inside that factorises). The parentheses belong to
    // the whole item, so they still lift a(x + 1) entire.
    var bracket = closest(e.target, 'data-b');
    if (bracket && term && bracket !== term && bracket.contains(term) &&
        !E.insideMoves(this.eq, +term.getAttribute('data-t'))) {
      coefficient = null; under = null; factor = null; term = null;
    } else {
      bracket = null;
    }
    var piece = coefficient || factor || bracket || term;
    this.touch = {
      x: touch.clientX, y: touch.clientY, target: e.target, piece: piece,
      kind: coefficient ? 'coefficient' : factor ? 'factor' : bracket ? 'bracket' : term ? 'term' : null,
      part: under ? 'bottom' : 'top',
      id: coefficient ? +coefficient.getAttribute(under ? 'data-u' : 'data-c') :
          factor ? +factor.getAttribute('data-k') :
          bracket ? +bracket.getAttribute('data-b') :
          term ? +term.getAttribute('data-t') : null,
      dragging: false,
      offset: anchor(touch, e.target)
    };
    if (this.touch.piece) { e.preventDefault(); }   // hold the page still for a drag
  };

  Board.prototype.moveTo = function (e) {
    var t = this.touch;
    if (!t || !t.piece) { return; }
    var touch = e.touches[0];
    var dx = touch.clientX - t.x, dy = touch.clientY - t.y;
    if (!t.dragging && Math.sqrt(dx * dx + dy * dy) < DRAG_START) { return; }
    e.preventDefault();
    if (!t.dragging) { this.lift(t); }
    t.float.style.transform = 'translate(' + dx + 'px,' + dy + 'px) scale(1.12)';
    var p = at(touch, t.offset);
    this.hover(p[0], p[1]);
  };

  Board.prototype.lift = function (t) {
    t.dragging = true;
    var r = t.piece.getBoundingClientRect();
    // The lifted copy rides in the stage, placed against the stage's own
    // rect, never against the window: a fixed element drifted by the page's
    // scroll in a rebuilt web view (the page comes back scrolled), lifting
    // the piece well above the finger. Differences of two rects hold.
    var base = this.stage.getBoundingClientRect();
    var f = document.createElement('div');
    f.className = 'ak-float katex';
    f.innerHTML = t.piece.outerHTML;
    f.style.left = (r.left - base.left) + 'px';
    f.style.top = (r.top - base.top) + 'px';
    f.style.color = window.getComputedStyle(t.piece).color;   // keep its family colour
    this.stage.appendChild(f);
    t.float = f;
    t.home = r;
    t.piece.classList.add('ak-lifted');
    this.hush();
    var part = t.kind === 'bracket' ? 'bracket' : undefined;
    if ((t.kind === 'term' || t.kind === 'bracket') && E.divide(this.eq, t.id, part).ok) { this.showUnder(t); }
  };

  // The dashed bar under the other side: drop a lone 3x here to divide by 3.
  Board.prototype.showUnder = function (t) {
    var found = E.find(this.eq, t.id);
    var side = this.live.querySelector('[data-side="' + found.other + '"]');
    if (!side) { return; }
    var base = this.stage.getBoundingClientRect();
    var r = side.getBoundingClientRect();
    var bar = document.createElement('div');
    bar.className = 'ak-under';
    bar.style.left = (r.left - base.left - 6) + 'px';
    bar.style.width = (r.width + 12) + 'px';
    bar.style.top = (r.bottom - base.top + 6) + 'px';
    bar.textContent = E.divide(this.eq, t.id, t.kind === 'bracket' ? 'bracket' : undefined).label;
    this.ghosts.appendChild(bar);
    t.under = bar;
  };

  Board.prototype.hideUnder = function (t) {
    if (t && t.under && t.under.parentNode) { t.under.parentNode.removeChild(t.under); }
  };

  // Which move a drop at (x, y) would make, or null for no move.
  Board.prototype.dropAt = function (t, x, y) {
    var found = E.find(this.eq, t.id);
    if (!found) { return null; }
    // Put back on its own spot: changed your mind, no move. (The spot is
    // the piece's outline, not a circle round the finger, so a small piece
    // like the 3 in 3(x + 1) can still be dropped on the x right beside it.)
    var home = t.home;
    if (home && x >= home.left - HOME_MARGIN && x <= home.right + HOME_MARGIN &&
        y >= home.top - HOME_MARGIN && y <= home.bottom + HOME_MARGIN) { return null; }
    // Which side of = the finger is on (an expression has one side only).
    var equalsSign = this.live.querySelector('[data-eq]');
    var equals = equalsSign ? equalsSign.getBoundingClientRect() : null;
    var landing = !equals ? found.side : x < equals.left + equals.width / 2 ? 'left' : 'right';
    // One bracket of a pair dropped on the other: each of its terms
    // multiplies the other bracket, (x + 2)(x + 3) -> x(x + 3) + 2(x + 3).
    if (found.product && E.isGroup(found.term)) {
      var other = found.product.factors[1 - found.index];
      return this.overBracket(other.id, x, y, true)
          ? {kind: 'split', args: [found.product.id, t.id]} : null;
    }
    if (t.kind === 'coefficient') {
      return landing !== found.side ? {kind: 'divide', args: [t.id, t.part]} : null;
    }
    if (t.kind === 'factor') {
      if (landing !== found.side) { return {kind: 'divide', args: [t.id, 'factor']}; }
      // The 4 of 4(x - 1)(x + 3) goes into the bracket it is dropped on.
      if (E.isProduct(found.term)) {
        var factors = found.term.factors;
        for (var f = 0; f < factors.length; f++) {
          if (this.overBracket(factors[f].id, x, y, true)) {
            return {kind: 'absorb', args: [t.id, factors[f].id]};
          }
        }
        return null;
      }
      return this.overBracket(t.id, x, y) ? {kind: 'expand', args: [t.id]} : null;
    }
    if (t.kind === 'bracket') {
      // The bracket alone across = divides both sides by it (subject boards;
      // elsewhere the engine says why not).
      return landing !== found.side ? {kind: 'divide', args: [t.id, 'bracket']} : null;
    }
    if (landing !== found.side) {
      var below = y > equals.top + equals.height / 2 + equals.height * UNDER_ZONE;
      if (t.under && below) { return {kind: 'divide', args: [t.id]}; }
      return {kind: 'across', args: [t.id]};
    }
    // Heading for a like term beside it: collect. The most common move,
    // so it snaps on intent rather than waiting for an exact drop.
    var like = this.likeAhead(t, found, x, y);
    if (like !== null) { return {kind: 'collect', args: [t.id, like]}; }
    var onto = this.termNear(x, y, t.id);
    if (onto === null || !E.isTerm(found.term)) { return null; }
    var target = E.find(this.eq, onto);
    // Like terms collect. Unlike pieces in the same place factorise: the
    // side, or inside one bracket the bracket (2(x\u00b2 + 4x + 3) ->
    // 2(x + 1)(x + 3)). When there is nothing to factorise, or the piece
    // dropped on is a bracket, the two swap places, so a student can write
    // a side in any order.
    if (target.list === found.list && !found.product && !E.like(target.term, found.term)) {
      var factorise = null;
      if (E.isTerm(target.term)) {
        factorise = found.group ? {kind: 'factorise', args: [found.group.id]}
                                : {kind: 'factorise', args: [found.side, this.factoriseReach(found, target)]};
      }
      if (factorise && E.play(this.eq, factorise).ok) { return factorise; }
      return {kind: 'reorder', args: [t.id, onto]};
    }
    return {kind: 'collect', args: [t.id, onto]};
  };

  // Which terms a factorise drag acts on (the board's policy; the engine
  // factorises whatever it is given). Everything from the start of the
  // side up to the further right of the two pieces: in 2x\u00b2 - 4x + 8,
  // 4x onto 2x\u00b2 takes 2x\u00b2 - 4x, and 8 onto 4x takes all three.
  Board.prototype.factoriseReach = function (found, target) {
    var last = Math.max(found.index, target.index);
    return found.list.slice(0, last + 1).map(function (t) { return t.id; });
  };

  // Is (x, y) inside the bracket with this id: past its own factor, over
  // the terms it multiplies? Dropping the factor back beside the bracket
  // is not an expand.
  // whole: anywhere over the bracket counts (a bracket of a pair, which
  // has no factor of its own).
  Board.prototype.overBracket = function (id, x, y, whole) {
    var el = this.live.querySelector('[data-t="' + id + '"]');
    var factor = this.live.querySelector('[data-k="' + id + '"]');
    if (!el || (!factor && !whole)) { return false; }
    var r = el.getBoundingClientRect();
    var inside = whole ? r.left - NEAR_TERM / 2 : factor.getBoundingClientRect().right + 4;
    return x >= inside && x <= r.right + NEAR_TERM / 2 &&
           y >= r.top - NEAR_TERM / 2 && y <= r.bottom + NEAR_TERM / 2;
  };

  // The like term (same letters and powers, same side or bracket) the finger
  // is heading for: measured along the line from where the piece started
  // to each like term. Null when none is clearly ahead.
  Board.prototype.likeAhead = function (t, found, x, y) {
    if (!E.isTerm(found.term) || !t.home) { return null; }
    var hx = t.home.left + t.home.width / 2, hy = t.home.top + t.home.height / 2;
    var best = null, bestProgress = SNAP_PROGRESS;
    for (var i = 0; i < found.list.length; i++) {
      var other = found.list[i];
      if (other.id === t.id || !E.like(other, found.term)) { continue; }
      var el = this.live.querySelector('[data-t="' + other.id + '"]');
      if (!el) { continue; }
      var r = el.getBoundingClientRect();
      var dx = r.left + r.width / 2 - hx, dy = r.top + r.height / 2 - hy;
      var length = Math.sqrt(dx * dx + dy * dy) || 1;
      var along = ((x - hx) * dx + (y - hy) * dy) / (length * length);
      var drift = Math.abs((x - hx) * dy - (y - hy) * dx) / length;
      if (along > bestProgress && drift < SNAP_DRIFT) { best = other.id; bestProgress = along; }
    }
    return best;
  };

  // The term under or near a point (not the one being dragged).
  Board.prototype.termNear = function (x, y, skip) {
    var best = null, bestDistance = NEAR_TERM;
    var els = this.live.querySelectorAll('[data-t]');
    for (var i = 0; i < els.length; i++) {
      var id = +els[i].getAttribute('data-t');
      if (id === skip) { continue; }
      var r = els[i].getBoundingClientRect();
      var dx = Math.max(r.left - x, 0, x - r.right);
      var dy = Math.max(r.top - y, 0, y - r.bottom);
      var distance = Math.sqrt(dx * dx + dy * dy);
      if (distance <= bestDistance) { best = id; bestDistance = distance; }
    }
    return best;
  };

  // DEBUG_TOUCH: a red dot where the board measures the finger, and a line
  // over the board with the touch's anchor offset, the page zoom and scroll,
  // and the move it would make. If the dot is not
  // under the finger, the touch maths is wrong; if it is, the move rules are.
  Board.prototype.debugTouch = function (x, y, move) {
    if (!DEBUG_TOUCH) { return; }
    var base = this.stage.getBoundingClientRect();
    var dot = this.dot;
    if (!dot) {
      dot = this.dot = document.createElement('div');
      dot.style.cssText = 'position:absolute;width:12px;height:12px;margin:-6px 0 0 -6px;' +
        'border-radius:6px;background:#ff3b30;z-index:60;pointer-events:none';
      this.stage.appendChild(dot);
    }
    dot.style.left = (x - base.left) + 'px';
    dot.style.top = (y - base.top) + 'px';
    var t = this.touch;
    var line = this.debugLine;
    if (!line) {
      line = this.debugLine = document.createElement('div');
      line.style.cssText = 'font:12px/1.3 -apple-system,sans-serif;color:#ff7b72;text-align:center';
      this.el.insertBefore(line, this.el.firstChild);
    }
    line.textContent = 'offset ' + Math.round(t.offset[0]) + ',' + Math.round(t.offset[1]) +
      ' \u00b7 zoom ' + (document.documentElement.style.zoom || 1) +
      ' \u00b7 scroll ' + Math.round(window.pageYOffset) +
      ' \u00b7 ' + (move ? move.kind : 'no move');
  };

  Board.prototype.hover = function (x, y) {
    var move = this.dropAt(this.touch, x, y);
    this.debugTouch(x, y, move);
    var verdict = move ? E.play(this.eq, move) : null;
    var float = this.touch.float;
    float.classList.toggle('ak-float-yes', !!(verdict && verdict.ok));
    float.classList.toggle('ak-float-no', !!(verdict && !verdict.ok));
    var targets = this.live.querySelectorAll('.ak-target');
    for (var i = 0; i < targets.length; i++) { targets[i].classList.remove('ak-target'); }
    var lit = null;
    if (move && verdict.ok && move.kind === 'collect') { lit = '[data-t="' + move.args[1] + '"]'; }
    if (move && verdict.ok && move.kind === 'expand') { lit = '[data-t="' + move.args[0] + '"]'; }
    if (move && verdict.ok && move.kind === 'split') {
      var pair = E.find(this.eq, move.args[0]).term.factors;
      lit = '[data-t="' + (pair[0].id === move.args[1] ? pair[1].id : pair[0].id) + '"]';
    }
    if (move && verdict.ok && move.kind === 'absorb') { lit = '[data-t="' + move.args[1] + '"]'; }
    if (move && verdict.ok && move.kind === 'factorise') {
      lit = typeof move.args[0] === 'number' ? '[data-t="' + move.args[0] + '"]'
          : move.args[1] ? move.args[1].map(function (id) { return '[data-t="' + id + '"]'; }).join(',')
          : '[data-side="' + move.args[0] + '"]';
    }
    var lights = lit ? this.live.querySelectorAll(lit) : [];
    for (var l = 0; l < lights.length; l++) { lights[l].classList.add('ak-target'); }
    if (this.touch.under) {
      this.touch.under.classList.toggle('ak-under-on', !!(move && move.kind === 'divide'));
    }
    // Say what letting go here would do (or why it cannot), before it happens.
    if (verdict) { this.say(verdict.ok ? verdict.label : verdict.reason, true); }
    else { this.hush(); }
  };

  Board.prototype.up = function (e) {
    this.lastTouch = Date.now();
    var t = this.touch;
    this.touch = null;
    if (!t) { return; }
    if (t.dragging) {
      e.preventDefault();
      var touch = e.changedTouches[0];
      var p = at(touch, t.offset);
      var move = this.dropAt(t, p[0], p[1]);
      var float = t.float;
      t.piece.classList.remove('ak-lifted');
      this.hideUnder(t);
      this.hush();
      if (move && this.play(move)) {
        float.parentNode.removeChild(float);
      } else {
        if (move) { this.say(E.play(this.eq, move).reason); }
        float.style.transition = 'transform ' + SNAP_BACK_MS + 'ms ease';
        float.style.transform = '';
        setTimeout(function () { if (float.parentNode) { float.parentNode.removeChild(float); } },
                   SNAP_BACK_MS + 30);
      }
      return;
    }
    if (this.tapAt(t.target)) { e.preventDefault(); }
  };

  Board.prototype.cancel = function () {
    var t = this.touch;
    this.touch = null;
    if (t && t.float && t.float.parentNode) { t.float.parentNode.removeChild(t.float); }
    if (t && t.piece) { t.piece.classList.remove('ak-lifted'); }
    this.hideUnder(t);
  };

  // A tap: a tool, a pill, =, or a term. True when the board used it.
  Board.prototype.tapAt = function (target) {
    var tool = closest(target, 'data-ak-tool');
    if (tool) {
      var name = tool.getAttribute('data-ak-tool');
      if (name === 'undo') { this.undo(); }
      if (name === 'restart') { this.restart(); this.hush(); this.draw(null); }
      return true;
    }
    var pill = closest(target, 'data-ak-move');
    if (pill) {
      this.play(this.moves[+pill.getAttribute('data-ak-move')]);
      return true;
    }
    if (closest(target, 'data-eq')) {
      this.play({kind: 'swap'});
      return true;
    }
    var term = closest(target, 'data-t');
    if (term) {
      var id = +term.getAttribute('data-t');
      var found = E.find(this.eq, id);
      // A fraction that can be simplified simplifies on a tap.
      if (found && E.simplify(this.eq, id).ok) {
        this.play({kind: 'simplify', args: [id]});
        return true;
      }
      this.selected = this.selected === id ? null : id;
      this.hush();
      this.drawPills();
      this.markSelected();
      return true;
    }
    if (closest(target, 'data-side') || target === this.live) {
      this.selected = null;
      this.drawPills();
      this.markSelected();
      return true;
    }
    return false;
  };

  // --- Finding boards ---------------------------------------------------------

  function wake() {
    if (!window.katex || !window.AlgebraEngine) { return; }
    var all = document.querySelectorAll('[data-ak-board]');
    var keepers = window.ekKeepers = window.ekKeepers || {};
    for (var i = 0; i < all.length; i++) {
      if (all[i].hasAttribute('data-ak-ready')) { continue; }
      all[i].setAttribute('data-ak-ready', '1');
      try {
        var text = all[i].getAttribute('data-ak-board');
        var board = new Board(all[i], JSON.parse(text));
        // Keyed by place and question, so a new question never takes an
        // old board's working.
        keepers['ak-board ' + i + ' ' + text] = board;
      } catch (error) {
        all[i].textContent = 'Board failed: ' + error;
      }
    }
  }

  new MutationObserver(wake).observe(document.documentElement, {childList: true, subtree: true});
  if (document.readyState !== 'loading') { wake(); }
  else { document.addEventListener('DOMContentLoaded', wake); }
})();
