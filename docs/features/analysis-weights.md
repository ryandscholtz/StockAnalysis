# Analysis Weights Configuration Guide

## Overview

The Stock Analysis Tool uses configurable weights to customize how different valuation methods contribute to the final fair value calculation. This allows you to tailor the valuation to different business types and investment strategies.

**The weightings in this system are based on industry-standard valuation practices for different business types**, as outlined in professional valuation guidelines. Each preset is calibrated to match how professional valuers typically weight different methods for specific industries and business models.

## Understanding Valuation Weights

### Valuation Method Weights

These weights determine how much each valuation method contributes to the final fair value:

- **DCF (Discounted Cash Flow) Weight**: Projects future free cash flows discounted to present value using WACC. Best for companies with predictable cash flows and growth potential. 
  - *Industry standard*: 40-55% for mature public companies, 40-50% for profitable tech companies, 15-25% for cyclical/manufacturing.

- **EPV (Earnings Power Value) Weight**: Normalizes single-period earnings and capitalizes them (similar to Capitalization of Earnings method). Best for stable, mature businesses with consistent earnings.
  - *Industry standard*: 30-40% for mature companies, 40-50% for banks (as proxy for Dividend Discount Model), 35-45% for EBITDA multiples.

- **Asset-Based Weight**: Calculates fair market value of all assets minus liabilities (Adjusted Net Asset Value). Best for asset-heavy businesses or liquidation scenarios.
  - *Industry standard*: 40-50% for manufacturing/industrial, 50-60% for REITs, 50-70% for distressed companies.

**Note**: These three weights must sum to 100% (1.0). The final fair value is calculated as a weighted average of these three valuation methods.

**Note on Method Mapping**: While comprehensive valuation guides include many methods (DDM, Comparable Company Analysis, Precedent Transactions, etc.), this system uses DCF, EPV, and Asset-Based as the core methods. EPV serves as a proxy for earnings-based methods (Capitalization of Earnings, EBITDA multiples, SDE multiples), and the weightings are calibrated to match industry standards for each business type.

## Business Type Presets

The system includes 20 pre-configured business type presets, each optimized for specific industries and business models based on industry-standard valuation practices:

### 1. High Growth
**Best for**: Technology startups, biotech, high-growth SaaS companies

**Valuation Weights (aligned with industry standards):**
- DCF: 55% (DCF with terminal value for high growth - industry standard 40-50% for profitable tech)
- EPV: 25% (lower weight due to earnings volatility)
- Asset-Based: 20% (assets less relevant for tech)

**Use when**: Company has >20% revenue growth, high growth potential, early-stage or scaling business.

**Industry Standard**: Technology/SaaS (Profitable): DCF 40-50%, Revenue Multiples 35-45%

---

### 2. Growth
**Best for**: Established growth companies, expanding businesses

**Valuation Weights (aligned with industry standards):**
- DCF: 50% (DCF primary for growth - industry standard 40-50%)
- EPV: 30% (earnings becoming more stable)
- Asset-Based: 20%

**Use when**: Company has 10-20% revenue growth, established but still expanding.

**Industry Standard**: Technology/SaaS (Profitable): DCF 40-50%, Revenue Multiples 35-45%

---

### 3. Mature
**Best for**: Stable, established companies, blue-chip stocks

**Valuation Weights (aligned with industry standards):**
- DCF: 50% (DCF primary - industry standard 45-55% for mature public companies)
- EPV: 35% (EPV important for stable earnings)
- Asset-Based: 15% (lower asset weight for mature public companies)

**Use when**: Company has stable, moderate growth (0-10%), established market position.

**Industry Standard**: Mature Public Companies: DCF 45-55%, Trading Comparables 30-40%

---

### 4. Cyclical
**Best for**: Industrial, manufacturing, materials, energy companies

