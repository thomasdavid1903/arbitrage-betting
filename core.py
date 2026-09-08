import math

import numpy as np


def line_intersection(line1, line2):
    """Intersection of two lines, each given as two [x, y] points.

    Returns None when the lines are parallel (no unique intersection).
    """
    xdiff = (line1[0][0] - line1[1][0], line2[0][0] - line2[1][0])
    ydiff = (line1[0][1] - line1[1][1], line2[0][1] - line2[1][1])

    def det(a, b):
        return a[0] * b[1] - a[1] * b[0]

    div = det(xdiff, ydiff)
    if div == 0:
        return None

    d = (det(*line1), det(*line2))
    return det(d, xdiff) / div, det(d, ydiff) / div


def profit_if(stakes, bet1, bet2, bet3):
    """Profit under each outcome, given stakes [x, y, z] on outcomes 1, 2, 3.

    The winning outcome returns its own stake plus `odds * stake`; the other
    two stakes are lost. Hence `stake * odds - total + stake`.
    """
    x, y, z = stakes
    total = x + y + z
    return [
        x * bet1 - total + x,
        y * bet2 - total + y,
        z * bet3 - total + z,
    ]


def is_arbitrage(x, y, z, bet1, bet2, bet3):
    """True when stakes (x, y, z) profit strictly under every outcome.

    Strict inequalities: a point sitting exactly on a constraint line breaks
    even, which is not an arbitrage.
    """
    return (y < bet1 * x - z) and (y > (z + x) / bet2) and (y < -x + z * bet3)


def search_box(bet1, bet2, bet3, z):
    """Bounding box of the profitable triangle as (min_x, max_x, min_y, max_y).

    Returns None when the three constraints do not bound a region.
    """
    width = 50
    test_x = width / 2

    bet1_line = [[0, -z], [test_x, bet1 * test_x - z]]
    bet2_line = [[0, z / bet2], [test_x, (z + test_x) / bet2]]
    bet3_line = [[0, z * bet3], [test_x, -test_x + z * bet3]]

    corners = [
        line_intersection(bet1_line, bet2_line),
        line_intersection(bet1_line, bet3_line),
        line_intersection(bet2_line, bet3_line),
    ]
    if any(c is None for c in corners):
        return None

    xs = [c[0] for c in corners]
    ys = [c[1] for c in corners]

    # Stakes cannot be negative, so clamp the lower bounds at zero.
    min_x = max(0, math.ceil(min(xs)))
    max_x = math.floor(max(xs))
    min_y = max(0, math.ceil(min(ys)))
    max_y = math.floor(max(ys))

    if max_x < min_x or max_y < min_y:
        return None
    return min_x, max_x, min_y, max_y


def iter_points(bet1: float, bet2: float, bet3: float, precision: int = 1, z: float = 1000.0):
    """Yield stake combinations that profit whichever way the match goes.

    Stakes on outcomes 1 and 2 are the coordinates x and y; the stake on
    outcome 3 is fixed at `z`. Each outcome gives one inequality:

        outcome 1 wins:  y < bet1 * x - z
        outcome 2 wins:  y > (z + x) / bet2
        outcome 3 wins:  y < z * bet3 - x

    The three lines bound a triangle; every point inside it is an arbitrage.
    `precision` is the number of grid steps per unit, so 2 checks every 0.5.
    """
    if precision < 1:
        raise ValueError("precision must be a positive integer")

    box = search_box(bet1, bet2, bet3, z)
    if box is None:
        return
    min_x, max_x, min_y, max_y = box

    step = 1 / precision
    for i in range(int((max_x - min_x) * precision) + 1):
        x = min_x + step * i
        for j in range(int((max_y - min_y) * precision) + 1):
            y = min_y + step * j
            if is_arbitrage(x, y, z, bet1, bet2, bet3):
                yield [x, y, z]


def points(bet1: float, bet2: float, bet3: float, precision: int = 1, z: float = 1000.0):
    """List form of `iter_points`, kept for plotting and ad-hoc inspection."""
    return list(iter_points(bet1, bet2, bet3, precision, z))


def overround(bet1: float, bet2: float, bet3: float) -> float:
    """Sum of the implied probabilities of the three prices.

    Below 1 means the prices are collectively generous enough to bet all
    three outcomes at a guaranteed profit; 1.05 means a 5% margin against
    you. This is the bookmakers' overround, and for the best price taken
    across several books it is the exact test for whether an arbitrage
    exists -- no search required.
    """
    return sum(1 / (bet + 1) for bet in (bet1, bet2, bet3))


def has_arbitrage(bet1: float, bet2: float, bet3: float) -> bool:
    """Whether any profitable stake combination exists, in constant time."""
    return overround(bet1, bet2, bet3) < 1


def best_stakes(bet1: float, bet2: float, bet3: float, precision: int = 1, z: float = 1000.0):
    """Stakes with the highest guaranteed return per pound staked.

    In a genuine arbitrage every outcome profits, so the meaningful objective
    is the worst case: maximise the smallest of the three profits, normalised
    by the total staked. Returns (stakes, ratio), or None when no arbitrage
    exists.

    Iterates rather than building a list, because a wide profitable region can
    hold millions of combinations.
    """
    # The grid search is expensive and the overround settles the question
    # outright, so reject hopeless matches before scanning anything.
    if not has_arbitrage(bet1, bet2, bet3):
        return None

    best = None
    best_ratio = 0.0

    for stakes in iter_points(bet1, bet2, bet3, precision, z):
        ratio = min(profit_if(stakes, bet1, bet2, bet3)) / sum(stakes)
        if ratio > best_ratio:
            best_ratio = ratio
            best = stakes

    return None if best is None else (best, best_ratio)


def implied_probability(odds: float) -> float:
    """Implied probability from fractional odds expressed as a ratio.

    Note this ignores the bookmaker's overround, so the three probabilities
    for a match will not sum to 1.
    """
    return 1 / (odds + 1)


def plot_region(bet1: float, bet2: float, bet3: float, precision: int = 1, z: float = 1000.0):
    """Draw the three constraint lines and the profitable region.

    Separate from the search so that scanning matches does not build a figure
    for every one of them.
    """
    import matplotlib.pyplot as plt

    profitable = points(bet1, bet2, bet3, precision, z)
    x = np.arange(0, 50, 1 / precision)

    fig, ax = plt.subplots()
    if profitable:
        ax.scatter([p[0] for p in profitable], [p[1] for p in profitable])
    ax.plot(x, bet1 * x - z, color='red', label="bet1")
    ax.plot(x, (z + x) / bet2, color='green', label="bet2")
    ax.plot(x, -x + z * bet3, color='royalblue', label="bet3")
    ax.fill_between(x, bet1 * x - z, alpha=.4, color='red')
    ax.fill_between(x, (z + x) / bet2, z * bet3, alpha=.4, color='yellow')
    ax.legend()
    return fig, ax
