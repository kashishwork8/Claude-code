#!/usr/bin/env python3
"""
Inflation-Adjusted Investment Calculator
=========================================

Answers the question:

    "How much do I need to invest at the beginning of every month,
    starting today, to have the equivalent purchasing power of
    $1,000,000 today after X years, under different investment
    return assumptions?"

The calculator:
  1. Converts a target amount in today's money into an inflation-adjusted
     future target (the only target used in all calculations).
  2. Solves for the required beginning-of-month contribution needed to
     reach that future target under each asset-class return assumption,
     taking any initial lump-sum investment into account.
  3. Prints a summary table and plots portfolio growth over time.

Run it directly:  python investment_calculator.py
"""

from __future__ import annotations

from dataclasses import dataclass, field

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class AssetClass:
    """A single investment scenario (e.g. Savings Account, Stock Market)."""
    name: str
    annual_return_pct: float  # e.g. 3.0 for 3%


@dataclass
class UserInputs:
    target_today: float
    horizon_years: float
    initial_investment: float
    inflation_rate_pct: float
    asset_classes: list = field(default_factory=list)


@dataclass
class ScenarioResult:
    asset_class: AssetClass
    monthly_contribution: float
    initial_investment: float
    total_contributions: float
    final_value: float
    investment_growth: float
    growth_pct_of_contributions: float
    inflation_adjusted_target: float
    schedule: list  # portfolio value at each month, index 0..num_months


# ---------------------------------------------------------------------------
# Input helpers
# ---------------------------------------------------------------------------

def _prompt_float(prompt: str, default: float) -> float:
    """Prompt for a float, returning `default` if the user presses Enter."""
    raw = input(f"{prompt} [default: {default}]: ").strip()
    if raw == "":
        return default
    try:
        return float(raw.replace(",", "").replace("$", "").replace("%", ""))
    except ValueError:
        print("  Invalid number, using default.")
        return default


def get_user_inputs() -> UserInputs:
    """Collect and validate all inputs needed for the calculation."""
    print("=" * 60)
    print("INVESTMENT GOAL SETUP")
    print("=" * 60)

    # Target purchasing power in today's money
    while True:
        target_today = _prompt_float(
            "Target purchasing power in today's money ($)", 1_000_000.0
        )
        if target_today > 0:
            break
        print("  Target amount must be greater than zero.")

    # Investment horizon
    while True:
        horizon_years = _prompt_float("Investment horizon (years)", 10.0)
        if horizon_years > 0:
            break
        print("  Investment horizon must be greater than zero.")

    # Initial investment
    while True:
        initial_investment = _prompt_float("Initial investment ($)", 0.0)
        if initial_investment >= 0:
            break
        print("  Initial investment cannot be negative.")

    # Inflation rate
    while True:
        inflation_rate_pct = _prompt_float("Expected annual inflation rate (%)", 2.5)
        if inflation_rate_pct >= 0:
            break
        print("  Inflation rate cannot be negative.")

    # Asset-class return assumptions (easy to extend with more scenarios)
    print("\nAsset-class return assumptions:")
    asset_classes = []
    for name, default_return in (("Savings Account", 3.0), ("Stock Market", 12.0)):
        while True:
            annual_return_pct = _prompt_float(
                f"  {name} - expected annual return (%)", default_return
            )
            if annual_return_pct > -100:
                break
            print("  Annual return must be greater than -100%.")
        asset_classes.append(AssetClass(name=name, annual_return_pct=annual_return_pct))

    return UserInputs(
        target_today=target_today,
        horizon_years=horizon_years,
        initial_investment=initial_investment,
        inflation_rate_pct=inflation_rate_pct,
        asset_classes=asset_classes,
    )


# ---------------------------------------------------------------------------
# Core financial calculations
# ---------------------------------------------------------------------------

def calculate_inflation_adjusted_target(
    target_today: float, inflation_rate_pct: float, horizon_years: float
) -> float:
    """Convert today's target purchasing power into the equivalent future
    dollar amount needed at the end of the horizon, given inflation.

        future_target = target_today * (1 + inflation_rate) ** horizon_years
    """
    inflation_rate = inflation_rate_pct / 100.0
    return target_today * (1 + inflation_rate) ** horizon_years


