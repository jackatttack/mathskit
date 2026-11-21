/* Engine tests: run with node (off device) from the project folder:

    node tests/engine_test.js

Pythonista cannot run JS headless, so these run wherever node is to hand.
The Python smoke (tests/smoke_board.py) checks the engine file ships and
the page builds.
*/
var E = require('../algebrakit/web/engine.js');
var failures = 0;
function check(ok, what) {
  if (!ok) { failures++; console.log('FAIL ' + what); } else { console.log('ok   ' + what); }
}
function side(eq, name) {
  return eq[name].map(function (t) { return t.n + '/' + t.d + letters(t); }).join(' ');
}
function letters(t) {      // 'x', 'ab', 'x2' for x squared: the term's letters
  return Object.keys(t.l).sort().map(function (v) { return v + (t.l[v] === 1 ? '' : t.l[v]); }).join('');
}

// 3x + 4 = 19
var eq = E.make({left: [{n: 3, v: 'x'}, {n: 4}], right: [{n: 19}]});
var four = eq.left[1].id, three = eq.left[0].id, nineteen = eq.right[0].id;

var r = E.across(eq, four);
check(r.ok && side(r.eq, 'left') === '3/1x' && side(r.eq, 'right') === '19/1 -4/1',
      'across: +4 lands as -4');
check(r.label === '\u22124', 'across label is \u22124');
check(r.eq.right[1].id === four, 'across keeps the id');
check(side(eq, 'left') === '3/1x 4/1', 'old equation untouched');

var c = E.collect(r.eq, four, nineteen);
check(c.ok && side(c.eq, 'right') === '15/1', 'collect: 19 - 4 = 15');
check(c.effects.merged[0][0] === four && c.effects.merged[0][1] === nineteen, 'merge recorded');

var bad = E.divide(eq, three);
check(!bad.ok && /whole side/.test(bad.reason), 'divide refused while side has two terms');

var d = E.divide(c.eq, three);
check(d.ok && side(d.eq, 'left') === '1/1x' && side(d.eq, 'right') === '15/3', 'divide: 15/3 unreduced');
check(d.label === '\u00f73', 'divide label');
check(!E.solved(d.eq), 'not solved while 15/3 unreduced');

var s = E.simplify(d.eq, nineteen);
check(s.ok && side(s.eq, 'right') === '5/1', 'simplify to 5');
check(E.solved(s.eq) && E.solved(s.eq).value === '5', 'solved x = 5');

// 2x + 3 = 5x - 9: unlike terms, cross-side collect refused
var e2 = E.make({left: [{n: 2, v: 'x'}, {n: 3}], right: [{n: 5, v: 'x'}, {n: -9}]});
check(!E.collect(e2, e2.left[0].id, e2.left[1].id).ok, 'unlike terms refused');
check(/same side/.test(E.collect(e2, e2.left[0].id, e2.right[0].id).reason), 'cross-side collect refused');
var a = E.across(e2, e2.left[0].id);
check(a.label === '\u22122x', 'moving 2x reads \u22122x');
var cx = E.collect(a.eq, e2.left[0].id, e2.right[0].id);
check(cx.ok && side(cx.eq, 'right') === '3/1x -9/1', '5x - 2x = 3x');

// cancel to zero
var z = E.make({left: [{n: 2, v: 'x'}, {n: -2, v: 'x'}, {n: 1}], right: [{n: 1}]});
var zz = E.collect(z, z.left[1].id, z.left[0].id);
check(zz.ok && side(zz.eq, 'left') === '1/1' && zz.effects.vanished, '2x - 2x vanishes');

// -x = 4: multiply by -1
var neg = E.make({left: [{n: -1, v: 'x'}], right: [{n: 4}]});
var m = E.divide(neg, neg.left[0].id);
check(m.ok && m.label === '\u00d7\u22121' && side(m.eq, 'right') === '-4/1', '-x = 4 gives x = -4');
check(E.solved(m.eq).value === '-4', 'solved -4');

// 2x = 7 stays a fraction answer
var h = E.make({left: [{n: 2, v: 'x'}], right: [{n: 7}]});
var hd = E.divide(h, h.left[0].id);
check(E.solved(hd.eq) && E.solved(hd.eq).value === '7/2', '7/2 is already simplest');
check(!E.simplify(hd.eq, h.right[0].id).ok, '7/2 cannot simplify');

// 12 = 4x, swap
var sw = E.make({left: [{n: 12}], right: [{n: 4, v: 'x'}]});
var sd = E.divide(sw, sw.right[0].id);
check(E.solved(E.simplify(sd.eq, sw.left[0].id).eq).flipped, '3 = x solved but flipped');

// available lists only valid moves
var av = E.available(e2, e2.left[1].id).map(function (mv) { return mv.kind; });
check(av.join(',') === 'across', '3 alone on its side: only across');
var av2 = E.available(sd.eq, sw.right[0].id);
check(av2.length === 1, 'x alone with coefficient 1: only across');

// TeX carries the touch data, plain TeX does not
var t = E.tex(eq);
check(t.indexOf('\\htmlData{t=1, f=x1}') >= 0 && t.indexOf('c=1') >= 0, 'tex tags term and coefficient');
check(E.plainTex(eq).indexOf('htmlData') < 0, 'plain tex has no tags');
check(E.tex(E.make({left: [], right: [{n: 1}]})).indexOf('{0}') >= 0, 'empty side shows 0');

