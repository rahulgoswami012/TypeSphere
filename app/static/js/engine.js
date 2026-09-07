/**
 * TypeSphere Core Engine (v2.3 Evolution)
 * - Infinite text streaming: tests never terminate because text ran out
 * - No Time Limit mode support
 * - Blind Mode: ON by default
 * - Ghost Mode: OFF by default
 * - Keyboard visible by default
 */
class TypingEngine {
  constructor() {
    this.targetText = "";
    this.currentIndex = 0;
    this.events = [];
    this.timeline = [];

    this.startTime = null;
    this.timerInterval = null;
    
    // Default Test Parameters
    this.durationLimit = 60; // 15s to 1200s, or 0 (No Time Limit)
    this.contentType = 'speed'; // speed, practice, full_passage, quote, story, article, numbers, numbers_text, punctuation, data_entry, professional, coding, custom
    this.level = 'moderate'; // easy, moderate, hard, expert
    this.codeLanguage = 'python';

    // Defaults: Blind Mode ON, Ghost Mode OFF
    this.blindModeActive = true;
    this.ghostEnabled = false;
    this.ghostWpm = 70;
    this.ghostProgress = 0;
    this.ghostInterval = null;

    this.isFinished = false;
    this.isPaused = false;
    this.pausedAt = 0;
    this.totalPausedDuration = 0;
    this.streak = 0;
    this.errors = 0;

    // DOM Caches
    this.container = document.getElementById('typing-box');
    this.display = document.getElementById('text-display');
    this.caret = document.getElementById('caret');
    this.ghostCaret = document.getElementById('ghost-caret');
    this.hudWpm = document.getElementById('hud-wpm');
    this.hudAcc = document.getElementById('hud-acc');
    this.hudTime = document.getElementById('hud-time');
    this.hudErrors = document.getElementById('hud-errors');
    this.speedometerArc = document.getElementById('speedo-arc');
    this.pauseModal = document.getElementById('pause-modal');
    this.mobileProxy = document.getElementById('mobile-text-proxy');
    this.keyboardContainer = document.getElementById('keyboard-container');

    // Guarantee keyboard visibility on startup
    if (this.keyboardContainer) {
      this.keyboardContainer.style.display = 'flex';
    }

    this.bindEvents();
    this.loadUserSessionPreferences();
  }

  loadUserSessionPreferences() {
    const prefs = window.settingsManager ? window.settingsManager.current : null;
    if (prefs) {
      if (prefs.default_duration !== undefined) this.durationLimit = prefs.default_duration;
      if (prefs.default_content) this.contentType = prefs.default_content;
      if (prefs.default_level) this.level = prefs.default_level;
      if (prefs.blind_mode !== undefined) this.blindModeActive = prefs.blind_mode;
      if (prefs.ghost_mode !== undefined) this.ghostEnabled = prefs.ghost_mode;
    }
    this.updateControlsUI();
  }

  updateControlsUI() {
    const typeSelect = document.getElementById('cfg-type-select');
    const timeSelect = document.getElementById('cfg-time-select');
    const diffSelect = document.getElementById('cfg-diff-select');
    const btnBlind = document.getElementById('btn-blind');
    const btnGhost = document.getElementById('btn-ghost');

    if (typeSelect) typeSelect.value = this.contentType;
    if (timeSelect) timeSelect.value = this.durationLimit.toString();
    if (diffSelect) diffSelect.value = this.level;

    if (btnBlind) {
      btnBlind.textContent = `Blind: ${this.blindModeActive ? 'ON' : 'OFF'}`;
      btnBlind.classList.toggle('active-choice', this.blindModeActive);
    }
    if (btnGhost) {
      btnGhost.textContent = `Ghost: ${this.ghostEnabled ? 'ON' : 'OFF'}`;
      btnGhost.classList.toggle('active-choice', this.ghostEnabled);
    }
  }

