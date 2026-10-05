import csv
import sys


def load(path):
    with open(path, encoding="utf-8") as f:
        rows = list(csv.reader(f))[1:]          # lewati header
    return {(r[0], r[1]): tuple(r[2:]) for r in rows}


def main(path_before, path_after):
    before, after = load(path_before), load(path_after)
    keys = sorted(set(before) | set(after))
    diff = [(k, before.get(k), after.get(k)) for k in keys if before.get(k) != after.get(k)]

    print(f"{len(diff)} perbedaan dari {len(keys)} baris")
    for (report_id, alias), old, new in diff[:50]:
        print(f"\nreport_id={report_id}  {alias}")
        print(f"   lama: {old}")
        print(f"   baru: {new}")
    if len(diff) > 50:
        print(f"\n... dan {len(diff) - 50} perbedaan lainnya")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Pemakaian: python compare_baseline.py <before.csv> <after.csv>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])