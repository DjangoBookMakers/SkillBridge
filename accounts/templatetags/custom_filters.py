from django import template

register = template.Library()


@register.filter
def add_class(value, arg):
    """폼 필드에 CSS 클래스를 추가하는 템플릿 필터"""
    css_classes = value.field.widget.attrs.get("class", "")
    if css_classes:
        css_classes = f"{css_classes} {arg}"
    else:
        css_classes = arg
    return value.as_widget(attrs={"class": css_classes})
