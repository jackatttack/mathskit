/* algebrakit engine: the expression tree and the moves on it. No DOM.

A board holds an equation (two sides) or an expression (one side, with a
goal: expand or factorise). Each side is a list of items:

    term     {id, n, d, l}                   n/d times its letters; l maps
                                             each letter to its power:
                                             {a: 1, b: 1} is ab, {x: 2} is
                                             x squared, {} is a number
    group    {id, kind: 'group', k, terms}   k times a bracket; k is a
                                             monomial {n, d, l}: 3, x, 2ab
             (under: [term], optional)       ...all over a bracket:
                                             (d - b)/(a - c)
    product  {id, kind: 'product', kn, kd,   kn/kd times two brackets
              factors: [group, group]}       multiplied: (x + 2)(x + 3)

    board    {left: [item], right: [item], next: the next free id,
              expression: true for one side, goal: 'expand' | 'factorise',
              subject: a letter to make the subject, or null}

A letter's power can be negative: {v: 1, a: -1} is v/a. Dividing a side
by a letter is how a subject is freed: at = v - u becomes t = (v - u)/a,
the bracket's factor being {n: 1, d: 1, l: {a: -1}}.

Fractions stay unreduced until the student simplifies them (the tree
decides when simplification happens, so each step can be seen and
animated). Items keep their id through every move: the board uses ids to
fly each piece from where it was to where it lands.

Every move returns {ok: true, eq, label, word, effects, working} with a
new board (the old one is never changed), or {ok: false, reason} saying in
plain words why the move is not allowed. working, when present, is TeX to
show for a moment before the result settles (3 x x + 3 x 4).

    across(eq, id)           move a term or bracket to the other side
    collect(eq, from, to)    add a term onto a like term beside it
    divide(eq, id)           divide both sides by what multiplies a side
    expand(eq, id)           multiply out a bracket, or both brackets
    split(eq, id, factorId)  (x + 2)(x + 3) -> x(x + 3) + 2(x + 3)
    absorb(eq, id, factorId) 4(x - 1)(x + 3) -> (4x - 4)(x + 3)
    factorise(eq, side, ids) common factor out, else two brackets; ids
                             (optional) picks which terms of the side
    simplify(eq, id)         reduce a fraction
    swap(eq)                 swap the sides
    reorder(eq, id, otherId) swap two pieces in the same place (a side or
                             one bracket): 3b + 2a -> 2a + 3b
    available(eq, id)        every valid move for one item
    solved(eq), finished(eq) the answer, or the goal reached
*/
(function (root) {
  'use strict';

  var MINUS = '\u2212';
  var TIMES = '\u00d7';
  var CANCEL_COLOUR = '#ff7b72';

  // --- Numbers and monomials ------------------------------------------------

  function gcd(a, b) {
    a = Math.abs(a); b = Math.abs(b);
    while (b) { var t = a % b; a = b; b = t; }
    return a || 1;
  }

  // Keep the denominator positive; never reduce here (simplify does that).
  function normal(n, d) {
    return d < 0 ? {n: -n, d: -d} : {n: n, d: d};
  }

  function isGroup(item) { return item.kind === 'group'; }
  function isProduct(item) { return item.kind === 'product'; }
  function isTerm(item) { return !item.kind; }

  // --- Letters: {a: 1, b: 2} is a b squared. Letters with power 0 are never
  // kept, so {} is a number and two monomials are like exactly when their
  // letter maps match.

  function letterNames(l) { return Object.keys(l).sort(); }

  function copyLetters(l) {
    var out = {};
    letterNames(l).forEach(function (v) { out[v] = l[v]; });
    return out;
  }

  // Total power: 3 for a b squared, 0 for a number.
  function degree(m) {
    return letterNames(m.l).reduce(function (sum, v) { return sum + m.l[v]; }, 0);
  }

  function hasLetters(m) { return letterNames(m.l).length > 0; }

  // Letters on top (positive powers) or underneath (negative powers).
  function topLetters(m) {
    var out = {};
    letterNames(m.l).forEach(function (v) { if (m.l[v] > 0) { out[v] = m.l[v]; } });
    return out;
  }

  function bottomLetters(m) {
    var out = {};
    letterNames(m.l).forEach(function (v) { if (m.l[v] < 0) { out[v] = -m.l[v]; } });
    return out;
  }

  function isEmpty(l) { return Object.keys(l).length === 0; }

  // Is anything written underneath: a number (x/3) or a letter (v/a)?
  function hasBottom(m) { return m.d > 1 || !isEmpty(bottomLetters(m)); }

  // 1 divided by a monomial: 2a becomes 1/(2a), v/a becomes a/v.
  function inverse(m) {
    var f = normal(m.d, m.n);
    var l = {};
    letterNames(m.l).forEach(function (v) { l[v] = -m.l[v]; });
    return {n: f.n, d: f.d, l: l};
  }

  // The family of a monomial's letters, the same for like terms: 'x1',
  // 'x2', 'a1b1', or 'n' for a number. The board colours by family.
  function family(m) {
    var names = letterNames(m.l);
    return names.length ? names.map(function (v) { return v + m.l[v]; }).join('') : 'n';
  }

  function sameLetters(a, b) { return family(a) === family(b); }

  // The only letter of a monomial in one letter (x, 3x\u00b2), else null.
  function onlyLetter(m) {
    var names = letterNames(m.l);
    return names.length === 1 ? names[0] : null;
  }

  // A monomial times a monomial: 3 times 2x is 6x, x times x is x^2,
  // a times b is ab.
  function times(a, b) {
    var f = normal(a.n * b.n, a.d * b.d);
    var l = copyLetters(a.l);
    letterNames(b.l).forEach(function (v) {
      l[v] = (l[v] || 0) + b.l[v];
      if (!l[v]) { delete l[v]; }             // a times 1/a: the a cancels
    });
    return {n: f.n, d: f.d, l: l};
  }

  function monomial(t) { return {n: t.n, d: t.d, l: copyLetters(t.l)}; }

  // A number as a monomial: the factor in front of a pair of brackets.
  function number(n, d) { return {n: n, d: d, l: {}}; }

  // A term with this id and the value of monomial m.
  function termOf(id, m) { return {id: id, n: m.n, d: m.d, l: copyLetters(m.l)}; }

  // One letter to the first power: {x: 1}.
  function single(v) { var l = {}; l[v] = 1; return l; }

  // An item's number: a term's coefficient, a bracket's or product's factor.
  function ratio(item) {
    if (isGroup(item)) { return {n: item.k.n, d: item.k.d}; }
    if (isProduct(item)) { return {n: item.kn, d: item.kd}; }
    return {n: item.n, d: item.d};
  }

  function setRatio(item, f) {
    if (isGroup(item)) { item.k.n = f.n; item.k.d = f.d; }
    else if (isProduct(item)) { item.kn = f.n; item.kd = f.d; }
    else { item.n = f.n; item.d = f.d; }
  }

  function reducible(item) {
    var f = ratio(item);
    return f.d !== 1 && (gcd(f.n, f.d) > 1 || f.n === 0);
  }

  function isOne(item) {
    var f = ratio(item);
    return f.n === f.d && (!isGroup(item) || !hasLetters(item.k));
  }

  function like(a, b) { return isTerm(a) && isTerm(b) && sameLetters(a, b); }

  // --- Building -------------------------------------------------------------

  // From the plain shape Python sends. A term is {n, d, v, p} for one
  // letter (v '' for a number) or {n, d, l} for any letters; a bracket is
  // {k, kd, kv, kp, terms} (or kl for its factor's letters); a product is
  // {k, kd, factors: [bracket, bracket]}; right is null for an expression.
  function lettersFrom(l, v, p) {
    var out = {};
    if (l) {
      Object.keys(l).forEach(function (name) { if (l[name]) { out[name] = l[name]; } });
    } else if (v) {
      out[v] = p || 1;
    }
    return out;
  }

  function make(shape) {
    var next = 1;
    function term(t) {
      return {id: next++, n: t.n, d: t.d || 1, l: lettersFrom(t.l, t.v, t.p)};
    }
    function group(t) {
      var g = {id: next++, kind: 'group', terms: []};
      g.k = {n: t.k === undefined ? 1 : t.k, d: t.kd || 1, l: lettersFrom(t.kl, t.kv, t.kp)};
      g.terms = t.terms.map(term);
      if (t.under) { g.under = t.under.map(term); }
      return g;
    }
    function item(t) {
      if (t.factors) {
        var product = {id: next++, kind: 'product', kn: t.k === undefined ? 1 : t.k,
                       kd: t.kd || 1, factors: []};
        product.factors = t.factors.map(group);
        return product;
      }
      return t.terms ? group(t) : term(t);
    }
    var eq = {left: shape.left.map(item), right: (shape.right || []).map(item)};
    eq.expression = !shape.right;
    eq.goal = shape.goal || null;
    eq.subject = shape.subject || null;
    eq.next = next;
    return eq;
  }

  function copyItem(t) {
    if (isGroup(t)) {
      var g = {id: t.id, kind: 'group', k: monomial(t.k), terms: t.terms.map(copyItem)};
      if (t.under) { g.under = t.under.map(copyItem); }
      return g;
    }
    if (isProduct(t)) {
      return {id: t.id, kind: 'product', kn: t.kn, kd: t.kd, factors: t.factors.map(copyItem)};
    }
    return termOf(t.id, t);
  }

  function copy(eq) {
    return {left: eq.left.map(copyItem), right: eq.right.map(copyItem), next: eq.next,
            expression: eq.expression, goal: eq.goal, subject: eq.subject};
  }

  // Where an item is: its side, the list it sits in (a side, a bracket's
  // terms, or a product's factors), its index there, the bracket it is in
  // and the product it is in (null at the top level).
  function find(eq, id) {
    var sides = ['left', 'right'];
    function at(side, list, index, group, product) {
      return {side: side, other: side === 'left' ? 'right' : 'left', list: list, index: index,
              term: list[index], group: group, product: product};
    }
    function inGroup(side, g, product) {
      for (var j = 0; j < g.terms.length; j++) {
        if (g.terms[j].id === id) { return at(side, g.terms, j, g, product); }
      }
      return null;
    }
    for (var s = 0; s < 2; s++) {
      var items = eq[sides[s]];
      for (var i = 0; i < items.length; i++) {
        var item = items[i];
        if (item.id === id) { return at(sides[s], items, i, null, null); }
        if (isGroup(item)) {
          var found = inGroup(sides[s], item, null);
          if (found) { return found; }
        }
        if (isProduct(item)) {
          for (var f = 0; f < item.factors.length; f++) {
            if (item.factors[f].id === id) { return at(sides[s], item.factors, f, null, item); }
            var inner = inGroup(sides[s], item.factors[f], item);
            if (inner) { return inner; }
          }
        }
      }
    }
    return null;
  }

  function fail(reason) { return {ok: false, reason: reason}; }

  function done(eq, label, word, effects, working) {
    return {ok: true, eq: eq, label: label, word: word, effects: effects || {},
            working: working || null};
  }

  // --- Words for a move -----------------------------------------------------

  function numberText(n, d) {
    var f = normal(n, d);
    var g = gcd(f.n, f.d);
    f = {n: f.n / g, d: f.d / g};
    return f.d === 1 ? String(f.n) : f.n + '/' + f.d;
  }

  var SQUARES = {2: '\u00b2', 3: '\u00b3'};

  // ab, x\u00b2, a\u00b2b: letters (a map of positive powers) in
  // alphabetical order.
  function powersText(l) {
    return letterNames(l).map(function (v) {
      var p = l[v];
      return v + (p === 1 ? '' : (SQUARES[p] || '^' + p));
    }).join('');
  }

  // The letters of a monomial as written: ab, x\u00b2, or 1/a when the
  // letter is underneath.
  function lettersText(m) {
    return monoText({n: 1, d: 1, l: m.l});
  }

  // A monomial without its sign: 3x, x\u00b2, 7, 2x/3, v/a, 2A/b (as it is
  // written: letters with negative powers go underneath).
  function monoText(m) {
    var parts = numberText(Math.abs(m.n), m.d).split('/');
    var upper = powersText(topLetters(m)), lower = powersText(bottomLetters(m));
    var top = (parts[0] === '1' && upper ? '' : parts[0]) + upper;
    var bottom = (parts[1] || '') + lower;
    return bottom ? top + '/' + bottom : top;
  }

  function sideText(items) {
    return items.map(function (t, index) {
      var negative = ratio(t).n < 0;
      var sign = index === 0 ? (negative ? MINUS : '') : (negative ? ' ' + MINUS + ' ' : ' + ');
      return sign + bodyText(t);
    }).join('');
  }

  // '3x', 'x\u00b2', '7', '3(x + 4)', '(x + 2)(x + 3)', without a sign.
  function bodyText(item) {
    if (isGroup(item) && item.under) {         // (d - b)/(a - c), 4/(y - 1)
      var unit = item.k.n === item.k.d || -item.k.n === item.k.d;
      var plainTop = unit && isEmpty(item.k.l);
      var inside = sideText(item.terms);
      var over = plainTop ? (item.terms.length > 1 ? '(' + inside + ')' : inside)
                          : monoText(item.k) + '(' + inside + ')';
      return over + '/' + bracketText(item.under);
    }
    if (isGroup(item)) {
      if (hasBottom(item.k)) {                  // (x + 5)/2, (v - u)/a, a(x + 2)/x
        var front = {n: Math.abs(item.k.n), d: 1, l: topLetters(item.k)};
        var top = front.n === 1 && isEmpty(front.l) ? '' : monoText(front);
        var under = (item.k.d > 1 ? item.k.d : '') + powersText(bottomLetters(item.k));
        return top + '(' + sideText(item.terms) + ')/' + under;
      }
      var k = isOne(item) ? '' : monoText(item.k);
      return k + '(' + sideText(item.terms) + ')';
    }
    if (isProduct(item)) {
      var size = numberText(Math.abs(item.kn), item.kd);
      return (size === '1' ? '' : size) +
             item.factors.map(function (f) { return '(' + sideText(f.terms) + ')'; }).join('');
    }
    return monoText(item);
  }

  function bracketText(terms) { return '(' + sideText(terms) + ')'; }

  function byText(n, d) { return numberText(n, d).replace('-', MINUS); }

  // --- Moves ----------------------------------------------------------------

  var NO_EQUALS = 'There is no equals sign here: this is an expression.';
  var INSIDE = 'That is inside a bracket. Expand the bracket first.';

  // Move a term or a bracket to the other side: it lands with its sign changed.
  function across(eq, id) {
    if (eq.expression) { return fail(NO_EQUALS); }
    var found = find(eq, id);
    if (!found) { return fail('That piece is not in the equation.'); }
    if (found.group || found.product) { return fail(INSIDE); }
    var out = copy(eq);
    var item = out[found.side].splice(found.index, 1)[0];
    var f = ratio(item);
    setRatio(item, {n: -f.n, d: f.d});
    var other = out[found.other];
    if (other.length === 1 && isTerm(other[0]) && other[0].n === 0) { other.pop(); }
    other.push(item);
    // Taking +3 from both sides is written -3; taking -3 is written +3.
    var negative = ratio(item).n < 0;
    var op = (negative ? MINUS : '+') + bodyText(item);
    var word = (negative ? 'subtract ' : 'add ') + bodyText(item) + ' on both sides';
    return done(out, op, word, {flipped: [id]});
  }

  // Add one term onto a like term in the same place (same side, or the same
  // bracket).
  function collect(eq, fromId, toId) {
    var from = find(eq, fromId);
    var to = find(eq, toId);
    if (!from || !to || fromId === toId) { return fail('Pick two different pieces.'); }
    if (!isTerm(from.term) || !isTerm(to.term)) {
      return fail('A bracket cannot be collected. Expand it first.');
    }
    if (from.side !== to.side) {
      return fail('Like terms are collected on the same side. Move one across first.');
    }
    if (from.list !== to.list) {
      return fail('One of those is inside a bracket. Expand the bracket first.');
    }
    if (!like(from.term, to.term)) {
      return fail(bodyText(from.term) + ' and ' + bodyText(to.term) + ' are not like terms.');
    }
    var out = copy(eq);
    var list = find(out, toId).list;
    var target = list[to.index];
    var source = list[from.index];
    var sum = target.d === source.d ? {n: target.n + source.n, d: target.d}
                                    : normal(target.n * source.d + source.n * target.d,
                                             target.d * source.d);
    target.n = sum.n;
    target.d = sum.d;
    list.splice(from.index, 1);
    var effects = {merged: [[fromId, toId]]};
    // A sum of nothing disappears, unless it is the last term in a bracket.
    if (target.n === 0 && (list.length > 1 || !from.group)) {
      list.splice(list.indexOf(target), 1);
      effects.vanished = [toId];
    }
    var label = hasLetters(target) ? 'collect ' + lettersText(target) : 'add numbers';
    var word = hasLetters(target) ? 'collect the ' + lettersText(target) + ' terms' : 'add the numbers';
    return done(out, label, word, effects);
  }

  // Divide everything in an item by c = cn/cd (multiply by cd/cn).
  function scale(item, cn, cd) {
    var f = ratio(item);
    setRatio(item, normal(f.n * cd, f.d * cn));
  }

  // Does an item hold the letter anywhere (a term, a bracket's factor or
  // inside it, either bracket of a pair)?
  function holds(item, letter) {
    if (isGroup(item)) {
      return !!item.k.l[letter] || item.terms.concat(item.under || []).some(function (t) { return holds(t, letter); });
    }
    if (isProduct(item)) { return item.factors.some(function (f) { return holds(f, letter); }); }
    return !!item.l[letter];
  }

  // What dividing by this item divides by. A lone term has two pieces a
  // student can drag: its top coefficient (the 3 of 3x; on a subject board
  // everything on top but the subject, the a of at) and what is underneath
  // (the 3 of x/3, the 2 of bh/2). part picks one: 'top' divides both sides
  // by the top coefficient, 'bottom' multiplies both sides by what is
  // underneath, one step each. Without part: the top, unless that is just 1.
  // A lone bracket divides by its factor. Null with a reason when it cannot.
  function divisor(eq, item, part) {
    var subject = eq.subject;
    if (isTerm(item)) {
      var top = {n: item.n, d: 1, l: {}};
      if (subject && item.l[subject] > 0) {
        top.l = topLetters(item);
        delete top.l[subject];
      }
      var bottom = {n: 1, d: item.d, l: {}};
      letterNames(item.l).forEach(function (v) { if (item.l[v] < 0) { bottom.l[v] = item.l[v]; } });
      if (!part) { part = hasBottom(item) && isUnit(top) ? 'bottom' : 'top'; }
      if (part === 'bottom') {
        return hasBottom(item) ? {by: bottom} : {reason: 'Nothing is underneath ' + bodyText(item) + '.'};
      }
      if (!hasLetters(item)) { return {reason: 'Only the number in front of a letter can divide.'}; }
      return {by: top};
    }
    if (isGroup(item)) {
      var k = monomial(item.k);
      if (topLettersHeld(k, subject)) {
        return {reason: 'Dividing by ' + lettersText(item.k) + ' can lose an answer. Expand instead.'};
      }
      return {by: k};
    }
    return {reason: 'Expand the brackets first.'};
  }

  // A bracket's factor may divide by a letter only on a subject board, and
  // never by the subject itself (x(x + 2) = 0 would lose x = 0).
  function topLettersHeld(k, subject) {
    return letterNames(k.l).some(function (v) { return !subject || v === subject; });
  }

  function isUnit(m) { return m.n === m.d && !hasLetters(m); }

  // Divide everything in an item by a number c = cn/cd (multiply by cd/cn).
  function scale(item, cn, cd) {
    var f = ratio(item);
    setRatio(item, normal(f.n * cd, f.d * cn));
  }

  // The words for dividing by c: "multiply both sides by 3" when c is 1/3
  // or 1/a, else "divide both sides by 2/3", "divide both sides by a".
  function divideWords(c) {
    var minus = c.n < 0 ? MINUS : '';
    if (Math.abs(c.n) === 1 && isEmpty(topLetters(c))) {
      var by = minus + monoText({n: c.d, d: 1, l: bottomLetters(c)});
      return {label: TIMES + by, word: 'multiply both sides by ' + by};
    }
    var size = minus + monoText(absolute(c));
    return {label: '\u00f7' + size, word: 'divide both sides by ' + size};
  }

  // Divide both sides by what multiplies the whole of one side: the
  // coefficient of a lone term, or the factor of a lone bracket. On a
  // subject board that can be letters: at = v - u becomes t = (v - u)/a.
  // part ('top' or 'bottom', see divisor) picks which piece of a term.
  function divide(eq, id, part) {
    if (eq.expression) { return fail(NO_EQUALS); }
    var found = find(eq, id);
    if (!found) { return fail('That piece is not in the equation.'); }
    var item = found.term;
    if (found.group || found.product) { return fail(INSIDE); }
    if (isGroup(item) && item.under) { return timesUnder(eq, found); }
    if (isGroup(item) && part === 'bracket') {
      return eq.subject ? divideByBracket(eq, found)
                        : fail('Dividing by a bracket can lose an answer. Expand instead.');
    }
    if (isGroup(item) && eq.subject && part !== 'factor' && item.k.l[eq.subject] > 0) {
      return divideByBracket(eq, found);
    }
    var d = divisor(eq, item, part);
    if (!d.by) { return fail(d.reason); }
    var c = d.by;
    if (isUnit(c)) {
      return fail(isTerm(item) ? lettersText(item) + ' is already on its own.'
                               : 'Nothing multiplies that bracket.');
    }
    if (eq[found.side].length > 1) {
      return fail((c.n < 0 ? MINUS : '') + monoText(c) + ' only multiplies ' + bodyText(item) +
                  ', not the whole side. Clear the rest of the side first.');
    }
    var theirs = eq[found.other];
    var byLetters = hasLetters(c);
    if (byLetters && theirs.some(isProduct)) { return fail('Expand the other side first.'); }
    if (byLetters && theirs.length > 1 && !theirs.every(isTerm)) {
      return fail('Expand the brackets on the other side first.');
    }
    var out = copy(eq);
    var mine = out[found.side][0];
    var effects = {freed: [id]};
    if (isGroup(mine)) {
      out[found.side] = mine.terms;           // the bracket opens: its terms stay
      effects.unwrapped = [id];
    } else {
      // The piece dragged away leaves the term: 3x/3 is x, bh/2 times 2 is
      // bh, 2x/3 over 2 is x/3 (reduced: the student chose to remove it).
      var left = times(mine, inverse(c));
      var g = gcd(left.n, left.d);
      out[found.side][0] = termOf(id, {n: left.n / g, d: left.d / g, l: left.l});
    }
    var other = out[found.other];
    // A whole side over a letter, or over a number on a subject board, is
    // written as one fraction: (v - u)/a, (y + 4)/3. Elsewhere a number
    // divides each term: 3x + 6 = 12 becomes x + 6/3 = 12/3.
    var wrap = byLetters || (eq.subject && other.length > 1 && other.every(isTerm));
    if (!wrap) {
      other.forEach(function (t) { scale(t, c.n, c.d); });
      effects.scaled = other.map(function (t) { return t.id; });
    } else if (other.length === 1 && isTerm(other[0])) {
      other[0] = termOf(other[0].id, times(other[0], inverse(c)));      // 12 over a: 12/a
      effects.scaled = [other[0].id];
    } else if (other.length === 1 && isGroup(other[0])) {
      other[0].k = times(other[0].k, inverse(c));
      effects.scaled = [other[0].id];
    } else {
      // A whole side over a letter is written as one fraction: (v - u)/a.
      var group = {id: out.next++, kind: 'group', k: inverse(c), terms: other};
      out[found.other] = [group];
      effects.gathered = [group.id];
    }
    var words = divideWords(c);
    return done(out, words.label, words.word, effects);
  }

  // Subject boards only: x(a - c) = d - b, the bracket dragged across =,
  // divides both sides by the bracket: x = (d - b)/(a - c). The bracket must
  // not hold the subject (that division could lose an answer).
  function divideByBracket(eq, found) {
    var item = found.term;
    if (eq[found.side].length > 1) {
      return fail(bracketText(item.terms) + ' only multiplies ' + bodyText(item) +
                  ', not the whole side. Clear the rest of the side first.');
    }
    if (item.terms.some(function (t) { return holds(t, eq.subject); })) {
      return fail('That bracket holds ' + eq.subject + ': dividing by it can lose an answer.');
    }
    var theirs = eq[found.other];
    if (!theirs.length || !theirs.every(isTerm)) { return fail('Expand the brackets on the other side first.'); }
    var out = copy(eq);
    var mine = out[found.side][0];
    out[found.side] = [termOf(mine.id, mine.k)];           // x(a - c) leaves x
    var group = {id: out.next++, kind: 'group', k: number(1, 1), terms: out[found.other],
                 under: mine.terms};
    out[found.other] = [group];
    var by = bracketText(item.terms);
    return done(out, '÷' + by, 'divide both sides by ' + by,
                {freed: [found.term.id], gathered: [group.id]});
  }

  // A lone fraction with a bracket underneath: its bottom dragged across =
  // multiplies both sides by that bracket. y = (x + a)/(x + b) becomes
  // y(x + b) = x + a; with several terms on the other side they become a
  // pair of brackets.
  function timesUnder(eq, found) {
    var item = found.term;
    if (eq[found.side].length > 1) {
      return fail(bracketText(item.under) + ' is only under ' + bodyText(item) +
                  ', not the whole side. Clear the rest of the side first.');
    }
    var theirs = eq[found.other];
    if (!theirs.length || !theirs.every(isTerm)) { return fail('Expand the brackets on the other side first.'); }
    var out = copy(eq);
    var mine = out[found.side][0];
    var under = mine.under;
    var plain = mine.k.n === mine.k.d && isEmpty(mine.k.l);
    out[found.side] = plain ? mine.terms
                            : [{id: mine.id, kind: 'group', k: mine.k, terms: mine.terms}];
    var other = out[found.other];
    var landed;
    if (other.length === 1) {
      landed = {id: out.next++, kind: 'group', k: monomial(other[0]), terms: under};
    } else {
      landed = {id: out.next++, kind: 'product', kn: 1, kd: 1,
                factors: [{id: out.next++, kind: 'group', k: number(1, 1), terms: other},
                          {id: out.next++, kind: 'group', k: number(1, 1), terms: under}]};
    }
    out[found.other] = [landed];
    var by = bracketText(item.under);
    return done(out, TIMES + by, 'multiply both sides by ' + by,
                {freed: [item.id], gathered: [landed.id]});
  }

  // TeX for "a x b" shown while expanding: magnitudes only, the sign of the
  // product goes on the term.
  function workingTex(a, b) {
    return monoTex(absolute(a)) + '\\times ' + monoTex(absolute(b));
  }

  function absolute(m) { return {n: Math.abs(m.n), d: m.d, l: m.l}; }

  // Multiply out a bracket (its factor into every term) or a product (every
  // term of one bracket by every term of the other).
  function expand(eq, id) {
    var found = find(eq, id);
    if (found && found.product) { return expand(eq, found.product.id); }   // a bracket of a pair
    if (!found || isTerm(found.term)) { return fail('Only a bracket can be expanded.'); }
    if (found.term.under) { return fail('That fraction has a bracket underneath: multiply it across first.'); }
    var out = copy(eq);
    var list = out[found.side];
    var item = list[found.index];
    var working = {};
    var made = [];
    var effects = {};
    if (isGroup(item)) {
      made = item.terms.map(function (t) {
        var m = times(item.k, t);
        working[t.id] = workingTex(item.k, t);
        return termOf(t.id, m);
      });
      effects.spread = [[id, made.map(function (t) { return t.id; })]];
    } else {
      // Every term of the first bracket times every term of the second.
      // a's terms keep their ids on their first product; b's terms fly as
      // ghosts into every product they make.
      var a = item.factors[0].terms, b = item.factors[1].terms;
      var k = number(item.kn, item.kd);
      var landing = b.map(function () { return []; });
      a.forEach(function (ta) {
        b.forEach(function (tb, j) {
          var m = times(k, times(ta, tb));
          var newId = j === 0 ? ta.id : out.next++;
          working[newId] = (k.n === k.d ? '' : monoTex(absolute(k)) + '\\times ') + workingTex(ta, tb);
          made.push(termOf(newId, m));
          landing[j].push(newId);
        });
      });
      effects.spread = b.map(function (tb, j) { return [tb.id, landing[j]]; });
    }
    Array.prototype.splice.apply(list, [found.index, 1].concat(made));
    return done(out, 'expand', 'expand the brackets', effects, working);
  }

  // (x + 2)(x + 3) -> x(x + 3) + 2(x + 3): each term of one bracket
  // multiplies a copy of the other. factorId is the bracket whose terms
  // spread (the one the student dragged).
  function split(eq, id, factorId) {
    var found = find(eq, id);
    if (!found || !isProduct(found.term)) { return fail('Only two brackets multiplied can be split.'); }
    var out = copy(eq);
    var product = out[found.side][found.index];
    var spreadIndex = product.factors[1].id === factorId ? 1 : 0;
    var spreading = product.factors[spreadIndex];
    var kept = product.factors[1 - spreadIndex];
    var k = number(product.kn, product.kd);
    var spread = [];
    var groups = spreading.terms.map(function (t, i) {
      var g = {id: out.next++, kind: 'group', k: times(k, t),
               terms: kept.terms.map(function (u) {
                 return termOf(i === 0 ? u.id : out.next++, u);
               })};
      spread.push([t.id, [g.id]]);
      return g;
    });
    Array.prototype.splice.apply(out[found.side], [found.index, 1].concat(groups));
    return done(out, TIMES + ' each term', 'multiply each term by the other bracket',
                {spread: spread});
  }

  // The number in front of a pair goes into one of its brackets:
  // 4(x - 1)(x + 3) -> (4x - 4)(x + 3). factorId is that bracket.
  function absorb(eq, id, factorId) {
    var found = find(eq, id);
    if (!found || !isProduct(found.term)) { return fail('Only the number in front of two brackets.'); }
    if (found.term.kn === found.term.kd) { return fail('Nothing multiplies those brackets.'); }
    var out = copy(eq);
    var product = out[found.side][found.index];
    var factor = product.factors.filter(function (f) { return f.id === factorId; })[0];
    if (!factor) { return fail('Drop it on one of the two brackets.'); }
    var k = number(product.kn, product.kd);
    var working = {};
    factor.terms = factor.terms.map(function (t) {
      var m = times(k, t);
      working[t.id] = workingTex(k, t);
      return termOf(t.id, m);
    });
    product.kn = 1;
    product.kd = 1;
    return done(out, monoText(k).replace('-', MINUS) + ' into a bracket',
                'multiply one bracket by ' + monoText(k),
                {spread: [[id, factor.terms.map(function (t) { return t.id; })]]}, working);
  }

  // Quadratic ax^2 + bx + c as two brackets (mx + r)(nx + s), or null.
  function twoBrackets(a, b, c) {
    if (!a || !c) { return null; }
    for (var m = 1; m <= Math.abs(a); m++) {
      if (a % m) { continue; }
      var n = a / m;
      for (var r = -Math.abs(c); r <= Math.abs(c); r++) {
        if (!r || c % r) { continue; }
        var s = c / r;
        if (m * s + n * r === b) { return [[m, r], [n, s]]; }
      }
    }
    return null;
  }

  // ax^2 + bx + c from a list of terms in one letter with powers 0 to 2,
  // at most one of each and whole-number coefficients, or null. q.v is
  // the letter.
  function quadratic(terms) {
    var q = {2: 0, 1: 0, 0: 0, v: ''}, seen = {};
    for (var i = 0; i < terms.length; i++) {
      var t = terms[i];
      if (!isTerm(t) || t.d !== 1) { return null; }
      var p = degree(t), v = onlyLetter(t);
      if (p < 0 || p > 2 || seen[p] || (p && !v) || !isEmpty(bottomLetters(t))) { return null; }
      if (p && q.v && v !== q.v) { return null; }
      if (p) { q.v = v; }
      seen[p] = true;
      q[p] = t.n;
    }
    return q[2] ? q : null;
  }

  function hasLikeTerms(terms) {
    for (var i = 0; i < terms.length; i++) {
      for (var j = i + 1; j < terms.length; j++) {
        if (like(terms[i], terms[j])) { return true; }
      }
    }
    return false;
  }

  // Factorise a side: take out the highest common factor (number and
  // letters) when there is one, else write a quadratic as two brackets.
  // where is a side ('left', 'right'), or the id of a bracket whose inside
  // is a quadratic: 2(x\u00b2 + 3x + 2) becomes 2(x + 1)(x + 2).
  // ids (optional) factorises only those terms of the side, in place:
  // 2x\u00b2 - 4x + 8 with the first two picked gives 2x(x - 2) + 8. Which
  // terms a gesture picks is the board's policy, not the engine's.
  function factorise(eq, where, ids) {
    if (typeof where === 'number') { return factoriseInside(eq, where); }
    var sideName = where;
    var whole = eq[sideName];
    var items = ids ? whole.filter(function (t) { return ids.indexOf(t.id) >= 0; }) : whole;
    if (ids && items.length !== ids.length) {
      return fail('Those are not all on the same side, outside brackets.');
    }
    if (items.length < 2) { return fail('Factorising needs two or more terms.'); }
    for (var i = 0; i < items.length; i++) {
      if (!isTerm(items[i])) { return fail('Expand the brackets on that side first.'); }
      if (items[i].d !== 1) { return fail('Simplify the fractions on that side first.'); }
    }
    if (hasLikeTerms(items)) { return fail('Collect the like terms first.'); }
    var g = items.reduce(function (acc, t) { return gcd(acc, t.n); }, 0);
    // Letters come out too: each letter every term has, to its lowest
    // power. 3a\u00b2 + 6a takes out a; 2ab + 6a\u00b2b takes out ab.
    var shared = {};
    letterNames(items[0].l).forEach(function (v) {
      var lowest = Math.min.apply(null, items.map(function (t) { return t.l[v] || 0; }));
      if (lowest > 0) { shared[v] = lowest; }
    });
    var out = copy(eq);
    var chosen = items.map(function (t) { return t.id; });
    // Put the result where the first chosen term was; the rest leave.
    function replaceChosen(made) {
      var side = out[sideName];
      var at = side.findIndex(function (t) { return chosen.indexOf(t.id) >= 0; });
      out[sideName] = side.filter(function (t, i) { return i < at || chosen.indexOf(t.id) < 0; });
      out[sideName].splice(at, 0, made);
    }
    if (g > 1 || letterNames(shared).length) {
      // A leading minus comes out with the factor: -3x - 6 is -3(x + 2).
      if (items[0].n < 0) { g = -g; }
      var k = {n: g, d: 1, l: shared};
      var group = {id: out.next++, kind: 'group', k: k,
                   terms: out[sideName].filter(function (t) { return chosen.indexOf(t.id) >= 0; })};
      group.terms.forEach(function (t) {
        t.n = t.n / g;
        letterNames(shared).forEach(function (v) {
          t.l[v] -= shared[v];
          if (!t.l[v]) { delete t.l[v]; }
        });
      });
      replaceChosen(group);
      return done(out, 'factorise', 'take out the common factor ' + monoText(k),
                  {gathered: [group.id]});
    }
    var q = quadratic(items);
    if (!q) { return fail(sideText(items) + ' has no common factor.'); }
    var pair = twoBrackets(q[2], q[1], q[0]);
    if (!pair) { return fail(sideText(items) + ' does not factorise.'); }
    var v = q.v;
    function bracket(mr) {
      return {id: out.next++, kind: 'group', k: number(1, 1),
              terms: [termOf(out.next++, {n: mr[0], d: 1, l: single(v)}),
                      termOf(out.next++, number(mr[1], 1))]};
    }
    var product = {id: out.next++, kind: 'product', kn: 1, kd: 1,
                   factors: [bracket(pair[0]), bracket(pair[1])]};
    replaceChosen(product);
    return done(out, 'factorise', 'factorise into two brackets',
                {gathered: [product.id],
                 spread: items.map(function (t) { return [t.id, [product.id]]; })});
  }

  function factoriseInside(eq, id) {
    var found = find(eq, id);
    if (!found || !isGroup(found.term) || found.product || found.term.under) {
      return fail('Pick a bracket to factorise inside.');
    }
    if (hasLetters(found.term.k)) { return fail('Expand the bracket first.'); }
    var q = quadratic(found.term.terms);
    var pair = q && twoBrackets(q[2], q[1], q[0]);
    if (!pair) { return fail('The inside of that bracket does not factorise into two brackets.'); }
    var out = copy(eq);
    var group = find(out, id).term;
    function bracket(mr) {
      return {id: out.next++, kind: 'group', k: number(1, 1),
              terms: [termOf(out.next++, {n: mr[0], d: 1, l: single(q.v)}),
                      termOf(out.next++, number(mr[1], 1))]};
    }
    var product = {id: id, kind: 'product', kn: group.k.n, kd: group.k.d,
                   factors: [bracket(pair[0]), bracket(pair[1])]};
    out[found.side][found.index] = product;
    return done(out, 'factorise', 'factorise the bracket into two',
                {spread: group.terms.map(function (t) { return [t.id, [id]]; })});
  }

  // Reduce a fraction (a coefficient, a number, or a bracket's factor).
  function simplify(eq, id) {
    var found = find(eq, id);
    if (!found) { return fail('That piece is not in the equation.'); }
    if (!reducible(found.term)) { return fail('That is as simple as it gets.'); }
    var out = copy(eq);
    var t = find(out, id).term;
    var f = ratio(t);
    var g = gcd(f.n, f.d);
    var reduced = {n: f.n / g, d: f.d / g};
    if (reduced.n === 0) { reduced.d = 1; }
    setRatio(t, reduced);
    return done(out, 'simplify', 'simplify ' + numberText(f.n, f.d), {simplified: [id]});
  }

  // Swap two pieces that sit in the same list: a side, or the inside of one
  // bracket. Nothing changes value, only the order it is written in. Each
  // piece keeps its own sign: 3b - 2a becomes -2a + 3b.
  function reorder(eq, id, otherId) {
    var a = find(eq, id), b = find(eq, otherId);
    if (!a || !b || id === otherId) { return fail('Pick two different pieces.'); }
    if (a.product || b.product) { return fail('Those are inside two brackets multiplied.'); }
    if (a.side !== b.side || a.group !== b.group) {
      return fail('Pieces swap places on the same side, or inside the same bracket.');
    }
    var out = copy(eq);
    var list = find(out, id).list;
    var first = list[a.index];
    list[a.index] = list[b.index];
    list[b.index] = first;
    return done(out, 'reorder', 'swap ' + bodyText(a.term) + ' and ' + bodyText(b.term),
                {reordered: [id, otherId]});
  }

  function swap(eq) {
    if (eq.expression) { return fail(NO_EQUALS); }
    var out = copy(eq);
    var left = out.left;
    out.left = out.right;
    out.right = left;
    return done(out, 'swap', 'swap the sides', {swapped: true});
  }

  // --- What can be done -----------------------------------------------------

  // Does a term inside a bracket have a move of its own there: a like term
  // to collect, or an inside that factorises (2(x\u00b2 + 4x + 3))? The
  // board lifts the term itself when it does, else the bracket alone.
  function insideMoves(eq, id) {
    var found = find(eq, id);
    if (!found || !found.group || found.product) { return false; }
    var likeInside = found.group.terms.some(function (t) { return t.id !== id && like(t, found.term); });
    return likeInside || factoriseInside(eq, found.group.id).ok;
  }

  // Every valid move for one item, as {kind, args, label}: the pills the
  // board offers when an item is selected. Only valid moves are listed.
  function available(eq, id) {
    var found = find(eq, id);
    if (!found) { return []; }
    var item = found.term;
    var moves = [];
    function offer(move, label) {
      var result = play(eq, move);
      if (result.ok) { moves.push({kind: move.kind, args: move.args, label: label || result.label}); }
    }
    offer({kind: 'across', args: [id]});
    if (isTerm(item)) {
      found.list.forEach(function (other) {
        if (other.id !== id && like(other, item)) { offer({kind: 'collect', args: [id, other.id]}); }
      });
    }
    if (isTerm(item)) {
      offer({kind: 'divide', args: [id, 'top']});
      offer({kind: 'divide', args: [id, 'bottom']});
    } else {
      offer({kind: 'divide', args: [id]});
      if (isGroup(item) && !item.under) { offer({kind: 'divide', args: [id, 'bracket']}); }
    }
    // Expanding is offered from anywhere in a bracket: its factor, its
    // parentheses, or a term inside it.
    var bracket = found.product ? found.product.id : found.group ? found.group.id
                : !isTerm(item) ? id : null;
    if (bracket !== null) { offer({kind: 'expand', args: [bracket]}); }
    if (found.product && !isTerm(item)) {
      offer({kind: 'split', args: [found.product.id, id]});
    }
    if (isProduct(item)) {
      item.factors.forEach(function (f, i) {
        offer({kind: 'absorb', args: [id, f.id]}, monoText(number(item.kn, item.kd)) +
              ' into ' + (i ? '2nd' : '1st'));
      });
    }
    if (reducible(item)) { offer({kind: 'simplify', args: [id]}); }
    if (!found.group && !found.product && isTerm(item)) {
      offer({kind: 'factorise', args: [found.side]});
    }
    if (isGroup(item) && !found.product) { offer({kind: 'factorise', args: [id]}); }
    if (found.group && !found.product) { offer({kind: 'factorise', args: [found.group.id]}); }
    return moves;
  }

  function play(eq, move) {
    var fns = {across: across, collect: collect, divide: divide, expand: expand, split: split,
               absorb: absorb,
               factorise: factorise, simplify: simplify, swap: swap, reorder: reorder};
    return fns[move.kind].apply(null, [eq].concat(move.args || []));
  }

  // The answer once a letter stands alone and the other side is one number
  // in its simplest form. On a subject board: once the subject stands alone
  // and the other side is free of it, with nothing left to simplify (the
  // value is then that side as text: (v - u)/a). Otherwise null.
  function solved(eq) {
    if (eq.expression) { return null; }
    var sides = [['left', 'right'], ['right', 'left']];
    for (var i = 0; i < 2; i++) {
      var mine = eq[sides[i][0]], theirs = eq[sides[i][1]];
      var letterAlone = mine.length === 1 && isTerm(mine[0]) && degree(mine[0]) === 1 &&
                        isOne(mine[0]) && !hasBottom(mine[0]);
      if (!letterAlone) { continue; }
      var letter = onlyLetter(mine[0]);
      if (eq.subject) {
        var free = theirs.length > 0 && theirs.every(function (t) {
          return !holds(t, eq.subject) && !reducible(t);
        });
        if (letter === eq.subject && free) {
          return {letter: letter, value: sideText(theirs), flipped: i === 1};
        }
        continue;
      }
      var numberAlone = theirs.length === 0 ||
          (theirs.length === 1 && isTerm(theirs[0]) && !hasLetters(theirs[0]) &&
           !reducible(theirs[0]));
      if (numberAlone) {
        var value = theirs.length ? numberText(theirs[0].n, theirs[0].d) : '0';
        return {letter: letter, value: value, flipped: i === 1};
      }
    }
    return null;
  }

  // For an expression: the words for its goal once reached, else null.
  //   expand     no brackets, no like terms, no fractions to simplify
  //   simplify   the same, for an expression that starts without brackets
  //   factorise  no common factor or quadratic left to take apart
  var FINISHED = {expand: 'Expanded and simplified', simplify: 'Simplified'};

  function finished(eq) {
    if (!eq.expression || !eq.goal) { return null; }
    var items = eq.left;
    if (FINISHED[eq.goal]) {
      var plain = items.every(function (t) { return isTerm(t) && !reducible(t); });
      return plain && !hasLikeTerms(items) ? FINISHED[eq.goal] : null;
    }
    if (items.length !== 1 || isTerm(items[0])) { return null; }
    var inner = isGroup(items[0]) ? items[0].terms : null;
    if (inner) {
      var q = quadratic(inner);
      var g = inner.reduce(function (acc, t) { return isTerm(t) ? gcd(acc, t.n) : acc; }, 0);
      // A letter in every term inside can still come out: 3(2ab + a).
      var letterLeft = inner.every(isTerm) && letterNames(inner[0].l).some(function (v) {
        return inner.every(function (t) { return t.l[v]; });
      });
      if (g > 1 || letterLeft || (q && twoBrackets(q[2], q[1], q[0]))) { return null; }
    }
    return 'Fully factorised';
  }

  // --- TeX ------------------------------------------------------------------

  // KaTeX for the board. Every item carries data-t (its id) and data-f
  // (its family: letters and powers like x1, a2 or a1b1, n for numbers,
  // g for brackets) so the board
  // can touch, colour and animate it. The number in front of a letter
  // carries data-c, and a bracket's factor carries data-k, so each can be
  // dragged alone. working (optional) maps an id to TeX shown in place of
  // that term's body for a moment: 27/9 as 9 x 3 over 9 x 1, 3 x 4.
  function numberTex(size, d) {
    return d === 1 ? String(size) : '\\frac{' + size + '}{' + d + '}';
  }

  // Letters (a map of positive powers) as TeX: ab, x^{2}y.
  function powersTex(l) {
    return letterNames(l).map(function (v) {
      return l[v] === 1 ? v : v + '^{' + l[v] + '}';
    }).join('');
  }

  // The letters of a monomial on top (positive powers).
  function lettersTex(m) { return powersTex(topLetters(m)); }

  // The top and bottom of a monomial without its sign: 2x/3 is
  // {top: '2x', bottom: '3'}; v/a is {top: 'v', bottom: 'a'}; bottom is ''
  // when nothing is underneath.
  function partsTex(m) {
    var size = Math.abs(m.n);
    var upper = lettersTex(m);
    return {top: (size === 1 && upper ? '' : String(size)) + upper,
            bottom: (m.d > 1 ? String(m.d) : '') + powersTex(bottomLetters(m))};
  }

  // A monomial without its sign, untagged.
  function monoTex(m) {
    if (hasBottom(m)) {
      var parts = partsTex(m);
      return '\\frac{' + parts.top + '}{' + parts.bottom + '}';
    }
    var letters = lettersTex(m);
    var size = Math.abs(m.n);
    if (!letters) { return numberTex(size, m.d); }
    return (size === m.d ? '' : numberTex(size, m.d)) + letters;
  }

  function signTex(negative, index) {
    if (index === 0) { return negative ? '-' : ''; }
    return negative ? '\\:-\\:' : '\\:+\\:';
  }

  // ctx carries working (see above) and the board's subject. A term is
  // written as its coefficient followed by its letters (3 then x), over
  // what is underneath when there is something (x/3, v/a). The coefficient
  // is tagged data-c and what is underneath data-u, so each can be dragged
  // alone: across = the first divides both sides by it, the second
  // multiplies both sides by it. On a subject board everything on top but
  // the subject is the coefficient, and letters keep their alphabetical
  // places: at with subject a tags the t after it.
  function termTex(t, index, ctx) {
    var sign = signTex(t.n < 0, index);
    if (ctx.working[t.id]) {
      return '\\htmlData{t=' + t.id + ', f=' + family(t) + '}{' + sign + ctx.working[t.id] + '}';
    }
    if (!hasLetters(t)) {
      return '\\htmlData{t=' + t.id + ', f=n}{' + sign + numberTex(Math.abs(t.n), t.d) + '}';
    }
    var tag = '\\htmlData{c=' + t.id + '}{';
    var subject = ctx.subject && t.l[ctx.subject] > 0 ? ctx.subject : null;
    // The top: tagged coefficient runs around the letters that stay.
    var size = Math.abs(t.n) === 1 ? '' : String(Math.abs(t.n));
    var first = size, stay = '', rest = '';
    if (subject) {
      var before = {}, after = {}, only = {};
      letterNames(topLetters(t)).forEach(function (v) {
        if (v === subject) { only[v] = t.l[v]; } else { (v < subject ? before : after)[v] = t.l[v]; }
      });
      first = size + powersTex(before);
      stay = powersTex(only);
      rest = powersTex(after);
    } else {
      stay = lettersTex(t);
    }
    var bottom = (t.d > 1 ? String(t.d) : '') + powersTex(bottomLetters(t));
    var inner;
    if (bottom) {
      var top = (first ? tag + first + '}' : '') + stay + (rest ? tag + rest + '}' : '');
      inner = sign + '\\frac{' + top + '}{\\htmlData{u=' + t.id + '}{' + bottom + '}}';
    } else if (first) {
      // A leading minus belongs to the coefficient.
      inner = (index === 0 ? tag + sign + first + '}' : sign + tag + first + '}') + stay +
              (rest ? tag + rest + '}' : '');
    } else {
      inner = sign + stay + (rest ? tag + rest + '}' : '');
    }
    return '\\htmlData{t=' + t.id + ', f=' + family(t) + '}{' + inner + '}';
  }

  function factorTex(id, negative, index, body) {
    var sign = signTex(negative, index);
    return index === 0 ? '\\htmlData{k=' + id + '}{' + sign + body + '}'
                       : sign + '\\htmlData{k=' + id + '}{' + body + '}';
  }

  // A bracket and its terms. tagged: the bracket itself carries data-b (its
  // group's id), so it can be lifted alone, without its factor: the (x + 1)
  // of a(x + 1).
  function bracketTex(group, ctx, tagged) {
    var tex = '\\left(' + group.terms.map(function (t, j) { return termTex(t, j, ctx); }).join('') +
              '\\right)';
    return tagged ? '\\htmlData{b=' + group.id + '}{' + tex + '}' : tex;
  }

  function groupTex(group, index, ctx) {
    if (group.under) {
      // (d - b)/(a - c): the bottom bracket is the group's factor (drag it
      // across to multiply both sides by it). Its terms are not pieces of
      // their own, so their touch data is left off.
      var inside = group.terms.map(function (t, j) { return termTex(t, j, ctx); }).join('');
      var plain = Math.abs(group.k.n) === group.k.d && isEmpty(group.k.l);
      var over = plain ? inside : monoTex(absolute(group.k)) + '\\left(' + inside + '\\right)';
      var bottom = bracketTex({terms: group.under}, ctx).replace(/\\htmlData\{[^}]*\}/g, '');
      return '\\htmlData{t=' + group.id + ', f=g}{' + signTex(group.k.n < 0, index) +
             '\\frac{' + over + '}{\\htmlData{k=' + group.id + '}{' + bottom + '}}}';
    }
    if (hasBottom(group.k)) {
      // (x + 5)/2, (v - u)/a, a(x + 2)/x: the bracket over its bottom,
      // written as a fraction with the bottom as the bracket's factor (drag
      // it across to multiply both sides, or into the top to share it out).
      var terms = group.terms.map(function (t, j) { return termTex(t, j, ctx); }).join('');
      var front = {n: Math.abs(group.k.n), d: 1, l: topLetters(group.k)};
      var top = front.n === 1 && isEmpty(front.l) ? terms
                : monoTex(front) + '\\left(' + terms + '\\right)';
      return '\\htmlData{t=' + group.id + ', f=g}{' + signTex(group.k.n < 0, index) +
             '\\frac{' + top + '}{\\htmlData{k=' + group.id + '}{' + partsTex(group.k).bottom + '}}}';
    }
    var body = isOne(group) ? '' : monoTex(absolute(group.k));
    return '\\htmlData{t=' + group.id + ', f=g}{' + factorTex(group.id, group.k.n < 0, index, body) +
           bracketTex(group, ctx, true) + '}';
  }

  function productTex(product, index, ctx) {
    var size = Math.abs(product.kn);
    var body = size === product.kd ? '' : numberTex(size, product.kd);
    var factors = product.factors.map(function (f) {
      return '\\htmlData{t=' + f.id + ', f=g}{' + bracketTex(f, ctx) + '}';
    }).join('');
    return '\\htmlData{t=' + product.id + ', f=g}{' +
           factorTex(product.id, product.kn < 0, index, body) + factors + '}';
  }

  function sideTex(items, sideName, ctx) {
    var parts = items.map(function (t, index) {
      if (isGroup(t)) { return groupTex(t, index, ctx); }
      if (isProduct(t)) { return productTex(t, index, ctx); }
      return termTex(t, index, ctx);
    });
    var body = parts.length ? parts.join('') : '0';
    return '\\htmlData{side=' + sideName + '}{' + body + '}';
  }

  function tex(eq, working) {
    var ctx = {working: working || {}, subject: eq.subject};
    if (eq.expression) { return sideTex(eq.left, 'left', ctx); }
    return sideTex(eq.left, 'left', ctx) + '\\htmlData{eq=1}{\\;=\\;}' +
           sideTex(eq.right, 'right', ctx);
  }

  // Plain TeX for the written trail: no touch data.
  function plainTex(eq) {
    return tex(eq).replace(/\\htmlData\{[^}]*\}/g, '');
  }

  // The steps of simplifying one fraction, as working for tex():
  // 27/9 -> (9 x 3)/(9 x 1) -> the 9s struck out. Null when it cannot.
  function cancelSteps(eq, id) {
    var found = find(eq, id);
    if (!found || !isTerm(found.term) || !reducible(found.term)) { return null; }
    var t = found.term;
    var size = Math.abs(t.n);
    var g = gcd(size, t.d);
    var top = size / g, bottom = t.d / g;
    function factored(cancelled) {
      var common = cancelled ? '\\textcolor{' + CANCEL_COLOUR + '}{\\cancel{' + g + '}}' : String(g);
      return '\\frac{' + common + '\\times ' + top + '}{' + common + '\\times ' + bottom + '}' +
             lettersTex(t);
    }
    var steps = [{}, {}];
    steps[0][id] = factored(false);
    steps[1][id] = factored(true);
    return steps;
  }

  var Engine = {
    gcd: gcd, make: make, copy: copy, find: find,
    isGroup: isGroup, isProduct: isProduct, isTerm: isTerm,
    like: like, family: family, degree: degree, hasLetters: hasLetters,
    across: across, collect: collect, divide: divide, expand: expand, split: split, absorb: absorb,
    factorise: factorise, simplify: simplify, swap: swap, reorder: reorder,
    available: available, play: play, solved: solved, finished: finished, insideMoves: insideMoves,
    tex: tex, plainTex: plainTex, bodyText: bodyText, cancelSteps: cancelSteps
  };

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = Engine;
  } else {
    root.AlgebraEngine = Engine;
  }
})(this);
