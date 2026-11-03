"""Model registry: map configuration dictionaries to model instances."""
from __future__ import annotations

import importlib

from volrisk.forecasting.base import MODEL_IMPLEMENTED, VolatilityModel

_REGISTRY: dict[str, type[VolatilityModel]] = {}
_MODULES = ("volrisk.forecasting.historical", "volrisk.forecasting.ewma", "volrisk.forecasting.garch",
            "volrisk.forecasting.regime_switching", "volrisk.forecasting.stochastic_volatility",
            "volrisk.forecasting.realized_volatility", "volrisk.forecasting.ml", "volrisk.forecasting.positive_har")


def register(type_name: str):
    def decorator(cls: type[VolatilityModel]):
        if type_name in _REGISTRY and _REGISTRY[type_name] is not cls:
            raise ValueError(f"model type {type_name!r} is already registered")
        _REGISTRY[type_name] = cls
        cls.type_name = type_name
        return cls
    return decorator


def _ensure_loaded() -> None:
    for module in _MODULES:
        importlib.import_module(module)


def available_model_types() -> dict[str, dict]:
    _ensure_loaded()
    return {key: {"class": cls.__name__, "family": cls.family, "version": cls.version,
                  "implementation_status": cls.implementation_status}
            for key, cls in sorted(_REGISTRY.items())}


def model_class(type_name: str) -> type[VolatilityModel]:
    _ensure_loaded()
    try:
        return _REGISTRY[type_name]
    except KeyError:
        raise KeyError(f"unknown model type {type_name!r}; known: {sorted(_REGISTRY)}") from None


def build_model(name: str, spec: dict) -> VolatilityModel:
    """``spec`` is a configuration mapping with a ``type`` key plus model keyword arguments."""
    spec = dict(spec)
    type_name = spec.pop("type", None)
    if not type_name:
        raise ValueError(f"model {name!r} needs a 'type' entry")
    spec.pop("enabled", None)
    return model_class(type_name)(name, **spec)


def build_models(model_specs: dict[str, dict], names: list[str] | None = None, *, implemented_only: bool = True):
    names = list(model_specs) if names is None else list(names)
    models = []
    for name in names:
        if name not in model_specs:
            raise KeyError(f"model {name!r} is not defined in the configuration")
        spec = model_specs[name]
        if not spec.get("enabled", True):
            continue
        model = build_model(name, spec)
        if implemented_only and model.implementation_status != MODEL_IMPLEMENTED:
            raise NotImplementedError(f"model {name!r} ({model.implementation_status}) cannot be run yet: "
                                      f"{getattr(model, 'pending_reason', 'not implemented')}")
        models.append(model)
    return models
