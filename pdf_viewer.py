"""
Minimal PDF preview widget for Tkinter.

Replaces the old vendored copy of the `tkPDFViewer` module, which rendered into
a Text widget from a background thread and kept its images in class-level state.
Here a single page is rasterised with PyMuPDF and shown in a Label; the image
reference is held by the widget so Tk does not garbage-collect it.
"""

import tkinter as tk

import pymupdf


def render_page(pdf_bytes, max_width, max_height, page_number=0):
    """
    Rasterises one page of an in-memory PDF into a Tk image scaled to fit
    (max_width, max_height) while keeping its aspect ratio.
    """
    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as document:
        page = document[page_number]
        zoom = min(max_width / page.rect.width, max_height / page.rect.height)
        pixmap = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
        return tk.PhotoImage(data=pixmap.tobytes("ppm"))


class PdfPreview(tk.Frame):
    """
    Fixed-size preview area showing either a placeholder message or a PDF page.

    A Frame is used as the container because its width/height are always in
    pixels, whereas a Label switches to characters/lines as soon as it holds
    text instead of an image.
    """

    def __init__(self, master, width, height, **kwargs):
        super().__init__(master, width=width, height=height, bg="white",
                         highlightthickness=1, highlightbackground="#c8c8c8", **kwargs)
        self.grid_propagate(False)
        self.pack_propagate(False)

        self._max_width = width
        self._max_height = height
        self._image = None

        self._label = tk.Label(self, bg="white", wraplength=width - 20)
        self._label.place(relx=0.5, rely=0.5, anchor="center")

    def show_message(self, message):
        self._image = None
        self._label.configure(image="", text=message)

    def show_pdf(self, pdf_bytes, page_number=0):
        # Keep a reference: Tk only holds a weak one and the image would vanish.
        self._image = render_page(pdf_bytes, self._max_width, self._max_height, page_number)
        self._label.configure(image=self._image, text="")
