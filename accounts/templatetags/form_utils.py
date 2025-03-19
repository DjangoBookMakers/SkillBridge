from django import template

register = template.Library()


@register.filter(name="add_class")
def add_class(field, css_class):
    """폼 필드에 CSS 클래스를 추가하는 필터"""
    return field.as_widget(attrs={"class": css_class})


@register.filter(name="add_attr")
def add_attr(field, attr_value):
    """폼 필드에 HTML 속성을 추가하는 필터

    사용 예: {{ form.name|add_attr:'placeholder:이름을 입력하세요' }}
    """
    attr_name, attr_value = attr_value.split(":", 1)
    return field.as_widget(attrs={attr_name: attr_value})


@register.filter(name="with_attrs")
def with_attrs(field, attrs_str):
    """폼 필드에 여러 속성을 추가하는 필터

    사용 예: {{ form.name|with_attrs:'class:input-field,placeholder:이름을 입력하세요' }}
    """
    attrs = {}
    attr_pairs = attrs_str.split(",")

    for pair in attr_pairs:
        if ":" in pair:
            attr_name, attr_value = pair.split(":", 1)
            attrs[attr_name.strip()] = attr_value.strip()

    return field.as_widget(attrs=attrs)
