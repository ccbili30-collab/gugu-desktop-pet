"""Art species registry for gugupet_v2.

At startup, each species registers its manifest here.
The body asks for frames by slot name and species id.
"""

from __future__ import annotations

from art.manifest import ALL_SLOTS, SLOT_FALLBACK, REQUIRED_SLOTS


_REGISTRY: dict[str, object] = {}


def register(manifest: object) -> None:
    """Register a species manifest.  Call once at startup."""
    species_id = str(getattr(manifest, "SPECIES_ID", "")).strip()
    if not species_id:
        raise ValueError("Manifest must define SPECIES_ID")
    slots = getattr(manifest, "SLOTS", {})
    missing = REQUIRED_SLOTS - set(slots.keys())
    if missing:
        raise ValueError(
            f"Manifest '{species_id}' is missing required slots: {missing}"
        )
    _REGISTRY[species_id] = manifest


def get_manifest(species_id: str) -> object:
    if species_id not in _REGISTRY:
        raise KeyError(f"No art manifest registered for species '{species_id}'")
    return _REGISTRY[species_id]


def frames_for_slot(species_id: str, slot: str) -> list[str]:
    """Return the list of frame keys for a given behavior slot.

    Falls back through SLOT_FALLBACK if the slot is not in the manifest.
    Raises KeyError if species is unknown.
    """
    manifest = get_manifest(species_id)
    slots: dict = getattr(manifest, "SLOTS", {})
    if slot in slots:
        return list(slots[slot])
    fallback = SLOT_FALLBACK.get(slot, "idle")
    return list(slots.get(fallback, []))


def pixel_size(species_id: str) -> int:
    return int(getattr(get_manifest(species_id), "PIXEL_SIZE", 6))


def palette(species_id: str) -> dict[str, str | None]:
    return dict(getattr(get_manifest(species_id), "PALETTE", {}))


def registered_species() -> list[str]:
    return list(_REGISTRY.keys())
