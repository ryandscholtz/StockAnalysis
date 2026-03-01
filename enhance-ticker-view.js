// Script to enhance the ticker view with key metrics
const fs = require('fs');

const appJsPath = 'frontend/dist/app.js';
let content = fs.readFileSync(appJsPath, 'utf8');

// Find the line where we need to insert the key metrics section
const insertMarker = '        <!-- Analysis Results -->';
const insertPosition = content.indexOf(insertMarker);

if (insertPosition === -1) {
    console.error('Could not find insertion point');
    process.exit(1);
}

// The new key metrics section to insert
const keyMetricsSection = `
        <!-- Key Metrics Overview (Always Visible) -->
        \${this.renderKeyMetricsOverview(analysis, quote, watchlistItem)}

        `;

// Insert the new section
content = content.slice(0, insertPosition) + keyMetricsSection + content.slice(insertPosition);

// Now add the renderKeyMetricsOverview function after renderTickerData
const functionInsertMarker = '  renderAnalysisResults(analysis) {';
const functionInsertPosition = content.indexOf(functionInsertMarker);

if (functionInsertPosition === -1) {
    console.error('Could not find function insertion point');
    process.exit(1);
}

const newFunction = `
  renderKeyMetricsOverview(analysis, quote, watchlistItem) {
    // Show key metrics prominently, whether from analysis or quote data
    const hasMetrics = analysis || quote;
    if (!hasMetrics) return '';

    return \`
      <div class="key-metrics-overview card">
        <h2 class="card-title">📊 Key Metrics</h2>
        <div class="metrics-grid">
          \${quote?.currentPrice ? \`
            <div class="metric-item">
              <div class="metric-label">Current Price</div>
              <div class="metric-value">\${quote.currentPrice.toFixed(2)}</div>
              <div class="metric-unit">\${analysis?.currency || 'USD'}</div>
            </div>
          \` : ''}
          
          \${analysis?.priceRatios?.pe ? \`
            <div class="metric-item">
              <div class="metric-label">P/E Ratio</div>
              <div class="metric-value \${analysis.priceRatios.pe < 20 ? 'good' : analysis.priceRatios.pe < 30 ? 'moderate' : 'poor'}">
                \${analysis.priceRatios.pe.toFixed(2)}
              </div>
              <div class="metric-unit">\${analysis.priceRatios.pe < 20 ? 'Attractive' : analysis.priceRatios.pe < 30 ? 'Fair' : 'High'}</div>
            </div>
          \` : ''}
          
          \${analysis?.priceRatios?.pb ? \`
            <div class="metric-item">
              <div class="metric-label">P/B Ratio</div>
              <div class="metric-value \${analysis.priceRatios.pb < 2 ? 'good' : analysis.priceRatios.pb < 4 ? 'moderate' : 'poor'}">
                \${analysis.priceRatios.pb.toFixed(2)}
              </div>
              <div class="metric-unit">\${analysis.priceRatios.pb < 2 ? 'Undervalued' : analysis.priceRatios.pb < 4 ? 'Fair' : 'Overvalued'}</div>
            </div>
          \` : ''}
          
          \${analysis?.marketCap ? \`
            <div class="metric-item">
              <div class="metric-label">Market Cap</div>
              <div class="metric-value">\${this.formatMarketCap(analysis.marketCap)}</div>
              <div class="metric-unit">\${analysis.currency || 'USD'}</div>
            </div>
          \` : ''}
          
          \${analysis?.financialHealth?.roe ? \`
            <div class="metric-item">
              <div class="metric-label">Return on Equity</div>
              <div class="metric-value \${analysis.financialHealth.roe > 0.15 ? 'good' : analysis.financialHealth.roe > 0.10 ? 'moderate' : 'poor'}">
                \${(analysis.financialHealth.roe * 100).toFixed(1)}%
              </div>
              <div class="metric-unit">\${analysis.financialHealth.roe > 0.15 ? 'Excellent' : analysis.financialHealth.roe > 0.10 ? 'Good' : 'Weak'}</div>
            </div>
          \` : ''}
          
          \${analysis?.financialHealth?.debtToEquity !== undefined ? \`
            <div class="metric-item">
              <div class="metric-label">Debt-to-Equity</div>
              <div class="metric-value \${analysis.financialHealth.debtToEquity < 0.5 ? 'good' : analysis.financialHealth.debtToEquity < 1.0 ? 'moderate' : 'poor'}">
                \${analysis.financialHealth.debtToEquity.toFixed(2)}
              </div>
              <div class="metric-unit">\${analysis.financialHealth.debtToEquity < 0.5 ? 'Low Risk' : analysis.financialHealth.debtToEquity < 1.0 ? 'Moderate' : 'High Risk'}</div>
            </div>
          \` : ''}
          
          \${analysis?.growthMetrics?.revenueGrowth !== undefined ? \`
            <div class="metric-item">
              <div class="metric-label">Revenue Growth</div>
              <div class="metric-value \${analysis.growthMetrics.revenueGrowth > 0.1 ? 'good' : analysis.growthMetrics.revenueGrowth > 0.05 ? 'moderate' : 'poor'}">
                \${(analysis.growthMetrics.revenueGrowth * 100).toFixed(1)}%
              </div>
              <div class="metric-unit">\${analysis.growthMetrics.revenueGrowth > 0.1 ? 'Strong' : analysis.growthMetrics.revenueGrowth > 0.05 ? 'Moderate' : 'Weak'}</div>
            </div>
          \` : ''}
          
          \${analysis?.growthMetrics?.earningsGrowth !== undefined ? \`
            <div class="metric-item">
              <div class="metric-label">Earnings Growth</div>
              <div class="metric-value \${analysis.growthMetrics.earningsGrowth > 0.15 ? 'good' : analysis.growthMetrics.earningsGrowth > 0.10 ? 'moderate' : 'poor'}">
                \${(analysis.growthMetrics.earningsGrowth * 100).toFixed(1)}%
              </div>
              <div class="metric-unit">\${analysis.growthMetrics.earningsGrowth > 0.15 ? 'Excellent' : analysis.growthMetrics.earningsGrowth > 0.10 ? 'Good' : 'Weak'}</div>
            </div>
          \` : ''}
          
          \${analysis?.fairValue ? \`
            <div class="metric-item highlight">
              <div class="metric-label">Fair Value</div>
              <div class="metric-value large">\${analysis.fairValue.toFixed(2)}</div>
              <div class="metric-unit">\${analysis.currency || 'USD'}</div>
            </div>
          \` : ''}
          
          \${analysis?.marginOfSafety !== undefined ? \`
            <div class="metric-item highlight">
              <div class="metric-label">Margin of Safety</div>
              <div class="metric-value large \${analysis.marginOfSafety > 0 ? 'positive' : 'negative'}">
                \${(analysis.marginOfSafety * 100).toFixed(1)}%
              </div>
              <div class="metric-unit">\${analysis.marginOfSafety > 0.2 ? 'Strong Buy' : analysis.marginOfSafety > 0 ? 'Buy' : 'Overvalued'}</div>
            </div>
          \` : ''}
        </div>
      </div>
    \`;
  }

  formatMarketCap(value) {
    if (value >= 1e12) return \`$\${(value / 1e12).toFixed(2)}T\`;
    if (value >= 1e9) return \`$\${(value / 1e9).toFixed(2)}B\`;
    if (value >= 1e6) return \`$\${(value / 1e6).toFixed(2)}M\`;
    return \`$\${value.toFixed(0)}\`;
  }

  `;

// Insert the new functions
content = content.slice(0, functionInsertPosition) + newFunction + content.slice(functionInsertPosition);

// Write the updated content
fs.writeFileSync(appJsPath, content, 'utf8');

console.log('✓ Enhanced ticker view with key metrics section');
console.log('✓ Added renderKeyMetricsOverview function');
console.log('✓ Added formatMarketCap helper function');
