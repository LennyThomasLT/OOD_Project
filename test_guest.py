"""
test_guest.py — Member 2 tests (guests, room numbers, indexes, search, room list, load stats)

Run:  python test_guest.py
      (also works with: python -m unittest test_guest)
"""

from guest import Guest, room_no
from hashring import guest_key, node_key
from hotel import HotelSystem
from testkit import ReportTestCase, main


def make_hotel(n=10, v=32, channels=3, per_channel=50, salt="0"):
    h = HotelSystem(v, salt=salt)
    h.setup(n, channels, per_channel)
    return h


def snapshot(h):
    """{(c, s): (node_id, room_no)} for every guest."""
    return {g.key: (g.node_id, g.room_no) for g in h.all_guests()}


# ======================================================================
class TestRoomNumber(ReportTestCase):
    def test_table(self):
        """Room numbers match the table in rule 4.2"""
        codes = [(1, 1), (2, 1), (1, 2), (3, 1), (2, 2)]
        self.check("room_no for (1,1), (2,1), (1,2), (3,1), (2,2)",
                   [1, 2, 3, 4, 5], [room_no(c, s) for c, s in codes])

    def test_unique(self):
        """Different guest codes never get the same room number"""
        rooms = [room_no(c, s) for c in range(1, 101) for s in range(1, 101)]
        self.check("distinct room numbers among 100 x 100 = 10,000 codes", 10000, len(set(rooms)))

    def test_integer_only(self):
        """Room numbers use integer arithmetic only (exact for huge codes)"""
        big = 10 ** 20
        a = b = big - 1
        expected = ((a + b) * (a + b + 1)) // 2 + b + 1
        r = room_no(big, big)
        self.check("type of room_no(10^20, 10^20)", "int", type(r).__name__)
        self.check("value of room_no(10^20, 10^20) is exact", expected, r)

    def test_invalid_codes(self):
        """Invalid codes are rejected (c and s must be positive integers)"""
        bad = [(0, 1), (1, 0), (-1, 1), (1.5, 1), ("1", 1), (True, 1)]
        rejected = []
        for c, s in bad:
            try:
                room_no(c, s)
            except ValueError:
                rejected.append((c, s))
        self.check("codes that were rejected", bad, rejected)

    def test_room_independent_of_node(self):
        """Room number depends on the code only, not on the node"""
        self.check("Guest(2, 3, node=1).room_no == Guest(2, 3, node=9).room_no",
                   Guest(2, 3, 1).room_no, Guest(2, 3, 9).room_no)


# ======================================================================
class TestSetup(ReportTestCase):
    def test_setup_counts(self):
        """setup(N=10, 3 channels, 50 guests each) creates 150 guests on 10 nodes"""
        h = make_hotel()
        self.check("number of guests K", 150, h.guest_count())
        self.check("node IDs", list(range(1, 11)), h.ring.nodes())
        self.check("sequence numbers of channel 2", list(range(1, 51)),
                   sorted(s for c, s in snapshot(h) if c == 2))
        self.check("indexes consistent", True, h.is_consistent())

    def test_setup_list_counts(self):
        """setup with a different number of guests per channel"""
        h = HotelSystem(8)
        ok, _ = h.setup(4, 3, [5, 0, 7])
        self.check("setup succeeds", True, ok)
        self.check("number of guests K", 12, h.guest_count())
        self.check("guests of channel 2", 0, sum(1 for c, _ in snapshot(h) if c == 2))

    def test_setup_bad_input(self):
        """setup rejects invalid input"""
        self.check("N = 0 -> ok", False, HotelSystem(4).setup(0, 1, 5)[0])
        self.check("negative guests per channel -> ok", False, HotelSystem(4).setup(3, 1, -5)[0])
        self.check("list length != channels -> ok", False, HotelSystem(4).setup(3, 2, [1])[0])
        h = make_hotel()
        self.check("calling setup twice -> ok", False, h.setup(5, 1, 1)[0])


