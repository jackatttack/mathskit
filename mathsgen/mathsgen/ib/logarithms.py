"""IB AI SL logarithms: the log-exponent link, log scales and unknown exponents.

SL 1.5 covers a^x = b <=> log_a(b) = x, logarithms with base 10 and e, and
evaluating them with technology. The laws of logarithms are AHL 1.9, so no
level asks students to expand or combine logarithms.

Level 1  fundamentals with no context: four parts drawn from five kinds
         (to log form, to exponential form, exact value, GDC value, solve).
Level 2  one log scale (pH, decibels, Richter, password entropy): a reading
         from a quantity, rearrange the formula, a quantity from a reading.
Level 3  comparing on a log scale: how many times greater, the effect of
         multiplying the quantity, the factor needed for a given change.
Level 4  unknown exponents in models (percentage growth and decay, half-life,
         continuous growth, cooling): a value, t as a logarithm, t to 3 s.f.,
         then a whole-unit answer or an interpretation.

Logarithms and powers use mpmath at 30 digits; the independent check uses
math.log10, math.log and float powers, written out per scale and model.
"""
import math
from fractions import Fraction

import mpmath

from ..core import GeneratorInfo, require
from ..family import GeneratorFamily
from .. import rich_blocks as rb
from . import common as ib
from . import distributions as dist


# --- Editable pools: level 1 ------------------------------------------------
E = 0   # base code meaning e, the natural logarithm
FUNDAMENTAL_KINDS = ("to_log", "to_exp", "exact", "gdc", "solve")
WHOLE_BASES = (2, 3, 4, 5, 10)
EXPONENTS = tuple(range(-3, 7))
GDC_NUMBERS = ("0.35", "0.62", "2.5", "3.9", "7.4", "18", "47.3", "125", "820", "2600")
SOLVE_POWERS = ("-0.5", "0.4", "0.85", "1.3", "1.6", "2.25", "2.7", "3.1")

# --- Editable pools: levels 2 and 3 -----------------------------------------
# Each pool is (name, reading), sorted by reading from lowest to highest.
SUBSTANCES = (("lemon juice", "2.2"), ("vinegar", "2.8"), ("orange juice", "3.5"),
              ("tomato juice", "4.3"), ("coffee", "5"), ("rainwater", "5.6"),
              ("milk", "6.6"), ("sea water", "8.1"), ("baking soda solution", "9"))
SOUNDS = (("a whisper", "30"), ("a quiet library", "40"), ("normal conversation", "60"),
          ("a vacuum cleaner", "75"), ("heavy traffic", "85"), ("a lawnmower", "90"),
          ("a motorbike", "95"), ("a rock concert", "110"), ("a chainsaw", "120"))
EARTHQUAKES = (("a minor tremor", "2.5"), ("a light earthquake", "4.2"),
               ("a moderate earthquake", "5.4"), ("a strong earthquake", "6.3"),
               ("a major earthquake", "7.1"), ("a great earthquake", "8.4"))
PASSWORDS = (("a four-digit PIN", "13.3"), ("a four-letter lower-case password", "18.8"),
             ("a six-letter lower-case password", "28.2"), ("a ten-digit number", "33.2"),
             ("an eight-character password using any keyboard symbol", "52.6"))
FACTORS = (2, 3, 4, 5, 8, 20, 50, 200, 1000)

