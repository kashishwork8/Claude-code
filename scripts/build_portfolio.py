"""Build My_Portfolio_BUILT.xlsx from the processed IBKR data.

This script ONLY assembles the workbook. It performs no market-data fetching
of its own: Data Lake sheets (Trade_Log, Market_Data, Reference_Data,
Daily_Units, Daily_Cash) are written as plain values already pulled straight
from Interactive Brokers (see scripts/reconstruct_daily_data.py and the raw
pulls under data/raw/). Every Analytics sheet (Dashboard, Positions,
Equity_Curve, Sector_Exposure, Geographic_Exposure) is 100% Excel formulas
referencing those data-lake sheets -- no calculated number is hardcoded.
"""
import csv
import json
import os

from openpyxl import Workbook
from openpyxl.chart import LineChart, PieChart, Reference
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

RAW = "data/raw"
PROC = "data/processed"
OUT_PATH = "output/My_Portfolio_BUILT.xlsx"

NAVY = "1C2541"
GREEN = "007A33"
RED = "B81D13"
ZEBRA = "F2F2F2"
FONT_NAME = "Segoe UI"

CURRENT_TICKERS = ["CGNX", "COPX", "DRAM", "DTC", "EMAAR", "EMIRATESN", "FPS", "GDXJ",
                   "HOOD", "ONDS", "RBRK", "RDDT", "SALIK", "SILJ", "STM", "URNM", "VSH", "WOLF"]
AED_TICKERS = {"DTC", "EMAAR", "EMIRATESN", "SALIK"}

header_font = Font(name=FONT_NAME, bold=True, color="FFFFFF", size=11)
header_fill = PatternFill("solid", fgColor=NAVY)
base_font = Font(name=FONT_NAME, size=10)
bold_font = Font(name=FONT_NAME, size=10, bold=True)
zebra_fill = PatternFill("solid", fgColor=ZEBRA)
title_font = Font(name=FONT_NAME, size=16, bold=True, color=NAVY)
kpi_font = Font(name=FONT_NAME, size=20, bold=True, color=NAVY)
kpi_label_font = Font(name=FONT_NAME, size=10, color="555555")

USD_FMT = '$#,##0.00'
PCT_FMT = '0.00%'
DATE_FMT = 'yyyy-mm-dd'


def style_sheet(ws, ncols):
    ws.sheet_view.showGridLines = False
    ws.sheet_view.zoomScale = 85
    ws.freeze_panes = "B2"
    for col in range(1, ncols + 1):
        ws.column_dimensions[get_column_letter(col)].width = 14


def write_header(ws, headers):
    for c, h in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=c, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 20


def zebra_rows(ws, first_row, last_row, first_col, last_col):
    for r in range(first_row, last_row + 1):
        if (r - first_row) % 2 == 1:
            for c in range(first_col, last_col + 1):
                cell = ws.cell(row=r, column=c)
                if cell.fill.fgColor.rgb in (None, "00000000"):
                    cell.fill = zebra_fill


def apply_posneg(ws, col_letter, first_row, last_row):
    rng = f"{col_letter}{first_row}:{col_letter}{last_row}"
    ws.conditional_formatting.add(
        rng, CellIsRule(operator="greaterThan", formula=["0"], font=Font(name=FONT_NAME, color=GREEN)))
    ws.conditional_formatting.add(
        rng, CellIsRule(operator="lessThan", formula=["0"], font=Font(name=FONT_NAME, color=RED)))


def load_csv(path):
    with open(path) as f:
        return list(csv.reader(f))


