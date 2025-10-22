"""Entry point class wired into the Phelia plugin loader."""

from __future__ import annotations

import logging
from typing import Any, Iterable

from app.services.search.registry import search_registry

from . import __version__
from .hooks import compose_remove, compose_stop, compose_up, ensure_config_dir, find_plugin_root, wait_for_api_key
from .normalizer import NormalizedResult
from .provider import JackettProvider
from .settings import PluginSettings, load_settings, persist_settings, schema_definition


PLUGIN_ID = "phelia.jackett"


class JackettPlugin:
    """Manage lifecycle hooks and provider registration."""

    def __init__(self) -> None:
        self._root = find_plugin_root()
        self._config_dir = ensure_config_dir(self._root)
        self._provider: JackettProvider | None = None
        self._logger = logging.getLogger(f"phelia.plugin.{PLUGIN_ID}")

    # ---- Hook helpers -------------------------------------------------
    def _resolve_logger(self, ctx: dict[str, Any]) -> logging.Logger:
        candidate = ctx.get("logger")
        if isinstance(candidate, logging.Logger):
            self._logger = candidate
        return self._logger

    def _store(self, ctx: dict[str, Any]):
        store = ctx.get("settings_store")
        if store is None:
            raise RuntimeError("Plugin context missing settings_store")
        return store

    def _register_settings_schema(self, ctx: dict[str, Any]) -> None:
        register = ctx.get("register_settings_panel")
        if callable(register):
            register(PLUGIN_ID, schema_definition())

    def _ensure_provider(self, settings: PluginSettings) -> JackettProvider:
        if self._provider is not None:
            self._provider.update_settings(settings)
            return self._provider
        provider = JackettProvider(settings=settings, logger=self._logger)
        self._provider = provider
        return provider

    def _register_provider(self, provider: JackettProvider) -> None:
        search_registry.unregister(provider.slug)
        search_registry.register(provider)

    def _unregister_provider(self) -> None:
        if self._provider is None:
            return
        search_registry.unregister(self._provider.slug)
        self._provider = None

    # ---- Lifecycle hooks ----------------------------------------------
    def on_install(self, ctx: dict[str, Any]) -> None:
        logger = self._resolve_logger(ctx)
        self._register_settings_schema(ctx)
        logger.info("Installing Jackett Integrator v%s", __version__)
        compose_up(self._root)

    def on_enable(self, ctx: dict[str, Any]) -> None:
        logger = self._resolve_logger(ctx)
        self._register_settings_schema(ctx)

        store = self._store(ctx)
        compose_up(self._root)
        settings = load_settings(store)

        if not settings.jackett_api_key:
            api_key = wait_for_api_key(self._config_dir)
            if api_key:
                settings.jackett_api_key = api_key
                persist_settings(store, settings, validate=False)
                logger.info("Captured Jackett API key from container")
            else:
                logger.warning(
                    "Jackett API key could not be determined automatically; please configure it manually"
                )

        provider = self._ensure_provider(settings)
        self._register_provider(provider)
        logger.info("Jackett Integrator enabled")

    def on_disable(self, ctx: dict[str, Any]) -> None:
        logger = self._resolve_logger(ctx)
        self._unregister_provider()
        compose_stop(self._root)
        logger.info("Jackett Integrator disabled")

    def on_uninstall(self, ctx: dict[str, Any]) -> None:
        logger = self._resolve_logger(ctx)
        self._unregister_provider()
        compose_remove(self._root)
        logger.info("Jackett Integrator uninstalled")

    # ---- Exposed actions ----------------------------------------------
    async def send_to_qbittorrent(self, items: Iterable[NormalizedResult]) -> list[str]:
        if self._provider is None:
            raise RuntimeError("Search provider has not been initialised")
        self._provider.settings.validate()
        return await self._provider.send_to_qbittorrent(items)