# reading = sign × spread × log10(quantity / reference)
SCALES = {
    "ph": {
        "sign": -1, "spread": Fraction(1), "reference": Fraction(1),
        "formula": ("\\mathrm{pH}=-\\log_{10}[\\mathrm{H}^{+}]", "pH = -log10[H+]"),
        "intro": "The pH of a solution is given by ",
        "where": ", where [H+] is the hydrogen-ion concentration in moles per litre.",
        "find": "Find the pH when [H+] = ", "quantity_unit": " mol/L", "reading_unit": "",
        "symbol": "[H+]", "subject": "[H+] = 10^(-pH)",
        "reading": "pH", "has": "a pH", "noun": "the hydrogen-ion concentration", "of": "of",
        "back_task": "Find its hydrogen-ion concentration",
        "exponents": tuple(range(-12, -1)), "pool": SUBSTANCES,
        "changes": ("0.5", "1", "1.5", "2", "2.5"),
    },
    "decibel": {
        "sign": 1, "spread": Fraction(10), "reference": Fraction(1, 10 ** 12),
        "formula": ("L=10\\log_{10}\\left(\\frac{I}{10^{-12}}\\right)", "L = 10 log10(I / 10^-12)"),
        "intro": "The loudness of a sound, L decibels, is given by ",
        "where": ", where I is the intensity of the sound in W/m^2.",
        "find": "Find L when I = ", "quantity_unit": " W/m^2", "reading_unit": " dB",
        "symbol": "I", "subject": "I = 10^-12 × 10^(L/10)",
        "reading": "sound level", "has": "a sound level", "noun": "the intensity", "of": "of",
        "back_task": "Find its intensity",
        "exponents": tuple(range(-11, 0)), "pool": SOUNDS,
        "changes": ("3", "5", "10", "15", "20", "30"),
    },
    "richter": {
        "sign": 1, "spread": Fraction(1), "reference": Fraction(1),
        "formula": ("M=\\log_{10}A", "M = log10(A)"),
        "intro": "The Richter magnitude of an earthquake, M, is given by ",
        "where": ", where A is the amplitude of a seismograph reading in micrometres.",
        "find": "Find M when A = ", "quantity_unit": " micrometres", "reading_unit": "",
        "symbol": "A", "subject": "A = 10^M",
        "reading": "magnitude", "has": "a magnitude", "noun": "the amplitude", "of": "of",
        "back_task": "Find the amplitude of its seismograph reading",
        "exponents": tuple(range(1, 7)), "pool": EARTHQUAKES,
        "changes": ("0.5", "1", "1.5", "2"),
    },
    "entropy": {
        "sign": 1, "spread": Fraction(1000, 301), "reference": Fraction(1),
        "formula": ("0.301p=\\log_{10}G", "0.301p = log10(G)"),
        "intro": "The entropy of a password, p bits, and the number of guesses, G, "
                 "needed to find it satisfy ",
        "where": ".",
        "find": "Find p when G = ", "quantity_unit": "", "reading_unit": " bits",
        "symbol": "G", "subject": "G = 10^(0.301p)",
        "reading": "entropy", "has": "an entropy", "noun": "the number of guesses needed",
        "of": "for", "back_task": "Find the number of guesses needed to find it",
        "exponents": tuple(range(2, 10)), "pool": PASSWORDS,
        "changes": ("1", "5", "10", "20"),
    },
}

# --- Editable pools: level 4 ------------------------------------------------
ROOM = 20   # room temperature in the cooling model, degrees C
MODEL_FORMS = ("growth", "decay", "half_life", "continuous", "cooling")
CEILING_FORMS = ("growth", "decay", "continuous")
MEASURED_UNITS = ("mg", "°C")
# form -> ((stem template, time unit, noun, value unit), ...)
STEMS = {
    "growth": (
        ("A town has a population of {start} people, which increases by {rate}% each year.",
         "years", "the population", "people"),
        ("A culture contains {start} bacteria, and the number increases by {rate}% each hour.",
         "hours", "the number of bacteria", "bacteria"),
    ),
    "decay": (
        ("A lake contains {start} fish, and the number falls by {rate}% each year.",
         "years", "the number of fish", "fish"),
        ("A patient has {start} mg of a medicine in their blood, and the amount falls by "
         "{rate}% each hour.", "hours", "the amount of medicine", "mg"),
    ),
    "half_life": (
        ("A sample contains {start} mg of a radioactive isotope with a half-life of {rate} "
         "years. Its mass after t years is {start} × 0.5^(t/{rate}) mg.",
         "years", "the mass of the isotope", "mg"),
    ),
    "continuous": (
        ("The number of users of an app, N, t months after launch is modelled by "
         "N = {start}e^({rate}t).", "months", "the number of users", "users"),
        ("The number of bacteria in a dish, N, after t hours is modelled by "
         "N = {start}e^({rate}t).", "hours", "the number of bacteria", "bacteria"),
    ),
    "cooling": (
        ("A cup of tea is left to cool. Its temperature, T °C, after t minutes is modelled "
         "by T = 20 + {gap}e^(-{rate}t).", "minutes", "the temperature", "°C"),
        ("A bowl of soup is left to cool. Its temperature, T °C, after t minutes is modelled "
         "by T = 20 + {gap}e^(-{rate}t).", "minutes", "the temperature", "°C"),
    ),
}
STARTS = {"growth": (1200, 2500, 4000, 6400, 8000, 12000, 15000, 24000),
          "decay": (400, 600, 800, 1200, 1500, 2000),
          "half_life": (40, 50, 60, 80, 100, 120, 200, 250),
          "continuous": (500, 800, 1200, 2000, 5000),
          "cooling": (75, 80, 85, 90, 95)}