**Valuation Weights (aligned with industry standards):**
- DCF: 25% (lower DCF due to volatility - industry standard 15-25%)
- EPV: 50% (EPV higher - normalized earnings more reliable - industry standard 30-40% EBITDA)
- Asset-Based: 25% (assets important for cyclical)

**Use when**: Company operates in cyclical industries, earnings vary with economic cycles.

**Industry Standard**: Manufacturing/Industrial: Adjusted NAV 40-50%, EBITDA 30-40%, DCF 15-25%

---

### 5. Asset Heavy
**Best for**: Real estate, utilities, infrastructure, capital-intensive businesses

**Valuation Weights (aligned with industry standards):**
- DCF: 20% (lower DCF weight)
- EPV: 25% (moderate EPV)
- Asset-Based: 55% (asset-based primary - industry standard 40-50% for manufacturing, 50-60% for REITs)

**Use when**: Company has high asset-to-revenue ratio (>2.0), asset value is primary consideration.

**Industry Standard**: Manufacturing/Industrial: Adjusted NAV 40-50%, Real Estate/REITs: NAV 50-60%

---

### 6. Distressed
**Best for**: Companies in financial difficulty, turnaround situations

**Valuation Weights (aligned with industry standards):**
- DCF: 10% (future cash flows uncertain)
- EPV: 10% (earnings power questionable)
- Asset-Based: 80% (liquidation value primary - industry standard 50-70%)

**Use when**: Company has declining revenue (>10%), financial distress, potential bankruptcy.

**Industry Standard**: Distressed/Turnaround: Liquidation Value 50-70%

---

### 7. Bank
**Best for**: Banks, financial services, credit institutions

**Valuation Weights (aligned with industry standards):**
- DCF: 25% (lower DCF weight)
- EPV: 50% (earnings power key - proxy for Dividend Discount Model 40-50% and P/B 30-40%)
- Asset-Based: 25% (book value important - Adjusted Book 15-25%)

**Special Metrics**: Includes bank-specific analysis:
- Net Interest Margin (NIM)
- Efficiency Ratio
- Loan-to-Deposit Ratio
- Tier 1 Capital Ratio (if available)

**Use when**: Company is a bank or financial services institution.

**Industry Standard**: Financial Institutions (Banks): Dividend Discount 40-50%, P/B 30-40%, Adjusted Book 15-25%

---

### 8. REIT
**Best for**: Real Estate Investment Trusts

**Valuation Weights (aligned with industry standards):**
- DCF: 30% (DCF for cash flows - proxy for Dividend Discount 25-35%)
- EPV: 20% (lower EPV weight)
- Asset-Based: 50% (NAV primary - industry standard 50-60%)

**Special Metrics**: Includes REIT-specific analysis:
- Funds From Operations (FFO)
- Adjusted Funds From Operations (AFFO)
- Net Asset Value (NAV)
- Dividend Yield
- Payout Ratio

**Use when**: Company is a REIT or real estate investment trust.

**Industry Standard**: Real Estate Holdings/REITs: NAV 50-60%, Dividend Discount 25-35%

---

### 9. Insurance
**Best for**: Insurance companies, reinsurance

**Valuation Weights (aligned with industry standards):**
- DCF: 20% (lower DCF - proxy for DDM 15-20%)
- EPV: 50% (embedded value/earnings primary - industry standard 45-55%)
- Asset-Based: 30% (book value important - P/B 25-35%)

**Special Metrics**: Includes insurance-specific analysis:
- Combined Ratio (Loss Ratio + Expense Ratio)
- Loss Ratio
- Expense Ratio
- Reserve Adequacy
- Investment Yield

**Use when**: Company is an insurance or reinsurance company.

---

### 10. Utility
**Best for**: Electric, water, gas utilities

**Valuation Weights:**
- DCF: 45% (regulated returns)
- EPV: 35%
- Asset-Based: 20%

**Use when**: Company is a regulated utility, stable cash flows, dividend-focused.

---

### 11. Technology
**Best for**: Software, internet, semiconductor, tech companies

