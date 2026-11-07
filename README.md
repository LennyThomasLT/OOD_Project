# Distributed Hilbert's Hotel — Consistent Hashing (OODS 1/2569)

Assigns guests to the buildings (nodes) of a hotel chain by **computing** where each guest
stays instead of storing it by hand: the node comes from a consistent-hashing ring
(SHA-256 truncated to 64 bits with virtual nodes) and the room number from Cantor
pairing of the guest code (c, s). Adding or removing a node moves as few guests as possible,
and the program is compared with hash mod N.

## Requirements
- Python **3.10 or newer** (developed and tested with Python 3.13)
- The program, tests and experiments use only the standard library
  (`hashlib`, `bisect`, `csv`, `math`, `time`, `tracemalloc`, `unittest`, …)
- `plot.py` only: `matplotlib` (`pip install matplotlib`). If it is not available, open
  `results/*_summary.csv` in Excel and draw the graphs there.

## How to run
```
python main.py            # text menu
python run_tests.py       # all automated tests, with PASS/FAIL and a summary
python experiments.py     # experiments A, B, C -> CSV files in results/  (about 15 s)
python plot.py            # 3 graphs (PNG) in results/ from those CSV files
```
`python experiments.py --quick` runs smaller sizes for a fast check only.

Each member's tests can also be run alone, e.g. `python test_hashring.py`.
Every test prints what it checks, the expected value, the actual value and PASS/FAIL.

## Files
| File | Contents | Member |
|---|---|---|
| `hashring.py` | `HashRing`: SHA-256 → 64-bit hash, virtual nodes, sorted list + `bisect`, wrap-around, collisions | 1 |
| `guest.py` | `room_no` (Cantor pairing), `Guest` | 2 |
| `hotel.py` | `HotelSystem`: guests, two-way indexes, search, room list, load stats | 2 |
| `hotel.py` | `add_node` / `remove_node`, `MoveReport` | 3 |
| `modn.py` | `ModNHashing` (hash mod N baseline) | 3 |
| `main.py` | Text menu (separate from the logic) | 4 |
| `export.py` | CSV export (UTF-8) | 4 |
| `experiments.py`, `plot.py` | Experiments A/B/C and graphs | 4 |
| `testkit.py`, `run_tests.py` | Shared test output format, run all tests | 4 |
| `test_hashring.py`, `test_guest.py`, `test_move.py`, `test_export.py` | Tests of members 1, 2, 3, 4 | 1–4 |
| `test_main.py` | Menu tests: keyboard input is simulated, same steps as the manual test cases | 4 |
| `results/` | Experiment CSVs, sample guest/move CSVs, graphs, `run_info.csv` | — |

## Main conventions
- Ring positions 0 … 2^64 − 1; position = first 8 bytes of SHA-256, big-endian.
- Hashed strings: guest `"{salt}|guest:{c}:{s}"`, virtual node `"{salt}|node:{node_id}:{j}"`, j = 0 … V−1.
- Points are sorted by (position, node_id, j); a guest belongs to the first point with
  position ≥ the guest's position, wrapping to the first point.
- `room_no = ((a+b)(a+b+1)) // 2 + b + 1` with a = c − 1, b = s − 1; it never changes when a guest moves.
- Node IDs are integers. Movers are found with approach A (recompute all K guests and compare).
- Operations that can fail return `(ok, message)`; `add_node` / `remove_node` return a `MoveReport`.
- Experiments: 10 channels, 3 rounds with salt 0, 1, 2, median reported with min–max.

## Output CSV columns
- Guests: `channel_id, sequence_id, node_id, room_no` (row count = number of guests)
- Moves: `action, changed_node, channel_id, sequence_id, old_node, new_node, room_no`