def calculate_required_monthly_contribution(
    future_target: float,
    initial_investment: float,
    annual_return_pct: float,
    horizon_years: float,
) -> float:
    """Solve for the beginning-of-month contribution required to reach
    `future_target`, given monthly compounding and an annuity-due schedule.

    Future value of the initial lump sum:
        fv_initial = initial_investment * (1 + r) ** n

    Future value of an annuity-due of monthly contributions C:
        fv_contributions = C * [((1 + r) ** n - 1) / r] * (1 + r)

    where r = monthly return, n = number of months.

    Solving fv_initial + fv_contributions = future_target for C gives the
    required monthly contribution. If the initial investment alone already
    meets or exceeds the target, no further contribution is needed (0.0).
    """
    monthly_rate = (annual_return_pct / 100.0) / 12.0
    num_months = round(horizon_years * 12)

    if monthly_rate == 0:
        fv_initial = initial_investment
    else:
        fv_initial = initial_investment * (1 + monthly_rate) ** num_months

    if fv_initial >= future_target:
        return 0.0

    remaining_target = future_target - fv_initial

    if monthly_rate == 0:
        # No growth: contribution is simply spread evenly across months.
        return remaining_target / num_months

    annuity_due_factor = ((1 + monthly_rate) ** num_months - 1) / monthly_rate * (
        1 + monthly_rate
    )
    return remaining_target / annuity_due_factor


def generate_growth_schedule(
    initial_investment: float,
    monthly_contribution: float,
    annual_return_pct: float,
    horizon_years: float,
) -> list:
    """Build month-by-month portfolio values from month 0 to the end of the
    horizon, assuming contributions at the beginning of each month and
    monthly compounding.
    """
    monthly_rate = (annual_return_pct / 100.0) / 12.0
    num_months = round(horizon_years * 12)

    schedule = [initial_investment]
    balance = initial_investment
    for _ in range(num_months):
        # Contribution happens at the beginning of the month, then it grows.
        balance += monthly_contribution
        balance *= (1 + monthly_rate)
        schedule.append(balance)

    return schedule


def build_scenario_result(
    asset_class: AssetClass,
    future_target: float,
    initial_investment: float,
    horizon_years: float,
) -> ScenarioResult:
    """Run the full calculation pipeline for a single asset class."""
    monthly_contribution = calculate_required_monthly_contribution(
        future_target, initial_investment, asset_class.annual_return_pct, horizon_years
    )
    schedule = generate_growth_schedule(
        initial_investment, monthly_contribution, asset_class.annual_return_pct, horizon_years
    )
    num_months = round(horizon_years * 12)

    total_contributions = initial_investment + monthly_contribution * num_months
    final_value = schedule[-1]
    investment_growth = final_value - total_contributions
    growth_pct_of_contributions = (
        (investment_growth / total_contributions) * 100.0 if total_contributions > 0 else 0.0
    )

    return ScenarioResult(
        asset_class=asset_class,
        monthly_contribution=monthly_contribution,
        initial_investment=initial_investment,
        total_contributions=total_contributions,
        final_value=final_value,
        investment_growth=investment_growth,
        growth_pct_of_contributions=growth_pct_of_contributions,
        inflation_adjusted_target=future_target,
        schedule=schedule,
    )


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def _fmt_money(amount: float) -> str:
    return f"${amount:,.2f}"


def display_results(
    inputs: UserInputs, future_target: float, results: list
) -> None:
    """Print the goal summary, inflation-adjusted target, and comparison
    tables for all scenarios."""

    print("\n" + "=" * 60)
    print("INVESTMENT GOAL")
    print("=" * 60)
    print(f"Target purchasing power in today's money: {_fmt_money(inputs.target_today)}")
    print(f"Investment horizon: {inputs.horizon_years:g} years")
    print(f"Initial investment: {_fmt_money(inputs.initial_investment)}")
    print(f"Inflation assumption: {inputs.inflation_rate_pct:g}%")

    print("\n" + "=" * 60)
    print("INFLATION-ADJUSTED TARGET")
    print("=" * 60)
    print(
        "Future amount required to have the equivalent purchasing power of "
        f"{_fmt_money(inputs.target_today)} today: {_fmt_money(future_target)}"
    )

    print("\n" + "=" * 60)
    print("REQUIRED MONTHLY INVESTMENT")
    print("=" * 60)
    print(f"{'Scenario':<20}{'Return':<12}{'Monthly Investment':>20}")
    for r in results:
        if r.monthly_contribution == 0.0:
            note = "(initial investment already covers target)"
            print(f"{r.asset_class.name:<20}{r.asset_class.annual_return_pct:>5g}%      "
                  f"{note:>20}")
        else:
            print(
                f"{r.asset_class.name:<20}{r.asset_class.annual_return_pct:>5g}%      "
                f"{_fmt_money(r.monthly_contribution):>20}"
            )

    print("\n" + "=" * 60)
    print("DETAILED COMPARISON")
    print("=" * 60)
    header = (
        f"{'Scenario':<18}{'Monthly Inv.':>15}{'Total Contrib.':>18}"
        f"{'Inv. Growth':>16}{'Final Value':>16}{'Growth % of Contrib.':>22}"
    )
    print(header)
    for r in results:
        print(
            f"{r.asset_class.name:<18}"
            f"{_fmt_money(r.monthly_contribution):>15}"
            f"{_fmt_money(r.total_contributions):>18}"
            f"{_fmt_money(r.investment_growth):>16}"
            f"{_fmt_money(r.final_value):>16}"
            f"{r.growth_pct_of_contributions:>21.1f}%"
        )

    print("\n" + "=" * 60)
    print("ASSUMPTIONS & NOTES")
    print("=" * 60)
    print(
        "- Returns compound monthly; each scenario's annual return is\n"
        "  converted to an equivalent constant monthly rate.\n"
        "- Contributions are made at the BEGINNING of every month\n"
        "  (annuity-due), so each contribution earns a full month of\n"
        "  return before the next one is added.\n"
        "- The initial investment (if any) is invested immediately at the\n"
        "  start of the horizon and grows for the full period.\n"
        "- The inflation-adjusted target converts today's target purchasing\n"
        "  power into the future dollar amount with equivalent purchasing\n"
        "  power, using: target_today x (1 + inflation)^years.\n"
        "- Annual returns are assumed constant for the entire horizon.\n"
        "  Actual stock market returns fluctuate year to year and will not\n"
        "  produce a smooth, consistent return like 12% every year - this\n"
        "  is a simplified planning model, not a guarantee."
    )


