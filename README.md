# Maths (mathskit)

Maths lessons to teach from on a shared screen, inside Toolbox for
Pythonista. Each topic is a ladder of stages: the idea, a worked example you
step through, questions with the answer hidden until you reveal it, and the
topic's key facts.

Algebra questions open as touch boards: drag a term across the equals sign,
drag a number into a bracket to expand it, drag what multiplies the letter
across to divide. Only valid moves exist, and any valid route works, so a
student can find their own way to the answer. Formulas can be rearranged to
make any letter the subject.

A question bank draws on the MathsGen question engine for anything a lesson
does not cover yet.

## Install

Maths runs inside Toolbox. Install Toolbox first:
[github.com/jackatttack/editorkit](https://github.com/jackatttack/editorkit).

Then make a new script in Pythonista (in Documents, not in iCloud), paste
this in and run it:

```python
import urllib.request
URL = 'https://raw.githubusercontent.com/jackatttack/mathskit/main/install.py'
code = urllib.request.urlopen(URL, timeout=60).read().decode('utf-8')
exec(compile(code, 'install.py', 'exec'), {'__name__': '__main__', '__file__': __file__})
```

It installs into `Documents/Mathskit` and adds a Maths card to Toolbox. Run
the same script again any time to update: the previous install is kept as a
dated backup.

## What is inside

- `maths_tool.py`: the Maths window (Lessons, Lesson, Facts, Bank). Run it by
  hand, or open Maths from Toolbox.
- `mathskit/`: lessons, worked steps, graphs, flashcards and the pages.
- `algebrakit/`: the touch algebra boards. The move engine is JavaScript
  (`algebrakit/web/engine.js`) and runs in the page.
- `mathsgen/`: the MathsGen question engine the bank draws from.
- `katex/`: KaTeX for the maths, under its MIT licence (`katex/LICENSE`).
- `tests/`: smoke tests. `tests/engine_test.js` runs under node.

## Licence

MIT, see `LICENSE`. KaTeX is MIT licensed by Khan Academy and other
contributors.
