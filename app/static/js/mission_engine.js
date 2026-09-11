/**
 * TypeSphere Standalone Mission Execution Engine
 * Handles tactical flight missions (Survival, Accuracy, Endurance, Sprint, Exam, Syntax)
 * with dedicated win/loss conditions, pause/resume states, and automatic DOM event bindings.
 */
class MissionExecutionEngine {
    constructor() {
        this.config = {};
        this.targetText = "";
        this.currentIndex = 0;
        this.events = [];
        this.timeline = [];
        this.startTime = null;
        this.timerInterval = null;
        this.remainingSeconds = 60;
        this.isRunning = false;
        this.isPaused = false;

        // Mode-Specific Telemetry
        this.shieldLives = 5;
        this.totalMistakes = 0;
        this.correctChars = 0;
        this.keydownHandler = (e) => this.handleInputKey(e);
    }

    start(config) {
        this.abort();
        this.config = config || this.config;
        this.targetText = (this.config.targetText || "").trim();
        this.currentIndex = 0;
        this.events = [];
        this.timeline = [];
        this.startTime = null;
        this.totalMistakes = 0;
        this.correctChars = 0;
        this.shieldLives = 5;
        this.remainingSeconds = this.config.duration || 60;
        this.isRunning = true;
        this.isPaused = false;

        window.scrollTo({ top: 0, behavior: 'instant' });

        this.updateHUD(0, 100, 0, this.remainingSeconds);
        this.updateShieldBatteryHUD();
        this.renderText();

        const input = document.getElementById('mission-input');
        if (input) {
            input.value = '';
            input.disabled = false;
            input.focus();
            input.oninput = (e) => this.handleTextInput(e);
        }

        window.removeEventListener('keydown', this.keydownHandler);
        window.addEventListener('keydown', this.keydownHandler);
    }

    abort() {
        this.isRunning = false;
        this.isPaused = false;
        clearInterval(this.timerInterval);
        window.removeEventListener('keydown', this.keydownHandler);
    }

    pause() {
        this.isPaused = true;
    }

    resume() {
        this.isPaused = false;
    }

    renderText() {
        const display = document.getElementById('mission-text-display');
        if (!display) return;
        display.innerHTML = '';
        const frag = document.createDocumentFragment();

        for (let i = 0; i < this.targetText.length; i++) {
            const s = document.createElement('span');
            s.className = (i === 0) ? 'char current' : 'char untyped';
            s.textContent = this.targetText[i];
            frag.appendChild(s);
        }
        display.appendChild(frag);
        this.updateCaret();
    }

    updateCaret() {
        const spans = document.querySelectorAll('#mission-text-display .char');
        const caret = document.getElementById('mission-caret');
        const box = document.getElementById('mission-typing-box');
        if (!caret || !box) return;

        if (this.currentIndex < spans.length) {
            const target = spans[this.currentIndex];
            caret.style.display = 'block';
            caret.style.left = `${target.offsetLeft}px`;
            caret.style.top = `${target.offsetTop + 3}px`;

            const targetMid = target.offsetTop - (box.clientHeight / 2) + 16;
            if (Math.abs(box.scrollTop - targetMid) > 16) {
                box.scrollTo({ top: Math.max(0, targetMid), behavior: 'smooth' });
            }
        } else if (spans.length > 0) {
            const last = spans[spans.length - 1];
            caret.style.left = `${last.offsetLeft + last.offsetWidth}px`;
            caret.style.top = `${last.offsetTop + 3}px`;
        }
    }

    updateShieldBatteryHUD() {
        const textEl = document.getElementById('shield-status-text');
        if (textEl) {
            const pct = Math.round((this.shieldLives / 5) * 100);
            textEl.textContent = `${this.shieldLives} / 5 UNITS (${pct}%)`;
            textEl.style.color = (this.shieldLives <= 1) ? 'var(--danger)' : ((this.shieldLives <= 3) ? 'var(--warning)' : 'var(--accent)');
        }

        for (let i = 1; i <= 5; i++) {
            const cell = document.getElementById(`sc-${i}`);
            if (cell) {
                cell.className = (i <= this.shieldLives) ? 'shield-cell' : 'shield-cell depleted';
                if (this.shieldLives === 1 && i === 1) cell.classList.add('critical');
            }
        }
    }

    handleInputKey(e) {
        if (!this.isRunning || this.isPaused) return;
        if (e.key === 'Backspace') {
            if (this.config.modeType === 'survival' || this.config.modeType === 'accuracy') {
                e.preventDefault();
            }
        }
    }