// Simplifying shows its working: 15/3 -> (3 x 5)/(3 x 1) -> 3s cancelled
var steps = E.cancelSteps(d.eq, nineteen);
check(steps && steps.length === 2, 'two cancel steps');
check(E.tex(d.eq, steps[0]).indexOf('\\frac{3\\times 5}{3\\times 1}') >= 0, 'factored step');
check(E.tex(d.eq, steps[1]).indexOf('\\cancel{3}') >= 0, 'cancel step strikes the 3s');
check(E.cancelSteps(hd.eq, h.right[0].id) === null, 'no steps for 7/2');

// --- Brackets (wave 2) ---
// 3(x + 4) = 21
var b = E.make({left: [{k: 3, terms: [{n: 1, v: 'x'}, {n: 4}]}], right: [{n: 21}]});
var g = b.left[0].id, bx = b.left[0].terms[0].id, b4 = b.left[0].terms[1].id, b21 = b.right[0].id;
check(E.bodyText(b.left[0]) === '3(x + 4)', 'bracket text');
check(!E.across(b, b4).ok && /inside a bracket/.test(E.across(b, b4).reason), 'inner term cannot cross');

var ex = E.expand(b, g);
check(ex.ok && side(ex.eq, 'left') === '3/1x 12/1', 'expand 3(x + 4) = 3x + 12');
check(ex.eq.left[0].id === bx && ex.eq.left[1].id === b4, 'expand keeps inner ids');
var ov = ex.working;
check(E.tex(ex.eq, ov).indexOf('3\\times 4') >= 0 && E.tex(ex.eq, ov).indexOf('3\\times x') >= 0,
      'expand working shows 3 x x + 3 x 4');

var dv = E.divide(b, g);
check(dv.ok && side(dv.eq, 'left') === '1/1x 4/1' && side(dv.eq, 'right') === '21/3', 'divide by bracket factor');
check(dv.label === '\u00f73' && dv.effects.unwrapped[0] === g, 'divide label, bracket opens');

var b2 = E.make({left: [{k: 2, terms: [{n: 1, v: 'x'}, {n: -3}]}, {n: 5}], right: [{n: 1, v: 'x'}]});
check(/whole side/.test(E.divide(b2, b2.left[0].id).reason), 'bracket factor refused when not alone');
var acrossGroup = E.across(b2, b2.left[0].id);
check(acrossGroup.ok && acrossGroup.label === '\u22122(x \u2212 3)', 'bracket crosses as \u22122(x \u2212 3)');
check(E.expand(acrossGroup.eq, b2.left[0].id).eq.right.map(function (t) { return t.n; }).join(',') === '1,-2,6',
      'expanding \u22122(x \u2212 3) gives \u22122x + 6');

// factorise 6x + 15 = 9
var f = E.make({left: [{n: 6, v: 'x'}, {n: 15}], right: [{n: 9}]});
var fz = E.factorise(f, 'left');
check(fz.ok && E.bodyText(fz.eq.left[0]) === '3(2x + 5)', 'factorise 6x + 15 = 3(2x + 5)');
check(fz.eq.left[0].terms[0].id === f.left[0].id, 'factorise keeps term ids');
check(fz.eq.next === f.next + 1 && fz.eq.left[0].id === f.next, 'new bracket gets a fresh id');
var nf = E.make({left: [{n: 6, v: 'x'}, {n: 7}], right: [{n: 9}]});
check(/no common factor/.test(E.factorise(nf, 'left').reason), 'no common factor refused');
check(E.available(f, f.left[1].id).some(function (m) { return m.kind === 'factorise'; }), 'factorise offered');

// collecting inside a bracket, not across its edge
var cb = E.make({left: [{k: 2, terms: [{n: 1, v: 'x'}, {n: 3}, {n: 1}]}, {n: 4}], right: [{n: 20}]});
var inner = cb.left[0].terms;
check(E.collect(cb, inner[2].id, inner[1].id).ok, 'collect inside a bracket');
check(/inside a bracket/.test(E.collect(cb, cb.left[1].id, inner[1].id).reason), 'no collecting across the bracket edge');
check(!E.solved(dv.eq), 'not solved with x + 4');
check(E.tex(b).indexOf('\\left(') >= 0 && E.tex(b).indexOf('k=' + g) >= 0, 'bracket tex tags the factor');

// --- Powers, two brackets, quadratics (wave 2b) ---
function poly(items) {      // {power: coefficient} of a side, for checking
  var out = {};
  function add(p, c) { out[p] = (out[p] || 0) + c; if (!out[p]) { delete out[p]; } }
  items.forEach(function (t) {
    if (E.isTerm(t)) { add(E.degree(t), t.n / t.d); }
    else if (E.isGroup(t)) { t.terms.forEach(function (u) { add(E.degree(u) + E.degree(t.k), t.k.n / t.k.d * u.n / u.d); }); }
    else {
      var a = t.factors[0].terms, bb = t.factors[1].terms;
      a.forEach(function (u) { bb.forEach(function (w) { add(E.degree(u) + E.degree(w), t.kn / t.kd * u.n * w.n / u.d / w.d); }); });
    }
  });
  return JSON.stringify(Object.keys(out).sort().map(function (k) { return k + ':' + out[k]; }));
}
var pair = E.make({left: [{factors: [{terms: [{n: 1, v: 'x'}, {n: 2}]}, {terms: [{n: 1, v: 'x'}, {n: 3}]}]}],
                   right: null, goal: 'expand'});
