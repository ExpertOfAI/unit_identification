import logging
import re
from ... import classes as cls
from ... import load, parser
from ... import regex as reg
from . import lang
from .load import COMMON_WORDS
_LOGGER = logging.getLogger(__name__)
def clean_surface(surface, span):
    surface = surface.replace("-", " ")
    no_start = ["and", " "]
    no_end = [" "] + [" {}".format(misc) for misc in reg.miscnum(lang)]
    found = True
    while found:
        found = False
        for word in no_start:
            if surface.lower().startswith(word):
                surface = surface[len(word) :]
                span = (span[0] + len(word), span[1])
                found = True
        for word in no_end:
            if surface.lower().endswith(word):
                surface = surface[: -len(word)]
                span = (span[0], span[1] - len(word))
                found = True
    if not surface:
        return None, None
    split = surface.lower().split()
    if (
        split[0] in reg.miscnum(lang)
        and len(split) > 1
        and split[1] in reg.units(lang) + reg.tens(lang)
    ):
        span = (span[0] + len(surface.split()[0]) + 1, span[1])
        surface = " ".join(surface.split()[1:])
    return surface, span
def split_spellout_sequence(text, span):
    negatives = reg.negatives(lang)
    units = reg.units(lang)
    tens = reg.tens(lang)
    scales = reg.scales(lang)
    start_offset = span[0]
    prev_word_rank = 0
    prev_scale = 0
    last_word_end = last_span_start = 0
    prev_word = ""
    for word_span in re.finditer(r"\w+", text):
        word = word_span.group(0)
        rank = (
            1
            if word in units
            else 2
            if word in tens
            else 3 + scales.index(word)
            if word in scales
            else 0
        )
        should_split = False
        if word in negatives:
            should_split = True
        elif prev_word_rank == 1 and rank in [1, 2]:
            should_split = True
        elif prev_word_rank == 2 and rank == 2:
            should_split = True
        elif rank >= 3 and rank == prev_scale:
            should_split = True
            prev_scale = rank
        if should_split and last_word_end > 0:
            adjust = 0
            if prev_word.lower() in [
                "and",
                "&",
            ]:
                adjust = -(len(prev_word) + 1)
            yield (
                text[last_span_start : last_word_end + adjust],
                (last_span_start + start_offset, last_word_end + start_offset + adjust),
            )
            last_span_start = word_span.span()[0]
        if rank >= 3:
            prev_scale = rank
        if word.lower() not in ["and", "&"]:
            prev_word_rank = rank
        prev_word = word
        last_word_end = word_span.span()[1]
    yield (
        text[last_span_start:],
        (last_span_start + start_offset, len(text) + start_offset),
    )
def extract_spellout_values(text):
    values = []
    number_candidates = []
    for range in reg.text_pattern_reg(lang).finditer(text):
        for seq, span in split_spellout_sequence(range.group(0), range.span()):
            number_candidates.append((seq, span))
    for seq, span in number_candidates:
        if (
            len(
                set(parser.words_before_span(text, span, 3)).intersection(
                    {"several", "couple", "some"}
                )
            )
            > 0
        ):
            continue
        try:
            is_negative = False
            surface, span = clean_surface(seq, span)
            if not surface:
                continue
            curr = result = 0.0
            for word in surface.lower().split():
                try:
                    scale, increment = (
                        1,
                        float(
                            re.sub(
                                r"(-$|[%s])" % reg.grouping_operators_regex(lang),
                                "",
                                word,
                            )
                        ),
                    )
                except ValueError:
                    match = re.search(reg.numberwords_regex(), word)
                    scale, increment = reg.numberwords(lang)[match.group(0)]
                if scale < 0:
                    is_negative = True
                    continue
                if (
                    scale > 0
                    and increment == 0
                    and curr == 0.0
                    and result == 0.0
                    and word != "zero"
                ):
                    increment = scale
                    scale = 0.0
                if scale > result > 0:
                    curr = curr + result
                    result = 0.0
                curr = curr * scale + increment
                if scale > 100 or word == "and":
                    result += curr
                    curr = 0.0
            value = result + curr
            if is_negative:
                value = -value
            values.append(
                {
                    "old_surface": surface,
                    "old_span": span,
                    "new_surface": str(value),
                }
            )
        except (KeyError, AttributeError):
            pass
    return sorted(values, key=lambda x: x["old_span"][0])
