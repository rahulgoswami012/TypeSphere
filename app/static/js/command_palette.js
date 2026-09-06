/**
 * TypeSphere Universal Command Palette & Hotkeys Engine
 * Activated globally with Ctrl+K, Cmd+K, or ?
 */
class CommandPalette {
  constructor() {
    this.commands = [
      // Test Modes
      { title: "Start 30s Sprint Benchmark", category: "Test Mode", action: () => window.location.href = '/typing/?mode=timed&duration=30' },
      { title: "Start 60s Official Benchmark", category: "Test Mode", action: () => window.location.href = '/typing/?mode=timed&duration=60' },
      { title: "Start 25 Words Sprint", category: "Test Mode", action: () => window.location.href = '/typing/?mode=words&words=25' },
      { title: "Start 50 Words Sprint", category: "Test Mode", action: () => window.location.href = '/typing/?mode=words&words=50' },
      { title: "Start Python Code Typing", category: "Code Mode", action: () => window.location.href = '/typing/?mode=code&lang=python' },
      { title: "Start JavaScript Code Typing", category: "Code Mode", action: () => window.location.href = '/typing/?mode=code&lang=javascript' },
      { title: "Start SQL Code Typing", category: "Code Mode", action: () => window.location.href = '/typing/?mode=code&lang=sql' },
      { title: "Start Quotes & Literature Mode", category: "Test Mode", action: () => window.location.href = '/typing/?mode=quote' },
      
      // Challenges
      { title: "Daily Challenge (Official 24H)", category: "Challenge", action: () => window.location.href = '/challenges/daily' },
      { title: "Survival Mode (3 Hearts)", category: "Challenge", action: () => window.location.href = '/typing/?mode=survival' },
      { title: "Accuracy Challenge (100% Mandatory)", category: "Challenge", action: () => window.location.href = '/typing/?mode=accuracy' },
      { title: "5-Minute Endurance Marathon", category: "Challenge", action: () => window.location.href = '/typing/?mode=timed&duration=300' },
      { title: "Launch Adaptive Weakness Drill", category: "AI Coach", action: () => window.location.href = '/typing/?mode=adaptive' },

      // Navigation
      { title: "Go to Multiplayer Arena", category: "Navigation", action: () => window.location.href = '/multiplayer/' },
      { title: "Go to Global Leaderboard", category: "Navigation", action: () => window.location.href = '/leaderboard/' },
      { title: "Go to Pilot Dashboard", category: "Navigation", action: () => window.location.href = '/dashboard/' },
      { title: "Go to Typing DNA Telemetry", category: "Navigation", action: () => window.location.href = '/dashboard/dna' },
      { title: "Go to Progression Analytics", category: "Navigation", action: () => window.location.href = '/dashboard/analytics' },
      { title: "Go to Settings & Preferences", category: "Navigation", action: () => window.location.href = '/settings/' },

      // Themes
      { title: "Switch Theme: Dark Matter", category: "Theme", action: () => window.settingsManager.update('theme', 'dark') },
      { title: "Switch Theme: Clean White", category: "Theme", action: () => window.settingsManager.update('theme', 'light') },
      { title: "Switch Theme: Neon Cyberpunk", category: "Theme", action: () => window.settingsManager.update('theme', 'cyber') },
      { title: "Switch Theme: Warm Sepia", category: "Theme", action: () => window.settingsManager.update('theme', 'sepia') }
    ];

    this.selectedIndex = 0;
    this.filteredCommands = [...this.commands];
    this.paletteEl = null;
    this.hotkeyEl = null;

    this.initDOM();
    this.bindEvents();
  }

