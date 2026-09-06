/**
 * Pure SVG Charting Engine (Zero external dependencies).
 * Produces smooth responsive WPM timeline and Accuracy visualizations.
 */
class SvgLineChart {
  static render(containerId, dataPoints, strokeColor = '#58a6ff') {
    const container = document.getElementById(containerId);
    if (!container || !dataPoints || dataPoints.length < 2) return;

    const width = container.clientWidth || 800;
    const height = 240;
    const padding = 35;

    const maxWpm = Math.max(...dataPoints.map(d => d.wpm), 60);
    const minWpm = 0;

    const getX = (index) => padding + (index / (dataPoints.length - 1)) * (width - 2 * padding);
    const getY = (val) => height - padding - ((val - minWpm) / (maxWpm - minWpm)) * (height - 2 * padding);

    let dStr = `M ${getX(0)} ${getY(dataPoints[0].wpm)}`;
    for (let i = 1; i < dataPoints.length; i++) {
      dStr += ` L ${getX(i)} ${getY(dataPoints[i].wpm)}`;
    }

    const svg = `
      <svg width="100%" height="${height}" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">
        <line x1="${padding}" y1="${height - padding}" x2="${width - padding}" y2="${height - padding}" stroke="#30363d" stroke-width="1"/>
        <line x1="${padding}" y1="${padding}" x2="${padding}" y2="${height - padding}" stroke="#30363d" stroke-width="1"/>
        <path d="${dStr}" fill="none" stroke="${strokeColor}" stroke-width="2.5" stroke-linecap="round"/>
        ${dataPoints.map((d, i) => `
          <circle cx="${getX(i)}" cy="${getY(d.wpm)}" r="3" fill="${strokeColor}"/>
        `).join('')}
      </svg>
    `;
    container.innerHTML = svg;
  }
}
window.SvgLineChart = SvgLineChart;