"""
Org registry reader/writer.

Manages system/org/registry.toml as the authoritative index of all
organizations created in this local installation.
"""

import logging
import tomllib
from pathlib import Path
from ...core.models.context import Context
from ...core.schemas.company import OrganizationEntity

logger = logging.getLogger(__name__)



def get_org(context: Context) -> list[OrganizationEntity]:
    """Return all organizations from the org registry index.

    Reads system/org/registry.toml rather than scanning data/ folders.
    Each entry provides only the left-pane fields (name, legal, currency);
    full org data is loaded separately via get_org_snapshot() when selected.
    """
    try:

        entries = read_org_registry()
        results = []
        for entry in entries:
            try:
                results.append(
                    OrganizationEntity(
                        name=entry["name"],
                        legal=entry.get("legal"),
                        currency=entry.get("currency"),
                    )
                )
            except Exception:
                continue
        return results
    except Exception:
        return []


def get_org_registry_path() -> Path:
    """
    Return the path to system/org/registry.toml.

    registry.toml lives in the same directory as this file.
    """
    return Path(__file__).resolve().parent / "registry.toml"


def read_org_registry() -> list[dict]:
    """
    Read all entries from registry.toml.

    Returns the [[organizations]] array as a list of dicts, each with at
    minimum id and name. Returns [] on any error (missing file, parse error,
    missing key).
    """
    try:
        registry_path = get_org_registry_path()
        if not registry_path.exists():
            return []
        with open(registry_path, "rb") as f:
            data = tomllib.load(f)
        return data.get("organizations", [])
    except Exception:
        return []


def write_org_to_registry(org_data: dict) -> bool:
    """
    Append or update one org entry in registry.toml.

    Idempotent — calling twice for the same org id does not create a duplicate.
    Uses string formatting rather than a TOML writer library.

    Args:
        org_data: dict with keys: name (required), legal (optional), currency (optional)

    Returns:
        True on success, False on any error. Never raises.
    """
    try:
        name: str | None = org_data.get("name")
        if not name:
            logger.warning("write_org_to_registry: missing 'name' in org_data")
            return False

        org_id = name.lower()
        registry_path = get_org_registry_path()

        # Read existing file content (or start empty).
        if registry_path.exists():
            current_text = registry_path.read_text(encoding="utf-8")
        else:
            current_text = ""

        # Idempotency check: skip if this id is already present.
        if f'id = "{org_id}"' in current_text:
            return True

        # Build the new [[organizations]] block.
        lines = [
            "\n[[organizations]]",
            f'id = "{org_id}"',
            f'name = "{name}"',
        ]
        legal: str | None = org_data.get("legal")
        if legal is not None:
            lines.append(f'legal = "{legal}"')
        currency: str | None = org_data.get("currency")
        if currency is not None:
            lines.append(f'currency = "{currency}"')

        block = "\n".join(lines) + "\n"

        # Append to file (ensure file and parent dirs exist).
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        with open(registry_path, "a", encoding="utf-8") as f:
            f.write(block)

        return True

    except Exception as exc:
        logger.warning("write_org_to_registry failed: %s", exc)
        return False