**Valuation Weights:**
- DCF: 55% (cash flow growth is primary)
- EPV: 30%
- Asset-Based: 15%

**Use when**: Company is in technology sector, software, internet, or tech services.

---

### 12. Healthcare
**Best for**: Pharmaceuticals, biotech, medical devices, healthcare services

**Valuation Weights (aligned with industry standards):**
- DCF: 50% (DCF primary - similar to technology)
- EPV: 35% (EPV important)
- Asset-Based: 15% (some assets like IP/R&D but less tangible)

**Use when**: Company is in healthcare, pharmaceutical, or biotech sector.

**Industry Standard**: Similar to Technology: DCF 40-50%, Revenue/Earnings Multiples 35-45%

---

### 13. Retail
**Best for**: Retail stores, consumer goods, e-commerce

**Valuation Weights (aligned with industry standards):**
- DCF: 35% (DCF moderate - proxy for EBITDA 35-45%)
- EPV: 40% (EPV important - EBITDA 35-45%)
- Asset-Based: 25% (assets important - Adjusted NAV 30-40%)

**Use when**: Company is in retail, consumer goods, or e-commerce sector.

**Industry Standard**: Retail Businesses: EBITDA 35-45%, Adjusted NAV 30-40%, Revenue 15-25%

---

### 14. Energy
**Best for**: Oil & gas, mining, energy exploration

**Valuation Weights:**
- DCF: 35%
- EPV: 40% (normalized earnings important)
- Asset-Based: 25% (reserves, assets matter)

**Use when**: Company is in energy, oil & gas, or mining sector.

**Industry Standard**: Energy is cyclical and asset-heavy - similar to Manufacturing/Industrial

---

### 15. Professional Services
**Best for**: Consulting, legal, accounting, advisory firms

**Valuation Weights (aligned with industry standards):**
- DCF: 40% (DCF for cash flows)
- EPV: 50% (EPV primary - Capitalized Excess Earnings 45-55%)
- Asset-Based: 10% (very low asset base)

**Use when**: Company is in professional services with low tangible assets, depends on client relationships.

**Industry Standard**: Professional Services: Capitalized Excess Earnings 45-55%, Revenue/Earnings Multiples 30-40%

---

### 16. Franchise
**Best for**: Franchise businesses

**Valuation Weights (aligned with industry standards):**
- DCF: 35% (DCF for cash flows)
- EPV: 50% (EPV primary - EBITDA/Royalty Stream 40-50%)
- Asset-Based: 15% (lower asset weight)

**Use when**: Company operates a franchise business model.

**Industry Standard**: Franchise: EBITDA 40-50%, Royalty Stream 30-40%, Asset 15-25%

---

### 17. E-commerce
**Best for**: E-commerce businesses

**Valuation Weights (aligned with industry standards):**
- DCF: 30% (DCF moderate - industry standard 25-35%)
- EPV: 55% (EPV primary - SDE Multiple 45-55%)
- Asset-Based: 15% (lower asset weight - industry standard 15-20%)

**Use when**: Company operates primarily through e-commerce channels.

**Industry Standard**: E-commerce: SDE Multiple 45-55%, DCF 25-35%, Asset 15-20%

---

### 18. Subscription
**Best for**: Subscription/recurring revenue models (SaaS, subscription services)

**Valuation Weights (aligned with industry standards):**
- DCF: 20% (lower DCF - industry standard 15-20%)
- EPV: 70% (EPV primary - CLV 40-50% + ARR/MRR Multiples 35-45%)
- Asset-Based: 10% (very low asset weight)

**Use when**: Company has subscription-based or recurring revenue model.

**Industry Standard**: Subscription/Recurring Revenue: CLV 40-50%, ARR/MRR Multiples 35-45%, DCF 15-20%

---

### 19. Manufacturing
**Best for**: Manufacturing, industrial companies

