/**
 * TypeSphere Biometric Heatmap & Vector Hands Visualizer
 * (Matches Screenshot 1 Hand Placements on A S D F & J K L ;)
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

    this.homeKeys = new Set(['a', 's', 'd', 'f', 'j', 'k', 'l', ';', 'space']);

    this.fingerMapping = {
      'q': 'lp', 'a': 'lp', 'z': 'lp', '1': 'lp', '`': 'lp',
      'w': 'lr', 's': 'lr', 'x': 'lr', '2': 'lr',
      'e': 'lm', 'd': 'lm', 'c': 'lm', '3': 'lm',
      'r': 'li', 'f': 'li', 'v': 'li', 't': 'li', 'g': 'li', 'b': 'li', '4': 'li', '5': 'li',
      'y': 'ri', 'h': 'ri', 'n': 'ri', 'u': 'ri', 'j': 'ri', 'm': 'ri', '6': 'ri', '7': 'ri',
      'i': 'rm', 'k': 'rm', ',': 'rm', '8': 'rm',
      'o': 'rr', 'l': 'rr', '.': 'rr', '9': 'rr',
      'p': 'rp', ';': 'rp', '/': 'rp', '0': 'rp', '[': 'rp', ']': 'rp', '\'': 'rp', '-': 'rp', '=': 'rp',
      ' ': 'thumb', 'space': 'thumb'
    };

    this.fingerNames = {
      'lp': 'Left Pinky', 'lr': 'Left Ring', 'lm': 'Left Middle', 'li': 'Left Index',
      'ri': 'Right Index', 'rm': 'Right Middle', 'rr': 'Right Ring', 'rp': 'Right Pinky',
      'thumb': 'Left / Right Thumb'
    };

    this.keyElements = {};
    if (this.container) {
      this.render();
      this.fetchHeatmapData();
    }
  }

  render() {
    this.container.innerHTML = '';

    // 1. Keyboard Rows
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

        if (this.homeKeys.has(lower)) {
          specialClass += ' home-pos';
        }

        keyDiv.className = `k-key ${specialClass}`;
        keyDiv.innerHTML = `<span class="key-label">${key}</span>`;
        keyDiv.dataset.key = lower;

        rowDiv.appendChild(keyDiv);
        this.keyElements[lower] = keyDiv;

        keyDiv.addEventListener('click', () => this.placeFingerOnKey(key));
      });
      this.container.appendChild(rowDiv);
    });

    // 2. Real Hands Illustration Overlay (Screenshot 1)
    const handsWrap = document.createElement('div');
    handsWrap.className = 'hands-visual-container';
    handsWrap.innerHTML = `
      <!-- Left Hand -->
      <svg class="hand-svg" viewBox="0 0 250 180">
        <path d="M 60 170 C 50 120, 50 90, 45 60 C 43 45, 58 45, 60 60 C 62 75, 65 110, 68 85 C 70 50, 85 50, 88 80 C 90 95, 93 115, 98 75 C 100 45, 115 45, 118 75 C 120 100, 125 125, 130 90 C 132 70, 145 70, 148 95 C 150 125, 160 145, 185 130 C 195 125, 205 135, 195 145 C 170 170, 140 180, 60 170 Z" fill="#ffd1a4" stroke="#d49b6a" stroke-width="3"/>
        <circle id="fing-lp" class="finger-tip" cx="52" cy="52" r="10" fill="#ffd1a4" stroke="#d49b6a" stroke-width="2"/>
        <circle id="fing-lr" class="finger-tip" cx="76" cy="50" r="10" fill="#ffd1a4" stroke="#d49b6a" stroke-width="2"/>
        <circle id="fing-lm" class="finger-tip" cx="106" cy="48" r="10" fill="#ffd1a4" stroke="#d49b6a" stroke-width="2"/>
        <circle id="fing-li" class="finger-tip" cx="138" cy="72" r="10" fill="#ffd1a4" stroke="#d49b6a" stroke-width="2"/>
        <circle id="fing-lthumb" class="finger-tip" cx="195" cy="130" r="11" fill="#ffd1a4" stroke="#d49b6a" stroke-width="2"/>
      </svg>

      <!-- Right Hand -->
      <svg class="hand-svg" viewBox="0 0 250 180">
        <path d="M 190 170 C 200 120, 200 90, 205 60 C 207 45, 192 45, 190 60 C 188 75, 185 110, 182 85 C 180 50, 165 50, 162 80 C 160 95, 157 115, 152 75 C 150 45, 135 45, 132 75 C 130 100, 125 125, 120 90 C 118 70, 105 70, 102 95 C 100 125, 90 145, 65 130 C 55 125, 45 135, 55 145 C 80 170, 110 180, 190 170 Z" fill="#ffd1a4" stroke="#d49b6a" stroke-width="3"/>
        <circle id="fing-rp" class="finger-tip" cx="198" cy="52" r="10" fill="#ffd1a4" stroke="#d49b6a" stroke-width="2"/>
        <circle id="fing-rr" class="finger-tip" cx="174" cy="50" r="10" fill="#ffd1a4" stroke="#d49b6a" stroke-width="2"/>
        <circle id="fing-rm" class="finger-tip" cx="144" cy="48" r="10" fill="#ffd1a4" stroke="#d49b6a" stroke-width="2"/>
        <circle id="fing-ri" class="finger-tip" cx="112" cy="72" r="10" fill="#ffd1a4" stroke="#d49b6a" stroke-width="2"/>
        <circle id="fing-rthumb" class="finger-tip" cx="55" cy="130" r="11" fill="#ffd1a4" stroke="#d49b6a" stroke-width="2"/>
      </svg>
    `;
    this.container.appendChild(handsWrap);
  }

  placeFingerOnKey(key) {
    const lower = (key === ' ' || key === 'Space') ? 'space' : key.toLowerCase();
    const fingerCode = this.fingerMapping[lower] || 'thumb';
    const fingerName = this.fingerNames[fingerCode] || 'Touch Key';

    const el = this.keyElements[lower];
    if (el) {
      el.classList.add('clicked-active');
      setTimeout(() => el.classList.remove('clicked-active'), 250);
    }

    this.highlightFingerOnHand(fingerCode);

    if (this.fingerGuide) {
      this.fingerGuide.innerHTML = `Placed Finger: <strong style="color: #5b92e5;">${fingerName}</strong> &rarr; Key: <span style="font-family: var(--font-mono); color: #f59e0b; background: var(--bg-card); padding: 0.15rem 0.5rem; border-radius: 4px; font-weight: 800;">${key.toUpperCase()}</span>`;
    }

    if (window.soundEngine) {
      window.soundEngine.playKey(false);
    }
  }

  highlightFingerOnHand(fingerCode) {
    document.querySelectorAll('.finger-tip').forEach(f => f.classList.remove('active-finger'));
    if (fingerCode === 'thumb') {
      const lt = document.getElementById('fing-lthumb');
      const rt = document.getElementById('fing-rthumb');
      if (lt) lt.classList.add('active-finger');
      if (rt) rt.classList.add('active-finger');
    } else {
      const tip = document.getElementById(`fing-${fingerCode}`);
      if (tip) tip.classList.add('active-finger');
    }
  }

  updateCurrentExpectedKey(expectedChar) {
    if (!expectedChar) return;
    const lower = (expectedChar === ' ') ? 'space' : expectedChar.toLowerCase();
    const fingerCode = this.fingerMapping[lower] || 'thumb';
    const fingerName = this.fingerNames[fingerCode] || 'Touch Key';

    this.highlightFingerOnHand(fingerCode);

    if (this.fingerGuide) {
      this.fingerGuide.innerHTML = `Use Finger: <strong style="color: #5b92e5;">${fingerName}</strong> &bull; Target: <span style="font-family: var(--font-mono); color: #f59e0b; background: var(--bg-card); padding: 0.1rem 0.45rem; border-radius: 4px; font-weight: 800;">${expectedChar === ' ' ? 'Space' : expectedChar}</span>`;
    }
  }

  highlightKey(key) {
    const norm = (key === ' ') ? 'space' : key.toLowerCase();
    const el = this.keyElements[norm];
    if (el) {
      el.classList.add('active');
      setTimeout(() => el.classList.remove('active'), 100);
    }
    const fingerCode = this.fingerMapping[norm] || 'thumb';
    this.highlightFingerOnHand(fingerCode);
  }

  async fetchHeatmapData() {
    try {
      const stored = localStorage.getItem('typesphere_key_stats');
      if (stored) {
        this.keyData = JSON.parse(stored);
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
    }
    localStorage.setItem('typesphere_key_stats', JSON.stringify(this.keyData));
  }
}

window.virtualKeyboard = new VirtualKeyboard();