from django import template

register = template.Library()

@register.filter
def latest_only(messages):
    """
    Consume the messages storage and return a one-item list
    containing only the latest message (or an empty list).
    This makes it safe to use in a {% for %} loop.
    """
    try:
        data = list(messages)  # consume the storage
    except TypeError:
        # If messages isn't iterable for some reason, fail safe
        return []
    return data[-1:]  # one-item list (latest) or empty list
