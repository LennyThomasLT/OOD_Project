"""
guest.py — Guest data and room numbers (Member 2)

Room number (rule 4.2): Cantor pairing on the guest code (c, s)
    a = c - 1, b = s - 1
    room_no = ((a + b) * (a + b + 1)) // 2 + b + 1
Integer arithmetic only (// is integer division, never float).

Why it never repeats (summary for the report):
    Let d = a + b (the diagonal). Diagonal d holds d + 1 pairs, and b runs 0..d on it.
    All pairs on diagonals 0..d-1 come first: there are d(d+1)/2 of them.
    So room_no - 1 = d(d+1)/2 + b, where 0 <= b <= d.
    Given room_no we can recover d (largest d with d(d+1)/2 <= room_no - 1),
    then b, then a = d - b — so the function is one-to-one (injective):
    two different codes can never get the same room number.

Big-O: room_no is O(1) assuming fixed-size codes (Python ints can grow, so
the true cost grows with the number of digits).
"""


def _is_positive_int(x):
    return isinstance(x, int) and not isinstance(x, bool) and x >= 1


def validate_code(c, s):
    """Return an error message if (c, s) is not a valid guest code, else None."""
    if not _is_positive_int(c) or not _is_positive_int(s):
        return f"รหัสแขก ({c!r}, {s!r}) ไม่ถูกต้อง: c และ s ต้องเป็นจำนวนเต็มบวก"
    return None


def room_no(c, s):
    """Cantor pairing room number for guest (c, s). Raises ValueError on an invalid code."""
    err = validate_code(c, s)
    if err:
        raise ValueError(err)
    a, b = c - 1, s - 1
    return ((a + b) * (a + b + 1)) // 2 + b + 1


class Guest:
    """One guest: code (c, s), room number (from the code only) and current node."""

    __slots__ = ("c", "s", "room_no", "node_id")

    def __init__(self, c, s, node_id=None):
        self.c = c
        self.s = s
        self.room_no = room_no(c, s)   # never changes, even when the guest moves node
        self.node_id = node_id         # changes only when nodes are added/removed

    @property
    def key(self):
        return (self.c, self.s)

    def __repr__(self):
        return f"Guest(c={self.c}, s={self.s}, node={self.node_id}, room={self.room_no})"
