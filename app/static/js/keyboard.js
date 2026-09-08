/**
 * TypeSphere Biometric Heatmap & Key Diagnostics Telemetry Inspector
 */
const SYMBOL_TO_PHYSICAL_KEY = {
    '!': '1', '@': '2', '#': '3', '$': '4', '%': '5', '^': '6', '&': '7', '*': '8', '(': '9', ')': '0',
    '_': '-', '+': '=', '{': '[', '}': ']', '|': '\\', ':': ';', '"': "'", '<': ',', '>': '.', '?': '/', '~': '`'
};

class VirtualKeyboard {
    constructor() {
        this.container = document.getElementById('on-screen-keyboard');
        this.fingerGuide = document.getElementById('active-finger-guide');
        this.keyData = {};
        this.keyElements = {};
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
            ' ': 'Thumb Anchor', 'space': 'Thumb Anchor'
        };

        if (this.container) {
            this.render();
            this.fetchHeatmapData();
        }
    }

    render() {
        this.container.innerHTML = '';
        this.keyElements = {};
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

                if (!this.keyElements[lower]) {
                    this.keyElements[lower] = keyDiv;
                }
                keyDiv.addEventListener('click', () => this.inspectKey(key));
            });
            this.container.appendChild(rowDiv);
        });
        this.paintHeatmap();
    }

    inspectKey(key) {
        const modal = document.getElementById('key-inspect-modal');
        if (!modal) return;

        const lower = key.toLowerCase();
        const data = this.keyData[lower] || { total: 0, errors: 0, delays: [], confusions: {} };
        const finger = this.fingerMapping[lower] || 'Touch Key';
        const errRate = data.total > 0 ? Math.round((data.errors / data.total) * 100) : 0;
        const avgDelay = data.delays && data.delays.length > 0 ? Math.round(data.delays.reduce((a, b) => a + b, 0) / data.delays.length) : 'N/A';

        let topConfusion = 'None detected';
        let maxConf = 0;
        if (data.confusions) {
            Object.keys(data.confusions).forEach(c => {
                if (data.confusions[c] > maxConf) {
                    maxConf = data.confusions[c];
                    topConfusion = `'${c.toUpperCase()}' (${maxConf} mistakes)`;
                }
            });
        }

        document.getElementById('km-key-title').textContent = `Key Diagnostics: [ ${key.toUpperCase()} ]`;
        document.getElementById('km-finger').textContent = finger;
        document.getElementById('km-total').textContent = data.total;
        document.getElementById('km-error-rate').textContent = `${errRate}%`;
        document.getElementById('km-delay').textContent = avgDelay === 'N/A' ? 'N/A' : `${avgDelay} ms`;
        document.getElementById('km-confusion').textContent = topConfusion;
        modal.style.display = 'flex';
    }

    updateCurrentExpectedKey(expectedChar) {
        if (!expectedChar || !this.fingerGuide) return;
        const baseKey = SYMBOL_TO_PHYSICAL_KEY[expectedChar] || expectedChar.toLowerCase();
        const finger = this.fingerMapping[baseKey] || 'Touch Key';
        const displayLabel = expectedChar === ' ' ? 'Space' : expectedChar;
        this.fingerGuide.innerHTML = `Next Finger: <strong style="color:var(--accent);">${finger}</strong> &bull; Target: <span style="font-family:var(--font-mono); color:#f59e0b; background:var(--bg-card); padding:0.1rem 0.45rem; border-radius:4px; font-weight:800;">${displayLabel}</span>`;
    }

    highlightKey(key) {
        if (!key) return;
        let norm = (key === ' ') ? 'space' : key.toLowerCase();
        norm = SYMBOL_TO_PHYSICAL_KEY[norm] || norm;
        const el = this.keyElements[norm];
        if (el) {
            el.classList.add('active');
            setTimeout(() => el.classList.remove('active'), 110);
        }
    }

    async fetchHeatmapData() {
        try {
            const stored = localStorage.getItem('typesphere_key_stats');
            if (stored) {
                this.keyData = JSON.parse(stored);
                this.paintHeatmap();
            }
        } catch (e) {}
    }

    recordKeyMetric(expected, typed, isCorrect, latencyMs) {
        if (!expected) return;
        let k = expected.toLowerCase();
        k = SYMBOL_TO_PHYSICAL_KEY[k] || k;

        if (!this.keyData[k]) {
            this.keyData[k] = { total: 0, errors: 0, delays: [], confusions: {} };
        }
        this.keyData[k].total++;
        if (!isCorrect) {
            this.keyData[k].errors++;
            this.keyData[k].confusions[typed] = (this.keyData[k].confusions[typed] || 0) + 1;
        }
        if (latencyMs && latencyMs > 0 && latencyMs < 2000) {
            this.keyData[k].delays.push(latencyMs);
            if (this.keyData[k].delays.length > 35) this.keyData[k].delays.shift();
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
                if (errRate > 0.22) {
                    el.style.borderColor = 'var(--danger)';
                    el.style.backgroundColor = 'rgba(244, 63, 94, 0.22)';
                } else if (errRate > 0.08) {
                    el.style.borderColor = 'var(--warning)';
                    el.style.backgroundColor = 'rgba(245, 158, 11, 0.18)';
                } else {
                    el.style.borderColor = 'var(--success)';
                    el.style.backgroundColor = 'rgba(16, 185, 129, 0.14)';
                }
            }
        });
    }
}

window.virtualKeyboard = new VirtualKeyboard();