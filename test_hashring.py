import hashlib
import os
import subprocess
import sys

from hashring import HashRing, RING_SIZE, guest_key, hash64, node_key
from testkit import ReportTestCase, main


A, B, C, D = 1, 2, 3, 4
NAME = {A: "A", B: "B", C: "C", D: "D"}


GUESTS = [(1, 1), (1, 2), (1, 3), (1, 4), (1, 5), (1, 6), (1, 7)]
GUEST_POS = [10, 20, 25, 35, 50, 70, 90]

TABLE = {node_key(A, 0): 20, node_key(B, 0): 50, node_key(C, 0): 80, node_key(D, 0): 35}
for (c, s), p in zip(GUESTS, GUEST_POS):
    TABLE[guest_key(c, s)] = p


def table_hash(text):
    return TABLE[text]


def ring_abc():
    ring = HashRing(1, hash_fn=table_hash)
    for n in (A, B, C):
        ring.add_node(n)
    return ring


def owners(ring):
    return [NAME[ring.locate(c, s)] for c, s in GUESTS]


class TestHashFunction(ReportTestCase):
    def test_sha256_first_8_bytes(self):
        text = "|guest:1:1"
        expected = int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:8], "big")
        self.check(f"hash64({text!r})", expected, hash64(text))

    def test_range(self):
        out_of_range = [i for i in range(1000) if not (0 <= hash64(f"x{i}") < RING_SIZE)]
        self.check("values out of range among 1,000 hashes", [], out_of_range)

    def test_same_value_across_runs(self):
        here = os.path.dirname(os.path.abspath(__file__))
        code = "from hashring import hash64; print(hash64('|guest:3:7'))"
        results = []
        for seed in ("1", "2", "999"):
            env = dict(os.environ, PYTHONHASHSEED=seed)
            r = subprocess.run([sys.executable, "-c", code], cwd=here, env=env,
                               capture_output=True, text=True, check=True)
            results.append(int(r.stdout.strip()))
        self.check("hash64('|guest:3:7') in 3 separate runs (PYTHONHASHSEED 1, 2, 999)",
                   [hash64("|guest:3:7")] * 3, results)

    def test_key_formats(self):
        self.check("guest_key(1, 2, salt='0')", "0|guest:1:2", guest_key(1, 2, "0"))
        self.check("node_key(1, 2, salt='0')", "0|node:1:2", node_key(1, 2, "0"))


class TestExample91(ReportTestCase):
    def test_initial(self):
        self.check("owners of guests at 10, 20, 25, 35, 50, 70, 90",
                   ["A", "A", "B", "B", "B", "C", "A"], owners(ring_abc()))

    def test_add_D(self):
        ring = ring_abc()
        before = owners(ring)
        ok, msg = ring.add_node(D)
        self.check("add_node(D) succeeds", True, ok)
        after = owners(ring)
        self.check("owners after adding D", ["A", "A", "D", "D", "B", "C", "A"], after)
        moved = [(b, a) for b, a in zip(before, after) if b != a]
        self.check("number of guests that moved", 2, len(moved))
        self.check("destination of every mover (must be the new node)",
                   ["D"] * len(moved), [a for _, a in moved])

    def test_remove_B(self):
        ring = ring_abc()
        before = owners(ring)
        ok, msg = ring.remove_node(B)
        self.check("remove_node(B) succeeds", True, ok)
        after = owners(ring)
        self.check("owners after removing B", ["A", "A", "C", "C", "C", "C", "A"], after)
        moved = [(b, a) for b, a in zip(before, after) if b != a]
        self.check("number of guests that moved", 3, len(moved))
        self.check("origin of every mover (only B's guests may move)",
                   ["B"] * len(moved), [b for b, _ in moved])


class TestLocate(ReportTestCase):
    def test_exact_point(self):
        ring = ring_abc()
        self.check("locate_position(20)", "A", NAME[ring.locate_position(20)])
        self.check("locate_position(50)", "B", NAME[ring.locate_position(50)])

    def test_between_points(self):
        ring = ring_abc()
        self.check("locate_position(21)", "B", NAME[ring.locate_position(21)])
        self.check("locate_position(79)", "C", NAME[ring.locate_position(79)])

    def test_wrap_around(self):
        ring = ring_abc()
        self.check("locate_position(81)", "A", NAME[ring.locate_position(81)])
        self.check("locate_position(2^64 - 1)", "A", NAME[ring.locate_position(RING_SIZE - 1)])
        self.check("locate_position(0)", "A", NAME[ring.locate_position(0)])

    def test_empty_ring(self):
        self.check("HashRing(1).locate(1, 1)", None, HashRing(1).locate(1, 1))

    def test_vnode_collision(self):
        tbl = {node_key(7, 0): 40, node_key(3, 0): 40, node_key(9, 0): 60, guest_key(1, 1): 40}
        ring = HashRing(1, hash_fn=lambda t: tbl[t])
        for n in (7, 3, 9):
            ring.add_node(n)
        self.check("points on the ring (nodes 7 and 3 both at 40)",
                   [(40, 3, 0), (40, 7, 0), (60, 9, 0)], ring.points())
        self.check("guest at 40 goes to the first point in key order", 3, ring.locate(1, 1))
        ring.remove_node(3)
        self.check("after removing node 3, guest at 40 goes to node 7", 7, ring.locate(1, 1))

    def test_guests_same_position(self):
        tbl = {node_key(1, 0): 50, guest_key(1, 1): 30, guest_key(2, 5): 30}
        ring = HashRing(1, hash_fn=lambda t: tbl[t])
        ring.add_node(1)
        self.check("nodes of guests (1,1) and (2,5), both at 30",
                   [1, 1], [ring.locate(1, 1), ring.locate(2, 5)])


