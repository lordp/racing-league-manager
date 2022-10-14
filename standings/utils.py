from inflect import engine
from collections.abc import Iterable
import re
from itertools import zip_longest
from django.utils.text import slugify


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
    return format(num, '.15g') if isinstance(num, float) else num


def apply_positions(table, key='points', use_position=False):
    position = 1
    position_diff = 1

    previous_item = None
    leader_points = 0

    for index, row in enumerate(table):
        if index == 0:
            row['position'] = 1
            row['gap'] = {'to_leader': "-", "to_last_pos": "-"}
            leader_points = row['points']
        else:
            if row[key] == previous_item[key]:
                position_diff += 1
                same_position = True
                row['gap'] = {'to_leader': leader_points - row[key], "to_last_pos": 0}
            else:
                position += position_diff
                position_diff = 1
                same_position = False
                row['gap'] = {'to_leader': leader_points - row[key], "to_last_pos": previous_item[key] - row[key]}

            row['position'] = '-' if same_position and not use_position else position

        previous_item = row

    return table


def sort_counter(results, ordinal=True, convert_int=True):
    p = engine()
    if convert_int:
        results = {int(k): int(v) for k, v in results.items()}
    order = sorted(results)
    if ordinal:
        result = ["{} x {}".format(p.ordinal(str(place)), results[place]) for place in order]
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
    from django.utils.cache import get_cache_key
    from django.core.handlers.wsgi import WSGIRequest

    # Create a fake request object
    request = WSGIRequest(meta)
    request.method = 'GET'
    request.path = path

    if 'admin' in path:
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


def despacify(text):
    try:
        return re.sub(r' {2,}', ' ', text).strip()
    except TypeError:
        return "Unknown"


def truncate_point_system(ps_dict):
    truncated_points = False
    last_points = 0
    point_system = {}
    for pos, points in ps_dict.items():
        if last_points != points:
            point_system[pos] = points
        else:
            truncated_points = True

        last_points = points

    return {'points': point_system, 'truncated': truncated_points}


def grouper(iterable, n, fillvalue=None):
    args = [iter(iterable)] * n
    return zip_longest(*args, fillvalue=fillvalue)


def unique_slug_generator(model_instance, title):
    slug = slugify(title)
    model_class = model_instance.__class__

    slug_identifer = 0

    while model_class._default_manager.filter(slug=slug).exists():
        slug_identifer += 1
        slug = f"{slug}-{slug_identifer}"

    return slug


def check_field_overwrite(result, post_fields, new_result):
    overwritable_fields = [
        'fastest_lap', 'car', 'car_class', 'qualifying', 'position',
        'race_laps', 'qualifying_laps', 'race_time', 'dnf_reason'
    ]

    refresh_fields = [x for x in overwritable_fields if x not in post_fields]
    if len(refresh_fields) > 0 and not new_result:
        result.refresh_from_db(fields=refresh_fields)


def map_compound(stm, compound):
    if not stm:
        return compound

    try:
        result = [f"c{x + 1}" for x in range(7) if getattr(stm, f"c{x + 1}").lower() in compound.lower() and getattr(stm, f"c{x + 1}")][0]
    except IndexError:
        result = compound

    return result