check(pair.expression && E.bodyText(pair.left[0]) === '(x + 2)(x + 3)', 'expression with two brackets');
check(!E.across(pair, pair.left[0].factors[0].terms[1].id).ok, 'no across in an expression');
var foil = E.expand(pair, pair.left[0].id);
check(foil.ok && foil.eq.left.length === 4 && poly(foil.eq.left) === poly(pair.left), 'expand two brackets: four terms, same value');
check(E.tex(foil.eq, foil.working).indexOf('x\\times x') >= 0 && E.tex(foil.eq).indexOf('x^{2}') >= 0, 'working x \u00d7 x, then x^2');
check(!E.finished(foil.eq), 'not finished with 3x + 2x');
var fx = foil.eq.left.filter(function (t) { return E.degree(t) === 1; });
var tidy = E.collect(foil.eq, fx[1].id, fx[0].id);
check(tidy.ok && E.finished(tidy.eq) === 'Expanded and simplified', 'collect 3x + 2x, expanded and simplified');
check(E.collect(foil.eq, foil.eq.left[0].id, fx[0].id).reason.indexOf('not like terms') >= 0, 'x\u00b2 and x are not like terms');

var halves = E.split(pair, pair.left[0].id, pair.left[0].factors[0].id);
check(halves.ok && halves.eq.left.length === 2 && E.bodyText(halves.eq.left[0]) === 'x(x + 3)' &&
      E.bodyText(halves.eq.left[1]) === '2(x + 3)', 'split: x(x + 3) + 2(x + 3)');
var xin = E.expand(halves.eq, halves.eq.left[0].id);
check(xin.ok && E.bodyText(xin.eq.left[0]) === 'x\u00b2' && E.bodyText(xin.eq.left[1]) === '3x', 'x(x + 3) = x\u00b2 + 3x');
check(poly(halves.eq.left) === poly(pair.left), 'split keeps the value');

var quad = E.make({left: [{n: 1, v: 'x', p: 2}, {n: 5, v: 'x'}, {n: 6}], right: null, goal: 'factorise'});
var fq = E.factorise(quad, 'left');
check(fq.ok && E.bodyText(fq.eq.left[0]) === '(x + 2)(x + 3)' || E.bodyText(fq.eq.left[0]) === '(x + 3)(x + 2)',
      'factorise x\u00b2 + 5x + 6 into two brackets');
check(E.finished(fq.eq) === 'Fully factorised', 'fully factorised');
var dots = E.make({left: [{n: 1, v: 'x', p: 2}, {n: -9}], right: null, goal: 'factorise'});
check(poly(E.factorise(dots, 'left').eq.left) === poly(dots.left), 'difference of two squares');
var ax = E.make({left: [{n: 3, v: 'x', p: 2}, {n: 6, v: 'x'}], right: null, goal: 'factorise'});
var fax = E.factorise(ax, 'left');
check(fax.ok && E.bodyText(fax.eq.left[0]) === '3x(x + 2)', 'common factor 3x');
var a2 = E.make({left: [{n: 2, v: 'x', p: 2}, {n: 7, v: 'x'}, {n: 3}], right: null, goal: 'factorise'});
check(poly(E.factorise(a2, 'left').eq.left) === poly(a2.left), '2x\u00b2 + 7x + 3 factorises');
var big = E.make({left: [{n: 2, v: 'x', p: 2}, {n: 8, v: 'x'}, {n: 6}], right: null, goal: 'factorise'});
var bg = E.factorise(big, 'left');
check(bg.ok && E.bodyText(bg.eq.left[0]) === '2(x\u00b2 + 4x + 3)' && !E.finished(bg.eq), '2(x\u00b2 + 4x + 3) is not fully factorised');
check(/does not factorise/.test(E.factorise(E.make({left: [{n: 1, v: 'x', p: 2}, {n: 1, v: 'x'}, {n: 1}], right: null}), 'left').reason),
      'x\u00b2 + x + 1 does not factorise');

var inside = E.factorise(bg.eq, bg.eq.left[0].id);
check(inside.ok && E.bodyText(inside.eq.left[0]).indexOf('2(x + ') === 0 && E.finished(inside.eq) === 'Fully factorised',
      '2(x\u00b2 + 4x + 3) -> 2(x + 1)(x + 3), fully factorised');
check(poly(inside.eq.left) === poly(big.left), 'inside factorising keeps the value');

// The number in front of a pair into one bracket
var four = E.make({left: [{k: 4, factors: [{terms: [{n: 1, v: 'x'}, {n: -1}]}, {terms: [{n: 1, v: 'x'}, {n: 3}]}]}],
                   right: null, goal: 'expand'});
var into = E.absorb(four, four.left[0].id, four.left[0].factors[0].id);
check(into.ok && E.bodyText(into.eq.left[0]) === '(4x \u2212 4)(x + 3)' && poly(into.eq.left) === poly(four.left),
      '4(x \u2212 1)(x + 3) -> (4x \u2212 4)(x + 3)');
check(E.available(four, four.left[0].id).filter(function (m) { return m.kind === 'absorb'; }).length === 2,
      'absorb offered for each bracket');

// Factorising some terms of a side, by ids
var some = E.make({left: [{n: 2, v: 'x', p: 2}, {n: -4, v: 'x'}, {n: 8}], right: null, goal: 'factorise'});
var firstTwo = E.factorise(some, 'left', [some.left[0].id, some.left[1].id]);
check(firstTwo.ok && E.bodyText(firstTwo.eq.left[0]) === '2x(x \u2212 2)' && firstTwo.eq.left[1].n === 8 &&
      poly(firstTwo.eq.left) === poly(some.left), '2x\u00b2 \u2212 4x picked: 2x(x \u2212 2) + 8');