class TestAddRemove(ReportTestCase):
    def test_v_points_per_node(self):
        ring = HashRing(32, salt="0")
        for n in range(1, 11):
            ring.add_node(n)
        self.check("point count with N=10, V=32", 320, ring.point_count())
        self.check("points are sorted", True, ring.points() == sorted(ring.points()))
        ring.remove_node(4)
        self.check("point count after removing node 4", 288, ring.point_count())
        self.check("points of node 4 left on the ring", 0,
                   sum(1 for p in ring.points() if p[1] == 4))

    def test_add_keeps_old_points(self):
        ring = HashRing(8)
        for n in (1, 2, 3):
            ring.add_node(n)
        old = set(ring.points())
        ring.add_node(4)
        self.check("all old points still present", True, old.issubset(set(ring.points())))

    def test_remove_keeps_other_points(self):
        ring = HashRing(8)
        for n in (1, 2, 3):
            ring.add_node(n)
        expected = sorted(p for p in ring.points() if p[1] != 2)
        ring.remove_node(2)
        self.check("points after removing node 2 (count)", len(expected), ring.point_count())
        self.check("points after removing node 2 are unchanged", expected, ring.points())

    def test_build_same_as_add(self):
        r1, r2 = HashRing(16, salt="1"), HashRing(16, salt="1")
        for n in range(1, 6):
            r1.add_node(n)
        r2.build(range(1, 6))
        self.check("rings are identical", True, r1.points() == r2.points())

    def test_salt(self):
        p0a = HashRing(4, "0").guest_position(1, 1)
        p0b = HashRing(4, "0").guest_position(1, 1)
        p1 = HashRing(4, "1").guest_position(1, 1)
        self.check("salt '0' twice gives the same position", True, p0a == p0b)
        self.check("salt '0' vs salt '1' gives different positions", True, p0a != p1)

    def test_nodes_sorted(self):
        ring = HashRing(2)
        for n in (10, 2, 7):
            ring.add_node(n)
        self.check("nodes() after adding 10, 2, 7", [2, 7, 10], ring.nodes())


class TestEdgeCases(ReportTestCase):
    def test_add_duplicate(self):
        ring = ring_abc()
        before = ring.points()
        ok, msg = ring.add_node(A)
        self.check("add_node(A) again -> ok", False, ok)
        self.note("Message", msg)
        self.check("ring unchanged", before, ring.points())

    def test_remove_missing(self):
        ring = ring_abc()
        before = ring.points()
        ok, msg = ring.remove_node(99)
        self.check("remove_node(99) -> ok", False, ok)
        self.note("Message", msg)
        self.check("ring unchanged", before, ring.points())

    def test_remove_last(self):
        ring = HashRing(4)
        ring.add_node(1)
        ok, msg = ring.remove_node(1)
        self.check("remove_node(1) when it is the only node -> ok", False, ok)
        self.note("Message", msg)
        self.check("nodes left", [1], ring.nodes())
        self.check("points left", 4, ring.point_count())

    def test_build_bad_input(self):
        self.check("build([]) -> ok", False, HashRing(2).build([])[0])
        self.check("build([1, 1]) -> ok", False, HashRing(2).build([1, 1])[0])
        self.check("build([5]) on a ring that already has nodes -> ok", False, ring_abc().build([5])[0])

    def test_invalid_v(self):
        rejected = []
        for bad in (0, -1, 1.5, "3", True):
            try:
                HashRing(bad)
            except ValueError:
                rejected.append(bad)
        self.check("values of V that were rejected", [0, -1, 1.5, "3", True], rejected)


TEST_CLASSES = [TestHashFunction, TestExample91, TestLocate, TestAddRemove, TestEdgeCases]

if __name__ == "__main__":
    main("HashRing tests (Member 1)", TEST_CLASSES)