  async loadPrompt(append = false) {
    if (this.contentType === 'custom') {
      const stored = sessionStorage.getItem('typesphere_custom_text');
      if (stored && stored.trim().length > 0) {
        if (append) {
          this.targetText += " " + stored.trim();
        } else {
          this.targetText = stored.trim();
        }
        this.renderText(append);
        if (!append) this.reset();
        return;
      }
    }

    try {
      const url = `/typing/api/text?test_type=${encodeURIComponent(this.contentType)}&level=${encodeURIComponent(this.level)}&code_lang=${encodeURIComponent(this.codeLanguage)}`;
      const res = await fetch(url);
      const data = await res.json();
      const newChunk = (data.content || "").trim();

      if (append) {
        this.targetText += " " + newChunk;
        this.renderText(true);
      } else {
        this.targetText = newChunk;
        this.renderText(false);
        this.reset();
      }
    } catch {
      const fallback = "Speed and precision compound into true keyboard mastery. Consistent cadence and deliberate finger movement build enduring velocity.";
      if (append) {
        this.targetText += " " + fallback;
        this.renderText(true);
      } else {
        this.targetText = fallback;
        this.renderText(false);
        this.reset();
      }
    }
  }

  renderText(isAppend = false) {
    if (!isAppend) {
      this.display.innerHTML = '';
      const fragment = document.createDocumentFragment();
      for (let i = 0; i < this.targetText.length; i++) {
        const span = document.createElement('span');
        span.className = 'char';
        span.textContent = this.targetText[i];
        fragment.appendChild(span);
      }
      this.display.appendChild(fragment);
      this.updateCaretPosition();
    } else {
      const currentSpanCount = this.display.children.length;
      const fragment = document.createDocumentFragment();
      for (let i = currentSpanCount; i < this.targetText.length; i++) {
        const span = document.createElement('span');
        span.className = 'char';
        span.textContent = this.targetText[i];
        fragment.appendChild(span);
      }
      this.display.appendChild(fragment);
    }
  }

  reset() {
    clearInterval(this.timerInterval);
    clearInterval(this.ghostInterval);
    this.currentIndex = 0;
    this.events = [];
    this.timeline = [];
    this.startTime = null;
    this.isFinished = false;
    this.isPaused = false;
    this.pausedAt = 0;
    this.totalPausedDuration = 0;
    this.streak = 0;
    this.errors = 0;
    this.ghostProgress = 0;

    if (this.pauseModal) this.pauseModal.style.display = 'none';
    if (this.display) this.display.style.filter = 'none';

    this.hudWpm.textContent = '0';
    this.hudAcc.textContent = '100%';
    this.hudErrors.textContent = '0';
    this.updateSpeedometer(0);

    if (this.durationLimit > 0) {
      this.hudTime.textContent = this.formatTimeDisplay(this.durationLimit);
    } else {
      this.hudTime.textContent = '0s (No Limit)';
    }

    const spans = this.display.querySelectorAll('.char');
    spans.forEach(s => s.className = 'char');
    this.updateCaretPosition();

    if (window.virtualKeyboard && this.targetText.length > 0) {
      window.virtualKeyboard.updateCurrentExpectedKey(this.targetText[0]);
    }
  }

  formatTimeDisplay(totalSeconds) {
    if (totalSeconds >= 60) {
      const mins = Math.floor(totalSeconds / 60);
      const secs = totalSeconds % 60;
      return `${mins}m ${secs > 0 ? secs + 's' : ''}`.trim();
    }
    return `${totalSeconds}s`;
  }

  bindEvents() {
    window.addEventListener('keydown', (e) => {
      if (this.isPaused) {
        if (e.key === ' ' || e.key === 'Escape') {
          e.preventDefault();
          this.resumeTest();
        }
        return;
      }

      if (e.key === 'Tab') {
        e.preventDefault();
        this.loadPrompt(false);
        return;
      }

      if (e.key === 'Escape') {
        if (this.startTime && !this.isFinished) {
          e.preventDefault();
          this.togglePause();
          return;
        }
        document.body.classList.toggle('focus-mode');
        return;
      }

      this.handleKeystroke(e.key, e);
    });

    this.container.addEventListener('click', () => {
      this.container.classList.add('focus-ring');
      if (this.mobileProxy) this.mobileProxy.focus();
    });

    if (this.mobileProxy) {
      this.mobileProxy.addEventListener('input', () => {
        if (this.isPaused || this.isFinished) return;
        const val = this.mobileProxy.value;
        if (val.length > 0) {
          const char = val[val.length - 1];
          this.handleKeystroke(char, null);
          this.mobileProxy.value = '';
        }
      });
    }
  }

