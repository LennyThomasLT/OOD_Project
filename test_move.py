from guest import room_no
from hotel import HotelSystem
from modn import ModNHashing, moves_between
from test_hashring import A, B, C, D, NAME, table_hash
from testkit import ReportTestCase, main


def hotel_91():
    h = HotelSystem(1, hash_fn=table_hash)
    h.setup(3, 1, 7, node_ids=[A, B, C])
    return h


def named(moves):
    return sorted((c, s, NAME[o], NAME[n], r) for c, s, o, n, r in moves)


def big_hotel(k_per_channel=200, n=10, v=32, salt="0"):
    h = HotelSystem(v, salt=salt)
    h.setup(n, 10, k_per_channel)
    return h


def snapshot(h):
    return {g.key: (g.node_id, g.room_no) for g in h.all_guests()}


class TestExample91Moves(ReportTestCase):
    def test_add_D(self):
        h = hotel_91()
        rep = h.add_node(D)
        self.check("report ok", True, rep.ok)
        self.note("Summary", rep.summary())
        self.check("move list (c, s, old, new, room)",
                   [(1, 3, "B", "D", room_no(1, 3)), (1, 4, "B", "D", room_no(1, 4))], named(rep.moves))
        self.check("count", 2, rep.count)
        self.check("rate = 2 / 7", round(2 / 7, 6), round(rep.rate, 6))

    def test_remove_B(self):
        h = hotel_91()
        rep = h.remove_node(B)
        self.check("report ok", True, rep.ok)
        self.note("Summary", rep.summary())
        self.check("move list (c, s, old, new, room)",
                   [(1, 3, "B", "C", room_no(1, 3)), (1, 4, "B", "C", room_no(1, 4)),
                    (1, 5, "B", "C", room_no(1, 5))], named(rep.moves))
        self.check("count", 3, rep.count)

    def test_wrap_guest_stays_on_A(self):
        h1, h2 = hotel_91(), hotel_91()
        h1.add_node(D)
        h2.remove_node(B)
        self.check("node of guest (1, 7) after add D / after remove B",
                   ("A", "A"), (NAME[h1.find_by_guest(1, 7)[0]], NAME[h2.find_by_guest(1, 7)[0]]))


class TestAddNodeV32(ReportTestCase):
    def setUp(self):
        super().setUp()
        self.h = big_hotel()
        self.before = snapshot(self.h)
        self.rep = self.h.add_node(11)
        self.after = snapshot(self.h)

    def test_movers_go_to_new_node_only(self):
        self.note("Summary", self.rep.summary())
        self.check("new nodes of movers that are not 11", [],
                   [m for m in self.rep.moves if m[3] != 11])

    def test_non_movers_unchanged(self):
        moved = {(c, s) for c, s, *_ in self.rep.moves}
        changed = [k for k in self.before if k not in moved and self.after[k] != self.before[k]]
        self.check("non-movers whose address changed", [], changed)

    def test_totals(self):
        self.check("K before / after", (2000, 2000), (len(self.before), len(self.after)))
        actually_changed = sum(1 for k in self.before if self.after[k][0] != self.before[k][0])
        self.check("reported count == guests whose node really changed", actually_changed, self.rep.count)
        self.check("movers whose room number changed", [],
                   [k for k in self.before if self.after[k][1] != self.before[k][1]])

    def test_indexes_consistent(self):
        self.check("indexes consistent", True, self.h.is_consistent())
        wrong = [g.key for g in self.h.all_guests() if g.node_id != self.h.locate(g.c, g.s)]
        self.check("guests whose stored node differs from the ring", [], wrong)

    def test_room_search_after_move(self):
        c, s, old, new, room = self.rep.moves[0]
        self.check(f"find_by_room({new}, {room}) (new address)", (c, s), self.h.find_by_room(new, room))
        self.check(f"find_by_room({old}, {room}) (old address)", None, self.h.find_by_room(old, room))
        self.check(f"find_by_guest({c}, {s})", (new, room), self.h.find_by_guest(c, s))


