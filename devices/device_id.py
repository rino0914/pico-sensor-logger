"""Stable, short identifiers derived from the Pico board unique ID."""

BASE36_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyz"
DEFAULT_SUFFIX_LENGTH = 2
FNV1A_OFFSET_BASIS = 2166136261
FNV1A_PRIME = 16777619


def unique_id_suffix(identifier, length=DEFAULT_SUFFIX_LENGTH):
    if not identifier:
        raise ValueError("identifier must not be empty")
    if length <= 0:
        raise ValueError("suffix length must be greater than zero")

    # Hash every byte so the suffix is not determined by only the final byte.
    value = FNV1A_OFFSET_BASIS
    for byte in identifier:
        value ^= byte
        value = (value * FNV1A_PRIME) & 0xFFFFFFFF

    base = len(BASE36_ALPHABET)
    value %= base ** length
    characters = ["0"] * length
    for index in range(length - 1, -1, -1):
        characters[index] = BASE36_ALPHABET[value % base]
        value //= base
    return "".join(characters)


def board_suffix(length=DEFAULT_SUFFIX_LENGTH):
    from machine import unique_id

    return unique_id_suffix(unique_id(), length)
