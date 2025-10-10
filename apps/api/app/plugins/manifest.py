"""Data models for plugin manifests."""

from __future__ import annotations

from typing import Any, Mapping

from pydantic import BaseModel, Field


class PluginAuthor(BaseModel):
    """Author metadata for a plugin."""

    name: str | None = None
    url: str | None = None
    email: str | None = None


class PluginManifest(BaseModel):
    """Normalized representation of a plugin manifest."""

    id: str
    name: str
    version: str
    entry_point: str
    min_phelia: str
    description: str | None = None
    author: PluginAuthor | None = None
    license: str | None = None
    python_requirement: str | None = None
    settings_schema: dict[str, Any] | None = None
    contributes_settings: bool | None = None
    permissions: list[str] = Field(default_factory=list)
    web_assets_path: str | None = None
    integrity_sha256: str | None = None

    @classmethod
    def from_yaml_mapping(
        cls,
        data: Mapping[str, Any],
        permissions: list[str] | None,
        web_assets_path: str | None,
    ) -> "PluginManifest":
        """Build a manifest model from the YAML mapping representation."""

        phelia = data.get("phelia")
        if not isinstance(phelia, Mapping):
            raise ValueError("Manifest missing 'phelia' section")
        hooks = phelia.get("hooks")
        if not isinstance(hooks, Mapping):
            raise ValueError("Manifest missing 'phelia.hooks'")
        backend = hooks.get("backend")
        if not isinstance(backend, Mapping):
            raise ValueError("Manifest missing backend hook definition")

        runtime = data.get("runtime")
        runtime_mapping: Mapping[str, Any] = (
            runtime if isinstance(runtime, Mapping) else {}
        )

        integrity_block = data.get("integrity")
        integrity_mapping: Mapping[str, Any] = (
            integrity_block if isinstance(integrity_block, Mapping) else {}
        )

        author_block = data.get("author")
        author_model = None
        if isinstance(author_block, Mapping):
            author_model = PluginAuthor.model_validate(author_block)

        settings_schema = runtime_mapping.get("settingsSchema")
        if settings_schema is not None and not isinstance(settings_schema, Mapping):
            raise ValueError("'runtime.settingsSchema' must be a mapping when provided")

        contributes_settings_raw = runtime_mapping.get("contributesSettings")
        contributes_settings: bool | None
        if contributes_settings_raw is None:
            contributes_settings = None
        elif isinstance(contributes_settings_raw, bool):
            contributes_settings = contributes_settings_raw
        elif isinstance(contributes_settings_raw, str):
            normalized = contributes_settings_raw.strip().lower()
            if normalized in {"true", "1", "yes", "on"}:
                contributes_settings = True
            elif normalized in {"false", "0", "no", "off"}:
                contributes_settings = False
            else:
                raise ValueError(
                    "'runtime.contributesSettings' must be a boolean or truthy/falsey string"
                )
        else:
            raise ValueError(
                "'runtime.contributesSettings' must be a boolean or string"
            )

        python_requirement = runtime_mapping.get("python")
        if python_requirement is not None and not isinstance(python_requirement, str):
            python_requirement = str(python_requirement)

        permissions_list = [str(item) for item in permissions or []]

        integrity_sha = integrity_mapping.get("sha256")
        if integrity_sha is not None and not isinstance(integrity_sha, str):
            integrity_sha = str(integrity_sha)

        min_version = phelia.get("minVersion")
        if not isinstance(min_version, str):
            raise ValueError("'phelia.minVersion' must be a string")

        entry_point = backend.get("entrypoint")
        if not isinstance(entry_point, str) or not entry_point:
            raise ValueError("Backend entry point must be specified")

        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            version=str(data["version"]),
            entry_point=entry_point,
            min_phelia=min_version,
            description=(
                str(data.get("description"))
                if data.get("description") is not None
                else None
            ),
            author=author_model,
            license=(
                str(data.get("license")) if data.get("license") is not None else None
            ),
            python_requirement=(
                python_requirement if isinstance(python_requirement, str) else None
            ),
            settings_schema=(
                dict(settings_schema) if isinstance(settings_schema, Mapping) else None
            ),
            contributes_settings=(
                contributes_settings
                if contributes_settings is not None
                else bool(settings_schema)
            ),
            permissions=permissions_list,
            web_assets_path=web_assets_path,
            integrity_sha256=integrity_sha if isinstance(integrity_sha, str) else None,
        )
