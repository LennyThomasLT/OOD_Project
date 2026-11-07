"""
modn.py — hash mod N, the baseline compared with consistent hashing (Member 3)

Rules (section 7.1)
- Keep node IDs in the order they were added (a list).
- A guest goes to nodes[H(guest) mod N].
- Adding a node appends to the end; removing a node deletes that ID and keeps the order of the rest.
- Moves are compared by real node ID, not by list index.
- H is the same 64-bit guest hash as the ring (same string format and salt), so both methods
  see exactly the same guests and hash values in each round.

Big-O (K guests, N nodes)
- locate            : O(1) hash + O(1) index
- add_node          : O(N) duplicate check (`in` on a list) + O(1) append
- remove_node       : O(N) list.remove keeps the order
- after a change, finding movers means recomputing all K guests: O(K)
- Space: O(N) for the node list. The extra space of the FORMULA is O(1), but the
  program still stores the N node IDs and the K guests (a common mistake in section 8.1).
"""

from hashring import guest_key, hash64


class ModNHashing:
    def __init__(self, salt="", hash_fn=None):
        self._salt = str(salt)
        self._hash = hash_fn if hash_fn is not None else hash64
        self.nodes = []                 # node IDs in the order they were added

    def build(self, node_ids):
        ids = list(node_ids)
        if not ids:
            return False, "ต้องมีอย่างน้อย 1 อาคาร"
        if len(set(ids)) != len(ids):
            return False, "มีรหัสอาคารซ้ำในรายการ"
        if self.nodes:
            return False, "build() ใช้ได้เฉพาะตอนยังไม่มีอาคาร"
        self.nodes = ids
        return True, f"สร้าง {len(ids)} อาคาร"

    def add_node(self, node_id):
        if node_id in self.nodes:
            return False, f"มีอาคาร {node_id} อยู่แล้ว ไม่เพิ่มซ้ำ"
        self.nodes.append(node_id)
        return True, f"เพิ่มอาคาร {node_id} แล้ว"

    def remove_node(self, node_id):
        if node_id not in self.nodes:
            return False, f"ไม่พบอาคาร {node_id}"
        if len(self.nodes) == 1:
            return False, "ลบอาคารสุดท้ายไม่ได้ ระบบต้องมีอย่างน้อย 1 อาคาร"
        self.nodes.remove(node_id)      # keeps the order of the remaining IDs
        return True, f"ลบอาคาร {node_id} แล้ว"

    def guest_hash(self, c, s):
        return self._hash(guest_key(c, s, self._salt))

    def locate(self, c, s):
        """Real node ID of guest (c, s), or None if there are no nodes."""
        if not self.nodes:
            return None
        return self.nodes[self.guest_hash(c, s) % len(self.nodes)]

    def assign(self, keys):
        """{(c, s): node_id} for every guest code in keys."""
        return {(c, s): self.locate(c, s) for c, s in keys}


def moves_between(before, after):
    """
    Guests whose node differs between two assignments {(c, s): node_id}.
    Returns a list of (c, s, old_node, new_node), compared by real node ID.
    """
    return [(c, s, before[(c, s)], after[(c, s)])
            for (c, s) in before if before[(c, s)] != after[(c, s)]]
