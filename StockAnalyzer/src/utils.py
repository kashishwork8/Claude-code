"""General-purpose helpers shared across the StockAnalyzer package.

This module intentionally has no dependency on the other ``src`` modules so
that it can be imported anywhere (data loading, indicators, plotting,
reporting) without creating circular imports.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Iterable, List

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

# A ticker is 1-10 upper-case letters, optionally followed by a dot/hyphen
# and a share-class suffix, e.g. "AAPL", "BRK.B", "BF-B".
_TICKER_PATTERN = re.compile(r"^[A-Z]{1,10}([.\-][A-Z]{1,4})?$")

HEADER_FILL = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
HEADER_FONT = Font(bold=True, color="FFFFFF")


def print_header(title: str) -> None:
    """Print a visually distinct section header to the console."""
    width = max(60, len(title) + 4)
    print("\n" + "=" * width)
    print(title.center(width))
    print("=" * width)


def print_subheader(title: str) -> None:
    """Print a lightweight subsection divider to the console."""
    print(f"\n--- {title} ---")


def print_warning(message: str) -> None:
    """Print a warning message with a consistent, greppable prefix."""
    print(f"[WARNING] {message}")


def print_error(message: str) -> None:
    """Print an error message with a consistent, greppable prefix."""
    print(f"[ERROR] {message}")


def print_success(message: str) -> None:
    """Print a success message with a consistent, greppable prefix."""
    print(f"[OK] {message}")


def parse_ticker_input(raw_input: str) -> List[str]:
    """Split a raw comma/space separated ticker string into a clean list.

    Args:
        raw_input: Free-form user input, e.g. ``"msft, nvda  aapl"``.

    Returns:
        A list of upper-cased, de-duplicated tickers preserving order.
    """
    if not raw_input:
        return []
    # Support both comma and whitespace as separators.
    tokens = [t for chunk in raw_input.split(",") for t in chunk.split()]
    seen: dict[str, None] = {}
    for token in tokens:
        cleaned = token.strip().upper()
        if cleaned:
            seen.setdefault(cleaned, None)
    return list(seen.keys())


def is_valid_ticker_format(ticker: str) -> bool:
    """Check whether a string looks like a plausible stock ticker.

    This is a cheap, offline sanity check performed *before* hitting the
    network. It does not guarantee the ticker exists, only that it is worth
    attempting to download.
    """
    return bool(_TICKER_PATTERN.match(ticker))


def validate_tickers(tickers: Iterable[str]) -> tuple[List[str], List[str]]:
    """Split tickers into those that pass basic format validation and those
    that don't.

    Returns:
        A tuple ``(valid, invalid)``.
    """
    valid, invalid = [], []
    for ticker in tickers:
        (valid if is_valid_ticker_format(ticker) else invalid).append(ticker)
    return valid, invalid


def ensure_directories(*paths: Path) -> None:
    """Create every directory in ``paths`` if it does not already exist."""
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def format_percent(value: float, decimals: int = 2) -> str:
    """Format a fractional or percentage float as a human-readable string."""
    return f"{value:.{decimals}f}%"


def _style_header_row(worksheet: Worksheet) -> None:
    """Bold and color the first row of a worksheet."""
    for cell in worksheet[1]:
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center")


def _autosize_columns(worksheet: Worksheet, min_width: int = 10, max_width: int = 40) -> None:
    """Resize every column in ``worksheet`` to fit its widest cell value."""
    for column_cells in worksheet.columns:
        first_cell = next((c for c in column_cells if c.value is not None), None)
        if first_cell is None:
            continue
        column_letter = get_column_letter(first_cell.column)
        longest = max(
            (len(str(cell.value)) for cell in column_cells if cell.value is not None),
            default=min_width,
        )
        worksheet.column_dimensions[column_letter].width = max(min_width, min(longest + 2, max_width))


def _apply_percent_format(worksheet: Worksheet, column_letters: Iterable[str], start_row: int = 2) -> None:
    """Apply a percentage number format to the given columns."""
    for column_letter in column_letters:
        for row in range(start_row, worksheet.max_row + 1):
            worksheet[f"{column_letter}{row}"].number_format = "0.00%"


def write_dataframe_to_sheet(workbook: Workbook, sheet_name: str, dataframe) -> Worksheet:
    """Write a pandas DataFrame to a new worksheet with headers.

    Args:
        workbook: The target ``openpyxl`` workbook.
        sheet_name: Name of the worksheet to create.
        dataframe: Data to write, one row per record.

    Returns:
        The newly created worksheet, for further formatting by the caller.
    """
    worksheet = workbook.create_sheet(title=sheet_name)
    worksheet.append(list(dataframe.columns))
    for row in dataframe.itertuples(index=False):
        worksheet.append(list(row))
    _style_header_row(worksheet)
    _autosize_columns(worksheet)
    worksheet.freeze_panes = "A2"
    return worksheet


def build_daily_returns_frame(daily_returns_by_ticker: Dict[str, pd.Series]) -> pd.DataFrame:
    """Combine each ticker's daily-return series into one wide DataFrame.

    Returns:
        A DataFrame with a ``Date`` column plus one column per ticker,
        sorted chronologically. Missing values (e.g. tickers with a
        shorter history) are left blank rather than dropped.
    """
    combined = pd.DataFrame({ticker: series for ticker, series in daily_returns_by_ticker.items()})
    combined = combined.sort_index()
    combined.index.name = "Date"
    return combined.reset_index()


def generate_excel_report(
    output_path: Path,
    summary_df: pd.DataFrame,
    signals_df: pd.DataFrame,
    daily_returns_df: pd.DataFrame,
) -> None:
    """Write the full multi-sheet Excel workbook described in the README.

    Args:
        output_path: Destination ``.xlsx`` path.
        summary_df: One row per ticker with headline stats.
        signals_df: One row per detected Golden/Death Cross event.
        daily_returns_df: Wide-format daily returns, one column per ticker.
    """
    workbook = Workbook()
    workbook.remove(workbook.active)  # Drop the default blank sheet.

    summary_ws = write_dataframe_to_sheet(workbook, "Summary", summary_df)
    percent_columns = {"Total Return", "Annual Return", "Maximum Drawdown"}
    for idx, column_name in enumerate(summary_df.columns, start=1):
        if column_name in percent_columns:
            _apply_percent_format(summary_ws, [get_column_letter(idx)])

    write_dataframe_to_sheet(workbook, "Signals", signals_df)

    returns_ws = write_dataframe_to_sheet(workbook, "Daily Returns", daily_returns_df)
    return_columns = [get_column_letter(i) for i in range(2, len(daily_returns_df.columns) + 1)]
    _apply_percent_format(returns_ws, return_columns)

    workbook.save(output_path)