  initDOM() {
    // 1. Command Palette Overlay
    const overlay = document.createElement('div');
    overlay.id = 'command-palette-overlay';
    overlay.className = 'palette-overlay';
    overlay.innerHTML = `
      <div class="palette-container">
        <div class="palette-search-box">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color: var(--text-muted);">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
          <input type="text" id="palette-input" class="palette-search-input" placeholder="Type a command, mode, or theme (e.g. 'code', 'cyber', 'daily')...">
          <span class="kbd-badge">ESC</span>
        </div>
        <div id="palette-list" class="palette-results"></div>
        <div class="palette-footer">
          <span>Navigation: <span class="kbd-badge">&uarr;</span> <span class="kbd-badge">&darr;</span></span>
          <span>Execute: <span class="kbd-badge">&crarr;</span></span>
        </div>
      </div>
    `;
    document.body.appendChild(overlay);
    this.paletteEl = overlay;

    // 2. Hotkeys Reference Modal
    const hotkeyModal = document.createElement('div');
    hotkeyModal.id = 'hotkey-ref-modal';
    hotkeyModal.className = 'palette-overlay';
    hotkeyModal.innerHTML = `
      <div class="palette-container" style="max-width: 480px;">
        <div style="padding: 1.25rem 1.5rem; border-bottom: 1px solid var(--border-color); display: flex; justify-content: space-between; align-items: center;">
          <h3 style="font-size: 1.15rem; margin: 0; font-weight: 700;">Keyboard Shortcuts</h3>
          <span class="kbd-badge" style="cursor: pointer;" onclick="document.getElementById('hotkey-ref-modal').style.display='none'">ESC</span>
        </div>
        <div style="padding: 1.25rem 1.5rem;">
          <div class="hotkey-row"><span>Quick Restart Test</span> <span class="kbd-badge">Tab</span></div>
          <div class="hotkey-row"><span>Universal Command Palette</span> <span class="kbd-badge">Ctrl + K</span></div>
          <div class="hotkey-row"><span>Distraction-Free Focus Mode</span> <span class="kbd-badge">Esc</span></div>
          <div class="hotkey-row"><span>Keyboard Shortcuts Guide</span> <span class="kbd-badge">?</span></div>
          <div class="hotkey-row"><span>Navigate Commands</span> <span class="kbd-badge">&uarr; / &darr;</span></div>
          <div class="hotkey-row"><span>Execute Selected Command</span> <span class="kbd-badge">Enter</span></div>
        </div>
      </div>
    `;
    document.body.appendChild(hotkeyModal);
    this.hotkeyEl = hotkeyModal;
  }

  bindEvents() {
    window.addEventListener('keydown', (e) => {
      // Ctrl+K or Cmd+K
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        this.openPalette();
        return;
      }

      // '?' for Shortcuts Guide (when not actively typing inside an input)
      if (e.key === '?' && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA') {
        e.preventDefault();
        this.openHotkeys();
        return;
      }

      // Escape to close
      if (e.key === 'Escape') {
        this.closeAll();
        return;
      }

      // Palette Navigation
      if (this.paletteEl.style.display === 'flex') {
        if (e.key === 'ArrowDown') {
          e.preventDefault();
          this.selectedIndex = (this.selectedIndex + 1) % this.filteredCommands.length;
          this.renderList();
        } else if (e.key === 'ArrowUp') {
          e.preventDefault();
          this.selectedIndex = (this.selectedIndex - 1 + this.filteredCommands.length) % this.filteredCommands.length;
          this.renderList();
        } else if (e.key === 'Enter') {
          e.preventDefault();
          this.executeSelected();
        }
      }
    });

    // Close on backdrop click
    this.paletteEl.addEventListener('click', (e) => {
      if (e.target === this.paletteEl) this.closeAll();
    });
    this.hotkeyEl.addEventListener('click', (e) => {
      if (e.target === this.hotkeyEl) this.closeAll();
    });

    // Search filter input
    const input = document.getElementById('palette-input');
    input.addEventListener('input', (e) => {
      const q = e.target.value.toLowerCase().trim();
      this.filteredCommands = this.commands.filter(c =>
        c.title.toLowerCase().includes(q) || c.category.toLowerCase().includes(q)
      );
      this.selectedIndex = 0;
      this.renderList();
    });
  }

  openPalette() {
    this.paletteEl.style.display = 'flex';
    this.filteredCommands = [...this.commands];
    this.selectedIndex = 0;
    this.renderList();
    const input = document.getElementById('palette-input');
    input.value = '';
    setTimeout(() => input.focus(), 50);
  }

  openHotkeys() {
    this.hotkeyEl.style.display = 'flex';
  }

  closeAll() {
    this.paletteEl.style.display = 'none';
    this.hotkeyEl.style.display = 'none';
  }

  renderList() {
    const list = document.getElementById('palette-list');
    list.innerHTML = '';

    if (this.filteredCommands.length === 0) {
      list.innerHTML = '<div style="padding: 1.5rem; text-align: center; color: var(--text-muted);">No matching commands found.</div>';
      return;
    }

    this.filteredCommands.forEach((cmd, idx) => {
      const item = document.createElement('div');
      item.className = `palette-item ${idx === this.selectedIndex ? 'selected' : ''}`;
      item.innerHTML = `
        <span>${cmd.title}</span>
        <span class="palette-item-category">${cmd.category}</span>
      `;
      item.addEventListener('click', () => {
        cmd.action();
        this.closeAll();
      });
      list.appendChild(item);
    });

    const activeItem = list.children[this.selectedIndex];
    if (activeItem) activeItem.scrollIntoView({ block: 'nearest' });
  }

  executeSelected() {
    if (this.filteredCommands[this.selectedIndex]) {
      this.filteredCommands[this.selectedIndex].action();
      this.closeAll();
    }
  }
}

window.commandPalette = new CommandPalette();