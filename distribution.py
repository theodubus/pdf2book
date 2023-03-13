def distribution_pages(begin, end):
    """
    Defines for a given booklet which pages go in which sheet, and in which order.
    """

    if type(begin) is not int or type(end) is not int:
        raise TypeError("begin and end must be integers")
    if begin > end:
        raise ValueError("begin must be less than or equal to end")
    
    number_of_pages = end - begin + 1


    # Because of duplex printing, Pages goes by 4 and not 2
    # therefore if you have 5 pages you need 3 blank pages to make it 8 pages, 2 for 6, 1 for 7, 0 for 8 and so on
    blank_pages = (4 - (number_of_pages % 4)) % 4 
    i = begin
    j = end
    j_first = True

    distrib = []
    while i <= j:
        if j_first:
            if blank_pages > 0:
                distrib.append((-1, i))
            else:
                distrib.append((j, i))
            j_first = False
        else:
            if blank_pages > 0:
                distrib.append((i, -1))
            else:
                distrib.append((i, j))
            j_first = True
        i += 1
        if blank_pages > 0:
            blank_pages -= 1
        else:
            j -= 1

    return distrib


def distribution_booklets(n_pages, n_booklets="auto", n_sheets=7):
    """
    Defines which pages go in which booklet.
    """

    if type(n_pages) is not int or n_pages <= 0:
        raise TypeError("number of pages must be integer greater than 0")

    if n_booklets == "auto":
        n_booklets = n_pages // (4 * n_sheets)  # average of n_sheets sheets of 4 pages each per booklet

        if n_booklets == 0:
            raise ValueError("Too many sheets")

        if n_pages % (4 * n_sheets) != 0:
            n_booklets += 1

    if type(n_booklets) is not int or n_booklets <= 0:
        raise TypeError("number of booklets must be integer greater than 0")

    n_sheets = n_pages // 4  # 4 pages per sheet, duplex printing
    if n_pages % 4 != 0:
        n_sheets += 1

    if n_sheets < n_booklets:
        raise ValueError("number of booklets must be less than or equal to the number of pages / 4")
    
    sheets_per_booklet = n_sheets // n_booklets
    sheets_left = n_sheets % n_booklets

    distrib = []
    for _ in range(n_booklets):
        if sheets_left > 0:
            distrib.append(sheets_per_booklet + 1)
            sheets_left -= 1
        else:
            distrib.append(sheets_per_booklet)

    distrib_begin_end = []
    begin = 0
    for n_sheets in distrib:
        end = min(begin + n_sheets * 4 - 1, n_pages - 1)
        distrib_begin_end.append((begin, end))
        begin = end + 1

    return distrib_begin_end


def distribution_booklets_pages(n_pages, n_booklets="auto", n_sheets=7):
    """
    Defines which pages go in which booklet, and in which order.
    """

    distrib_booklets = distribution_booklets(n_pages, n_booklets, n_sheets)
    distrib_booklets_pages = []
    for begin, end in distrib_booklets:
        distrib_booklets_pages.append(distribution_pages(begin, end))

    return distrib_booklets_pages