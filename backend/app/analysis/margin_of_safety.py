"""
Margin of Safety Calculator
"""
from dataclasses import dataclass
from typing import List


@dataclass
class MarginOfSafetyResult:
    """Result of margin of safety calculation"""
    margin_of_safety: float  # Percentage
    upside_potential: float  # Percentage
    price_to_intrinsic_value: float
    recommendation: str  # 'Strong Buy', 'Buy', 'Hold', 'Avoid'
    reasoning: str


class MarginOfSafetyCalculator:
    """Calculate margin of safety and investment recommendation"""
    
    def __init__(self, current_price: float, fair_value: float):
        self.current_price = current_price
        self.fair_value = fair_value
    
    def calculate(self, business_quality_score: float = 50.0,
                  financial_health_score: float = 50.0,
                  beta: float = 1.0,
                  market_cap: float = None) -> MarginOfSafetyResult:
        """
        Calculate margin of safety with risk adjustments
        """
        if self.fair_value <= 0:
            return MarginOfSafetyResult(
                margin_of_safety=0.0,
                upside_potential=0.0,
                price_to_intrinsic_value=999.0,
                recommendation='Avoid',
                reasoning='Unable to calculate fair value. Insufficient data.'
            )
        
        # Basic margin of safety
        margin_of_safety = ((self.fair_value - self.current_price) / self.fair_value) * 100
        
        # Upside potential
        if self.current_price > 0:
            upside_potential = ((self.fair_value - self.current_price) / self.current_price) * 100
        else:
            upside_potential = 0.0
        
        # Price to Intrinsic Value ratio
        price_to_iv = self.current_price / self.fair_value
        
        # Calculate required margin based on risk
        base_required_margin = 30.0
        required_margin = base_required_margin
        
        # Adjustments
        if business_quality_score < 60:
            required_margin += 10.0
        if financial_health_score < 60:
            required_margin += 10.0
        if beta > 1.5:
            required_margin += 5.0
        if market_cap and market_cap < 2_000_000_000:  # < $2B
            required_margin += 10.0
        
        # Determine recommendation
        if margin_of_safety > 50.0 and business_quality_score > 70:
            recommendation = 'Strong Buy'
            reasoning = f"Significant margin of safety ({margin_of_safety:.1f}%) with high business quality. Stock is substantially undervalued."
        elif margin_of_safety > 30.0 and business_quality_score > 60:
            recommendation = 'Buy'
            reasoning = f"Good margin of safety ({margin_of_safety:.1f}%) with solid business quality. Stock appears undervalued."
        elif margin_of_safety > 10.0 or (business_quality_score >= 50 and business_quality_score < 60):
            recommendation = 'Hold'
            reasoning = f"Limited margin of safety ({margin_of_safety:.1f}%). Consider holding if already owned, but not attractive for new purchases."
        else:
            recommendation = 'Avoid'
            if margin_of_safety < 0:
                reasoning = f"Stock is overvalued ({abs(margin_of_safety):.1f}% above fair value). Not recommended for purchase."
            else:
                reasoning = f"Insufficient margin of safety ({margin_of_safety:.1f}%) or poor business quality. Required margin: {required_margin:.1f}%."
        
        # Add additional context to reasoning
        if business_quality_score < 50:
            reasoning += " Low business quality score increases risk."
        if financial_health_score < 50:
            reasoning += " Poor financial health increases risk."
        
        return MarginOfSafetyResult(
            margin_of_safety=margin_of_safety,
            upside_potential=upside_potential,
            price_to_intrinsic_value=price_to_iv,
            recommendation=recommendation,
            reasoning=reasoning
        )

