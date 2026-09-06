/**
 * TypeSphere Biometric Heatmap & Real-Time Finger Placement Guide
 * (Inspired by TypingOwl.com's interactive hand biomechanics)
 */
class VirtualKeyboard {
  constructor() {
    this.container = document.getElementById('on-screen-keyboard');
    this.modal = document.getElementById('key-inspect-modal');
    this.fingerGuide = document.getElementById('active-finger-guide');
    this.keyData = {};
    
    this.layout = [
      ["`", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "=", "Backspace"],
      ["Tab", "q", "w", "e", "r", "t", "y", "u", "i", "o", "p", "[", "]", "\\"],
      ["Caps", "a", "s", "d", "f", "g", "h", "j", "k", "l", ";", "'", "Enter"],
      ["Shift", "z", "x", "c", "v", "b", "n", "m", ",", ".", "/", "Shift"],
      ["Space"]
    ];

    this.fingerMapping = {
      'q': 'Left Pinky', 'a': 'Left Pinky', 'z': 'Left Pinky', '1': 'Left Pinky', '`': 'Left Pinky',
      'w': 'Left Ring', 's': 'Left Ring', 'x': 'Left Ring', '2': 'Left Ring',
      'e': 'Left Middle', 'd': 'Left Middle', 'c': 'Left Middle', '3': 'Left Middle',
      'r': 'Left Index', 'f': 'Left Index', 'v': 'Left Index', 't': 'Left Index', 'g': 'Left Index', 'b': 'Left Index', '4': 'Left Index', '5': 'Left Index',
      'y': 'Right Index', 'h': 'Right Index', 'n': 'Right Index', 'u': 'Right Index', 'j': 'Right Index', 'm': 'Right Index', '6': 'Right Index', '7': 'Right Index',
      'i': 'Right Middle', 'k': 'Right Middle', ',': 'Right Middle', '8': 'Right Middle',
      'o': 'Right Ring', 'l': 'Right Ring', '.': 'Right Ring', '9': 'Right Ring',
      'p': 'Right Pinky', ';': 'Right Pinky', '/': 'Right Pinky', '0': 'Right Pinky', '[': 'Right Pinky', ']': 'Right Pinky', '\'': 'Right Pinky', '-': 'Right Pinky', '=': 'Right Pinky',
      ' ': 'Left / Right Thumb', 'Space': 'Left / Right Thumb'
    };

    this.keyElements = {};
    if (this.container) {
      this.render();
      this.fetchHeatmapData();
    }
  }

  render() {
    this.container.innerHTML = '';
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

        keyDiv.className = `k-key ${specialClass}`;
        keyDiv.innerHTML = `<span class="key-label">${key}</span>`;
        keyDiv.dataset.key = lower;

        rowDiv.appendChild(keyDiv);
        this.keyElements[lower] = keyDiv;

        keyDiv.addEventListener('click', () => this.inspectKey(key));
      });
      this.container.appendChild(rowDiv);
    });
  }

  updateCurrentExpectedKey(expectedChar) {
    if (!expectedChar) return;
    const lower = (expectedChar === ' ') ? 'space' : expectedChar.toLowerCase();
    const finger = this.fingerMapping[expectedChar.toLowerCase()] || this.fingerMapping[expectedChar] || 'Touch Key';
    
    if (this.fingerGuide) {
      this.fingerGuide.innerHTML = `Use: <strong>${finger}</strong> &bull; Target: <span style="font-family: var(--font-mono); color: var(--accent); background: var(--bg-card); padding: 0.1rem 0.4rem; border-radius: 4px;">${expectedChar === ' ' ? 'Space' : expectedChar}</span>`;
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
    } catch(e) {
      console.warn("Heatmap query note:", e);
    }
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

  inspectKey(key) {
    const modal = document.getElementById('key-inspect-modal');
    if (!modal) return;

    const lower = key.toLowerCase();
    const data = this.keyData[lower] || { total: 0, errors: 0, delays: [], confusions: {} };
    const finger = this.fingerMapping[key] || this.fingerMapping[lower] || 'Adaptive Hand';
    
    const errRate = data.total > 0 ? Math.round((data.errors / data.total) * 100) : 0;
    const avgDelay = data.delays.length > 0 ? Math.round(data.delays.reduce((a,b)=>a+b,0) / data.delays.length) : 'N/A';

    let topConfusion = 'None detected';
    let maxConf = 0;
    Object.keys(data.confusions).forEach(c => {
      if (data.confusions[c] > maxConf) {
        maxConf = data.confusions[c];
        topConfusion = `'${c.toUpperCase()}' (${maxConf} mistakes)`;
      }
    });

    document.getElementById('km-key-title').textContent = `Key Diagnostics: [ ${key.toUpperCase()} ]`;
    document.getElementById('km-finger').textContent = finger;
    document.getElementById('km-total').textContent = data.total;
    document.getElementById('km-error-rate').textContent = `${errRate}%`;
    document.getElementById('km-delay').textContent = avgDelay === 'N/A' ? 'N/A' : `${avgDelay} ms`;
    document.getElementById('km-confusion').textContent = topConfusion;

    modal.style.display = 'flex';
  }
}

window.virtualKeyboard = new VirtualKeyboard();