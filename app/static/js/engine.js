/**
 * TypeSphere Unified Engine with Version 2.0 In-Browser Layout Translation
 */
class TypingEngine {
  constructor() {
    this.targetText = "";
    this.currentIndex = 0;
    this.events = [];
    this.timeline = [];
    this.startTime = null;
    this.timerInterval = null;
    this.durationLimit = 60;
    this.wordLimit = 25;
    this.mode = 'timed';
    this.codeLanguage = 'python';
    this.withPunctuation = false;
    this.withNumbers = false;
    this.isFinished = false;
    this.isPaused = false;
    this.pausedAt = 0;
    this.totalPausedDuration = 0;
    this.streak = 0;
    this.errors = 0;

    // Survival Mode
    this.maxLives = 3;
    this.lives = 3;

    // Ghost Replay
    this.ghostEnabled = true;
    this.ghostWpm = 70;
    this.ghostTimeline = null;
    this.ghostProgress = 0;
    this.ghostInterval = null;

    // DOM Bindings
    this.container = document.getElementById('typing-box');
    this.display = document.getElementById('text-display');
    this.caret = document.getElementById('caret');
    this.ghostCaret = document.getElementById('ghost-caret');
    this.hudWpm = document.getElementById('hud-wpm');
    this.hudAcc = document.getElementById('hud-acc');
    this.hudTime = document.getElementById('hud-time');
    this.hudStreak = document.getElementById('hud-streak');
    this.fatigueBanner = document.getElementById('fatigue-alert');
    this.livesContainer = document.getElementById('survival-lives');
    this.dailyBanner = document.getElementById('daily-badge-banner');
    this.pauseModal = document.getElementById('pause-modal');
    this.pausedFloatingBar = document.getElementById('paused-floating-bar');
    this.pauseBtn = document.getElementById('pause-btn');
    this.mobileProxy = document.getElementById('mobile-text-proxy');
    this.speedometerArc = document.getElementById('speedo-arc');

    this.bindEvents();
    this.checkUrlParameters();
  }

  async checkUrlParameters() {
    const params = new URLSearchParams(window.location.search);
    
    const ghostTestId = params.get('ghost_race');
    if (ghostTestId) {
      try {
        const res = await fetch(`/typing/api/ghost/${ghostTestId}`);
        const data = await res.json();
        if (data && data.timeline) {
          this.ghostTimeline = data.timeline;
          this.ghostWpm = Math.round(data.wpm);
          const banner = document.getElementById('ghost-toggle');
          if (banner) banner.textContent = `Ghost: PB (${this.ghostWpm} WPM)`;
        }
      } catch (err) {}
    }

    const modeParam = params.get('mode');
    if (modeParam) this.mode = modeParam;

    const durationParam = params.get('duration');
    if (durationParam) this.durationLimit = parseInt(durationParam);
  }

  async loadPrompt(customEndpoint = null) {
    let endpoint = customEndpoint;

    const params = new URLSearchParams(window.location.search);
    const retryTestId = params.get('retry_test_id');
    if (retryTestId && !endpoint) {
      endpoint = `/typing/api/text?retry_test_id=${retryTestId}`;
    }

    if (this.mode === 'custom' && !endpoint) {
      const storedText = sessionStorage.getItem('typesphere_custom_text');
      const storedDuration = sessionStorage.getItem('typesphere_custom_duration');

      if (storedDuration !== null && storedDuration !== undefined) {
        const dur = parseInt(storedDuration);
        this.durationLimit = dur > 0 ? dur : 0;
      }

      if (storedText && storedText.length > 0) {
        this.targetText = storedText.trim();
        this.renderText();
        this.reset();
        return;
      }
    }

    if (this.durationLimit >= 300 && !endpoint) {
      endpoint = `/typing/api/text?mode=timed&words=600&punctuation=${this.withPunctuation}&numbers=${this.withNumbers}`;
    }

    if (!endpoint) {
      if (this.mode === 'daily') {
        endpoint = '/typing/api/daily-text';
      } else if (this.mode === 'words') {
        endpoint = `/typing/api/text?mode=words&words=${this.wordLimit}&punctuation=${this.withPunctuation}&numbers=${this.withNumbers}`;
      } else if (this.mode === 'quote') {
        endpoint = `/typing/api/text?category=Quote&punctuation=true`;
      } else if (this.mode === 'code') {
        endpoint = `/typing/api/text?is_code=true&code_lang=${this.codeLanguage}`;
      } else {
        endpoint = `/typing/api/text?mode=timed&punctuation=${this.withPunctuation}&numbers=${this.withNumbers}`;
      }
    }

    try {
      const res = await fetch(endpoint);
      const data = await res.json();
      this.targetText = data.content.trim();

      if (this.durationLimit >= 300) {
        this.targetText = this.targetText + " " + this.targetText + " " + this.targetText;
      }

      if (this.dailyBanner) {
        if (this.mode === 'daily') {
          this.dailyBanner.style.display = 'flex';
          const titleSpan = document.getElementById('daily-challenge-title');
          if (titleSpan && data.title) titleSpan.textContent = data.title;
        } else {
          this.dailyBanner.style.display = 'none';
        }
      }

      this.renderText();
      this.reset();
    } catch (err) {
      this.targetText = "Speed and precision compound into true keyboard mastery.";
      this.renderText();
      this.reset();
    }
  }