    handleTextInput(e) {
        if (!this.isRunning || this.isPaused) return;

        const now = performance.now();
        if (!this.startTime) {
            this.startTime = now;
            this.startCountdown();
        }

        const val = e.target.value;
        const spans = document.querySelectorAll('#mission-text-display .char');
        this.currentIndex = Math.min(val.length, this.targetText.length);

        let mistakes = 0;
        let corrects = 0;

        for (let i = 0; i < spans.length; i++) {
            if (i < val.length) {
                if (val[i] === this.targetText[i]) {
                    spans[i].className = 'char correct';
                    corrects++;
                } else {
                    spans[i].className = 'char incorrect';
                    mistakes++;
                }
            } else if (i === val.length) {
                spans[i].className = 'char current';
            } else {
                spans[i].className = 'char untyped';
            }
        }

        if (val.length > 0) {
            const lastTyped = val[val.length - 1];
            const isLastCorrect = (val.length <= this.targetText.length) && (lastTyped === this.targetText[val.length - 1]);

            if (window.soundEngine) {
                window.soundEngine.playKey(!isLastCorrect);
            }

            if (!isLastCorrect) {
                this.totalMistakes++;

                if (this.config.modeType === 'survival') {
                    this.shieldLives = Math.max(0, 5 - this.totalMistakes);
                    this.updateShieldBatteryHUD();
                    if (this.shieldLives <= 0) {
                        this.concludeMission(false, "Reactor Hull Breach: All 5 shield integrity batteries depleted under excessive keystroke strain.");
                        return;
                    }
                }

                if (this.config.modeType === 'accuracy') {
                    this.concludeMission(false, "Mission Aborted: Zero-error precision protocol breached. A single typographical error compromises flight stealth.");
                    return;
                }
            }
        }

        this.correctChars = corrects;
        this.updateCaret();

        const elapsedMin = (now - this.startTime) / 60000.0;
        const netWpm = elapsedMin > 0 ? Math.round((corrects / 5.0) / elapsedMin) : 0;
        const liveAcc = this.currentIndex > 0 ? Math.round((corrects / this.currentIndex) * 100) : 100;

        this.updateHUD(netWpm, liveAcc, this.totalMistakes, this.remainingSeconds);

        if (val.length >= this.targetText.length) {
            this.evaluateMissionEnd(netWpm, liveAcc);
        }
    }

    startCountdown() {
        clearInterval(this.timerInterval);
        this.timerInterval = setInterval(() => {
            if (!this.isRunning || this.isPaused) return;
            this.remainingSeconds--;
            
            const now = performance.now();
            const elapsedMin = (now - this.startTime) / 60000.0;
            const netWpm = elapsedMin > 0 ? Math.round((this.correctChars / 5.0) / elapsedMin) : 0;
            const liveAcc = this.currentIndex > 0 ? Math.round((this.correctChars / this.currentIndex) * 100) : 100;

            this.updateHUD(netWpm, liveAcc, this.totalMistakes, this.remainingSeconds);

            if (this.remainingSeconds <= 0) {
                this.evaluateMissionEnd(netWpm, liveAcc);
            }
        }, 1000);
    }

    updateHUD(wpm, acc, err, timeSec) {
        const wEl = document.getElementById('hud-mission-wpm');
        const aEl = document.getElementById('hud-mission-acc');
        const eEl = document.getElementById('hud-mission-err');
        const tEl = document.getElementById('hud-mission-time');

        if (wEl) wEl.textContent = wpm;
        if (aEl) aEl.textContent = `${acc}%`;
        if (eEl) eEl.textContent = err;
        if (tEl) tEl.textContent = `${Math.max(0, timeSec)}s`;
    }

    evaluateMissionEnd(finalWpm, finalAcc) {
        const mType = this.config.modeType;

        if (mType === 'speed_sprint') {
            if (finalWpm >= 70 && finalAcc >= 90) {
                this.concludeMission(true, `Supersonic Intercept Success! Checkpoint cleared with ${finalWpm} WPM and ${finalAcc}% accuracy.`);
            } else {
                this.concludeMission(false, `Velocity Threshold Missed: Achieved ${finalWpm} WPM (70+ WPM required). Re-engage with higher burst cadence.`);
            }
        } else if (mType === 'endurance') {
            if (finalAcc >= 92) {
                this.concludeMission(true, `Endurance Marathon Mastered! Maintained ${finalWpm} WPM through all 300 seconds.`);
            } else {
                this.concludeMission(false, `Precision Exhaustion: Final accuracy was ${finalAcc}% (92% required across 300s).`);
            }
        } else if (mType === 'exam') {
            if (finalAcc >= 95) {
                this.concludeMission(true, `Statutory Administrative Benchmark Satisfied! Transcribed with ${finalAcc}% precision.`);
            } else {
                this.concludeMission(false, `Standard Not Met: ${finalAcc}% accuracy achieved (95%+ required for civil service clearance).`);
            }
        } else {
            this.concludeMission(true, `Mission Objectives Satisfied! Completed flight with ${finalWpm} WPM and ${finalAcc}% accuracy.`);
        }
    }

