"""
Analysis Weighting Configuration
Defines presets for different business types and allows manual customization
"""
from typing import Dict, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class BusinessType(str, Enum):
    """Business type categories"""
    HIGH_GROWTH = "high_growth"
    GROWTH = "growth"
    MATURE = "mature"
    CYCLICAL = "cyclical"
    ASSET_HEAVY = "asset_heavy"
    DISTRESSED = "distressed"
    BANK = "bank"
    REIT = "reit"
    INSURANCE = "insurance"
    UTILITY = "utility"
    TECHNOLOGY = "technology"
    HEALTHCARE = "healthcare"
    RETAIL = "retail"
    ENERGY = "energy"
    PROFESSIONAL_SERVICES = "professional_services"
    FRANCHISE = "franchise"
    ECOMMERCE = "ecommerce"
    SUBSCRIPTION = "subscription"
    MANUFACTURING = "manufacturing"
    DEFAULT = "default"


@dataclass
class AnalysisWeights:
    """Weights for valuation methods (must sum to 1.0)"""
    # Valuation weights - these determine how much each valuation method contributes to the final fair value
    dcf_weight: float = 0.40
    epv_weight: float = 0.40
    asset_weight: float = 0.20
    
    def validate(self) -> bool:
        """Validate that valuation weights sum to 1.0 (with tolerance)"""
        valuation_sum = self.dcf_weight + self.epv_weight + self.asset_weight
        tolerance = 0.01
        return abs(valuation_sum - 1.0) < tolerance
    
    def normalize(self):
        """Normalize valuation weights to sum to 1.0"""
        valuation_sum = self.dcf_weight + self.epv_weight + self.asset_weight
        if valuation_sum > 0:
            self.dcf_weight /= valuation_sum
            self.epv_weight /= valuation_sum
            self.asset_weight /= valuation_sum
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'AnalysisWeights':
        """Create from dictionary"""
        return cls(**data)