RATES = {"growth": ("1.5", "2", "2.5", "3", "4", "5", "6", "8"),
         "decay": ("2", "3", "4", "5", "6", "8", "10", "12"),
         "half_life": ("5", "8", "10", "12", "15", "20", "25", "30"),
         "continuous": ("0.02", "0.025", "0.035", "0.04", "0.05", "0.08", "0.12"),
         "cooling": ("0.03", "0.04", "0.05", "0.06", "0.08")}
# Targets are multiples of the start value, except cooling (a temperature).
TARGETS = {"growth": ("3/2", "2", "5/2", "3", "4"),
           "decay": ("1/2", "1/3", "1/4", "2/5", "3/5", "3/4"),
           "half_life": ("3/4", "2/5", "3/10", "1/5", "1/10", "1/20"),
           "continuous": ("2", "3", "5", "10"),
           "cooling": ("30", "35", "40", "45", "50", "55", "60")}
TIMES = {"growth": tuple(range(3, 11)), "decay": tuple(range(2, 9)),
         "half_life": (3, 6, 10, 18, 25, 40), "continuous": tuple(range(3, 13)),
         "cooling": (5, 10, 15, 20)}

LOG_TEX = {"log": "\\log_{10}", "ln": "\\ln "}
LOG_PLAIN = {"log": "log10", "ln": "ln"}


# ------------------------------------------------------------ mathematics

def log10(value):
    with mpmath.workdps(dist.PRECISION):
        return dist.fraction(mpmath.log10(dist.mp(value)))


def ln(value):
    with mpmath.workdps(dist.PRECISION):
        return dist.fraction(mpmath.log(dist.mp(value)))


def ten_to(power):
    with mpmath.workdps(dist.PRECISION):
        return dist.fraction(mpmath.power(10, dist.mp(power)))


def e_to(power):
    with mpmath.workdps(dist.PRECISION):
        return dist.fraction(mpmath.exp(dist.mp(power)))


def scientific(mantissa, exponent):
    """(plain, TeX) for m × 10^k."""
    return ("{} × 10^{}".format(mantissa, exponent),
            "{}\\times10^{{{}}}".format(mantissa, exponent))


def capital(text):
    return text[0].upper() + text[1:]


def size_text(value):
    """3 s.f., switching to a × 10^k once the value reaches a million."""
    return ib.standard_form(value) if value >= 10 ** 6 else ib.sf3(value)


def power_fits(base, exponent):
    """Whole-base powers stay readable: at most 1000 and at least 1/125."""
    if base == 10:
        return True
    value = Fraction(base) ** exponent
    return Fraction(1, 130) <= value <= 1000


def power_text(base, exponent):
    """(TeX, plain) for base^exponent: 32, 0.001 or 1/8."""
    value = Fraction(base) ** exponent
    if value.denominator == 1:
        return str(value.numerator), str(value.numerator)
    if base == 10:
        text = ib.nice(value)
        return text, text
    return "\\frac{{1}}{{{}}}".format(value.denominator), "1/{}".format(value.denominator)


