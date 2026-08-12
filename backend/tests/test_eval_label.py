import csv
from pathlib import Path
from unittest.mock import patch

from eval.label import (
    group_by_order,
    load_rows,
    order_is_fully_labelled,
    run,
    save_rows,
)

FIELDNAMES = [
    "order_id",
    "subject_raw",
    "case_number",
    "bench",
    "outcome",
    "field_name",
    "expected_value",
]


def _write_worksheet(path: Path, order_ids: list[str], fields: list[str]) -> None:
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for order_id in order_ids:
            for field in fields:
                writer.writerow(
                    {
                        "order_id": order_id,
                        "subject_raw": f"In the matter of Order {order_id}",
                        "case_number": f"CP(IB)/{order_id}/MB/2024",
                        "bench": "MB",
                        "outcome": "admitted",
                        "field_name": field,
                        "expected_value": "",
                    }
                )


class TestGroupByOrder:
    def test_groups_rows_by_order_id(self, tmp_path: object) -> None:
        path = Path(str(tmp_path)) / "worksheet.csv"
        _write_worksheet(path, ["1", "2"], ["corporate_debtor", "claim_amount"])
        rows = load_rows(path)
        groups = group_by_order(rows)
        assert set(groups.keys()) == {"1", "2"}
        assert len(groups["1"]) == 2


class TestOrderIsFullyLabelled:
    def test_all_blank_is_not_labelled(self) -> None:
        rows = [{"expected_value": ""}, {"expected_value": ""}]
        assert order_is_fully_labelled(rows) is False

    def test_all_filled_is_labelled(self) -> None:
        rows = [{"expected_value": "a"}, {"expected_value": "b"}]
        assert order_is_fully_labelled(rows) is True

    def test_partial_is_not_labelled(self) -> None:
        rows = [{"expected_value": "a"}, {"expected_value": ""}]
        assert order_is_fully_labelled(rows) is False


class TestRunInteractiveSession:
    def test_typed_values_are_saved(self, tmp_path: object) -> None:
        tmp = Path(str(tmp_path))
        csv_path = tmp / "worksheet.csv"
        pages_dir = tmp / "worksheet_pages"
        pages_dir.mkdir()
        _write_worksheet(csv_path, ["1"], ["corporate_debtor", "claim_amount"])
        (pages_dir / "order_1.txt").write_text("Some order text")

        with patch("builtins.input", side_effect=["Test Co Ltd", "Rs. 5,00,000"]):
            run(csv_path, pages_dir, relabel=False)

        rows = load_rows(csv_path)
        values = {r["field_name"]: r["expected_value"] for r in rows}
        assert values["corporate_debtor"] == "Test Co Ltd"
        assert values["claim_amount"] == "Rs. 5,00,000"

    def test_blank_enter_leaves_field_blank(self, tmp_path: object) -> None:
        tmp = Path(str(tmp_path))
        csv_path = tmp / "worksheet.csv"
        pages_dir = tmp / "worksheet_pages"
        pages_dir.mkdir()
        _write_worksheet(csv_path, ["1"], ["corporate_debtor", "claim_amount"])
        (pages_dir / "order_1.txt").write_text("Some order text")

        with patch("builtins.input", side_effect=["Test Co Ltd", ""]):
            run(csv_path, pages_dir, relabel=False)

        rows = load_rows(csv_path)
        values = {r["field_name"]: r["expected_value"] for r in rows}
        assert values["corporate_debtor"] == "Test Co Ltd"
        assert values["claim_amount"] == ""

    def test_quit_saves_progress_and_stops(self, tmp_path: object) -> None:
        tmp = Path(str(tmp_path))
        csv_path = tmp / "worksheet.csv"
        pages_dir = tmp / "worksheet_pages"
        pages_dir.mkdir()
        _write_worksheet(csv_path, ["1", "2"], ["corporate_debtor", "claim_amount"])
        (pages_dir / "order_1.txt").write_text("text 1")
        (pages_dir / "order_2.txt").write_text("text 2")

        with patch("builtins.input", side_effect=["Test Co Ltd", "q"]):
            run(csv_path, pages_dir, relabel=False)

        rows = load_rows(csv_path)
        by_order = group_by_order(rows)
        assert by_order["1"][0]["expected_value"] == "Test Co Ltd"
        assert by_order["1"][1]["expected_value"] == ""
        # order 2 was never reached
        assert by_order["2"][0]["expected_value"] == ""

    def test_skip_moves_to_next_order_without_saving_remaining_fields(
        self, tmp_path: object
    ) -> None:
        tmp = Path(str(tmp_path))
        csv_path = tmp / "worksheet.csv"
        pages_dir = tmp / "worksheet_pages"
        pages_dir.mkdir()
        _write_worksheet(csv_path, ["1", "2"], ["corporate_debtor", "claim_amount"])
        (pages_dir / "order_1.txt").write_text("text 1")
        (pages_dir / "order_2.txt").write_text("text 2")

        with patch(
            "builtins.input", side_effect=["s", "Second Order Co", "Rs. 1,00,000"]
        ):
            run(csv_path, pages_dir, relabel=False)

        rows = load_rows(csv_path)
        by_order = group_by_order(rows)
        assert by_order["1"][0]["expected_value"] == ""
        assert by_order["2"][0]["expected_value"] == "Second Order Co"

    def test_already_labelled_orders_are_skipped_without_prompting(
        self, tmp_path: object
    ) -> None:
        tmp = Path(str(tmp_path))
        csv_path = tmp / "worksheet.csv"
        pages_dir = tmp / "worksheet_pages"
        pages_dir.mkdir()
        _write_worksheet(csv_path, ["1"], ["corporate_debtor"])
        rows = load_rows(csv_path)
        rows[0]["expected_value"] = "Already Done Ltd"
        save_rows(csv_path, rows)
        (pages_dir / "order_1.txt").write_text("text 1")

        with patch("builtins.input", side_effect=AssertionError("should not prompt")):
            run(csv_path, pages_dir, relabel=False)

        rows_after = load_rows(csv_path)
        assert rows_after[0]["expected_value"] == "Already Done Ltd"

    def test_relabel_reprompts_already_labelled_fields(self, tmp_path: object) -> None:
        tmp = Path(str(tmp_path))
        csv_path = tmp / "worksheet.csv"
        pages_dir = tmp / "worksheet_pages"
        pages_dir.mkdir()
        _write_worksheet(csv_path, ["1"], ["corporate_debtor"])
        rows = load_rows(csv_path)
        rows[0]["expected_value"] = "Old Value"
        save_rows(csv_path, rows)
        (pages_dir / "order_1.txt").write_text("text 1")

        with patch("builtins.input", side_effect=["New Value"]):
            run(csv_path, pages_dir, relabel=True)

        rows_after = load_rows(csv_path)
        assert rows_after[0]["expected_value"] == "New Value"