  togglePause() {
    if (this.isPaused) this.resumeTest();
    else this.pauseTest();
  }

  pauseTest() {
    if (!this.startTime || this.isFinished || this.isPaused) return;
    this.isPaused = true;
    this.pausedAt = performance.now() / 1000.0;
    clearInterval(this.timerInterval);
    clearInterval(this.ghostInterval);

    if (this.display) this.display.style.filter = 'blur(4px)';
    if (this.pauseModal) this.pauseModal.style.display = 'flex';
  }

  resumeTest() {
    if (!this.isPaused) return;
    const now = performance.now() / 1000.0;
    this.totalPausedDuration += (now - this.pausedAt);
    this.isPaused = false;

    if (this.display) this.display.style.filter = 'none';
    if (this.pauseModal) this.pauseModal.style.display = 'none';

    this.startTick(true);
    if (this.ghostEnabled) this.startGhostRacer();
    if (this.mobileProxy) this.mobileProxy.focus();
  }

  handleKeystroke(key, originalEvent) {
    if (this.isFinished || this.isPaused) return;
    if (['Shift', 'Control', 'Alt', 'Meta', 'CapsLock'].includes(key)) return;

    const now = performance.now() / 1000.0;

    if (!this.startTime) {
      this.startTime = now;
      this.startTick(false);
      if (this.ghostEnabled) this.startGhostRacer();
    }

    const spans = this.display.querySelectorAll('.char');
    if (this.currentIndex >= spans.length) return;

    const expectedChar = this.targetText[this.currentIndex];

    // Backspace: In Blind Mode (default ON), Backspace is disabled
    if (key === 'Backspace') {
      if (originalEvent) originalEvent.preventDefault();
      if (this.blindModeActive) return;

      if (this.currentIndex > 0) {
        this.currentIndex--;
        spans[this.currentIndex].className = 'char';
        this.updateCaretPosition();
      }
      return;
    }

    if (key.length !== 1) return;
    if (originalEvent) originalEvent.preventDefault();

    const isCorrect = (key === expectedChar);

    if (isCorrect) {
      spans[this.currentIndex].className = 'char correct';
      this.streak++;
      if (window.soundEngine) window.soundEngine.playKey(false);
    } else {
      spans[this.currentIndex].className = 'char incorrect';
      this.streak = 0;
      this.errors++;
      if (window.soundEngine) window.soundEngine.playKey(true);
    }

    this.events.push({
      char_index: this.currentIndex,
      expected: expectedChar,
      typed: key,
      correct: isCorrect,
      timestamp: parseFloat(now.toFixed(4))
    });

    if (window.virtualKeyboard) {
      window.virtualKeyboard.highlightKey(key);
      window.virtualKeyboard.recordKeyMetric(expectedChar, key, isCorrect, 0);
    }

    this.currentIndex++;
    this.updateCaretPosition();
    this.updateLiveStats(now);

    // Continuous Infinite Text Streaming: Load subsequent passages before reaching the boundary
    if (this.currentIndex >= spans.length - 25) {
      this.loadPrompt(true);
    }

    if (window.virtualKeyboard && this.currentIndex < this.targetText.length) {
      window.virtualKeyboard.updateCurrentExpectedKey(this.targetText[this.currentIndex]);
    }
  }

