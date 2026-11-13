import sys

import test_export
import test_guest
import test_hashring
import test_main
import test_move
from testkit import LINE, run_suite

SUITES = [
    ("Member 1 — HashRing (test_hashring.py)", test_hashring.TEST_CLASSES),
    ("Member 2 — guests, rooms, indexes (test_guest.py)", test_guest.TEST_CLASSES),
    ("Member 3 — add/remove node, moves, hash mod N (test_move.py)", test_move.TEST_CLASSES),
    ("Member 4 — CSV, experiments, menu input (test_export.py)", test_export.TEST_CLASSES),
    ("Member 4 — text menu, keyboard simulated (test_main.py)", test_main.TEST_CLASSES),
]


def main():
    results = [(title, run_suite(title, classes)) for title, classes in SUITES]
    print(f"\n{LINE}\nOVERALL RESULT\n{LINE}")
    total = [0, 0, 0, 0]
    for title, r in results:
        status = "PASS" if r[0] == r[1] else "FAIL"
        print(f"  [{status}] {title}: tests {r[0]}/{r[1]}, checks {r[2]}/{r[3]}")
        total = [a + b for a, b in zip(total, r)]
    print(f"{LINE}\n  ALL: tests {total[0]}/{total[1]}, checks {total[2]}/{total[3]}  -> "
          f"{'ALL PASSED' if total[0] == total[1] else 'SOME TESTS FAILED'}\n{LINE}")
    return total[0] == total[1]


if __name__ == "__main__":
    sys.exit(0 if main() else 1)