class TestRemoveNodeV32(ReportTestCase):
    def setUp(self):
        super().setUp()
        self.h = big_hotel()
        self.before = snapshot(self.h)
        self.on_node3 = sorted(k for k, (n, _) in self.before.items() if n == 3)
        self.rep = self.h.remove_node(3)
        self.after = snapshot(self.h)

    def test_only_removed_node_guests_move(self):
        self.note("Summary", self.rep.summary())
        self.check("movers == guests that were on node 3",
                   self.on_node3, sorted((c, s) for c, s, *_ in self.rep.moves))
        self.check("guests left on node 3", 0, sum(1 for n, _ in self.after.values() if n == 3))

    def test_others_unchanged(self):
        changed = [k for k in self.before if self.before[k][0] != 3 and self.after[k] != self.before[k]]
        self.check("guests of other nodes whose address changed", [], changed)

    def test_totals(self):
        self.check("K after", 2000, len(self.after))
        self.check("count == len(move list)", len(self.rep.moves), self.rep.count)
        self.check("rate", round(self.rep.count / 2000, 6), round(self.rep.rate, 6))
        self.check("indexes consistent", True, self.h.is_consistent())


class TestEdgeCases(ReportTestCase):
    def test_add_existing_node(self):
        h = big_hotel(20)
        before = snapshot(h)
        rep = h.add_node(5)
        self.check("ok", False, rep.ok)
        self.note("Message", rep.summary())
        self.check("count", 0, rep.count)
        self.check("data unchanged", before, snapshot(h))
        self.check("points on the ring", 10 * 32, h.ring.point_count())

    def test_remove_missing_node(self):
        h = big_hotel(20)
        before = snapshot(h)
        rep = h.remove_node(99)
        self.check("ok", False, rep.ok)
        self.note("Message", rep.summary())
        self.check("count", 0, rep.count)
        self.check("data unchanged", before, snapshot(h))

    def test_remove_last_node(self):
        h = HotelSystem(4)
        h.setup(1, 0, 0)
        rep = h.remove_node(1)
        self.check("ok", False, rep.ok)
        self.note("Message", rep.summary())
        self.check("nodes left", [1], h.ring.nodes())

    def test_no_guests(self):
        h = HotelSystem(4)
        h.setup(3, 0, 0)
        rep = h.add_node(4)
        self.check("ok", True, rep.ok)
        self.note("Summary", rep.summary())
        self.check("count, rate", (0, None), (rep.count, rep.rate))
        rep2 = h.remove_node(1)
        self.check("remove: count, rate", (0, None), (rep2.count, rep2.rate))


class TestModN(ReportTestCase):
    def test_locate_formula(self):
        m = ModNHashing(salt="0")
        m.build([10, 20, 30])
        h = m.guest_hash(1, 1)
        self.check("locate(1, 1)", [10, 20, 30][h % 3], m.locate(1, 1))

    def test_remove_keeps_order(self):
        m = ModNHashing()
        m.build([5, 1, 9, 3])
        m.remove_node(1)
        self.check("node list after removing 1", [5, 9, 3], m.nodes)
        m.add_node(7)
        self.check("node list after adding 7 (appended)", [5, 9, 3, 7], m.nodes)

    def test_moves_compared_by_real_id(self):
        before = {(1, 1): 5, (1, 2): 9}
        after = {(1, 1): 5, (1, 2): 3}
        self.check("moves_between", [(1, 2, 9, 3)], moves_between(before, after))

    def test_edge_cases(self):
        m = ModNHashing()
        self.check("locate with no nodes", None, m.locate(1, 1))
        m.build([1])
        self.check("add existing -> ok", False, m.add_node(1)[0])
        self.check("remove missing -> ok", False, m.remove_node(9)[0])
        self.check("remove last -> ok", False, m.remove_node(1)[0])

    def test_modn_moves_more(self):
        h = big_hotel()
        keys = [g.key for g in h.all_guests()]
        m = ModNHashing(salt="0")
        m.build(range(1, 11))
        before = m.assign(keys)
        m.add_node(11)
        modn_moves = len(moves_between(before, m.assign(keys)))
        ch_moves = h.add_node(11).count
        self.note("Counts", f"consistent hashing = {ch_moves}, hash mod N = {modn_moves} (K = 2000)")
        self.check("hash mod N moved more", True, modn_moves > ch_moves)
        self.check("hash mod N moved more than half of the guests", True, modn_moves > 1000)


TEST_CLASSES = [TestExample91Moves, TestAddNodeV32, TestRemoveNodeV32, TestEdgeCases, TestModN]

if __name__ == "__main__":
    main("Add/remove node and move tests (Member 3)", TEST_CLASSES)