check(!E.finished(firstTwo.eq), 'partly factorised is not finished');
var lastTwo = E.factorise(some, 'left', [some.left[1].id, some.left[2].id]);
check(lastTwo.ok && E.bodyText(lastTwo.eq.left[1]) === '4(x \u2212 2)' && lastTwo.eq.left[1].k.n === -4 &&
      poly(lastTwo.eq.left) === poly(some.left), 'last two picked: 2x\u00b2 \u2212 4(x \u2212 2)');
check(!E.factorise(some, 'left', [some.left[0].id, 999]).ok, 'unknown ids refused');

// Any letter: families, factorising, the simplify goal
var lettered = E.make({left: [{n: 3, v: 'a', p: 2}, {n: 6, v: 'a'}], right: null, goal: 'factorise'});
var fa = E.factorise(lettered, 'left');
check(fa.ok && E.bodyText(fa.eq.left[0]) === '3a(a + 2)', 'factorise 3a\u00b2 + 6a = 3a(a + 2)');
check(E.tex(lettered).indexOf('f=a2') >= 0, 'family a2');
var mixed = E.make({left: [{n: 2, v: 'm'}, {n: 3, v: 'y'}, {n: 4, v: 'm'}], right: null, goal: 'simplify'});
check(!E.finished(mixed), 'like terms left: not simplified');
var ms = E.collect(mixed, mixed.left[2].id, mixed.left[0].id);
check(ms.ok && E.finished(ms.eq) === 'Simplified', '6m + 3y simplified');
check(/no common factor/.test(E.factorise(mixed, 'left', [mixed.left[0].id, mixed.left[1].id]).reason) ||
      E.factorise(mixed, 'left', [mixed.left[0].id, mixed.left[1].id]).ok === false, '2m + 3y: no common factor');
var qa = E.make({left: [{n: 1, v: 'y', p: 2}, {n: 5, v: 'y'}, {n: 6}], right: null, goal: 'factorise'});
check(E.bodyText(E.factorise(qa, 'left').eq.left[0]).indexOf('(y + ') === 0, 'y\u00b2 + 5y + 6 in y');

// Over a number: x/3 = 10, (3x - 6)/2 = 12 (wave 3's first over pieces)
var over = E.make({left: [{n: 1, d: 3, v: 'x'}], right: [{n: 10}]});
check(E.tex(over).indexOf('\\frac{x}{\\htmlData{u=') >= 0, 'x/3 written as a fraction, the 3 draggable (data-u)');
check(E.bodyText(over.left[0]) === 'x/3', 'x/3 in words');
var om = E.divide(over, over.left[0].id);
check(om.ok && om.word === 'multiply both sides by 3' && E.solved(om.eq).value === '30', 'x/3 = 10 -> x = 30');
var ob = E.make({left: [{k: 1, kd: 2, terms: [{n: 3, v: 'x'}, {n: -6}]}], right: [{n: 12}]});
check(E.bodyText(ob.left[0]) === '(3x \u2212 6)/2', '(3x - 6)/2 in words');
check(E.tex(ob).indexOf('\\htmlData{k=' + ob.left[0].id + '}{2}') >= 0, 'bracket over 2: the 2 draggable');
var obm = E.divide(ob, ob.left[0].id);
check(obm.ok && side(obm.eq, 'left') === '3/1x -6/1' && side(obm.eq, 'right') === '24/1',
      '(3x - 6)/2 = 12 -> 3x - 6 = 24');
var obe = E.expand(ob, ob.left[0].id);
check(obe.ok && side(obe.eq, 'left') === '3/2x -6/2', 'share the 2 out: 3x/2 - 6/2');

// Terms with more than one letter (wave 3): ab, x²y
function word(item) { return E.bodyText(item); }
var ab = E.make({left: [{n: 3, l: {a: 1, b: 1}}, {n: 2, l: {b: 1, a: 1}}, {n: 4, v: 'a'}], right: null,
                 goal: 'simplify'});
check(word(ab.left[0]) === '3ab' && word(ab.left[1]) === '2ab', '3ab and ba written ab');
check(E.tex(ab).indexOf('f=a1b1') >= 0, 'family a1b1');
check(E.like(ab.left[0], ab.left[1]) && !E.like(ab.left[0], ab.left[2]), 'ab and ba like; ab and a not');
var abc = E.collect(ab, ab.left[1].id, ab.left[0].id);
check(abc.ok && word(abc.eq.left[0]) === '5ab' && abc.eq.left.length === 2 && abc.word === 'collect the ab terms',
      '3ab + 2ab = 5ab');
check(E.finished(abc.eq) === 'Simplified', '5ab + 4a simplified');
check(!E.collect(ab, ab.left[2].id, ab.left[0].id).ok, '4a and 3ab refused');
var sq = E.make({left: [{n: 1, l: {x: 2, y: 1}}], right: null});
check(word(sq.left[0]) === 'x²y' && E.tex(sq).indexOf('x^{2}y') >= 0 && E.degree(sq.left[0]) === 3,
      'x²y written and degree 3');

