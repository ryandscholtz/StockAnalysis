"""
Financial constants and assumptions
"""
# Risk-free rate (will be fetched from FRED, but default here)
DEFAULT_RISK_FREE_RATE = 0.04  # 4%

# Equity risk premium
EQUITY_RISK_PREMIUM = 0.06  # 6%

# Terminal growth rate (GDP growth)
TERMINAL_GROWTH_RATE = 0.025  # 2.5%

# Corporate tax rate
CORPORATE_TAX_RATE = 0.21  # 21%

# Default capitalization rate for EPV
DEFAULT_CAP_RATE = 0.10  # 10%

# Forecast period for DCF
DEFAULT_FORECAST_PERIOD = 5  # 5 years

# Required margin of safety thresholds
MARGIN_STRONG_BUY = 50.0  # %
MARGIN_BUY = 30.0  # %
MARGIN_HOLD = 10.0  # %

# Financial health thresholds
CURRENT_RATIO_GOOD = 1.5
CURRENT_RATIO_WARNING = 1.0
QUICK_RATIO_GOOD = 1.0
QUICK_RATIO_WARNING = 0.5
DEBT_TO_EQUITY_GOOD = 0.5
DEBT_TO_EQUITY_WARNING = 1.0
INTEREST_COVERAGE_GOOD = 5.0
INTEREST_COVERAGE_WARNING = 2.0
ROE_GOOD = 0.15  # 15%
ROE_WARNING = 0.10  # 10%
ROIC_GOOD = 0.12  # 12%
ROIC_WARNING = 0.08  # 8%
ROA_GOOD = 0.08  # 8%
ROA_WARNING = 0.05  # 5%
FCF_MARGIN_GOOD = 10.0  # 10%
FCF_MARGIN_WARNING = 5.0  # 5%