    concludeMission(isVictory, summaryMessage) {
        this.abort();
        window.scrollTo({ top: 0, behavior: 'instant' });

        const input = document.getElementById('mission-input');
        if (input) input.disabled = true;

        const cockpitEl = document.getElementById('mission-active-cockpit');
        const resultEl = document.getElementById('mission-result-screen');
        if (cockpitEl) cockpitEl.style.display = 'none';
        if (resultEl) resultEl.style.display = 'block';

        const elapsedSec = Math.max(1, (this.config.duration || 60) - this.remainingSeconds);
        const elapsedMin = elapsedSec / 60.0;
        const finalWpm = elapsedMin > 0 ? Math.round((this.correctChars / 5.0) / elapsedMin) : 0;
        const finalAcc = this.currentIndex > 0 ? Math.round((this.correctChars / this.currentIndex) * 100) : 100;

        const badge = document.getElementById('mission-outcome-badge');
        const icon = document.getElementById('mission-outcome-icon');
        const title = document.getElementById('mission-outcome-title');
        const desc = document.getElementById('mission-outcome-desc');

        if (isVictory) {
            badge.textContent = "MISSION ACCOMPLISHED";
            badge.style.background = "var(--success-bg)";
            badge.style.color = "var(--success)";
            icon.textContent = "🏆";
            title.textContent = "Flight Directives Satisfied";
            title.style.color = "var(--success)";
        } else {
            badge.textContent = "MISSION FAILED";
            badge.style.background = "var(--danger-bg)";
            badge.style.color = "var(--danger)";
            icon.textContent = "💥";
            title.textContent = "Tactical Abort Triggered";
            title.style.color = "var(--danger)";
        }

        desc.textContent = summaryMessage;

        document.getElementById('res-m-wpm').textContent = `${finalWpm} WPM`;
        document.getElementById('res-m-acc').textContent = `${finalAcc}%`;
        document.getElementById('res-m-err').textContent = this.totalMistakes;
        document.getElementById('res-m-time').textContent = `${Math.round(elapsedSec)}s`;

        fetch('/challenges/api/submit-mission', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                mode: `mission_${this.config.slug}`,
                duration: elapsedSec,
                target_text: this.targetText,
                total_mistakes: this.totalMistakes,
                outcome: isVictory ? 'VICTORY' : 'DEFEAT',
                events: this.events
            })
        }).catch(() => {});
    }
}

window.missionEngine = new MissionExecutionEngine();

// Automatic Event Bindings
document.addEventListener('DOMContentLoaded', () => {
    const root = document.getElementById('mission-arena-root');
    if (!root) return;

    const passageEl = document.getElementById('mission-raw-passage');
    const targetText = passageEl ? passageEl.textContent.trim() : "";

    const missionConfig = {
        slug: root.dataset.slug,
        modeType: root.dataset.mode,
        duration: parseInt(root.dataset.duration, 10) || 60,
        targetText: targetText
    };

    // Launch Button
    const launchBtn = document.getElementById('btn-launch-mission');
    if (launchBtn) {
        launchBtn.addEventListener('click', () => {
            document.getElementById('mission-briefing-screen').style.display = 'none';
            document.getElementById('mission-result-screen').style.display = 'none';
            document.getElementById('mission-active-cockpit').style.display = 'block';
            window.missionEngine.start(missionConfig);
        });
    }

    // Abort Prompt Button
    const abortPromptBtn = document.getElementById('btn-prompt-abort');
    if (abortPromptBtn) {
        abortPromptBtn.addEventListener('click', () => {
            window.missionEngine.pause();
            const input = document.getElementById('mission-input');
            if (input) input.blur();
            const modal = document.getElementById('mission-abort-modal');
            if (modal) modal.style.display = 'flex';
        });
    }

    // Modal Resume Button
    const modalResumeBtn = document.getElementById('btn-modal-resume');
    if (modalResumeBtn) {
        modalResumeBtn.addEventListener('click', () => {
            const modal = document.getElementById('mission-abort-modal');
            if (modal) modal.style.display = 'none';
            window.missionEngine.resume();
            const input = document.getElementById('mission-input');
            if (input) input.focus();
        });
    }

    // Modal Confirm Abort Button
    const modalConfirmBtn = document.getElementById('btn-modal-confirm');
    if (modalConfirmBtn) {
        modalConfirmBtn.addEventListener('click', () => {
            const modal = document.getElementById('mission-abort-modal');
            if (modal) modal.style.display = 'none';
            window.missionEngine.abort();
            document.getElementById('mission-briefing-screen').style.display = 'block';
            document.getElementById('mission-active-cockpit').style.display = 'none';
            document.getElementById('mission-result-screen').style.display = 'none';
        });
    }

    // Restart Mission Button
    const restartBtn = document.getElementById('btn-restart-mission');
    if (restartBtn) {
        restartBtn.addEventListener('click', () => {
            document.getElementById('mission-result-screen').style.display = 'none';
            document.getElementById('mission-active-cockpit').style.display = 'block';
            window.missionEngine.start(missionConfig);
        });
    }

    // Focus input on typing container click
    const typingBox = document.getElementById('mission-typing-box');
    if (typingBox) {
        typingBox.addEventListener('click', () => {
            const input = document.getElementById('mission-input');
            if (input) input.focus();
        });
    }
});