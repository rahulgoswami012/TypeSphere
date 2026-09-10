/**
 * TypeSphere Core Engine
 * Two-tier UI architecture, continuous passage streaming for timed tests,
 * genuine completion points for untimed and custom tests, 5-battery survival mode,
 * and live biometric keyboard synchronization without layout jumping.
 */
class TypingEngine {
    constructor() {
        this.targetText = "";
        this.currentIndex = 0;
        this.events = [];
        this.timeline = [];
        this.startTime = null;
        this.lastKeystrokeTime = null;
        this.timerInterval = null;

        // Test Configuration
        this.durationLimit = 60; // 15, 30, 60, 120, 300, 600, 1200, or 0 (No Limit)
        this.contentType = 'words';
        this.level = 'moderate'; // easy, moderate, hard, expert
        this.codeLanguage = 'python'; // python, javascript, html, css, sql, java, c, cpp
        this.mode = 'timed'; // 'timed', 'accuracy', 'survival', 'adaptive', 'daily', 'custom'
        this.retryTestId = null;
        this.isRankedEligible = true;

        // Survival Challenge: Exactly 5 Shield Cells
        this.shieldLives = 5;
        this.maxShields = 5;

        // Behavioral Defaults
        this.blindModeActive = true; // Blind Mode: ON by default
        this.ghostEnabled = false; // Ghost Mode: OFF by default
        this.ghostWpm = 70;
        this.ghostProgress = 0;
        this.ghostInterval = null;

        // Keystroke Error Telemetry
        this.totalMistakes = 0; // Cumulative mistakes made
        this.uncorrectedErrors = 0; // Red spans remaining
        this.streak = 0;

        // Runtime Lifecycle
        this.isFinished = false;
        this.isPaused = false;
        this.pausedAt = 0;
        this.totalPausedDuration = 0;
        this.handledByKeyDown = false;

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
        this.survivalHud = document.getElementById('survival-shield-hud');
        this.manualFinishWrap = document.getElementById('manual-finish-wrap');

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

        const langParam = params.get('code_lang') || params.get('lang');
        if (langParam) this.codeLanguage = langParam.toLowerCase();

        const retryParam = params.get('retry_test_id');
        if (retryParam) this.retryTestId = retryParam;

        const ghostParam = params.get('ghost_race');
        if (ghostParam) {
            this.loadGhostRace(ghostParam);
        }

        if (this.mode === 'custom') {
            this.contentType = 'custom';
            const storedDur = sessionStorage.getItem('typesphere_custom_duration');
            if (storedDur !== null) {
                this.durationLimit = parseInt(storedDur, 10);
            }
        }

        this.updateRankedEligibility();
    }

    async loadGhostRace(testId) {
        try {
            const res = await fetch(`/typing/api/ghost/${testId}`);
            const data = await res.json();
            if (data && data.wpm) {
                this.ghostWpm = parseFloat(data.wpm);
                this.ghostEnabled = true;
                this.updateControlsUI();
            }
        } catch {}
    }

