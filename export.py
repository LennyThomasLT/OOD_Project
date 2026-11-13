import csv
import os

GUEST_FIELDS = ["channel_id", "sequence_id", "node_id", "room_no"]
MOVE_FIELDS = ["action", "changed_node", "channel_id", "sequence_id", "old_node", "new_node", "room_no"]


def _open(path):
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    return open(path, "w", newline="", encoding="utf-8")


def export_guests(hotel, path):
    rows = hotel.list_rooms()
    with _open(path) as f:
        w = csv.writer(f)
        w.writerow(GUEST_FIELDS)
        for node_id, room, c, s in rows:
            w.writerow([c, s, node_id, room])
    return len(rows)


def export_moves(report, path):
    with _open(path) as f:
        w = csv.writer(f)
        w.writerow(MOVE_FIELDS)
        for c, s, old, new, room in sorted(report.moves):
            w.writerow([report.action, report.node_id, c, s, old, new, room])
    return report.count


def export_rows(rows, path, fields=None):
    if fields is None:
        fields = list(rows[0].keys()) if rows else []
    with _open(path) as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    return len(rows)
