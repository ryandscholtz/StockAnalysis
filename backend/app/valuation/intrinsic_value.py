"""
Intrinsic Value Calculator - Aggregates multiple valuation methods
"""
from dataclasses import dataclass
from typing import Optional
import logging
from app.data.data_fetcher import CompanyData
from app.valuation.dcf_model import DCFModel
from app.valuation.earnings_power import EarningsPowerValue
from app.valuation.asset_based import AssetBasedValuation

logger = logging.getLogger(__name__)


@dataclass
class ValuationBreakdown:
    """Breakdown of valuation methods"""
    dcf: float
    earningsPower: float
    assetBased: float
    weightedAverage: float


@dataclass
class IntrinsicValueResult:
    """Result of intrinsic value calculation"""
    fair_value: float
    confidence_lower: float
    confidence_upper: float
    breakdown: ValuationBreakdown


class IntrinsicValueCalculator:
    """Main intrinsic value calculator that aggregates multiple methods"""
    
    def __init__(self, company_data: CompanyData, risk_free_rate: float = 0.04):
        self.company_data = company_data
        self.risk_free_rate = risk_free_rate
    
    def determine_business_type(self) -> str:
        """
        Determine business type for weighting based on multiple factors:
        - Revenue growth rate
        - Asset intensity (assets/revenue ratio)
        - Profitability and cash flow patterns
        - Industry characteristics
        """
        # Check revenue growth (if available) - look at multiple years for trend
        revenue_growth = 0.0
        revenue_growth_trend = []
        if self.company_data.income_statement and len(self.company_data.income_statement) >= 2:
            sorted_dates = sorted(self.company_data.income_statement.keys(), reverse=True)
            if len(sorted_dates) >= 2:
                latest = self.company_data.income_statement[sorted_dates[0]]
                previous = self.company_data.income_statement[sorted_dates[1]]
                if isinstance(latest, dict) and isinstance(previous, dict):
                    latest_rev = latest.get('Total Revenue', 0) or latest.get('Revenue', 0) or 0
                    prev_rev = previous.get('Total Revenue', 0) or previous.get('Revenue', 0) or 0
                    if prev_rev > 0:
                        revenue_growth = (latest_rev - prev_rev) / prev_rev
                
                # Calculate multi-year trend if available
                if len(sorted_dates) >= 3:
                    for i in range(min(3, len(sorted_dates) - 1)):
                        curr = self.company_data.income_statement[sorted_dates[i]]
                        prev = self.company_data.income_statement[sorted_dates[i + 1]]
                        if isinstance(curr, dict) and isinstance(prev, dict):
                            curr_rev = curr.get('Total Revenue', 0) or curr.get('Revenue', 0) or 0
                            prev_rev = prev.get('Total Revenue', 0) or prev.get('Revenue', 0) or 0
                            if prev_rev > 0:
                                revenue_growth_trend.append((curr_rev - prev_rev) / prev_rev)
        
        avg_growth = sum(revenue_growth_trend) / len(revenue_growth_trend) if revenue_growth_trend else revenue_growth
        
        # Check if asset-heavy
        asset_based = AssetBasedValuation(self.company_data)
        asset_business_type = asset_based.determine_business_type()
        
        # Calculate asset intensity (assets to revenue ratio)
        asset_intensity = 0.0
        if self.company_data.balance_sheet and self.company_data.income_statement:
            sorted_bs_dates = sorted(self.company_data.balance_sheet.keys(), reverse=True)
            sorted_is_dates = sorted(self.company_data.income_statement.keys(), reverse=True)
            if sorted_bs_dates and sorted_is_dates:
                latest_bs = self.company_data.balance_sheet[sorted_bs_dates[0]]
                latest_is = self.company_data.income_statement[sorted_is_dates[0]]
                if isinstance(latest_bs, dict) and isinstance(latest_is, dict):
                    total_assets = latest_bs.get('Total Assets', 0) or 0
                    revenue = latest_is.get('Total Revenue', 0) or latest_is.get('Revenue', 0) or 0
                    if revenue > 0:
                        asset_intensity = total_assets / revenue
        
        # Determine category with more nuanced logic
        # High growth companies (>20% revenue growth)
        if avg_growth > 0.20:
            return 'high_growth'
        # Growth companies (10-20% revenue growth)
        elif avg_growth > 0.10:
            return 'growth'
        # Distressed companies (declining revenue >10%)
        elif avg_growth < -0.10:
            return 'distressed'
        # Asset-heavy companies (high asset intensity or explicitly asset-heavy)
        elif asset_business_type == 'asset_heavy' or asset_intensity > 2.0:
            return 'asset_heavy'
        # Stable mature companies (low growth, stable)
        elif avg_growth > -0.05 and avg_growth < 0.10:
            return 'mature'
        # Cyclical or volatile (inconsistent growth patterns)
        elif len(revenue_growth_trend) >= 2:
            growth_volatility = max(revenue_growth_trend) - min(revenue_growth_trend)
            if growth_volatility > 0.30:  # High volatility
                return 'cyclical'
        
        # Default to mature
        return 'mature'
    
    def get_weights(self, business_type: str) -> tuple[float, float, float]:
        """
        Get weights for each valuation method based on business type
        
        The weighting reflects which valuation method is most appropriate for each business type:
        - DCF: Best for companies with predictable cash flows and growth
        - EPV: Best for stable, mature businesses with consistent earnings
        - Asset-Based: Best for asset-heavy businesses or liquidation scenarios
        
        Returns (dcf_weight, epv_weight, asset_weight)
        """
        weights = {
            # High growth companies: DCF is most reliable (cash flow growth is key)
            'high_growth': (0.60, 0.25, 0.15),
            
            # Growth companies: DCF primary, EPV secondary
            'growth': (0.50, 0.30, 0.20),
            
            # Mature/stable companies: Balanced between DCF and EPV
            'mature': (0.40, 0.40, 0.20),
            
            # Cyclical companies: More weight on EPV (normalized earnings)
            'cyclical': (0.35, 0.45, 0.20),
            
            # Asset-heavy companies: Asset-based valuation is most relevant
            'asset_heavy': (0.25, 0.25, 0.50),
            
            # Distressed companies: Asset-based (liquidation value) is most important
            'distressed': (0.15, 0.15, 0.70),
        }
        return weights.get(business_type, (0.40, 0.40, 0.20))  # Default to mature
    
    def _normalize_valuation_to_price_units(self, value: float) -> float:
        """Convert valuation from base currency to match current_price units (cents if needed)"""
        currency = (self.company_data.currency or '').upper()
        ticker = (self.company_data.ticker or '').upper()
        current_price = self.company_data.current_price
        
        # If price is in cents/subunits, convert valuation to cents too
        # Check if this is a cents-based currency
        if ticker.endswith('.JO') and currency == 'ZAR':
            # South African stocks: if current_price > 10, it's likely in cents
            if current_price and current_price > 10:
                # Convert from ZAR to ZAc (multiply by 100)
                return value * 100.0
        
        # Check for explicit subunit currencies
        subunit_currencies = ['ZAC', 'ZARC', 'GBX', 'GBPX']
        if currency in subunit_currencies:
            return value * 100.0
        
        # Check if currency ends with 'C' or 'X'
        if currency.endswith('C') or currency.endswith('X'):
            return value * 100.0
        
        return value
    
    def calculate(self, business_quality_score: float = None, 
                  financial_health_score: float = None) -> IntrinsicValueResult:
        """
        Calculate intrinsic value using weighted average of methods
        """
        # Calculate each valuation method
        dcf_model = DCFModel(self.company_data, self.risk_free_rate)
        dcf_result = dcf_model.calculate()
        dcf_value = dcf_result.fair_value_per_share
        # Convert to match current_price units (cents if needed)
        dcf_value = self._normalize_valuation_to_price_units(dcf_value)
        
        # Use default quality score if not provided
        quality_score = business_quality_score if business_quality_score is not None else 50.0
        epv_model = EarningsPowerValue(self.company_data, self.risk_free_rate)
        epv_result = epv_model.calculate(quality_score)
        epv_value = epv_result.fair_value_per_share
        # Convert to match current_price units (cents if needed)
        epv_value = self._normalize_valuation_to_price_units(epv_value)
        
        asset_model = AssetBasedValuation(self.company_data)
        asset_result = asset_model.calculate()
        asset_value = asset_result.fair_value_per_share
        # Convert to match current_price units (cents if needed)
        asset_value = self._normalize_valuation_to_price_units(asset_value)
        
        # Debug logging
        logger.info(f"Valuation values - DCF: {dcf_value}, EPV: {epv_value}, Asset: {asset_value}")
        
        # Determine business type and weights
        business_type = self.determine_business_type()
        dcf_weight, epv_weight, asset_weight = self.get_weights(business_type)
        
        # Calculate weighted average, but only use methods with valid (positive) values
        # If a method returns 0, redistribute its weight to the other methods
        valid_methods = []
        if dcf_value > 0:
            valid_methods.append(('dcf', dcf_value, dcf_weight))
        if epv_value > 0:
            valid_methods.append(('epv', epv_value, epv_weight))
        if asset_value > 0:
            valid_methods.append(('asset', asset_value, asset_weight))
        
        if valid_methods:
            # Redistribute weights proportionally among valid methods
            total_valid_weight = sum(w for _, _, w in valid_methods)
            if total_valid_weight > 0:
                # Normalize weights so they sum to 1.0
                normalized_weights = [(name, val, w / total_valid_weight) for name, val, w in valid_methods]
                weighted_avg = sum(val * w for _, val, w in normalized_weights)
                logger.info(f"Weighted average (using {len(valid_methods)} valid methods): {weighted_avg}")
            else:
                weighted_avg = 0.0
        else:
            # All methods returned 0 or invalid - use simple average of all (even if 0)
            weighted_avg = (dcf_value * dcf_weight) + (epv_value * epv_weight) + (asset_value * asset_weight)
            logger.warning(f"All valuation methods returned 0 or invalid. Weighted avg: {weighted_avg}")
        
        # Calculate confidence interval
        values = [dcf_value, epv_value, asset_value]
        valid_values = [v for v in values if v > 0]
        
        if valid_values:
            min_val = min(valid_values)
            max_val = max(valid_values)
            range_val = max_val - min_val
            
            confidence_lower = weighted_avg - (range_val * 0.2)
            confidence_upper = weighted_avg + (range_val * 0.2)
        else:
            confidence_lower = weighted_avg * 0.8
            confidence_upper = weighted_avg * 1.2
        
        # Apply quality adjustments (only if weighted_avg > 0)
        if weighted_avg > 0:
            if business_quality_score is not None and business_quality_score < 50:
                adjustment = 0.10  # Reduce by 10%
                weighted_avg *= (1 - adjustment)
                confidence_lower *= (1 - adjustment)
                confidence_upper *= (1 - adjustment)
                logger.info(f"Applied business quality adjustment: {adjustment*100}% reduction (score: {business_quality_score})")
            
            if financial_health_score is not None and financial_health_score < 50:
                adjustment = 0.05  # Reduce by 5%
                weighted_avg *= (1 - adjustment)
                confidence_lower *= (1 - adjustment)
                confidence_upper *= (1 - adjustment)
                logger.info(f"Applied financial health adjustment: {adjustment*100}% reduction (score: {financial_health_score})")
            
            logger.info(f"Weighted average after quality adjustments: {weighted_avg}")
        
        # Ensure non-negative and handle NaN
        import math
        if math.isnan(weighted_avg) or not math.isfinite(weighted_avg):
            weighted_avg = 0.0
        if math.isnan(confidence_lower) or not math.isfinite(confidence_lower):
            confidence_lower = 0.0
        if math.isnan(confidence_upper) or not math.isfinite(confidence_upper):
            confidence_upper = 0.0
        
        weighted_avg = max(weighted_avg, 0.0)
        confidence_lower = max(confidence_lower, 0.0)
        confidence_upper = max(confidence_upper, 0.0)
        
        # Handle NaN in individual values
        dcf_value = 0.0 if (math.isnan(dcf_value) or not math.isfinite(dcf_value)) else max(dcf_value, 0.0)
        epv_value = 0.0 if (math.isnan(epv_value) or not math.isfinite(epv_value)) else max(epv_value, 0.0)
        asset_value = 0.0 if (math.isnan(asset_value) or not math.isfinite(asset_value)) else max(asset_value, 0.0)
        weighted_avg = 0.0 if (math.isnan(weighted_avg) or not math.isfinite(weighted_avg)) else max(weighted_avg, 0.0)
        
        breakdown = ValuationBreakdown(
            dcf=dcf_value,
            earningsPower=epv_value,
            assetBased=asset_value,
            weightedAverage=weighted_avg
        )
        
        return IntrinsicValueResult(
            fair_value=weighted_avg,
            confidence_lower=confidence_lower,
            confidence_upper=confidence_upper,
            breakdown=breakdown
        )

