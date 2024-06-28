from . import load
from . import no_classifier as no_clf
def disambiguate_unit(unit_surface, text, lang="en_US", classifier_path=None):
    units_ = load.units(lang)
    base = (
        units_.symbols[unit_surface]
        or units_.surfaces[unit_surface]
        or units_.surfaces_lower[unit_surface.lower()]
        or units_.symbols_lower[unit_surface.lower()]
    )
    if len(base) > 1:
        base = no_clf.disambiguate_no_classifier(base, text, lang)
    elif len(base) == 1:
        base = next(iter(base))
    if base:
        base = base.name
    else:
        base = "unk"
    return base
def disambiguate_entity(key, text, lang="en_US", classifier_path=None):
    entities_ = load.entities(lang)
    try: 
        derived = entities_.derived[key]
        if len(derived) > 1:
            ent = no_clf.disambiguate_no_classifier(derived, text, lang)
            ent = entities_.names[ent]
        elif len(derived) == 1:
            ent = next(iter(derived))
        else:
            ent = None
    except (KeyError, StopIteration):
        ent = None
    return ent