// Expanding with letters
var ea = E.make({left: [{k: 1, kv: 'a', terms: [{n: 1, v: 'b'}, {n: 1, v: 'c'}]}], right: null, goal: 'expand'});
var eae = E.expand(ea, ea.left[0].id);
check(eae.ok && side(eae.eq, 'left') === '1/1ab 1/1ac', 'a(b + c) = ab + ac');
var eb = E.make({left: [{k: 2, kv: 'a', terms: [{n: 3, v: 'b'}, {n: -1, v: 'c'}]}], right: null, goal: 'expand'});
check(side(E.expand(eb, eb.left[0].id).eq, 'left') === '6/1ab -2/1ac', '2a(3b - c) = 6ab - 2ac');
var ec = E.make({left: [{k: 1, kv: 'x', terms: [{n: 1, l: {x: 1, y: 1}}, {n: 2}]}], right: null, goal: 'expand'});
check(side(E.expand(ec, ec.left[0].id).eq, 'left') === '1/1x2y 2/1x', 'x(xy + 2) = x²y + 2x');
var ed = E.make({left: [{factors: [{terms: [{n: 1, v: 'a'}, {n: 1, v: 'b'}]},
                                   {terms: [{n: 1, v: 'a'}, {n: -1, v: 'b'}]}]}], right: null, goal: 'expand'});
var ede = E.expand(ed, ed.left[0].id);
check(ede.ok && side(ede.eq, 'left') === '1/1a2 -1/1ab 1/1ab -1/1b2', '(a + b)(a - b): four products');

// Factorising takes out every shared letter
function factorised(left) {
  var e = E.make({left: left, right: null, goal: 'factorise'});
  var r = E.factorise(e, 'left');
  return r.ok ? word(r.eq.left[0]) : r.reason;
}
check(factorised([{n: 3, l: {a: 1, b: 1}}, {n: 6, v: 'a'}]) === '3a(b + 2)', '3ab + 6a = 3a(b + 2)');
check(factorised([{n: 2, l: {a: 1, b: 1}}, {n: 6, l: {a: 2, b: 1}}]) === '2ab(1 + 3a)', '2ab + 6a²b = 2ab(1 + 3a)');
check(factorised([{n: 4, l: {x: 1, y: 1}}, {n: -6, v: 'y'}]) === '2y(2x − 3)', '4xy - 6y = 2y(2x - 3)');
check(factorised([{n: 1, l: {a: 1, b: 1}}, {n: 1, l: {b: 1, c: 1}}]) === 'b(a + c)', 'ab + bc = b(a + c)');
check(/no common factor/.test(factorised([{n: 1, v: 'a'}, {n: 1, v: 'b'}])), 'a + b: no common factor');

var part = E.make({left: [{k: 3, terms: [{n: 2, l: {a: 1, b: 1}}, {n: 1, v: 'a'}]}], right: null, goal: 'factorise'});
check(E.finished(part) === null, '3(2ab + a) is not fully factorised');
var full = E.make({left: [{k: 3, kv: 'a', terms: [{n: 2, v: 'b'}, {n: 1}]}], right: null, goal: 'factorise'});
check(E.finished(full) === 'Fully factorised', '3a(2b + 1) is fully factorised');

// Reordering: swap two pieces in the same place
var ro = E.make({left: [{n: 3, v: 'b'}, {n: -2, v: 'a'}, {k: 2, terms: [{n: 1, v: 'c'}, {n: 5}]}], right: [{n: 1}]});
var r1 = E.reorder(ro, ro.left[0].id, ro.left[1].id);
check(r1.ok && r1.eq.left[0].n === -2 && E.bodyText(r1.eq.left[0]) === '2a' &&
      E.bodyText(r1.eq.left[1]) === '3b' && r1.eq.left[0].id === ro.left[1].id,
      '3b - 2a -> -2a + 3b, ids kept');
check(E.reorder(ro, ro.left[0].id, ro.left[2].id).ok, 'a term swaps with a bracket on its side');
var inner = ro.left[2].terms;
var r2 = E.reorder(ro, inner[0].id, inner[1].id);
check(r2.ok && E.bodyText(r2.eq.left[2]) === '2(5 + c)', 'inside a bracket: 2(c + 5) -> 2(5 + c)');
check(!E.reorder(ro, ro.left[0].id, ro.right[0].id).ok, 'not across =');
check(!E.reorder(ro, ro.left[0].id, inner[0].id).ok, 'not into a bracket');
check(E.play(ro, {kind: 'reorder', args: [ro.left[0].id, ro.left[1].id]}).ok, 'reorder through play');

// Equations in other letters, and a letter that is not alone
var ey = E.make({left: [{n: 2, v: 'y'}], right: [{n: 8}]});
var eyd = E.divide(ey, ey.left[0].id);
var eys = eyd.ok && E.simplify(eyd.eq, eyd.eq.right[0].id);
check(eys.ok && E.solved(eys.eq).letter === 'y' && E.solved(eys.eq).value === '4', '2y = 8 -> y = 4');
var eab = E.make({left: [{n: 3, l: {a: 1, b: 1}}], right: [{n: 12}]});
var eabd = E.divide(eab, eab.left[0].id);
check(eabd.ok && word(eabd.eq.left[0]) === 'ab' && E.solved(eabd.eq) === null, '3ab = 12 -> ab = 4, not solved');