def reading_from(scale, quantity):
    return scale["sign"] * scale["spread"] * log10(Fraction(quantity) / scale["reference"])


def quantity_from(scale, reading):
    return scale["reference"] * ten_to(scale["sign"] * Fraction(reading) / scale["spread"])


def growth_factor(p):
    rate = Fraction(p["rate"]) / 100
    return 1 + rate if p["form"] == "growth" else 1 - rate


def target_value(p):
    if p["form"] == "cooling":
        return Fraction(p["target"])
    return p["start"] * Fraction(p["target"])


def ratio_needed(p):
    """c in the logarithm that gives t."""
    if p["form"] == "cooling":
        return Fraction(int(p["target"]) - ROOM, p["start"] - ROOM)
    return Fraction(p["target"])


def model_value(p, time):
    form, start, time = p["form"], Fraction(p["start"]), Fraction(time)
    if form in ("growth", "decay"):
        return start * growth_factor(p) ** int(time)
    rate = Fraction(p["rate"])
    with mpmath.workdps(dist.PRECISION):
        if form == "half_life":
            value = dist.mp(start) * mpmath.power(mpmath.mpf(1) / 2, dist.mp(time / rate))
        elif form == "continuous":
            value = dist.mp(start) * mpmath.exp(dist.mp(rate * time))
        else:
            value = ROOM + dist.mp(start - ROOM) * mpmath.exp(-dist.mp(rate * time))
        return dist.fraction(value)


def solve_time(p):
    form, rate = p["form"], Fraction(p["rate"])
    with mpmath.workdps(dist.PRECISION):
        log_c = mpmath.log(dist.mp(ratio_needed(p)))
        if form in ("growth", "decay"):
            time = log_c / mpmath.log(dist.mp(growth_factor(p)))
        elif form == "half_life":
            time = dist.mp(rate) * log_c / mpmath.log(mpmath.mpf(1) / 2)
        elif form == "continuous":
            time = log_c / dist.mp(rate)
        else:
            time = -log_c / dist.mp(rate)
        return dist.fraction(time)


def log_form(p):
    """(pattern asked for, answer) for t written as a logarithm."""
    c = ib.exact_or_fraction(ratio_needed(p))
    form, rate = p["form"], p["rate"]
    if form in ("growth", "decay"):
        return ("t = log_b(c)", "t = log_{}({})".format(ib.nice(growth_factor(p)), c))
    if form == "half_life":
        return ("t = h log_0.5(c), where h is the half-life", "t = {} log_0.5({})".format(rate, c))
    if form == "continuous":
        return ("t = ln(c)/k", "t = ln({})/{}".format(c, rate))
    return ("t = -ln(c)/k", "t = -ln({})/{}".format(c, rate))


# ------------------------------------------------------------ level 1 parts

def fundamental_item(kind, rng):
    if kind == "to_log":
        return [kind, rng.choice(WHOLE_BASES), rng.choice(EXPONENTS)]
    if kind == "to_exp":
        base = rng.choice(WHOLE_BASES + (E,))
        return [kind, base, rng.randint(2, 5) if base == E else rng.choice(EXPONENTS)]
    if kind == "exact":
        return [kind, rng.choice(WHOLE_BASES + (E,)), rng.choice(EXPONENTS)]
    if kind == "gdc":
        return [kind, rng.choice(("log", "ln")), rng.choice(GDC_NUMBERS)]
    return [kind, rng.choice(("log", "ln")), rng.choice(SOLVE_POWERS)]


def check_item(item):
    require(isinstance(item, list) and len(item) == 3, "Malformed level 1 item")
    kind, first, second = item
    require(kind in FUNDAMENTAL_KINDS, "Unknown level 1 kind")
    if kind in ("gdc", "solve"):
        require(first in ("log", "ln"), "Unknown logarithm")
        require(second in (GDC_NUMBERS if kind == "gdc" else SOLVE_POWERS), "Value outside pool")
        return
    require(type(first) is int and type(second) is int, "Base and exponent must be integers")
    if first == E:
        require(kind != "to_log", "Logarithmic form needs a whole-number base")
        if kind == "to_exp":
            ib.require_int(second, 2, 5, "ln value outside bounds")
        else:
            require(second in EXPONENTS, "Exponent outside pool")
        return
    require(first in WHOLE_BASES and second in EXPONENTS, "Base or exponent outside pools")
    require(power_fits(first, second), "Power too large or too small")


