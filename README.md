# Pdf2Book

Pdf2Book is a tool that transforms PDF files into a format suitable for printing and folding into booklets. It works by rearranging the pages of a PDF file so that they can be printed on both sides of a sheet of paper and then folded in half to create a booklet.

## Installation
```bash
git clone
cd pdf2book
pip install -r requirements.txt
```

## Usage
To use the PDF Booklet Maker, start by loading the file you want to convert. Once the file is loaded, a preview of the converted booklet will be displayed, allowing you to see the result of the conversion.

You can then customize the conversion process using the following options:
+ Delete annotations: This option allows you to remove annotations from the original PDF file that may interfere with the booklet layout, causing them to be displayed incorrectly or in the wrong place.
+ Distribution:
    + Auto: The Auto option automatically calculates the number of booklets to create an average of 7 sheets per booklet based on the number of pages in the PDF file.
    + Specify number of booklets: This option allows you to specify the number of booklets you want to print, and then the program calculates the number of sheets per booklet required to achieve this.
    + Specify number of sheets per booklet: This option lets you set the number of sheets you want to print per booklet, and then calculates the number of booklets required to print the entire PDF file.

If you make any changes to these options, you can update the preview by clicking on the "Update preview" button or by previewing another page.

Once you're satisfied with the preview, you can render the PDF by clicking on the "Render PDF" button. The rendering process will display a progress bar, indicating the estimated time remaining for the PDF rendering. During the rendering process, you can continue to change the conversion options or preview other files since the rendering and preview processes are independent.

Here is an image of the application :

<img src="./img/app.png" alt="app" width="500"/>

After the PDF has been generated, utilize duplex printing and then follow the given instructions to arrange the sheets:
<img src="./img/steps.png" alt="sheets" width="500"/>

It's important to keep in mind that in case the original PDF pages are of varying sizes, a few of them might get cropped or not show correctly. The software endeavors to adjust the size based on the most frequently occurring page size in the input PDF file.

<div align="right" style="display: flex">
    <img src="https://visitor-badge.glitch.me/badge?page_id=Th3o-D/pdf2book&left_color=gray&right_color=blue" height="20"/>
    <a href="https://github.com/Th3o-D" alt="https://github.com/Th3o-D"><img height="20" style="border-radius: 5px" src="https://img.shields.io/static/v1?style=for-the-badge&label=CREE%20PAR&message=Th3o-D&color=1182c2"></a>
    <a href="LICENSE" alt="licence"><img style="border-radius: 5px" height="20" src="https://img.shields.io/static/v1?style=for-the-badge&label=LICENSE&message=GNU+GPL+V3&color=1182c2"></a>
</div>
