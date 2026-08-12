"""Interactive helper for filling in the gold-set worksheet. See
docs/EVALUATION.md.

python -m eval.label --file eval/worksheet.csv

Walks through each sampled order one at a time, shows its page text right
in the terminal, and prompts for each field's expected_value. This does
NOT generate any answers - every value still comes from you typing it in.
It only saves you from manually cross-referencing a spreadsheet against 25
separate text files. Progress is saved after every order, so you can quit
(Ctrl-C or `q`) and resume later - already-answered fields are skipped on
the next run unless you pass --relabel.
"""

import argparse
import csv
from pathlib import Path

QUIT_COMMANDS = {"q", "quit"}
SKIP_ORDER_COMMANDS = {"s", "skip"}


def load_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open(newline="") as f:
        return list(csv.DictReader(f))


def save_rows(csv_path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = [
        "order_id",
        "subject_raw",
        "case_number",
        "bench",
        "outcome",
        "field_name",
        "expected_value",
    ]
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def group_by_order(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    groups: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        groups.setdefault(row["order_id"], []).append(row)
    return groups


def order_is_fully_labelled(order_rows: list[dict[str, str]]) -> bool:
    return all(row["expected_value"].strip() for row in order_rows)


def print_order_header(order_rows: list[dict[str, str]]) -> None:
    first = order_rows[0]
    print("\n" + "=" * 78)
    print(
        f"order_id: {first['order_id']}   bench: {first['bench']}   "
        f"outcome: {first['outcome']}"
    )
    print(f"subject:  {first['subject_raw']}")
    print(f"case_number: {first['case_number']}")
    print("=" * 78)


def print_page_text(pages_dir: Path, order_id: str) -> None:
    text_path = pages_dir / f"order_{order_id}.txt"
    if not text_path.exists():
        print(f"(no page text file found at {text_path})")
        return
    print(text_path.read_text())
    print("-" * 78)


def label_order(order_rows: list[dict[str, str]], relabel: bool) -> str:
    """Returns 'done', 'skip', or 'quit'."""
    for row in order_rows:
        if row["expected_value"].strip() and not relabel:
            continue

        current = (
            f" [current: {row['expected_value']}]" if row["expected_value"] else ""
        )
        prompt = f"  {row['field_name']}{current} > "
        try:
            answer = input(prompt)
        except EOFError:
            return "quit"

        stripped = answer.strip()
        if stripped.lower() in QUIT_COMMANDS:
            return "quit"
        if stripped.lower() in SKIP_ORDER_COMMANDS:
            return "skip"

        row["expected_value"] = stripped

    return "done"


def run(csv_path: Path, pages_dir: Path, relabel: bool) -> None:
    rows = load_rows(csv_path)
    groups = group_by_order(rows)

    print(
        "Type the value for each field, or leave blank + Enter if it's not "
        "in the document. Commands: 's' skips the rest of this order, 'q' "
        "saves and quits."
    )

    labelled_orders = 0
    for order_id, order_rows in groups.items():
        if order_is_fully_labelled(order_rows) and not relabel:
            continue

        print_order_header(order_rows)
        print_page_text(pages_dir, order_id)

        outcome = label_order(order_rows, relabel)
        save_rows(csv_path, rows)

        if outcome == "quit":
            print(f"\nSaved. {labelled_orders} order(s) fully labelled this session.")
            return
        if outcome == "done":
            labelled_orders += 1

    print(
        f"\nAll orders processed. {labelled_orders} order(s) fully "
        "labelled this session."
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Interactively fill in the gold-set worksheet."
    )
    parser.add_argument("--file", type=str, default="eval/worksheet.csv")
    parser.add_argument(
        "--pages-dir",
        type=str,
        default=None,
        help="Defaults to a worksheet_pages/ directory next to --file.",
    )
    parser.add_argument(
        "--relabel",
        action="store_true",
        help="Re-prompt for fields that already have a value.",
    )
    args = parser.parse_args()

    csv_path = Path(args.file)
    pages_dir = (
        Path(args.pages_dir) if args.pages_dir else csv_path.parent / "worksheet_pages"
    )

    run(csv_path, pages_dir, args.relabel)


if __name__ == "__main__":
    main()
