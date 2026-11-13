import csv
import os
import tempfile

from experiments import channel_counts, guest_keys, sample_keys, summarize
from export import GUEST_FIELDS, export_guests, export_moves
from hotel import HotelSystem
from main import parse_int
from testkit import ReportTestCase, main


def read_csv(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.reader(f))


def make_hotel(per_channel=30):
    h = HotelSystem(32, salt="0")
    h.setup(10, 10, per_channel)
    return h


class TempDirCase(ReportTestCase):
    def setUp(self):
        super().setUp()
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def path(self, name):
        return os.path.join(self.dir, name)


class TestGuestCSV(TempDirCase):
    def test_rows_equal_guests(self):
        h = make_hotel()
        n = export_guests(h, self.path("g.csv"))
        rows = read_csv(self.path("g.csv"))
        self.check("header", GUEST_FIELDS, rows[0])
        self.check("data rows in the file", h.guest_count(), len(rows) - 1)
        self.check("rows reported by export_guests", h.guest_count(), n)

    def test_rows_after_changes(self):
        h = make_hotel()
        h.remove_guest(1, 1)
        h.remove_guest(2, 2)
        h.add_node(11)
        h.remove_node(4)
        export_guests(h, self.path("g.csv"))
        self.check("data rows == K", h.guest_count(), len(read_csv(self.path("g.csv"))) - 1)

    def test_values_match_system(self):
        h = make_hotel()
        export_guests(h, self.path("g.csv"))
        wrong = [r for r in read_csv(self.path("g.csv"))[1:]
                 if h.find_by_guest(int(r[0]), int(r[1])) != (int(r[2]), int(r[3]))]
        self.check("rows that disagree with find_by_guest", [], wrong)

    def test_empty_system(self):
        h = HotelSystem(4)
        h.setup(3, 0, 0)
        export_guests(h, self.path("g.csv"))
        self.check("file content", [GUEST_FIELDS], read_csv(self.path("g.csv")))

    def test_utf8(self):
        export_guests(make_hotel(1), self.path("g.csv"))
        with open(self.path("g.csv"), "rb") as f:
            raw = f.read()
        self.check("decodes as UTF-8", True, raw.decode("utf-8").startswith("channel_id"))


class TestMoveCSV(TempDirCase):
    def test_rows_equal_move_count(self):
        h = make_hotel()
        rep = h.add_node(11)
        n = export_moves(rep, self.path("m.csv"))
        rows = read_csv(self.path("m.csv"))
        self.check("data rows == report.count", rep.count, len(rows) - 1)
        self.check("rows reported by export_moves", rep.count, n)
        self.check("every new_node is 11", {"11"}, {r[5] for r in rows[1:]})

    def test_failed_change(self):
        h = make_hotel()
        rep = h.remove_node(99)
        export_moves(rep, self.path("m.csv"))
        self.check("data rows", 0, len(read_csv(self.path("m.csv"))) - 1)


class TestExperimentHelpers(ReportTestCase):
    def test_channel_counts(self):
        self.check("channel_counts(10005)", [1001] * 5 + [1000] * 5, channel_counts(10005))
        self.check("total of channel_counts(10005)", 10005, sum(channel_counts(10005)))

    def test_guest_keys_unique(self):
        keys = guest_keys(1000)
        self.check("number of codes / distinct codes", (1000, 1000), (len(keys), len(set(keys))))
        self.check("first code of each channel", [(c, 1) for c in range(1, 11)],
                   sorted({(c, 1) for c, s in keys if s == 1}))

    def test_sample_keys(self):
        keys = guest_keys(100000)
        sample = sample_keys(keys)
        self.check("batch size", 1000, len(sample))
        self.check("all sampled codes exist", True, set(sample) <= set(keys))
        self.check("batch size when K = 300", 1000, len(sample_keys(guest_keys(300))))

    def test_summarize_median(self):
        rows = [{"K": 10, "t": 5.0}, {"K": 10, "t": 1.0}, {"K": 10, "t": 3.0}]
        s = summarize(rows, ["K"], ["t"])[0]
        self.check("median, min, max", (3.0, 1.0, 5.0), (s["median"], s["min"], s["max"]))


class TestMenuInput(ReportTestCase):
    def test_parse_int(self):
        cases = [("12", 1), ("  7 ", 1), ("abc", 1), ("", 1), ("0", 1), ("0", 0), ("-3", 0), ("2.5", 1)]
        got = [parse_int(text, minimum)[0] for text, minimum in cases]
        self.check("accepted? for '12','  7 ','abc','','0'(min 1),'0'(min 0),'-3'(min 0),'2.5'",
                   [12, 7, None, None, None, 0, None, None], got)


TEST_CLASSES = [TestGuestCSV, TestMoveCSV, TestExperimentHelpers, TestMenuInput]

if __name__ == "__main__":
    main("CSV export / experiments / menu tests (Member 4)", TEST_CLASSES)
