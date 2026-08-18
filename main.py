import math
import os
import threading
import tkinter as tk
from io import BytesIO
from tkinter import filedialog, messagebox, ttk

import sv_ttk
from pypdf import PdfReader, PdfWriter
from screeninfo import get_monitors

import pdf_viewer
from distribution import BLANK, DEFAULT_SHEETS_PER_BOOKLET, distribution_booklets_pages
from pdf_maker import get_dimensions, make_pdf, make_sheet_side, prepare_document

NO_FILE = "No file selected"
OUTPUT_SUFFIX = "-booklet"
PREVIEW_WIDTH = 600
PREVIEW_HEIGHT = 424
PROGRESS_REFRESH_MS = 100
# Options are applied live; wait for a pause in typing before re-rendering.
PREVIEW_DEBOUNCE_MS = 350


class Application(tk.Tk):
    def __init__(self, width=1180, height=860):
        super().__init__()
        self.title("Pdf2Book")

        sv_ttk.set_theme("light")

        pos_x, pos_y = self.centered_position(width, height)
        self.geometry(f"{width}x{height}+{pos_x}+{pos_y}")
        self.resizable(False, False)

        # Source document, cached so that changing an option does not re-read
        # the file from disk: only the endpaper padding is redone when needed.
        self.source_bytes = None
        self.source_path = None
        self.source_page_count = 0
        self.padded_pdf = None
        self.prepared_key = None
        self.preview_dimensions = None

        self.distrib_booklets_pages = None
        self.preview_booklet = 0
        self.preview_pair = 0
        self.endpapers = 0
        self.preview_job = None

        # Rendering runs in a worker thread. The thread only touches these three
        # plain attributes; every widget update happens on the main thread, from
        # poll_render(). Tk is not thread-safe, so widgets must not be touched
        # from anywhere else.
        self.render_thread = None
        self.render_error = None
        self.progress_total = 0
        self.progress_done = 0

        self.build_layout()
        self.bind_shortcuts()

        # Guard against the traces firing while the widgets are still being set up.
        self.ready = True

    # ----------------------------------------------------------------- layout

    def build_layout(self):
        container = ttk.Frame(self, padding=20)
        container.pack(fill="both", expand=True)
        container.grid_columnconfigure(0, minsize=440)
        container.grid_columnconfigure(1, weight=1)
        container.grid_rowconfigure(0, weight=1)

        left = ttk.Frame(container)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 20))

        right = ttk.Frame(container)
        right.grid(row=0, column=1, sticky="n")

        self.build_files(left)
        self.build_options(left)
        self.build_summary(left)
        self.build_preview(right)
        self.build_details(right)
        self.build_actions(container)

    def build_files(self, parent):
        frame = ttk.LabelFrame(parent, text="Files", padding=15)
        frame.pack(fill="x")
        frame.grid_columnconfigure(1, weight=1)

        self.input_variable = tk.StringVar(value=NO_FILE)
        ttk.Label(frame, text="Input").grid(row=0, column=0, sticky="w", pady=(0, 10))
        self.input_entry = ttk.Entry(frame, textvariable=self.input_variable, state="readonly", width=28)
        self.input_entry.grid(row=0, column=1, sticky="ew", padx=10, pady=(0, 10))
        ttk.Button(frame, text="Browse", command=self.select_input_file, width=8).grid(
            row=0, column=2, pady=(0, 10))

        self.output_variable = tk.StringVar(value=NO_FILE)
        ttk.Label(frame, text="Output").grid(row=1, column=0, sticky="w")
        self.output_entry = ttk.Entry(frame, textvariable=self.output_variable, state="readonly", width=28)
        self.output_entry.grid(row=1, column=1, sticky="ew", padx=10)
        ttk.Button(frame, text="Browse", command=self.select_output_file, width=8).grid(
            row=1, column=2)

        # A path is too long for the field: show its end, where the name is.
        for variable, entry in ((self.input_variable, self.input_entry),
                                (self.output_variable, self.output_entry)):
            variable.trace_add("write", lambda *_, widget=entry: widget.after_idle(widget.xview_moveto, 1.0))

        ttk.Label(frame, text="The output name is filled in automatically; browse to change it.",
                  foreground="gray").grid(row=2, column=0, columnspan=3, sticky="w", pady=(10, 0))

    def build_options(self, parent):
        frame = ttk.LabelFrame(parent, text="Options", padding=15)
        frame.pack(fill="x", pady=(20, 0))
        frame.grid_columnconfigure(1, weight=1)

        self.remove_annotations = tk.BooleanVar(value=True)
        ttk.Checkbutton(frame, text="Delete annotations", variable=self.remove_annotations).grid(
            row=0, column=0, columnspan=2, sticky="w")

        self.empty_pages = tk.StringVar(value="0")
        ttk.Label(frame, text="Endpapers (per side)").grid(row=1, column=0, sticky="w", pady=(15, 0))
        ttk.Entry(frame, textvariable=self.empty_pages, width=6, justify="center").grid(
            row=1, column=1, sticky="e", pady=(15, 0))
        ttk.Label(frame, text="Blank pages to glue to the cover, added at both ends.",
                  foreground="gray", wraplength=380).grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(4, 0))

        ttk.Separator(frame).grid(row=3, column=0, columnspan=2, sticky="ew", pady=15)

        self.page_numbers = tk.BooleanVar(value=False)
        ttk.Checkbutton(frame, text="Add page numbers", variable=self.page_numbers,
                        command=self.toggle_numbering).grid(row=4, column=0, columnspan=2, sticky="w")

        self.numbering_start = tk.StringVar(value="1")
        self.numbering_start_label = ttk.Label(frame, text="Start on physical page")
        self.numbering_start_label.grid(row=5, column=0, sticky="w", pady=(10, 0))
        self.numbering_start_entry = ttk.Entry(frame, textvariable=self.numbering_start,
                                               width=6, justify="center")
        self.numbering_start_entry.grid(row=5, column=1, sticky="e", pady=(10, 0))
        self.numbering_hint = ttk.Label(
            frame, text="That page gets the number 1. Earlier pages and the endpapers stay blank.",
            foreground="gray", wraplength=380)
        self.numbering_hint.grid(row=6, column=0, columnspan=2, sticky="w", pady=(4, 0))
        self.toggle_numbering()

        ttk.Separator(frame).grid(row=7, column=0, columnspan=2, sticky="ew", pady=15)

        ttk.Label(frame, text="Distribution").grid(row=8, column=0, columnspan=2, sticky="w")
        self.radio_value = tk.StringVar(value="auto")
        for index, (value, text) in enumerate((
            ("auto", "Auto"),
            ("booklet", "Specify number of booklets"),
            ("sheet", "Specify number of sheets per booklet"),
        )):
            ttk.Radiobutton(frame, text=text, variable=self.radio_value, value=value,
                            command=self.change_entry).grid(
                row=9 + index, column=0, columnspan=2, sticky="w", pady=(6, 0))

        self.variable_title_entry = tk.StringVar(value="Number of booklets")
        self.title_entry = ttk.Label(frame, textvariable=self.variable_title_entry)
        self.variable_entry = tk.StringVar()
        self.number_entry = ttk.Entry(frame, textvariable=self.variable_entry, width=6, justify="center")

        for variable in (self.empty_pages, self.variable_entry, self.radio_value,
                         self.remove_annotations, self.page_numbers, self.numbering_start):
            variable.trace_add("write", self.schedule_preview_refresh)

    def toggle_numbering(self):
        state = "normal" if self.page_numbers.get() else "disabled"
        self.numbering_start_label.configure(state=state)
        self.numbering_start_entry.configure(state=state)
        self.numbering_hint.configure(state=state)

    def build_summary(self, parent):
        frame = ttk.LabelFrame(parent, text="Result", padding=15)
        frame.pack(fill="x", pady=(20, 0))

        self.summary_variable = tk.StringVar(value="Select a PDF file to start.")
        ttk.Label(frame, textvariable=self.summary_variable, wraplength=380,
                  justify="left").pack(anchor="w")

    def build_preview(self, parent):
        self.preview = pdf_viewer.PdfPreview(parent, width=PREVIEW_WIDTH, height=PREVIEW_HEIGHT)
        self.preview.pack()
        self.preview.show_message(NO_FILE)

        navigation = ttk.Frame(parent)
        navigation.pack(fill="x", pady=(15, 0))
        navigation.grid_columnconfigure(1, weight=1)

        ttk.Button(navigation, text="‹", width=4, command=self.previous_preview).grid(row=0, column=0)
        self.navigation_variable = tk.StringVar(value="")
        ttk.Label(navigation, textvariable=self.navigation_variable, anchor="center").grid(
            row=0, column=1, sticky="ew")
        ttk.Button(navigation, text="›", width=4, command=self.next_preview).grid(row=0, column=2)

    def build_details(self, parent):
        frame = ttk.LabelFrame(parent, text="Current sheet", padding=15)
        frame.pack(fill="x", pady=(20, 0))
        frame.grid_columnconfigure(1, weight=1)

        self.booklet_value = tk.StringVar(value="-")
        self.booklet_sheet_value = tk.StringVar(value="-")
        self.sheet_value = tk.StringVar(value="-")
        self.page_input_value = tk.StringVar(value="-")
        self.page_value = tk.StringVar(value="-")

        rows = (
            ("Booklet", self.booklet_value),
            ("Sheet inside this booklet", self.booklet_sheet_value),
            ("Sheet overall", self.sheet_value),
            ("Pages of the input file", self.page_input_value),
            ("Page of the output file", self.page_value),
        )
        for index, (text, variable) in enumerate(rows):
            ttk.Label(frame, text=text).grid(row=index, column=0, sticky="w", pady=3)
            ttk.Label(frame, textvariable=variable, anchor="e", width=10).grid(
                row=index, column=1, sticky="e", pady=3)

    def build_actions(self, parent):
        frame = ttk.Frame(parent)
        frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(20, 0))
        frame.grid_columnconfigure(0, weight=1)

        self.button_render_pdf = ttk.Button(frame, text="Render PDF", command=self.render, style="Accent.TButton")
        self.button_render_pdf.grid(row=0, column=0)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(frame, variable=self.progress_var, maximum=100)

        self.error_variable = tk.StringVar()
        self.error_label = ttk.Label(frame, textvariable=self.error_variable, foreground="#c0392b",
                                     wraplength=1100, justify="center", anchor="center")

    def bind_shortcuts(self):
        self.bind("<Left>", self.on_arrow_key)
        self.bind("<Right>", self.on_arrow_key)

    def on_arrow_key(self, event):
        # Let the arrows move the caret when the user is typing in a field.
        if isinstance(self.focus_get(), (ttk.Entry, tk.Entry)):
            return
        self.move_preview(-1 if event.keysym == "Left" else 1)

    @staticmethod
    def centered_position(width, height):
        """
        Top-left corner centring the window on the primary monitor.
        """
        try:
            monitors = get_monitors()
        except Exception:  # no monitor detected (headless, remote display, ...)
            monitors = []

        if monitors:
            monitor = next((m for m in monitors if m.is_primary), monitors[0])
            return (monitor.x + (monitor.width - width) // 2,
                    monitor.y + (monitor.height - height) // 2)

        return 0, 0

    # ---------------------------------------------------------------- errors

    def set_error(self, error):
        self.error_variable.set(f"Error : {error}")
        self.error_label.grid(row=2, column=0, sticky="ew", pady=(15, 0))

    def clear_error(self):
        self.error_variable.set("")
        self.error_label.grid_forget()

    # -------------------------------------------------------------- progress

    def progress_init(self, max_value):
        """
        Called from the worker thread: record the total, do not touch widgets.
        """
        self.progress_total = max_value
        self.progress_done = 0

    def update_progress(self):
        """
        Called from the worker thread once per rendered side.
        """
        self.progress_done += 1

    def refresh_progress(self):
        self.progress_bar["maximum"] = max(self.progress_total, 1)
        self.progress_var.set(min(self.progress_done, self.progress_total))

    # ------------------------------------------------------------ validation

    def read_options(self, preview=False):
        """
        Validates the form and returns the keyword arguments for make_pdf.

        Raises ValueError with a user-facing message when something is wrong.
        In preview mode the output file is not required.
        """
        if self.input_variable.get() == NO_FILE:
            raise ValueError("No input file selected")

        if not preview and self.output_variable.get() == NO_FILE:
            raise ValueError("No output file selected")

        mode = self.radio_value.get()
        number = self.variable_entry.get().strip()
        n_booklets, n_sheets = "auto", DEFAULT_SHEETS_PER_BOOKLET

        if mode in ("booklet", "sheet"):
            label = "booklets" if mode == "booklet" else "sheets"
            if not number.isdigit() or int(number) < 1:
                raise ValueError(f"Number of {label} must be an integer greater than 0")
            if mode == "booklet":
                n_booklets = int(number)
            else:
                n_sheets = int(number)

        endpapers = self.empty_pages.get().strip()
        if not endpapers.isdigit():
            raise ValueError("Number of endpapers must be an integer greater than or equal to 0")

        start = self.numbering_start.get().strip()
        if self.page_numbers.get() and (not start.isdigit() or int(start) < 1):
            raise ValueError("The first numbered page must be an integer greater than 0")

        return {
            "n_booklets": n_booklets,
            "n_sheets": n_sheets,
            "empty_pages": int(endpapers),
            "page_numbers": self.page_numbers.get(),
            "numbering_start": int(start) if start.isdigit() else 1,
        }

    # --------------------------------------------------------------- preview

    def load_source(self, options):
        """
        Returns the document to impose, endpapers and page numbers included.

        The file bytes and the prepared document are cached separately, so
        changing only the distribution costs nothing and browsing the preview
        never rebuilds anything.
        """
        path = self.input_variable.get()

        if path != self.source_path:
            with open(path, "rb") as input_file:
                self.source_bytes = input_file.read()
            self.source_path = path
            self.source_page_count = len(PdfReader(BytesIO(self.source_bytes)).pages)
            self.prepared_key = None

        key = (options["empty_pages"], options["page_numbers"], options["numbering_start"])
        if key != self.prepared_key:
            reader = prepare_document(PdfReader(BytesIO(self.source_bytes)), *key)
            self.padded_pdf = reader
            self.preview_dimensions = get_dimensions(reader.pages)
            self.prepared_key = key

        self.endpapers = options["empty_pages"]
        return self.padded_pdf

    def schedule_preview_refresh(self, *_):
        """
        Trace callback on the option variables: refresh once typing settles.
        """
        if not getattr(self, "ready", False):
            return
        if self.preview_job is not None:
            self.after_cancel(self.preview_job)
        self.preview_job = self.after(PREVIEW_DEBOUNCE_MS, self.update_preview)

    def update_preview(self):
        """
        Recomputes the distribution from the current options and redraws.
        """
        self.preview_job = None
        try:
            options = self.read_options(preview=True)
            reader = self.load_source(options)
            self.distrib_booklets_pages = distribution_booklets_pages(
                len(reader.pages), options["n_booklets"], options["n_sheets"])
            self.clamp_preview_position()
            self.show_preview()
            self.summary_variable.set(self.summary_text(options))
        except Exception as error:
            self.distrib_booklets_pages = None
            self.preview.show_message(f"Cannot preview : {error}")
            self.summary_variable.set(str(error))
            self.navigation_variable.set("")

    def clamp_preview_position(self):
        """
        Keeps the current position valid after the distribution changed.
        """
        self.preview_booklet = min(self.preview_booklet, len(self.distrib_booklets_pages) - 1)
        self.preview_pair = min(self.preview_pair, len(self.distrib_booklets_pages[self.preview_booklet]) - 1)

    def summary_text(self, options):
        """
        One-paragraph recap of what the program decided on its own.
        """
        booklets = self.distrib_booklets_pages
        sheets = [math.ceil(len(booklet) / 2) for booklet in booklets]
        # Endpapers are real (blank) pages of the padded document, so the BLANK
        # sentinels left in the distribution are exactly the filler pages.
        padding = sum(1 for booklet in booklets for pair in booklet for page in pair if page == BLANK)
        total = self.source_page_count + 2 * self.endpapers

        lines = [f"{self.source_page_count} pages"]
        if self.endpapers:
            lines[0] += f" + {self.endpapers} endpapers on each side = {total} pages"

        counts = " + ".join(str(sheet) for sheet in sheets)
        booklet_word = "booklet" if len(booklets) == 1 else "booklets"
        lines.append(f"{len(booklets)} {booklet_word} of {counts} sheets, {sum(sheets)} sheets in total.")

        if padding > 0:
            page_word = "page" if padding == 1 else "pages"
            lines.append(f"{padding} blank {page_word} added at the very end to fill the last sheet.")

        if options["page_numbers"]:
            first = options["numbering_start"]
            last = total - self.endpapers
            if first > last:
                lines.append("No page numbered: numbering starts past the last page.")
            else:
                lines.append(f"Numbers 1 to {last - first + 1} printed on physical pages "
                             f"{first} to {last}.")

        return "\n".join(lines)

    def source_page_label(self, index):
        """
        Page number as it appears in the file the user selected.

        Endpapers and filler pages have no counterpart there.
        """
        if index == BLANK:
            return "—"
        original = index - self.endpapers
        if 0 <= original < self.source_page_count:
            return str(original + 1)
        return "—"

    def show_preview(self):
        """
        Renders the currently selected printed side into the preview area.
        """
        pair = self.distrib_booklets_pages[self.preview_booklet][self.preview_pair]
        width, height = self.preview_dimensions

        writer = PdfWriter()
        writer.add_page(make_sheet_side(self.padded_pdf, pair, width, height))
        if self.remove_annotations.get():
            writer.remove_links()

        buffer = BytesIO()
        writer.write(buffer)
        self.preview.show_pdf(buffer.getvalue())

        page = self.current_page()
        total_sheets = sum(math.ceil(len(booklet) / 2) for booklet in self.distrib_booklets_pages)
        sheet = (page + 1) // 2
        side = "front" if self.preview_pair % 2 == 0 else "back"

        self.navigation_variable.set(f"Sheet {sheet} of {total_sheets} · {side}")
        self.booklet_value.set(f"{self.preview_booklet + 1} / {len(self.distrib_booklets_pages)}")
        self.booklet_sheet_value.set(str((self.preview_pair // 2) + 1))
        self.sheet_value.set(str(sheet))
        self.page_value.set(str(page))
        self.page_input_value.set(" – ".join(self.source_page_label(index) for index in pair))

    def current_page(self):
        """
        1-based index of the current side in the output file.
        """
        previous = sum(len(booklet) for booklet in self.distrib_booklets_pages[:self.preview_booklet])
        return previous + self.preview_pair + 1

    def move_preview(self, step):
        if not self.distrib_booklets_pages:
            return

        self.preview_pair += step
        booklets = self.distrib_booklets_pages

        if self.preview_pair >= len(booklets[self.preview_booklet]):
            self.preview_booklet = (self.preview_booklet + 1) % len(booklets)
            self.preview_pair = 0
        elif self.preview_pair < 0:
            self.preview_booklet = (self.preview_booklet - 1) % len(booklets)
            self.preview_pair = len(booklets[self.preview_booklet]) - 1

        self.show_preview()

    def next_preview(self):
        self.move_preview(1)

    def previous_preview(self):
        self.move_preview(-1)

    def reset_preview(self):
        self.distrib_booklets_pages = None
        self.preview_booklet = 0
        self.preview_pair = 0
        self.preview.show_message(NO_FILE)
        self.navigation_variable.set("")
        self.summary_variable.set("Select a PDF file to start.")
        for variable in (self.booklet_value, self.booklet_sheet_value, self.sheet_value,
                         self.page_input_value, self.page_value):
            variable.set("-")

    # ------------------------------------------------------------- rendering

    def render(self):
        if self.render_thread is not None and self.render_thread.is_alive():
            self.set_error("A process is already running")
            return

        try:
            options = self.read_options()
        except Exception as error:
            self.set_error(error)
            return

        self.clear_error()
        self.render_error = None
        self.progress_total = 0
        self.progress_done = 0

        self.render_thread = threading.Thread(
            target=self.thread_make_pdf,
            args=(self.input_variable.get(), self.output_variable.get()),
            kwargs={**options, "remove_annotations": self.remove_annotations.get(), "progress": self},
            daemon=True,
        )
        self.render_thread.start()

        self.progress_bar.grid(row=1, column=0, sticky="ew", pady=(15, 0))
        self.after(PROGRESS_REFRESH_MS, self.poll_render)

    def thread_make_pdf(self, input_file, output_file, **kwargs):
        """
        Worker thread. Never touches a widget: errors are stored and picked up
        by poll_render() on the main thread.
        """
        try:
            make_pdf(input_file, output_file, **kwargs)
        except Exception as error:
            self.render_error = error

    def poll_render(self):
        """
        Main-thread poller driving the progress bar and reporting the outcome.
        """
        self.refresh_progress()

        if self.render_thread.is_alive():
            self.after(PROGRESS_REFRESH_MS, self.poll_render)
            return

        self.progress_bar.grid_forget()

        if self.render_error is not None:
            self.set_error(self.render_error)
            self.render_error = None
        else:
            self.clear_error()
            messagebox.showinfo("Success", "PDF created successfully")

    # ----------------------------------------------------------------- files

    def change_entry(self):
        mode = self.radio_value.get()
        if mode in ("booklet", "sheet"):
            self.variable_title_entry.set(
                "Number of booklets" if mode == "booklet" else "Number of sheets per booklet"
            )
            self.title_entry.grid(row=12, column=0, sticky="w", pady=(10, 0))
            self.number_entry.grid(row=12, column=1, sticky="e", pady=(10, 0))
        else:
            self.title_entry.grid_forget()
            self.number_entry.grid_forget()

    @staticmethod
    def default_output(input_path):
        """
        Sibling of the input file, with a suffix: book.pdf -> book-booklet.pdf.
        """
        directory, filename = os.path.split(input_path)
        stem, extension = os.path.splitext(filename)
        return os.path.join(directory, f"{stem}{OUTPUT_SUFFIX}{extension or '.pdf'}")

    def select_input_file(self):
        filename = filedialog.askopenfilename(
            initialdir=os.path.expanduser("~"), title="Select a file",
            filetypes=[("PDF files", "*.pdf")])

        if filename:
            self.reset_preview()
            self.input_variable.set(filename)
            self.output_variable.set(self.default_output(filename))
            self.update_preview()

    def select_output_file(self):
        current = self.output_variable.get()
        directory = os.path.dirname(current) if current != NO_FILE else os.path.expanduser("~")
        initial = os.path.basename(current) if current != NO_FILE else "output.pdf"

        filename = filedialog.asksaveasfilename(
            defaultextension=".pdf", initialdir=directory,
            filetypes=[("PDF files", "*.pdf")], title="Select a file",
            initialfile=initial)

        if filename:
            self.output_variable.set(filename)


if __name__ == "__main__":
    app = Application()
    app.mainloop()
