/**
 * TypeSphere Core Engine
 * Two-tier UI architecture, continuous passage streaming for timed tests,
 * and reliable state transitions without layout jumping.
 */
class TypingEngine {
  constructor() {
    this.targetText = "";
    this.currentIndex = 0;
    this.events = [];
    this.timeline = [];

    this.startTime = null;
    this.timerInterval = null;

    // Test Configuration
    this.durationLimit = 60; // 15, 30, 60, 120, 300, 600, 1200, or 0 (No Limit)
    this.contentType = 'words';
    this.level = 'moderate'; // easy, moderate, hard, expert
    this.codeLanguage = 'python';
    this.mode = 'timed'; // 'timed', 'accuracy', 'survival', 'adaptive'
    this.isRankedEligible = true;

    // Behavioral Defaults
    this.blindModeActive = true;  // Blind Mode: ON by default
    this.ghostEnabled = false;    // Ghost Mode: OFF by default
    this.ghostWpm = 70;
    this.ghostProgress = 0;
    this.ghostInterval = null;

    // Runtime Lifecycle
    this.isFinished = false;
    this.isPaused = false;
    this.pausedAt = 0;
    this.totalPausedDuration = 0;
    this.streak = 0;
    this.errors = 0;

    // DOM References
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
    this.rankNoticeBadge = document.getElementById('rank-eligibility-badge');

    this.bindEvents();
    this.parseUrlParameters();
    this.loadUserSessionPreferences();
  }

  parseUrlParameters() {
    const params = new URLSearchParams(window.location.search);
    
    const modeParam = params.get('mode');
    if (modeParam) this.mode = modeParam;

    const durParam = params.get('duration');
    if (durParam) this.durationLimit = parseInt(durParam, 10);

    const typeParam = params.get('content_type');
    if (typeParam) this.contentType = typeParam;

    const levelParam = params.get('level');
    if (levelParam) this.level = levelParam;

    // Ranked eligibility validation: Custom text & unstandardized runs are NOT ranked
    this.updateRankedEligibility();
  }

  updateRankedEligibility() {
    // Ranked eligible ONLY if: standard timed test (15s, 30s, 60s, 120s) with standard content
    const isStandardTime = [15, 30, 60, 120].includes(this.durationLimit);
    const isStandardContent = ['words', 'paragraphs', 'quotes'].includes(this.contentType);
    this.isRankedEligible = isStandardTime && isStandardContent && (this.mode !== 'custom');

    if (this.rankNoticeBadge) {
      if (this.isRankedEligible) {
        this.rankNoticeBadge.innerHTML = `<span style="color:var(--success);">● Ranked Match</span>`;
        this.rankNoticeBadge.title = "Eligible for Global Leaderboards and Personal Records.";
      } else {
        this.rankNoticeBadge.innerHTML = `<span style="color:var(--text-muted);">○ Practice Only</span>`;
        this.rankNoticeBadge.title = "Custom content or irregular parameters will not affect public leaderboards.";
      }
    }
  }

  loadUserSessionPreferences() {
    const prefs = window.settingsManager ? window.settingsManager.current : null;
    if (prefs) {
      if (!window.location.search.includes('duration=')) this.durationLimit = prefs.default_duration || 60;
      if (!window.location.search.includes('content_type=')) this.contentType = prefs.default_content || 'words';
      if (!window.location.search.includes('level=')) this.level = prefs.default_level || 'moderate';
      this.blindModeActive = prefs.blind_mode !== undefined ? prefs.blind_mode : true;
      this.ghostEnabled = prefs.ghost_mode !== undefined ? prefs.ghost_mode : false;
    }
    this.updateControlsUI();
  }

