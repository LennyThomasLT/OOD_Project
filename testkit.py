import os
import sys
import unittest

LINE = "=" * 72
SUB = "-" * 72
stats = {"test_no": 0, "checks": 0, "checks_passed": 0}


def _short(value, limit=90):
    text = repr(value)
    return text if len(text) <= limit else text[:limit - 3] + "..."


class ReportTestCase(unittest.TestCase):

    def setUp(self):
        stats["test_no"] += 1
        title = (self._testMethodDoc or self._testMethodName).strip().splitlines()[0]
        print(f"\n{LINE}\nTEST {stats['test_no']}: {title}\n{SUB}")

    def check(self, what, expected, actual):
        ok = expected == actual
        stats["checks"] += 1
        stats["checks_passed"] += ok
        print(f"  Check    : {what}")
        print(f"  Expected : {_short(expected)}")
        print(f"  Actual   : {_short(actual)}")
        print(f"  Result   : {'PASS' if ok else 'FAIL'}\n")
        self.assertEqual(actual, expected, what)

    def note(self, label, text):
        print(f"  {label:<9}: {text}\n")


def load_suite(classes):
    suite = unittest.TestSuite()
    for cls in classes:
        names = [n for n in cls.__dict__ if n.startswith("test_")]
        suite.addTests(cls(n) for n in names)
    return suite


def run_suite(title, classes):
    stats.update(test_no=0, checks=0, checks_passed=0)
    print(f"\n{'#' * 72}\n# {title}\n{'#' * 72}")
    with open(os.devnull, "w") as devnull:
        result = unittest.TextTestRunner(verbosity=0, stream=devnull).run(load_suite(classes))
    failed = result.failures + result.errors
    print(LINE)
    print(f"SUMMARY: tests passed {result.testsRun - len(failed)}/{result.testsRun}, "
          f"checks passed {stats['checks_passed']}/{stats['checks']}")
    for test, trace in failed:
        name = (test._testMethodDoc or test._testMethodName).strip().splitlines()[0]
        print(f"  FAILED: {name}  ({type(test).__name__}.{test._testMethodName})")
        if test in [t for t, _ in result.errors]:
            print("     error: " + trace.strip().splitlines()[-1])
    print(LINE)
    return (result.testsRun - len(failed), result.testsRun, stats["checks_passed"], stats["checks"])


def main(title, classes):
    passed, run, _, _ = run_suite(title, classes)
    sys.exit(0 if passed == run else 1)
