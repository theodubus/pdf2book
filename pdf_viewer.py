# this file is a modified and fixed version of the "tkPDFViewer" module by Roshan Paswan
# See more about this module at https://pypi.org/project/tkPDFViewer/

try:
    from tkinter import *
    import fitz
    from tkinter.ttk import Progressbar
    from threading import Thread
    import math
except Exception as e:
    print(f"This error occured while importing neccesary modules or library {e}")

class ShowPdf():

    img_object_li = [None]

    def pdf_view(self, master, width=1200, height=600, pdf_location="", bar=True, load="after"):

        self.frame = Frame(master,width= width,height= height,bg="white")

        percentage_view = 0
        percentage_load = StringVar()

        if bar==True and load=="after":
            self.display_msg = Label(textvariable=percentage_load)
            # self.display_msg.grid(pady=10, padx=10, row=0, column=0)

            loading = Progressbar(self.frame,orient= HORIZONTAL,length=100,mode='determinate')
            loading.pack(side = TOP,fill=X)

        self.text = Text(self.frame, width= width, height= height)

        self.text.pack(side="left")

        def add_img():
            precentage_dicide = 0
            open_pdf = fitz.open(pdf_location)

            page = open_pdf[0]
            pix = page.get_pixmap()
            pix1 = fitz.Pixmap(pix,0) if pix.alpha else pix
            img = pix1.tobytes("ppm")
            timg = PhotoImage(data = img)
            self.img_object_li[0] = timg
            if bar==True and load=="after":
                precentage_dicide = precentage_dicide + 1
                percentage_view = (float(precentage_dicide)/float(len(open_pdf))*float(100))
                loading['value'] = percentage_view
                percentage_load.set(f"Please wait!, your pdf is loading {int(math.floor(percentage_view))}%")

            if bar==True and load=="after":
                loading.pack_forget()
                self.display_msg.pack_forget()

            for i in self.img_object_li:
                self.text.image_create(END,image=i)
                self.text.insert(END,"\n\n")
            self.text.config(state="disabled")

        def start_pack():
            t1 = Thread(target=add_img)
            t1.start()

        if load=="after":
            master.after(250,start_pack)
        else:
            start_pack()

        return self.frame