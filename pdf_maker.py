"""
Turns a regular PDF into a duplex-printable, foldable booklet PDF.

Each output page is one side of a physical sheet: two source pages scaled to
half size and placed side by side, so the sheet keeps the same paper format as
the input, only rotated to landscape.
"""

import os
from collections import Counter
from io import BytesIO

import pymupdf
from pypdf import PageObject, PdfReader, PdfWriter, Transformation

from distribution import BLANK, DEFAULT_SHEETS_PER_BOOKLET, distribution_booklets_pages

# Page numbers are stamped on the source pages, which the imposition then scales
# to half size, so both ratios are expressed against the source page height and
# chosen to give roughly 10 pt of text about 1 cm above the edge once printed.
NUMBER_FONT_RATIO = 1 / 42
NUMBER_MARGIN_RATIO = 1 / 14
NUMBER_FONT = "helv"


def get_dimensions(pages):
    """
    Returns the most common (width, height) among the given pages.

    Source pages of any other size are scaled to fit that format.
    """
    sizes = Counter((page.mediabox.width, page.mediabox.height) for page in pages)
    if not sizes:
        raise ValueError("the PDF file has no page")

    width, height = sizes.most_common(1)[0][0]
    return float(width), float(height)


def add_empty_pages(reader, n_pages):
    """
    Returns a new reader with n_pages blank pages added at the beginning and at
    the end of the document, to be glued to the cover.
    """
    if n_pages <= 0:
        return reader

    width, height = get_dimensions(reader.pages)

    writer = PdfWriter()
    for _ in range(n_pages):
        writer.add_blank_page(width=width, height=height)
    for page in reader.pages:
        writer.add_page(page)
    for _ in range(n_pages):
        writer.add_blank_page(width=width, height=height)

    buffer = BytesIO()
    writer.write(buffer)
    buffer.seek(0)
    return PdfReader(buffer)


def add_page_numbers(reader, first_page=1, last_page=None):
    """
    Returns a new reader with a page number centred at the bottom of every page
    from first_page to last_page (1-based, inclusive).

    The numbering restarts at 1 on first_page, so skipping the endpapers still
    gives the content a natural 1, 2, 3... Pages outside the range are left
    untouched, which is how endpapers stay blank.

    Numbers are stamped on the source pages, before the imposition: they are
    then scaled, letterboxed and rotated along with the page they belong to.
    """
    total = len(reader.pages)
    first_page = max(1, first_page)
    last_page = total if last_page is None else min(last_page, total)

    if first_page > last_page:
        return reader

    buffer = BytesIO()
    PdfWriter(clone_from=reader).write(buffer)

    with pymupdf.open(stream=buffer.getvalue(), filetype="pdf") as document:
        for index in range(first_page - 1, last_page):
            page = document[index]
            rect = page.rect
            size = rect.height * NUMBER_FONT_RATIO
            text = str(index - first_page + 2)
            text_width = pymupdf.get_text_length(text, fontname=NUMBER_FONT, fontsize=size)
            # pymupdf places text from the top of the page, on the baseline.
            page.insert_text(
                (rect.x0 + (rect.width - text_width) / 2,
                 rect.y1 - rect.height * NUMBER_MARGIN_RATIO),
                text, fontname=NUMBER_FONT, fontsize=size)

        return PdfReader(BytesIO(document.tobytes()))


def _needs_rotation(page_width, page_height, box_width, box_height):
    """
    True when the page and the slot it must fill have opposite orientations.
    """
    return (page_width > page_height) != (box_width > box_height)


def _placement(page, box_width, box_height, x_offset):
    """
    Transformation fitting a source page into the (box_width, box_height) slot
    starting at x_offset on the sheet.

    The page keeps its aspect ratio and is centred in the slot, leaving white
    margins when the formats differ (letterboxing). A page whose orientation is
    the opposite of the slot's is rotated 90° counter-clockwise first, the usual
    convention for landscape plates: the reader turns the book clockwise.
    """
    box = page.mediabox
    page_width, page_height = float(box.width), float(box.height)

    # Bring the page origin to (0, 0) first: a mediabox does not necessarily
    # start there (cropped or scanned documents often do not).
    transformation = Transformation().translate(-float(box.left), -float(box.bottom))

    if _needs_rotation(page_width, page_height, box_width, box_height):
        # Rotating counter-clockwise sends the page into negative x; push it
        # back, and swap the dimensions used for the fit.
        transformation = transformation.rotate(90).translate(page_height, 0)
        page_width, page_height = page_height, page_width

    # A single ratio for both axes, so nothing is stretched.
    ratio = min(box_width / page_width, box_height / page_height)
    margin_x = (box_width - page_width * ratio) / 2
    margin_y = (box_height - page_height * ratio) / 2

    return transformation.scale(ratio, ratio).translate(x_offset + margin_x, margin_y)


def make_sheet_side(reader, pair, width, height):
    """
    Builds one printed side from a (left, right) pair of source page indices.

    The result is a landscape page of width x height/2 carrying both source
    pages side by side, each in a slot half as wide and half as tall as the
    reference format. BLANK leaves the corresponding half empty.
    """
    left, right = pair
    slot_width, slot_height = width / 2, height / 2
    sheet = PageObject.create_blank_page(width=width, height=slot_height)

    for index, x_offset in ((left, 0), (right, slot_width)):
        if index == BLANK:
            continue
        page = reader.pages[index]
        sheet.merge_transformed_page(page, _placement(page, slot_width, slot_height, x_offset))

    return sheet


def prepare_document(reader, empty_pages=0, page_numbers=False, numbering_start=1):
    """
    Applies to a source document everything that happens before the imposition:
    the endpapers, then the page numbers.

    Order matters. The endpapers become real pages first, so numbering_start
    counts physical pages of the document that will actually be printed, and the
    trailing endpapers are excluded from the numbering.
    """
    reader = add_empty_pages(reader, empty_pages)

    if page_numbers:
        reader = add_page_numbers(reader, numbering_start, len(reader.pages) - empty_pages)

    return reader


def make_pdf(input_filename, output_filename, n_booklets="auto", remove_annotations=True,
             n_sheets=DEFAULT_SHEETS_PER_BOOKLET, progress=None, empty_pages=0,
             page_numbers=False, numbering_start=1):
    """
    Writes the booklet version of input_filename to output_filename.

    progress, if given, is any object exposing progress_init(total) and
    update_progress(); it is called once per printed side.
    """

    if os.path.realpath(input_filename) == os.path.realpath(output_filename):
        raise ValueError("The input and output file cannot be the same")

    reader = prepare_document(PdfReader(input_filename), empty_pages, page_numbers, numbering_start)

    distrib_booklets_pages = distribution_booklets_pages(len(reader.pages), n_booklets, n_sheets)
    width, height = get_dimensions(reader.pages)

    if progress:
        progress.progress_init(sum(len(booklet) for booklet in distrib_booklets_pages))

    writer = PdfWriter()
    for booklet in distrib_booklets_pages:
        for pair in booklet:
            writer.add_page(make_sheet_side(reader, pair, width, height))
            if progress:
                progress.update_progress()

    if remove_annotations:
        writer.remove_links()

    with open(output_filename, "wb") as output_file:
        writer.write(output_file)
