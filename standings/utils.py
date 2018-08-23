from inflect import engine
from collections import Iterable


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


def apply_positions(table, key='points', use_position=False):
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

            row['position'] = '-' if same_position and not use_position else position

        previous_item = row

    return table


def sort_counter(results, ordinal=True, convert_int=True):
    p = engine()
    if convert_int:
        results = {int(k): int(v) for k, v in results.items()}
    order = sorted(results)
    if ordinal:
        result = ["{} x {}".format(p.ordinal(place), results[place]) for place in order]
    else:
        result = ["{} x {}".format(place, results[place]) for place in order]

    return result


def flatten(l):
    for el in l:
        if isinstance(el, Iterable) and not isinstance(el, (str, bytes)):
            yield from flatten(el)
        else:
            yield el


def expire_view_cache(path, meta, key_prefix=None):
    """
    This function allows you to invalidate any item from the per-view cache.
    It probably won't work with things cached using the per-site cache
    middleware (because that takes account of the Vary: Cookie header).
    This assumes you're using the Sites framework.
    Arguments:
        * path: The URL of the view to invalidate, like `/blog/posts/1234/`.
        * meta: Meta details of the request
        * key_prefix: The same as that used for the cache_page()
          function/decorator (if any).
    """
    from django.conf import settings
    from django.core.cache import cache
    from django.http import HttpRequest
    from django.utils.cache import get_cache_key

    # Create a fake request object
    request = HttpRequest()
    request.method = 'GET'
    request.META = meta
    request.path = path

    request.META['QUERY_STRING'] = ''

    if settings.USE_I18N:
        request.LANGUAGE_CODE = settings.LANGUAGE_CODE

    # If this key is in the cache, delete it:
    try:
        cache_key = get_cache_key(request, key_prefix=key_prefix)
        if cache_key:
            if cache_key in cache:
                cache.delete(cache_key)
                return (True, 'Successfully invalidated')
            else:
                return (False, 'Cache_key does not exist in cache')
        else:
            raise ValueError('Failed to create cache_key')
    except (ValueError, Exception) as e:
        return (False, e)


def calculate_average(values, key):
    try:
        value = sum(values[key]) / len(values[key])
    except (ZeroDivisionError, KeyError):
        value = 0

    return value
