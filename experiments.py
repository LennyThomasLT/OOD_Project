"""
experiments.py — experiments A, B, C from section 7 (Member 4)

Run:  python experiments.py            (full sizes from the spec)
      python experiments.py --quick    (small sizes, for a fast check only)

Method (section 7.1 / 7.2)
- Guests come from 10 channels, spread as evenly as possible (sizes differ by at most 1).
- Each experiment runs 3 rounds with salt "0", "1", "2". In a round, consistent hashing and
  hash mod N use the same salt, guests, node IDs and hash values.
- Time: time.perf_counter(); ring build, adding guests, search, sorting and add/remove node are
  timed separately; no keyboard, printing or file writing inside a timed section.
  Searches are timed as a batch of 1,000 and divided by 1,000.
- Memory: tracemalloc, measured in a SEPARATE run from the timing run. Reported in MiB
  (1 MiB = 1,048,576 bytes); it is memory traced by Python, not the whole process.
- Each summary reports the median of the 3 rounds plus min and max.
- Experiment B removes node 1 (the first node added) for both methods, and adds node N + 1.

Output (folder results/)
- exp_A_runs.csv, exp_B_runs.csv, exp_C_runs.csv, exp_C_loads.csv : one row per round
- exp_A_summary.csv, exp_B_summary.csv, exp_C_summary.csv          : median / min / max
- sample_guests.csv, sample_moves_add.csv, sample_moves_remove.csv  : sample data
- run_info.csv : Python version, machine, parameters
"""

import gc
import platform
import statistics
import sys
import time
import tracemalloc

from export import export_guests, export_moves, export_rows
from hotel import HotelSystem
from modn import ModNHashing, moves_between

SALTS = ["0", "1", "2"]
CHANNELS = 10
BATCH = 1000
OUT = "results"
MIB = 1024 * 1024


# ---------------------------------------------------------------- helpers
def channel_counts(k, channels=CHANNELS):
    """Spread K guests over the channels; sizes differ by at most 1."""
    base, extra = divmod(k, channels)
    return [base + (1 if i < extra else 0) for i in range(channels)]


def guest_keys(k, channels=CHANNELS):
    return [(c, s) for c, cnt in enumerate(channel_counts(k, channels), start=1)
            for s in range(1, cnt + 1)]


