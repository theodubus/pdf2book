"""
Tests for the page-fitting rules (letterboxing, rotation, reference format).

Run with `pytest`, or directly:

    python test_pdf_maker.py
"""

from io import BytesIO

import pymupdf
import pytest
from pypdf import PdfReader, PdfWriter

from distribution import BLANK
from pdf_maker import (add_empty_pages, add_page_numbers, get_dimensions, make_pdf,
                       make_sheet_side, prepare_document)

A4 = (595, 842)
A4_LANDSCAPE = (842, 595)
LETTER = (612, 792)


def build_pdf(sizes):
    """
    In-memory PDF with one bordered page per (width, height) given, so the
    outline of each source page can be measured in the output.
    """
    document = pymupdf.open()
    for index, (width, height) in enumerate(sizes):
        page = document.new_page(width=width, height=height)
        page.draw_rect(pymupdf.Rect(0, 0, width, height), color=(0, 0, 0), width=2)
        page.insert_text((30, 60), f"page {index + 1}", fontsize=24)
    return PdfReader(BytesIO(document.tobytes()))


def blank_pdf(count, size=A4):
    """
    Wordless pages, so any text found afterwards can only be a page number.
    """
    document = pymupdf.open()
    for _ in range(count):
        document.new_page(width=size[0], height=size[1])
    return PdfReader(BytesIO(document.tobytes()))


def stamped_numbers(reader):
    """
    Text found on each page, '' when the page carries none.
    """
    return [page.extract_text().strip() for page in reader.pages]


def render(page):
    """
    Rasterises a single pypdf page through pymupdf so it can be inspected.
    """
    writer = PdfWriter()
    writer.add_page(page)
    buffer = BytesIO()
    writer.write(buffer)
    return pymupdf.open(stream=buffer.getvalue(), filetype="pdf")[0]


def drawn_boxes(page):
    """
    Bounding boxes of the borders drawn on a rendered sheet, left to right.
    """
    boxes = [d["rect"] for d in page.get_drawings()]
    return sorted(boxes, key=lambda rect: rect.x0)


# ------------------------------------------------------------ reference format


def test_reference_format_is_the_most_common_one():
    reader = build_pdf([A4, A4, A4, LETTER])
    assert get_dimensions(reader.pages) == (595.0, 842.0)


def test_reference_format_is_always_a_real_page_format():
    # Regression: taking the modal width and the modal height separately used to
    # yield 595x595 here, a square no page of the document actually has.
    reader = build_pdf([A4, A4, A4_LANDSCAPE, A4_LANDSCAPE, A4_LANDSCAPE])
    assert get_dimensions(reader.pages) == (842.0, 595.0)


def test_empty_document_is_rejected():
    with pytest.raises(ValueError):
        get_dimensions([])


# ------------------------------------------------------------------- geometry


def test_sheet_is_the_reference_format_rotated():
    reader = build_pdf([A4, A4])
    sheet = make_sheet_side(reader, (0, 1), 595, 842)
    assert (float(sheet.mediabox.width), float(sheet.mediabox.height)) == (595, 421)


def test_matching_format_fills_its_half_exactly():
    reader = build_pdf([A4, A4])
    left, right = drawn_boxes(render(make_sheet_side(reader, (0, 1), 595, 842)))

    assert left.x0 == pytest.approx(0, abs=1)
    assert left.x1 == pytest.approx(297.5, abs=1)
    assert right.x0 == pytest.approx(297.5, abs=1)
    assert right.x1 == pytest.approx(595, abs=1)
    for box in (left, right):
        assert box.y0 == pytest.approx(0, abs=1)
        assert box.y1 == pytest.approx(421, abs=1)


def test_blank_slot_stays_empty():
    reader = build_pdf([A4, A4])
    assert len(drawn_boxes(render(make_sheet_side(reader, (BLANK, 1), 595, 842)))) == 1
    assert len(drawn_boxes(render(make_sheet_side(reader, (0, BLANK), 595, 842)))) == 1


def test_odd_format_keeps_its_aspect_ratio_and_is_centred():
    reader = build_pdf([A4, A4, A4, LETTER])
    # Pair the Letter page (index 3) with an A4 one.
    letter, _ = drawn_boxes(render(make_sheet_side(reader, (3, 0), 595, 842)))

    source_ratio = LETTER[0] / LETTER[1]
    assert letter.width / letter.height == pytest.approx(source_ratio, rel=0.01)
    # Centred in its half: equal margins above and below.
    assert letter.y0 == pytest.approx(421 - letter.y1, abs=1)


def test_letterboxing_never_overflows_its_half():
    reader = build_pdf([A4, A4, A4, LETTER])
    letter, _ = drawn_boxes(render(make_sheet_side(reader, (3, 0), 595, 842)))
    assert letter.x0 >= -1 and letter.x1 <= 297.5 + 1
    assert letter.y0 >= -1 and letter.y1 <= 421 + 1


# ------------------------------------------------------------------- rotation