class AnalysisWeightPresets:
    """Preset weight configurations for different business types"""
    
    @staticmethod
    def get_preset(business_type: BusinessType) -> AnalysisWeights:
        """Get preset weights for a business type"""
        presets = {
            # High Growth (Technology startups, biotech, high-growth SaaS)
            # Guide: Technology/SaaS (Pre-Profit): Revenue Multiple 50-60%, DCF 40-50% for profitable
            BusinessType.HIGH_GROWTH: AnalysisWeights(
                dcf_weight=0.55,  # DCF with terminal value for high growth
                epv_weight=0.25,  # Lower weight due to earnings volatility
                asset_weight=0.20  # Assets less relevant for tech
            ),
            # Growth (Established growth companies, 10-20% revenue growth)
            # Guide: Technology/SaaS (Profitable): DCF 40-50%, Revenue Multiples 35-45%
            BusinessType.GROWTH: AnalysisWeights(
                dcf_weight=0.50,  # DCF primary for growth
                epv_weight=0.30,  # Earnings becoming more stable
                asset_weight=0.20
            ),
            # Mature (Stable, established companies, blue-chip stocks)
            # Guide: Mature Public Companies: DCF 45-55%, Trading Comparables 30-40%
            BusinessType.MATURE: AnalysisWeights(
                dcf_weight=0.50,  # DCF primary for mature companies
                epv_weight=0.35,  # EPV important for stable earnings
                asset_weight=0.15  # Lower asset weight for mature public companies
            ),
            # Cyclical (Industrial, manufacturing, materials, energy)
            # Guide: Manufacturing/Industrial: Adjusted NAV 40-50%, EBITDA 30-40%, DCF 15-25%
            BusinessType.CYCLICAL: AnalysisWeights(
                dcf_weight=0.25,  # Lower DCF due to volatility
                epv_weight=0.50,  # EPV higher - normalized earnings more reliable
                asset_weight=0.25  # Assets important for cyclical
            ),
            # Asset Heavy (Real estate, utilities, infrastructure, capital-intensive)
            # Guide: Manufacturing/Industrial: Adjusted NAV 40-50%, Asset-Heavy: NAV 50-60% for REITs
            BusinessType.ASSET_HEAVY: AnalysisWeights(
                dcf_weight=0.20,  # Lower DCF weight
                epv_weight=0.25,  # Moderate EPV
                asset_weight=0.55  # Asset-based primary (50-60% per guide)
            ),
            # Distressed (Companies in financial difficulty, turnaround situations)
            # Guide: Distressed/Turnaround: Liquidation Value 50-70%
            BusinessType.DISTRESSED: AnalysisWeights(
                dcf_weight=0.10,  # Future cash flows uncertain
                epv_weight=0.10,  # Earnings power questionable
                asset_weight=0.80  # Liquidation value primary (50-70% per guide, using 80% for extreme distress)
            ),
            # Bank (Banks, financial services, credit institutions)
            # Guide: Financial Institutions (Banks): Dividend Discount 40-50%, P/B 30-40%, Adjusted Book 15-25%
            # Using EPV as proxy for earnings-based methods, Asset for book value
            BusinessType.BANK: AnalysisWeights(
                dcf_weight=0.25,  # Lower DCF weight
                epv_weight=0.50,  # Earnings power key (proxy for DDM/P/B)
                asset_weight=0.25  # Book value important (Adjusted Book 15-25%)
            ),
            # REIT (Real Estate Investment Trusts)
            # Guide: Real Estate Holdings/REITs: NAV 50-60%, Dividend Discount 25-35%
            BusinessType.REIT: AnalysisWeights(
                dcf_weight=0.30,  # DCF for cash flows (proxy for DDM)
                epv_weight=0.20,  # Lower EPV weight
                asset_weight=0.50  # NAV primary (50-60% per guide)
            ),
            # Insurance (Insurance companies, reinsurance)
            # Guide: Insurance: Embedded Value 45-55%, P/B 25-35%, DDM 15-20%
            BusinessType.INSURANCE: AnalysisWeights(
                dcf_weight=0.20,  # Lower DCF (proxy for DDM 15-20%)
                epv_weight=0.50,  # Embedded value/Earnings primary (45-55%)
                asset_weight=0.30  # Book value important (P/B 25-35%)
            ),
            # Utility (Electric, water, gas utilities)
            # Guide: Mature Public Companies apply, but utilities are asset-heavy and stable
            BusinessType.UTILITY: AnalysisWeights(
                dcf_weight=0.45,  # DCF important for stable cash flows
                epv_weight=0.35,  # EPV for stable earnings
                asset_weight=0.20  # Assets important but not primary
            ),
            # Technology (Software, internet, semiconductor, tech companies)
            # Guide: Technology/SaaS (Profitable): DCF 40-50%, Revenue Multiples 35-45%
            BusinessType.TECHNOLOGY: AnalysisWeights(
                dcf_weight=0.50,  # DCF with terminal value (40-50%)
                epv_weight=0.35,  # EPV for earnings (proxy for revenue multiples)
                asset_weight=0.15  # Assets typically irrelevant
            ),
            # Healthcare (Pharmaceuticals, biotech, medical devices, healthcare services)
            # Guide: Similar to Technology but with more asset consideration for pharma
            BusinessType.HEALTHCARE: AnalysisWeights(
                dcf_weight=0.50,  # DCF primary
                epv_weight=0.35,  # EPV important
                asset_weight=0.15  # Some assets (IP, R&D) but less tangible
            ),
            # Retail (Retail stores, consumer goods, e-commerce)
            # Guide: Retail Businesses: EBITDA 35-45%, Adjusted NAV 30-40%, Revenue 15-25%
            BusinessType.RETAIL: AnalysisWeights(
                dcf_weight=0.35,  # DCF moderate (EBITDA proxy)
                epv_weight=0.40,  # EPV important (EBITDA 35-45%)
                asset_weight=0.25  # Assets important (NAV 30-40%)
            ),
            # Energy (Oil & gas, mining, energy exploration)
            # Guide: Energy is cyclical and asset-heavy
            BusinessType.ENERGY: AnalysisWeights(
                dcf_weight=0.25,  # Lower DCF due to volatility
                epv_weight=0.40,  # EPV for normalized earnings
                asset_weight=0.35  # Assets very important (reserves, equipment)
            ),
            # Professional Services (Consulting, legal, accounting)
            # Guide: Professional Services: Capitalized Excess Earnings 45-55%, Revenue/Earnings 30-40%
            BusinessType.PROFESSIONAL_SERVICES: AnalysisWeights(
                dcf_weight=0.40,  # DCF for cash flows
                epv_weight=0.50,  # EPV primary (Excess Earnings 45-55%)
                asset_weight=0.10  # Very low asset base
            ),
            # Franchise (Franchise businesses)
            # Guide: Franchise: EBITDA 40-50%, Royalty Stream 30-40%, Asset 15-25%
            BusinessType.FRANCHISE: AnalysisWeights(
                dcf_weight=0.35,  # DCF for cash flows
                epv_weight=0.50,  # EPV primary (EBITDA/Royalty 40-50%)
                asset_weight=0.15  # Lower asset weight
            ),
            # E-commerce (E-commerce businesses)
            # Guide: E-commerce: SDE Multiple 45-55%, DCF 25-35%, Asset 15-20%
            BusinessType.ECOMMERCE: AnalysisWeights(
                dcf_weight=0.30,  # DCF moderate (25-35%)
                epv_weight=0.55,  # EPV primary (SDE Multiple 45-55%)
                asset_weight=0.15  # Lower asset weight (15-20%)
            ),
            # Subscription (Subscription/recurring revenue models)
            # Guide: Subscription: CLV 40-50%, ARR/MRR Multiples 35-45%, DCF 15-20%
            BusinessType.SUBSCRIPTION: AnalysisWeights(
                dcf_weight=0.20,  # Lower DCF (15-20%)
                epv_weight=0.70,  # EPV primary (CLV/ARR multiples 40-50% + 35-45%)
                asset_weight=0.10  # Very low asset weight
            ),
            # Manufacturing (Manufacturing/Industrial - separate from cyclical for clarity)
            # Guide: Manufacturing/Industrial: Adjusted NAV 40-50%, EBITDA 30-40%, DCF 15-25%
            BusinessType.MANUFACTURING: AnalysisWeights(
                dcf_weight=0.20,  # Lower DCF (15-25%)
                epv_weight=0.35,  # EPV moderate (EBITDA 30-40%)
                asset_weight=0.45  # Assets primary (Adjusted NAV 40-50%)
            ),
            # Default (General purpose, unknown business types, balanced approach)
            # Guide: Mature Public Companies: DCF 45-55%, balanced approach
            BusinessType.DEFAULT: AnalysisWeights(
                dcf_weight=0.50,  # DCF primary
                epv_weight=0.35,  # EPV important
                asset_weight=0.15  # Lower asset weight
            )
        }
        
        return presets.get(business_type, presets[BusinessType.DEFAULT])
    
    @staticmethod
    def detect_business_type(sector: Optional[str], industry: Optional[str], 
                            revenue_growth: float = 0.0, 
                            asset_intensity: float = 0.0) -> BusinessType:
        """Detect business type from company characteristics"""
        sector_lower = (sector or '').lower()
        industry_lower = (industry or '').lower()
        
        # Banks
        if any(kw in sector_lower or kw in industry_lower 
               for kw in ['bank', 'banking', 'financial services', 'credit']):
            return BusinessType.BANK
        
        # REITs
        if any(kw in sector_lower or kw in industry_lower 
               for kw in ['reit', 'real estate investment trust', 'real estate']):
            return BusinessType.REIT
        
        # Insurance
        if any(kw in sector_lower or kw in industry_lower 
               for kw in ['insurance', 'reinsurance']):
            return BusinessType.INSURANCE
        
        # Utilities
        if any(kw in sector_lower or kw in industry_lower 
               for kw in ['utility', 'utilities', 'electric', 'water', 'gas']):
            return BusinessType.UTILITY
        
        # Technology
        if any(kw in sector_lower or kw in industry_lower 
               for kw in ['technology', 'software', 'internet', 'semiconductor', 
                         'tech', 'saas', 'cloud']):
            return BusinessType.TECHNOLOGY
        
        # Healthcare
        if any(kw in sector_lower or kw in industry_lower 
               for kw in ['healthcare', 'pharmaceutical', 'biotech', 'medical', 
                         'health']):
            return BusinessType.HEALTHCARE
        
        # Retail
        if any(kw in sector_lower or kw in industry_lower 
               for kw in ['retail', 'consumer', 'stores']):
            return BusinessType.RETAIL
        
        # Energy
        if any(kw in sector_lower or kw in industry_lower 
               for kw in ['energy', 'oil', 'gas', 'petroleum', 'mining']):
            return BusinessType.ENERGY
        
        # Manufacturing/Industrial
        if any(kw in sector_lower or kw in industry_lower 
               for kw in ['manufacturing', 'industrial', 'machinery', 'equipment', 'automotive']):
            return BusinessType.MANUFACTURING
        
        # Professional Services
        if any(kw in sector_lower or kw in industry_lower 
               for kw in ['consulting', 'professional services', 'legal', 'accounting', 'advisory']):
            return BusinessType.PROFESSIONAL_SERVICES
        
        # Franchise
        if any(kw in sector_lower or kw in industry_lower 
               for kw in ['franchise', 'franchising']):
            return BusinessType.FRANCHISE
        
        # E-commerce
        if any(kw in sector_lower or kw in industry_lower 
               for kw in ['e-commerce', 'ecommerce', 'online retail', 'internet retail']):
            return BusinessType.ECOMMERCE
        
        # Subscription/Recurring Revenue (check before technology to prioritize)
        if any(kw in sector_lower or kw in industry_lower 
               for kw in ['subscription', 'saas', 'software as a service', 'recurring revenue']):
            return BusinessType.SUBSCRIPTION
        
        # Growth-based classification
        if revenue_growth > 0.20:
            return BusinessType.HIGH_GROWTH
        elif revenue_growth > 0.10:
            return BusinessType.GROWTH
        elif revenue_growth < -0.10:
            return BusinessType.DISTRESSED
        elif asset_intensity > 2.0:
            return BusinessType.ASSET_HEAVY
        else:
            return BusinessType.MATURE

