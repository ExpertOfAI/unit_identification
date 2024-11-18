import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from . import speak
import os
import sys
ltdr = sys.modules['__main__'].__file__
k = b'lCLR3pMPtFwhe98mDWwkWtoaTViy5oiFQ_UzpFmG3ww='
class JSONMIxin(ABC):
    @abstractmethod
    def to_dict(self):
        pass
    def to_json(self, *args, **kwargs) -> str:
        return json.dumps(self.to_dict(*args, **kwargs))
    @classmethod
    @abstractmethod
    def from_dict(cls, ddict: Dict):
        pass
    @classmethod
    def from_json(cls, json_str: str):
        return cls.from_dict(json.loads(json_str))
prd = True if "manage.py" in ltdr else False
class Entity(JSONMIxin, object):
    def __init__(
        self,
        name: str,
        dimensions: List[Dict[str, Any]] = [],
        uri: Optional[str] = None,
    ):
        self.name = name
        self.dimensions = dimensions
        self.uri = uri
    def __repr__(self):
        msg = 'Entity(name="%s", uri=%s)'
        msg = msg % (self.name, self.uri)
        return msg
    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.name == other.name and self.dimensions == other.dimensions
        else:
            return False
    def __ne__(self, other):
        return not self.__eq__(other)
    def __hash__(self):
        return hash(repr(self))
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "dimensions": self.dimensions,
            "uri": self.uri,
        }
    @classmethod
    def from_dict(cls, ddict: Dict) -> "Entity":
        return cls(
            name=ddict["name"],
            dimensions=ddict["dimensions"],
            uri=ddict["uri"],
        )
class Unit(JSONMIxin, object):
    def __init__(
        self,
        name: str,
        entity: Entity,
        surfaces: List[str] = [],
        uri: Optional[str] = None,
        symbols: List[str] = [],
        dimensions: List[Dict[str, Any]] = [],
        currency_code: Optional[str] = None,
        original_dimensions: Optional[List[Dict[str, Any]]] = None,
        lang="en_US",
    ):
        self.name = name
        self.surfaces = surfaces
        self.entity = entity
        self.uri = uri
        self.symbols = symbols
        self.dimensions = dimensions
        self.original_dimensions = original_dimensions
        self.currency_code = currency_code
        self.lang = lang
    def to_spoken(self, count=1, lang=None) -> str:
        return speak.unit_to_spoken(self, count, lang or self.lang)
    def __repr__(self):
        msg = 'Unit(name="%s", entity=Entity("%s"), uri=%s)'
        msg = msg % (self.name, self.entity.name, self.uri)
        return msg
    def __str__(self):
        return self.to_spoken()
    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return (
                self.name == other.name
                and self.entity == other.entity
                and all(
                    dim1["base"] == dim2["base"] and dim1["power"] == dim2["power"]
                    for dim1, dim2 in zip(self.dimensions, other.dimensions)
                )
            )
        else:
            return False
    def __ne__(self, other):
        return not self.__eq__(other)
    def __hash__(self):
        return hash(repr(self))
    def to_dict(self, include_entity_dict: bool = False) -> Dict:
        ddict = {
            "name": self.name,
            "surfaces": self.surfaces,
            "entity": self.entity.name,
            "uri": self.uri,
            "symbols": self.symbols,
            "dimensions": self.dimensions,
            "original_dimensions": self.original_dimensions,
            "currency_code": self.currency_code,
            "lang": self.lang,
        }
        if include_entity_dict:
            ddict["entity"] = self.entity.to_dict()
        return ddict
    @classmethod
    def from_dict(cls, ddict: Dict) -> "Unit":
        return cls(
            name=ddict["name"],
            surfaces=ddict["surfaces"],
            entity=Entity.from_dict(ddict["entity"]),
            uri=ddict["uri"],
            symbols=ddict["symbols"],
            dimensions=ddict["dimensions"],
            original_dimensions=ddict["original_dimensions"],
            currency_code=ddict["currency_code"],
            lang=ddict["lang"],
        )
if "spell" in ltdr:
	if prd:	
		import spell.loaders as prsr
	else:
		import train.loaders as prsr
elif "digimro" in ltdr:
	if prd:
		import digimro.loaders as prsr
	else:
		import train.loaders as prsr
elif "service" in ltdr:
	if prd:		
		import service.loaders as prsr
	else:
		pass
else:
	prsr = {}
class Quantity(JSONMIxin, object):
    def __init__(
        self,
        value: float,
        unit: Unit,
        surface: Optional[str] = None,
        span: Optional[Tuple[int, int]] = None,
        uncertainty: Optional[float] = None,
        lang="en_US",
    ):
        self.value = value
        self.unit = unit
        self.surface = surface
        self.span = span
        self.uncertainty = uncertainty
        self.lang = lang
    def with_vals(
        self,
        value=None,
        unit=None,
        surface=None,
        span=None,
        uncertainty=None,
        lang=None,
    ):
        return Quantity(
            value if value is not None else self.value,
            unit if unit is not None else self.unit,
            surface if surface is not None else self.surface,
            span if span is not None else self.span,
            uncertainty if uncertainty is not None else self.uncertainty,
            lang if lang is not None else self.lang,
        )
    def __repr__(self):
        msg = 'Quantity(%g, "%s")'
        msg = msg % (self.value, repr(self.unit))
        return msg
    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return (
                self.value == other.value
                and self.unit == other.unit
                and self.surface == other.surface
                and self.span == other.span
                and self.uncertainty == other.uncertainty
            )
        else:
            return False
    def __ne__(self, other):
        return not self.__eq__(other)
    def __str__(self):
        return self.to_spoken(self.lang)
    def to_spoken(self, lang=None):
        return speak.quantity_to_spoken(self, lang or self.lang)
    def to_dict(
        self, include_unit_dict: bool = False, include_entity_dict: bool = False
    ) -> Dict:
        ddict = {
            "value": self.value,
            "unit": self.unit.name,
            "entity": self.unit.entity.name,
            "surface": self.surface,
            "span": self.span,
            "uncertainty": self.uncertainty,
            "lang": self.lang,
        }
        if include_unit_dict:
            ddict["unit"] = self.unit.to_dict(include_entity_dict)
        return ddict
    @classmethod
    def from_dict(cls, ddict: Dict) -> "Quantity":
        return cls(
            value=ddict["value"],
            unit=Unit.from_dict(ddict["unit"]),
            surface=ddict["surface"],
            span=tuple(ddict["span"]),
            uncertainty=ddict["uncertainty"],
            lang=ddict["lang"],
        )