**Valuation Weights (aligned with industry standards):**
- DCF: 20% (lower DCF - industry standard 15-25%)
- EPV: 35% (EPV moderate - EBITDA 30-40%)
- Asset-Based: 45% (assets primary - Adjusted NAV 40-50%)

**Use when**: Company is in manufacturing or industrial sector with significant tangible assets.

**Industry Standard**: Manufacturing/Industrial: Adjusted NAV 40-50%, EBITDA 30-40%, DCF 15-25%

---

### 20. Default
**Best for**: General purpose, unknown business types, balanced approach

**Valuation Weights (aligned with industry standards):**
- DCF: 50% (DCF primary - industry standard 45-55% for mature public companies)
- EPV: 35% (EPV important)
- Asset-Based: 15% (lower asset weight)

**Use when**: Business type is unknown or you want a balanced, general-purpose analysis.

**Industry Standard**: Mature Public Companies: DCF 45-55%, Trading Comparables 30-40%

---

## Automatic Business Type Detection

The system uses **AI-powered detection** (AWS Bedrock or OpenAI) combined with rule-based fallback to automatically determine the most appropriate business type for valuation.

### AI-Powered Detection

**🤖 Auto-Assign Feature**: The system can use AI (AWS Bedrock or OpenAI) to research the company and automatically assign the best valuation model. This happens:

1. **When adding to watchlist**: Business type is automatically detected using AI (if enabled)
2. **During first analysis**: If no business type is specified, AI detection is attempted first
3. **Manual trigger**: Click the "🤖 Auto-Assign" button in the Analysis Configuration panel

**AI Detection Process**:
- Analyzes company name, sector, industry, and business description
- Considers business model characteristics (e.g., subscription, e-commerce, franchise)
- Evaluates growth stage and asset intensity
- Returns the most appropriate business type from the 20 available presets

**Fallback**: If AI detection is unavailable or fails, the system falls back to rule-based detection.

### Rule-Based Detection (Fallback)

The system automatically detects business type based on:

1. **Sector/Industry**: Checks company sector and industry classification
2. **Revenue Growth**: Analyzes revenue growth trends
3. **Asset Intensity**: Calculates asset-to-revenue ratio

### Detection Priority

1. **Sector-based detection** (highest priority):
   - Banks → Bank preset
   - REITs → REIT preset
   - Insurance → Insurance preset
   - Utilities → Utility preset
   - Technology → Technology preset
   - Healthcare → Healthcare preset
   - Retail → Retail preset
   - Energy → Energy preset
   - Manufacturing/Industrial → Manufacturing preset
   - Professional Services (consulting, legal, accounting) → Professional Services preset
   - Franchise → Franchise preset
   - E-commerce → E-commerce preset
   - Subscription/SaaS → Subscription preset

