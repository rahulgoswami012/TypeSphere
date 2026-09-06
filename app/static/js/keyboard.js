/**
 * TypeSphere Biometric Heatmap & Real-Time Finger Placement Guide
 * Features: Home-Row resting hand guide and instant direct finger placement on click.
 */
class VirtualKeyboard {
  constructor() {
    this.container = document.getElementById('on-screen-keyboard');
    this.fingerGuide = document.getElementById('active-finger-guide');
    this.keyData = {};
    
    this.layout = [
      ["`", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "=", "Backspace"],
      ["Tab", "q", "w", "e", "r", "t", "y", "u", "i", "o", "p", "[", "]", "\\"],
      ["Caps", "a", "s", "d", "f", "g", "h", "j", "k", "l", ";", "'", "Enter"],
      ["Shift", "z", "x", "c", "v", "b", "n", "m", ",", ".", "/", "Shift"],
      ["Space"]
    ];

    // Home-Row Resting Hand Finger Assignments
    this.homeRowKeys = {
      'a': 'L.Pinky', 's': 'L.Ring', 'd': 'L.Middle', 'f': 'L.Index',
      'j': 'R.Index', 'k': 'R.Middle', 'l': 'R.Ring', ';': 'R.Pinky'
    };

    this.fingerMapping = {
      'q': 'Left Pinky', 'a': 'Left Pinky', 'z': 'Left Pinky', '1': 'Left Pinky', '`': 'Left Pinky',
      'w': 'Left Ring', 's': 'Left Ring', 'x': 'Left Ring', '2': 'Left Ring',
      'e': 'Left Middle', 'd': 'Left Middle', 'c': 'Left Middle', '3': 'Left Middle',
      'r': 'Left Index', 'f': 'Left Index', 'v': 'Left Index', 't': 'Left Index', 'g': 'Left Index', 'b': 'Left Index', '4': 'Left Index', '5': 'Left Index',
      'y': 'Right Index', 'h': 'Right Index', 'n': 'Right Index', 'u': 'Right Index', 'j': 'Right Index', 'm': 'Right Index', '6': 'Right Index', '7': 'Right Index',
      'i': 'Right Middle', 'k': 'Right Middle', ',': 'Right Middle', '8': 'Right Middle',
      'o': 'Right Ring', 'l': 'Right Ring', '.': 'Right Ring', '9': 'Right Ring',
      'p': 'Right Pinky', ';': 'Right Pinky', '/': 'Right Pinky', '0': 'Right Pinky', '[': 'Right Pinky', ']': 'Right Pinky', '\'': 'Right Pinky', '-': 'Right Pinky', '=': 'Right Pinky',
      ' ': 'Thumb', 'Space': 'Thumb'
    };

    this.keyElements = {};
    if (this.container) {
      this.render();
      this.fetchHeatmapData();
    }
  }

  render() {
    this.container.innerHTML = '';

    // 1. Home-Row Resting Hand Guide Header
    const legend = document.createElement('div');
    legend.className = 'hand-placement-legend';
    legend.innerHTML = `
      <div class="hand-label">
        <span>Left Hand Resting:</span>
        <span class="hand-badge">A (Pinky)</span>
        <span class="hand-badge">S (Ring)</span>
        <span class="hand-badge">D (Middle)</span>
        <span class="hand-badge">F (Index)</span>
      </div>
      <div class="hand-label">
        <span>Right Hand Resting:</span>
        <span class="hand-badge">J (Index)</span>
        <span class="hand-badge">K (Middle)</span>
        <span class="hand-badge">L (Ring)</span>
        <span class="hand-badge">; (Pinky)</span>
      </div>
    `;
    this.container.appendChild(legend);

    // 2. Keyboard Rows
    this.layout.forEach(row => {
      const rowDiv = document.createElement('div');
      rowDiv.className = 'keyboard-row';
      row.forEach(key => {
        const keyDiv = document.createElement('div');
        const lower = key.toLowerCase();
        
        let specialClass = '';
        if (key === 'Space') specialClass = 'space';
        else if (key === 'Backspace') specialClass = 'backspace';
        else if (key === 'Tab') specialClass = 'tab';
        else if (key === 'Caps') specialClass = 'caps';
        else if (key === 'Enter') specialClass = 'enter';
        else if (key === 'Shift') specialClass = 'shift';

        // Tag Home-Row keys
        let homeTag = '';
        if (this.homeRowKeys[lower]) {
          specialClass += ' home-key';
          homeTag = this.homeRowKeys[lower];
          keyDiv.dataset.fingerTag = homeTag;
        }

        keyDiv.className = `k-key ${specialClass}`;
        keyDiv.innerHTML = `<span class="key-label">${key}</span>`;
        keyDiv.dataset.key = lower;

        rowDiv.appendChild(keyDiv);
        this.keyElements[lower] = keyDiv;

        // Directly update finger guide on click without opening a popup box
        keyDiv.addEventListener('click', () => this.placeFingerOnKey(key));
      });
      this.container.appendChild(rowDiv);
    });
  }

