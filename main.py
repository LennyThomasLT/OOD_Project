"""
main.py — text menu (Member 4)

Run:  python main.py

The menu only reads input and shows results. All rules live in hashring.py,
guest.py, hotel.py and modn.py (logic is separate from the interface, section 6).
Large lists show only the first rows on screen together with the total;
CSV export always writes everything.
"""

import time

from export import export_guests, export_moves
from hotel import HotelSystem

SHOW = 20   # rows shown on screen for long lists


def parse_int(text, minimum=1):
    """Return (value, None) or (None, error message). Never raises."""
    text = text.strip()
    try:
        value = int(text)
    except ValueError:
        return None, f"'{text}' ไม่ใช่จำนวนเต็ม"
    if value < minimum:
        return None, f"ต้องเป็นจำนวนเต็มตั้งแต่ {minimum} ขึ้นไป"
    return value, None


def ask_int(prompt, minimum=1, default=None):
    """Ask until a valid integer is typed. Empty input uses the default if there is one."""
    while True:
        hint = f" [{default}]" if default is not None else ""
        text = input(f"{prompt}{hint}: ")
        if text.strip() == "" and default is not None:
            return default
        value, err = parse_int(text, minimum)
        if err is None:
            return value
        print(f"  ! {err} กรุณาลองใหม่")


def ask_code():
    c = ask_int("  ช่องทาง c", 1)
    s = ask_int("  ลำดับ s", 1)
    return c, s


