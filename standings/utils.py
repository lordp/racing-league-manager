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
