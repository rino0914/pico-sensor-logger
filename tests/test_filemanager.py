import os
import tempfile
import unittest

from core.data_connector import DataConnector
from storage.filemanager import CsvWriter, FileHandler


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

    def test_csv_writer_never_exceeds_record_limit(self):
        descriptor, path = tempfile.mkstemp()
        os.close(descriptor)
        try:
            connector = DataConnector()
            writer = CsvWriter(
                connector,
                FileHandler(path),
                "timestamp,co2,temperature,humidity",
                max_records=2,
            )
            connector.start_sensing()
            timestamp = (2026, 7, 15, 2, 10, 0, 0, 0)
            for value in (400, 401, 402):
                connector.publish(timestamp, value, 50, 25)

            writer.flush()

            self.assertTrue(writer.is_full())
            self.assertEqual(2, writer.record_count())
            self.assertEqual(0, writer.pending_count())
            self.assertEqual(3, FileHandler(path).count_lines())
        finally:
            os.unlink(path)

    def test_csv_writer_counts_existing_records_on_startup(self):
        descriptor, path = tempfile.mkstemp()
        os.close(descriptor)
        try:
            handler = FileHandler(path)
            handler.write("header\nfirst\nsecond\n")

            writer = CsvWriter(DataConnector(), handler, "header", max_records=2)

            self.assertEqual(2, writer.record_count())
            self.assertTrue(writer.is_full())
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
