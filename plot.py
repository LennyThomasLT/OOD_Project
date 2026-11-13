import csv

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = "results"


def read_summary(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def series(rows, x_col, metric, **where):
    pts = []
    for r in rows:
        if r["metric"] != metric or any(r[k] != str(v) for k, v in where.items()):
            continue
        med, lo, hi = float(r["median"]), float(r["min"]), float(r["max"])
        pts.append((float(r[x_col]), med, med - lo, hi - med))
    pts.sort()
    return ([p[0] for p in pts], [p[1] for p in pts], [[p[2] for p in pts], [p[3] for p in pts]])


def line(ax, rows, x_col, metric, label, style="o-", **where):
    x, y, err = series(rows, x_col, metric, **where)
    ax.errorbar(x, y, yerr=err, fmt=style, capsize=4, label=label)
    return x


def graph_a():
    rows = read_summary(f"{OUT}/exp_A_summary.csv")
    fig, (left, right) = plt.subplots(1, 2, figsize=(12, 4.8))

    line(left, rows, "K", "add_all_guests_s", "Add all K guests")
    line(left, rows, "K", "sort_rooms_s", "Sort room list")
    line(left, rows, "K", "ring_build_s", "Build ring (N x V points)")
    left.set_xscale("log"); left.set_yscale("log")
    left.set_xlabel("Number of guests K (log scale)")
    left.set_ylabel("Time (seconds, log scale)")
    left.set_title("Total time of whole operations")
    left.grid(True, which="both", alpha=0.3); left.legend()

    line(right, rows, "K", "find_by_guest_us", "Find by guest code (dict)")
    line(right, rows, "K", "find_by_room_us", "Find by address (dict)")
    line(right, rows, "K", "locate_on_ring_us", "Compute node on ring (bisect)")
    line(right, rows, "K", "add_per_guest_us", "Add one guest (average)")
    right.set_xscale("log")
    right.set_ylim(0, right.get_ylim()[1] * 1.5)
    right.set_xlabel("Number of guests K (log scale)")
    right.set_ylabel("Time per operation (microseconds)")
    right.set_title("Time per operation (batch of 1,000 / 1,000)")
    right.grid(True, which="both", alpha=0.3); right.legend(loc="upper left", ncol=2, fontsize=8)

    fig.suptitle("Experiment A: time vs K  (N = 10, V = 32; median of 3 runs, bars = min-max)")
    fig.tight_layout()
    fig.savefig(f"{OUT}/graph_A_time_vs_K.png", dpi=150)
    plt.close(fig)


def graph_b():
    rows = read_summary(f"{OUT}/exp_B_summary.csv")
    k = rows[0]["K"]
    fig, (left, right) = plt.subplots(1, 2, figsize=(12, 4.8))

    for action, title, exp_label in (("add", "Add node N+1", "Expected 1/(N+1)"),
                                     ("remove", "Remove node 1", "Expected 1/N")):
        ax = left if action == "add" else right
        line(ax, rows, "N", "rate", "Consistent hashing", "o-", method="consistent", action=action)
        line(ax, rows, "N", "rate", "hash mod N", "s-", method="modn", action=action)
        x, y, _ = series(rows, "N", "expected_rate", method="consistent", action=action)
        ax.plot(x, y, "k--", label=exp_label)
        ax.set_xticks(x)
        ax.set_ylim(0, 1.05)
        ax.set_xlabel("Number of nodes N before the change")
        ax.set_ylabel("Move rate (guests moved / K)")
        ax.set_title(title)
        ax.grid(True, alpha=0.3); ax.legend()

    fig.suptitle(f"Experiment B: move rate vs N  (K = {k}, V = 32; median of 3 runs, bars = min-max)")
    fig.tight_layout()
    fig.savefig(f"{OUT}/graph_B_moves_vs_N.png", dpi=150)
    plt.close(fig)


def graph_c():
    rows = read_summary(f"{OUT}/exp_C_summary.csv")
    k = rows[0]["K"]
    fig, (left, right) = plt.subplots(1, 2, figsize=(12, 4.8))

    x = line(left, rows, "V", "cv", "CV of guests per node")
    left.set_xticks(x)
    left.set_xlabel("Virtual nodes per node V")
    left.set_ylabel("Coefficient of variation (std / mean, no unit)")
    left.set_title("Load balance (lower = more even)")
    left.grid(True, alpha=0.3); left.legend()

    line(right, rows, "V", "ring_mem_peak_mib", "Ring only (peak)")
    line(right, rows, "V", "hotel_mem_peak_mib", "Ring + guests + indexes (peak)", "s-")
    right.set_xticks(x)
    right.set_xlabel("Virtual nodes per node V")
    right.set_ylabel("Memory traced by Python (MiB)")
    right.set_title("Memory (tracemalloc)")
    right.set_yscale("log")
    right.grid(True, which="both", alpha=0.3); right.legend()

    fig.suptitle(f"Experiment C: effect of V  (N = 10, K = {k}; median of 3 runs, bars = min-max)")
    fig.tight_layout()
    fig.savefig(f"{OUT}/graph_C_effect_of_V.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    graph_a()
    graph_b()
    graph_c()
    print(f"Saved 3 graphs in {OUT}/")