// Change the subject (wave 3): letters as divisors, a subject board
function board(text) { return E.plainTex(text); }
function moveAll(eq, moves) {      // play [kind, pick] steps, pick(eq) -> args
  var result = {ok: true, eq: eq};
  for (var i = 0; i < moves.length && result.ok; i++) {
    result = E.play(result.eq, {kind: moves[i][0], args: moves[i][1](result.eq)});
  }
  return result;
}
// v = u + at, make t the subject
var suvat = E.make({left: [{n: 1, v: 'v'}], right: [{n: 1, v: 'u'}, {n: 1, l: {a: 1, t: 1}}], subject: 't'});
check(E.tex(suvat).indexOf('\\htmlData{c=3}{a}t') >= 0, 'subject board: the a of at is the coefficient');
var s1 = E.across(suvat, suvat.right[0].id);                  // v - u = at
check(s1.ok && E.solved(s1.eq) === null, 'v - u = at is not done');
var s2 = E.divide(s1.eq, s1.eq.right[0].id);                  // (v - u)/a = t
check(s2.ok && s2.word === 'divide both sides by a' && s2.label === '÷a', 'divide both sides by a');
check(E.bodyText(s2.eq.left[0]) === '(v − u)/a' && E.bodyText(s2.eq.right[0]) === 't',
      '(v - u)/a = t');
check(E.tex(s2.eq).indexOf('\\frac{') >= 0 && E.tex(s2.eq).indexOf('{\\htmlData{k=') >= 0,
      '(v - u)/a written as a fraction, the a draggable');
var s3 = E.solved(s2.eq);
check(s3 && s3.letter === 't' && s3.value === '(v − u)/a' && s3.flipped, 'solved: t = (v - u)/a, after a swap');
var s4 = E.swap(s2.eq);
check(E.solved(s4.eq).flipped === false, 'swapped: t = (v - u)/a');
// multiply back: drag the a of (v - u)/a across
var back = E.divide(s2.eq, s2.eq.left[0].id);
check(back.ok && back.word === 'multiply both sides by a' && E.bodyText(back.eq.right[0]) === 'at',
      'drag the a back: v - u = at');
// share the a out: (v - u)/a -> v/a - u/a
var shared = E.expand(s2.eq, s2.eq.left[0].id);
check(shared.ok && E.bodyText(shared.eq.left[0]) === 'v/a' && E.bodyText(shared.eq.left[1]) === 'u/a',
      'share the a out: v/a - u/a');
check(E.solved(shared.eq).value === 'v/a − u/a', 'v/a - u/a also counts');

// A = bh/2, make h the subject: the 2 and the b are separate drags
var tri = E.make({left: [{n: 1, v: 'A'}], right: [{n: 1, d: 2, l: {b: 1, h: 1}}], subject: 'h'});
check(E.tex(tri).indexOf('\\frac{\\htmlData{c=2}{b}h}{\\htmlData{u=2}{2}}') >= 0,
      'bh/2: the b is the coefficient, the 2 underneath');
var t2 = E.divide(tri, tri.right[0].id, 'bottom');
check(t2.ok && t2.word === 'multiply both sides by 2' && E.bodyText(t2.eq.left[0]) === '2A' &&
      E.bodyText(t2.eq.right[0]) === 'bh', 'drag the 2: 2A = bh');
var th = E.divide(t2.eq, t2.eq.right[0].id, 'top');
check(th.ok && th.word === 'divide both sides by b' && E.solved(th.eq).value === '2A/b',
      'then drag the b: h = 2A/b');
var tb = E.divide(tri, tri.right[0].id, 'top');
check(tb.ok && E.bodyText(tb.eq.left[0]) === 'A/b' && E.bodyText(tb.eq.right[0]) === 'h/2',
      'or the b first: A/b = h/2');
check(!E.divide(E.make({left: [{n: 3, v: 'x'}], right: [{n: 6}]}), 1, 'bottom').ok, 'nothing underneath 3x');
var two3 = E.make({left: [{n: 2, d: 3, v: 'x'}], right: [{n: 8}]});
check(E.tex(two3).indexOf('\\frac{\\htmlData{c=1}{2}x}{\\htmlData{u=1}{3}}') >= 0, '2x/3: 2 and 3 tagged apart');
var tw = E.divide(two3, two3.left[0].id, 'top');
check(tw.ok && E.bodyText(tw.eq.left[0]) === 'x/3' && tw.word === 'divide both sides by 2', '2x/3 = 8: drag the 2 -> x/3');
var tu = E.divide(two3, two3.left[0].id, 'bottom');
check(tu.ok && E.bodyText(tu.eq.left[0]) === '2x' && tu.word === 'multiply both sides by 3', '2x/3 = 8: drag the 3 -> 2x'); 
// y = mx + c, make m the subject: the x of mx is the coefficient
var line = E.make({left: [{n: 1, v: 'y'}], right: [{n: 1, l: {m: 1, x: 1}}, {n: 1, v: 'c'}], subject: 'm'});
check(E.tex(line).indexOf('m\\htmlData{c=2}{x}') >= 0, 'subject m: mx keeps its order, the x is the coefficient');
var lm = moveAll(line, [['across', function (e) { return [e.right[1].id]; }],
                        ['divide', function (e) { return [e.right[0].id]; }]]);
check(lm.ok && E.solved(lm.eq).value === '(y − c)/x', 'y = mx + c -> m = (y - c)/x');
// P = 2l + 2w, make l the subject: a number divides as before
var per = E.make({left: [{n: 1, v: 'P'}], right: [{n: 2, v: 'l'}, {n: 2, v: 'w'}], subject: 'l'});
var pl = moveAll(per, [['across', function (e) { return [e.right[1].id]; }],
                       ['divide', function (e) { return [e.right[0].id]; }]]);