  updateControlsUI() {
    const tSel = document.getElementById('cfg-time-select');
    const cSel = document.getElementById('cfg-type-select');
    const dSel = document.getElementById('cfg-diff-select');
    const bBtn = document.getElementById('btn-blind');
    const gBtn = document.getElementById('btn-ghost');

    if (tSel) tSel.value = this.durationLimit.toString();
    if (cSel) cSel.value = this.contentType;
    if (dSel) dSel.value = this.level;

    if (bBtn) {
      bBtn.textContent = `Blind: ${this.blindModeActive ? 'ON' : 'OFF'}`;
      bBtn.classList.toggle('active-choice', this.blindModeActive);
    }
    if (gBtn) {
      gBtn.textContent = `Ghost: ${this.ghostEnabled ? 'ON' : 'OFF'}`;
      gBtn.classList.toggle('active-choice', this.ghostEnabled);
    }

    this.updateRankedEligibility();
  }

  async loadPrompt(append = false) {
    if (this.contentType === 'custom') {
      const stored = sessionStorage.getItem('typesphere_custom_text');
      if (stored && stored.trim().length > 0) {
        this.targetText = append ? `${this.targetText} ${stored.trim()}` : stored.trim();
        this.renderText(append);
        if (!append) this.reset();
        return;
      }
    }

    try {
      const url = `/typing/api/text?content_type=${encodeURIComponent(this.contentType)}&level=${encodeURIComponent(this.level)}&code_lang=${encodeURIComponent(this.codeLanguage)}&batch_size=75`;
      const res = await fetch(url);
      const data = await res.json();
      const chunk = (data.content || "").trim();

      if (append) {
        this.targetText = `${this.targetText} ${chunk}`;
        this.renderText(true);
      } else {
        this.targetText = chunk;
        this.renderText(false);
        this.reset();
      }
    } catch {
      const fallback = "Simplicity is prerequisite for reliability. Excellence is not an act but a habit honed by persistent, focused rhythm.";
      if (append) {
        this.targetText = `${this.targetText} ${fallback}`;
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
    const floatBar = document.getElementById('paused-floating-bar');
    if (floatBar) floatBar.style.display = 'none';

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
  }

  formatTimeDisplay(totalSeconds) {
    if (totalSeconds >= 60) {
      const mins = Math.floor(totalSeconds / 60);
      const secs = totalSeconds % 60;
      return `${mins}m ${secs > 0 ? `${secs}s` : ''}`.trim();
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

    if (this.pauseModal) this.pauseModal.style.display = 'flex';
  }

  closePauseModal() {
    if (this.pauseModal) this.pauseModal.style.display = 'none';
    const floatBar = document.getElementById('paused-floating-bar');
    if (this.isPaused && floatBar) floatBar.style.display = 'flex';
  }

  resumeTest() {
    if (!this.isPaused) return;
    const now = performance.now() / 1000.0;
    this.totalPausedDuration += (now - this.pausedAt);
    this.isPaused = false;

    if (this.pauseModal) this.pauseModal.style.display = 'none';
    const floatBar = document.getElementById('paused-floating-bar');
    if (floatBar) floatBar.style.display = 'none';

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

    // Backspace Handling: Disabled if Blind Mode is ON
    if (key === 'Backspace') {
      if (originalEvent) originalEvent.preventDefault();
      if (this.blindModeActive) return; // Strict blind mode enforcement

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

      if (this.mode === 'accuracy') {
        alert("Zero-Error Gauntlet breached. 100% accuracy required.");
        this.reset();
        return;
      }
    }

    this.events.push({
      char_index: this.currentIndex,
      expected: expectedChar,
      typed: key,
      correct: isCorrect,
      timestamp: parseFloat(now.toFixed(4))
    });

    this.currentIndex++;
    this.updateCaretPosition();
    this.updateLiveStats(now);

    // Continuous Infinite Content Pipeline: Stream more text before reaching boundary
    if (this.currentIndex >= spans.length - 20) {
      this.loadPrompt(true);
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

      // Smooth Line-by-Line Auto-Centering
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
      mode: this.durationLimit > 0 ? `timed_${this.durationLimit}` : 'no_limit',
      is_ranked: this.isRankedEligible,
      content_category: this.contentType,
      difficulty: this.level
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