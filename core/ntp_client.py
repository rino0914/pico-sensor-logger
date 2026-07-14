import socket
import struct
from time import gmtime


NTP_SERVER = "pool.ntp.org"
NTP_PORT = 123
NTP_TIMEOUT_SECONDS = 5
LOCAL_UTC_OFFSET_SECONDS = 9 * 60 * 60

NTP_PACKET_SIZE = 48
NTP_UNIX_EPOCH_DELTA = 2208988800
NTP_2000_EPOCH_DELTA = 3155673600


class NtpClient:
    def __init__(
        self,
        server=NTP_SERVER,
        utc_offset_seconds=LOCAL_UTC_OFFSET_SECONDS,
        timeout_seconds=NTP_TIMEOUT_SECONDS,
        socket_module=socket,
    ):
        self.server = server
        self.utc_offset_seconds = utc_offset_seconds
        self.timeout_seconds = timeout_seconds
        self.socket_module = socket_module

    def request_local_datetime(self):
        response = self._request()
        if len(response) < NTP_PACKET_SIZE:
            raise RuntimeError("Invalid NTP response length")
        if response[1] == 0:
            raise RuntimeError("NTP server is not synchronized")

        ntp_seconds = struct.unpack("!I", response[40:44])[0]
        epoch_delta = self._epoch_delta()
        local_seconds = (
            ntp_seconds
            - epoch_delta
            + self.utc_offset_seconds
        )
        values = gmtime(local_seconds)
        return (
            values[0],
            values[1],
            values[2],
            values[6],
            values[3],
            values[4],
            values[5],
        )

    def _request(self):
        request = bytearray(NTP_PACKET_SIZE)
        request[0] = 0x1B
        address = self.socket_module.getaddrinfo(
            self.server,
            NTP_PORT,
            0,
            self.socket_module.SOCK_DGRAM,
        )[0][-1]
        client = self.socket_module.socket(
            self.socket_module.AF_INET,
            self.socket_module.SOCK_DGRAM,
        )

        try:
            client.settimeout(self.timeout_seconds)
            client.sendto(request, address)
            response, _ = client.recvfrom(NTP_PACKET_SIZE)
            return response
        finally:
            client.close()

    @staticmethod
    def _epoch_delta():
        if gmtime(0)[0] == 2000:
            return NTP_2000_EPOCH_DELTA
        return NTP_UNIX_EPOCH_DELTA
