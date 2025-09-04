from rest_framework.exceptions import ValidationError

def parse_int_param(params, name):
    """Gets a query param and checks if it's a valid number, returns None if not set"""
    value = params.get(name)
    if value is None:
        return None
    if not value.isdigit():
        raise ValidationError({name: 'Muss eine ganze Zahl sein.'})
    return int(value)