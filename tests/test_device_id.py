import unittest

from devices.device_id import unique_id_suffix


class DeviceIdTest(unittest.TestCase):
    def test_creates_stable_two_character_base36_suffix(self):
        identifier = bytes((0x01, 0x23, 0x45, 0x67, 0x89, 0xAB, 0xCD, 0xEF))

        suffix = unique_id_suffix(identifier)

        self.assertEqual(2, len(suffix))
        self.assertTrue(all(character in "0123456789abcdefghijklmnopqrstuvwxyz" for character in suffix))
        self.assertEqual(suffix, unique_id_suffix(identifier))

    def test_uses_the_complete_identifier(self):
        self.assertNotEqual(
            unique_id_suffix(bytes((0x01, 0x02, 0x03))),
            unique_id_suffix(bytes((0x02, 0x02, 0x03))),
        )

    def test_rejects_empty_identifier(self):
        with self.assertRaisesRegex(ValueError, "must not be empty"):
            unique_id_suffix(b"")


if __name__ == "__main__":
    unittest.main()