def sample_keys(keys, n=BATCH):
    """n codes spread evenly over the guest list (same every run)."""
    step = max(1, len(keys) // n)
    picked = keys[::step][:n]
    while len(picked) < n:              # fewer guests than n: repeat
        picked += picked[:n - len(picked)]
    return picked


def build(n, v, k, salt):
    """Build a hotel; returns (hotel, ring build seconds, add-all-guests seconds)."""
    h = HotelSystem(v, salt=salt)
    gc.collect()
    t0 = time.perf_counter()
    h.ring.build(range(1, n + 1))
    t1 = time.perf_counter()
    for c, cnt in enumerate(channel_counts(k), start=1):
        h.add_group(c, 1, cnt)
    t2 = time.perf_counter()
    return h, t1 - t0, t2 - t1


def memory_of(fn):
    """Run fn() under tracemalloc; return (result, current MiB, peak MiB)."""
    gc.collect()
    tracemalloc.start()
    result = fn()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return result, current / MIB, peak / MIB


def summarize(rows, group_by, metrics):
    """Median / min / max of each metric over the rounds with the same parameters."""
    groups = {}
    for r in rows:
        groups.setdefault(tuple(r[g] for g in group_by), []).append(r)
    out = []
    for key, rs in groups.items():
        for m in metrics:
            vals = [r[m] for r in rs if r[m] is not None]
            if not vals:
                continue
            row = dict(zip(group_by, key))
            row.update({"metric": m, "median": statistics.median(vals),
                        "min": min(vals), "max": max(vals), "rounds": len(vals)})
            out.append(row)
    return out


def log(text):
    print(text, flush=True)


# ---------------------------------------------------------------- experiment A
def experiment_a(ks, n=10, v=32):
    rows = []
    for k in ks:
        for salt in SALTS:
            h, t_ring, t_add = build(n, v, k, salt)
            keys = sample_keys(guest_keys(k))
            addrs = [h.find_by_guest(c, s) for c, s in keys]

            gc.collect()
            t0 = time.perf_counter()
            for c, s in keys:
                h.find_by_guest(c, s)
            t1 = time.perf_counter()
            for node, room in addrs:
                h.find_by_room(node, room)
            t2 = time.perf_counter()
            for c, s in keys:
                h.locate(c, s)
            t3 = time.perf_counter()
            h.list_rooms()
            t4 = time.perf_counter()

            _, cur, peak = memory_of(lambda: build(n, v, k, salt)[0])
            rows.append({"K": k, "N": n, "V": v, "salt": salt,
                         "ring_build_s": t_ring, "add_all_guests_s": t_add,
                         "add_per_guest_us": t_add / k * 1e6,
                         "find_by_guest_us": (t1 - t0) / BATCH * 1e6,
                         "find_by_room_us": (t2 - t1) / BATCH * 1e6,
                         "locate_on_ring_us": (t3 - t2) / BATCH * 1e6,
                         "sort_rooms_s": t4 - t3,
                         "mem_current_mib": cur, "mem_peak_mib": peak})
            log(f"  A  K={k:>6} salt={salt}  add all {t_add:.3f}s  peak {peak:.2f} MiB")
    metrics = [m for m in rows[0] if m not in ("K", "N", "V", "salt")]
    return rows, summarize(rows, ["K", "N", "V"], metrics)


# ---------------------------------------------------------------- experiment B
def consistent_change(n, v, k, salt, action, node_id):
    h, _, _ = build(n, v, k, salt)
    rep = h.add_node(node_id) if action == "add" else h.remove_node(node_id)
    t = rep.times
    return rep.count, t["ring"], t["find"], t["update"]


def modn_change(n, k, salt, action, node_id):
    keys = guest_keys(k)
    m = ModNHashing(salt=salt)
    m.build(range(1, n + 1))
    stored = m.assign(keys)                         # current node of every guest
    gc.collect()
    t0 = time.perf_counter()
    m.add_node(node_id) if action == "add" else m.remove_node(node_id)
    t1 = time.perf_counter()
    moves = moves_between(stored, m.assign(keys))   # recompute all K and compare
    t2 = time.perf_counter()
    for c, s, _old, new in moves:
        stored[(c, s)] = new
    t3 = time.perf_counter()
    return len(moves), t1 - t0, t2 - t1, t3 - t2


def experiment_b(ns, k=10000, v=32):
    rows = []
    for n in ns:
        for salt in SALTS:
            for action, node_id, expected in (("add", n + 1, 1 / (n + 1)), ("remove", 1, 1 / n)):
                for method in ("consistent", "modn"):
                    if method == "consistent":
                        moved, tr, tf, tu = consistent_change(n, v, k, salt, action, node_id)
                    else:
                        moved, tr, tf, tu = modn_change(n, k, salt, action, node_id)
                    rows.append({"N": n, "K": k, "V": v, "salt": salt, "method": method,
                                 "action": action, "changed_node": node_id,
                                 "moved": moved, "rate": moved / k, "expected_rate": expected,
                                 "time_total_s": tr + tf + tu, "time_ring_s": tr,
                                 "time_find_s": tf, "time_update_s": tu})
            log(f"  B  N={n:>2} salt={salt}  done")
    metrics = ["moved", "rate", "expected_rate", "time_total_s", "time_ring_s", "time_find_s", "time_update_s"]
    return rows, summarize(rows, ["N", "K", "V", "method", "action", "changed_node"], metrics)


# ---------------------------------------------------------------- experiment C
def experiment_c(vs, n=10, k=10000):
    rows, loads = [], []
    for v in vs:
        for salt in SALTS:
            h, _, _ = build(n, v, k, salt)
            st = h.load_stats()
            for node, cnt in st["counts"].items():
                loads.append({"V": v, "salt": salt, "node_id": node, "guests": cnt})

            def ring_only():
                hh = HotelSystem(v, salt=salt)
                hh.ring.build(range(1, n + 1))
                return hh
            _, ring_cur, ring_peak = memory_of(ring_only)
            _, hot_cur, hot_peak = memory_of(lambda: build(n, v, k, salt)[0])

            add_moved = build(n, v, k, salt)[0].add_node(n + 1).count
            rem_moved = build(n, v, k, salt)[0].remove_node(1).count
            rows.append({"V": v, "N": n, "K": k, "salt": salt, "M": n * v,
                         "max": st["max"], "min": st["min"], "mean": st["mean"],
                         "std": st["std"], "cv": st["cv"],
                         "ring_mem_current_mib": ring_cur, "ring_mem_peak_mib": ring_peak,
                         "hotel_mem_current_mib": hot_cur, "hotel_mem_peak_mib": hot_peak,
                         "add_moved": add_moved, "add_rate": add_moved / k,
                         "remove_moved": rem_moved, "remove_rate": rem_moved / k})
            log(f"  C  V={v:>2} salt={salt}  CV {st['cv']:.3f}")
    metrics = [m for m in rows[0] if m not in ("V", "N", "K", "salt", "M")]
    return rows, loads, summarize(rows, ["V", "N", "K", "M"], metrics)


# ---------------------------------------------------------------- samples
def samples(n=10, v=32, k=1000, salt="0"):
    h, _, _ = build(n, v, k, salt)
    rows = export_guests(h, f"{OUT}/sample_guests.csv")
    rep_add = h.add_node(n + 1)
    export_moves(rep_add, f"{OUT}/sample_moves_add.csv")
    rep_rem = h.remove_node(1)
    export_moves(rep_rem, f"{OUT}/sample_moves_remove.csv")
    log(f"  samples: {rows} guests, add moved {rep_add.count}, remove moved {rep_rem.count}")


# ---------------------------------------------------------------- main
def main():
    quick = "--quick" in sys.argv
    ks = [1000, 10000] if quick else [1000, 10000, 100000]
    k_bc = 2000 if quick else 10000
    started = time.perf_counter()

    log("Experiment A (data size)")
    a_runs, a_sum = experiment_a(ks)
    export_rows(a_runs, f"{OUT}/exp_A_runs.csv")
    export_rows(a_sum, f"{OUT}/exp_A_summary.csv")

    log("Experiment B (number of nodes)")
    b_runs, b_sum = experiment_b([5, 10, 20], k=k_bc)
    export_rows(b_runs, f"{OUT}/exp_B_runs.csv")
    export_rows(b_sum, f"{OUT}/exp_B_summary.csv")

    log("Experiment C (virtual nodes)")
    c_runs, c_loads, c_sum = experiment_c([1, 8, 32], k=k_bc)
    export_rows(c_runs, f"{OUT}/exp_C_runs.csv")
    export_rows(c_loads, f"{OUT}/exp_C_loads.csv")
    export_rows(c_sum, f"{OUT}/exp_C_summary.csv")

    log("Sample data")
    samples()

    export_rows([{"python": platform.python_version(), "implementation": platform.python_implementation(),
                  "machine": platform.machine(), "system": platform.system(),
                  "salts": " ".join(SALTS), "channels": CHANNELS, "batch": BATCH,
                  "quick_mode": quick, "A_K": " ".join(map(str, ks)), "B_C_K": k_bc,
                  "B_removed_node": 1, "B_added_node": "N+1"}], f"{OUT}/run_info.csv")
    log(f"Done in {time.perf_counter() - started:.1f} s. Results are in {OUT}/")


if __name__ == "__main__":
    main()
