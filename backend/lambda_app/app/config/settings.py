"""
User preferences and configuration settings
"""
from dataclasses import dataclass
from typing import List


@dataclass
class UserPreferences:
    """User investment preferences"""
    required_margin_of_safety: float = 30.0  # Default 30%
    wacc_risk_premium: float = 0.06  # 6% equity risk premium
    terminal_growth_rate: float = 0.025  # 2.5% terminal growth
    forecast_period: int = 5  # 5 years
    circle_of_competence_industries: List[str] = None
    risk_tolerance: str = "moderate"  # "conservative", "moderate", "aggressive"

    def __post_init__(self):
        if self.circle_of_competence_industries is None:
            self.circle_of_competence_industries = []


# Default settings instance
default_settings = UserPreferences()
