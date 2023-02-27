from pdf_maker import *
import tkinter as tk
from tkinter import filedialog
from screeninfo import get_monitors
import os
from tkinter.ttk import Progressbar
import threading
import time
from tkinter import messagebox
import PyPDF2
from distribution import distribution_booklets_pages
import pdf_viewer as pdf

class Application(tk.Tk):
    def __init__(self, height=800, width=1200):
        super().__init__()
        self.title("Printable PDF Maker")

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        central_monitor = len(get_monitors()) // 2
        cumulated_width = sum([get_monitors()[i].width for i in range(central_monitor)])

        pos_x = screen_width // 2 - width // 2 + cumulated_width // 2
        pos_y = screen_height // 2 - height // 2

        self.geometry(f"{width}x{height}+{pos_x}+{pos_y}")

        self.resizable(False, False)

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, minsize=300, weight=1)
        self.grid_columnconfigure(3, minsize=300, weight=1)
        self.grid_columnconfigure(4, minsize=300, weight=1)

        self.title_input = tk.Label(self, text="Input file : ")
        self.title_input.grid(row=0, column=0, sticky="w", padx=(30, 0), pady=(20, 0), columnspan=2)

        self.input_variable = tk.StringVar()
        self.input_variable.set("No file selected")
        self.input_file = tk.Label(self, textvariable=self.input_variable, bg="white", anchor="w", width=30)
        self.input_file.grid(row=0, column=2, pady=(20, 0), sticky="ew", columnspan=2)

        self.button_input = tk.Button(self, text="Select a file", command=self.select_input_file)
        self.button_input.grid(row=0, column=4, sticky="e", pady=(20, 0), padx=(0, 30))


        self.title_output = tk.Label(self, text="Output file : ")
        self.title_output.grid(row=1, column=0, sticky="w", padx=(30, 0), columnspan=2)

        self.output_variable = tk.StringVar()
        self.output_variable.set("No file selected")
        self.output_file = tk.Label(self, textvariable=self.output_variable, bg="white", anchor="w", width=30)
        self.output_file.grid(row=1, column=2, sticky="ew", columnspan=2)

        self.button_output = tk.Button(self, text="Select a file", command=self.select_output_file)
        self.button_output.grid(row=1, column=4, sticky="e", padx=(0, 30))

        self.remove_annotations = tk.BooleanVar()
        self.remove_annotations.set(True)
        self.check_remove_annotations = tk.Checkbutton(self, text="Delete annotations", variable=self.remove_annotations, onvalue=True, offvalue=False)
        self.check_remove_annotations.grid(row=2, column=0, sticky="w", padx=(25, 0), pady=(20, 0), columnspan=2)

        self.label_distribution = tk.Label(self, text="Distribution : ")
        self.label_distribution.grid(row=3, column=0, sticky="w", padx=(30, 0), pady=(20, 0), columnspan=2)

        self.radio_value = tk.StringVar()
        self.radio_value.set("auto")
        self.radio_auto = tk.Radiobutton(self, text="Auto", variable=self.radio_value, value="auto", command=self.change_entry)
        self.radio_auto.grid(row=4, column=0, sticky="w", padx=(25, 0), columnspan=2)
        self.radio_booklet = tk.Radiobutton(self, text="Specify number of booklets", variable=self.radio_value, value="booklet", command=self.change_entry)
        self.radio_booklet.grid(row=5, column=0, sticky="w", padx=(25, 0), columnspan=2)
        self.radio_sheet = tk.Radiobutton(self, text="Specify number of sheets per booklet", variable=self.radio_value, value="sheet", command=self.change_entry)
        self.radio_sheet.grid(row=6, column=0, sticky="w", pady=(0, 20), padx=(25, 0), columnspan=2)
        
        self.preview_variable = tk.StringVar()
        self.preview_variable.set("No file selected")
        self.preview_label = tk.Label(self, bg="white", width=75, height=25, textvariable=self.preview_variable)
        self.preview_label.grid(row=2, column=2, columnspan=3, rowspan=11, pady=(30, 0))
        self.preview_pdf = None
        self.preview_booklet = None
        self.preview_pair = None
        self.preview_file = f"{os.path.dirname(os.path.realpath(__file__))}/temp/preview.pdf"
        self.distrib_booklets_pages = None

        self.label_booklet = tk.Label(self, text="Current booklet : ")
        self.label_booklet.grid(row=8, column=0, sticky="w", padx=(30, 0), pady=(20, 0))

        self.booklet_value = tk.IntVar()
        self.booklet_value.set(1)
        self.label_booklet_value = tk.Label(self, textvariable=self.booklet_value, bg="white", width=7)
        self.label_booklet_value.grid(row=8, column=1, sticky="e", pady=(20, 0))

        self.label_booklet_sheet = tk.Label(self, text="Current sheet for this booklet : ")
        self.label_booklet_sheet.grid(row=9, column=0, sticky="w", padx=(30, 0), pady=(20, 0))

        self.booklet_sheet_value = tk.IntVar()
        self.booklet_sheet_value.set(1)
        self.label_booklet_sheet_value = tk.Label(self, textvariable=self.booklet_sheet_value, bg="white", width=7)
        self.label_booklet_sheet_value.grid(row=9, column=1, sticky="e", pady=(20, 0))

        self.label_sheet = tk.Label(self, text="Current sheet : ")
        self.label_sheet.grid(row=10, column=0, sticky="w", padx=(30, 0), pady=(20, 0))

        self.sheet_value = tk.IntVar()
        self.sheet_value.set(1)
        self.label_sheet_value = tk.Label(self, textvariable=self.sheet_value, bg="white", width=7)
        self.label_sheet_value.grid(row=10, column=1, sticky="e", pady=(20, 0))

        self.label_page_input = tk.Label(self, text="Current pages in the input file : ")
        self.label_page_input.grid(row=11, column=0, sticky="w", padx=(30, 0), pady=(20, 0))

        self.page_input_value = tk.StringVar()
        self.page_input_value.set("")
        self.label_page_input_value = tk.Label(self, textvariable=self.page_input_value, bg="white", width=7)
        self.label_page_input_value.grid(row=11, column=1, sticky="e", pady=(20, 0))

        self.label_page = tk.Label(self, text="Current page in the output file : ")
        self.label_page.grid(row=12, column=0, sticky="w", padx=(30, 0), pady=(20, 0))

        self.page_value = tk.IntVar()
        self.page_value.set(1)
        self.label_page_value = tk.Label(self, textvariable=self.page_value, bg="white", width=7)
        self.label_page_value.grid(row=12, column=1, sticky="e", pady=(20, 0))

        self.button_preview_previous = tk.Button(self, text="<", command=self.previous_preview)
        self.button_preview_previous.grid(row=13, column=2, sticky="e", pady=(20), padx=(0, 10))

        self.button_preview_update = tk.Button(self, text="Update preview", command=self.update_preview)
        self.button_preview_update.grid(row=13, column=3, sticky="ew", pady=(20))

        self.button_preview_next = tk.Button(self, text=">", command=self.next_preview)
        self.button_preview_next.grid(row=13, column=4, sticky="w", pady=(20), padx=(10, 0))

        self.variable_title_entry = tk.StringVar()
        self.variable_title_entry.set("Number of booklets : ")
        self.title_entry = tk.Label(self, textvariable=self.variable_title_entry)

        self.variable_entry = tk.StringVar()
        self.number_entry = tk.Entry(self, textvariable=self.variable_entry, width=7)        

        self.button_render_pdf = tk.Button(self, text="Render PDF", command=self.render)
        self.button_render_pdf.grid(row=14, column=0, columnspan=5, pady=(20))
        self.make_thread = None
        self.exception_render_thread = None
        self.errors = []

        self.progression_label = tk.Label(self, text="Loading : ")
        self.progress_var = tk.DoubleVar()
        self.progress_bar = Progressbar(self, variable=self.progress_var, maximum=100)

        self.error_variable = tk.StringVar()
        self.error_label = tk.Label(self, textvariable=self.error_variable, fg="red")

    def set_error(self, error):
        self.error_variable.set(f"Error : {error}")
        self.error_label.grid(row=16, column=0, columnspan=5, sticky="we", padx=(30, 30), pady=(20, 0))

    def clear_error(self):
        self.error_variable.set("")
        self.error_label.grid_forget()

    def progress_init(self, max_value):
        self.progress_var.set(0)
        self.progress_bar["maximum"] = max_value
        self.progression_label.grid(row=15, column=0, sticky="w", padx=(30, 0), pady=(20, 0))
        self.progress_bar.grid(row=15, column=1, columnspan=4, sticky="we", padx=(0, 30), pady=(20, 0))

    def update_progress(self):
        progress = self.progress_var.get() + 1
        if progress > self.progress_bar["maximum"]:
            progress = 0
        self.progress_var.set(progress)

    def valid_data(self, preview=False):
        input_file = self.input_variable.get()
        output_file = self.output_variable.get()
        number = self.variable_entry.get()

        if input_file == "No file selected":
            if not preview:
                self.set_error("No input file selected")
            return False
        
        if not preview:
            if output_file == "No file selected":
                self.set_error("No output file selected")
                return False
        
        if self.radio_value.get() == "booklet":
            if number == "":
                if not preview:
                    self.set_error("No number of booklets specified")
                return False
            if not number.isdigit() or int(number) < 1:
                if not preview:
                    self.set_error("Number of booklets must be an integer greater than 0")
                return False
            
        elif self.radio_value.get() == "sheet":
            if number == "":
                if not preview:
                    self.set_error("No number of sheets specified")
                return False
            if not number.isdigit() or int(number) < 1:
                if not preview:
                    self.set_error("Number of sheets must be an integer greater than 0")
                return False
            
        self.clear_error()
        return True

    def render(self):
        input_file = self.input_variable.get()
        output_file = self.output_variable.get()
        remove_annotations = self.remove_annotations.get()
        number = self.variable_entry.get()

        if not self.valid_data():
            return
        
        if (self.make_thread is not None and self.make_thread.is_alive()) or (self.exception_render_thread is not None and self.exception_render_thread.is_alive()):
            self.set_error("A process is already running")
            return
        
        try:
            if self.radio_value.get() == "booklet":
                self.make_thread = threading.Thread(target=self.thread_make_pdf, args=(input_file, output_file), kwargs={"remove_annotations": remove_annotations, "n_booklets": int(number), "progress": self})
                self.make_thread.start()
            elif self.radio_value.get() == "sheet":
                self.make_thread = threading.Thread(target=self.thread_make_pdf, args=(input_file, output_file), kwargs={"remove_annotations": remove_annotations, "n_sheets": int(number), "progress": self})
                self.make_thread.start()
            else:
                self.make_thread = threading.Thread(target=self.thread_make_pdf, args=(input_file, output_file), kwargs={"remove_annotations": remove_annotations, "progress": self})
                self.make_thread.start()

            self.exception_render_thread = threading.Thread(target=self.exception_render_daemon)
            self.exception_render_thread.start()

        except Exception as e:
            self.set_error(str(e))
            return
        
    def update_preview(self, event=None):
        self.preview_label.grid_forget()
        try:
            if self.preview_variable.get() in  {"No file selected", "Error while generating preview, invalid options may have been selected"}:
                self.preview_init()
            else:
                self.preview()
            self.preview_variable.set("")
        except Exception as e:
            self.preview_variable.set("Error while generating preview, invalid options may have been selected")
            self.preview_label.grid(row=2, column=2, columnspan=3, rowspan=11, pady=(30, 0))

            raise e
    
    def preview_init(self):
        if not self.valid_data(preview=True):
            raise Exception("Invalid data")
        
        self.preview_booklet = 0
        self.preview_pair = 0
        
        if self.radio_value.get() == "booklet":
            n_booklets = int(self.variable_entry.get())
            n_sheets = 7
        elif self.radio_value.get() == "sheet":
            n_sheets = int(self.variable_entry.get())
            n_booklets = "auto"
        else:
            n_booklets = "auto"
            n_sheets = 7

        input_filename = self.input_variable.get()
        with open(input_filename, 'rb') as input_file:
            reader = PyPDF2.PdfReader(input_file)
            self.distrib_booklets_pages = distribution_booklets_pages(len(reader.pages), n_booklets, n_sheets)
        
        self.preview_booklet = 0
        self.preview_pair = 0
        self.preview()

        
    def preview(self):
        if not self.valid_data(preview=True):
            raise Exception("Invalid data")
        
        if self.distrib_booklets_pages is None:
            raise Exception("No preview data")
        
        if self.preview_pdf is not None:
            self.preview_pdf.destroy()

        page_left = self.distrib_booklets_pages[self.preview_booklet][self.preview_pair][0]
        page_right = self.distrib_booklets_pages[self.preview_booklet][self.preview_pair][1]

        input_filename = self.input_variable.get()

        with open(input_filename, 'rb') as input_file:
            reader = PyPDF2.PdfReader(input_file)

            width, height = get_dimensions(reader.pages)

            new_page_1 = PyPDF2.PageObject.create_blank_page(
                        width=2*width,
                        height=height)
                    
            new_page_2 = PyPDF2.PageObject.create_blank_page(
                width=2*width,
                height=height)
            
            if page_left != -1:  # -1 means no page
                page = reader.pages[page_left]
                if page.mediabox.width != width or page.mediabox.height != height:
                    page = resize(page, width, height)
                new_page_1.merge_page(page)


            if page_right != -1:
                page = reader.pages[page_right]
                if page.mediabox.width != width or page.mediabox.height != height:
                    page = resize(page, width, height)
                new_page_2.merge_page(page)
                new_page_2.add_transformation(PyPDF2.Transformation().translate(width, 0))

            new_page_1.merge_page(new_page_2)
            new_page_1 = resize(new_page_1, 600, 424)

            writer = PyPDF2.PdfWriter()
            writer.add_page(new_page_1)

            if self.remove_annotations.get():
                writer.remove_links()

            with open(self.preview_file, 'wb') as output_file:
                writer.write(output_file)

            v1 = pdf.ShowPdf()
            
            self.preview_pdf = v1.pdf_view(self,
                                        pdf_location=self.preview_file,
                                        width=75, height=25)
            
            self.preview_pdf.grid(row=2, column=2, columnspan=3, rowspan=11, pady=(30, 0))
        
        self.booklet_value.set(self.preview_booklet + 1)
        self.booklet_sheet_value.set((self.preview_pair//2) + 1)
        self.page_value.set(self.get_current_page())
        self.sheet_value.set(self.get_current_sheet())
        current_pair = self.distrib_booklets_pages[self.preview_booklet][self.preview_pair]
        self.page_input_value.set(f"{current_pair[0] + 1}-{current_pair[1] + 1}")


    def next_preview(self):
        if self.preview_booklet is None or self.preview_pair is None:
            return
        
        current_booklet = self.distrib_booklets_pages[self.preview_booklet]
        if self.preview_pair == len(current_booklet) - 1:
            if self.preview_booklet == len(self.distrib_booklets_pages) - 1:
                self.preview_booklet = 0
            else:
                self.preview_booklet += 1
            self.preview_pair = 0
        else:
            self.preview_pair += 1
        self.update_preview()

    def previous_preview(self):
        if self.preview_booklet is None or self.preview_pair is None:
            return
        
        if self.preview_pair == 0:
            if self.preview_booklet == 0:
                self.preview_booklet = len(self.distrib_booklets_pages) - 1
            else:
                self.preview_booklet -= 1
            self.preview_pair = len(self.distrib_booklets_pages[self.preview_booklet]) - 1
        else:
            self.preview_pair -= 1
        self.update_preview()

    def get_current_sheet(self):
        return (sum(len(booklet) for booklet in self.distrib_booklets_pages[:self.preview_booklet]) + self.preview_pair + 2) // 2
    
    def get_current_page(self):
        return sum(len(booklet) for booklet in self.distrib_booklets_pages[:self.preview_booklet]) + self.preview_pair + 1
        
    def exception_render_daemon(self):
        while self.make_thread.is_alive():
                time.sleep(1)

        if len(self.errors) > 0:
            self.set_error(self.errors[0])
            self.errors = []
        else:
            self.progression_label.grid_forget()
            self.progress_bar.grid_forget()
            self.clear_error()
            messagebox.showinfo("Success", "PDF created successfully")     

    def thread_make_pdf(self, input_file, output_file, n_booklets="auto", remove_annotations=True, n_sheets=7, progress=None):
        try:
            make_pdf(input_file, output_file, n_booklets=n_booklets, remove_annotations=remove_annotations, n_sheets=n_sheets, progress=progress)
        except Exception as e:
            self.errors.append(str(e))
            return

    def change_entry(self):
        if self.radio_value.get() == "booklet":
            self.title_entry.grid(row=7, column=0, sticky="w", padx=(30, 0))
            self.number_entry.grid(row=7, column=1, sticky="e")
            self.variable_title_entry.set("Number of booklets : ")
        elif self.radio_value.get() == "sheet":
            self.title_entry.grid(row=7, column=0, sticky="w", padx=(30, 0))
            self.number_entry.grid(row=7, column=1, sticky="e")
            self.variable_title_entry.set("Number of sheets per booklet : ")
        else:
            self.title_entry.grid_forget()
            self.number_entry.grid_forget()

    def select_input_file(self):
        file_selected = filedialog.askopenfile(mode='r', initialdir=os.path.expanduser("~"), title="Select a file",
                                               filetypes=[("fichiers pdf", "*.pdf")])
        
        if file_selected:
            self.input_variable.set(file_selected.name)
            self.input_file.update()
            self.preview_booklet = 0
            self.preview_pair = 0
            self.update_preview()

    def select_output_file(self):
        file_selected = filedialog.asksaveasfile(mode='w', defaultextension=".pdf", initialdir=os.path.expanduser("~"),
                                                 filetypes=[("fichiers pdf", "*.pdf")], title="Select a file",
                                                 initialfile="output")
        
        if file_selected:
            self.output_variable.set(file_selected.name)
            self.output_file.update()


if __name__ == "__main__":
    app = Application()
    app.mainloop()

