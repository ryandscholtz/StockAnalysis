'use client'

export default function AboutPage() {
  return (
    <div className="container" style={{ maxWidth: '900px', margin: '0 auto', padding: '40px 20px' }}>
      <h1 style={{ fontSize: '36px', fontWeight: '700', marginBottom: '8px', color: 'var(--text-primary)' }}>
        About
      </h1>
      <p style={{ fontSize: '18px', color: 'var(--text-muted)', marginBottom: '40px' }}>
        How this tool works — the methodology, models, and philosophy behind each analysis
      </p>

      {/* Overview Section */}
      <section style={{ marginBottom: '60px' }}>
        <h2 style={{ fontSize: '28px', fontWeight: '600', marginBottom: '16px', color: 'var(--text-primary)', borderBottom: '2px solid var(--border-default)', paddingBottom: '8px' }}>
          Overview
        </h2>
        <p style={{ fontSize: '16px', lineHeight: '1.7', color: 'var(--text-secondary)', marginBottom: '16px' }}>
          This tool uses value investing principles to analyze stocks. The analysis focuses on calculating
          <strong> intrinsic value</strong> (the true worth of a business) and comparing it to the current market price
          to determine the <strong>margin of safety</strong>.
        </p>
        <p style={{ fontSize: '16px', lineHeight: '1.7', color: 'var(--text-secondary)' }}>
          The goal is to find stocks trading at a significant discount to their intrinsic value (ideally 30-50% discount),
          which provides a safety buffer against estimation errors and market volatility.
        </p>
      </section>

      {/* Valuation Models Section */}
      <section style={{ marginBottom: '60px' }}>
        <h2 style={{ fontSize: '28px', fontWeight: '600', marginBottom: '24px', color: 'var(--text-primary)', borderBottom: '2px solid var(--border-default)', paddingBottom: '8px' }}>
          Valuation Models
        </h2>
        <p style={{ fontSize: '16px', lineHeight: '1.7', color: 'var(--text-secondary)', marginBottom: '24px' }}>
          The tool calculates intrinsic value using four complementary methods, then combines them into a single
          weighted fair value estimate. Each model captures a different dimension of a company's worth, so using
          all four together produces a more robust estimate than any single method alone.
        </p>

        {/* Model 1: DCF */}
        <div style={{ marginBottom: '32px' }}>
          <h3 style={{ fontSize: '22px', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '12px' }}>
            1. Discounted Cash Flow (DCF)
          </h3>
          <p style={{ fontSize: '16px', lineHeight: '1.7', color: 'var(--text-secondary)', marginBottom: '12px' }}>
            <strong>Best for:</strong> Companies with predictable, growing free cash flows — technology, consumer staples, industrials.
          </p>
          <p style={{ fontSize: '16px', lineHeight: '1.7', color: 'var(--text-secondary)', marginBottom: '12px' }}>
            DCF projects the company's future free cash flows over a multi-year period (typically 5–10 years), then
            discounts them back to today's money using a required rate of return (discount rate). A terminal value
            is added to capture cash flows beyond the projection window. The sum of all discounted cash flows,
            divided by shares outstanding, gives the intrinsic value per share.
          </p>
          <p style={{ fontSize: '16px', lineHeight: '1.7', color: 'var(--text-secondary)', marginBottom: '12px' }}>
            DCF is the gold standard of intrinsic value analysis because it is grounded in the fundamental
            principle that an asset is worth the present value of all cash it will generate over its lifetime.
            However, it is sensitive to growth rate and discount rate assumptions — small changes in inputs can
            produce very different outputs.
          </p>
          <div style={{ backgroundColor: 'var(--docs-note-teal-bg)', padding: '16px', borderRadius: '8px', borderLeft: '4px solid #0d9488' }}>
            <p style={{ fontSize: '14px', lineHeight: '1.6', color: 'var(--text-secondary)', margin: 0 }}>
              <strong>Formula:</strong> Intrinsic Value = Σ (FCF × (1 + g)ⁿ / (1 + r)ⁿ) + Terminal Value / (1 + r)ⁿ
              <br />where FCF = free cash flow, g = growth rate, r = discount rate, n = year
            </p>
          </div>
        </div>

        {/* Model 2: P/E */}
        <div style={{ marginBottom: '32px' }}>
          <h3 style={{ fontSize: '22px', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '12px' }}>
            2. P/E Model (Price-to-Earnings)
          </h3>
          <p style={{ fontSize: '16px', lineHeight: '1.7', color: 'var(--text-secondary)', marginBottom: '12px' }}>
            <strong>Best for:</strong> Profitable companies across most sectors where earnings are the primary value driver.
          </p>
          <p style={{ fontSize: '16px', lineHeight: '1.7', color: 'var(--text-secondary)', marginBottom: '12px' }}>
            The P/E model estimates intrinsic value by multiplying the company's earnings per share (EPS) by an
            appropriate P/E ratio. The P/E ratio used is sourced from the company's own reported ratio or a
            sector average — whichever better reflects a fair multiple for the business. This approach is simple,
            widely understood, and directly comparable across companies in the same industry.
          </p>
          <p style={{ fontSize: '16px', lineHeight: '1.7', color: 'var(--text-secondary)', marginBottom: '12px' }}>
            The P/E model anchors the valuation to actual reported earnings, which makes it less reliant on
            long-range forecasts than DCF. It works best when earnings are stable and the chosen P/E multiple
            reflects the company's growth prospects and risk profile accurately.
          </p>
          <div style={{ backgroundColor: 'var(--docs-note-purple-bg)', padding: '16px', borderRadius: '8px', borderLeft: '4px solid #7c3aed' }}>
            <p style={{ fontSize: '14px', lineHeight: '1.6', color: 'var(--text-secondary)', margin: 0 }}>
              <strong>Formula:</strong> Fair Value per Share = EPS × Industry P/E Ratio
              <br />where EPS = net income / shares outstanding
            </p>
          </div>
        </div>

        {/* Model 3: EPV */}
        <div style={{ marginBottom: '32px' }}>
          <h3 style={{ fontSize: '22px', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '12px' }}>
            3. Earnings Power Value (EPV)
          </h3>
          <p style={{ fontSize: '16px', lineHeight: '1.7', color: 'var(--text-secondary)', marginBottom: '12px' }}>
            <strong>Best for:</strong> Mature, stable businesses where current earnings are a reliable indicator of future performance.
          </p>
          <p style={{ fontSize: '16px', lineHeight: '1.7', color: 'var(--text-secondary)', marginBottom: '12px' }}>
            EPV, developed by Columbia Business School professor Bruce Greenwald, is a deliberately conservative
            valuation. It assumes the company will maintain its current level of earnings indefinitely — zero
            growth. This makes it a useful floor value: if the market price is below EPV, the stock is cheap
            even under the most pessimistic assumption about future growth.
          </p>
          <p style={{ fontSize: '16px', lineHeight: '1.7', color: 'var(--text-secondary)', marginBottom: '12px' }}>
            Unlike DCF, EPV requires no growth assumptions, which eliminates a major source of estimation error.
            The trade-off is that it can significantly undervalue high-growth companies.
          </p>
          <div style={{ backgroundColor: 'var(--docs-note-cyan-bg)', padding: '16px', borderRadius: '8px', borderLeft: '4px solid #0891b2' }}>
            <p style={{ fontSize: '14px', lineHeight: '1.6', color: 'var(--text-secondary)', margin: 0 }}>
              <strong>Formula:</strong> EPV per Share = (Operating Income × (1 − Tax Rate)) / Discount Rate / Shares Outstanding
            </p>
          </div>
        </div>

        {/* Model 4: Book Value */}
        <div style={{ marginBottom: '32px' }}>
          <h3 style={{ fontSize: '22px', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '12px' }}>
            4. Book Value
          </h3>
          <p style={{ fontSize: '16px', lineHeight: '1.7', color: 'var(--text-secondary)', marginBottom: '12px' }}>
            <strong>Best for:</strong> Asset-heavy businesses — banks, insurance companies, manufacturers, and real estate firms where tangible assets are central to the business model.
          </p>
          <p style={{ fontSize: '16px', lineHeight: '1.7', color: 'var(--text-secondary)', marginBottom: '12px' }}>
            Book value per share is the accounting value of a company's equity divided by its shares outstanding.
            It represents the amount shareholders would theoretically receive if the company were liquidated at
            balance sheet values. While book value rarely equals true market value (due to unrecorded intangibles
            like brand or intellectual property), it provides an important anchor for the downside — particularly
            for financial companies where asset quality is the primary risk.
          </p>
          <p style={{ fontSize: '16px', lineHeight: '1.7', color: 'var(--text-secondary)', marginBottom: '12px' }}>
            Stocks trading below book value (price-to-book &lt; 1) are often considered statistically cheap and
            have historically outperformed as a group, though this signal is less reliable for asset-light
            businesses.
          </p>
          <div style={{ backgroundColor: 'var(--docs-note-blue-bg)', padding: '16px', borderRadius: '8px', borderLeft: '4px solid #0284c7' }}>
            <p style={{ fontSize: '14px', lineHeight: '1.6', color: 'var(--text-secondary)', margin: 0 }}>
              <strong>Formula:</strong> Book Value per Share = Total Stockholder Equity / Shares Outstanding
            </p>
          </div>
        </div>
      </section>

      {/* Analysis Weights & Presets Section */}
      <section style={{ marginBottom: '60px' }}>
        <h2 style={{ fontSize: '28px', fontWeight: '600', marginBottom: '24px', color: 'var(--text-primary)', borderBottom: '2px solid var(--border-default)', paddingBottom: '8px' }}>
          Analysis Weights & Business Type Presets
        </h2>
        <p style={{ fontSize: '16px', lineHeight: '1.7', color: 'var(--text-secondary)', marginBottom: '12px' }}>
          The four model outputs (DCF, P/E, EPV, and Book Value) are combined into a single fair value estimate using a
          weighted average. You choose the weights via a preset or custom configuration: DCF is often weighted highest
          because it is the most comprehensive (current earnings and future growth), P/E grounds the valuation in
          reported earnings, EPV provides a conservative floor, and Book Value guards against overpaying for
          asset-light businesses. If a model produces an invalid result (zero, negative, or missing data), its weight
          is automatically redistributed proportionally across the remaining valid models, so the final fair value
          always uses the best available data.
        </p>
        <p style={{ fontSize: '16px', lineHeight: '1.7', color: 'var(--text-secondary)', marginBottom: '24px' }}>
          The tool includes 15 pre-configured business type presets, each optimized for specific industries and business models
          based on industry-standard valuation practices. You can select a preset or manually configure weights to customize the analysis.
        </p>

        <h3 style={{ fontSize: '22px', fontWeight: '600', marginBottom: '16px', marginTop: '32px', color: 'var(--text-primary)' }}>
          All Available Presets
        </h3>

        <div style={{ overflowX: 'auto', marginBottom: '8px' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '14px' }}>
            <thead>
              <tr style={{ background: 'var(--bg-hover)' }}>
                <th style={{ textAlign: 'left', padding: '10px 14px', fontWeight: '600', color: 'var(--text-secondary)', borderBottom: '2px solid var(--border-default)', whiteSpace: 'nowrap' }}>Preset</th>
                <th style={{ textAlign: 'left', padding: '10px 14px', fontWeight: '600', color: 'var(--text-secondary)', borderBottom: '2px solid var(--border-default)' }}>Best For</th>
                <th style={{ textAlign: 'center', padding: '10px 14px', fontWeight: '600', color: '#f59e0b', borderBottom: '2px solid var(--border-default)', whiteSpace: 'nowrap' }}>DCF</th>
                <th style={{ textAlign: 'center', padding: '10px 14px', fontWeight: '600', color: '#7c3aed', borderBottom: '2px solid var(--border-default)', whiteSpace: 'nowrap' }}>P/E</th>
                <th style={{ textAlign: 'center', padding: '10px 14px', fontWeight: '600', color: '#0891b2', borderBottom: '2px solid var(--border-default)', whiteSpace: 'nowrap' }}>EPV</th>
                <th style={{ textAlign: 'center', padding: '10px 14px', fontWeight: '600', color: '#4f46e5', borderBottom: '2px solid var(--border-default)', whiteSpace: 'nowrap' }}>Book</th>
              </tr>
            </thead>
            <tbody>
              {[
                { name: 'High Growth',        bestFor: 'Technology startups, high-growth SaaS, biotech',               dcf: 60, pe: 15, epv: 20, book:  5 },
                { name: 'Growth Company',     bestFor: 'Established growth companies, expanding businesses',           dcf: 50, pe: 25, epv: 15, book: 10 },
                { name: 'Mature Company',     bestFor: 'Stable blue-chips, dividend payers',                           dcf: 35, pe: 35, epv: 20, book: 10 },
                { name: 'Technology',         bestFor: 'Software, internet, semiconductors',                           dcf: 50, pe: 25, epv: 20, book:  5 },
                { name: 'Healthcare',         bestFor: 'Pharma, biotech, medical devices, healthcare services',        dcf: 45, pe: 25, epv: 25, book:  5 },
                { name: 'Retail',             bestFor: 'Retail stores, consumer goods, e-commerce',                   dcf: 40, pe: 30, epv: 20, book: 10 },
                { name: 'Utility',            bestFor: 'Electric, water, gas utilities',                               dcf: 40, pe: 20, epv: 30, book: 10 },
                { name: 'Cyclical',           bestFor: 'Industrials, manufacturing, materials',                        dcf: 25, pe: 25, epv: 35, book: 15 },
                { name: 'Energy',             bestFor: 'Oil & gas, mining, energy exploration',                        dcf: 25, pe: 15, epv: 40, book: 20 },
                { name: 'Bank',               bestFor: 'Banks, financial services, credit institutions ★',             dcf: 20, pe: 30, epv: 35, book: 15 },
                { name: 'Insurance',          bestFor: 'Insurance companies, reinsurance ★',                           dcf: 20, pe: 25, epv: 40, book: 15 },
                { name: 'Asset Heavy',        bestFor: 'Infrastructure, capital-intensive businesses',                 dcf: 20, pe: 10, epv: 25, book: 45 },
                { name: 'REIT',               bestFor: 'Real Estate Investment Trusts ★',                              dcf: 30, pe: 10, epv: 15, book: 45 },
                { name: 'Distressed Company', bestFor: 'Companies in financial difficulty, turnaround situations',     dcf: 10, pe:  5, epv: 15, book: 70 },
                { name: 'Default',            bestFor: 'General purpose, balanced approach',                           dcf: 40, pe: 30, epv: 20, book: 10 },
              ].map((row, i) => (
                <tr key={row.name} style={{ background: i % 2 === 0 ? 'var(--bg-surface)' : 'var(--bg-surface-subtle)', borderBottom: '1px solid var(--border-default)' }}>
                  <td style={{ padding: '9px 14px', fontWeight: '600', color: 'var(--text-primary)', whiteSpace: 'nowrap' }}>{row.name}</td>
                  <td style={{ padding: '9px 14px', color: 'var(--text-muted)' }}>{row.bestFor}</td>
                  <td style={{ padding: '9px 14px', textAlign: 'center', color: '#92400e', fontWeight: '500' }}>{row.dcf}%</td>
                  <td style={{ padding: '9px 14px', textAlign: 'center', color: '#5b21b6', fontWeight: '500' }}>{row.pe}%</td>
                  <td style={{ padding: '9px 14px', textAlign: 'center', color: '#0e7490', fontWeight: '500' }}>{row.epv}%</td>
                  <td style={{ padding: '9px 14px', textAlign: 'center', color: '#3730a3', fontWeight: '500' }}>{row.book}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p style={{ fontSize: '12px', color: 'var(--text-subtle)', marginBottom: '24px' }}>
          ★ Includes additional industry-specific metrics (Bank: NIM, Efficiency Ratio; REIT: FFO, AFFO, NAV; Insurance: Combined Ratio, Loss Ratio)
        </p>

        <div style={{ backgroundColor: 'var(--docs-note-green-bg)', padding: '20px', borderRadius: '8px', marginTop: '24px', border: '1px solid #86efac' }}>
          <h4 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '12px', color: 'var(--status-success-text)' }}>
            How to Use Presets
          </h4>
          <p style={{ fontSize: '15px', lineHeight: '1.6', color: 'var(--text-secondary)', marginBottom: '12px' }}>
            The system automatically detects the business type based on sector, industry, revenue growth, and asset intensity.
            You can also manually select a preset or configure custom weights:
          </p>
          <ol style={{ fontSize: '15px', lineHeight: '1.6', color: 'var(--text-secondary)', paddingLeft: '24px' }}>
            <li>Click the <strong>"⚙️ [Business Type] (Weighting)"</strong> button on any stock analysis page</li>
            <li>Select a business type preset from the dropdown, or switch to "Manual Configuration"</li>
            <li>Click <strong>"Re-analyze with New Weights"</strong> to apply the changes</li>
          </ol>
          <p style={{ fontSize: '14px', lineHeight: '1.6', color: 'var(--status-success-text)', marginTop: '12px', margin: 0 }}>
            <strong>Note:</strong> Specialised presets (Bank, REIT, Insurance) include additional industry-specific metrics
            that are automatically calculated when those presets are selected.
          </p>
        </div>
      </section>

      {/* Analysis Components Section */}
      <section style={{ marginBottom: '60px' }}>
        <h2 style={{ fontSize: '28px', fontWeight: '600', marginBottom: '24px', color: 'var(--text-primary)', borderBottom: '2px solid var(--border-default)', paddingBottom: '8px' }}>
          Analysis Components
        </h2>

        <div style={{ marginBottom: '32px' }}>
          <h3 style={{ fontSize: '22px', fontWeight: '600', marginBottom: '12px', color: 'var(--text-primary)' }}>
            Margin of Safety
          </h3>
          <p style={{ fontSize: '16px', lineHeight: '1.7', color: 'var(--text-secondary)' }}>
            The margin of safety is the percentage discount between the current market price and the calculated intrinsic value.
            Value investing principles recommend looking for stocks trading at 30–50% below intrinsic value. This provides
            a buffer against estimation errors and market volatility.
          </p>
        </div>

        <div style={{ marginBottom: '32px' }}>
          <h3 style={{ fontSize: '22px', fontWeight: '600', marginBottom: '12px', color: 'var(--text-primary)' }}>
            Financial Health
          </h3>
          <p style={{ fontSize: '16px', lineHeight: '1.7', color: 'var(--text-secondary)' }}>
            Analyses the company's financial stability through metrics like:
          </p>
          <ul style={{ fontSize: '16px', lineHeight: '1.7', color: 'var(--text-secondary)', paddingLeft: '24px', marginTop: '8px' }}>
            <li><strong>Debt-to-Equity Ratio:</strong> Measures financial leverage and risk</li>
            <li><strong>Current Ratio:</strong> Assesses short-term liquidity</li>
            <li><strong>Interest Coverage:</strong> Ability to service debt obligations</li>
            <li><strong>Free Cash Flow:</strong> Cash available after capital expenditures</li>
            <li><strong>Profitability Metrics:</strong> ROE, ROA, profit margins</li>
          </ul>
        </div>

        <div style={{ marginBottom: '32px' }}>
          <h3 style={{ fontSize: '22px', fontWeight: '600', marginBottom: '12px', color: 'var(--text-primary)' }}>
            Business Quality
          </h3>
          <p style={{ fontSize: '16px', lineHeight: '1.7', color: 'var(--text-secondary)' }}>
            Evaluates the company's competitive position and business model strength:
          </p>
          <ul style={{ fontSize: '16px', lineHeight: '1.7', color: 'var(--text-secondary)', paddingLeft: '24px', marginTop: '8px' }}>
            <li><strong>Competitive Moat:</strong> Sustainable competitive advantages</li>
            <li><strong>Market Position:</strong> Industry leadership and market share</li>
            <li><strong>Business Model:</strong> Revenue quality and predictability</li>
            <li><strong>Operational Efficiency:</strong> How well the company uses its assets</li>
          </ul>
        </div>

        <div style={{ marginBottom: '32px' }}>
          <h3 style={{ fontSize: '22px', fontWeight: '600', marginBottom: '12px', color: 'var(--text-primary)' }}>
            Growth Metrics
          </h3>
          <p style={{ fontSize: '16px', lineHeight: '1.7', color: 'var(--text-secondary)' }}>
            Analyses historical growth rates across revenue, earnings, and free cash flow:
          </p>
          <ul style={{ fontSize: '16px', lineHeight: '1.7', color: 'var(--text-secondary)', paddingLeft: '24px', marginTop: '8px' }}>
            <li><strong>Revenue Growth:</strong> Top-line growth trends</li>
            <li><strong>Earnings Growth:</strong> Bottom-line growth trends</li>
            <li><strong>Free Cash Flow Growth:</strong> Cash generation growth</li>
            <li><strong>Growth Consistency:</strong> Stability of growth over time</li>
          </ul>
        </div>

        <div style={{ marginBottom: '32px' }}>
          <h3 style={{ fontSize: '22px', fontWeight: '600', marginBottom: '12px', color: 'var(--text-primary)' }}>
            Price Ratios
          </h3>
          <p style={{ fontSize: '16px', lineHeight: '1.7', color: 'var(--text-secondary)' }}>
            Compares current market valuation to fundamental metrics:
          </p>
          <ul style={{ fontSize: '16px', lineHeight: '1.7', color: 'var(--text-secondary)', paddingLeft: '24px', marginTop: '8px' }}>
            <li><strong>P/E Ratio:</strong> Price-to-Earnings (compared to industry and historical averages)</li>
            <li><strong>P/B Ratio:</strong> Price-to-Book (useful for asset-heavy companies)</li>
            <li><strong>P/FCF Ratio:</strong> Price-to-Free Cash Flow (cash generation efficiency)</li>
            <li><strong>EV/EBITDA:</strong> Enterprise Value to EBITDA (normalised for capital structure)</li>
          </ul>
        </div>

        <div style={{ marginBottom: '32px' }}>
          <h3 style={{ fontSize: '22px', fontWeight: '600', marginBottom: '12px', color: 'var(--text-primary)' }}>
            Management Quality
          </h3>
          <p style={{ fontSize: '16px', lineHeight: '1.7', color: 'var(--text-secondary)' }}>
            Assesses management effectiveness through financial performance:
          </p>
          <ul style={{ fontSize: '16px', lineHeight: '1.7', color: 'var(--text-secondary)', paddingLeft: '24px', marginTop: '8px' }}>
            <li><strong>Capital Allocation:</strong> How management invests company resources</li>
            <li><strong>Return on Equity (ROE):</strong> Management's efficiency in generating returns</li>
            <li><strong>Return on Assets (ROA):</strong> Asset utilisation efficiency</li>
            <li><strong>Earnings Quality:</strong> Consistency and sustainability of earnings</li>
          </ul>
        </div>
      </section>

      {/* AI & Machine Learning Section */}
      <section style={{ marginBottom: '60px' }}>
        <h2 style={{ fontSize: '28px', fontWeight: '600', marginBottom: '24px', color: 'var(--text-primary)', borderBottom: '2px solid var(--border-default)', paddingBottom: '8px' }}>
          AI & Machine Learning
        </h2>
        <p style={{ fontSize: '16px', lineHeight: '1.7', color: 'var(--text-secondary)', marginBottom: '24px' }}>
          Claude (Anthropic's large language model, accessed via AWS Bedrock) is used at three distinct points in
          every analysis. It acts as a reasoning layer — not a replacement for quantitative models — handling tasks
          where structured rules alone fall short.
        </p>

        <div style={{ marginBottom: '32px' }}>
          <h3 style={{ fontSize: '22px', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '12px' }}>
            1. Automatic Preset Selection
          </h3>
          <p style={{ fontSize: '16px', lineHeight: '1.7', color: 'var(--text-secondary)', marginBottom: '12px' }}>
            When you run an analysis with the preset set to "Automatic", Claude reads the company's name, sector,
            and industry and selects the most appropriate valuation preset from the 15 available options. A bank
            should not be valued the same way as a SaaS company — the AI handles this classification step so the
            right weighting is applied without manual intervention.
          </p>
          <p style={{ fontSize: '16px', lineHeight: '1.7', color: 'var(--text-secondary)' }}>
            You can always override the selection by opening the weights panel and choosing a different preset or
            configuring custom weights manually.
          </p>
        </div>

        <div style={{ marginBottom: '32px' }}>
          <h3 style={{ fontSize: '22px', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '12px' }}>
            2. Financial Data Retrieval (Fallback)
          </h3>
          <p style={{ fontSize: '16px', lineHeight: '1.7', color: 'var(--text-secondary)', marginBottom: '12px' }}>
            The primary data pipeline pulls financial statements from Yahoo Finance, SEC EDGAR, and other market
            data providers. When these sources are unavailable, incomplete, or the ticker is not listed on a major
            US exchange, Claude is used as a fallback to supply the missing financial data — income statement,
            balance sheet, cash flow statement, and key metrics — from its training knowledge.
          </p>
          <p style={{ fontSize: '16px', lineHeight: '1.7', color: 'var(--text-secondary)', marginBottom: '12px' }}>
            AI-sourced data is clearly labelled in the "Stored Financial Data" panel so you can see which sections
            came from structured feeds versus the model. Any data retrieved this way is also cached to DynamoDB so
            subsequent analyses for the same ticker avoid the round-trip.
          </p>
          <div style={{ backgroundColor: 'var(--status-warning-bg)', padding: '16px', borderRadius: '8px', borderLeft: '4px solid #f59e0b' }}>
            <p style={{ fontSize: '14px', lineHeight: '1.6', color: 'var(--status-warning-text)', margin: 0 }}>
              <strong>Note:</strong> AI-sourced financials reflect the model's training data and may not match the
              latest reported figures. Where AI data is used, the analysis flags this. For greater accuracy,
              upload the company's PDF annual report to override specific fields with the source data.
            </p>
          </div>
        </div>

        <div style={{ marginBottom: '32px' }}>
          <h3 style={{ fontSize: '22px', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '12px' }}>
            3. Investment Commentary
          </h3>
          <p style={{ fontSize: '16px', lineHeight: '1.7', color: 'var(--text-secondary)', marginBottom: '12px' }}>
            Once the quantitative models have run and a fair value estimate is calculated, Claude generates a
            short plain-language commentary covering three things:
          </p>
          <ul style={{ fontSize: '16px', lineHeight: '1.7', color: 'var(--text-secondary)', paddingLeft: '24px', marginBottom: '12px' }}>
            <li><strong>Price context:</strong> What sector trends, business model characteristics, and recent financial performance explain the current market price</li>
            <li><strong>Valuation opinion:</strong> Whether the stock appears cheap or expensive relative to the model's fair value estimate and margin of safety</li>
            <li><strong>Recommendation with risks:</strong> A clear buy / hold / avoid opinion with one or two key risks the investor should monitor</li>
          </ul>
          <p style={{ fontSize: '16px', lineHeight: '1.7', color: 'var(--text-secondary)' }}>
            The commentary is grounded in the quantitative outputs — the AI is given the fair value, margin of safety,
            key financial ratios, and the selected preset — so its opinion stays consistent with the model's findings
            rather than forming an independent view.
          </p>
        </div>

        <div style={{ marginBottom: '32px' }}>
          <h3 style={{ fontSize: '22px', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '12px' }}>
            4. Independent Confirmation of the Analysis
          </h3>
          <p style={{ fontSize: '16px', lineHeight: '1.7', color: 'var(--text-secondary)', marginBottom: '12px' }}>
            After the quantitative verdict is reached, Claude independently reviews the full analysis — the fair value
            estimate, margin of safety, financial ratios, and business context — and issues its own standalone
            recommendation: <strong>Buy</strong>, <strong>Hold</strong>, or <strong>Avoid</strong>. This is separate from
            the commentary step and is designed to act as a second opinion on the model's conclusion.
          </p>
          <p style={{ fontSize: '16px', lineHeight: '1.7', color: 'var(--text-secondary)', marginBottom: '12px' }}>
            The two verdicts — quantitative model and AI analyst — are then compared:
          </p>
          <ul style={{ fontSize: '16px', lineHeight: '1.7', color: 'var(--text-secondary)', paddingLeft: '24px', marginBottom: '12px' }}>
            <li><strong>Agreement:</strong> The overall recommendation reflects the shared verdict, with higher confidence</li>
            <li><strong>Conflict:</strong> If the model and AI point in opposite directions (e.g. model says Buy, AI says Avoid), the overall recommendation is shown as <strong>AI Conflict</strong> — a deliberate signal to pause and review the commentary carefully before acting</li>
          </ul>
          <div style={{ backgroundColor: 'var(--status-warning-bg)', padding: '16px', borderRadius: '8px', borderLeft: '4px solid #f59e0b' }}>
            <p style={{ fontSize: '14px', lineHeight: '1.6', color: 'var(--status-warning-text)', margin: 0 }}>
              <strong>AI Conflict:</strong> This status does not mean one side is right and the other wrong. It means
              the quantitative and qualitative signals diverge and warrant closer scrutiny — for example, a stock that
              looks cheap on numbers alone but faces a structural business risk the model cannot price in.
            </p>
          </div>
        </div>
      </section>

      {/* Data Sources Section */}
      <section style={{ marginBottom: '60px' }}>
        <h2 style={{ fontSize: '28px', fontWeight: '600', marginBottom: '24px', color: 'var(--text-primary)', borderBottom: '2px solid var(--border-default)', paddingBottom: '8px' }}>
          Data Sources
        </h2>
        <p style={{ fontSize: '16px', lineHeight: '1.7', color: 'var(--text-secondary)', marginBottom: '16px' }}>
          The tool uses multiple data sources to ensure accuracy and reliability:
        </p>
        <ul style={{ fontSize: '16px', lineHeight: '1.7', color: 'var(--text-secondary)', paddingLeft: '24px', marginBottom: '16px' }}>
          <li><strong>Yahoo Finance:</strong> Primary source for stock prices, company info, and financial statements</li>
          <li><strong>Alpha Vantage:</strong> Backup data source and financial statement data</li>
          <li><strong>Financial Modeling Prep:</strong> Additional backup for price and company data</li>
          <li><strong>MarketStack:</strong> Alternative backup data source</li>
          <li><strong>SEC EDGAR:</strong> Official financial filings for verification</li>
        </ul>
        <div style={{ backgroundColor: 'var(--status-warning-bg)', padding: '16px', borderRadius: '8px', borderLeft: '4px solid #f59e0b' }}>
          <p style={{ fontSize: '14px', lineHeight: '1.6', color: 'var(--status-warning-text)', margin: 0 }}>
            <strong>Note:</strong> The tool includes data quality warnings when assumptions are made or data is incomplete.
            Always review these warnings and consider uploading PDF financial statements for custom or private companies.
          </p>
        </div>
      </section>

      {/* Investment Philosophy Section */}
      <section style={{ marginBottom: '60px' }}>
        <h2 style={{ fontSize: '28px', fontWeight: '600', marginBottom: '24px', color: 'var(--text-primary)', borderBottom: '2px solid var(--border-default)', paddingBottom: '8px' }}>
          Investment Philosophy
        </h2>
        <p style={{ fontSize: '16px', lineHeight: '1.7', color: 'var(--text-secondary)', marginBottom: '16px' }}>
          This tool is built on value investing principles, which emphasise:
        </p>
        <ul style={{ fontSize: '16px', lineHeight: '1.7', color: 'var(--text-secondary)', paddingLeft: '24px' }}>
          <li><strong>Intrinsic Value:</strong> Every business has a true worth independent of its market price</li>
          <li><strong>Margin of Safety:</strong> Requiring a significant discount (30–50%) to intrinsic value before buying</li>
          <li><strong>Long-Term Focus:</strong> Investing in quality businesses held over years, not days</li>
          <li><strong>Fundamental Analysis:</strong> Understanding the business before the stock</li>
          <li><strong>Quality First:</strong> Preferring great businesses at fair prices over fair businesses at great prices</li>
        </ul>
      </section>

      {/* Disclaimer */}
      <section style={{ backgroundColor: 'var(--bg-hover)', padding: '24px', borderRadius: '8px', marginTop: '60px' }}>
        <h3 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '12px', color: 'var(--text-primary)' }}>
          Important Disclaimer
        </h3>
        <p style={{ fontSize: '14px', lineHeight: '1.6', color: 'var(--text-muted)', margin: 0 }}>
          This tool is for educational and research purposes only. The analysis and valuations are estimates based on
          available data and should not be considered as investment advice. Always conduct your own research and
          consult with a qualified financial adviser before making investment decisions. Past performance does not
          guarantee future results.
        </p>
      </section>
    </div>
  )
}