    updateRankedEligibility() {
        const isStandardTime = [15, 30, 60, 120].includes(this.durationLimit);
        const isStandardContent = ['words', 'paragraphs', 'quotes'].includes(this.contentType);
        this.isRankedEligible = isStandardTime && isStandardContent && (this.mode === 'timed');

        if (this.rankNoticeBadge) {
            if (this.isRankedEligible) {
                this.rankNoticeBadge.innerHTML = `<span style="color:var(--success);">● Ranked Match</span>`;
                this.rankNoticeBadge.title = "Eligible for Global Leaderboards and Verified Flight Wings.";
            } else {
                this.rankNoticeBadge.innerHTML = `<span style="color:var(--text-muted);">○ Practice / Unranked</span>`;
                this.rankNoticeBadge.title = "Specialized parameters or custom text are excluded from ranked standings.";
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

            if (this.container && prefs.typing_area_style) {
                this.container.className = `typing-container focus-ring style-${prefs.typing_area_style}`;
            }
        }
        this.updateControlsUI();
    }

    updateControlsUI() {
        const tSel = document.getElementById('cfg-time-select');
        const cSel = document.getElementById('cfg-type-select');
        const dSel = document.getElementById('cfg-diff-select');
        const lSel = document.getElementById('cfg-code-lang-select');
        const bBtn = document.getElementById('btn-blind');
        const gBtn = document.getElementById('btn-ghost');
        const codeWrap = document.getElementById('cfg-code-lang-wrap');

        if (tSel) tSel.value = this.durationLimit.toString();
        if (cSel) cSel.value = this.contentType;
        if (dSel) dSel.value = this.level;
        if (lSel) lSel.value = this.codeLanguage;
        if (codeWrap) codeWrap.style.display = (this.contentType === 'code') ? 'flex' : 'none';

        if (bBtn) {
            bBtn.textContent = `Blind: ${this.blindModeActive ? 'ON' : 'OFF'}`;
            bBtn.classList.toggle('active-choice', this.blindModeActive);
        }
        if (gBtn) {
            gBtn.textContent = `Ghost: ${this.ghostEnabled ? 'ON' : 'OFF'}`;
            gBtn.classList.toggle('active-choice', this.ghostEnabled);
        }

        // Display 5-Shield HUD only in Survival Mode
        if (this.survivalHud) {
            this.survivalHud.style.display = (this.mode === 'survival') ? 'block' : 'none';
        }

        this.updateRankedEligibility();
    }

    updateShieldHUD() {
        if (this.mode !== 'survival') return;
        const statusText = document.getElementById('shield-status-text');
        const pct = Math.round((this.shieldLives / this.maxShields) * 100);

        if (statusText) {
            statusText.textContent = `${pct}% STABILITY (${this.shieldLives}/${this.maxShields} CELLS)`;
            statusText.style.color = (this.shieldLives <= 1) ? 'var(--danger)' : ((this.shieldLives <= 3) ? 'var(--warning)' : 'var(--accent)');
        }

        for (let i = 1; i <= this.maxShields; i++) {
            const cell = document.getElementById(`sc-${i}`);
            if (cell) {
                cell.className = (i <= this.shieldLives) ? 'shield-cell' : 'shield-cell depleted';
                if (this.shieldLives === 1 && i === 1) cell.classList.add('critical');
            }
        }
    }

    async loadPrompt(append = false) {
        // 1. Custom Text Practice (Never loops or duplicates)
        if (this.contentType === 'custom' || this.mode === 'custom') {
            const stored = sessionStorage.getItem('typesphere_custom_text');
            if (stored && stored.trim().length > 0) {
                this.targetText = stored.trim();
                this.renderText(false);
                this.reset();
                return;
            }
        }

        // 2. Daily Challenge Synchronization
        if (this.mode === 'daily') {
            try {
                const res = await fetch('/typing/api/daily-text');
                const data = await res.json();
                this.targetText = (data.content || "").trim();
                this.renderText(false);
                this.reset();
                return;
            } catch {}
        }

        // 3. Adaptive Weakness Drill
        if (this.mode === 'adaptive') {
            try {
                const res = await fetch('/typing/api/adaptive-drill');
                const data = await res.json();
                this.targetText = (data.drill_text || data.content || "").trim();
                this.renderText(false);
                this.reset();
                return;
            } catch {}
        }

        // 4. Standard Dynamic Streams / Retry Prompts
        try {
            let url = `/typing/api/text?content_type=${encodeURIComponent(this.contentType)}&level=${encodeURIComponent(this.level)}&code_lang=${encodeURIComponent(this.codeLanguage)}&batch_size=75`;
            if (this.retryTestId) {
                url += `&retry_test_id=${encodeURIComponent(this.retryTestId)}`;
            }
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

            if (window.virtualKeyboard && this.targetText.length > 0) {
                window.virtualKeyboard.updateCurrentExpectedKey(this.targetText[0]);
            }
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
        this.lastKeystrokeTime = null;
        this.isFinished = false;
        this.isPaused = false;
        this.pausedAt = 0;
        this.totalPausedDuration = 0;
        this.streak = 0;
        this.totalMistakes = 0;
        this.uncorrectedErrors = 0;
        this.ghostProgress = 0;
        this.shieldLives = 5;

        if (this.container) {
            this.container.scrollTop = 0;
        }

        if (this.pauseModal) this.pauseModal.style.display = 'none';
        const floatBar = document.getElementById('paused-floating-bar');
        if (floatBar) floatBar.style.display = 'none';

        if (this.manualFinishWrap) {
            this.manualFinishWrap.style.display = 'none';
        }

        this.hudWpm.textContent = '0';
        this.hudAcc.textContent = '100%';
        this.hudErrors.textContent = '0';
        this.updateSpeedometer(0);
        this.updateShieldHUD();

        if (this.durationLimit > 0) {
            this.hudTime.textContent = this.formatTimeDisplay(this.durationLimit);
        } else {
            this.hudTime.textContent = '0s (Open Stopwatch)';
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
            if (e.key === 'Enter' && (this.durationLimit === 0 || this.mode === 'custom')) {
                if (this.currentIndex >= this.targetText.length - 5) {
                    e.preventDefault();
                    this.finishTest();
                    return;
                }
            }

            this.handledByKeyDown = true;
            this.handleKeystroke(e.key, e);
            setTimeout(() => { this.handledByKeyDown = false; }, 25);
        });

        this.container.addEventListener('click', () => {
            this.container.classList.add('focus-ring');
            if (this.mobileProxy) this.mobileProxy.focus();
        });

        if (this.mobileProxy) {
            this.mobileProxy.addEventListener('input', () => {
                if (this.isPaused || this.isFinished) return;
                if (this.handledByKeyDown) {
                    this.mobileProxy.value = '';
                    return;
                }
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
        if (['Shift', 'Control', 'Alt', 'Meta', 'CapsLock', 'Dead'].includes(key)) return;

        const now = performance.now() / 1000.0;
        const latencyMs = this.lastKeystrokeTime ? Math.round((now - this.lastKeystrokeTime) * 1000) : 120;
        this.lastKeystrokeTime = now;

        if (!this.startTime) {
            this.startTime = now;
            this.startTick(false);
            if (this.ghostEnabled) this.startGhostRacer();
        }

        const spans = this.display.querySelectorAll('.char');
        if (this.currentIndex >= spans.length) return;
        const expectedChar = this.targetText[this.currentIndex];

        // Backspace Handling: Blocked if Blind Mode is ON
        if (key === 'Backspace') {
            if (originalEvent) originalEvent.preventDefault();
            if (this.blindModeActive) return;

            if (this.currentIndex > 0) {
                this.currentIndex--;
                if (spans[this.currentIndex].classList.contains('incorrect')) {
                    this.uncorrectedErrors = Math.max(0, this.uncorrectedErrors - 1);
                }
                spans[this.currentIndex].className = 'char';
                this.updateCaretPosition();

                if (window.virtualKeyboard && this.currentIndex < spans.length) {
                    window.virtualKeyboard.updateCurrentExpectedKey(this.targetText[this.currentIndex]);
                }
                this.updateLiveStats(now);
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
            this.totalMistakes++;
            this.uncorrectedErrors++;
            if (window.soundEngine) window.soundEngine.playKey(true);

            // Survival Challenge 5-Shield Integrity Overload
            if (this.mode === 'survival') {
                this.shieldLives--;
                this.updateShieldHUD();
                if (this.shieldLives <= 0) {
                    this.finishSurvivalFail();
                    return;
                }
            }

            // Accuracy Gauntlet Elimination
            if (this.mode === 'accuracy') {
                alert("Accuracy Gauntlet Breached: 100% precision required.");
                this.reset();
                return;
            }
        }

        if (window.virtualKeyboard) {
            window.virtualKeyboard.highlightKey(expectedChar);
            window.virtualKeyboard.recordKeyMetric(expectedChar, key, isCorrect, latencyMs);
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

        if (window.virtualKeyboard && this.currentIndex < spans.length) {
            window.virtualKeyboard.updateCurrentExpectedKey(this.targetText[this.currentIndex]);
        }

        // Continuous Infinite Pipeline for Standard Timed Benchmarks
        const isFiniteMode = (this.durationLimit === 0 || this.mode === 'custom');
        if (!isFiniteMode) {
            if (this.currentIndex >= spans.length - 20) {
                this.loadPrompt(true);
            }
        } else {
            // Natural completion for No Time Limit and Custom Passage
            if (this.currentIndex >= spans.length) {
                this.finishTest();
            } else if (this.currentIndex >= spans.length - 10 && this.manualFinishWrap) {
                this.manualFinishWrap.style.display = 'block';
            }
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
                this.hudTime.textContent = `${this.formatTimeDisplay(this.tickElapsed)} (Stopwatch)`;
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
        this.hudErrors.textContent = this.totalMistakes;
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

    finishSurvivalFail() {
        this.isFinished = true;
        clearInterval(this.timerInterval);
        clearInterval(this.ghostInterval);
        alert("💥 COCKPIT SHIELD BREACH! All 5 battery cells exhausted. Reactor containment compromised.");
        this.reset();
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
            mode: this.durationLimit > 0 ? `timed_${this.durationLimit}` : (this.mode || 'stopwatch'),
            is_ranked: this.isRankedEligible,
            content_category: this.contentType,
            difficulty: this.level,
            total_mistakes: this.totalMistakes,
            uncorrected_errors: this.uncorrectedErrors
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