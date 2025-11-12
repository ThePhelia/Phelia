from __future__ import annotations

from fastapi import APIRouter


router = APIRouter(prefix="/market", tags=["market"])


@router.get("/preinstall_warning")
async def preinstall_warning() -> dict[str, object]:
    return {
        "title": "Installing a third-party plugin",
        "paragraphs": [
            "Plugins are created by independent developers, and Phelia does not verify their contents. By installing them, you agree that:",
            "- Some plugins may request access to your data or work with unverified sources.",
            "- If a plugin you install violates copyright or other laws, all responsibility for its use lies with you.",
            "- Install only plugins from trusted sources. If you doubt the safety or legality of a plugin, it is better to cancel installation.",
            "By continuing, you confirm that you understand these risks.",
        ],
        "confirm_button": "Install plugin",
        "cancel_button": "Cancel",
    }
