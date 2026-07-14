import calendar
import struct
import unittest

from core.ntp_client import NTP_UNIX_EPOCH_DELTA, NtpClient


class FakeSocket:
    def __init__(self, response):
        self.response = response
        self.timeout = None
        self.request = None
        self.address = None
        self.closed = False

    def settimeout(self, timeout):
        self.timeout = timeout

    def sendto(self, request, address):
        self.request = bytes(request)
        self.address = address

    def recvfrom(self, size):
        return self.response[:size], self.address

    def close(self):
        self.closed = True


class FakeSocketModule:
    AF_INET = 2
    SOCK_DGRAM = 2

    def __init__(self, response):
        self.client = FakeSocket(response)

    def getaddrinfo(self, host, port, family, socket_type):
        return [(family, socket_type, 0, "", ("192.0.2.1", port))]

    def socket(self, family, socket_type):
        return self.client


def create_ntp_response(year, month, day, hour, minute, second):
    unix_seconds = calendar.timegm((year, month, day, hour, minute, second))
    response = bytearray(48)
    response[0] = 0x1C
    response[1] = 1
    response[40:44] = struct.pack("!I", unix_seconds + NTP_UNIX_EPOCH_DELTA)
    return bytes(response)


class NtpClientTest(unittest.TestCase):
    def test_requests_time_and_applies_korea_utc_offset(self):
        sockets = FakeSocketModule(
            create_ntp_response(2026, 7, 12, 0, 30, 45)
        )
        client = NtpClient(socket_module=sockets)

        values = client.request_local_datetime()

        self.assertEqual((2026, 7, 12, 6, 9, 30, 45), values)
        self.assertEqual(0x1B, sockets.client.request[0])
        self.assertEqual(("192.0.2.1", 123), sockets.client.address)
        self.assertTrue(sockets.client.closed)

    def test_rejects_short_response_and_closes_socket(self):
        sockets = FakeSocketModule(b"short")
        client = NtpClient(socket_module=sockets)

        with self.assertRaisesRegex(RuntimeError, "response length"):
            client.request_local_datetime()

        self.assertTrue(sockets.client.closed)


if __name__ == "__main__":
    unittest.main()
