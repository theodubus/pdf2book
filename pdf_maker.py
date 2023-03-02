import PyPDF2
from distribution import distribution_booklets_pages
import os

def add_empty_pages(input_filename, n_pages):
    """
    Adds a certain number of empty pages at the beggining
    and the end of the PDF file.
    """
    with open(input_filename, 'rb') as input_file:
        reader = PyPDF2.PdfReader(input_file)

        writer = PyPDF2.PdfWriter()

        output_filename = f"{os.path.dirname(os.path.realpath(__file__))}/temp/empty.pdf"
        with open(output_filename, 'wb') as output_file:
            width, height = get_dimensions(reader.pages)

            for _ in range(n_pages):
                page = PyPDF2.PageObject.create_blank_page(
                    width=width,
                    height=height)
                writer.add_page(page)

            for page in reader.pages:
                writer.add_page(page)

            for _ in range(n_pages):
                page = PyPDF2.PageObject.create_blank_page(
                    width=width,
                    height=height)
                writer.add_page(page)
            
            writer.write(output_file)

    return output_filename



def make_pdf(input_filename, output_filename, n_booklets="auto", remove_annotations=True, n_sheets=7, progress=None, empty_pages=0):

    if input_filename == output_filename:
        raise ValueError("The input and output file cannot be the same")
    
    if empty_pages > 0:
        input_filename = add_empty_pages(input_filename, empty_pages)

    # Open the input PDF file in read-binary mode
    with open(input_filename, 'rb') as input_file:
        # Create a PDF reader object
        reader = PyPDF2.PdfReader(input_file)

        # Create a PDF writer object
        writer = PyPDF2.PdfWriter()

        # Get the distribution of pages in booklets
        distrib_booklets_pages = distribution_booklets_pages(len(reader.pages), n_booklets, n_sheets)

        # Create a new PDF file in write-binary mode
        with open(output_filename, 'wb') as output_file:

            if progress:
                nb_pairs = [len(booklet) for booklet in distrib_booklets_pages]
                nb_pairs = sum(nb_pairs)
                progress.progress_init(nb_pairs)
            
            width, height = get_dimensions(reader.pages)

            # Loop through each booklet
            for distrib_booklet_pages in distrib_booklets_pages:

                # Loop through each pair of pages
                for pair_pages in distrib_booklet_pages:

                    if progress:
                        progress.update_progress()

                    # Create new blank pages
                    new_page_1 = PyPDF2.PageObject.create_blank_page(
                        width=2*width,
                        height=height)
                    
                    new_page_2 = PyPDF2.PageObject.create_blank_page(
                        width=2*width,
                        height=height)


                    # Merge the two pages into the new page

                    # Merge the new page (twice as big as A4 and horizontal) with a page letting the right half empty
                    if pair_pages[0] != -1:  # -1 means no page
                        page = reader.pages[pair_pages[0]]
                        if page.mediabox.width != width or page.mediabox.height != height:
                            page = resize(page, width, height)
                        new_page_1.merge_page(page)

                    # Do the same for the second page but translate it to the right to let the left half empty
                    if pair_pages[1] != -1:
                        page = reader.pages[pair_pages[1]]
                        if page.mediabox.width != width or page.mediabox.height != height:
                            page = resize(page, width, height)
                        new_page_2.merge_page(page)
                        new_page_2.add_transformation(PyPDF2.Transformation().translate(width, 0))
                
                    # Merge the two pages into the new page
                    new_page_1.merge_page(new_page_2)

                    # Scale the new page to half the size to fit on A4
                    new_page_1.scale(0.5, 0.5)

                    # Add the new page to the output PDF file
                    writer.add_page(new_page_1)

            # Remove annotations
            if remove_annotations:
                writer.remove_links()

            # Write the output PDF file
            writer.write(output_file)


def resize(page, new_width, new_height):

    width = page.mediabox.width
    height = page.mediabox.height

    ratio_width = float(round(new_width / width, 3))
    ratio_height = float(round(new_height / height, 3))

    page.scale(ratio_width, ratio_height)

    return page


def get_dimensions(reader_pages):

    dimensions = {"width": dict(), "height": dict()}
    for page in reader_pages:
        width = page.mediabox.width
        height = page.mediabox.height
        if width in dimensions["width"]:
            dimensions["width"][width] += 1
        else:
            dimensions["width"][width] = 1
        if height in dimensions["height"]:
            dimensions["height"][height] += 1
        else:
            dimensions["height"][height] = 1
    
    most_common_width = max(dimensions["width"], key=dimensions["width"].get)
    most_common_height = max(dimensions["height"], key=dimensions["height"].get)

    return most_common_width, most_common_height