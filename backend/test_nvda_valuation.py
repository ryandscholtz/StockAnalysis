"""
Test script to verify NVIDIA valuation calculations
"""
import yfinance as yf
import sys
sys.path.insert(0, '.')

from app.data.data_fetcher import DataFetcher
from app.valuation.intrinsic_value import IntrinsicValueCalculator
from app.valuation.dcf_model import DCFModel
from app.valuation.earnings_power import EarningsPowerValue
from app.valuation.asset_based import AssetBasedValuation

async def test_nvda():
    print("=" * 60)
    print("NVIDIA (NVDA) Valuation Verification")
    print("=" * 60)
    
    # Fetch data
    print("\n1. Fetching company data...")
    data_fetcher = DataFetcher()
    company_data = await data_fetcher.fetch_company_data("NVDA")
    
    if not company_data:
        print("ERROR: Could not fetch company data")
        return
    
    print(f"   Current Price: ${company_data.current_price:.2f}")
    print(f"   Market Cap: ${company_data.market_cap:,.0f}" if company_data.market_cap else "   Market Cap: N/A")
    print(f"   Shares Outstanding: {company_data.shares_outstanding:,.0f}" if company_data.shares_outstanding else "   Shares Outstanding: N/A")
    print(f"   Currency: {company_data.currency}")
    
    # Check financial data
    print(f"\n2. Financial Data Availability:")
    print(f"   Income Statements: {len(company_data.income_statement)} periods")
    print(f"   Balance Sheets: {len(company_data.balance_sheet)} periods")
    print(f"   Cash Flow Statements: {len(company_data.cashflow)} periods")
    
    if company_data.income_statement:
        latest_date = sorted(company_data.income_statement.keys(), reverse=True)[0]
        latest_income = company_data.income_statement[latest_date]
        if isinstance(latest_income, dict):
            revenue = latest_income.get('Total Revenue') or latest_income.get('Revenue', 0)
            net_income = latest_income.get('Net Income') or latest_income.get('Net Income Common Stockholders', 0)
            print(f"   Latest Revenue ({latest_date}): ${revenue:,.0f}")
            print(f"   Latest Net Income ({latest_date}): ${net_income:,.0f}")
            if company_data.shares_outstanding:
                eps = net_income / company_data.shares_outstanding
                print(f"   EPS: ${eps:.2f}")
    
    if company_data.cashflow:
        latest_date = sorted(company_data.cashflow.keys(), reverse=True)[0]
        latest_cf = company_data.cashflow[latest_date]
        if isinstance(latest_cf, dict):
            ocf = latest_cf.get('Operating Cash Flow') or latest_cf.get('Total Cash From Operating Activities', 0)
            capex = abs(latest_cf.get('Capital Expenditures') or latest_cf.get('Capital Expenditure', 0))
            fcf = ocf - capex
            print(f"   Latest FCF ({latest_date}): ${fcf:,.0f}")
            if company_data.shares_outstanding:
                fcf_per_share = fcf / company_data.shares_outstanding
                print(f"   FCF per Share: ${fcf_per_share:.2f}")
    
    # Test DCF
    print(f"\n3. DCF Model Calculation:")
    dcf_model = DCFModel(company_data, risk_free_rate=0.04)
    dcf_result = dcf_model.calculate()
    print(f"   Fair Value per Share: ${dcf_result.fair_value_per_share:.2f}")
    print(f"   WACC: {dcf_result.wacc*100:.2f}%")
    print(f"   Enterprise Value: ${dcf_result.enterprise_value:,.0f}")
    print(f"   Equity Value: ${dcf_result.equity_value:,.0f}")
    
    # Test EPV
    print(f"\n4. Earnings Power Value Calculation:")
    epv_model = EarningsPowerValue(company_data, risk_free_rate=0.04)
    epv_result = epv_model.calculate(business_quality_score=75.0)  # High quality score
    print(f"   Fair Value per Share: ${epv_result.fair_value_per_share:.2f}")
    print(f"   Normalized Earnings: ${epv_result.normalized_earnings:,.0f}")
    print(f"   Capitalization Rate: {epv_result.capitalization_rate*100:.2f}%")
    
    # Test Asset-Based
    print(f"\n5. Asset-Based Valuation:")
    asset_model = AssetBasedValuation(company_data)
    asset_result = asset_model.calculate()
    print(f"   Fair Value per Share: ${asset_result.fair_value_per_share:.2f}")
    print(f"   Book Value per Share: ${asset_result.book_value_per_share:.2f}")
    print(f"   Method Used: {asset_result.method_used}")
    
    # Full calculation
    print(f"\n6. Full Intrinsic Value Calculation:")
    intrinsic_calc = IntrinsicValueCalculator(company_data, risk_free_rate=0.04)
    business_type = intrinsic_calc.determine_business_type()
    print(f"   Business Type: {business_type}")
    weights = intrinsic_calc.get_weights(business_type)
    print(f"   Weights - DCF: {weights[0]*100:.0f}%, EPV: {weights[1]*100:.0f}%, Asset: {weights[2]*100:.0f}%")
    
    valuation_result = intrinsic_calc.calculate(business_quality_score=75.0, financial_health_score=80.0)
    print(f"   Fair Value (Weighted): ${valuation_result.fair_value:.2f}")
    print(f"   DCF Component: ${valuation_result.breakdown.dcf:.2f}")
    print(f"   EPV Component: ${valuation_result.breakdown.earningsPower:.2f}")
    print(f"   Asset Component: ${valuation_result.breakdown.assetBased:.2f}")
    
    print(f"\n7. Comparison:")
    print(f"   Current Price: ${company_data.current_price:.2f}")
    print(f"   Calculated Fair Value: ${valuation_result.fair_value:.2f}")
    print(f"   Difference: {((company_data.current_price / valuation_result.fair_value - 1) * 100):.1f}%")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_nvda())

