from hashring import guest_key, hash64


class ModNHashing:
    def __init__(self, salt="", hash_fn=None):
        self._salt = str(salt)
        self._hash = hash_fn if hash_fn is not None else hash64
        self.nodes = []

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
        self.nodes.remove(node_id)
        return True, f"ลบอาคาร {node_id} แล้ว"

    def guest_hash(self, c, s):
        return self._hash(guest_key(c, s, self._salt))

    def locate(self, c, s):
        if not self.nodes:
            return None
        return self.nodes[self.guest_hash(c, s) % len(self.nodes)]

    def assign(self, keys):
        return {(c, s): self.locate(c, s) for c, s in keys}


def moves_between(before, after):
    return [(c, s, before[(c, s)], after[(c, s)])
            for (c, s) in before if before[(c, s)] != after[(c, s)]]
