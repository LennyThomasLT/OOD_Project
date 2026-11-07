"""
test_main.py — Member 4 tests of the text menu (main.py)

The keyboard is simulated: each step gives the menu choice and the values a user would type,
then checks the result line the menu prints. The steps are the same as the manual test cases
(part A: normal system, part B: no guests), so the menu is tested without anyone typing.

Run:  python test_main.py
      (also works with: python -m unittest test_main)
"""

import contextlib
import csv
import io
import os
import tempfile

import main as menu
from testkit import ReportTestCase, main


class MenuTestCase(ReportTestCase):
    def setUp(self):
        super().setUp()
        self.app = menu.App()
        self._tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self._tmp.cleanup()

    def tmp(self, name):
        return os.path.join(self._tmp.name, name)

    def run_step(self, choice, *typed):
        """Simulate one menu choice plus what the user types; return the printed text."""
        answers = iter(str(x) for x in typed)
        original = getattr(menu, "input", None)
        menu.input = lambda prompt="": next(answers)      # replaces the keyboard
        out = io.StringIO()
        try:
            with contextlib.redirect_stdout(out):
                self.app.handle(str(choice))
        finally:
            if original is None:
                del menu.input
            else:
                menu.input = original
        return out.getvalue()

    @staticmethod
    def result_line(text):
        """Last line starting with ✓ or ! (the result message)."""
        lines = [l.strip() for l in text.splitlines() if l.strip().startswith(("✓", "!"))]
        return lines[-1] if lines else text.strip()

    def step(self, no, label, choice, typed, expected):
        out = self.run_step(choice, *typed)
        self.check(f"Step {no}: menu {choice} {label}  (typed: {', '.join(map(str, typed)) or '-'})",
                   expected, self.result_line(out))
        return out


def rows(path):
    with open(path, encoding="utf-8") as f:
        return len(list(csv.reader(f))) - 1


# ======================================================================
class TestMenuSession(MenuTestCase):
    def setUp(self):
        super().setUp()
        self.run_step(1, 5, 8, 3, 10, "0")   # N=5, V=8, 3 channels x 10 guests, salt 0

    def test_before_setup(self):
        """Steps 1–2: using the menu before setup, then starting the system"""
        app = self.app
        self.app = menu.App()
        self.step(1, "list rooms before setup", 9, [], "! ยังไม่ได้เริ่มระบบ กรุณาเลือกเมนู 1 ก่อน")
        self.step(2, "start system", 1, [5, 8, 3, 10, "0"], "✓ เริ่มระบบแล้ว: 5 อาคาร, V = 8, แขก 30 คน")
        self.app = app

    def test_search(self):
        """Steps 3–6: search by guest code and by address"""
        self.step(3, "find guest", 5, [1, 1], "✓ แขก (1, 1) อยู่อาคาร 2 ห้อง 1")
        self.step(4, "find guest", 5, [2, 3], "✓ แขก (2, 3) อยู่อาคาร 4 ห้อง 9")
        self.step(5, "find room", 6, [3, 5], "✓ อาคาร 3 ห้อง 5: แขกรหัส (2, 2)")
        self.step(6, "find room (empty)", 6, [3, 99], "! ไม่พบผู้พักที่อาคาร 3 ห้อง 99")

    def test_add_remove_guests(self):
        """Steps 7–14: add/remove guests, duplicates, groups, bad input"""
        self.step(7, "add duplicate guest", 2, [1, 1], "! มีแขกรหัส (1, 1) อยู่แล้ว ไม่เพิ่มซ้ำ")
        self.step(8, "add guest, new channel", 2, [9, 3], "✓ เพิ่มแขก (9, 3) -> อาคาร 4 ห้อง 58")
        self.step(9, "group with duplicates", 3, [2, 9, 5],
                  "! ปฏิเสธทั้งกลุ่ม: มีรหัสซ้ำ 2 รหัส ได้แก่ (2, 9), (2, 10)")
        self.step(10, "add group", 3, [4, 1, 3], "✓ เพิ่มแขกช่องทาง 4 ลำดับ 1..3 (3 คน)")
        self.step(11, "group of 0", 3, [3, 1, 0], "✓ จำนวนแขกเป็น 0 ไม่มีการเปลี่ยนแปลง")
        self.step(12, "remove guest", 4, [2, 1], "✓ นำแขก (2, 1) ออกจากอาคาร 4 ห้อง 2 แล้ว")
        self.step(13, "remove missing guest", 4, [2, 1], "! ไม่พบแขกรหัส (2, 1)")
        out = self.step(14, "typing 'abc' then a valid code", 5, ["abc", 2, 1], "! ไม่พบแขกรหัส (2, 1)")
        self.check("Step 14: the bad input was reported, not crashed", True,
                   "! 'abc' ไม่ใช่จำนวนเต็ม กรุณาลองใหม่" in out)
        self.check("number of guests after steps 7–14", 33, self.app.hotel.guest_count())

    def _to_step_14(self):
        for choice, typed in ((2, [9, 3]), (3, [4, 1, 3]), (4, [2, 1])):
            self.run_step(choice, *typed)

    def test_add_remove_nodes(self):
        """Steps 15–18: add/remove nodes and the move lists"""
        self._to_step_14()
        self.step(15, "add existing node", 7, [3], "! ไม่สำเร็จ: มีอาคาร 3 อยู่แล้ว ไม่เพิ่มซ้ำ")
        self.step(16, "add node 6", 7, [6], "✓ เพิ่มอาคาร 6 แล้ว: ย้าย 7 จาก 33 คน (อัตรา 0.2121 = 21.21%)")
        rep = self.app.last_report
        self.check("Step 16: new node of every mover", [6] * 7, [m[3] for m in rep.moves])
        self.step(17, "remove missing node", 8, [99], "! ไม่สำเร็จ: ไม่พบอาคาร 99")
        self.step(18, "remove node 2", 8, [2], "✓ ลบอาคาร 2 แล้ว: ย้าย 9 จาก 33 คน (อัตรา 0.2727 = 27.27%)")
        rep = self.app.last_report
        self.check("Step 18: old node of every mover", [2] * 9, [m[2] for m in rep.moves])
        self.step("18b", "find (1, 1) after it moved", 5, [1, 1], "✓ แขก (1, 1) อยู่อาคาร 4 ห้อง 1")

    def test_stats_list_export(self):
        """Steps 19–23: load stats, room list, CSV export, unknown menu"""
        self._to_step_14()
        self.run_step(7, 6)
        self.run_step(8, 2)
        out = self.run_step(10)
        self.check("Step 19: menu 10 stats line", True,
                   "สูงสุด 11, ต่ำสุด 4, เฉลี่ย 6.60, ส่วนเบี่ยงเบนมาตรฐาน 2.42, CV 0.3662" in out)
        out = self.run_step(9)
        self.check("Step 20: menu 9 header", True, "ห้องที่มีผู้พักทั้งหมด 33 ห้อง (แสดง 20 แถวแรก)" in out)
        first = [l.split() for l in out.splitlines() if l.strip()[:1].isdigit()][0]
        self.check("Step 20: first row (node, room, code)", ["1", "12", "(4,", "2)"], first)
        g, m = self.tmp("guests.csv"), self.tmp("moves.csv")
        self.step(21, "export guests", 11, [g], f"✓ บันทึก 33 แถว (เท่ากับจำนวนแขก) ลง {g}")
        self.check("Step 21: data rows in guests.csv", 33, rows(g))
        self.step(22, "export moves", 12, [m], f"✓ บันทึกรายการย้าย 9 แถว ลง {m}")
        self.check("Step 22: data rows in moves.csv", 9, rows(m))
        self.step(23, "unknown menu", 13, [], "! ไม่มีเมนูนี้ กรุณาเลือกใหม่")