# ---------------------------------------------------------------------------
# Chart
# ---------------------------------------------------------------------------

def _currency_formatter(value, _pos):
    return f"${value:,.0f}"


def plot_growth_chart(inputs: UserInputs, future_target: float, results: list) -> None:
    """Plot portfolio growth over time for each scenario, alongside the
    inflation-adjusted target as a horizontal reference line."""
    fig, ax = plt.subplots(figsize=(11, 6.5))

    num_months = round(inputs.horizon_years * 12)
    months = list(range(num_months + 1))

    colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]

    for i, r in enumerate(results):
        color = colors[i % len(colors)]
        ax.plot(
            months,
            r.schedule,
            label=f"{r.asset_class.name} ({r.asset_class.annual_return_pct:g}% annual return)",
            linewidth=2.2,
            color=color,
        )
        # Annotate final portfolio value at the end of the line. Scenarios
        # converge on the same target, so stagger labels vertically to
        # avoid overlapping text when final values are close together.
        ax.annotate(
            _fmt_money(r.final_value),
            xy=(months[-1], r.schedule[-1]),
            xytext=(6, 10 - i * 20),
            textcoords="offset points",
            va="center",
            fontsize=9,
            color=color,
            fontweight="bold",
        )

    # Cumulative personal contributions line (initial + monthly, no growth)
    # shown for the first scenario's contribution schedule as a reference of
    # "money in" vs. "money grown" -- helps visualize investment growth.
    for i, r in enumerate(results):
        contrib_schedule = [
            r.initial_investment + r.monthly_contribution * m for m in months
        ]
        ax.plot(
            months,
            contrib_schedule,
            linestyle="--",
            linewidth=1.2,
            color=colors[i % len(colors)],
            alpha=0.55,
            label=f"{r.asset_class.name} - cumulative contributions",
        )

    # Inflation-adjusted target reference line
    ax.axhline(
        future_target,
        color="crimson",
        linestyle=":",
        linewidth=2,
        label=f"Inflation-adjusted target ({_fmt_money(future_target)})",
    )

    ax.set_xlabel("Investment Period (Months)")
    ax.set_ylabel("Portfolio Value ($)")
    ax.set_title(
        "Portfolio Growth vs. Inflation-Adjusted Target\n"
        f"Reaching the equivalent of {_fmt_money(inputs.target_today)} today "
        f"over {inputs.horizon_years:g} years"
    )
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_currency_formatter))
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(True, alpha=0.3)

    fig.tight_layout()

    output_path = "investment_growth_chart.png"
    fig.savefig(output_path, dpi=150)
    print(f"\nChart saved to: {output_path}")

    try:
        plt.show()
    except Exception:
        # A display may not be available (e.g. headless environment);
        # the saved PNG above is the primary output in that case.
        pass


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    inputs = get_user_inputs()

    future_target = calculate_inflation_adjusted_target(
        inputs.target_today, inputs.inflation_rate_pct, inputs.horizon_years
    )

    results = [
        build_scenario_result(
            asset_class, future_target, inputs.initial_investment, inputs.horizon_years
        )
        for asset_class in inputs.asset_classes
    ]

    display_results(inputs, future_target, results)
    plot_growth_chart(inputs, future_target, results)


if __name__ == "__main__":
    main()