def fundamental_part(label, item):
    kind, first, second = item
    if kind == "gdc":
        number = Fraction(second)
        value = log10(number) if first == "log" else ln(number)
        expression = rb.maths(LOG_TEX[first] + second, "{}({})".format(LOG_PLAIN[first], second))
        return ib.part(label, [rb.text("Use your GDC to find "), expression, rb.text(".")],
                       1, ib.sf3(value), value)
    if kind == "solve":
        power = Fraction(second)
        value = ten_to(power) if first == "log" else e_to(power)
        equation = rb.maths("{}x={}".format(LOG_TEX[first], second),
                            "{}(x) = {}".format(LOG_PLAIN[first], second))
        return ib.part(label, [rb.text("Solve "), equation, rb.text(".")],
                       2, "x = " + ib.sf3(value), value)
    if first == E:
        if kind == "to_exp":
            statement = rb.maths("\\ln x={}".format(second), "ln(x) = {}".format(second))
            return ib.part(label, [rb.text("Write "), statement, rb.text(" in exponential form.")],
                           1, "x = e^{}".format(second))
        expression = rb.maths("\\ln\\left(e^{{{}}}\\right)".format(second), "ln(e^{})".format(second))
        return ib.part(label, [rb.text("Find the exact value of "), expression, rb.text(".")],
                       1, str(second), Fraction(second))
    value_tex, value_plain = power_text(first, second)
    if kind == "to_log":
        statement = rb.maths("{}^{{{}}}={}".format(first, second, value_tex),
                             "{}^{} = {}".format(first, second, value_plain))
        return ib.part(label, [rb.text("Write "), statement, rb.text(" in logarithmic form.")],
                       1, "log_{}({}) = {}".format(first, value_plain, second))
    log_tex = "\\log_{{{}}}{}".format(first, value_tex)
    log_plain = "log_{}({})".format(first, value_plain)
    if kind == "to_exp":
        statement = rb.maths("{}={}".format(log_tex, second), "{} = {}".format(log_plain, second))
        return ib.part(label, [rb.text("Write "), statement, rb.text(" in exponential form.")],
                       1, "{}^{} = {}".format(first, second, value_plain))
    return ib.part(label, [rb.text("Find the exact value of "), rb.maths(log_tex, log_plain),
                           rb.text(".")], 1, str(second), Fraction(second))


# ------------------------------------------------------------ generator