class TestMenuNoGuests(MenuTestCase):
    def test_no_guests(self):
        """Steps 24–29: restart with no guests, removing the last node, exit"""
        self.run_step(1, 5, 8, 3, 10, "0")          # a running system, as at the end of part A
        self.step(24, "restart with 1 node, 0 guests", 1, ["y", 1, 4, 0, 0, "0"],
                  "✓ เริ่มระบบแล้ว: 1 อาคาร, V = 4, แขก 0 คน")
        out = self.run_step(10)
        self.check("Step 25: menu 10 with K = 0", True, "ยังไม่มีแขก: สถิติเป็น 0 และไม่คำนวณ CV" in out)
        self.step(26, "add node 2", 7, [2], "✓ เพิ่มอาคาร 2 แล้ว: ย้าย 0 คน (ไม่คำนวณอัตราเพราะไม่มีแขก)")
        self.step(27, "remove node 1", 8, [1], "✓ ลบอาคาร 1 แล้ว: ย้าย 0 คน (ไม่คำนวณอัตราเพราะไม่มีแขก)")
        self.step(28, "remove last node", 8, [2], "! ไม่สำเร็จ: ลบอาคารสุดท้ายไม่ได้ ระบบต้องมีอย่างน้อย 1 อาคาร")
        with contextlib.redirect_stdout(io.StringIO()):
            keep_running = self.app.handle("0")
        self.check("Step 29: menu 0 stops the loop (handle returns False)", False, keep_running)

    def test_export_moves_before_any_change(self):
        """Edge case — exporting moves before any node change is refused politely"""
        self.run_step(1, 3, 4, 1, 5, "0")
        self.step("-", "export moves with no move list", 12, [],
                  "! ยังไม่มีรายการย้าย (ต้องเพิ่มหรือลบอาคารสำเร็จก่อน)")


# ======================================================================
TEST_CLASSES = [TestMenuSession, TestMenuNoGuests]

if __name__ == "__main__":
    main("Text menu tests (Member 4)", TEST_CLASSES)