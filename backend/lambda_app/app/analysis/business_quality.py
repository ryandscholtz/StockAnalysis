"""
Business Quality Assessment
"""
from dataclasses import dataclass
from typing import List
from app.data.data_fetcher import CompanyData
from app.api.models import BusinessQuality
import numpy as np


class BusinessQualityAnalyzer:
    """Analyze business quality and competitive moats"""

    def __init__(self, company_data: CompanyData):
        self.company_data = company_data

    def assess_brand_strength(self) -> float:
        """Assess brand strength (0-10 points)"""
        score = 0.0

        # Check gross margin trends (pricing power indicator)
        if self.company_data.income_statement:
            sorted_dates = sorted(self.company_data.income_statement.keys(), reverse=True)[:5]
            gross_margins = []

            for date in sorted_dates:
                income = self.company_data.income_statement.get(date, {})
                if isinstance(income, dict):
                    revenue = income.get('Total Revenue', 0) or income.get('Revenue', 0) or 0
                    cogs = abs(income.get('Cost Of Revenue', 0) or income.get('Cost Of Goods Sold', 0) or 0)
                    if revenue > 0:
                        gross_margin = ((revenue - cogs) / revenue) * 100
                        gross_margins.append(gross_margin)

            if gross_margins:
                avg_margin = np.mean(gross_margins)
                if avg_margin > 40:
                    score = 8.0  # Market leader
                elif avg_margin > 30:
                    score = 6.0  # Strong
                elif avg_margin > 20:
                    score = 4.0  # Moderate
                else:
                    score = 2.0  # Weak

        return score

    def assess_network_effects(self) -> float:
        """Assess network effects (0-10 points)"""
        # This is simplified - in reality would need industry-specific analysis
        # For now, check if it's a platform/tech company
        industry = (self.company_data.industry or '').lower()
        sector = (self.company_data.sector or '').lower()

        network_industries = ['technology', 'software', 'internet', 'social media', 'platform']

        if any(keyword in industry or keyword in sector for keyword in network_industries):
            # Check user growth if available (would need additional data)
            return 6.0  # Moderate network effects assumed

        return 3.0  # Limited network effects

    def assess_cost_advantages(self) -> float:
        """Assess cost advantages (0-10 points)"""
        score = 0.0

        # Check operating margin trends (operational efficiency)
        if self.company_data.income_statement:
            sorted_dates = sorted(self.company_data.income_statement.keys(), reverse=True)[:5]
            operating_margins = []

            for date in sorted_dates:
                income = self.company_data.income_statement.get(date, {})
                if isinstance(income, dict):
                    revenue = income.get('Total Revenue', 0) or income.get('Revenue', 0) or 0
                    operating_income = income.get('Operating Income', 0) or income.get('EBIT', 0) or 0
                    if revenue > 0:
                        op_margin = (operating_income / revenue) * 100
                        operating_margins.append(op_margin)

            if operating_margins:
                avg_margin = np.mean(operating_margins)
                if avg_margin > 20:
                    score = 8.0  # Significant
                elif avg_margin > 10:
                    score = 5.0  # Moderate
                else:
                    score = 2.0  # None

        return score

    def assess_regulatory_barriers(self) -> float:
        """Assess regulatory barriers (0-10 points)"""
        # This is simplified - would need industry-specific knowledge
        industry = (self.company_data.industry or '').lower()
        sector = (self.company_data.sector or '').lower()

        high_barrier_industries = ['banking', 'pharmaceutical', 'telecommunications', 'utilities', 'insurance']

        if any(keyword in industry or keyword in sector for keyword in high_barrier_industries):
            return 7.0  # High barriers

        return 3.0  # Low barriers

    def assess_market_position(self) -> float:
        """Assess market position (0-20 points)"""
        score = 0.0

        # Market share ranking would require industry data
        # For now, use market cap as proxy (larger = better position)
        if self.company_data.market_cap:
            if self.company_data.market_cap > 100_000_000_000:  # > $100B
                score = 10.0  # Likely #1 or #2
            elif self.company_data.market_cap > 10_000_000_000:  # > $10B
                score = 7.0  # Top 5
            elif self.company_data.market_cap > 1_000_000_000:  # > $1B
                score = 4.0  # Top 10
            else:
                score = 2.0  # Below top 10

        # Market share trend (simplified - check revenue growth)
        if self.company_data.income_statement and len(self.company_data.income_statement) >= 2:
            sorted_dates = sorted(self.company_data.income_statement.keys(), reverse=True)
            if len(sorted_dates) >= 2:
                latest = self.company_data.income_statement[sorted_dates[0]]
                previous = self.company_data.income_statement[sorted_dates[1]]
                if isinstance(latest, dict) and isinstance(previous, dict):
                    latest_rev = latest.get('Total Revenue', 0) or latest.get('Revenue', 0) or 0
                    prev_rev = previous.get('Total Revenue', 0) or previous.get('Revenue', 0) or 0
                    if prev_rev > 0:
                        growth = (latest_rev - prev_rev) / prev_rev
                        if growth > 0.1:
                            score += 5.0  # Growing
                        elif growth > 0:
                            score += 3.0  # Stable
                        else:
                            score += 0.0  # Declining

        return min(score, 20.0)

    def assess_business_model(self) -> float:
        """Assess business model quality (0-20 points)"""
        score = 0.0

        # Recurring revenue (simplified - check revenue stability)
        if self.company_data.income_statement:
            sorted_dates = sorted(self.company_data.income_statement.keys(), reverse=True)[:5]
            revenues = []
            for date in sorted_dates:
                income = self.company_data.income_statement.get(date, {})
                if isinstance(income, dict):
                    revenue = income.get('Total Revenue', 0) or income.get('Revenue', 0) or 0
                    if revenue > 0:
                        revenues.append(revenue)

            if revenues:
                # Check consistency
                cv = np.std(revenues) / np.mean(revenues) if np.mean(revenues) > 0 else 1.0
                if cv < 0.2:
                    score += 10.0  # High recurring revenue
                elif cv < 0.4:
                    score += 5.0  # Moderate

        # Capital efficiency (check CapEx relative to revenue)
        if self.company_data.cashflow and self.company_data.income_statement:
            sorted_dates = sorted(self.company_data.cashflow.keys(), reverse=True)[:3]
            capex_ratios = []

            for date in sorted_dates:
                cf = self.company_data.cashflow.get(date, {})
                income = self.company_data.income_statement.get(date, {})
                if isinstance(cf, dict) and isinstance(income, dict):
                    capex = abs(cf.get('Capital Expenditures', 0) or 0)
                    revenue = income.get('Total Revenue', 0) or income.get('Revenue', 0) or 0
                    if revenue > 0:
                        capex_ratio = (capex / revenue) * 100
                        capex_ratios.append(capex_ratio)

            if capex_ratios:
                avg_capex_ratio = np.mean(capex_ratios)
                if avg_capex_ratio < 5:
                    score += 10.0  # Low CapEx needs
                elif avg_capex_ratio < 10:
                    score += 5.0  # Moderate

        return min(score, 20.0)

    def assess_financial_characteristics(self) -> float:
        """Assess financial characteristics (0-20 points)"""
        score = 0.0

        if self.company_data.income_statement:
            sorted_dates = sorted(self.company_data.income_statement.keys(), reverse=True)[:5]

            gross_margins = []
            operating_margins = []

            for date in sorted_dates:
                income = self.company_data.income_statement.get(date, {})
                if isinstance(income, dict):
                    revenue = income.get('Total Revenue', 0) or income.get('Revenue', 0) or 0
                    cogs = abs(income.get('Cost Of Revenue', 0) or income.get('Cost Of Goods Sold', 0) or 0)
                    operating_income = income.get('Operating Income', 0) or income.get('EBIT', 0) or 0

                    if revenue > 0:
                        gross_margin = ((revenue - cogs) / revenue) * 100
                        op_margin = (operating_income / revenue) * 100
                        gross_margins.append(gross_margin)
                        operating_margins.append(op_margin)

            # Gross margin
            if gross_margins:
                avg_gross = np.mean(gross_margins)
                if avg_gross > 40:
                    score += 7.0
                elif avg_gross > 30:
                    score += 5.0
                elif avg_gross > 20:
                    score += 3.0

            # Operating margin
            if operating_margins:
                avg_op = np.mean(operating_margins)
                if avg_op > 20:
                    score += 7.0
                elif avg_op > 10:
                    score += 5.0
                elif avg_op > 5:
                    score += 3.0

            # ROIC trend (simplified)
            score += 6.0  # Assume stable for now

        return min(score, 20.0)

    def identify_moat_indicators(self, moat_scores: dict) -> List[str]:
        """Identify which moats are present"""
        indicators = []

        if moat_scores.get('brand', 0) >= 7:
            indicators.append('Brand Strength')
        if moat_scores.get('network', 0) >= 6:
            indicators.append('Network Effects')
        if moat_scores.get('cost', 0) >= 7:
            indicators.append('Cost Advantages')
        if moat_scores.get('regulatory', 0) >= 6:
            indicators.append('Regulatory Barriers')

        return indicators

    def analyze(self) -> BusinessQuality:
        """Perform comprehensive business quality analysis"""
        # Assess competitive moat (0-40 points)
        brand_score = self.assess_brand_strength()
        network_score = self.assess_network_effects()
        cost_score = self.assess_cost_advantages()
        regulatory_score = self.assess_regulatory_barriers()

        moat_score = brand_score + network_score + cost_score + regulatory_score

        # Assess other factors
        market_position = self.assess_market_position()
        business_model = self.assess_business_model()
        financial_chars = self.assess_financial_characteristics()

        # Calculate total score
        total_score = moat_score + market_position + business_model + financial_chars

        # Normalize to 0-100
        quality_score = min(total_score, 100.0)

        # Identify moat indicators
        moat_scores = {
            'brand': brand_score,
            'network': network_score,
            'cost': cost_score,
            'regulatory': regulatory_score
        }
        moat_indicators = self.identify_moat_indicators(moat_scores)

        # Determine competitive position
        if market_position >= 15:
            competitive_position = "Market Leader"
        elif market_position >= 10:
            competitive_position = "Strong Position"
        elif market_position >= 5:
            competitive_position = "Moderate Position"
        else:
            competitive_position = "Weak Position"

        return BusinessQuality(
            score=quality_score,
            moatIndicators=moat_indicators,
            competitivePosition=competitive_position
        )
