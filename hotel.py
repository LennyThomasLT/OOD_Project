import math
import time

from guest import Guest, room_no, validate_code
from hashring import HashRing


class HotelSystem:
    def __init__(self, v, salt="", hash_fn=None):
        self.ring = HashRing(v, salt=salt, hash_fn=hash_fn)
        self._guests = {}
        self._room_index = {}

    def setup(self, n, channels, guests_per_channel, node_ids=None):
        if self.ring.node_count() > 0 or self._guests:
            return False, "ระบบเริ่มต้นไปแล้ว"
        if not isinstance(n, int) or isinstance(n, bool) or n < 1:
            return False, "จำนวนอาคาร N ต้องเป็นจำนวนเต็มตั้งแต่ 1 ขึ้นไป"
        if not isinstance(channels, int) or isinstance(channels, bool) or channels < 0:
            return False, "จำนวนช่องทางต้องเป็นจำนวนเต็มไม่ติดลบ"
        if isinstance(guests_per_channel, list):
            counts = guests_per_channel
            if len(counts) != channels:
                return False, "จำนวนรายการแขกต่อช่องทางไม่เท่ากับจำนวนช่องทาง"
        else:
            counts = [guests_per_channel] * channels
        for k in counts:
            if not isinstance(k, int) or isinstance(k, bool) or k < 0:
                return False, "จำนวนแขกต่อช่องทางต้องเป็นจำนวนเต็มไม่ติดลบ"

        ids = list(node_ids) if node_ids is not None else list(range(1, n + 1))
        if len(ids) != n:
            return False, "จำนวนรหัสอาคารไม่เท่ากับ N"
        ok, msg = self.ring.build(ids)
        if not ok:
            return False, msg
        for c, k in enumerate(counts, start=1):
            self.add_group(c, 1, k)
        return True, f"เริ่มระบบแล้ว: {n} อาคาร, V = {self.ring.v}, แขก {len(self._guests)} คน"

    def guest_count(self):
        return len(self._guests)

    def has_guest(self, c, s):
        return (c, s) in self._guests

    def get_guest(self, c, s):
        return self._guests.get((c, s))

    def all_guests(self):
        return list(self._guests.values())

    def _insert(self, guest):
        addr = (guest.node_id, guest.room_no)
        if addr in self._room_index:
            raise RuntimeError(f"ห้อง {addr} มีผู้พักอยู่แล้ว")
        self._guests[guest.key] = guest
        self._room_index[addr] = guest.key

    def _delete(self, key):
        guest = self._guests.pop(key)
        del self._room_index[(guest.node_id, guest.room_no)]
        return guest

    def _relocate(self, key, new_node_id):
        guest = self._guests[key]
        del self._room_index[(guest.node_id, guest.room_no)]
        guest.node_id = new_node_id
        self._room_index[(new_node_id, guest.room_no)] = key

    def is_consistent(self):
        if len(self._guests) != len(self._room_index):
            return False
        for key, g in self._guests.items():
            if self._room_index.get((g.node_id, g.room_no)) != key:
                return False
            if g.room_no != room_no(g.c, g.s):
                return False
        return True

    def add_guest(self, c, s):
        err = validate_code(c, s)
        if err:
            return False, err
        if (c, s) in self._guests:
            return False, f"มีแขกรหัส ({c}, {s}) อยู่แล้ว ไม่เพิ่มซ้ำ"
        node = self.ring.locate(c, s)
        if node is None:
            return False, "ยังไม่มีอาคารในระบบ"
        g = Guest(c, s, node)
        self._insert(g)
        return True, f"เพิ่มแขก ({c}, {s}) -> อาคาร {node} ห้อง {g.room_no}"

    def add_group(self, c, s_start, count):
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            return False, "จำนวนแขกต้องเป็นจำนวนเต็มไม่ติดลบ"
        if count == 0:
            return True, "จำนวนแขกเป็น 0 ไม่มีการเปลี่ยนแปลง"
        err = validate_code(c, s_start)
        if err:
            return False, err
        if self.ring.node_count() == 0:
            return False, "ยังไม่มีอาคารในระบบ"

        dup = [s for s in range(s_start, s_start + count) if (c, s) in self._guests]
        if dup:
            shown = ", ".join(f"({c}, {s})" for s in dup[:5])
            more = f" และอีก {len(dup) - 5} รหัส" if len(dup) > 5 else ""
            return False, f"ปฏิเสธทั้งกลุ่ม: มีรหัสซ้ำ {len(dup)} รหัส ได้แก่ {shown}{more}"

        for s in range(s_start, s_start + count):
            self._insert(Guest(c, s, self.ring.locate(c, s)))
        return True, f"เพิ่มแขกช่องทาง {c} ลำดับ {s_start}..{s_start + count - 1} ({count} คน)"

    def remove_guest(self, c, s):
        if (c, s) not in self._guests:
            return False, f"ไม่พบแขกรหัส ({c}, {s})"
        g = self._delete((c, s))
        return True, f"นำแขก ({c}, {s}) ออกจากอาคาร {g.node_id} ห้อง {g.room_no} แล้ว"

    def find_by_guest(self, c, s):
        g = self._guests.get((c, s))
        return None if g is None else (g.node_id, g.room_no)

    def find_by_room(self, node_id, room):
        return self._room_index.get((node_id, room))

    def locate(self, c, s):
        return self.ring.locate(c, s)

    def list_rooms(self):
        rows = [(g.node_id, g.room_no, g.c, g.s) for g in self._guests.values()]
        rows.sort()
        return rows

    def load_stats(self):
        counts = {node: 0 for node in self.ring.nodes()}
        for g in self._guests.values():
            counts[g.node_id] = counts.get(g.node_id, 0) + 1

        k = len(self._guests)
        n = len(counts)
        if k == 0 or n == 0:
            return {"counts": counts, "K": 0, "N": n, "max": 0, "min": 0,
                    "mean": 0, "std": 0, "cv": None}
        values = list(counts.values())
        mean = k / n
        std = math.sqrt(sum((x - mean) ** 2 for x in values) / n)
        return {"counts": counts, "K": k, "N": n, "max": max(values), "min": min(values),
                "mean": mean, "std": std, "cv": std / mean}

    def add_node(self, node_id):
        return self._change_nodes("add", node_id)

    def remove_node(self, node_id):
        return self._change_nodes("remove", node_id)

    def _change_nodes(self, action, node_id):
        k = len(self._guests)

        t0 = time.perf_counter()
        if action == "add":
            ok, msg = self.ring.add_node(node_id)
        else:
            ok, msg = self.ring.remove_node(node_id)
        t1 = time.perf_counter()
        if not ok:
            return MoveReport(False, msg, action, node_id, k, [])

        moves = []
        for g in self._guests.values():
            new_node = self.ring.locate(g.c, g.s)
            if new_node != g.node_id:
                moves.append((g.c, g.s, g.node_id, new_node, g.room_no))
        t2 = time.perf_counter()

        for c, s, _old, new_node, _room in moves:
            self._relocate((c, s), new_node)
        t3 = time.perf_counter()

        return MoveReport(True, msg, action, node_id, k, moves,
                          times={"ring": t1 - t0, "find": t2 - t1, "update": t3 - t2})


class MoveReport:
    def __init__(self, ok, message, action, node_id, k_before, moves, times=None):
        self.ok = ok
        self.message = message
        self.action = action
        self.node_id = node_id
        self.k = k_before
        self.moves = moves
        self.times = times or {"ring": 0.0, "find": 0.0, "update": 0.0}

    @property
    def count(self):
        return len(self.moves)

    @property
    def rate(self):
        return self.count / self.k if self.k > 0 else None

    def summary(self):
        if not self.ok:
            return f"ไม่สำเร็จ: {self.message}"
        verb = "เพิ่ม" if self.action == "add" else "ลบ"
        if self.k == 0:
            return f"{verb}อาคาร {self.node_id} แล้ว: ย้าย 0 คน (ไม่คำนวณอัตราเพราะไม่มีแขก)"
        return (f"{verb}อาคาร {self.node_id} แล้ว: ย้าย {self.count} จาก {self.k} คน "
                f"(อัตรา {self.rate:.4f} = {self.rate * 100:.2f}%)")

    def __repr__(self):
        return f"MoveReport(ok={self.ok}, action={self.action!r}, node={self.node_id}, count={self.count}, K={self.k})"
