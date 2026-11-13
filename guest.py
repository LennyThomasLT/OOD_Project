def _is_positive_int(x):
    return isinstance(x, int) and not isinstance(x, bool) and x >= 1


def validate_code(c, s):
    if not _is_positive_int(c) or not _is_positive_int(s):
        return f"รหัสแขก ({c!r}, {s!r}) ไม่ถูกต้อง: c และ s ต้องเป็นจำนวนเต็มบวก"
    return None


def room_no(c, s):
    err = validate_code(c, s)
    if err:
        raise ValueError(err)
    a, b = c - 1, s - 1
    return ((a + b) * (a + b + 1)) // 2 + b + 1


class Guest:
    __slots__ = ("c", "s", "room_no", "node_id")

    def __init__(self, c, s, node_id=None):
        self.c = c
        self.s = s
        self.room_no = room_no(c, s)
        self.node_id = node_id

    @property
    def key(self):
        return (self.c, self.s)

    def __repr__(self):
        return f"Guest(c={self.c}, s={self.s}, node={self.node_id}, room={self.room_no})"