check(pl.ok && E.bodyText(pl.eq.left[0]) === '(P \u2212 2w)/2' && E.solved(pl.eq).value === '(P \u2212 2w)/2',
      'P - 2w = 2l -> l = (P - 2w)/2 (a subject board keeps one fraction)');
var plShare = E.expand(pl.eq, pl.eq.left[0].id);
check(plShare.ok && E.solved(plShare.eq) === null, 'shared out: 2w/2 still to simplify');
var plDone = E.simplify(plShare.eq, plShare.eq.left[1].id);
check(plDone.ok && E.solved(plDone.eq).value === 'P/2 \u2212 w', 'simplified: l = P/2 - w');
var at = E.make({left: [{n: 1, v: 'v'}], right: [{n: 1, l: {a: 1, t: 1}}], subject: 'a'});
check(E.tex(at).indexOf('a\\htmlData{c=2}{t}') >= 0, 'subject a: at keeps its order, the t is the coefficient');
var three = E.make({left: [{n: 3, l: {a: 1, b: 1, c: 1}}], right: [{n: 1, v: 'k'}], subject: 'b'});
check(E.tex(three).indexOf('\\htmlData{c=1}{3a}b\\htmlData{c=1}{c}') >= 0, '3abc, subject b: 3a and c tagged around b');
var plain3 = E.make({left: [{n: 3, v: 'x'}, {n: 6}], right: [{n: 12}]});
var p3 = E.divide(E.across(plain3, plain3.left[1].id).eq, plain3.left[0].id);
check(p3.ok && p3.eq.right.length === 2, 'no subject: a number still divides each term');
// V = IR: a single term over a letter
var ohm = E.make({left: [{n: 1, v: 'V'}], right: [{n: 1, l: {I: 1, R: 1}}], subject: 'R'});
var or = E.divide(ohm, ohm.right[0].id);
check(or.ok && E.bodyText(or.eq.left[0]) === 'V/I' && E.solved(or.eq).value === 'V/I', 'V = IR -> R = V/I');
// Refusals
check(!E.divide(suvat, suvat.right[1].id).ok, 'cannot divide while u is on the side');
var xx = E.make({left: [{k: 1, kv: 'x', terms: [{n: 1, v: 'x'}, {n: 2}]}], right: [{n: 0}], subject: 'x'});
check(!E.divide(xx, xx.left[0].id).ok, 'never divide by the subject itself');
var plain = E.make({left: [{k: 1, kv: 'x', terms: [{n: 1, v: 'x'}, {n: 2}]}], right: [{n: 3}]});
check(!E.divide(plain, plain.left[0].id).ok, 'no subject: dividing by a letter still refused');
check(E.solved(E.make({left: [{n: 1, v: 't'}], right: [{n: 1, v: 't'}, {n: 1, v: 'u'}], subject: 't'})) === null,
      't = t + u is not done: t on both sides');
// a times 1/a cancels
var cancel = E.make({left: [{n: 1, l: {a: 1, v: 1}}], right: [{n: 1, v: 'a'}], subject: 'v'});
var cv = E.divide(cancel, cancel.left[0].id);
check(cv.ok && E.bodyText(cv.eq.right[0]) === '1', 'av = a -> v = 1 (a/a cancels)');

// Change the subject, stage 2: the subject twice (factorise it out, divide
// by the bracket), and a bracket underneath
var twice = E.make({left: [{n: 1, l: {a: 1, x: 1}}, {n: 1, v: 'b'}], right: [{n: 1, l: {c: 1, x: 1}}, {n: 1, v: 'd'}],
                    subject: 'x'});
var w = moveAll(twice, [['across', function (e) { return [e.right[0].id]; }],          // ax + b - cx = d
                        ['across', function (e) { return [e.left[1].id]; }]]);         // ax - cx = d - b
check(w.ok && E.bodyText(w.eq.left[0]) === 'ax' && E.bodyText(w.eq.left[1]) === 'cx' && w.eq.left[1].n === -1,
      'ax + b = cx + d -> ax - cx = d - b');
var wf = E.factorise(w.eq, 'left');
check(wf.ok && E.bodyText(wf.eq.left[0]) === 'x(a − c)', 'factorise: x(a - c)');
check(E.tex(wf.eq).indexOf('\\htmlData{k=') >= 0, 'x(a - c): the x is the factor');
check(!E.divide(wf.eq, wf.eq.left[0].id, 'factor').ok, 'dragging the x across is refused (the subject)');
var wd = E.divide(wf.eq, wf.eq.left[0].id);
check(wd.ok && wd.word === 'divide both sides by (a − c)', 'the bracket across: divide by (a - c)');
check(E.bodyText(wd.eq.left[0]) === 'x' && E.bodyText(wd.eq.right[0]) === '(d − b)/(a − c)',
      'x = (d - b)/(a - c)');
var ws = E.solved(wd.eq);
check(ws && !ws.flipped && ws.value === '(d − b)/(a − c)', 'solved: x = (d - b)/(a - c)');
check(E.tex(wd.eq).indexOf('\\frac{') >= 0 && E.tex(wd.eq).indexOf('\\left(') >= 0, 'written as a fraction over a bracket');
check(!E.expand(wd.eq, wd.eq.right[0].id).ok, 'a bracket underneath cannot be expanded');
// multiply back: drag the bottom bracket across
var wb = E.divide(wd.eq, wd.eq.right[0].id, 'factor');
check(wb.ok && E.bodyText(wb.eq.left[0]) === 'x(a − c)' && E.bodyText(wb.eq.right[0]) === 'd' &&
      wb.word === 'multiply both sides by (a − c)', 'drag (a - c) back: x(a - c) = d - b');