def main():
    os.makedirs("output", exist_ok=True)
    wb = Workbook()
    wb.remove(wb.active)

    # ---------------- Data Lake: Trade_Log ----------------
    trade_rows = load_csv(f"{PROC}/trade_log.csv")
    ws = wb.create_sheet("Trade_Log")
    headers = ["Date", "Symbol", "Company", "SecType", "Currency", "Side", "Size",
               "Price", "Commission", "NetAmount", "RealizedPnL", "Exchange", "OrderType"]
    write_header(ws, headers)
    for r, row in enumerate(trade_rows[1:], start=2):
        (trade_time, symbol, company, sec_type, currency, side, size, price,
         commission, net_amount, realized_pnl, exchange, order_type) = row
        ws.cell(row=r, column=1, value=trade_time[:10])
        ws.cell(row=r, column=2, value=symbol)
        ws.cell(row=r, column=3, value=company)
        ws.cell(row=r, column=4, value=sec_type)
        ws.cell(row=r, column=5, value=currency)
        ws.cell(row=r, column=6, value=side)
        ws.cell(row=r, column=7, value=float(size))
        ws.cell(row=r, column=8, value=float(price)).number_format = '#,##0.0000'
        ws.cell(row=r, column=9, value=float(commission)).number_format = USD_FMT
        ws.cell(row=r, column=10, value=float(net_amount)).number_format = USD_FMT
        ws.cell(row=r, column=11, value=float(realized_pnl)).number_format = USD_FMT
        ws.cell(row=r, column=12, value=exchange)
        ws.cell(row=r, column=13, value=order_type)
    last_trade_row = len(trade_rows)
    for r in range(2, last_trade_row + 1):
        for c in range(1, 14):
            ws.cell(row=r, column=c).font = base_font
    zebra_rows(ws, 2, last_trade_row, 1, 13)
    style_sheet(ws, 13)

    # ---------------- Data Lake: Market_Data ----------------
    md_rows = load_csv(f"{PROC}/market_data.csv")
    md_header = md_rows[0]  # date, CGNX, ..., USD_AED
    ws = wb.create_sheet("Market_Data")
    write_header(ws, ["Date"] + md_header[1:])
    for r, row in enumerate(md_rows[1:], start=2):
        ws.cell(row=r, column=1, value=row[0]).number_format = DATE_FMT
        for c, val in enumerate(row[1:], start=2):
            ws.cell(row=r, column=c, value=float(val)).number_format = '#,##0.0000'
    last_md_row = len(md_rows)
    for r in range(2, last_md_row + 1):
        for c in range(1, len(md_header) + 1):
            ws.cell(row=r, column=c).font = base_font
    zebra_rows(ws, 2, last_md_row, 1, len(md_header))
    style_sheet(ws, len(md_header))
    md_ticker_col = {t: get_column_letter(2 + i) for i, t in enumerate(md_header[1:])}

    # ---------------- Data Lake: Reference_Data ----------------
    ref = json.load(open(f"{RAW}/reference_data.json"))
    pos_rows = load_csv(f"{PROC}/positions_current.csv")
    pos_map = {r[0]: r for r in pos_rows[1:]}  # ticker -> [ticker, shares, avg_cost, currency]

    ws = wb.create_sheet("Reference_Data")
    write_header(ws, ["Ticker", "Company", "Sector", "Industry", "Country", "Beta", "AvgCost", "Currency"])
    for r, ticker in enumerate(CURRENT_TICKERS, start=2):
        info = ref[ticker]
        avg_cost = float(pos_map[ticker][2])
        currency = pos_map[ticker][3]
        ws.cell(row=r, column=1, value=ticker)
        ws.cell(row=r, column=2, value=info["company_name"])
        ws.cell(row=r, column=3, value=info["sector"])
        ws.cell(row=r, column=4, value=info["industry"])
        ws.cell(row=r, column=5, value=info["country"])
        ws.cell(row=r, column=6, value=info["beta"] if info["beta"] is not None else "N/A")
        ws.cell(row=r, column=7, value=avg_cost).number_format = '#,##0.0000'
        ws.cell(row=r, column=8, value=currency)
    last_ref_row = 1 + len(CURRENT_TICKERS)
    for r in range(2, last_ref_row + 1):
        for c in range(1, 9):
            ws.cell(row=r, column=c).font = base_font
    zebra_rows(ws, 2, last_ref_row, 1, 8)
    style_sheet(ws, 8)

    # ---------------- Data Lake: Daily_Units ----------------
    du_rows = load_csv(f"{PROC}/daily_units.csv")
    du_header = du_rows[0]
    ws = wb.create_sheet("Daily_Units")
    write_header(ws, ["Date"] + du_header[1:])
    for r, row in enumerate(du_rows[1:], start=2):
        ws.cell(row=r, column=1, value=row[0]).number_format = DATE_FMT
        for c, val in enumerate(row[1:], start=2):
            ws.cell(row=r, column=c, value=float(val))
    last_du_row = len(du_rows)
    for r in range(2, last_du_row + 1):
        for c in range(1, len(du_header) + 1):
            ws.cell(row=r, column=c).font = base_font
    zebra_rows(ws, 2, last_du_row, 1, len(du_header))
    style_sheet(ws, len(du_header))
    du_ticker_col = {t: get_column_letter(2 + i) for i, t in enumerate(du_header[1:])}

    # ---------------- Data Lake: Daily_Cash ----------------
    dc_rows = load_csv(f"{PROC}/daily_cash.csv")
    ws = wb.create_sheet("Daily_Cash")
    write_header(ws, ["Date", "NAV", "InvestedValue_Estimate", "Cash"])
    for r, row in enumerate(dc_rows[1:], start=2):
        date, nav, invested, cash = row
        ws.cell(row=r, column=1, value=date).number_format = DATE_FMT
        ws.cell(row=r, column=2, value=float(nav)).number_format = USD_FMT
        ws.cell(row=r, column=3, value=float(invested)).number_format = USD_FMT
        ws.cell(row=r, column=4, value=float(cash)).number_format = USD_FMT
    last_dc_row = len(dc_rows)
    for r in range(2, last_dc_row + 1):
        for c in range(1, 5):
            ws.cell(row=r, column=c).font = base_font
    zebra_rows(ws, 2, last_dc_row, 1, 4)
    style_sheet(ws, 4)

    # ================= Analytics: Positions =================
    ws = wb.create_sheet("Positions")
    headers = ["Ticker", "Company", "Sector", "Currency", "Shares", "Avg Cost", "Current Price",
               "Day Change %", "Cost Basis ($)", "Market Value ($)", "Unrealized P&L ($)",
               "P&L %", "Portfolio Weight"]
    write_header(ws, headers)
    n = len(CURRENT_TICKERS)
    first_pos_row, last_pos_row = 2, 1 + n
    for i, ticker in enumerate(CURRENT_TICKERS):
        r = 2 + i
        ref_row = 2 + i  # Reference_Data rows are in the same ticker order
        md_col = md_ticker_col[ticker]
        du_col = du_ticker_col[ticker]
        is_aed = ticker in AED_TICKERS
        fx_ref = f"'Market_Data'!$T${last_md_row}"  # USD_AED column, today's rate

        ws.cell(row=r, column=1, value=f"='Reference_Data'!A{ref_row}")
        ws.cell(row=r, column=2, value=f"='Reference_Data'!B{ref_row}")
        ws.cell(row=r, column=3, value=f"='Reference_Data'!C{ref_row}")
        ws.cell(row=r, column=4, value=f"='Reference_Data'!H{ref_row}")
        ws.cell(row=r, column=5, value=f"='Daily_Units'!{du_col}${last_du_row}")
        ws.cell(row=r, column=6, value=f"='Reference_Data'!G{ref_row}").number_format = '#,##0.0000'
        ws.cell(row=r, column=7, value=f"='Market_Data'!{md_col}${last_md_row}").number_format = '#,##0.0000'
        ws.cell(row=r, column=8,
                value=(f"=('Market_Data'!{md_col}${last_md_row}-'Market_Data'!{md_col}${last_md_row - 1})"
                       f"/'Market_Data'!{md_col}${last_md_row - 1}")).number_format = PCT_FMT
        fx_div = f"/{fx_ref}" if is_aed else ""
        ws.cell(row=r, column=9, value=f"=E{r}*F{r}{fx_div}").number_format = USD_FMT
        ws.cell(row=r, column=10, value=f"=E{r}*G{r}{fx_div}").number_format = USD_FMT
        ws.cell(row=r, column=11, value=f"=J{r}-I{r}").number_format = USD_FMT
        ws.cell(row=r, column=12, value=f"=IFERROR(K{r}/I{r},0)").number_format = PCT_FMT
        ws.cell(row=r, column=13,
                value=f"=J{r}/SUM($J${first_pos_row}:$J${last_pos_row})").number_format = PCT_FMT
        for c in range(1, 14):
            ws.cell(row=r, column=c).font = base_font
    zebra_rows(ws, first_pos_row, last_pos_row, 1, 13)
    apply_posneg(ws, "H", first_pos_row, last_pos_row)
    apply_posneg(ws, "K", first_pos_row, last_pos_row)
    apply_posneg(ws, "L", first_pos_row, last_pos_row)
    style_sheet(ws, 13)
    ws.column_dimensions["B"].width = 26

    # ================= Analytics: Equity_Curve =================
    ws = wb.create_sheet("Equity_Curve")
    headers = ["Date", "Cash ($)", "Invested Value ($)", "Total NAV ($)",
               "Daily Return", "Cumulative Return", "Drawdown"]
    write_header(ws, headers)
    first_eq_row, last_eq_row = 2, last_dc_row
    for r in range(first_eq_row, last_eq_row + 1):
        ws.cell(row=r, column=1, value=f"='Daily_Cash'!A{r}").number_format = DATE_FMT
        ws.cell(row=r, column=2, value=f"='Daily_Cash'!D{r}").number_format = USD_FMT
        ws.cell(row=r, column=3, value=f"=D{r}-B{r}").number_format = USD_FMT
        ws.cell(row=r, column=4, value=f"='Daily_Cash'!B{r}").number_format = USD_FMT
        if r == first_eq_row:
            ws.cell(row=r, column=5, value=0).number_format = PCT_FMT
        else:
            ws.cell(row=r, column=5, value=f"=D{r}/D{r - 1}-1").number_format = PCT_FMT
        ws.cell(row=r, column=6, value=f"=D{r}/D${first_eq_row}-1").number_format = PCT_FMT
        ws.cell(row=r, column=7, value=f"=D{r}/MAX(D${first_eq_row}:D{r})-1").number_format = PCT_FMT
        for c in range(1, 8):
            ws.cell(row=r, column=c).font = base_font
    zebra_rows(ws, first_eq_row, last_eq_row, 1, 7)
    apply_posneg(ws, "E", first_eq_row, last_eq_row)
    apply_posneg(ws, "F", first_eq_row, last_eq_row)
    apply_posneg(ws, "G", first_eq_row, last_eq_row)
    style_sheet(ws, 7)

    # ================= Analytics: Sector_Exposure =================
    sectors = sorted({ref[t]["sector"] for t in CURRENT_TICKERS})
    ws = wb.create_sheet("Sector_Exposure")
    write_header(ws, ["Sector", "Market Value ($)", "Weight"])
    first_se_row = 2
    for i, sector in enumerate(sectors):
        r = 2 + i
        ws.cell(row=r, column=1, value=sector)
        ws.cell(row=r, column=2,
                value=f'=SUMIF(Positions!$C${first_pos_row}:$C${last_pos_row},A{r},'
                      f'Positions!$J${first_pos_row}:$J${last_pos_row})').number_format = USD_FMT
        ws.cell(row=r, column=3, value=f"=B{r}/SUM($B$2:$B${1 + len(sectors)})").number_format = PCT_FMT
        for c in range(1, 4):
            ws.cell(row=r, column=c).font = base_font
    last_se_row = 1 + len(sectors)
    zebra_rows(ws, 2, last_se_row, 1, 3)
    style_sheet(ws, 3)
    ws.column_dimensions["A"].width = 28

    # ================= Analytics: Geographic_Exposure =================
    countries = sorted({ref[t]["country"] for t in CURRENT_TICKERS})
    ws = wb.create_sheet("Geographic_Exposure")
    write_header(ws, ["Country", "Market Value ($)", "Weight"])
    for i, country in enumerate(countries):
        r = 2 + i
        ws.cell(row=r, column=1, value=country)
        # Matched against Reference_Data's Country column (not Positions' Currency) since
        # currency codes don't uniquely map to country for tickers like STM/URNM.
        ws.cell(row=r, column=2,
                value=(f'=SUMPRODUCT((\'Reference_Data\'!$E$2:$E${last_ref_row}=A{r})*'
                       f'Positions!$J${first_pos_row}:$J${last_pos_row})')).number_format = USD_FMT
        ws.cell(row=r, column=3, value=f"=B{r}/SUM($B$2:$B${1 + len(countries)})").number_format = PCT_FMT
        for c in range(1, 4):
            ws.cell(row=r, column=c).font = base_font
    last_ge_row = 1 + len(countries)
    zebra_rows(ws, 2, last_ge_row, 1, 3)
    style_sheet(ws, 3)
    ws.column_dimensions["A"].width = 28

    # ================= Analytics: Dashboard =================
    ws = wb.create_sheet("Dashboard", 0)
    ws.sheet_view.showGridLines = False
    ws.sheet_view.zoomScale = 85
    ws.column_dimensions["A"].width = 3
    for col in "BCDEFGH":
        ws.column_dimensions[col].width = 16

    ws["B2"] = "Portfolio Dashboard"
    ws["B2"].font = title_font

    kpis = [
        ("Net Asset Value", f"=Equity_Curve!D{last_eq_row}", USD_FMT),
        ("Total Return", f"=Equity_Curve!F{last_eq_row}", PCT_FMT),
        ("Sharpe Ratio (ann.)",
         f"=AVERAGE(Equity_Curve!E{first_eq_row + 1}:E{last_eq_row})/"
         f"STDEV(Equity_Curve!E{first_eq_row + 1}:E{last_eq_row})*SQRT(252)", '0.00'),
        ("Max Drawdown", f"=MIN(Equity_Curve!G{first_eq_row}:G{last_eq_row})", PCT_FMT),
    ]
    for i, (label, formula, fmt) in enumerate(kpis):
        col = get_column_letter(2 + i * 2)
        ws[f"{col}4"] = label
        ws[f"{col}4"].font = kpi_label_font
        ws[f"{col}5"] = formula
        ws[f"{col}5"].font = kpi_font
        ws[f"{col}5"].number_format = fmt
    apply_posneg(ws, get_column_letter(2 * 2), 5, 5)  # Total Return
    apply_posneg(ws, get_column_letter(4 * 2), 5, 5)  # Max Drawdown

    ws["B8"] = "Cash"
    ws["B8"].font = kpi_label_font
    ws["B9"] = f"=Equity_Curve!B{last_eq_row}"
    ws["B9"].number_format = USD_FMT
    ws["B9"].font = Font(name=FONT_NAME, size=14, bold=True, color=NAVY)
    ws["D8"] = "Invested Value"
    ws["D8"].font = kpi_label_font
    ws["D9"] = f"=Equity_Curve!C{last_eq_row}"
    ws["D9"].number_format = USD_FMT
    ws["D9"].font = Font(name=FONT_NAME, size=14, bold=True, color=NAVY)

    # NAV line chart
    line = LineChart()
    line.title = "NAV Over Time"
    line.style = 2
    line.y_axis.title = "NAV ($)"
    line.x_axis.title = "Date"
    line.height, line.width = 9, 18
    data_ref = Reference(wb["Equity_Curve"], min_col=4, min_row=1, max_row=last_eq_row)
    cats_ref = Reference(wb["Equity_Curve"], min_col=1, min_row=2, max_row=last_eq_row)
    line.add_data(data_ref, titles_from_data=True)
    line.set_categories(cats_ref)
    line.series[0].graphicalProperties.line.solidFill = NAVY
    line.series[0].graphicalProperties.line.width = 20000
    ws.add_chart(line, "B12")

    # Allocation pie chart
    pie = PieChart()
    pie.title = "Portfolio Allocation by Position"
    pie.height, pie.width = 9, 12
    pdata = Reference(wb["Positions"], min_col=10, min_row=1, max_row=last_pos_row)
    pcats = Reference(wb["Positions"], min_col=1, min_row=first_pos_row, max_row=last_pos_row)
    pie.add_data(pdata, titles_from_data=True)
    pie.set_categories(pcats)
    ws.add_chart(pie, "J12")

    wb.save(OUT_PATH)
    print("Saved", OUT_PATH)


if __name__ == "__main__":
    main()