class LogarithmicScales(GeneratorFamily):
    info = GeneratorInfo(
        id="ib_ai_sl.number.logarithms",
        version=2,
        topic=ib.TOPIC,
        subtopic="number_and_algebra",
        title="Logarithms",
        difficulty_descriptions={
            1: "Exponential and log forms, exact values, GDC values and simple log equations.",
            2: "One log scale (pH, decibels, Richter, entropy): reading, rearranging, a × 10^k.",
            3: "Comparing on a log scale: times greater, multiplying the quantity, factor needed.",
            4: "Unknown exponents in growth, decay, half-life, continuous and cooling models.",
        },
        tags=ib.BASE_TAGS + ("logarithms", "natural_logarithm", "exponentials",
                             "exponential_equations", "standard_form"),
    )
    keys = {
        1: {"items"},
        2: {"scale", "mantissa", "exponent", "back"},
        3: {"scale", "first", "second", "factor", "change"},
        4: {"form", "stem", "start", "rate", "target", "time"},
    }

    def build(self, level, rng):
        return ib.pick_valid(rng, lambda r: self.candidate(level, r),
                             lambda p: self.check_rules(p, level))

    def candidate(self, level, rng):
        if level == 1:
            kinds = sorted(rng.sample(FUNDAMENTAL_KINDS, 4), key=FUNDAMENTAL_KINDS.index)
            return {"items": [fundamental_item(kind, rng) for kind in kinds]}
        if level in (2, 3):
            name = rng.choice(sorted(SCALES))
            scale = SCALES[name]
            if level == 2:
                return {"scale": name, "mantissa": rng.randint(1, 9),
                        "exponent": rng.choice(scale["exponents"]),
                        "back": rng.randrange(len(scale["pool"]))}
            first, second = sorted(rng.sample(range(len(scale["pool"])), 2))
            return {"scale": name, "first": first, "second": second,
                    "factor": rng.choice(FACTORS), "change": rng.choice(scale["changes"])}
        form = rng.choice(MODEL_FORMS)
        return {"form": form, "stem": rng.randrange(len(STEMS[form])),
                "start": rng.choice(STARTS[form]), "rate": rng.choice(RATES[form]),
                "target": rng.choice(TARGETS[form]), "time": rng.choice(TIMES[form])}

    def check_rules(self, p, level):
        if level == 1:
            items = p["items"]
            require(isinstance(items, list) and len(items) == 4, "Level 1 needs four items")
            for item in items:
                check_item(item)
            kinds = [item[0] for item in items]
            require(kinds == sorted(set(kinds), key=FUNDAMENTAL_KINDS.index),
                    "Kinds must be distinct and in order")
            return
        if level in (2, 3):
            require(p["scale"] in SCALES, "Unknown scale")
            scale = SCALES[p["scale"]]
            last = len(scale["pool"]) - 1
            if level == 2:
                ib.require_int(p["mantissa"], 1, 9, "Mantissa outside bounds")
                require(type(p["exponent"]) is int and p["exponent"] in scale["exponents"],
                        "Exponent outside bounds")
                ib.require_int(p["back"], 0, last, "Unknown pool entry")
                return
            ib.require_int(p["first"], 0, last, "Unknown pool entry")
            ib.require_int(p["second"], 0, last, "Unknown pool entry")
            require(p["first"] < p["second"], "First must have the lower reading")
            require(type(p["factor"]) is int and p["factor"] in FACTORS, "Factor outside pool")
            require(p["change"] in scale["changes"], "Change outside pool")
            new = (Fraction(scale["pool"][p["second"]][1])
                   + scale["sign"] * scale["spread"] * log10(Fraction(p["factor"])))
            require(0 < new <= 150, "New reading outside a sensible range")
            return
        form = p["form"]
        require(form in MODEL_FORMS, "Unknown model")
        ib.require_int(p["stem"], 0, len(STEMS[form]) - 1, "Unknown stem")
        require(p["start"] in STARTS[form] and p["rate"] in RATES[form]
                and p["target"] in TARGETS[form] and p["time"] in TIMES[form],
                "Values outside pools")
        if form == "half_life":
            # A whole number of half-lives makes part (a) mental arithmetic.
            require(p["time"] % int(p["rate"]) != 0, "Time is a whole number of half-lives")
        if form == "cooling":
            require(ROOM < int(p["target"]) < p["start"] - 5, "Target temperature outside rules")
        else:
            require(target_value(p).denominator == 1, "Target must be a whole number")
        time = solve_time(p)
        require(1 < time < 80, "Time outside bounds")
        if form in CEILING_FORMS:
            fraction = time - math.floor(time)
            require(Fraction(1, 20) < fraction < Fraction(19, 20), "Time too close to a whole number")

    def parts(self, p, level):
        if level == 1:
            return ib.assemble(["Give answers that are not exact to 3 significant figures."],
                               [fundamental_part(label, item)
                                for label, item in zip("abcd", p["items"])])
        if level in (2, 3):
            return self.scale_parts(p, level)
        return self.model_parts(p)

    def scale_parts(self, p, level):
        scale = SCALES[p["scale"]]
        context = [[rb.text(scale["intro"]), rb.maths(*scale["formula"]), rb.text(scale["where"])]]
        unit = scale["reading_unit"]
        if level == 2:
            quantity = Fraction(p["mantissa"]) * Fraction(10) ** p["exponent"]
            reading = reading_from(scale, quantity)
            plain, tex = scientific(p["mantissa"], p["exponent"])
            name, back_reading = scale["pool"][p["back"]]
            back = quantity_from(scale, back_reading)
            return ib.assemble(context, [
                ib.part("a", [rb.text(scale["find"]), rb.maths(tex, plain),
                              rb.text(scale["quantity_unit"] + ".")], 2,
                        ib.sf3(reading) + unit, reading),
                ib.part("b", "Rearrange the formula to make {} the subject.".format(scale["symbol"]),
                        2, scale["subject"]),
                ib.part("c", "{} has {} of {}{}. {}. Give your answer in the form a × 10^k, where "
                        "1 <= a < 10 and k is an integer.".format(
                            capital(name), scale["has"], back_reading, unit, scale["back_task"]),
                        2, ib.standard_form(back) + scale["quantity_unit"], back),
            ])
        (low_name, low_text), (high_name, high_text) = (scale["pool"][p["first"]],
                                                        scale["pool"][p["second"]])
        if scale["sign"] > 0:
            big, small = (high_name, high_text), (low_name, low_text)
        else:
            big, small = (low_name, low_text), (high_name, high_text)
        ratio = ten_to((Fraction(high_text) - Fraction(low_text)) / scale["spread"])
        new = Fraction(high_text) + scale["sign"] * scale["spread"] * log10(Fraction(p["factor"]))
        needed = ten_to(Fraction(p["change"]) / scale["spread"])
        direction = "raise" if scale["sign"] > 0 else "lower"
        return ib.assemble(context, [
            ib.part("a", "{} has {} of {}{} and {} has {} of {}{}. Find how many times greater {} {} "
                    "{} is than that {} {}.".format(
                        capital(big[0]), scale["has"], big[1], unit, small[0], scale["has"],
                        small[1], unit, scale["noun"], scale["of"], big[0], scale["of"], small[0]),
                    2, size_text(ratio), ratio),
            ib.part("b", "{} {} {} is multiplied by {}. Find the new {}.".format(
                        capital(scale["noun"]), scale["of"], high_name, p["factor"], scale["reading"]),
                    2, ib.sf3(new) + unit, new),
            ib.part("c", "Find the factor by which {} must be multiplied to {} the {} by {}{}.".format(
                        scale["noun"], direction, scale["reading"], p["change"], unit),
                    2, size_text(needed), needed),
        ])

    def model_parts(self, p):
        form = p["form"]
        template, time_unit, noun, value_unit = STEMS[form][p["stem"]]
        stem = template.format(start=p["start"], rate=p["rate"], gap=p["start"] - ROOM)
        context = [stem, "Give answers that are not exact to 3 significant figures."]
        value = model_value(p, p["time"])
        time = solve_time(p)
        # Measured units follow the number; counts (people, fish) are already in the noun.
        target_text = ib.nice(target_value(p))
        if value_unit in MEASURED_UNITS:
            target_text += " " + value_unit
        verb = "reaches" if form in ("growth", "continuous") else "falls to"
        pattern, written = log_form(p)
        parts = [
            ib.part("a", "Find {} after {} {}.".format(noun, p["time"], time_unit), 2,
                    "{} {}".format(ib.sf3(value), value_unit), value),
            ib.part("b", "Write an equation for t, the number of {} until {} {} {}, in the form "
                    "{}.".format(time_unit, noun, verb, target_text, pattern), 2, written),
            ib.part("c", "Hence find t.", 1, "t = " + ib.sf3(time), time),
        ]
        if form in CEILING_FORMS:
            whole = math.ceil(time)
            comparison = "more" if form != "decay" else "less"
            parts.append(ib.part("d", "Find the least whole number of {} after which {} is {} than "
                                 "{}.".format(time_unit, noun, comparison, target_text), 1,
                                 "{} {}".format(whole, time_unit), Fraction(whole)))
        elif form == "half_life":
            parts.append(ib.part("d", "Explain why the mass of the isotope never reaches 0 mg.", 1,
                                 "0.5^(t/{}) is positive for every t, so the mass is always more "
                                 "than 0 mg.".format(p["rate"])))
        else:
            parts.append(ib.part("d", "State the value that T approaches as t increases, and "
                                 "explain why.", 2,
                                 "20 °C, the room temperature, because e^(-{}t) approaches 0."
                                 .format(p["rate"])))
        return ib.assemble(context, parts)

    def validate_independently(self, question):
        """Float logarithms and powers, written out per kind, scale and model."""
        p, level = question.parameters, question.difficulty
        values, shown = ib.answer_values(question), ib.answer_shown(question)
        if level == 1:
            for label, (kind, first, second) in zip("abcd", p["items"]):
                if kind == "gdc":
                    expected = (math.log10(float(second)) if first == "log"
                                else math.log(float(second)))
                elif kind == "solve":
                    expected = 10 ** float(second) if first == "log" else math.exp(float(second))
                elif kind == "exact":
                    expected = (float(second) if first == E
                                else math.log(float(first) ** second, first))
                elif kind == "to_log":
                    require(shown[label].endswith("= {}".format(second)), "Independent log form failed")
                    continue
                else:
                    start = "x = e^" if first == E else "{}^{} = ".format(first, second)
                    require(shown[label].startswith(start), "Independent exponential form failed")
                    continue
                require(ib.close(values[label], expected, 1e-9), "Independent level 1 answer failed")
            return True
        if level in (2, 3):
            forward = {"ph": lambda q: -math.log10(q),
                       "decibel": lambda q: 10 * math.log10(q / 1e-12),
                       "richter": lambda q: math.log10(q),
                       "entropy": lambda q: math.log10(q) / 0.301}[p["scale"]]
            back = {"ph": lambda r: 10 ** -r,
                    "decibel": lambda r: 1e-12 * 10 ** (r / 10),
                    "richter": lambda r: 10 ** r,
                    "entropy": lambda r: 10 ** (0.301 * r)}[p["scale"]]
            pool = SCALES[p["scale"]]["pool"]
            if level == 2:
                quantity = p["mantissa"] * 10.0 ** p["exponent"]
                require(ib.close(values["a"], forward(quantity)), "Independent reading failed")
                require(ib.close(values["c"], back(float(pool[p["back"]][1]))),
                        "Independent quantity failed")
                return True
            low, high = float(pool[p["first"]][1]), float(pool[p["second"]][1])
            big = max(back(low), back(high))
            small = min(back(low), back(high))
            require(ib.close(values["a"], big / small, 1e-8), "Independent ratio failed")
            require(ib.close(values["b"], forward(back(high) * p["factor"]), 1e-8),
                    "Independent new reading failed")
            change = float(p["change"])
            moved = high - change if p["scale"] == "ph" else high + change
            require(ib.close(values["c"], back(moved) / back(high), 1e-8),
                    "Independent factor failed")
            return True
        form, start, rate, time = p["form"], p["start"], float(Fraction(p["rate"])), p["time"]
        if form in ("growth", "decay"):
            g = 1 + rate / 100 if form == "growth" else 1 - rate / 100
            value = start * g ** time
            t = math.log(float(Fraction(p["target"]))) / math.log(g)
        elif form == "half_life":
            value = start * 0.5 ** (time / rate)
            t = rate * math.log(float(Fraction(p["target"]))) / math.log(0.5)
        elif form == "continuous":
            value = start * math.exp(rate * time)
            t = math.log(float(Fraction(p["target"]))) / rate
        else:
            target = float(p["target"])
            value = 20 + (start - 20) * math.exp(-rate * time)
            t = -math.log((target - 20) / (start - 20)) / rate
        require(ib.close(values["a"], value, 1e-8), "Independent model value failed")
        require(ib.close(values["c"], t, 1e-8), "Independent time failed")
        if form in CEILING_FORMS:
            require(Fraction(values["d"]) == math.ceil(t), "Independent whole time failed")
        return True
