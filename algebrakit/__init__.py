"""algebrakit: touch-based visual algebra for editorkit.web pages.

Every maths object on a board is an expression tree; every term on screen
is a node you can touch. Moves are rewrite rules with a precondition, so
only valid moves exist. See VISION.txt for where this is going.

    page.py        what a page needs: page_extras(), board_html(shape)
    equations.py   linear equations: read, text, answer, random_equation
    web/engine.js  the tree and the moves (no DOM; tests/engine_test.js)
    web/board.js   drawing, touch, drag, and pieces flying between steps
    web/board.css  the look
"""