2. **Growth-based detection** (if sector doesn't match):
   - Revenue growth >20% → High Growth
   - Revenue growth 10-20% → Growth
   - Revenue growth < -10% → Distressed
   - Asset intensity >2.0 → Asset Heavy
   - Otherwise → Mature

### Configuring AI Services

To enable AI-powered detection, you can use either AWS Bedrock or OpenAI.

#### Option 1: AWS Bedrock (Recommended for Production)

**Quick Setup via CLI:**

1. **Configure AWS credentials** (if not already done):
   ```bash
   aws configure
   ```
   You'll need:
   - AWS Access Key ID
   - AWS Secret Access Key
   - Default region (recommended: `us-east-1`)
   - Default output format (`json`)

2. **Run the setup script**:
   ```powershell
   cd backend
   .\setup_bedrock.ps1
   ```
   This script will:
   - Verify AWS CLI and credentials
   - Check Bedrock model availability
   - Create/update `.env` file with Bedrock configuration

3. **Enable Bedrock model access** (one-time setup):
   - Go to [AWS Bedrock Console](https://console.aws.amazon.com/bedrock/)
   - Click "Model access" in the left menu
   - Request access to "Claude 3 Sonnet" (approval is usually instant)
   - Wait for approval (usually instant for Claude models)

4. **Manual configuration** (if you prefer):
   Add to `backend/.env`:
   ```bash
   USE_AWS_BEDROCK=true
   AWS_REGION=us-east-1
   BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
   ```

#### Option 2: OpenAI (Simpler Alternative)

Just add to `backend/.env`:
```bash
OPENAI_API_KEY=your-openai-api-key-here
```

**Note**: If neither AWS Bedrock nor OpenAI is configured, the system will automatically use rule-based detection as a fallback.

## Manual Configuration

You can override the automatic detection and manually configure weights:

### Using Presets

1. Click "⚙️ [Business Type] (Weighting)" button on the stock analysis page
2. Select a business type from the dropdown
3. Click "Re-analyze with New Weights"

### Custom Weights

1. Click "⚙️ [Business Type] Model" button
2. Select "Manual Configuration"
3. Adjust valuation weights using the input fields:
   - **DCF Weight**: For companies with predictable, growing cash flows
   - **EPV Weight**: For companies with stable, consistent earnings
   - **Asset-Based Weight**: For asset-heavy companies or distressed situations
   - **Note**: All three weights must sum to 100%
4. Use "Normalize Valuation Weights" button to auto-adjust weights to sum to 100%
5. Click "Re-analyze with New Weights"

## Best Practices

### When to Use Presets

- **Use presets** when you know the business type and want industry-optimized analysis
- **Use presets** for consistency across similar companies
- **Use presets** when you trust the automatic detection

### When to Use Custom Weights

- **Use custom weights** when you have specific investment criteria
- **Use custom weights** for unique business models not covered by presets
- **Use custom weights** to test different valuation approaches
- **Use custom weights** when you want to emphasize certain valuation methods

### Weight Adjustment Guidelines

**Valuation Weights:**
- **Increase DCF weight** if company has predictable, growing cash flows (e.g., high-growth tech companies)
- **Increase EPV weight** if company has stable, consistent earnings (e.g., mature utilities, banks)
- **Increase Asset-Based weight** if company is asset-heavy or distressed (e.g., real estate, distressed companies)

## Specialized Metrics

Some business types include specialized metrics:

### Banks
- Net Interest Margin (NIM)
- Efficiency Ratio
- Loan-to-Deposit Ratio
- Tier 1 Capital Ratio

### REITs
- Funds From Operations (FFO)
- Adjusted Funds From Operations (AFFO)
- Net Asset Value (NAV)
- Dividend Yield
- Payout Ratio

### Insurance
- Combined Ratio
- Loss Ratio
- Expense Ratio
- Reserve Adequacy
- Investment Yield

## Examples

### Example 1: Analyzing a Tech Startup
1. Select "High Growth" preset
2. System emphasizes DCF (55%) - DCF with terminal value for high growth (industry standard 40-50%)
3. EPV gets lower weight (25%) - earnings less predictable for startups
4. Asset-Based gets lower weight (20%) - assets less relevant for tech companies

### Example 2: Analyzing a Bank
1. System auto-detects "Bank" preset
2. EPV gets higher weight (50%) - earnings power key (proxy for DDM 40-50% and P/B 30-40%)
3. DCF gets lower weight (25%) - cash flows less reliable than earnings for banks
4. Asset-Based gets moderate weight (25%) - book value important (Adjusted Book 15-25%)
5. Bank-specific metrics (NIM, efficiency ratio) are calculated

### Example 3: Analyzing a Distressed Company
1. Select "Distressed" preset
2. Asset-Based gets highest weight (80%) - liquidation value primary (industry standard 50-70%)
3. DCF gets lowest weight (10%) - future cash flows uncertain
4. EPV gets lowest weight (10%) - earnings power questionable

### Example 4: Analyzing a Professional Services Firm
1. Select "Professional Services" preset
2. EPV gets highest weight (50%) - Capitalized Excess Earnings primary (industry standard 45-55%)
3. DCF gets moderate weight (40%) - cash flows important
4. Asset-Based gets lowest weight (10%) - very low asset base, depends on client relationships

## Technical Details

### Weight Normalization

If weights don't sum to exactly 100%, the system automatically normalizes them:
- All weights are proportionally adjusted to sum to 100%
- Relative relationships between weights are preserved

### Weight Validation

The system validates that:
- Valuation weights (DCF + EPV + Asset) = 100%

### Storage

- Weights are stored with each analysis in the database
- Business type is stored for reference
- You can see what weights were used for any historical analysis

## API Usage

### Get Available Presets

```bash
GET /api/analysis-presets
```

Returns all available business type presets and their default weights.

### Analyze with Custom Weights

```bash
GET /api/analyze/{ticker}?business_type=bank
GET /api/analyze/{ticker}?weights={"dcf_weight":0.5,"epv_weight":0.3,"asset_weight":0.2}
```

### Auto-Assign Business Type

```bash
POST /api/auto-assign-business-type/{ticker}
```

Uses AI to automatically detect and assign the best business type for a company. Returns the detected business type and corresponding weights.

**Response**:
```json
{
  "success": true,
  "ticker": "AAPL",
  "detected_business_type": "technology",
  "business_type_display": "Technology",
  "weights": {
    "dcf_weight": 0.50,
    "epv_weight": 0.35,
    "asset_weight": 0.15
  },
  "message": "Auto-detected business type: Technology"
}
```

## Troubleshooting

### Weights Don't Sum to 100%

- Use the "Normalize" buttons in the UI
- The system will automatically adjust weights proportionally

### Analysis Results Seem Wrong

- Check if the correct business type preset is selected
- Verify the company's sector/industry matches the preset
- Try a different preset or custom weights

### Specialized Metrics Not Showing

- Ensure the correct business type preset is selected (Bank, REIT, or Insurance)
- Some metrics require specific financial data that may not be available
- Check data quality warnings for missing information

## Valuation Methods Mapping

This system uses three core valuation methods (DCF, EPV, Asset-Based) that map to the comprehensive range of valuation methods used in professional practice:

### Income Approach Methods
- **DCF (Discounted Cash Flow)**: Directly implemented - projects future free cash flows discounted to present value
- **EPV (Earnings Power Value)**: Maps to Capitalization of Earnings, EBITDA multiples, SDE multiples, and other earnings-based methods
- **Dividend Discount Model (DDM)**: EPV serves as proxy for DDM in dividend-paying companies (banks, REITs, utilities)

### Market Approach Methods
- **Comparable Company Analysis**: Not directly implemented (requires peer company data), but EPV weightings reflect market multiple approaches
- **Precedent Transaction Analysis**: Not directly implemented (requires transaction data), but considered in weightings

### Asset Approach Methods
- **Adjusted Net Asset Value (NAV)**: Directly implemented as Asset-Based valuation
- **Liquidation Value**: Asset-Based method handles distressed scenarios
- **Book Value**: Asset-Based method includes book value calculations

### Method Selection Rationale

The three-method approach (DCF, EPV, Asset-Based) provides:
- **Comprehensive coverage**: Covers all three primary valuation approaches (Income, Market, Asset)
- **Data availability**: Uses data readily available from public financial statements
- **Industry alignment**: Weightings calibrated to match how professionals combine multiple methods
- **Practical implementation**: Avoids need for peer company or transaction databases

The weightings for each business type are calibrated based on industry standards that typically combine multiple methods, ensuring the final valuation reflects professional valuation practices.

## Related Documentation

- [Database Migration Guide](./DATABASE_MIGRATION_ANALYSIS_WEIGHTS.md)
- [Database Guide](./backend/DATABASE_GUIDE.md)
- [Batch Analysis Guide](./backend/BATCH_ANALYSIS_GUIDE.md)

