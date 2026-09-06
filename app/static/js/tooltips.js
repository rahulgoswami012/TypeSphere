/**
 * TypeSphere Real-Time Predictive Tooltip Engine
 * Dynamically computes screen bounds and displays actionable button telemetry on hover.
 */
class TooltipEngine {
  constructor() {
    this.tooltipEl = null;
    this.activeTarget = null;
    this.initDOM();
    this.bindEvents();
  }

  initDOM() {
    let el = document.getElementById('typesphere-tooltip');
    if (!el) {
      el = document.createElement('div');
      el.id = 'typesphere-tooltip';
      document.body.appendChild(el);
    }
    this.tooltipEl = el;
  }

  bindEvents() {
    // Event delegation on mouseover
    document.addEventListener('mouseover', (e) => {
      const target = e.target.closest('[data-tooltip]');
      if (target) {
        this.showTooltip(target);
      }
    }, true);

    document.addEventListener('mouseout', (e) => {
      const target = e.target.closest('[data-tooltip]');
      if (target && target === this.activeTarget) {
        this.hideTooltip();
      }
    }, true);

    document.addEventListener('click', () => {
      this.hideTooltip();
    });

    window.addEventListener('scroll', () => this.hideTooltip(), { passive: true });
  }

  showTooltip(target) {
    this.activeTarget = target;
    const rawContent = target.getAttribute('data-tooltip');
    if (!rawContent) return;

    let title = target.getAttribute('data-tooltip-title') || 'ACTION OUTCOME';
    let body = rawContent;

    this.tooltipEl.innerHTML = `
      <div class="tooltip-header">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="12" y1="16" x2="12" y2="12"></line>
          <line x1="12" y1="8" x2="12.01" y2="8"></line>
        </svg>
        ${title}
      </div>
      <div class="tooltip-body">${body}</div>
    `;

    const rect = target.getBoundingClientRect();
    const tooltipRect = this.tooltipEl.getBoundingClientRect();

    // Position above by default; flip below if near top of screen
    let top = rect.top - 58;
    let left = rect.left + (rect.width / 2) - 80;

    if (top < 10) {
      top = rect.bottom + 10;
    }
    if (left < 10) {
      left = 10;
    }
    if (left + 280 > window.innerWidth) {
      left = window.innerWidth - 290;
    }

    this.tooltipEl.style.top = `${top}px`;
    this.tooltipEl.style.left = `${left}px`;
    this.tooltipEl.classList.add('visible');
  }

  hideTooltip() {
    this.activeTarget = null;
    if (this.tooltipEl) {
      this.tooltipEl.classList.remove('visible');
    }
  }
}

window.tooltipEngine = new TooltipEngine();