def text_direction(page):
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            if "".join(span["text"] for span in line["spans"]).strip():
                return tuple(round(value) for value in line["dir"])
    raise AssertionError("no text found on the rendered sheet")


def test_page_of_opposite_orientation_is_rotated():
    reader = build_pdf([A4_LANDSCAPE, A4, A4, A4])
    sheet = render(make_sheet_side(reader, (0, BLANK), 595, 842))
    # (0, -1) in pymupdf's y-down space: the text reads bottom-to-top, so the
    # reader turns the book clockwise.
    assert text_direction(sheet) == (0, -1)


def test_page_of_matching_orientation_is_not_rotated():
    reader = build_pdf([A4, A4])
    assert text_direction(render(make_sheet_side(reader, (0, BLANK), 595, 842))) == (1, 0)


def test_rotated_landscape_page_fills_the_slot():
    # A4 landscape rotated becomes A4 portrait: same ratio as the slot, no margin.
    reader = build_pdf([A4_LANDSCAPE, A4, A4, A4])
    box = drawn_boxes(render(make_sheet_side(reader, (0, BLANK), 595, 842)))[0]
    assert box.width == pytest.approx(297.5, abs=1)
    assert box.height == pytest.approx(421, abs=1)


# ----------------------------------------------------------------- whole file


def test_add_empty_pages_pads_both_ends():
    reader = build_pdf([A4, A4, A4])
    padded = add_empty_pages(reader, 2)
    assert len(padded.pages) == 7
    assert padded.pages[0].extract_text().strip() == ""
    assert padded.pages[-1].extract_text().strip() == ""
    assert "page 1" in padded.pages[2].extract_text()


def test_add_empty_pages_is_a_no_op_for_zero():
    reader = build_pdf([A4, A4])
    assert add_empty_pages(reader, 0) is reader


# ------------------------------------------------------------ page numbering


def test_every_page_is_numbered_by_default():
    assert stamped_numbers(add_page_numbers(blank_pdf(5))) == ["1", "2", "3", "4", "5"]


def test_numbering_restarts_at_one_on_the_first_numbered_page():
    # Physical pages 1 and 2 stay blank; page 3 becomes number 1.
    assert stamped_numbers(add_page_numbers(blank_pdf(6), first_page=3)) == [
        "", "", "1", "2", "3", "4"]


def test_pages_after_the_range_stay_blank():
    assert stamped_numbers(add_page_numbers(blank_pdf(6), first_page=2, last_page=4)) == [
        "", "1", "2", "3", "", ""]


def test_numbering_outside_the_document_changes_nothing():
    reader = blank_pdf(3)
    assert add_page_numbers(reader, first_page=10) is reader


def test_number_sits_at_the_bottom_centre():
    buffer = BytesIO()
    PdfWriter(clone_from=add_page_numbers(blank_pdf(1))).write(buffer)
    document = pymupdf.open(stream=buffer.getvalue(), filetype="pdf")

    rect = document[0].rect
    x0, _, x1, y1 = document[0].get_text("dict")["blocks"][0]["lines"][0]["bbox"]
    assert (x0 + x1) / 2 == pytest.approx(rect.width / 2, abs=2)          # centred
    assert rect.height - y1 == pytest.approx(rect.height / 14, rel=0.3)   # near the bottom


def test_prepare_document_numbers_the_content_not_the_endpapers():
    # 4 real pages, 1 endpaper each side, numbering starting after the first one.
    reader = prepare_document(blank_pdf(4), empty_pages=1, page_numbers=True, numbering_start=2)
    assert stamped_numbers(reader) == ["", "1", "2", "3", "4", ""]


def test_numbers_survive_the_imposition(tmp_path):
    source = tmp_path / "in.pdf"
    document = pymupdf.open()
    for _ in range(4):
        document.new_page(width=A4[0], height=A4[1])
    document.save(source)

    output = tmp_path / "out.pdf"
    make_pdf(str(source), str(output), page_numbers=True)

    # 4 pages = 1 sheet: front carries 4 and 1, back carries 2 and 3.
    rendered = pymupdf.open(output)
    assert sorted(rendered[0].get_text().split()) == ["1", "4"]
    assert sorted(rendered[1].get_text().split()) == ["2", "3"]


def test_make_pdf_writes_one_page_per_printed_side(tmp_path):
    source = tmp_path / "in.pdf"
    document = pymupdf.open()
    for _ in range(10):
        document.new_page(width=A4[0], height=A4[1])
    document.save(source)

    output = tmp_path / "out.pdf"
    make_pdf(str(source), str(output))

    # 10 pages padded to 12 = 3 sheets = 6 printed sides.
    assert len(pymupdf.open(output)) == 6


def test_make_pdf_refuses_to_overwrite_its_input(tmp_path):
    source = tmp_path / "in.pdf"
    document = pymupdf.open()
    document.new_page()
    document.save(source)

    with pytest.raises(ValueError):
        make_pdf(str(source), str(tmp_path / "." / "in.pdf"))


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
