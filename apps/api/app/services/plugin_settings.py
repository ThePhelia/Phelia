"""Persistence and validation helpers for plugin settings."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import PluginSetting


class PluginSettingsValidationError(ValueError):
    """Raised when submitted plugin settings fail schema validation."""

    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(message)
        self.field = field


def _extract_types(field_schema: Mapping[str, Any]) -> tuple[set[str], bool]:
    raw_type = field_schema.get("type")
    types: set[str] = set()
    nullable = False

    if isinstance(raw_type, str):
        if raw_type == "null":
            nullable = True
        else:
            types.add(raw_type)
    elif isinstance(raw_type, list):
        for entry in raw_type:
            if entry == "null":
                nullable = True
            elif isinstance(entry, str):
                types.add(entry)

    # Some schemas may use "password" as a primary type which should behave like string
    if "password" in types:
        types.add("string")

    return types, nullable


def _coerce_boolean(raw: Any) -> bool:
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        normalized = raw.strip().lower()
        if normalized in {"true", "1", "yes", "on"}:
            return True
        if normalized in {"false", "0", "no", "off"}:
            return False
    raise PluginSettingsValidationError("Value must be a boolean")


def _validate_field(field: str, field_schema: Mapping[str, Any], raw: Any) -> Any:
    enum_values = field_schema.get("enum")
    types, nullable = _extract_types(field_schema)

    if isinstance(enum_values, list) and enum_values:
        allowed = set(enum_values)
        if raw is None:
            if nullable or None in allowed:
                return None
            raise PluginSettingsValidationError("Value is required", field=field)
        if raw not in allowed:
            raise PluginSettingsValidationError("Value must match one of the allowed options", field=field)
        return raw

    if raw is None:
        if nullable:
            return None
        raise PluginSettingsValidationError("Value is required", field=field)

    if "boolean" in types:
        try:
            return _coerce_boolean(raw)
        except PluginSettingsValidationError as exc:
            exc.field = field
            raise

    if field_schema.get("format") == "password":
        types.add("string")

    if "string" in types or not types:
        if isinstance(raw, str):
            return raw
        return str(raw)

    raise PluginSettingsValidationError("Unsupported field type", field=field)


def validate_against_schema(
    schema: Mapping[str, Any] | None,
    values: Mapping[str, Any],
) -> tuple[dict[str, Any], set[str]]:
    """Validate ``values`` against ``schema`` returning sanitized data and allowed keys."""

    if not isinstance(values, Mapping):
        raise PluginSettingsValidationError("Settings values must be an object")

    if not schema:
        sanitized = {str(key): value for key, value in values.items()}
        return sanitized, set(sanitized.keys())

    if not isinstance(schema, Mapping):
        raise PluginSettingsValidationError("Invalid schema definition")

    properties = schema.get("properties") or {}
    if not isinstance(properties, Mapping):
        raise PluginSettingsValidationError("Invalid schema definition")

    required = schema.get("required") or []
    if not isinstance(required, (list, tuple, set)):
        raise PluginSettingsValidationError("Invalid schema definition")

    allowed_keys = {str(key) for key in properties.keys()}
    values_dict = {str(key): value for key, value in values.items()}

    for key in values_dict.keys():
        if key not in allowed_keys:
            raise PluginSettingsValidationError("Unknown setting key", field=key)

    for key in required:
        key_str = str(key)
        if key_str not in values_dict:
            raise PluginSettingsValidationError("Missing required field", field=key_str)

    sanitized: dict[str, Any] = {}
    for key, field_schema in properties.items():
        if key not in values_dict:
            continue
        if not isinstance(field_schema, Mapping):
            raise PluginSettingsValidationError("Invalid field schema", field=key)
        sanitized[key] = _validate_field(key, field_schema, values_dict[key])

    return sanitized, allowed_keys


def apply_defaults(schema: Mapping[str, Any] | None, values: Mapping[str, Any]) -> dict[str, Any]:
    """Merge schema defaults with stored values without mutating the originals."""

    merged = {str(key): value for key, value in values.items()}

    if not schema or not isinstance(schema, Mapping):
        return merged

    properties = schema.get("properties") or {}
    if not isinstance(properties, Mapping):
        return merged

    for key, field_schema in properties.items():
        if key in merged:
            continue
        if isinstance(field_schema, Mapping) and "default" in field_schema:
            merged[key] = field_schema["default"]

    return merged


def get_settings(db: Session, plugin_id: str) -> dict[str, Any]:
    result = db.execute(
        select(PluginSetting).where(PluginSetting.plugin_id == plugin_id)
    )
    rows = result.scalars().all()
    return {row.key: row.value_json for row in rows}


def get_setting(db: Session, plugin_id: str, key: str) -> Any:
    result = db.execute(
        select(PluginSetting.value_json).where(
            PluginSetting.plugin_id == plugin_id, PluginSetting.key == key
        )
    )
    return result.scalar_one_or_none()


def set_value(db: Session, plugin_id: str, key: str, value: Any) -> None:
    result = db.execute(
        select(PluginSetting).where(
            PluginSetting.plugin_id == plugin_id, PluginSetting.key == key
        )
    )
    existing = result.scalar_one_or_none()
    if existing is None:
        db.add(PluginSetting(plugin_id=plugin_id, key=key, value_json=value))
    else:
        existing.value_json = value
    db.flush()


def replace_settings(
    db: Session,
    plugin_id: str,
    values: Mapping[str, Any],
    allowed_keys: set[str] | None = None,
) -> None:
    result = db.execute(
        select(PluginSetting).where(PluginSetting.plugin_id == plugin_id)
    )
    existing = {row.key: row for row in result.scalars().all()}

    incoming_keys = {str(key) for key in values.keys()}

    for key, value in values.items():
        record = existing.get(key)
        if record is None:
            db.add(PluginSetting(plugin_id=plugin_id, key=key, value_json=value))
        else:
            record.value_json = value

    for key, record in existing.items():
        if key in incoming_keys:
            continue
        if allowed_keys is not None and key not in allowed_keys:
            continue
        db.delete(record)

    db.flush()


def delete_settings(db: Session, plugin_id: str) -> None:
    db.execute(delete(PluginSetting).where(PluginSetting.plugin_id == plugin_id))
    db.flush()