  placeFingerOnKey(key) {
    const lower = (key === ' ' || key === 'Space') ? 'space' : key.toLowerCase();
    const finger = this.fingerMapping[lower] || this.fingerMapping[key] || 'Touch Key';

    // Highlight key visually with a pulse
    const el = this.keyElements[lower];
    if (el) {
      el.classList.add('clicked-active');
      setTimeout(() => el.classList.remove('clicked-active'), 250);
    }

    // Direct Finger Placement: updates guide immediately
    if (this.fingerGuide) {
      this.fingerGuide.innerHTML = `Placed Finger: <strong style="color: var(--success);">${finger}</strong> &rarr; Key: <span style="font-family: var(--font-mono); color: var(--accent); background: var(--bg-card); padding: 0.1rem 0.5rem; border-radius: 4px; font-weight: 700;">${key.toUpperCase()}</span>`;
    }

    if (window.soundEngine) {
      window.soundEngine.playKey(false);
    }
  }

  updateCurrentExpectedKey(expectedChar) {
    if (!expectedChar) return;
    const lower = (expectedChar === ' ') ? 'space' : expectedChar.toLowerCase();
    const finger = this.fingerMapping[expectedChar.toLowerCase()] || this.fingerMapping[expectedChar] || 'Touch Key';
    
    if (this.fingerGuide) {
      this.fingerGuide.innerHTML = `Use Finger: <strong>${finger}</strong> &bull; Target: <span style="font-family: var(--font-mono); color: var(--accent); background: var(--bg-card); padding: 0.1rem 0.4rem; border-radius: 4px;">${expectedChar === ' ' ? 'Space' : expectedChar}</span>`;
    }
  }

  highlightKey(key) {
    const norm = (key === ' ') ? 'space' : key.toLowerCase();
    const el = this.keyElements[norm];
    if (el) {
      el.classList.add('active');
      setTimeout(() => el.classList.remove('active'), 100);
    }
  }

  async fetchHeatmapData() {
    try {
      const stored = localStorage.getItem('typesphere_key_stats');
      if (stored) {
        this.keyData = JSON.parse(stored);
        this.paintHeatmap();
      }
    } catch(e) {}
  }

  recordKeyMetric(expected, typed, isCorrect, latencyMs) {
    const k = expected.toLowerCase();
    if (!this.keyData[k]) {
      this.keyData[k] = { total: 0, errors: 0, delays: [], confusions: {} };
    }
    this.keyData[k].total++;
    if (!isCorrect) {
      this.keyData[k].errors++;
      const t = typed.toLowerCase();
      this.keyData[k].confusions[t] = (this.keyData[k].confusions[t] || 0) + 1;
    }
    if (latencyMs && latencyMs > 0 && latencyMs < 2000) {
      this.keyData[k].delays.push(latencyMs);
      if (this.keyData[k].delays.length > 30) this.keyData[k].delays.shift();
    }
    localStorage.setItem('typesphere_key_stats', JSON.stringify(this.keyData));
    this.paintHeatmap();
  }

  paintHeatmap() {
    Object.keys(this.keyData).forEach(k => {
      const el = this.keyElements[k];
      if (!el) return;
      const data = this.keyData[k];
      if (data.total >= 3) {
        const errRate = data.errors / data.total;
        if (errRate > 0.25) {
          el.style.borderColor = 'var(--danger)';
          el.style.backgroundColor = 'rgba(248, 81, 73, 0.18)';
        } else if (errRate > 0.1) {
          el.style.borderColor = 'var(--warning)';
          el.style.backgroundColor = 'rgba(210, 153, 34, 0.15)';
        } else {
          el.style.borderColor = 'var(--success)';
          el.style.backgroundColor = 'rgba(63, 185, 80, 0.12)';
        }
      }
    });
  }
}

window.virtualKeyboard = new VirtualKeyboard();