  startTick(isResume = false) {
    if (!isResume) this.tickElapsed = 0;

    this.timerInterval = setInterval(() => {
      this.tickElapsed++;
      const now = performance.now() / 1000.0;
      this.updateLiveStats(now);

      if (this.durationLimit > 0) {
        const remaining = Math.max(0, this.durationLimit - this.tickElapsed);
        this.hudTime.textContent = this.formatTimeDisplay(remaining);
        if (remaining <= 0) {
          this.finishTest();
        }
      } else {
        this.hudTime.textContent = `${this.formatTimeDisplay(this.tickElapsed)} (No Limit)`;
      }
    }, 1000);
  }

  startGhostRacer() {
    const charsPerSec = (this.ghostWpm * 5) / 60;
    this.ghostInterval = setInterval(() => {
      if (this.isFinished || this.isPaused) {
        clearInterval(this.ghostInterval);
        return;
      }
      this.ghostProgress += (charsPerSec * 0.1);
      const ghostIdx = Math.min(this.targetText.length - 1, Math.floor(this.ghostProgress));
      const spans = this.display.querySelectorAll('.char');
      if (spans[ghostIdx] && this.ghostCaret) {
        this.ghostCaret.style.display = 'block';
        this.ghostCaret.style.left = `${spans[ghostIdx].offsetLeft}px`;
        this.ghostCaret.style.top = `${spans[ghostIdx].offsetTop + 4}px`;
      }
    }, 100);
  }

  updateLiveStats(now) {
    const elapsedMinutes = (now - this.startTime - this.totalPausedDuration) / 60.0;
    if (elapsedMinutes <= 0) return;

    const correctChars = this.events.filter(ev => ev.correct).length;
    const netWpm = Math.max(0, Math.round((correctChars / 5.0) / elapsedMinutes));
    const acc = this.currentIndex > 0 ? Math.round((correctChars / this.currentIndex) * 100) : 100;

    this.hudWpm.textContent = netWpm;
    this.hudAcc.textContent = `${acc}%`;
    this.hudErrors.textContent = this.errors;
    this.updateSpeedometer(netWpm);

    this.timeline.push({
      t: parseFloat((now - this.startTime - this.totalPausedDuration).toFixed(2)),
      wpm: netWpm,
      acc: acc
    });
  }

  updateSpeedometer(wpm) {
    if (!this.speedometerArc) return;
    const pct = Math.min(1.0, wpm / 150.0);
    const offset = 100 - (pct * 100);
    this.speedometerArc.style.strokeDashoffset = offset;
  }

  updateCaretPosition() {
    const spans = this.display.querySelectorAll('.char');
    if (this.currentIndex < spans.length) {
      const target = spans[this.currentIndex];
      this.caret.style.left = `${target.offsetLeft}px`;
      this.caret.style.top = `${target.offsetTop + 4}px`;

      const targetMid = target.offsetTop - (this.container.clientHeight / 2) + 25;
      if (Math.abs(this.container.scrollTop - targetMid) > 20) {
        this.container.scrollTo({
          top: Math.max(0, targetMid),
          behavior: 'smooth'
        });
      }
    } else if (spans.length > 0) {
      const last = spans[spans.length - 1];
      this.caret.style.left = `${last.offsetLeft + last.offsetWidth}px`;
      this.caret.style.top = `${last.offsetTop + 4}px`;
    }
  }

  async finishTest() {
    if (this.isFinished) return;
    this.isFinished = true;
    clearInterval(this.timerInterval);
    clearInterval(this.ghostInterval);

    const finishTime = performance.now() / 1000.0;
    const duration = parseFloat((finishTime - (this.startTime || finishTime) - this.totalPausedDuration).toFixed(2));

    const payload = {
      events: this.events,
      timeline: this.timeline,
      duration: Math.max(1.0, duration),
      target_text: this.targetText.substring(0, this.currentIndex),
      mode: this.durationLimit > 0 ? `timed_${this.durationLimit}` : 'no_limit'
    };

    try {
      const res = await fetch('/typing/api/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (data.success && data.test_id) {
        window.location.href = `/typing/result/${data.test_id}`;
      }
    } catch {
      window.location.reload();
    }
  }
}

window.typingEngine = new TypingEngine();
document.addEventListener('DOMContentLoaded', () => {
  window.typingEngine.loadPrompt(false);
});