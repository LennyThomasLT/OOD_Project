import bisect
import hashlib

RING_BITS = 64
RING_SIZE = 2 ** RING_BITS


def hash64(text):
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def guest_key(c, s, salt=""):
    return f"{salt}|guest:{c}:{s}"


def node_key(node_id, j, salt=""):
    return f"{salt}|node:{node_id}:{j}"


class HashRing:
    def __init__(self, v, salt="", hash_fn=None):
        if not isinstance(v, int) or isinstance(v, bool) or v < 1:
            raise ValueError("V ต้องเป็นจำนวนเต็มตั้งแต่ 1 ขึ้นไป")
        self._v = v
        self._salt = str(salt)
        self._hash = hash_fn if hash_fn is not None else hash64
        self._points = []
        self._nodes = set()

    @property
    def v(self):
        return self._v

    @property
    def salt(self):
        return self._salt

    def nodes(self):
        return sorted(self._nodes)

    def has_node(self, node_id):
        return node_id in self._nodes

    def node_count(self):
        return len(self._nodes)

    def point_count(self):
        return len(self._points)

    def points(self):
        return list(self._points)
    
    def guest_position(self, c, s):
        return self._hash(guest_key(c, s, self._salt))

    def node_position(self, node_id, j):
        return self._hash(node_key(node_id, j, self._salt))

    def add_node(self, node_id):
        if node_id in self._nodes:
            return False, f"มีอาคาร {node_id} อยู่แล้ว ไม่เพิ่มซ้ำ"
        for j in range(self._v):
            pos = self.node_position(node_id, j)
            if not (0 <= pos < RING_SIZE):
                raise ValueError(f"ตำแหน่ง {pos} อยู่นอกช่วง 0..2^64-1")
            bisect.insort(self._points, (pos, node_id, j))
        self._nodes.add(node_id)
        return True, f"เพิ่มอาคาร {node_id} แล้ว ({self._v} จุด)"

    def remove_node(self, node_id):
        if node_id not in self._nodes:
            return False, f"ไม่พบอาคาร {node_id}"
        if len(self._nodes) == 1:
            return False, "ลบอาคารสุดท้ายไม่ได้ ระบบต้องมีอย่างน้อย 1 อาคาร"
        self._points = [p for p in self._points if p[1] != node_id]
        self._nodes.remove(node_id)
        return True, f"ลบอาคาร {node_id} แล้ว"

    def build(self, node_ids):
        if self._nodes:
            return False, "build() ใช้ได้เฉพาะตอนวงแหวนยังว่าง"
        ids = list(node_ids)
        if len(ids) == 0:
            return False, "ต้องมีอย่างน้อย 1 อาคาร"
        if len(set(ids)) != len(ids):
            return False, "มีรหัสอาคารซ้ำในรายการ"
        pts = []
        for node_id in ids:
            for j in range(self._v):
                pos = self.node_position(node_id, j)
                if not (0 <= pos < RING_SIZE):
                    raise ValueError(f"ตำแหน่ง {pos} อยู่นอกช่วง 0..2^64-1")
                pts.append((pos, node_id, j))
        pts.sort()
        self._points = pts
        self._nodes = set(ids)
        return True, f"สร้างวงแหวน {len(ids)} อาคาร {len(pts)} จุด"

    def locate_position(self, pos):
        if not self._points:
            return None
        i = bisect.bisect_left(self._points, (pos,))
        if i == len(self._points):
            i = 0
        return self._points[i][1]

    def locate(self, c, s):
        return self.locate_position(self.guest_position(c, s))