# ======================================================================
class TestAddRemove(ReportTestCase):
    def test_add_guest(self):
        """Add one guest: node is computed from the ring, room from the code"""
        h = make_hotel(channels=0)
        ok, msg = h.add_guest(4, 7)
        self.check("add_guest(4, 7) succeeds", True, ok)
        self.note("Message", msg)
        self.check("find_by_guest(4, 7)", (h.locate(4, 7), room_no(4, 7)), h.find_by_guest(4, 7))

    def test_old_guests_do_not_move(self):
        """Rule 9.2(1) — adding guests (old and new channels) never moves existing guests"""
        h = make_hotel()
        before = snapshot(h)
        h.add_group(1, 51, 100)      # existing channel
        h.add_group(11, 1, 100)      # new channel
        h.add_guest(2, 999)
        after = snapshot(h)
        changed = [k for k in before if after.get(k) != before[k]]
        self.check("guests added", 150 + 201, h.guest_count())
        self.check("old guests whose address changed", [], changed)

    def test_duplicate_guest(self):
        """Edge case — adding an existing code is rejected, data unchanged"""
        h = make_hotel()
        before = snapshot(h)
        ok, msg = h.add_guest(1, 1)
        self.check("add_guest(1, 1) again -> ok", False, ok)
        self.note("Message", msg)
        self.check("data unchanged", before, snapshot(h))

    def test_group_partial_duplicate(self):
        """Rule 4.1(3) — a group with even one duplicate is rejected entirely"""
        h = HotelSystem(8)
        h.setup(4, 1, 5)                 # (1,1)..(1,5)
        before = snapshot(h)
        ok, msg = h.add_group(1, 4, 5)   # (1,4)..(1,8): 4 and 5 already exist
        self.check("add_group(1, 4, 5) -> ok", False, ok)
        self.note("Message", msg)
        self.check("data unchanged (6, 7, 8 were NOT added)", before, snapshot(h))

    def test_group_count_zero_and_negative(self):
        """Group with count 0 changes nothing; negative count is rejected"""
        h = make_hotel()
        before = snapshot(h)
        ok0, msg0 = h.add_group(5, 1, 0)
        self.check("add_group(5, 1, 0) -> ok", True, ok0)
        self.note("Message", msg0)
        okn, msgn = h.add_group(5, 1, -3)
        self.check("add_group(5, 1, -3) -> ok", False, okn)
        self.note("Message", msgn)
        self.check("data unchanged", before, snapshot(h))

    def test_invalid_guest_code(self):
        """Edge case — invalid guest codes are rejected without crashing"""
        h = make_hotel()
        results = [h.add_guest(0, 1)[0], h.add_guest(1, -2)[0], h.add_group(1, 0, 3)[0]]
        self.check("add_guest(0,1), add_guest(1,-2), add_group(1,0,3) -> ok", [False] * 3, results)
        self.check("number of guests unchanged", 150, h.guest_count())

    def test_no_nodes(self):
        """Edge case — adding a guest before any node exists is rejected"""
        h = HotelSystem(4)
        ok, msg = h.add_guest(1, 1)
        self.check("add_guest on a system with no nodes -> ok", False, ok)
        self.note("Message", msg)

    def test_remove_guest(self):
        """Remove a guest: gone from both indexes"""
        h = make_hotel()
        node, room = h.find_by_guest(2, 10)
        ok, msg = h.remove_guest(2, 10)
        self.check("remove_guest(2, 10) -> ok", True, ok)
        self.note("Message", msg)
        self.check("number of guests", 149, h.guest_count())
        self.check("find_by_guest(2, 10)", None, h.find_by_guest(2, 10))
        self.check(f"find_by_room({node}, {room})", None, h.find_by_room(node, room))
        self.check("indexes consistent", True, h.is_consistent())

    def test_remove_missing(self):
        """Edge case — removing a guest that does not exist is rejected, data unchanged"""
        h = make_hotel()
        before = snapshot(h)
        ok, msg = h.remove_guest(9, 9)
        self.check("remove_guest(9, 9) -> ok", False, ok)
        self.note("Message", msg)
        self.check("data unchanged", before, snapshot(h))

    def test_readd_after_remove(self):
        """Rule 4.1(4) — re-adding a removed code is a new check-in computed from the current ring"""
        h = make_hotel()
        h.remove_guest(3, 3)
        ok, _ = h.add_guest(3, 3)
        self.check("add_guest(3, 3) after removal -> ok", True, ok)
        self.check("address", (h.locate(3, 3), room_no(3, 3)), h.find_by_guest(3, 3))