  renderText() {
    this.display.innerHTML = '';
    for (let i = 0; i < this.targetText.length; i++) {
      const span = document.createElement('span');
      span.className = 'char';
      span.textContent = this.targetText[i];
      this.display.appendChild(span);
    }
    this.updateCaretPosition();
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
    this.lives = this.maxLives;
    this.ghostProgress = 0;

    if (this.pauseModal) this.pauseModal.style.display = 'none';
    if (this.pausedFloatingBar) this.pausedFloatingBar.style.display = 'none';
    if (this.pauseBtn) this.pauseBtn.textContent = '⏸ Pause';
    if (this.display) this.display.style.filter = 'none';

    this.hudWpm.textContent = '0';
    this.hudAcc.textContent = '100%';
    this.hudStreak.textContent = '0';
    this.updateSpeedometer(0);

    if (this.durationLimit > 0) {
      this.hudTime.textContent = this.formatTimeDisplay(this.durationLimit);
    } else if (this.mode === 'words') {
      this.hudTime.textContent = this.wordLimit + 'w';
    } else {
      this.hudTime.textContent = 'FULL';
    }

    if (this.livesContainer) {
      this.livesContainer.style.display = (this.mode === 'survival') ? 'flex' : 'none';
      this.renderLives();
    }
    if (this.fatigueBanner) this.fatigueBanner.style.display = 'none';

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
      return `${mins}m ${secs > 0 ? secs + 's' : ''}`;
    }
    return `${totalSeconds}s`;
  }

  renderLives() {
    if (!this.livesContainer) return;
    this.livesContainer.innerHTML = '';
    for (let i = 0; i < this.maxLives; i++) {
      const heart = document.createElement('span');
      heart.textContent = i < this.lives ? '❤️' : '🖤';
      heart.style.fontSize = '1.3rem';
      this.livesContainer.appendChild(heart);
    }
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
        this.loadPrompt();
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

      // Translate through layout manager if active
      const translatedKey = window.layoutManager ? window.layoutManager.translateEvent(e) : e.key;
      this.handleKeystroke(translatedKey, e);
    });

    this.container.addEventListener('click', () => {
      this.container.classList.add('focus-ring');
      if (this.mobileProxy) {
        this.mobileProxy.focus();
      }
    });

    if (this.mobileProxy) {
      this.mobileProxy.addEventListener('input', (e) => {
        if (this.isPaused || this.isFinished) return;
        const val = this.mobileProxy.value;
        if (val.length > 0) {
          const char = val[val.length - 1];
          this.handleKeystroke(char, null);
          this.mobileProxy.value = '';
        }
      });

      this.mobileProxy.addEventListener('keydown', (e) => {
        if (e.key === 'Backspace') {
          this.handleKeystroke('Backspace', e);
        }
      });
    }
  }

  togglePause() {
    if (this.isPaused) {
      this.resumeTest();
    } else {
      this.pauseTest();
    }
  }

  pauseTest() {
    if (!this.startTime || this.isFinished || this.isPaused) return;
    this.isPaused = true;
    this.pausedAt = performance.now() / 1000.0;
    clearInterval(this.timerInterval);
    clearInterval(this.ghostInterval);

    if (this.pauseBtn) this.pauseBtn.textContent = '▶ Resume';
    if (this.display) this.display.style.filter = 'blur(4px)';
    if (this.pauseModal) this.pauseModal.style.display = 'flex';
    if (this.pausedFloatingBar) this.pausedFloatingBar.style.display = 'none';
  }

  closePauseModal() {
    if (this.pauseModal) this.pauseModal.style.display = 'none';
    if (this.isPaused && this.pausedFloatingBar) {
      this.pausedFloatingBar.style.display = 'flex';
    }
  }

  resumeTest() {
    if (!this.isPaused) return;
    const now = performance.now() / 1000.0;
    this.totalPausedDuration += (now - this.pausedAt);
    this.isPaused = false;

    if (this.pauseBtn) this.pauseBtn.textContent = '⏸ Pause';
    if (this.display) this.display.style.filter = 'none';
    if (this.pauseModal) this.pauseModal.style.display = 'none';
    if (this.pausedFloatingBar) this.pausedFloatingBar.style.display = 'none';

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
      this.startTick();
      if (this.ghostEnabled) this.startGhostRacer();
    }

    const expectedChar = this.targetText[this.currentIndex];
    const spans = this.display.querySelectorAll('.char');
    const lastTimestamp = this.events.length > 0 ? this.events[this.events.length - 1].timestamp : this.startTime;
    const latencyMs = Math.round((now - lastTimestamp) * 1000);

    if (key === 'Backspace') {
      if (originalEvent) originalEvent.preventDefault();
      if (this.currentIndex > 0) {
        this.currentIndex--;
        spans[this.currentIndex].className = 'char';
        this.updateCaretPosition();
        if (window.virtualKeyboard) {
          window.virtualKeyboard.updateCurrentExpectedKey(this.targetText[this.currentIndex]);
        }
      }
      return;
    }

    if (key.length !== 1) return;
    if (originalEvent) originalEvent.preventDefault();

    const isCorrect = (key === expectedChar);

    if (isCorrect) {
      spans[this.currentIndex].className = 'char correct';
      this.streak++;
      window.soundEngine.playKey(false);
    } else {
      spans[this.currentIndex].className = 'char incorrect';
      this.streak = 0;
      this.errors++;
      window.soundEngine.playKey(true);

      if (this.mode === 'survival') {
        this.lives--;
        this.renderLives();
        if (this.lives <= 0) {
          this.finishTest(true);
          return;
        }
      }

      if (this.mode === 'accuracy') {
        alert("Accuracy challenge breached! Restarting run.");
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

    if (window.virtualKeyboard) {
      window.virtualKeyboard.highlightKey(key);
      window.virtualKeyboard.recordKeyMetric(expectedChar, key, isCorrect, latencyMs);
    }

    this.currentIndex++;
    this.updateCaretPosition();
    this.updateLiveStats(now);

    if (this.currentIndex < this.targetText.length) {
      if (window.virtualKeyboard) {
        window.virtualKeyboard.updateCurrentExpectedKey(this.targetText[this.currentIndex]);
      }
    } else {
      this.finishTest();
    }
  }

  startTick(isResume = false) {
    if (!isResume) {
      this.tickElapsed = 0;
    }
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
        this.hudTime.textContent = this.formatTimeDisplay(this.tickElapsed);
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
        this.ghostCaret.style.left = spans[ghostIdx].offsetLeft + 'px';
        this.ghostCaret.style.top = spans[ghostIdx].offsetTop + 4 + 'px';
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
    this.hudAcc.textContent = acc + '%';
    this.hudStreak.textContent = this.streak;
    this.updateSpeedometer(netWpm);

    this.timeline.push({
      t: parseFloat((now - this.startTime - this.totalPausedDuration).toFixed(2)),
      wpm: netWpm,
      acc: acc
    });
  }

  updateSpeedometer(wpm) {
    if (!this.speedometerArc) return;
    const pct = Math.min(1.0, wpm / 140.0);
    const offset = 100 - (pct * 100);
    this.speedometerArc.style.strokeDashoffset = offset;
  }

  updateCaretPosition() {
    const spans = this.display.querySelectorAll('.char');
    if (this.currentIndex < spans.length) {
      const target = spans[this.currentIndex];
      this.caret.style.left = target.offsetLeft + 'px';
      this.caret.style.top = target.offsetTop + 4 + 'px';

      const targetMid = target.offsetTop - (this.container.clientHeight / 2) + 30;
      if (Math.abs(this.container.scrollTop - targetMid) > 25) {
        this.container.scrollTo({
          top: Math.max(0, targetMid),
          behavior: 'smooth'
        });
      }
    } else if (spans.length > 0) {
      const last = spans[spans.length - 1];
      this.caret.style.left = (last.offsetLeft + last.offsetWidth) + 'px';
      this.caret.style.top = last.offsetTop + 4 + 'px';
    }
  }

  async finishTest(survivalFailed = false) {
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
      target_text: this.targetText,
      mode: this.mode,
      layout: window.layoutManager ? window.layoutManager.activeLayout : 'qwerty'
    };

    this.displayResultOverlay(survivalFailed);

    try {
      const res = await fetch('/typing/api/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (data.success && data.test_id) {
        setTimeout(() => {
          window.location.href = `/typing/result/${data.test_id}`;
        }, 1200);
      }
    } catch (err) {}
  }

  displayResultOverlay(survivalFailed) {
    const overlay = document.getElementById('result-modal');
    if (!overlay) return;

    const correctChars = this.events.filter(e => e.correct).length;
    const finalWpm = this.hudWpm.textContent;
    const finalAcc = this.hudAcc.textContent;

    document.getElementById('res-wpm').textContent = finalWpm;
    document.getElementById('res-acc').textContent = finalAcc;
    document.getElementById('res-chars').textContent = `${correctChars} / ${this.events.length}`;
    document.getElementById('res-status').textContent = survivalFailed ? "ELIMINATED (Out of Lives)" : "BENCHMARK COMPLETED";

    overlay.style.display = 'flex';
  }
}

window.typingEngine = new TypingEngine();
document.addEventListener('DOMContentLoaded', () => {
  window.typingEngine.loadPrompt();
});