import time
import threading
from hashids import Hashids

from ..config import settings


hashids = Hashids(salt=settings.HASHIDS_SALT, min_length=settings.HASHIDS_MIN_LENGTH)


class SnowflakeGenerator:
    def __init__(self, worker_id: int = 1, datacenter_id: int = 1):
        self.worker_id = worker_id
        self.datacenter_id = datacenter_id
        self.sequence = 0
        self.last_timestamp = -1
        self.lock = threading.Lock()

        self.worker_id_bits = 5
        self.datacenter_id_bits = 5
        self.sequence_bits = 12

        self.max_worker_id = -1 ^ (-1 << self.worker_id_bits)
        self.max_datacenter_id = -1 ^ (-1 << self.datacenter_id_bits)
        self.sequence_mask = -1 ^ (-1 << self.sequence_bits)

        self.worker_id_shift = self.sequence_bits
        self.datacenter_id_shift = self.sequence_bits + self.worker_id_bits
        self.timestamp_shift = self.sequence_bits + self.worker_id_bits + self.datacenter_id_bits
        self.twepoch = 1704067200000

    def _gen_timestamp(self) -> int:
        return int(time.time() * 1000)

    def _next_millis(self, last_timestamp: int) -> int:
        timestamp = self._gen_timestamp()
        while timestamp <= last_timestamp:
            timestamp = self._gen_timestamp()
        return timestamp

    def next_id(self) -> int:
        with self.lock:
            timestamp = self._gen_timestamp()

            if timestamp < self.last_timestamp:
                raise RuntimeError("时钟回拨，拒绝生成ID")

            if timestamp == self.last_timestamp:
                self.sequence = (self.sequence + 1) & self.sequence_mask
                if self.sequence == 0:
                    timestamp = self._next_millis(self.last_timestamp)
            else:
                self.sequence = 0

            self.last_timestamp = timestamp

            snowflake_id = (
                ((timestamp - self.twepoch) << self.timestamp_shift)
                | (self.datacenter_id << self.datacenter_id_shift)
                | (self.worker_id << self.worker_id_shift)
                | self.sequence
            )
            return snowflake_id


_id_generator = SnowflakeGenerator()


def generate_id() -> int:
    return _id_generator.next_id()


def encode_id(id: int) -> str:
    return hashids.encode(id)


def decode_id(hashid: str) -> int | None:
    try:
        decoded = hashids.decode(hashid)
        return decoded[0] if decoded else None
    except Exception:
        return None
