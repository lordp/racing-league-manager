def format_time(seconds):
    m, s = divmod(seconds, 60)
    if m > 60:
        h, m = divmod(m, 60)
        return '{h:0.0f}h{m:02.0f}m{s:06.3f}'.format(h=h, m=m, s=s)
    elif m > 0:
        return '{m:0.0f}m{s:06.3f}'.format(m=m, s=s)
    else:
        return '{s:0.3f}'.format(s=s)


def format_float(num):
    return format(num, '.15g')


def apply_positions(table, key='points'):
    position = 1
    position_diff = 1

    previous_item = None

    for index, row in enumerate(table):
        if index == 0:
            row['position'] = 1
        else:
            if row[key] == previous_item[key]:
                position_diff += 1
                same_position = True
            else:
                position += position_diff
                position_diff = 1
                same_position = False

            row['position'] = '-' if same_position else position

        previous_item = row

    return table
