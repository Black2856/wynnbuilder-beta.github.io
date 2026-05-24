"""Build URL encode/decode for Wynnbuilder V12 binary format.

Ports the binary BitVector encoding from js/builder/build_encode_decode.js and
js/utils.js. Only NORMAL (non-crafted, non-custom) equipment items are supported.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Custom Base64 alphabet used by Wynnbuilder (NOT standard Base64).
B64_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz+-"
B64_MAP: dict[str, int] = {c: i for i, c in enumerate(B64_CHARS)}

# First 6 bits of a V12 binary hash. Must be > 11 to distinguish from legacy format.
VECTOR_FLAG = 0xC  # 12
VERSION_BITLEN = 10

# Ordered list of Wynncraft data versions (mirrors load_item.js::wynn_version_names).
WYNN_VERSION_NAMES: list[str] = [
    "2.0.1.1", "2.0.1.2", "2.0.2.1", "2.0.2.3", "2.0.3.1",
    "2.0.4.1", "2.0.4.3", "2.0.4.4",
    "2.1.0.0", "2.1.0.1",
    "2.1.1.0", "2.1.1.1", "2.1.1.2", "2.1.1.3", "2.1.1.4",
    "2.1.1.5", "2.1.1.6", "2.1.1.7",
    "2.1.2.0", "2.1.3.0", "2.1.3.4",
    "2.1.4.0", "2.1.5.0", "2.1.6.0",
    "2.2.0.0", "2.2.0.7", "2.2.0.12", "2.2.0.14", "2.2.0.19", "2.2.0.21", "2.2.0.31",
]
WYNN_VERSION_LATEST: int = len(WYNN_VERSION_NAMES) - 1  # 30

# Equipment indices that support powders (helmet, chestplate, leggings, boots, weapon).
POWDERABLE_INDICES: frozenset[int] = frozenset({0, 1, 2, 3, 8})

EQUIPMENT_KIND_BITLEN = 2
EQUIPMENT_KIND_NORMAL = 0
EQUIPMENT_KIND_CRAFTED = 1
EQUIPMENT_KIND_CUSTOM = 2

DEFAULT_DATA_ROOT = Path(__file__).resolve().parents[4]


class BitWriter:
    """Bit writer using LSB-first encoding, matching JS BitVector.

    Bits are stored as a Python int with bit 0 = LSB.
    append(value, bitlen) stores bitlen bits of value at the current position.
    to_b64() converts the bit array to the Wynnbuilder custom Base64 string.
    """

    def __init__(self) -> None:
        self._bits = 0
        self._length = 0

    def append(self, value: int, bitlen: int) -> None:
        if bitlen == 0:
            return
        mask = (1 << bitlen) - 1
        self._bits |= (value & mask) << self._length
        self._length += bitlen

    def to_b64(self) -> str:
        result: list[str] = []
        pos = 0
        while pos < self._length:
            result.append(B64_CHARS[(self._bits >> pos) & 0x3F])
            pos += 6
        return "".join(result)


class BitReader:
    """Bit reader using LSB-first encoding, matching JS BitVectorCursor.

    Parses a Wynnbuilder Base64 string into a bit array (LSB-first).
    advance_by(n) extracts n bits at the current position and advances.
    """

    def __init__(self, s: str) -> None:
        self._bits = 0
        self._length = len(s) * 6
        for i, c in enumerate(s):
            self._bits |= B64_MAP[c] << (i * 6)
        self._pos = 0

    def advance_by(self, bitlen: int) -> int:
        mask = (1 << bitlen) - 1
        value = (self._bits >> self._pos) & mask
        self._pos += bitlen
        return value

    def remaining(self) -> int:
        return self._length - self._pos

    def consume_b64(self) -> str:
        """Return all remaining bits as a Base64 string (used for atree data)."""
        result: list[str] = []
        pos = self._pos
        while pos < self._length:
            result.append(B64_CHARS[(self._bits >> pos) & 0x3F])
            pos += 6
        return "".join(result)


def _load_enc(data_root: Path, version_name: str) -> dict[str, Any]:
    path = data_root / "data" / version_name / "encoding_consts.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _skip_powders(cursor: BitReader, enc: dict[str, Any]) -> None:
    """Advance the cursor past powder data for one item without decoding values."""
    flag = cursor.advance_by(enc["EQUIPMENT_POWDERS_FLAG"]["BITLEN"])
    if flag == enc["EQUIPMENT_POWDERS_FLAG"]["NO_POWDERS"]:
        return
    # HAS_POWDERS: first powder ID is always encoded
    cursor.advance_by(enc["POWDER_ID_BITLEN"])
    while True:
        repeat_op = cursor.advance_by(enc["POWDER_REPEAT_OP"]["BITLEN"])
        if repeat_op == enc["POWDER_REPEAT_OP"]["REPEAT"]:
            continue
        # NO_REPEAT
        tier_op = cursor.advance_by(enc["POWDER_REPEAT_TIER_OP"]["BITLEN"])
        if tier_op == enc["POWDER_REPEAT_TIER_OP"]["REPEAT_TIER"]:
            cursor.advance_by(enc["POWDER_WRAPPER_BITLEN"])
        else:
            # CHANGE_POWDER
            change_op = cursor.advance_by(enc["POWDER_CHANGE_OP"]["BITLEN"])
            if change_op == enc["POWDER_CHANGE_OP"]["NEW_ITEM"]:
                break
            # NEW_POWDER: another powder ID follows
            cursor.advance_by(enc["POWDER_ID_BITLEN"])


def decode_build(
    url_hash: str,
    wynn_data: Any,
    data_root: Path | None = None,
) -> dict[str, Any]:
    """Decode a V12 binary Wynnbuilder URL hash.

    Returns a dict with keys:
      equipment  -- list of 8 item display names (or None for empty slot)
      weapon     -- weapon display name (or None)
      level      -- build level (int)
      version_id -- numeric version index
      version_name -- version string like "2.2.0.31"

    Raises ValueError for legacy (pre-V12) hashes.
    Raises NotImplementedError for CRAFTED or CUSTOM equipment items.
    """
    if data_root is None:
        data_root = DEFAULT_DATA_ROOT

    cursor = BitReader(url_hash)

    vector_flag = cursor.advance_by(6)
    if vector_flag <= 11:
        raise ValueError(
            f"Legacy build hash not supported (first 6-bit value = {vector_flag}). "
            "Only V12 binary format is decoded."
        )

    version_id = cursor.advance_by(VERSION_BITLEN)
    if version_id >= len(WYNN_VERSION_NAMES):
        raise ValueError(f"Unknown version ID {version_id} in build hash.")
    version_name = WYNN_VERSION_NAMES[version_id]
    enc = _load_enc(data_root, version_name)

    items: list[str | None] = []
    redirect_map: dict[int, int] = getattr(wynn_data, "_redirect_map", {})
    items_by_id: dict[int, dict[str, Any]] = getattr(wynn_data, "_items_by_id", {})

    for i in range(enc["EQUIPMENT_NUM"]):
        kind = cursor.advance_by(enc["EQUIPMENT_KIND"]["BITLEN"])
        if kind == EQUIPMENT_KIND_NORMAL:
            raw_id = cursor.advance_by(enc["ITEM_ID_BITLEN"])
            if raw_id == 0:
                items.append(None)
            else:
                item_id = raw_id - 1
                item_id = redirect_map.get(item_id, item_id)
                item = items_by_id.get(item_id)
                if item is not None:
                    items.append(item.get("displayName") or item.get("name"))
                else:
                    items.append(None)
        elif kind == EQUIPMENT_KIND_CRAFTED:
            raise NotImplementedError("Crafted item decoding is not supported.")
        else:
            raise NotImplementedError("Custom item decoding is not supported.")

        if i in POWDERABLE_INDICES:
            _skip_powders(cursor, enc)

    # Skip tomes
    tomes_flag = cursor.advance_by(enc["TOMES_FLAG"]["BITLEN"])
    if tomes_flag == enc["TOMES_FLAG"]["HAS_TOMES"]:
        for _ in range(enc["TOME_NUM"]):
            slot_flag = cursor.advance_by(enc["TOME_SLOT_FLAG"]["BITLEN"])
            if slot_flag == enc["TOME_SLOT_FLAG"]["USED"]:
                cursor.advance_by(enc["TOME_ID_BITLEN"])

    # Skip skillpoints
    sp_flag = cursor.advance_by(enc["SP_FLAG"]["BITLEN"])
    if sp_flag == enc["SP_FLAG"]["ASSIGNED"]:
        for _ in range(enc["SP_TYPES"]):
            elem_flag = cursor.advance_by(enc["SP_ELEMENT_FLAG"]["BITLEN"])
            if elem_flag == enc["SP_ELEMENT_FLAG"]["ELEMENT_ASSIGNED"]:
                cursor.advance_by(enc["MAX_SP_BITLEN"])

    # Level
    level_flag = cursor.advance_by(enc["LEVEL_FLAG"]["BITLEN"])
    if level_flag == enc["LEVEL_FLAG"]["MAX"]:
        level = enc["MAX_LEVEL"]
    else:
        level = cursor.advance_by(enc["LEVEL_BITLEN"])

    return {
        "equipment": items[:8],
        "weapon": items[8] if len(items) > 8 else None,
        "level": level,
        "version_id": version_id,
        "version_name": version_name,
    }


def encode_build(
    equipment: list[str | None],
    weapon: str | None,
    level: int,
    wynn_data: Any,
    data_root: Path | None = None,
    version_id: int | None = None,
) -> str:
    """Encode 8 equipment item names + weapon + level to a V12 Wynnbuilder URL hash.

    equipment: list of exactly 8 names in slot order
        [helmet, chestplate, leggings, boots, ring1, ring2, bracelet, necklace].
        Use None for an empty slot.
    weapon: weapon item name, or None.
    level: build level (1..MAX_LEVEL).

    Output: Base64 hash string suitable for appending after '#' in a Wynnbuilder URL.
    No powders, no tomes, no manually assigned skillpoints, no aspects are encoded.
    All items must be NORMAL (not crafted or custom).
    """
    if data_root is None:
        data_root = DEFAULT_DATA_ROOT
    if version_id is None:
        version_id = WYNN_VERSION_LATEST
    version_name = WYNN_VERSION_NAMES[version_id]
    enc = _load_enc(data_root, version_name)

    writer = BitWriter()

    # Header
    writer.append(VECTOR_FLAG, 6)
    writer.append(version_id, VERSION_BITLEN)

    # Equipment: 8 armor/accessory items + weapon (index 8)
    all_items = list(equipment) + [weapon]
    for i, name in enumerate(all_items):
        writer.append(EQUIPMENT_KIND_NORMAL, EQUIPMENT_KIND_BITLEN)
        if name is None:
            writer.append(0, enc["ITEM_ID_BITLEN"])
        else:
            item = wynn_data.item(name)
            writer.append(item["id"] + 1, enc["ITEM_ID_BITLEN"])
        if i in POWDERABLE_INDICES:
            writer.append(
                enc["EQUIPMENT_POWDERS_FLAG"]["NO_POWDERS"],
                enc["EQUIPMENT_POWDERS_FLAG"]["BITLEN"],
            )

    # Tomes: NO_TOMES
    writer.append(enc["TOMES_FLAG"]["NO_TOMES"], enc["TOMES_FLAG"]["BITLEN"])

    # Skillpoints: AUTOMATIC (no manual assignment)
    writer.append(enc["SP_FLAG"]["AUTOMATIC"], enc["SP_FLAG"]["BITLEN"])

    # Level
    if level == enc["MAX_LEVEL"]:
        writer.append(enc["LEVEL_FLAG"]["MAX"], enc["LEVEL_FLAG"]["BITLEN"])
    else:
        writer.append(enc["LEVEL_FLAG"]["OTHER"], enc["LEVEL_FLAG"]["BITLEN"])
        writer.append(level, enc["LEVEL_BITLEN"])

    # Aspects: NO_ASPECTS
    writer.append(enc["ASPECTS_FLAG"]["NO_ASPECTS"], enc["ASPECTS_FLAG"]["BITLEN"])

    # Ability tree: empty (nothing appended; Wynnbuilder treats missing atree as all-off)

    return writer.to_b64()
