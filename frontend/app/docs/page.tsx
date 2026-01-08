'use client'

export default function DocsPage() {
  return (
    <div className="container" style={{ maxWidth: '900px', margin: '0 auto', padding: '40px 20px' }}>
      <h1 style={{ fontSize: '36px', fontWeight: '700', marginBottom: '8px', color: '#111827' }}>
        Documentation
      </h1>
      <p style={{ fontSize: '18px', color: '#6b7280', marginBottom: '40px' }}>
        Learn how the Stock Analysis Tool works and understand each analysis model
      </p>

      {/* Overview Section */}
      <section style={{ marginBottom: '60px' }}>
        <h2 style={{ fontSize: '28px', fontWeight: '600', marginBottom: '16px', color: '#111827', borderBottom: '2px solid #e5e7eb', paddingBottom: '8px' }}>
          Overview
        </h2>
        <p style={{ fontSize: '16px', lineHeight: '1.7', color: '#374151', marginBottom: '16px' }}>
          This tool uses value investing principles to analyze stocks. The analysis focuses on calculating 
          <strong> intrinsic value</strong> (the true worth of a business) and comparing it to the current market price 
          to determine the <strong>margin of safety</strong>.
        </p>
        <p style={{ fontSize: '16px', lineHeight: '1.7', color: '#374151' }}>
          The goal is to find stocks trading at a significant discount to their intrinsic value (ideally 30-50% discount), 
          which provides a safety buffer against estimation errors and market volatility.
        </p>
      </section>

      {/* Valuation Models Section */}
      <section style={{ marginBottom: '60px' }}>
        <h2 style={{ fontSize: '28px', fontWeight: '600', marginBottom: '24px', color: '#111827', borderBottom: '2px solid #e5e7eb', paddingBottom: '8px' }}>
          Valuation Models
        </h2>
        <p style={{ fontSize: '16px', lineHeight: '1.7', color: '#374151', marginBottom: '24px' }}>
          The tool uses three primary valuation methods, then calculates a weighted average based on the business type:
        </p>

        <div style={{ marginBottom: '32px' }}>
          <h3 style={{ fontSize: '22px', fontWeight: '600', marginBottom: '12px', color: '#111827' }}>
            1. Discounted Cash Flow (DCF) Model
          </h3>
          <p style={{ fontSize: '16px', lineHeight: '1.7', color: '#374151', marginBottom: '12px' }}>
            <strong>Best for:</strong> Companies with predictable cash flows and growth patterns
          </p>
          <p style={{ fontSize: '16px', lineHeight: '1.7', color: '#374151', marginBottom: '12px' }}>
            The DCF model estimates the present value of a company's future free cash flows. It projects cash flows 
            into the future and discounts them back to today's value using a discount rate (typically the weighted 
            average cost of capital or risk-free rate plus a risk premium).
          </p>
          <div style={{ backgroundColor: '#f9fafb', padding: '16px', borderRadius: '8px', borderLeft: '4px solid #3b82f6' }}>
            <p style={{ fontSize: '14px', lineHeight: '1.6', color: '#374151', margin: 0 }}>
              <strong>Key Formula:</strong> Present Value = Σ (Free Cash Flow / (1 + Discount Rate)^n)
            </p>
          </div>
        </div>

        <div style={{ marginBottom: '32px' }}>
          <h3 style={{ fontSize: '22px', fontWeight: '600', marginBottom: '12px', color: '#111827' }}>
            2. Earnings Power Value (EPV)
          </h3>
          <p style={{ fontSize: '16px', lineHeight: '1.7', color: '#374151', marginBottom: '12px' }}>
            <strong>Best for:</strong> Mature, stable businesses with consistent earnings
          </p>
          <p style={{ fontSize: '16px', lineHeight: '1.7', color: '#374151', marginBottom: '12px' }}>
            EPV assumes the company maintains its current earnings power indefinitely (no growth). This conservative 
            approach values the business based on its ability to generate earnings in perpetuity, discounted to 
            present value. It's useful for identifying the minimum value of a stable business.
          </p>
          <div style={{ backgroundColor: '#f9fafb', padding: '16px', borderRadius: '8px', borderLeft: '4px solid #10b981' }}>
            <p style={{ fontSize: '14px', lineHeight: '1.6', color: '#374151', margin: 0 }}>
              <strong>Key Formula:</strong> EPV = Normalized Earnings / Discount Rate
            </p>
          </div>
        </div>

        <div style={{ marginBottom: '32px' }}>
          <h3 style={{ fontSize: '22px', fontWeight: '600', marginBottom: '12px', color: '#111827' }}>
            3. Asset-Based Valuation
          </h3>
          <p style={{ fontSize: '16px', lineHeight: '1.7', color: '#374151', marginBottom: '12px' }}>
            <strong>Best for:</strong> Asset-heavy businesses, liquidation scenarios, or companies with significant tangible assets
          </p>
          <p style={{ fontSize: '16px', lineHeight: '1.7', color: '#374151', marginBottom: '12px' }}>
            This method values a company based on its net assets (assets minus liabilities). It's particularly useful 
            for companies where the liquidation value or book value is meaningful, such as real estate companies, 
            manufacturing firms, or financial institutions.
          </p>
          <div style={{ backgroundColor: '#f9fafb', padding: '16px', borderRadius: '8px', borderLeft: '4px solid #f59e0b' }}>
            <p style={{ fontSize: '14px', lineHeight: '1.6', color: '#374151', margin: 0 }}>
              <strong>Key Formula:</strong> Asset Value = Total Assets - Total Liabilities (adjusted for market values where applicable)
            </p>
          </div>
        </div>

        <div style={{ backgroundColor: '#eff6ff', padding: '20px', borderRadius: '8px', border: '1px solid #bfdbfe', marginTop: '24px' }}>
          <h4 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '12px', color: '#1e40af' }}>
            Weighted Average Calculation
          </h4>
          <p style={{ fontSize: '16px', lineHeight: '1.7', color: '#374151', marginBottom: '16px' }}>
            The final intrinsic value is calculated as a <strong>weighted average</strong> of these three methods. 
            The weights are dynamically determined based on the company's business characteristics, ensuring the most 
            appropriate valuation method receives the highest weight.
          </p>
          
          <h5 style={{ fontSize: '16px', fontWeight: '600', marginTop: '20px', marginBottom: '12px', color: '#1e40af' }}>
            How Business Type is Determined
          </h5>
          <p style={{ fontSize: '15px', lineHeight: '1.6', color: '#374151', marginBottom: '12px' }}>
            The system analyzes multiple factors to classify each company:
          </p>
          <ul style={{ fontSize: '15px', lineHeight: '1.6', color: '#374151', paddingLeft: '24px', marginBottom: '20px' }}>
            <li><strong>Revenue Growth Rate:</strong> Multi-year trend analysis</li>
            <li><strong>Asset Intensity:</strong> Ratio of total assets to revenue</li>
            <li><strong>Growth Volatility:</strong> Consistency of growth patterns</li>
            <li><strong>Industry Characteristics:</strong> Asset-heavy vs. asset-light business models</li>
          </ul>

          <div style={{ backgroundColor: '#fef3c7', padding: '16px', borderRadius: '6px', marginTop: '20px', borderLeft: '4px solid #f59e0b' }}>
            <p style={{ fontSize: '14px', lineHeight: '1.6', color: '#92400e', margin: 0 }}>
              <strong>Note:</strong> If any valuation method returns an invalid value (zero or negative), its weight is 
              automatically redistributed proportionally among the remaining valid methods. This ensures the final 
              valuation always uses the best available data.
            </p>
          </div>
        </div>
      </section>

      {/* Analysis Weights & Presets Section */}
      <section style={{ marginBottom: '60px' }}>
        <h2 style={{ fontSize: '28px', fontWeight: '600', marginBottom: '24px', color: '#111827', borderBottom: '2px solid #e5e7eb', paddingBottom: '8px' }}>
          Analysis Weights & Business Type Presets
        </h2>
        <p style={{ fontSize: '16px', lineHeight: '1.7', color: '#374151', marginBottom: '24px' }}>
          The tool includes 20 pre-configured business type presets, each optimized for specific industries and business models 
          based on industry-standard valuation practices. You can select a preset or manually configure weights to customize the analysis.
        </p>


        <h3 style={{ fontSize: '22px', fontWeight: '600', marginBottom: '16px', marginTop: '32px', color: '#111827' }}>
          All Available Presets
        </h3>

        {/* High Growth */}
        <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', marginBottom: '16px', border: '1px solid #e5e7eb', borderLeft: '4px solid #3b82f6' }}>
          <h4 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '8px', color: '#111827' }}>1. High Growth</h4>
          <p style={{ fontSize: '14px', color: '#6b7280', marginBottom: '12px' }}><strong>Best for:</strong> Technology startups, biotech, high-growth SaaS companies</p>
          <div style={{ fontSize: '14px' }}>
            <strong style={{ color: '#374151' }}>Valuation Weights:</strong> DCF 55% | EPV 25% | Asset 20%
          </div>
        </div>

        {/* Growth */}
        <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', marginBottom: '16px', border: '1px solid #e5e7eb', borderLeft: '4px solid #10b981' }}>
          <h4 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '8px', color: '#111827' }}>2. Growth</h4>
          <p style={{ fontSize: '14px', color: '#6b7280', marginBottom: '12px' }}><strong>Best for:</strong> Established growth companies, expanding businesses</p>
          <div style={{ fontSize: '14px' }}>
            <strong style={{ color: '#374151' }}>Valuation Weights:</strong> DCF 50% | EPV 30% | Asset 20%
          </div>
        </div>

        {/* Mature */}
        <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', marginBottom: '16px', border: '1px solid #e5e7eb', borderLeft: '4px solid #6b7280' }}>
          <h4 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '8px', color: '#111827' }}>3. Mature</h4>
          <p style={{ fontSize: '14px', color: '#6b7280', marginBottom: '12px' }}><strong>Best for:</strong> Stable, established companies, blue-chip stocks</p>
          <div style={{ fontSize: '14px' }}>
            <strong style={{ color: '#374151' }}>Valuation Weights:</strong> DCF 50% | EPV 35% | Asset 15%
          </div>
        </div>

        {/* Cyclical */}
        <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', marginBottom: '16px', border: '1px solid #e5e7eb', borderLeft: '4px solid #f59e0b' }}>
          <h4 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '8px', color: '#111827' }}>4. Cyclical</h4>
          <p style={{ fontSize: '14px', color: '#6b7280', marginBottom: '12px' }}><strong>Best for:</strong> Industrial, manufacturing, materials, energy companies</p>
          <div style={{ fontSize: '14px' }}>
            <strong style={{ color: '#374151' }}>Valuation Weights:</strong> DCF 25% | EPV 50% | Asset 25%
          </div>
        </div>

        {/* Asset Heavy */}
        <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', marginBottom: '16px', border: '1px solid #e5e7eb', borderLeft: '4px solid #8b5cf6' }}>
          <h4 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '8px', color: '#111827' }}>5. Asset Heavy</h4>
          <p style={{ fontSize: '14px', color: '#6b7280', marginBottom: '12px' }}><strong>Best for:</strong> Real estate, utilities, infrastructure, capital-intensive businesses</p>
          <div style={{ fontSize: '14px' }}>
            <strong style={{ color: '#374151' }}>Valuation Weights:</strong> DCF 20% | EPV 25% | Asset 55%
          </div>
        </div>

        {/* Distressed */}
        <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', marginBottom: '16px', border: '1px solid #e5e7eb', borderLeft: '4px solid #ef4444' }}>
          <h4 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '8px', color: '#111827' }}>6. Distressed</h4>
          <p style={{ fontSize: '14px', color: '#6b7280', marginBottom: '12px' }}><strong>Best for:</strong> Companies in financial difficulty, turnaround situations</p>
          <div style={{ fontSize: '14px' }}>
            <strong style={{ color: '#374151' }}>Valuation Weights:</strong> DCF 10% | EPV 10% | Asset 80%
          </div>
        </div>

        {/* Bank */}
        <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', marginBottom: '16px', border: '1px solid #e5e7eb', borderLeft: '4px solid #059669' }}>
          <h4 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '8px', color: '#111827' }}>7. Bank</h4>
          <p style={{ fontSize: '14px', color: '#6b7280', marginBottom: '12px' }}><strong>Best for:</strong> Banks, financial services, credit institutions</p>
          <div style={{ fontSize: '14px', marginBottom: '8px' }}>
            <strong style={{ color: '#374151' }}>Valuation Weights:</strong> DCF 25% | EPV 50% | Asset 25%
          </div>
          <p style={{ fontSize: '13px', color: '#059669', fontStyle: 'italic', margin: 0 }}>Includes: Net Interest Margin (NIM), Efficiency Ratio, Loan-to-Deposit Ratio</p>
        </div>

        {/* REIT */}
        <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', marginBottom: '16px', border: '1px solid #e5e7eb', borderLeft: '4px solid #dc2626' }}>
          <h4 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '8px', color: '#111827' }}>8. REIT</h4>
          <p style={{ fontSize: '14px', color: '#6b7280', marginBottom: '12px' }}><strong>Best for:</strong> Real Estate Investment Trusts</p>
          <div style={{ fontSize: '14px', marginBottom: '8px' }}>
            <strong style={{ color: '#374151' }}>Valuation Weights:</strong> DCF 30% | EPV 20% | Asset 50%
          </div>
          <p style={{ fontSize: '13px', color: '#dc2626', fontStyle: 'italic', margin: 0 }}>Includes: FFO, AFFO, NAV, Dividend Yield, Payout Ratio</p>
        </div>

        {/* Insurance */}
        <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', marginBottom: '16px', border: '1px solid #e5e7eb', borderLeft: '4px solid #0284c7' }}>
          <h4 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '8px', color: '#111827' }}>9. Insurance</h4>
          <p style={{ fontSize: '14px', color: '#6b7280', marginBottom: '12px' }}><strong>Best for:</strong> Insurance companies, reinsurance</p>
          <div style={{ fontSize: '14px', marginBottom: '8px' }}>
            <strong style={{ color: '#374151' }}>Valuation Weights:</strong> DCF 20% | EPV 50% | Asset 30%
          </div>
          <p style={{ fontSize: '13px', color: '#0284c7', fontStyle: 'italic', margin: 0 }}>Includes: Combined Ratio, Loss Ratio, Expense Ratio, Reserve Adequacy</p>
        </div>

        {/* Utility */}
        <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', marginBottom: '16px', border: '1px solid #e5e7eb', borderLeft: '4px solid #0ea5e9' }}>
          <h4 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '8px', color: '#111827' }}>10. Utility</h4>
          <p style={{ fontSize: '14px', color: '#6b7280', marginBottom: '12px' }}><strong>Best for:</strong> Electric, water, gas utilities</p>
          <div style={{ fontSize: '14px' }}>
            <strong style={{ color: '#374151' }}>Valuation Weights:</strong> DCF 45% | EPV 35% | Asset 20%
          </div>
        </div>

        {/* Technology */}
        <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', marginBottom: '16px', border: '1px solid #e5e7eb', borderLeft: '4px solid #6366f1' }}>
          <h4 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '8px', color: '#111827' }}>11. Technology</h4>
          <p style={{ fontSize: '14px', color: '#6b7280', marginBottom: '12px' }}><strong>Best for:</strong> Software, internet, semiconductor, tech companies</p>
          <div style={{ fontSize: '14px' }}>
            <strong style={{ color: '#374151' }}>Valuation Weights:</strong> DCF 50% | EPV 35% | Asset 15%
          </div>
        </div>

        {/* Healthcare */}
        <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', marginBottom: '16px', border: '1px solid #e5e7eb', borderLeft: '4px solid #ec4899' }}>
          <h4 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '8px', color: '#111827' }}>12. Healthcare</h4>
          <p style={{ fontSize: '14px', color: '#6b7280', marginBottom: '12px' }}><strong>Best for:</strong> Pharmaceuticals, biotech, medical devices, healthcare services</p>
          <div style={{ fontSize: '14px' }}>
            <strong style={{ color: '#374151' }}>Valuation Weights:</strong> DCF 50% | EPV 35% | Asset 15%
          </div>
        </div>

        {/* Retail */}
        <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', marginBottom: '16px', border: '1px solid #e5e7eb', borderLeft: '4px solid #f97316' }}>
          <h4 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '8px', color: '#111827' }}>13. Retail</h4>
          <p style={{ fontSize: '14px', color: '#6b7280', marginBottom: '12px' }}><strong>Best for:</strong> Retail stores, consumer goods, e-commerce</p>
          <div style={{ fontSize: '14px' }}>
            <strong style={{ color: '#374151' }}>Valuation Weights:</strong> DCF 50% | EPV 35% | Asset 15%
          </div>
        </div>

        {/* Energy */}
        <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', marginBottom: '16px', border: '1px solid #e5e7eb', borderLeft: '4px solid #eab308' }}>
          <h4 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '8px', color: '#111827' }}>14. Energy</h4>
          <p style={{ fontSize: '14px', color: '#6b7280', marginBottom: '12px' }}><strong>Best for:</strong> Oil & gas, mining, energy exploration</p>
          <div style={{ fontSize: '14px' }}>
            <strong style={{ color: '#374151' }}>Valuation Weights:</strong> DCF 25% | EPV 40% | Asset 35%
          </div>
        </div>

        {/* Default */}
        <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', marginBottom: '16px', border: '1px solid #e5e7eb', borderLeft: '4px solid #6b7280' }}>
          <h4 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '8px', color: '#111827' }}>15. Default</h4>
          <p style={{ fontSize: '14px', color: '#6b7280', marginBottom: '12px' }}><strong>Best for:</strong> General purpose, unknown business types, balanced approach</p>
          <div style={{ fontSize: '14px' }}>
            <strong style={{ color: '#374151' }}>Valuation Weights:</strong> DCF 50% | EPV 35% | Asset 15%
          </div>
        </div>

        <div style={{ backgroundColor: '#f0fdf4', padding: '20px', borderRadius: '8px', marginTop: '24px', border: '1px solid #86efac' }}>
          <h4 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '12px', color: '#166534' }}>
            How to Use Presets
          </h4>
          <p style={{ fontSize: '15px', lineHeight: '1.6', color: '#374151', marginBottom: '12px' }}>
            The system automatically detects the business type based on sector, industry, revenue growth, and asset intensity. 
            You can also manually select a preset or configure custom weights:
          </p>
          <ol style={{ fontSize: '15px', lineHeight: '1.6', color: '#374151', paddingLeft: '24px' }}>
            <li>Click the <strong>"⚙️ [Business Type] (Weighting)"</strong> button on any stock analysis page</li>
            <li>Select a business type preset from the dropdown, or switch to "Manual Configuration"</li>
            <li>Click <strong>"Re-analyze with New Weights"</strong> to apply the changes</li>
          </ol>
          <p style={{ fontSize: '14px', lineHeight: '1.6', color: '#166534', marginTop: '12px', margin: 0 }}>
            <strong>Note:</strong> Specialized presets (Bank, REIT, Insurance) include additional industry-specific metrics 
            that are automatically calculated when those presets are selected.
          </p>
        </div>
      </section>

      {/* Analysis Components Section */}
      <section style={{ marginBottom: '60px' }}>
        <h2 style={{ fontSize: '28px', fontWeight: '600', marginBottom: '24px', color: '#111827', borderBottom: '2px solid #e5e7eb', paddingBottom: '8px' }}>
          Analysis Components
        </h2>

        <div style={{ marginBottom: '32px' }}>
          <h3 style={{ fontSize: '22px', fontWeight: '600', marginBottom: '12px', color: '#111827' }}>
            Margin of Safety
          </h3>
          <p style={{ fontSize: '16px', lineHeight: '1.7', color: '#374151' }}>
            The margin of safety is the percentage discount between the current market price and the calculated intrinsic value. 
            Value investing principles recommend looking for stocks trading at 30-50% below intrinsic value. This provides 
            a buffer against estimation errors and market volatility.
          </p>
        </div>

        <div style={{ marginBottom: '32px' }}>
          <h3 style={{ fontSize: '22px', fontWeight: '600', marginBottom: '12px', color: '#111827' }}>
            Financial Health
          </h3>
          <p style={{ fontSize: '16px', lineHeight: '1.7', color: '#374151' }}>
            Analyzes the company's financial stability through metrics like:
          </p>
          <ul style={{ fontSize: '16px', lineHeight: '1.7', color: '#374151', paddingLeft: '24px', marginTop: '8px' }}>
            <li><strong>Debt-to-Equity Ratio:</strong> Measures financial leverage and risk</li>
            <li><strong>Current Ratio:</strong> Assesses short-term liquidity</li>
            <li><strong>Interest Coverage:</strong> Ability to service debt obligations</li>
            <li><strong>Free Cash Flow:</strong> Cash available after capital expenditures</li>
            <li><strong>Profitability Metrics:</strong> ROE, ROA, profit margins</li>
          </ul>
        </div>

        <div style={{ marginBottom: '32px' }}>
          <h3 style={{ fontSize: '22px', fontWeight: '600', marginBottom: '12px', color: '#111827' }}>
            Business Quality
          </h3>
          <p style={{ fontSize: '16px', lineHeight: '1.7', color: '#374151' }}>
            Evaluates the company's competitive position and business model strength:
          </p>
          <ul style={{ fontSize: '16px', lineHeight: '1.7', color: '#374151', paddingLeft: '24px', marginTop: '8px' }}>
            <li><strong>Competitive Moat:</strong> Sustainable competitive advantages</li>
            <li><strong>Market Position:</strong> Industry leadership and market share</li>
            <li><strong>Business Model:</strong> Revenue quality and predictability</li>
            <li><strong>Operational Efficiency:</strong> How well the company uses its assets</li>
          </ul>
        </div>

        <div style={{ marginBottom: '32px' }}>
          <h3 style={{ fontSize: '22px', fontWeight: '600', marginBottom: '12px', color: '#111827' }}>
            Growth Metrics
          </h3>
          <p style={{ fontSize: '16px', lineHeight: '1.7', color: '#374151' }}>
            Analyzes historical and projected growth rates:
          </p>
          <ul style={{ fontSize: '16px', lineHeight: '1.7', color: '#374151', paddingLeft: '24px', marginTop: '8px' }}>
            <li><strong>Revenue Growth:</strong> Top-line growth trends</li>
            <li><strong>Earnings Growth:</strong> Bottom-line growth trends</li>
            <li><strong>Free Cash Flow Growth:</strong> Cash generation growth</li>
            <li><strong>Growth Consistency:</strong> Stability of growth over time</li>
          </ul>
        </div>

        <div style={{ marginBottom: '32px' }}>
          <h3 style={{ fontSize: '22px', fontWeight: '600', marginBottom: '12px', color: '#111827' }}>
            Price Ratios
          </h3>
          <p style={{ fontSize: '16px', lineHeight: '1.7', color: '#374151' }}>
            Compares current market valuation to fundamental metrics:
          </p>
          <ul style={{ fontSize: '16px', lineHeight: '1.7', color: '#374151', paddingLeft: '24px', marginTop: '8px' }}>
            <li><strong>P/E Ratio:</strong> Price-to-Earnings (compared to industry and historical averages)</li>
            <li><strong>P/B Ratio:</strong> Price-to-Book (useful for asset-heavy companies)</li>
            <li><strong>P/FCF Ratio:</strong> Price-to-Free Cash Flow (cash generation efficiency)</li>
            <li><strong>EV/EBITDA:</strong> Enterprise Value to EBITDA (normalized for capital structure)</li>
          </ul>
        </div>

        <div style={{ marginBottom: '32px' }}>
          <h3 style={{ fontSize: '22px', fontWeight: '600', marginBottom: '12px', color: '#111827' }}>
            Management Quality
          </h3>
          <p style={{ fontSize: '16px', lineHeight: '1.7', color: '#374151' }}>
            Assesses management effectiveness through financial performance:
          </p>
          <ul style={{ fontSize: '16px', lineHeight: '1.7', color: '#374151', paddingLeft: '24px', marginTop: '8px' }}>
            <li><strong>Capital Allocation:</strong> How management invests company resources</li>
            <li><strong>Return on Equity (ROE):</strong> Management's efficiency in generating returns</li>
            <li><strong>Return on Assets (ROA):</strong> Asset utilization efficiency</li>
            <li><strong>Earnings Quality:</strong> Consistency and sustainability of earnings</li>
          </ul>
        </div>
      </section>

      {/* Data Quality Section */}
      <section style={{ marginBottom: '60px' }}>
        <h2 style={{ fontSize: '28px', fontWeight: '600', marginBottom: '24px', color: '#111827', borderBottom: '2px solid #e5e7eb', paddingBottom: '8px' }}>
          Data Quality & Sources
        </h2>
        <p style={{ fontSize: '16px', lineHeight: '1.7', color: '#374151', marginBottom: '16px' }}>
          The tool uses multiple data sources to ensure accuracy and reliability:
        </p>
        <ul style={{ fontSize: '16px', lineHeight: '1.7', color: '#374151', paddingLeft: '24px', marginBottom: '16px' }}>
          <li><strong>Yahoo Finance:</strong> Primary source for stock prices, company info, and financial statements</li>
          <li><strong>Alpha Vantage:</strong> Backup data source and financial statement data</li>
          <li><strong>Financial Modeling Prep:</strong> Additional backup for price and company data</li>
          <li><strong>MarketStack:</strong> Alternative backup data source</li>
          <li><strong>SEC EDGAR:</strong> Official financial filings for verification</li>
        </ul>
        <div style={{ backgroundColor: '#fef3c7', padding: '16px', borderRadius: '8px', borderLeft: '4px solid #f59e0b' }}>
          <p style={{ fontSize: '14px', lineHeight: '1.6', color: '#92400e', margin: 0 }}>
            <strong>Note:</strong> The tool includes data quality warnings when assumptions are made or data is incomplete. 
            Always review these warnings and consider uploading PDF financial statements for custom/private companies.
          </p>
        </div>
      </section>

      {/* Methodology Section */}
      <section style={{ marginBottom: '60px' }}>
        <h2 style={{ fontSize: '28px', fontWeight: '600', marginBottom: '24px', color: '#111827', borderBottom: '2px solid #e5e7eb', paddingBottom: '8px' }}>
          Investment Philosophy
        </h2>
        <p style={{ fontSize: '16px', lineHeight: '1.7', color: '#374151', marginBottom: '16px' }}>
          This tool is based on value investing principles, which emphasize:
        </p>
        <ul style={{ fontSize: '16px', lineHeight: '1.7', color: '#374151', paddingLeft: '24px' }}>
          <li><strong>Value Investing:</strong> Buying stocks below their intrinsic value</li>
          <li><strong>Margin of Safety:</strong> Requiring a significant discount (30-50%) to intrinsic value</li>
          <li><strong>Long-Term Focus:</strong> Investing in quality businesses for the long term</li>
          <li><strong>Fundamental Analysis:</strong> Deep understanding of business fundamentals</li>
          <li><strong>Quality First:</strong> Preferring great businesses at fair prices over fair businesses at great prices</li>
        </ul>
      </section>

      {/* Disclaimer */}
      <section style={{ backgroundColor: '#f3f4f6', padding: '24px', borderRadius: '8px', marginTop: '60px' }}>
        <h3 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '12px', color: '#111827' }}>
          Important Disclaimer
        </h3>
        <p style={{ fontSize: '14px', lineHeight: '1.6', color: '#6b7280', margin: 0 }}>
          This tool is for educational and research purposes only. The analysis and valuations are estimates based on 
          available data and should not be considered as investment advice. Always conduct your own research and 
          consult with a qualified financial advisor before making investment decisions. Past performance does not 
          guarantee future results.
        </p>
      </section>
    </div>
  )
}