// xy = x + 4
var xy = E.make({left: [{n: 1, l: {x: 1, y: 1}}], right: [{n: 1, v: 'x'}, {n: 4}], subject: 'x'});
var xyd = moveAll(xy, [['across', function (e) { return [e.right[0].id]; }],
                       ['factorise', function (e) { return ['left']; }],
                       ['divide', function (e) { return [e.left[0].id]; }]]);
check(xyd.ok && E.solved(xyd.eq).value === '4/(y − 1)', 'xy = x + 4 -> x = 4/(y - 1)');
// refusals
var inside = E.make({left: [{k: 1, kv: 'x', terms: [{n: 1, v: 'x'}, {n: 1, v: 'a'}]}], right: [{n: 1, v: 'b'}], subject: 'x'});
check(!E.divide(inside, inside.left[0].id).ok, 'never divide by a bracket holding the subject');
var crowded = E.make({left: [{k: 1, kv: 'x', terms: [{n: 1, v: 'a'}, {n: -1, v: 'c'}]}, {n: 1, v: 'e'}],
                      right: [{n: 1, v: 'b'}], subject: 'x'});
check(!E.divide(crowded, crowded.left[0].id).ok, 'the bracket must multiply the whole side');
// y = (x + a)/(x + b): multiply by the bottom
var rat = E.make({left: [{n: 1, v: 'y'}],
                  right: [{k: 1, terms: [{n: 1, v: 'x'}, {n: 1, v: 'a'}], under: [{n: 1, v: 'x'}, {n: 1, v: 'b'}]}],
                  subject: 'x'});
check(E.bodyText(rat.right[0]) === '(x + a)/(x + b)', '(x + a)/(x + b) in words');
var rm = E.divide(rat, rat.right[0].id, 'factor');
check(rm.ok && E.bodyText(rm.eq.left[0]) === 'y(x + b)' && E.bodyText(rm.eq.right[0]) === 'x' &&
      E.bodyText(rm.eq.right[1]) === 'a', 'y = (x + a)/(x + b) -> y(x + b) = x + a');
check(E.solved(rat) === null, 'x on both sides: not done');
var single = E.make({left: [{n: 3, v: 'p'}], right: [{k: 1, terms: [{n: 1, v: 'q'}], under: [{n: 1, v: 'q'}, {n: 2}]}],
                     subject: 'q'});
check(E.bodyText(single.right[0]) === 'q/(q + 2)', 'one term on top: q/(q + 2)');
var many = E.make({left: [{n: 1, v: 'y'}, {n: 1}], right: [{k: 1, terms: [{n: 1, v: 'x'}], under: [{n: 1, v: 'x'}, {n: -1}]}],
                   subject: 'x'});
var mm = E.divide(many, many.right[0].id, 'factor');
check(mm.ok && E.bodyText(mm.eq.left[0]) === '(y + 1)(x − 1)', 'several terms times the bottom: (y + 1)(x - 1)');

var ax2 = E.make({left: [{k: 1, kv: 'a', terms: [{n: 1, v: 'x'}, {n: 2}]}], right: [{n: 1, l: {b: 1, x: 1}}], subject: 'b'});
var ax2s = E.swap(ax2).eq;
var ab2 = E.divide(ax2s, ax2s.left[0].id);
check(ab2.ok && E.bodyText(ab2.eq.right[0]) === 'a(x + 2)/x' && E.tex(ab2.eq).indexOf('\\frac{a\\left(') >= 0,
      'a(x + 2) over x written a(x + 2)/x');

// The bracket alone: data-b, divide by it, insideMoves
var ax1 = E.make({left: [{k: 1, kv: 'a', terms: [{n: 1, v: 'x'}, {n: 1}]}], right: [{n: 1, v: 'y'}], subject: 'a'});
check(E.tex(ax1).indexOf('\\htmlData{b=1}{\\left(') >= 0, 'a(x + 1): the bracket tagged data-b');
var ab1 = E.divide(ax1, 1, 'bracket');
check(ab1.ok && E.bodyText(ab1.eq.left[0]) === 'a' && E.bodyText(ab1.eq.right[0]) === 'y/(x + 1)',
      'a(x + 1) = y: the bracket across gives a = y/(x + 1)');
check(!E.divide(E.make({left: [{k: 3, terms: [{n: 1, v: 'x'}, {n: 4}]}], right: [{n: 21}]}), 1, 'bracket').ok,
      'no subject: dividing by a bracket refused');
check(!E.insideMoves(ax1, ax1.left[0].terms[0].id), 'x of a(x + 1): no move inside, the bracket lifts');
var inl = E.make({left: [{k: 2, terms: [{n: 1, v: 'x'}, {n: 3}, {n: 2, v: 'x'}]}], right: [{n: 4}]});
check(E.insideMoves(inl, inl.left[0].terms[0].id), 'x of 2(x + 3 + 2x): a like term inside, the term lifts');
var inq = E.make({left: [{k: 2, terms: [{n: 1, v: 'x', p: 2}, {n: 4, v: 'x'}, {n: 3}]}], right: null, goal: 'factorise'});
check(E.insideMoves(inq, inq.left[0].terms[1].id), '4x of 2(x² + 4x + 3): the inside factorises, the term lifts');
check(!E.insideMoves(ax1, ax1.left[0].id), 'the group itself is not inside anything');

console.log(failures ? failures + ' FAILED' : 'all passed');
process.exit(failures ? 1 : 0);
