from ... import load, parser
from . import lang
def quantity_to_spoken(quantity):
    count = quantity.value
    unit_string = quantity.unit.to_spoken(count)
    return "{}{}{}".format(
        load.number_to_words(count), " " if len(unit_string) else "", unit_string
    )
def unit_to_spoken(unit, count=1):
    if unit.surfaces:
        unit_string = unit.surfaces[0]
        unit_string = load.pluralize(unit_string, count)
    else:
        denominator_dimensions = [i for i in unit.dimensions if i["power"] > 0]
        denominator_string = parser.name_from_dimensions(denominator_dimensions, lang)
        if denominator_string:
            plural_denominator_string = load.pluralize(denominator_string)
        else:
            plural_denominator_string = denominator_string
        unit_string = unit.name.replace(denominator_string, plural_denominator_string)
    return unit_string