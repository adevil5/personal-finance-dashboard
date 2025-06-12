"""
HTMX template tags for reusable patterns.
"""

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def htmx_get(url, target=None, trigger="click", swap="innerHTML", **kwargs):
    """
    Generate HTMX GET request attributes.

    Usage:
        {% htmx_get "/api/data/" "#target-id" "click" "innerHTML" %}
    """
    attrs = [f'hx-get="{url}"']

    if target:
        attrs.append(f'hx-target="{target}"')

    if trigger != "click":
        attrs.append(f'hx-trigger="{trigger}"')

    if swap != "innerHTML":
        attrs.append(f'hx-swap="{swap}"')

    # Add any additional HTMX attributes
    for key, value in kwargs.items():
        if key.startswith("hx_"):
            attr_name = key.replace("_", "-")
            attrs.append(f'{attr_name}="{value}"')

    return mark_safe(" ".join(attrs))


@register.simple_tag
def htmx_post(url, target=None, trigger="submit", swap="innerHTML", **kwargs):
    """
    Generate HTMX POST request attributes.

    Usage:
        {% htmx_post "/api/create/" "#result" "submit" "innerHTML" %}
    """
    attrs = [f'hx-post="{url}"']

    if target:
        attrs.append(f'hx-target="{target}"')

    if trigger != "submit":
        attrs.append(f'hx-trigger="{trigger}"')

    if swap != "innerHTML":
        attrs.append(f'hx-swap="{swap}"')

    # Add any additional HTMX attributes
    for key, value in kwargs.items():
        if key.startswith("hx_"):
            attr_name = key.replace("_", "-")
            attrs.append(f'{attr_name}="{value}"')

    return mark_safe(" ".join(attrs))


@register.simple_tag
def htmx_delete(url, target=None, confirm=None, swap="delete", **kwargs):
    """
    Generate HTMX DELETE request attributes with confirmation.

    Usage:
        {% htmx_delete "/api/delete/1/" "#item-1" "Are you sure?" %}
    """
    attrs = [f'hx-delete="{url}"']

    if target:
        attrs.append(f'hx-target="{target}"')

    if confirm:
        attrs.append(f'hx-confirm="{confirm}"')

    if swap != "delete":
        attrs.append(f'hx-swap="{swap}"')

    # Add any additional HTMX attributes
    for key, value in kwargs.items():
        if key.startswith("hx_"):
            attr_name = key.replace("_", "-")
            attrs.append(f'{attr_name}="{value}"')

    return mark_safe(" ".join(attrs))


@register.simple_tag
def htmx_form(url, target=None, swap="innerHTML", **kwargs):
    """
    Generate HTMX form attributes with CSRF protection.

    Usage:
        {% htmx_form "/api/update/" "#form-container" %}
    """
    attrs = [f'hx-post="{url}"', 'hx-headers=\'{"X-CSRFToken": "{{ csrf_token }}"}\'']

    if target:
        attrs.append(f'hx-target="{target}"')

    if swap != "innerHTML":
        attrs.append(f'hx-swap="{swap}"')

    # Add any additional HTMX attributes
    for key, value in kwargs.items():
        if key.startswith("hx_"):
            attr_name = key.replace("_", "-")
            attrs.append(f'{attr_name}="{value}"')

    return mark_safe(" ".join(attrs))


@register.inclusion_tag("htmx/loading_indicator.html")
def htmx_loading(target_id, message="Loading..."):
    """
    Include a loading indicator for HTMX requests.

    Usage:
        {% htmx_loading "form-container" "Saving..." %}
    """
    return {
        "target_id": target_id,
        "message": message,
    }


@register.inclusion_tag("htmx/error_container.html")
def htmx_error_container(target_id):
    """
    Include an error container for HTMX error handling.

    Usage:
        {% htmx_error_container "form-errors" %}
    """
    return {
        "target_id": target_id,
    }


@register.filter
def htmx_trigger_from_element(element_id):
    """
    Generate HTMX trigger from specific element.

    Usage:
        {{ "button-id"|htmx_trigger_from_element }}
    """
    return mark_safe(f"from:#{element_id}")


@register.simple_tag
def htmx_boost(enabled=True):
    """
    Enable/disable HTMX boost for progressive enhancement.

    Usage:
        {% htmx_boost True %}
    """
    if enabled:
        return mark_safe('hx-boost="true"')
    return ""


@register.simple_tag
def htmx_push_url(enabled=True):
    """
    Enable URL pushing for HTMX requests.

    Usage:
        {% htmx_push_url True %}
    """
    if enabled:
        return mark_safe('hx-push-url="true"')
    return ""