class App:
    def __init__(self):
        self.hotel = None
        self.last_report = None

    # ---------- helpers ----------
    def need_hotel(self):
        if self.hotel is None:
            print("  ! ยังไม่ได้เริ่มระบบ กรุณาเลือกเมนู 1 ก่อน")
            return False
        return True

    @staticmethod
    def result(ok, msg):
        print(("  ✓ " if ok else "  ! ") + msg)

    # ---------- menu actions ----------
    def start(self):
        if self.hotel is not None:
            ans = input("  ระบบเริ่มไว้แล้ว ต้องการล้างข้อมูลแล้วเริ่มใหม่หรือไม่ (y/n): ")
            if ans.strip().lower() != "y":
                return
        n = ask_int("  จำนวนอาคาร N", 1, 10)
        v = ask_int("  virtual node ต่ออาคาร V", 1, 32)
        channels = ask_int("  จำนวนช่องทาง", 0, 10)
        per = ask_int("  จำนวนแขกต่อช่องทาง", 0, 100)
        salt = input("  salt [0]: ").strip() or "0"
        hotel = HotelSystem(v, salt=salt)
        t0 = time.perf_counter()
        ok, msg = hotel.setup(n, channels, per)
        t1 = time.perf_counter()
        self.result(ok, msg)
        if ok:
            self.hotel, self.last_report = hotel, None
            print(f"    รหัสอาคาร: 1 ถึง {n}   เวลา {t1 - t0:.4f} วินาที")

    def add_guest(self):
        if self.need_hotel():
            self.result(*self.hotel.add_guest(*ask_code()))

    def add_group(self):
        if not self.need_hotel():
            return
        c = ask_int("  ช่องทาง c", 1)
        s_start = ask_int("  ลำดับเริ่มต้น s_start", 1)
        count = ask_int("  จำนวนแขก", 0)
        self.result(*self.hotel.add_group(c, s_start, count))

    def remove_guest(self):
        if self.need_hotel():
            self.result(*self.hotel.remove_guest(*ask_code()))

    def find_guest(self):
        if not self.need_hotel():
            return
        c, s = ask_code()
        found = self.hotel.find_by_guest(c, s)
        if found is None:
            print(f"  ! ไม่พบแขกรหัส ({c}, {s})")
        else:
            print(f"  ✓ แขก ({c}, {s}) อยู่อาคาร {found[0]} ห้อง {found[1]}")

    def find_room(self):
        if not self.need_hotel():
            return
        node = ask_int("  รหัสอาคาร", 0)
        room = ask_int("  หมายเลขห้อง", 1)
        found = self.hotel.find_by_room(node, room)
        if found is None:
            print(f"  ! ไม่พบผู้พักที่อาคาร {node} ห้อง {room}")
        else:
            print(f"  ✓ อาคาร {node} ห้อง {room}: แขกรหัส {found}")

    def change_node(self, action):
        if not self.need_hotel():
            return
        print(f"  อาคารปัจจุบัน: {self.hotel.ring.nodes()}")
        node = ask_int("  รหัสอาคาร", 0)
        rep = self.hotel.add_node(node) if action == "add" else self.hotel.remove_node(node)
        self.result(rep.ok, rep.summary())
        if not rep.ok:
            return
        self.last_report = rep
        t = rep.times
        print(f"    เวลา: ปรับวงแหวน {t['ring']:.6f} s, หาผู้ย้าย {t['find']:.6f} s, "
              f"ปรับข้อมูล/ดัชนี {t['update']:.6f} s")
        if rep.count:
            print(f"    รายการย้าย (แสดง {min(SHOW, rep.count)} จาก {rep.count} รายการ)")
            print(f"    {'รหัสแขก':<14}{'อาคารเดิม':>10}{'อาคารใหม่':>10}{'ห้อง':>10}")
            for c, s, old, new, room in sorted(rep.moves)[:SHOW]:
                print(f"    {str((c, s)):<14}{old:>10}{new:>10}{room:>10}")

    def list_rooms(self):
        if not self.need_hotel():
            return
        rows = self.hotel.list_rooms()
        print(f"  ห้องที่มีผู้พักทั้งหมด {len(rows)} ห้อง (แสดง {min(SHOW, len(rows))} แถวแรก)")
        print(f"    {'อาคาร':>6}{'ห้อง':>10}   รหัสแขก")
        for node, room, c, s in rows[:SHOW]:
            print(f"    {node:>6}{room:>10}   ({c}, {s})")

    def stats(self):
        if not self.need_hotel():
            return
        st = self.hotel.load_stats()
        print(f"  แขก K = {st['K']}, อาคาร N = {st['N']}")
        for node, cnt in st["counts"].items():
            print(f"    อาคาร {node:>4}: {cnt} คน")
        if st["cv"] is None:
            print("  ยังไม่มีแขก: สถิติเป็น 0 และไม่คำนวณ CV")
        else:
            print(f"  สูงสุด {st['max']}, ต่ำสุด {st['min']}, เฉลี่ย {st['mean']:.2f}, "
                  f"ส่วนเบี่ยงเบนมาตรฐาน {st['std']:.2f}, CV {st['cv']:.4f}")

    def export_guests(self):
        if not self.need_hotel():
            return
        path = input("  ชื่อไฟล์ [guests.csv]: ").strip() or "guests.csv"
        try:
            n = export_guests(self.hotel, path)
            print(f"  ✓ บันทึก {n} แถว (เท่ากับจำนวนแขก) ลง {path}")
        except OSError as e:
            print(f"  ! บันทึกไฟล์ไม่ได้: {e}")

    def export_moves(self):
        if self.last_report is None:
            print("  ! ยังไม่มีรายการย้าย (ต้องเพิ่มหรือลบอาคารสำเร็จก่อน)")
            return
        path = input("  ชื่อไฟล์ [moves.csv]: ").strip() or "moves.csv"
        try:
            n = export_moves(self.last_report, path)
            print(f"  ✓ บันทึกรายการย้าย {n} แถว ลง {path}")
        except OSError as e:
            print(f"  ! บันทึกไฟล์ไม่ได้: {e}")

    # ---------- loop ----------
    MENU = [
        ("1", "เริ่มระบบ (N, V, ช่องทาง, แขกต่อช่องทาง, salt)", "start"),
        ("2", "เพิ่มแขก 1 คน", "add_guest"),
        ("3", "เพิ่มแขกเป็นกลุ่ม", "add_group"),
        ("4", "นำแขกออก", "remove_guest"),
        ("5", "ค้นหาด้วยรหัสแขก", "find_guest"),
        ("6", "ค้นหาด้วยอาคารและหมายเลขห้อง", "find_room"),
        ("7", "เพิ่มอาคาร", "add_node"),
        ("8", "ลบอาคาร", "remove_node"),
        ("9", "แสดงรายการห้องที่มีผู้พัก", "list_rooms"),
        ("10", "สถิติความสมดุลของโหลด", "stats"),
        ("11", "ส่งออก CSV ข้อมูลแขก", "export_guests"),
        ("12", "ส่งออก CSV รายการย้ายล่าสุด", "export_moves"),
        ("0", "ออกจากโปรแกรม", None),
    ]

    def handle(self, choice):
        """Run one menu choice. Returns False when the user chooses to exit."""
        choice = choice.strip()
        if choice == "0":
            print("ออกจากโปรแกรม")
            return False
        name = {k: n for k, _, n in self.MENU}.get(choice)
        if name is None:
            print("  ! ไม่มีเมนูนี้ กรุณาเลือกใหม่")
        elif name == "add_node":
            self.change_node("add")
        elif name == "remove_node":
            self.change_node("remove")
        else:
            getattr(self, name)()
        return True

    def run(self):
        while True:
            print("\n========== Distributed Hilbert's Hotel ==========")
            for key, label, _ in self.MENU:
                print(f"  {key:>2}. {label}")
            if not self.handle(input("เลือกเมนู: ")):
                return

if __name__ == "__main__":
    try:
        App().run()
    except (EOFError, KeyboardInterrupt):
        print("\nออกจากโปรแกรม")