def parse_unit(_, unit, slash):
    surface = unit.replace(".", "")
    power = re.findall(r"-?[0-9%s]+" % reg.unicode_superscript_regex(), surface)
    power_written = re.findall(r"\b(%s)\b" % "|".join(reg.powers(lang)), surface)
    if power:
        power = [
            reg.unicode_superscript()[i] if i in reg.unicode_superscript() else i
            for i in power
        ]
        power = "".join(power)
        new_power = -1 * int(power) if slash else int(power)
        surface = re.sub(r"\^?-?[0-9%s]+" % reg.unicode_superscript(), "", surface)
    elif power_written:
        exponent = reg.powers(lang)[power_written[0]]
        new_power = -exponent if slash else exponent
        surface = re.sub(r"\b%s\b" % power_written[0], "", surface).strip()
    else:
        new_power = -1 if slash else 1
    return surface, new_power
def build_quantity(
    orig_text, text, item, values, unit, surface, span, uncert, classifier_path=None
):
    units_ = load.units(lang)
    dimension_change = True
    _absolute = "absolute "
    if (
        unit.name == "dimensionless"
        and _absolute == orig_text[span[0] - len(_absolute) : span[0]]
    ):
        unit = units_.names["kelvin"]
        unit.original_dimensions = unit.dimensions
        surface = _absolute + surface
        span = (span[0] - len(_absolute), span[1])
        dimension_change = True
    if unit.entity.dimensions:
        if (
            len(unit.entity.dimensions) > 1
            and unit.entity.dimensions[0]["base"] == "currency"
            and unit.original_dimensions[1]["surface"] in reg.suffixes(lang).keys()
        ):
            suffix = unit.original_dimensions[1]["surface"]
            if re.search(r"\d{}\b".format(suffix), text):
                values = [value * reg.suffixes(lang)[suffix] for value in values]
                unit.original_dimensions = [
                    unit.original_dimensions[0]
                ] + unit.original_dimensions[2:]
                dimension_change = True
        elif unit.original_dimensions[0]["surface"] in reg.suffixes(lang).keys():
            symbolic = all(
                dim["surface"] in units_.names[dim["base"]].symbols
                for dim in unit.original_dimensions[1:]
            )
            if not symbolic:
                suffix = unit.original_dimensions[0]["surface"]
                values = [value * reg.suffixes(lang)[suffix] for value in values]
                unit.original_dimensions = unit.original_dimensions[1:]
                dimension_change = True
    elif re.match(r"[1-2]\d\d0s", surface):
        unit.original_dimensions = []
        dimension_change = True
        surface = surface[:-1]
        span = (span[0], span[1] - 1)
        _LOGGER.debug('\tCorrect for "1990s" pattern')
    if (
        len(unit.dimensions) == 1
        and ("pm" == item.group("unit1") or "am" == item.group("unit1"))
        and unit.entity.name == "length"
        and re.fullmatch(r"\d(\.\d\d)?", item.group("value"))
    ):
        _LOGGER.debug("\tCorrect for am/pm time pattern")
        return
    try:
        if (
            len(values) == 1
            and unit.entity.name == "currency"
            and span[0] > 0
            and orig_text[span[0] - 1] == "("
            and orig_text[span[1]] == ")"
            and values[0] >= 0
        ):
            span = (span[0] - 1, span[1] + 1)
            surface = "({})".format(surface)
            values[0] = -values[0]
    except IndexError:
        pass
    pruned_common_word = unit.original_dimensions
    while pruned_common_word:
        pruned_common_word = False
        if (
            unit.original_dimensions
            and unit.original_dimensions[-1]["base"] == "inch"
            and re.search(r" in$", surface)
            and "/" not in surface
            and not re.search(
                r" in(\.|,|\?|!|$)",
                orig_text[span[0] : min(len(orig_text), span[1] + 1)],
            )
        ):
            unit.original_dimensions = unit.original_dimensions[:-1]
            dimension_change = True
            pruned_common_word = True
            surface = surface[:-3]
            span = (span[0], span[1] - 3)
            _LOGGER.debug("\tCorrect for 'in' pattern")
            continue
        if (
            unit.original_dimensions
            and unit.original_dimensions[-1]["base"] == "megayear"
            and re.search(r" my$", surface)
            and "/" not in surface
            and not re.search(
                r" my(\.|,|\?|!|$)",
                orig_text[span[0] : min(len(orig_text), span[1] + 1)],
            )
        ):
            unit.original_dimensions = unit.original_dimensions[:-1]
            dimension_change = True
            pruned_common_word = True
            surface = surface[:-3]
            span = (span[0], span[1] - 3)
            _LOGGER.debug("\tCorrect for 'my' pattern")
            continue
        candidates = [u["power"] == 1 for u in unit.original_dimensions]
        for start in range(0, len(unit.original_dimensions)):
            for end in reversed(range(start + 2, len(unit.original_dimensions) + 1)):
                if not all(candidates[start:end]):
                    continue
                combination = "".join(
                    u.get("surface", "") for u in unit.original_dimensions[start:end]
                )
                if len(combination) < 1:
                    continue
                if combination not in surface:
                    continue
                if combination.lower() not in COMMON_WORDS[len(combination)]:
                    continue
                match = re.search(r"[-\s]%s\b" % combination, surface)
                if not match:
                    continue
                span = (span[0], span[0] + match.start())
                surface = surface[: match.start()]
                unit.original_dimensions = unit.original_dimensions[:start]
                dimension_change = True
                pruned_common_word = True
                _LOGGER.debug(
                    "\tDetected common word '{}' and removed it".format(combination)
                )
                continue
    match = parser.is_quote_artifact(text, item.span())
    if match:
        surface = surface[:-1]
        span = (span[0], span[1] - 1)
        if unit.original_dimensions and (
            unit.original_dimensions[-1]["surface"] == '"'
        ):
            unit.original_dimensions = unit.original_dimensions[:-1]
            dimension_change = True
        _LOGGER.debug("\tCorrect for quotes")
    if (
        re.search(r" time$", surface)
        and unit.original_dimensions
        and len(unit.original_dimensions) > 1
        and unit.original_dimensions[-1]["base"] == "count"
    ):
        unit.original_dimensions = unit.original_dimensions[:-1]
        dimension_change = True
        surface = surface[:-5]
        span = (span[0], span[1] - 5)
        _LOGGER.debug('\tCorrect for "time"')
    if dimension_change:
        if unit.original_dimensions:
            unit = parser.get_unit_from_dimensions(
                unit.original_dimensions, orig_text, lang, classifier_path
            )
        else:
            unit = units_.names["dimensionless"]
    if (
        surface.lower() in ["a", "an", "one"]
        or re.search(r"1st|2nd|3rd|[04-9]th", surface)
        or re.search(r"\d+[A-Z]+\d+", surface)
        or re.search(r"\ba second\b", surface, re.IGNORECASE)
    ):
        _LOGGER.debug('\tMeaningless quantity ("%s"), discard', surface)
        return
    objs = []
    for value in values:
        obj = cls.Quantity(
            value=value,
            unit=unit,
            surface=surface,
            span=span,
            uncertainty=uncert,
            lang=lang,
        )
        objs.append(obj)
    return objs
def clean_text(text):
    text = re.sub(r"(?<=\w)(\'s\b|s\')(?!\w)", "  ", text)
    return text
def name_from_dimensions(dimensions):
    name = ""
    for unit in dimensions:
        if unit["power"] < 0:
            name += "per "
        power = abs(unit["power"])
        if power == 1:
            name += unit["base"]
        elif power == 2:
            name += "square " + unit["base"]
        elif power == 3:
            name += "cubic " + unit["base"]
        elif power > 3:
            name += unit["base"] + " to the %g" % power
        name += " "
    name = name.strip()
    return name
def is_ranged(quantity1, quantity2, context):
    connective = context[quantity1.span[1] : quantity2.span[0]].strip().lower()
    before = set(parser.words_before_span(context, quantity1.span, 3))
    if connective == "to":
        return (quantity1.span[0], quantity2.span[1])
    elif connective == "and" and "between" in before:
        start = context.rfind("between", 0, quantity1.span[0])
        return (start, quantity2.span[1])
    else:
        return None
def is_coordinated(quantity1, quantity2, context) -> bool:
    connective = context[quantity1.span[1] : quantity2.span[0]].strip().lower()
    if connective in ["and", "or", "but"]:
        return (quantity1.span[0], quantity2.span[1])
    return None