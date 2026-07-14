import os
import tempfile
import unittest

from storage.filemanager import FileHandler


class FileHandlerStreamingTest(unittest.TestCase):
    def test_iter_chunks_uses_file_size_snapshot(self):
        descriptor, path = tempfile.mkstemp()
        os.close(descriptor)
        try:
            handler = FileHandler(path)
            handler.write("abcdef")
            chunks = handler.iter_chunks(2)

            self.assertEqual(b"ab", next(chunks))
            handler.write_line("new")

            self.assertEqual(b"cdef", b"".join(chunks))
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