# ======================================================================
class TestSearch(ReportTestCase):
    def test_two_way_search(self):
        """Search by guest code and by address give matching answers"""
        h = make_hotel()
        node, room = h.find_by_guest(3, 25)
        self.check("find_by_room of the address of (3, 25)", (3, 25), h.find_by_room(node, room))

    def test_search_matches_ring(self):
        """Stored node equals the node computed from the ring (no ring change)"""
        h = make_hotel()
        wrong = [g.key for g in h.all_guests() if g.node_id != h.locate(g.c, g.s)]
        self.check("guests whose stored node differs from the ring", [], wrong)

    def test_not_found(self):
        """Search that finds nothing returns None instead of crashing"""
        h = make_hotel()
        self.check("find_by_guest(99, 99)", None, h.find_by_guest(99, 99))
        self.check("find_by_room(1, 10**9)", None, h.find_by_room(1, 10 ** 9))
        self.check("find_by_room(77, 1) (node does not exist)", None, h.find_by_room(77, 1))

    def test_relocate_keeps_indexes_in_sync(self):
        """_relocate (used by Member 3) updates both indexes and keeps room_no"""
        h = make_hotel()
        old_node, room = h.find_by_guest(1, 1)
        new_node = 1 if old_node != 1 else 2
        h._relocate((1, 1), new_node)
        self.check("find_by_guest(1, 1)", (new_node, room), h.find_by_guest(1, 1))
        self.check(f"find_by_room(old node {old_node}, {room})", None, h.find_by_room(old_node, room))
        self.check(f"find_by_room(new node {new_node}, {room})", (1, 1), h.find_by_room(new_node, room))
        self.check("indexes consistent", True, h.is_consistent())


# ======================================================================
class TestRoomList(ReportTestCase):
    def test_sorted(self):
        """Room list is sorted by node_id, then room_no as numbers"""
        h = make_hotel(channels=12, per_channel=12)
        rows = h.list_rooms()
        self.check("rows in the list", h.guest_count(), len(rows))
        keys = [(r[0], r[1]) for r in rows]
        self.check("sorted by (node_id, room_no)", sorted(keys), keys)
        self.check("room numbers compared as numbers (not text)", "int", type(rows[0][1]).__name__)


# ======================================================================
def fixed_hotel():
    """Nodes 1, 2, 3 at 100, 200, 300 (V = 1). Guests: 3 on node 1, 1 on node 2, 0 on node 3."""
    tbl = {node_key(1, 0): 100, node_key(2, 0): 200, node_key(3, 0): 300,
           guest_key(1, 1): 50, guest_key(1, 2): 60, guest_key(1, 3): 350, guest_key(1, 4): 150}
    h = HotelSystem(1, hash_fn=lambda t: tbl[t])
    h.setup(3, 1, 4)
    return h


class TestLoadStats(ReportTestCase):
    def test_counts_include_empty_nodes(self):
        """Load counts include nodes with 0 guests"""
        st = fixed_hotel().load_stats()
        self.check("guests per node", {1: 3, 2: 1, 3: 0}, st["counts"])

    def test_values(self):
        """max, min, mean, std (population) and CV"""
        st = fixed_hotel().load_stats()
        self.check("max, min", (3, 0), (st["max"], st["min"]))
        self.check("mean (4 guests / 3 nodes)", 1.3333, round(st["mean"], 4))
        self.check("std = sqrt(((3-4/3)^2 + (1-4/3)^2 + (0-4/3)^2) / 3)", 1.2472, round(st["std"], 4))
        self.check("CV = std / mean", 0.9354, round(st["cv"], 4))

    def test_no_guests(self):
        """Edge case — K = 0: stats are 0 and CV is not computed (no division by zero)"""
        h = HotelSystem(4)
        h.setup(5, 0, 0)
        st = h.load_stats()
        self.check("K, max, min, mean, std",
                   (0, 0, 0, 0, 0), (st["K"], st["max"], st["min"], st["mean"], st["std"]))
        self.check("CV", None, st["cv"])
        self.check("all 5 nodes listed with 0 guests", {i: 0 for i in range(1, 6)}, st["counts"])


# ======================================================================
TEST_CLASSES = [TestRoomNumber, TestSetup, TestAddRemove, TestSearch, TestRoomList, TestLoadStats]

if __name__ == "__main__":
    main("Guest / room / index tests (Member 2)", TEST_CLASSES)
