"""
Booklet imposition maths.

Pure logic: no PDF library, no I/O. Page numbers are 0-based indices into the
input document, and BLANK marks a slot that must stay empty.
"""

import math

# Sentinel used in place of a page index when a slot must be left blank.
BLANK = -1

# A folded sheet carries 4 pages (2 per side, duplex printing).
PAGES_PER_SHEET = 4

DEFAULT_SHEETS_PER_BOOKLET = 7


def distribution_pages(begin, end):
    """
    Defines for a given booklet which pages go in which sheet, and in which order.

    Returns a list of (left, right) pairs, one per printed side, ordered from the
    outermost sheet inwards: [sheet1 front, sheet1 back, sheet2 front, ...].
    """

    if not isinstance(begin, int) or not isinstance(end, int):
        raise TypeError("begin and end must be integers")
    if begin > end:
        raise ValueError("begin must be less than or equal to end")

    number_of_pages = end - begin + 1

    # Because of duplex printing, pages go by 4 and not 2: with 5 pages you need
    # 3 blank pages to reach 8, 2 for 6, 1 for 7, 0 for 8, and so on.
    # The blanks are consumed first so that they land on the *last* reading slots
    # of the booklet, i.e. after the final real page once folded.
    blank_pages = (-number_of_pages) % PAGES_PER_SHEET

    i = begin
    j = end
    j_first = True

    distrib = []
    while i <= j:
        far_page = BLANK if blank_pages > 0 else j
        # Sides alternate: on a front side the high page sits on the left,
        # on the following back side it sits on the right.
        distrib.append((far_page, i) if j_first else (i, far_page))
        j_first = not j_first

        i += 1
        if blank_pages > 0:
            blank_pages -= 1
        else:
            j -= 1

    return distrib


def distribution_booklets(n_pages, n_booklets="auto", n_sheets=DEFAULT_SHEETS_PER_BOOKLET):
    """
    Defines which pages go in which booklet, as a list of (begin, end) ranges.
    """

    if not isinstance(n_pages, int) or isinstance(n_pages, bool):
        raise TypeError("number of pages must be an integer")
    if n_pages <= 0:
        raise ValueError("number of pages must be greater than 0")

    if n_booklets == "auto":
        if not isinstance(n_sheets, int) or n_sheets <= 0:
            raise ValueError("number of sheets per booklet must be an integer greater than 0")
        # Aim for n_sheets sheets per booklet, rounding up, and never fewer than
        # one booklet (a document shorter than one full booklet still needs one).
        n_booklets = max(1, math.ceil(n_pages / (PAGES_PER_SHEET * n_sheets)))

    if not isinstance(n_booklets, int) or isinstance(n_booklets, bool):
        raise TypeError("number of booklets must be an integer")
    if n_booklets <= 0:
        raise ValueError("number of booklets must be greater than 0")

    total_sheets = math.ceil(n_pages / PAGES_PER_SHEET)

    if total_sheets < n_booklets:
        raise ValueError(
            f"cannot split {n_pages} pages ({total_sheets} sheets) into {n_booklets} booklets"
        )

    # Spread the leftover sheets one per booklet, over the first ones.
    sheets_per_booklet, sheets_left = divmod(total_sheets, n_booklets)

    distrib_begin_end = []
    begin = 0
    for index in range(n_booklets):
        sheets = sheets_per_booklet + (1 if index < sheets_left else 0)
        end = min(begin + sheets * PAGES_PER_SHEET - 1, n_pages - 1)
        distrib_begin_end.append((begin, end))
        begin = end + 1

    return distrib_begin_end


def distribution_booklets_pages(n_pages, n_booklets="auto", n_sheets=DEFAULT_SHEETS_PER_BOOKLET):
    """
    Defines which pages go in which booklet, and in which order.
    """

    return [
        distribution_pages(begin, end)
        for begin, end in distribution_booklets(n_pages, n_booklets, n_sheets)
    ]
