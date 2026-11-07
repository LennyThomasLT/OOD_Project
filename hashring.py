"""
hashring.py — Consistent hashing ring and node (building) selection (Member 1)

Group conventions
- Ring positions: integers from 0 to 2^64 - 1
- Hash function: SHA-256 of the UTF-8 string, first 8 bytes read as a big-endian integer
- Strings to hash (always use exactly this format):
      guest        -> f"{salt}|guest:{c}:{s}"
      virtual node -> f"{salt}|node:{node_id}:{j}"   where j = 0 .. V-1
- node_id is an int (sorts correctly and is comparable inside tuple keys)
- Operations that can fail return (ok: bool, message: str) so the menu can show the reason

Big-O (M = N x V points on the ring)
- add_node      : O(V log M) to find positions + O(V x M) to shift list elements  => O(V x M)
- remove_node   : O(M) to rebuild the list without that node's points
- locate        : O(1) to hash the guest (assuming fixed-size IDs) + O(log M) bisect
- Initial ring of N nodes via add_node one at a time: O(N x V x M) = O(M^2 / V)
  (building all at once and sorting is O(M log M) — see build())
- Space: O(M) for the point list + O(N) for the node set
"""

import bisect
import hashlib

RING_BITS = 64
RING_SIZE = 2 ** RING_BITS  # valid positions: 0 .. RING_SIZE - 1


def hash64(text):
    """SHA-256 truncated to 64 bits (first 8 bytes, big-endian) — stable across runs."""
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def guest_key(c, s, salt=""):
    return f"{salt}|guest:{c}:{s}"


def node_key(node_id, j, salt=""):
    return f"{salt}|node:{node_id}:{j}"


class HashRing:
    """
    The ring is a sorted list of tuples (pos, node_id, j).
    - Sorted by the key (position, node_id, j) as required by rule 4.3(4),
      so colliding points are all kept.
    - A guest belongs to the first point with pos >= the guest's position;
      if there is none, wrap around to the first point of the ring.

    hash_fn: optional text -> int function used instead of hash64
             (for the section 9.1 test, where positions are fixed by hand).
    """

    def __init__(self, v, salt="", hash_fn=None):
        if not isinstance(v, int) or isinstance(v, bool) or v < 1:
            raise ValueError("V ต้องเป็นจำนวนเต็มตั้งแต่ 1 ขึ้นไป")
        self._v = v
        self._salt = str(salt)
        self._hash = hash_fn if hash_fn is not None else hash64
        self._points = []      # sorted list of (pos, node_id, j)
        self._nodes = set()    # node IDs currently on the ring

    # ---------- basic info ----------
    @property
    def v(self):
        return self._v

    @property
    def salt(self):
        return self._salt

    def nodes(self):
        """All node IDs in ascending order (Member 2 uses this to count nodes with 0 guests)."""
        return sorted(self._nodes)

    def has_node(self, node_id):
        return node_id in self._nodes

    def node_count(self):
        return len(self._nodes)

    def point_count(self):
        """Number of points on the ring, M = N x V."""
        return len(self._points)

    def points(self):
        """Copy of all points (for tests/display) — the internal list is never exposed."""
        return list(self._points)

    # ---------- positions ----------
    def guest_position(self, c, s):
        return self._hash(guest_key(c, s, self._salt))

    def node_position(self, node_id, j):
        return self._hash(node_key(node_id, j, self._salt))

    # ---------- add / remove nodes ----------
    def add_node(self, node_id):
        """Insert only the new node's V points; existing points are untouched. Returns (ok, message)."""
        if node_id in self._nodes:
            return False, f"มีอาคาร {node_id} อยู่แล้ว ไม่เพิ่มซ้ำ"
        for j in range(self._v):
            pos = self.node_position(node_id, j)
            if not (0 <= pos < RING_SIZE):
                raise ValueError(f"ตำแหน่ง {pos} อยู่นอกช่วง 0..2^64-1")
            bisect.insort(self._points, (pos, node_id, j))   # O(log M) search + O(M) shift
        self._nodes.add(node_id)
        return True, f"เพิ่มอาคาร {node_id} แล้ว ({self._v} จุด)"

    def remove_node(self, node_id):
        """Remove every point of that node; other points are untouched. Returns (ok, message)."""
        if node_id not in self._nodes:
            return False, f"ไม่พบอาคาร {node_id}"
        if len(self._nodes) == 1:
            return False, "ลบอาคารสุดท้ายไม่ได้ ระบบต้องมีอย่างน้อย 1 อาคาร"
        self._points = [p for p in self._points if p[1] != node_id]   # O(M)
        self._nodes.remove(node_id)
        return True, f"ลบอาคาร {node_id} แล้ว"

    def build(self, node_ids):
        """
        Build the initial ring in one go: collect all points, then sort once — O(M log M).
        Faster than calling add_node per node. Only allowed while the ring is empty.
        """
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

    # ---------- node selection ----------
    def locate_position(self, pos):
        """Owner of the first point with position >= pos, wrapping to the first point; None if the ring is empty."""
        if not self._points:
            return None
        # (pos,) is smaller than every tuple (pos, node_id, j), so this finds the first point with position >= pos
        i = bisect.bisect_left(self._points, (pos,))
        if i == len(self._points):
            i = 0   # past the last point -> wrap to the start of the ring
        return self._points[i][1]

    def locate(self, c, s):
        """Compute guest (c, s)'s node from the current ring, without using any stored result."""
        return self.locate_position(self.guest_position(c, s))
