/**
 * TypeSphere Arcade Unified Client Runtime Engine
 * Drives all 11 educational typing games with explicit timers, objectives,
 * auto-centering paragraph scrolling, dynamic AI competitor simulation,
 * score recoil penalties on errors, and viewport-centered results transitions.
 */
class ArcadeRuntimeEngine {
    constructor() {
        this.viewport = null;
        this.config = {};
        this.socket = null;

        // Core Metrics
        this.score = 0;
        this.errors = 0;
        this.combo = 0;
        this.maxCombo = 0;
        this.totalCharsTyped = 0;
        this.correctCharsTyped = 0;
        this.startTime = 0;
        this.reactionLatencies = [];
        this.lastActionTimestamp = 0;

        // Engine State
        this.entities = [];
        this.gameLoopTimer = null;
        this.spawnTimer = null;
        this.aiLoopTimer = null;
        this.objectiveCountdownTimer = null;
        this.activeTarget = null;
        this.inputBuffer = "";
        this.isRunning = false;
        this.isPaused = false;
        this.contentBatch = [];
        this.remainingSeconds = 60;
        this.botSimulator = null;
        this.keydownHandler = (e) => this.handleKeystroke(e);
    }

    start(config) {
        this.stop();
        this.config = config;
        this.viewport = document.getElementById('arcade-viewport');
        if (!this.viewport) return;
        this.viewport.innerHTML = '';

        this.score = 0;
        this.errors = 0;
        this.combo = 0;
        this.maxCombo = 0;
        this.totalCharsTyped = 0;
        this.correctCharsTyped = 0;
        this.reactionLatencies = [];
        this.entities = [];
        this.inputBuffer = "";
        this.activeTarget = null;
        this.isRunning = true;
        this.isPaused = false;
        this.startTime = performance.now();
        this.lastActionTimestamp = this.startTime;
        this.remainingSeconds = parseInt(this.config.objectiveVal) || 60;

        // Snap viewport directly to top so active workspace is centered
        window.scrollTo({ top: 0, behavior: 'instant' });

        // Dynamic Pilot AI Simulator
        const userWpmRef = (this.config.userWpm || 60);
        if (typeof DynamicPilotAISimulator !== 'undefined') {
            this.botSimulator = new DynamicPilotAISimulator(this.config.difficulty, userWpmRef);
        } else if (typeof window.DynamicPilotAISimulator !== 'undefined') {
            this.botSimulator = new window.DynamicPilotAISimulator(this.config.difficulty, userWpmRef);
        } else {
            this.botSimulator = {
                callsign: 'PILOT AI',
                currentWpm: 55,
                progressPct: 0,
                progressChars: 0,
                tick: (dt, total) => {
                    this.botSimulator.progressPct = Math.min(100, this.botSimulator.progressPct + (dt * 3.0));
                    return {
                        wpm: 55,
                        progressPct: this.botSimulator.progressPct,
                        progressChars: Math.round((this.botSimulator.progressPct / 100) * total),
                        callsign: 'PILOT AI'
                    };
                },
                reset: () => { this.botSimulator.progressPct = 0; }
            };
        }

        this.updateHUD(0, 0, 0);
        this.contentBatch = this.getFallbackBatch(config.slug, config.difficulty, config.charMode);

        this.initSockets();
        this.initGameMode(config.slug);

        window.removeEventListener('keydown', this.keydownHandler);
        window.addEventListener('keydown', this.keydownHandler);
        this.viewport.focus();
    }

    stop() {
        this.isRunning = false;
        clearInterval(this.gameLoopTimer);
        clearInterval(this.spawnTimer);
        clearInterval(this.aiLoopTimer);
        clearInterval(this.objectiveCountdownTimer);
        if (this.moleWindowTimer) clearTimeout(this.moleWindowTimer);
        window.removeEventListener('keydown', this.keydownHandler);

        if (this.socket) {
            this.socket.disconnect();
            this.socket = null;
        }
    }

    pause() { this.isPaused = true; }
    resume() { this.isPaused = false; }

    getFallbackBatch(slug, diff, charMode) {
        const common = [
            "velocity", "cadence", "rhythm", "kinetic", "precision", "matrix",
            "stream", "quantum", "tactile", "circuit", "binary", "system",
            "engine", "pilot", "balance", "command", "transit", "standard",
            "channel", "motion", "action", "focus", "dynamic", "pressure"
        ];

        if (slug === 'speed_racer') {
            return [
                "The open highway stretched across the desert floor under a wide expanse of pale morning sky. High velocity demands relaxed control and steady breathing. When the throttle opens every second compounds into pure forward momentum.",
                "Aerodynamic contours slice through the crosswinds while tire grip holds the apex through turn four. Precision steering and rhythmic engine shifts maintain the optimal racing line.",
                "Competitive speed is born from calculated motion. Downshifting before the curve preserves brake integrity and guarantees blistering acceleration down the main straight."
            ];
        }

        if (slug === 'bubble_pop') {
            const sets = {
                'letters': [..."abcdefghijklmnopqrstuvwxyz"],
                'uppercase': [..."ABCDEFGHIJKLMNOPQRSTUVWXYZ"],
                'numbers': [..."0123456789"],
                'symbols': [..."!@#$%^&*()-_=+[]{}|;:,.<>?/"],
                'letters_numbers': [..."abcdefghijklmnopqrstuvwxyz0123456789"],
                'mixed_all': [..."abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()"]
            };
            return sets[charMode] || sets['letters'];
        }

        if (slug === 'cipher_hacker') {
            return [
                ["0x7FA9", "0xDE4B", "0x91C0"],
                ["AES_256", "SHA_512", "TLS_13"],
                ["chmod 755", "int main()", "return 0;"],
                ["0xFF00AA55BB66CC77", "const auto&& ptr = null;"]
            ];
        }

        if (slug === 'bomb_defuse') {
            return ["ALPHA78", "DELTA94", "OMEGA12", "BRAVO33", "HAZARD8", "VECTOR0", "PULSE99"];
        }

        if (slug === 'memory_type') {
            return ["recall", "phantom", "quantum", "horizon", "velocity", "kinetic", "matrix", "cadence", "stream"];
        }

        if (slug === 'keyboard_quest') {
            return ["asdf", "jkl;", "glad", "flask", "half", "fall", "quiet", "write", "power", "tower", "cabin", "zinc", "calm", "jump", "quick", "orbit", "stream", "focus", "clean", "speed"];
        }

        return common;
    }

    initSockets() {
        if (!window.io) return;
        this.socket = io();

        this.socket.emit('arcade_room_create', {
            game_slug: this.config.slug,
            play_mode: this.config.playMode,
            difficulty: this.config.difficulty,
            objective_val: this.config.objectiveVal,
            blind_mode: this.config.blindMode,
            backspace_allowed: this.config.backspaceAllowed,
            char_mode: this.config.charMode,
            room_code: this.config.roomCode,
            player_name: "Pilot"
        });

        this.socket.on('arcade_room_ready', (room) => {
            if (room.content && room.content.length > 0) {
                this.contentBatch = room.content;
                if (this.config.slug === 'speed_racer' && this.racerIdx === 0) {
                    this.racerPassage = this.contentBatch[0];
                    this.renderRacerSpans();
                }
            }
        });

        this.socket.on('arcade_live_telemetry', (data) => {
            if (this.isPaused) return;
            if (this.config.playMode !== 'solo_ai') {
                const players = data.players || {};
                const opp = Object.values(players).find(p => p.sid !== (this.socket ? this.socket.id : ''));
                if (opp) {
                    const oppStat = document.getElementById('live-opp-stat');
                    const oppWpm = document.getElementById('live-opp-wpm');
                    if (oppStat) oppStat.textContent = `${Math.round(opp.score)} pts`;
                    if (oppWpm) oppWpm.textContent = `${Math.round(opp.wpm)} WPM`;

                    if (this.config.slug === 'speed_racer') {
                        this.updateSpeedRacerPosition('bot', opp.progress);
                        if (opp.progress >= 100 && this.isRunning) {
                            this.finishGame(false, `${opp.name || 'Opponent'} crossed the finish line ahead of you!`);
                        }
                    }
                }
            }
        });

        if (this.config.playMode === 'solo_ai') {
            const aiTickInterval = 120;
            const totalChars = (this.config.slug === 'speed_racer') ? (this.targetDistanceMeters * 0.4) : 250;

            this.aiLoopTimer = setInterval(() => {
                if (this.isRunning && !this.isPaused && this.botSimulator) {
                    const aiTick = this.botSimulator.tick(aiTickInterval / 1000.0, totalChars);
                    this.renderDynamicAITelemetry(aiTick);
                }
            }, aiTickInterval);
        }
    }

    renderDynamicAITelemetry(aiData) {
        const oppStat = document.getElementById('live-opp-stat');
        const oppWpm = document.getElementById('live-opp-wpm');
        const oppLabel = document.getElementById('live-opp-label');

        if (oppLabel) oppLabel.textContent = aiData.callsign;
        if (oppStat) oppStat.textContent = `${Math.round(aiData.progressPct * 10)} pts`;
        if (oppWpm) oppWpm.textContent = `${aiData.wpm} WPM`;

        if (this.config.slug === 'speed_racer') {
            this.updateSpeedRacerPosition('bot', aiData.progressPct);
            if (aiData.progressPct >= 100 && this.isRunning) {
                this.finishGame(false, `${aiData.callsign} crossed the finish line first!`);
            }
        }

        if (this.config.slug === 'zombie_duel' && this.isRunning) {
            if (Math.random() < (aiData.wpm / 1500.0)) {
                this.playerHP = Math.max(0, this.playerHP - 6);
                const bar = document.getElementById('duel-player-hp');
                const lbl = document.getElementById('player-hp-label');
                if (bar) bar.style.width = `${this.playerHP}%`;
                if (lbl) lbl.textContent = `${this.playerHP} / 100 HP`;

                if (window.soundEngine) window.soundEngine.playKey(true);
                if (this.playerHP <= 0) {
                    this.finishGame(false, `Combat Loss: ${aiData.callsign} overwhelmed your shields!`);
                }
            }
        }
    }

    syncProgressToServer(progressPct, wpm) {
        if (!this.socket || !this.isRunning) return;
        const acc = this.totalCharsTyped > 0 
            ? Math.round((this.correctCharsTyped / this.totalCharsTyped) * 100.0) 
            : 100;

        this.socket.emit('arcade_progress_sync', {
            progress: progressPct,
            score: this.score,
            wpm: wpm,
            accuracy: acc,
            errors: this.errors,
            finished: progressPct >= 100
        });
    }

    initGameMode(slug) {
        switch (slug) {
            case 'speed_racer': this.initSpeedRacer(); break;
            case 'bubble_pop': this.initBubblePop(); break;
            case 'whack_a_word': this.initWhackAWord(); break;
            case 'zombie_duel': this.initZombieDuel(); break;
            case 'cipher_hacker': this.initCipherHacker(); break;
            case 'falling_words': this.initFallingWords(); break;
            case 'zombie_defense': this.initZombieDefense(); break;
            case 'space_defender': this.initSpaceDefender(); break;
            case 'bomb_defuse': this.initBombDefuse(); break;
            case 'typing_ninja': this.initTypingNinja(); break;
            case 'memory_type': this.initMemoryType(); break;
            case 'keyboard_quest': this.initKeyboardQuest(); break;
            default: this.initFallingWords();
        }
    }

    // 1. SPEED RACER
    initSpeedRacer() {
        const isMultiplayer = (this.config.playMode !== 'solo_ai' && this.config.playMode !== 'solo_practice');
        const oppIcon = isMultiplayer ? "🏎️" : "🤖";
        const botName = this.botSimulator ? this.botSimulator.callsign : "CyberBot (AI)";
        const oppLabel = isMultiplayer ? "Opponent" : botName;

        this.viewport.innerHTML = `
            <div class="racer-track-surface"></div>
            <div class="racer-lane-divider" style="top:30%;"></div>
            <div class="racer-lane-divider" style="top:60%;"></div>
            <div class="racer-finish-gate"></div>
            <div id="car-player" class="racer-vehicle-node" style="top:65px; left:25px;">
                <div class="racer-vehicle-icon" style="filter:drop-shadow(0 4px 10px rgba(56,189,248,0.8));">🏎️</div>
                <div class="racer-hud-tag" style="border-color:var(--accent); color:var(--accent);">You</div>
                <div id="player-nitro" class="nitro-exhaust-burn" style="display:none;"></div>
            </div>
            <div id="car-bot" class="racer-vehicle-node" style="top:185px; left:25px; ${this.config.playMode === 'solo_practice' ? 'display:none;' : ''}">
                <div class="racer-vehicle-icon">${oppIcon}</div>
                <div class="racer-hud-tag" id="live-opp-label" style="border-color:var(--warning); color:var(--warning);">${oppLabel}</div>
            </div>
            <div id="racer-text-track" class="arcade-passage-box"></div>
        `;

        this.racerBatchIndex = 0;
        this.racerPassage = this.contentBatch[0] || "Speed is born from economy of movement.";
        this.racerIdx = 0;
        this.playerDistanceMeters = 0;
        this.targetDistanceMeters = parseInt(this.config.objectiveVal) || 500;
        this.renderRacerSpans();
    }

    renderRacerSpans() {
        const box = document.getElementById('racer-text-track');
        if (!box) return;
        box.innerHTML = '';
        const frag = document.createDocumentFragment();
        for (let i = 0; i < this.racerPassage.length; i++) {
            const s = document.createElement('span');
            s.className = (i === 0) ? 'char current' : 'char untyped';
            s.textContent = this.racerPassage[i];
            frag.appendChild(s);
        }
        box.appendChild(frag);
        box.scrollTop = 0;
    }

    scrollRacerTextToActive(span) {
        const box = document.getElementById('racer-text-track');
        if (!box || !span) return;
        const targetMid = span.offsetTop - (box.clientHeight / 2) + 16;
        if (Math.abs(box.scrollTop - targetMid) > 16) {
            box.scrollTo({ top: Math.max(0, targetMid), behavior: 'smooth' });
        }
    }

    updateSpeedRacerPosition(target, pct) {
        const maxPixels = this.viewport.clientWidth - 110;
        const offset = Math.max(25, (pct / 100.0) * maxPixels);
        const car = document.getElementById(target === 'player' ? 'car-player' : 'car-bot');
        if (car) car.style.left = `${offset}px`;
    }

    // 2. BUBBLE POP
    initBubblePop() {
        this.viewport.innerHTML = `
            <div style="position:absolute; top:35px; left:0; right:0; height:2px; background:var(--danger); opacity:0.6;"></div>
            <div style="position:absolute; top:12px; right:20px; font-family:var(--font-mono); font-weight:800; color:var(--accent);">
                Time: <span id="bubble-clock">${this.remainingSeconds}s</span>
            </div>
        `;
        this.bubbleLives = 3;

        this.spawnCharBubble();
        this.spawnCharBubble();

        this.spawnTimer = setInterval(() => { if (!this.isPaused) this.spawnCharBubble(); }, 1000);
        this.gameLoopTimer = setInterval(() => { if (!this.isPaused) this.tickBubbles(); }, 40);

        this.objectiveCountdownTimer = setInterval(() => {
            if (this.isPaused) return;
            this.remainingSeconds--;
            const clk = document.getElementById('bubble-clock');
            if (clk) clk.textContent = `${this.remainingSeconds}s`;
            if (this.remainingSeconds <= 0) {
                this.finishGame(true, `Victory! You defended the ceiling and scored ${this.score} points!`);
            }
        }, 1000);
    }

    spawnCharBubble() {
        if (this.entities.length >= 10 || !this.isRunning) return;
        const char = this.contentBatch[Math.floor(Math.random() * this.contentBatch.length)] || 'a';
        const el = document.createElement('div');
        el.className = 'arcade-char-bubble';
        el.textContent = char;
        const maxW = Math.max(80, this.viewport.clientWidth - 80);
        el.style.left = `${Math.floor(Math.random() * maxW) + 15}px`;
        el.style.bottom = '0px';
        this.viewport.appendChild(el);
        this.entities.push({ el, char, y: 0, speed: 1.3 + Math.random() * 1.1 });
    }

    tickBubbles() {
        for (let i = this.entities.length - 1; i >= 0; i--) {
            const b = this.entities[i];
            b.y += b.speed;
            b.el.style.bottom = `${b.y}px`;
            if (b.y >= this.viewport.clientHeight - 60) {
                b.el.remove();
                this.entities.splice(i, 1);
                this.bubbleLives--;
                this.registerError();
                if (this.bubbleLives <= 0) {
                    this.finishGame(false, "Loss: 3 bubbles burst against the ceiling barrier.");
                    break;
                }
            }
        }
    }

    // 3. WHACK-A-WORD
    initWhackAWord() {
        this.whackLives = 5;
        this.viewport.innerHTML = `
            <div style="display:flex; justify-content:space-between; padding:12px 25px 0; align-items:center;">
                <div>Hammers: <span id="whack-hammers" style="font-size:1.1rem;">🔨🔨🔨🔨🔨</span></div>
                <div style="font-family:var(--font-mono); font-weight:800; color:var(--warning);">Time: <span id="whack-clock">${this.remainingSeconds}s</span></div>
            </div>
            <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:1rem; max-width:620px; margin:16px auto;">
                ${[0,1,2,3,4,5,6,7,8].map(i => `
                    <div id="hole-${i}" style="height:88px; background:var(--bg-card); border:2px solid var(--border-color); border-radius:8px; display:flex; align-items:center; justify-content:center; font-family:var(--font-mono); font-weight:800; font-size:1.15rem; color:var(--text-muted); transition:background 0.15s ease, border-color 0.15s ease;"></div>
                `).join('')}
            </div>
        `;
        this.whackTarget = "";
        this.whackBuffer = "";
        this.currentHole = -1;
        this.spawnNextMole();

        this.objectiveCountdownTimer = setInterval(() => {
            if (this.isPaused) return;
            this.remainingSeconds--;
            const clk = document.getElementById('whack-clock');
            if (clk) clk.textContent = `${this.remainingSeconds}s`;
            if (this.remainingSeconds <= 0) {
                this.finishGame(true, `Victory! Target exposure rounds mastered with ${this.score} pts!`);
            }
        }, 1000);
    }

    spawnNextMole() {
        if (this.moleWindowTimer) clearTimeout(this.moleWindowTimer);
        if (!this.isRunning || this.isPaused) return;

        if (this.currentHole >= 0) {
            const prev = document.getElementById(`hole-${this.currentHole}`);
            if (prev) {
                prev.textContent = '';
                prev.style.borderColor = 'var(--border-color)';
                prev.style.background = 'var(--bg-card)';
            }
        }

        this.currentHole = Math.floor(Math.random() * 9);
        this.whackTarget = this.contentBatch[Math.floor(Math.random() * this.contentBatch.length)] || "strike";
        this.whackBuffer = "";
        this.lastActionTimestamp = performance.now();

        const hole = document.getElementById(`hole-${this.currentHole}`);
        if (hole) {
            hole.innerHTML = `<span class="char untyped">${this.whackTarget}</span>`;
            hole.style.borderColor = 'var(--accent)';
            hole.style.background = 'var(--bg-card)';
        }

        const windowMs = {'easy': 4200, 'moderate': 3500, 'hard': 3000, 'expert': 2600}[this.config.difficulty] || 3500;
        this.moleWindowTimer = setTimeout(() => {
            if (this.isPaused) return;
            this.whackLives--;
            this.registerError();
            const hEl = document.getElementById('whack-hammers');
            if (hEl) hEl.textContent = "🔨".repeat(Math.max(0, this.whackLives)) || "💥 Defeated";

            if (this.whackLives <= 0) {
                this.finishGame(false, "Loss: Missed 5 reaction exposure windows.");
            } else {
                this.spawnNextMole();
            }
        }, windowMs);
    }

    // 4. ZOMBIE DUEL
    initZombieDuel() {
        this.playerHP = 100;
        this.opponentHP = 100;
        const oppName = (this.config.playMode === 'solo_ai') ? (this.botSimulator ? this.botSimulator.callsign : "CyberZombie (AI)") : "Opponent";

        this.viewport.innerHTML = `
            <div class="duel-combat-arena">
                <div class="duel-combatant-card">
                    <div style="font-size:1.6rem;">🧙‍♂️ <strong style="font-size:1.05rem; color:var(--accent);">You</strong></div>
                    <div class="duel-hp-bar-container">
                        <div id="duel-player-hp" class="duel-hp-fill" style="width:100%; background:var(--success);"></div>
                    </div>
                    <span id="player-hp-label" style="font-family:var(--font-mono); font-size:0.8rem;">100 / 100 HP</span>
                </div>
                <div style="font-size:2.2rem; font-weight:900; color:var(--warning);">VS</div>
                <div class="duel-combatant-card" style="text-align:right;">
                    <div style="font-size:1.6rem;"><strong id="live-opp-label" style="font-size:1.05rem; color:var(--danger);">${oppName}</strong> 🧟</div>
                    <div class="duel-hp-bar-container">
                        <div id="duel-opp-hp" class="duel-hp-fill" style="width:100%; background:var(--danger);"></div>
                    </div>
                    <span id="opp-hp-label" style="font-family:var(--font-mono); font-size:0.8rem;">100 / 100 HP</span>
                </div>
            </div>
            <div style="text-align:center; margin-top:35px;">
                <div style="font-size:0.85rem; text-transform:uppercase; color:var(--text-muted); font-weight:700;">Cast Combat Spell:</div>
                <div id="duel-spell-box" style="font-family:var(--font-mono); font-size:2.6rem; font-weight:900; margin:12px 0;">ATTACK</div>
            </div>
        `;
        this.spawnDuelTarget();
    }

    spawnDuelTarget() {
        this.duelTarget = this.contentBatch[Math.floor(Math.random() * this.contentBatch.length)] || "strike";
        this.duelBuffer = "";
        const box = document.getElementById('duel-spell-box');
        if (box) box.innerHTML = `<span class="char untyped">${this.duelTarget}</span>`;
    }

    // 5. CIPHER HACKER
    initCipherHacker() {
        this.currentLayer = 1;
        this.totalLayers = parseInt(this.config.objectiveVal) || 4;
        this.layerTokens = this.contentBatch[0] || ["0x7FA9", "0xDE4B", "0x91C0"];
        this.tokenIdx = 0;
        this.lockdownSeconds = 60;

        this.viewport.innerHTML = `
            <div style="text-align:center; padding-top:25px;">
                <div style="display:flex; justify-content:space-between; max-width:480px; margin:0 auto 10px;">
                    <div class="cipher-layer-badge" id="cipher-layer-title">SECURITY LAYER 1 / ${this.totalLayers}</div>
                    <span style="font-family:var(--font-mono); font-weight:800; color:var(--danger);">Lockdown: <span id="cipher-lockdown-clk">60s</span></span>
                </div>
                <div class="cipher-terminal-window" style="max-width:480px; margin:0 auto 1.5rem;">
                    <div id="cipher-target-token" style="font-size:2.5rem; font-weight:900; word-break:break-all;">...</div>
                </div>
                <div style="color:var(--text-muted); font-size:0.85rem;">Decrypt all sequential tokens to breach security clearance.</div>
            </div>
        `;
        this.loadNextCipherToken();

        this.objectiveCountdownTimer = setInterval(() => {
            if (this.isPaused) return;
            this.lockdownSeconds--;
            const clk = document.getElementById('cipher-lockdown-clk');
            if (clk) clk.textContent = `${this.lockdownSeconds}s`;
            if (this.lockdownSeconds <= 0) {
                this.finishGame(false, "Loss: Firewall lockdown timer expired. Root decryption halted.");
            }
        }, 1000);
    }

    loadNextCipherToken() {
        this.cipherTarget = this.layerTokens[this.tokenIdx % this.layerTokens.length] || "0x7FA9";
        this.cipherBuffer = "";
        const el = document.getElementById('cipher-target-token');
        if (el) el.innerHTML = `<span class="char untyped">${this.cipherTarget}</span>`;
    }

    // 6. FALLING WORDS
    initFallingWords() {
        this.lives = 3;
        this.viewport.innerHTML = `
            <div style="display:flex; justify-content:space-between; padding:12px 25px 0;">
                <span style="font-weight:700; color:var(--accent);">Flight Clock: <span id="fw-clock">${this.remainingSeconds}s</span></span>
                <span style="font-family:var(--font-mono); font-weight:800; color:var(--danger);">Lives: <span id="fw-lives-num">❤️❤️❤️</span></span>
            </div>
            <div class="danger-laser-line"></div>
        `;

        this.spawnFallingNode();
        this.spawnFallingNode();

        this.spawnTimer = setInterval(() => { if (!this.isPaused) this.spawnFallingNode(); }, 1800);
        this.gameLoopTimer = setInterval(() => { if (!this.isPaused) this.tickFallingNodes(); }, 40);

        this.objectiveCountdownTimer = setInterval(() => {
            if (this.isPaused) return;
            this.remainingSeconds--;
            const clk = document.getElementById('fw-clock');
            if (clk) clk.textContent = `${this.remainingSeconds}s`;
            if (this.remainingSeconds <= 0) {
                this.finishGame(true, `Victory! Survived orbital descent with ${this.score} pts!`);
            }
        }, 1000);
    }

    spawnFallingNode() {
        if (this.entities.length >= 6 || !this.isRunning) return;
        const word = this.contentBatch[Math.floor(Math.random() * this.contentBatch.length)] || "velocity";
        const el = document.createElement('div');
        el.className = 'falling-meteor-word';
        el.innerHTML = `<span class="char untyped">${word}</span>`;

        const availableWidth = Math.max(100, this.viewport.clientWidth - 160);
        const randomX = Math.floor(Math.random() * availableWidth) + 20;

        el.style.left = `${randomX}px`;
        el.style.top = '0px';
        this.viewport.appendChild(el);
        this.entities.push({ el, word, typed: '', y: 0, speed: 1.1 + Math.random() * 0.5 });
    }

    tickFallingNodes() {
        for (let i = this.entities.length - 1; i >= 0; i--) {
            const e = this.entities[i];
            e.y += e.speed;
            e.el.style.top = `${e.y}px`;
            if (e.y >= this.viewport.clientHeight - 55) {
                e.el.remove();
                this.entities.splice(i, 1);
                if (this.activeTarget === e) this.activeTarget = null;
                this.lives--;
                this.registerError();
                const lEl = document.getElementById('fw-lives-num');
                if (lEl) lEl.textContent = "❤️".repeat(Math.max(0, this.lives)) || "☠️";

                if (this.lives <= 0) {
                    this.finishGame(false, "Loss: Defense barrier breached. All lives lost.");
                    break;
                }
            }
        }
    }

    // 7. ZOMBIE DEFENSE
    initZombieDefense() {
        this.baseHP = 100;
        this.viewport.innerHTML = `
            <div style="position:absolute; right:35px; top:0; bottom:0; width:6px; background:var(--accent); opacity:0.75; box-shadow:0 0 12px var(--accent);"></div>
            <div style="display:flex; justify-content:space-between; padding:12px 25px 0; width:calc(100% - 50px);">
                <span style="font-weight:700; color:var(--accent);">Time: <span id="zd-clock">${this.remainingSeconds}s</span></span>
                <span style="font-family:var(--font-mono); font-weight:800; color:var(--warning);">Base Barrier: <span id="defense-hp">100%</span></span>
            </div>
        `;

        this.spawnZombieDefenseUnit();

        this.spawnTimer = setInterval(() => { if (!this.isPaused) this.spawnZombieDefenseUnit(); }, 2100);
        this.gameLoopTimer = setInterval(() => { if (!this.isPaused) this.tickZombieDefense(); }, 45);

        this.objectiveCountdownTimer = setInterval(() => {
            if (this.isPaused) return;
            this.remainingSeconds--;
            const clk = document.getElementById('zd-clock');
            if (clk) clk.textContent = `${this.remainingSeconds}s`;
            if (this.remainingSeconds <= 0) {
                this.finishGame(true, `Victory! Perimeter held successfully with ${this.score} pts!`);
            }
        }, 1000);
    }

    spawnZombieDefenseUnit() {
        if (this.entities.length >= 6 || !this.isRunning) return;
        const word = this.contentBatch[Math.floor(Math.random() * this.contentBatch.length)] || "stalker";
        const el = document.createElement('div');
        el.className = 'zombie-walker-unit';
        el.innerHTML = `🧟 <span class="char untyped">${word}</span>`;

        const lane = Math.floor(Math.random() * 4);
        const yPos = 45 + (lane * 62);

        el.style.left = '0px';
        el.style.top = `${yPos}px`;
        this.viewport.appendChild(el);
        this.entities.push({ el, word, typed: '', x: 0, speed: 1.1 + Math.random() * 0.8 });
    }

    tickZombieDefense() {
        for (let i = this.entities.length - 1; i >= 0; i--) {
            const z = this.entities[i];
            z.x += z.speed;
            z.el.style.left = `${z.x}px`;
            if (z.x >= this.viewport.clientWidth - 110) {
                z.el.remove();
                this.entities.splice(i, 1);
                this.baseHP -= 20;
                const hpEl = document.getElementById('defense-hp');
                if (hpEl) hpEl.textContent = `${Math.max(0, this.baseHP)}%`;
                this.registerError();
                if (this.baseHP <= 0) {
                    this.finishGame(false, "Loss: Perimeter breached. Base collapsed.");
                    break;
                }
            }
        }
    }

    // 8. SPACE DEFENDER
    initSpaceDefender() {
        this.shields = 100;
        this.viewport.innerHTML = `
            <div style="position:absolute; left:50%; top:50%; transform:translate(-50%, -50%); font-size:3rem;">🚀</div>
            <div style="display:flex; justify-content:space-between; padding:12px 25px 0;">
                <span style="font-weight:700; color:var(--accent);">Flight Clock: <span id="sd-clock">${this.remainingSeconds}s</span></span>
                <span style="font-family:var(--font-mono); font-weight:800; color:var(--success);">Shields: <span id="sd-shields">100%</span></span>
            </div>
        `;

        this.spawnAsteroidUnit();

        this.spawnTimer = setInterval(() => { if (!this.isPaused) this.spawnAsteroidUnit(); }, 2000);
        this.gameLoopTimer = setInterval(() => { if (!this.isPaused) this.tickAsteroids(); }, 40);

        this.objectiveCountdownTimer = setInterval(() => {
            if (this.isPaused) return;
            this.remainingSeconds--;
            const clk = document.getElementById('sd-clock');
            if (clk) clk.textContent = `${this.remainingSeconds}s`;
            if (this.remainingSeconds <= 0) {
                this.finishGame(true, `Victory! Defended starship through orbital sector!`);
            }
        }, 1000);
    }

    spawnAsteroidUnit() {
        if (this.entities.length >= 6 || !this.isRunning) return;
        const word = this.contentBatch[Math.floor(Math.random() * this.contentBatch.length)] || "orbit";
        const el = document.createElement('div');
        el.className = 'falling-meteor-word';
        el.innerHTML = `☄️ <span class="char untyped">${word}</span>`;

        const angle = Math.random() * Math.PI * 2;
        const radius = 220;
        const startX = (this.viewport.clientWidth / 2) + Math.cos(angle) * radius;
        const startY = (this.viewport.clientHeight / 2) + Math.sin(angle) * radius;

        el.style.left = `${startX}px`;
        el.style.top = `${startY}px`;
        this.viewport.appendChild(el);
        this.entities.push({ el, word, typed: '', x: startX, y: startY, angle, speed: 0.85 + Math.random() * 0.5 });
    }

    tickAsteroids() {
        const cx = this.viewport.clientWidth / 2;
        const cy = this.viewport.clientHeight / 2;
        for (let i = this.entities.length - 1; i >= 0; i--) {
            const a = this.entities[i];
            a.x -= Math.cos(a.angle) * a.speed;
            a.y -= Math.sin(a.angle) * a.speed;
            a.el.style.left = `${a.x}px`;
            a.el.style.top = `${a.y}px`;
            if (Math.hypot(cx - a.x, cy - a.y) < 35) {
                a.el.remove();
                this.entities.splice(i, 1);
                this.shields -= 25;
                const shld = document.getElementById('sd-shields');
                if (shld) shld.textContent = `${Math.max(0, this.shields)}%`;
                this.registerError();
                if (this.shields <= 0) {
                    this.finishGame(false, "Loss: Starship shields vaporized under asteroid bombardment.");
                    break;
                }
            }
        }
    }

    // 9. BOMB DEFUSE
    initBombDefuse() {
        this.bombSeconds = 40;
        this.bombStage = 0;
        this.maxStages = parseInt(this.config.objectiveVal) || 5;

        this.viewport.innerHTML = `
            <div style="text-align:center; padding-top:35px;">
                <div style="font-size:2.8rem; margin-bottom:0.2rem;">💣</div>
                <div style="font-weight:700; color:var(--text-muted); margin-bottom:0.4rem;">STAGE <span id="bomb-stg">1</span> / ${this.maxStages}</div>
                <div id="bomb-digital-clock" class="bomb-timer-display" style="font-size:3rem; font-family:var(--font-mono); font-weight:800; color:var(--danger);">00:40</div>
                <div id="bomb-code-box" style="margin:20px auto; max-width:440px; background:var(--bg-card); border:2px solid var(--accent); border-radius:8px; padding:1.25rem; font-family:var(--font-mono); font-size:1.8rem; letter-spacing:0.12em;">
                    INIT...
                </div>
            </div>
        `;
        this.spawnBombCode();
        this.objectiveCountdownTimer = setInterval(() => {
            if (this.isPaused) return;
            this.bombSeconds--;
            const el = document.getElementById('bomb-digital-clock');
            if (el) el.textContent = `00:${this.bombSeconds < 10 ? '0' : ''}${this.bombSeconds}`;
            if (this.bombSeconds <= 0) {
                this.finishGame(false, "Loss: Countdown reached 00:00. Detonation triggered.");
            }
        }, 1000);
    }

    spawnBombCode() {
        this.bombTarget = this.contentBatch[this.bombStage % this.contentBatch.length] || "ALPHA7";
        this.bombBuffer = "";
        const box = document.getElementById('bomb-code-box');
        if (box) box.innerHTML = `<span class="char untyped">${this.bombTarget}</span>`;
    }

    // 10. TYPING NINJA
    initTypingNinja() {
        this.ninjaMisses = 0;

        this.viewport.innerHTML = `
            <div style="display:flex; justify-content:space-between; padding:12px 25px 0;">
                <span style="font-weight:700; color:var(--accent);">Flight Clock: <span id="ninja-clk">${this.remainingSeconds}s</span></span>
                <span style="font-family:var(--font-mono); font-weight:800; color:var(--warning);">Misses: <span id="ninja-m">0</span> / 3</span>
            </div>
        `;

        this.spawnNinjaTarget();

        this.spawnTimer = setInterval(() => { if (!this.isPaused) this.spawnNinjaTarget(); }, 1900);
        this.gameLoopTimer = setInterval(() => { if (!this.isPaused) this.tickNinjaTargets(); }, 40);

        this.objectiveCountdownTimer = setInterval(() => {
            if (this.isPaused) return;
            this.remainingSeconds--;
            const clk = document.getElementById('ninja-clk');
            if (clk) clk.textContent = `${this.remainingSeconds}s`;
            if (this.remainingSeconds <= 0) {
                this.finishGame(true, `Victory! Completed slice run with ${this.score} pts!`);
            }
        }, 1000);
    }

    spawnNinjaTarget() {
        if (this.entities.length >= 6 || !this.isRunning) return;
        const word = this.contentBatch[Math.floor(Math.random() * this.contentBatch.length)] || "strike";
        const el = document.createElement('div');
        el.className = 'falling-meteor-word';
        el.innerHTML = `<span class="char untyped">${word}</span>`;

        const availableWidth = Math.max(100, this.viewport.clientWidth - 160);
        const startX = Math.floor(Math.random() * availableWidth) + 20;

        el.style.left = `${startX}px`;
        el.style.top = `${this.viewport.clientHeight - 40}px`;
        this.viewport.appendChild(el);
        this.entities.push({ el, word, typed: '', x: startX, y: this.viewport.clientHeight - 40, vy: -6.5 - Math.random() * 2.5, vx: (Math.random() - 0.5) * 2 });
    }

    tickNinjaTargets() {
        for (let i = this.entities.length - 1; i >= 0; i--) {
            const n = this.entities[i];
            n.vy += 0.16;
            n.y += n.vy;
            n.x += n.vx;
            n.el.style.top = `${n.y}px`;
            n.el.style.left = `${n.x}px`;
            if (n.y > this.viewport.clientHeight + 20) {
                n.el.remove();
                this.entities.splice(i, 1);
                if (this.activeTarget === n) this.activeTarget = null;
                this.ninjaMisses++;
                const mEl = document.getElementById('ninja-m');
                if (mEl) mEl.textContent = this.ninjaMisses;

                if (this.ninjaMisses >= 3) {
                    this.finishGame(false, "Loss: Allowed 3 targets to drop unsliced.");
                    break;
                }
            }
        }
    }

    // 11. MEMORY TYPE
    initMemoryType() {
        this.memoryIndex = 0;
        this.memoryStrikes = 0;

        this.viewport.innerHTML = `
            <div style="display:flex; justify-content:space-between; padding:12px 25px 0;">
                <span style="font-weight:700; color:var(--accent);">Time: <span id="mem-clk">${this.remainingSeconds}s</span></span>
                <span style="font-family:var(--font-mono); font-weight:800; color:var(--danger);">Strikes: <span id="mem-str">0</span> / 3</span>
            </div>
            <div style="text-align:center; padding-top:35px;">
                <span class="badge" style="background:var(--accent-glow); color:var(--accent); font-weight:800; padding:0.2rem 0.6rem; border-radius:4px;">RECALL DRILL</span>
                <div id="memory-box" style="margin:25px auto; max-width:440px; background:var(--bg-card); border:2px solid var(--accent); border-radius:8px; padding:2rem; font-family:var(--font-mono); font-size:2.5rem; letter-spacing:0.15em;">
                    READY
                </div>
                <div id="memory-hint" style="font-size:0.85rem; color:var(--text-muted);">Sequence flashes for 1.5 seconds...</div>
            </div>
        `;
        setTimeout(() => this.flashMemoryTarget(), 700);

        this.objectiveCountdownTimer = setInterval(() => {
            if (this.isPaused) return;
            this.remainingSeconds--;
            const clk = document.getElementById('mem-clk');
            if (clk) clk.textContent = `${this.remainingSeconds}s`;
            if (this.remainingSeconds <= 0) {
                this.finishGame(true, `Victory! Memory recall endurance mastered with ${this.score} pts!`);
            }
        }, 1000);
    }

    flashMemoryTarget() {
        if (!this.isRunning || this.isPaused) return;
        this.memoryTarget = this.contentBatch[this.memoryIndex % this.contentBatch.length] || "recall";
        const box = document.getElementById('memory-box');
        const hint = document.getElementById('memory-hint');
        if (!box) return;

        box.textContent = this.memoryTarget;
        box.style.color = "var(--text-primary)";
        if (hint) hint.textContent = "Memorize the sequence...";
        this.memoryBuffer = "";

        setTimeout(() => {
            if (!this.isRunning) return;
            box.textContent = "••••••••";
            box.style.color = "var(--accent)";
            if (hint) hint.textContent = "Type the sequence completely from mental recall!";
        }, 1500);
    }

    // 12. KEYBOARD QUEST
    initKeyboardQuest() {
        this.questIndex = 0;
        this.viewport.innerHTML = `
            <div style="display:flex; justify-content:space-between; padding:12px 25px 0;">
                <span style="font-weight:700; color:var(--accent);">Ergonomic Row Stream</span>
                <span style="font-family:var(--font-mono); font-weight:800; color:var(--warning);">Time: <span id="kq-clock">${this.remainingSeconds}s</span></span>
            </div>
            <div style="text-align:center; padding-top:35px;">
                <div id="quest-target-box" style="margin:20px auto; max-width:440px; background:var(--bg-card); border:2px solid var(--accent); border-radius:8px; padding:1.5rem; font-family:var(--font-mono); font-size:2.2rem; font-weight:800;">
                    ...
                </div>
                <div style="font-size:0.85rem; color:var(--text-muted);">Anchor palms on home-row. Execute cleanly.</div>
            </div>
        `;
        this.loadNextQuestTarget();

        this.objectiveCountdownTimer = setInterval(() => {
            if (this.isPaused) return;
            this.remainingSeconds--;
            const clk = document.getElementById('kq-clock');
            if (clk) clk.textContent = `${this.remainingSeconds}s`;
            if (this.remainingSeconds <= 0) {
                this.finishGame(true, `Victory! Completed ergonomic sequence stream with ${this.score} pts!`);
            }
        }, 1000);
    }

    loadNextQuestTarget() {
        this.questTarget = this.contentBatch[this.questIndex % this.contentBatch.length] || "asdf";
        this.questBuffer = "";
        const box = document.getElementById('quest-target-box');
        if (box) box.innerHTML = `<span class="char untyped">${this.questTarget}</span>`;
    }

    // ==========================================================
    // KEYSTROKE DISPATCHER
    // ==========================================================
    handleKeystroke(e) {
        if (!this.isRunning || this.isPaused) return;
        if (e.key === 'Backspace' && !this.config.backspaceAllowed) {
            e.preventDefault();
            return;
        }
        if (e.key.length !== 1 || e.ctrlKey || e.metaKey || e.altKey) return;
        e.preventDefault();

        const char = e.key;
        this.totalCharsTyped++;

        const elapsedMin = Math.max(0.01, (performance.now() - this.startTime) / 60000.0);
        const liveNetWpm = Math.round((this.correctCharsTyped / 5.0) / elapsedMin);

        // 1. SPEED RACER
        if (this.config.slug === 'speed_racer') {
            const expected = this.racerPassage[this.racerIdx];
            const spans = document.querySelectorAll('#racer-text-track .char');

            if (char === expected) {
                if (spans[this.racerIdx]) spans[this.racerIdx].className = 'char correct';
                this.racerIdx++;
                this.correctCharsTyped++;
                this.registerHit(10);
                this.playerDistanceMeters += 2.5;

                if (this.combo > 6) {
                    this.playerDistanceMeters += 1.5;
                    const nitro = document.getElementById('player-nitro');
                    if (nitro) nitro.style.display = 'block';
                }
            } else {
                if (spans[this.racerIdx]) spans[this.racerIdx].className = 'char incorrect';
                this.racerIdx++;
                this.playerDistanceMeters = Math.max(0, this.playerDistanceMeters - 1.2);
                const nitro = document.getElementById('player-nitro');
                if (nitro) nitro.style.display = 'none';
                this.registerError();
            }

            if (this.racerIdx < spans.length) {
                spans[this.racerIdx].className = 'char current';
                this.scrollRacerTextToActive(spans[this.racerIdx]);
            }

            const pct = Math.min(100, (this.playerDistanceMeters / this.targetDistanceMeters) * 100);
            this.updateSpeedRacerPosition('player', pct);
            this.syncProgressToServer(pct, liveNetWpm);

            if (pct >= 100) {
                this.finishGame(true, "Victory! You crossed the finish gate first!");
                return;
            }

            if (this.racerIdx >= this.racerPassage.length) {
                this.racerBatchIndex++;
                this.racerPassage = this.contentBatch[this.racerBatchIndex % this.contentBatch.length];
                this.racerIdx = 0;
                this.renderRacerSpans();
            }
            return;
        }

        // 2. BUBBLE POP
        if (this.config.slug === 'bubble_pop') {
            const match = this.entities.find(b => b.char === char);
            if (match) {
                match.el.remove();
                this.entities.splice(this.entities.indexOf(match), 1);
                this.correctCharsTyped++;
                this.registerHit(15);
                this.syncProgressToServer(0, liveNetWpm);
            } else {
                this.registerError();
            }
            return;
        }

        // 3. WHACK-A-WORD
        if (this.config.slug === 'whack_a_word') {
            const latency = performance.now() - this.lastActionTimestamp;
            this.reactionLatencies.push(latency);

            if (this.whackTarget.startsWith(this.whackBuffer + char)) {
                this.whackBuffer += char;
                this.correctCharsTyped++;
                this.registerHit(10);
                const hole = document.getElementById(`hole-${this.currentHole}`);
                if (hole) {
                    hole.innerHTML = `<span class="char correct">${this.whackBuffer}</span><span class="char untyped">${this.whackTarget.slice(this.whackBuffer.length)}</span>`;
                }

                if (this.whackBuffer === this.whackTarget) {
                    this.spawnNextMole();
                }
                this.syncProgressToServer(0, liveNetWpm);
            } else {
                this.registerError();
            }
            return;
        }

        // 4. ZOMBIE DUEL
        if (this.config.slug === 'zombie_duel') {
            if (this.duelTarget.startsWith(this.duelBuffer + char)) {
                this.duelBuffer += char;
                this.correctCharsTyped++;
                this.registerHit(15);
                const box = document.getElementById('duel-spell-box');
                if (box) {
                    box.innerHTML = `<span class="char correct">${this.duelBuffer}</span><span class="char untyped">${this.duelTarget.slice(this.duelBuffer.length)}</span>`;
                }

                if (this.duelBuffer === this.duelTarget) {
                    this.opponentHP = Math.max(0, this.opponentHP - 25);
                    const oppBar = document.getElementById('duel-opp-hp');
                    const oppLbl = document.getElementById('opp-hp-label');
                    if (oppBar) oppBar.style.width = `${this.opponentHP}%`;
                    if (oppLbl) oppLbl.textContent = `${this.opponentHP} / 100 HP`;

                    if (this.opponentHP <= 0) {
                        this.finishGame(true, "Victory! Knockout strike executed!");
                        return;
                    } else {
                        this.spawnDuelTarget();
                    }
                }
                this.syncProgressToServer(100 - this.opponentHP, liveNetWpm);
            } else {
                this.registerError();
            }
            return;
        }

        // 5. CIPHER HACKER
        if (this.config.slug === 'cipher_hacker') {
            if (this.cipherTarget.startsWith(this.cipherBuffer + char)) {
                this.cipherBuffer += char;
                this.correctCharsTyped++;
                this.registerHit(20);
                const tokenEl = document.getElementById('cipher-target-token');
                if (tokenEl) {
                    tokenEl.innerHTML = `<span class="char correct">${this.cipherBuffer}</span><span class="char untyped">${this.cipherTarget.slice(this.cipherBuffer.length)}</span>`;
                }

                if (this.cipherBuffer === this.cipherTarget) {
                    this.tokenIdx++;
                    if (this.tokenIdx >= this.layerTokens.length) {
                        this.currentLayer++;
                        if (this.currentLayer > this.totalLayers) {
                            this.finishGame(true, "Victory! Final root clearance decrypted. System breached!");
                            return;
                        }
                        this.tokenIdx = 0;
                        this.layerTokens = this.contentBatch[Math.min(this.contentBatch.length - 1, this.currentLayer - 1)];
                        const titleEl = document.getElementById('cipher-layer-title');
                        if (titleEl) titleEl.textContent = `SECURITY LAYER ${this.currentLayer} / ${this.totalLayers}`;
                    }
                    this.loadNextCipherToken();
                }
                this.syncProgressToServer(Math.round(((this.currentLayer - 1) / this.totalLayers) * 100), liveNetWpm);
            } else {
                this.registerError();
            }
            return;
        }

        // 6. BOMB DEFUSE
        if (this.config.slug === 'bomb_defuse') {
            if (this.bombTarget.startsWith(this.bombBuffer + char)) {
                this.bombBuffer += char;
                this.correctCharsTyped++;
                this.registerHit(15);
                const box = document.getElementById('bomb-code-box');
                if (box) {
                    box.innerHTML = `<span class="char correct">${this.bombBuffer}</span><span class="char untyped">${this.bombTarget.slice(this.bombBuffer.length)}</span>`;
                }

                if (this.bombBuffer === this.bombTarget) {
                    this.bombStage++;
                    if (this.bombStage >= this.maxStages) {
                        this.finishGame(true, "Victory! All sequence stages decrypted. Bomb safely defused!");
                        return;
                    }
                    const stgEl = document.getElementById('bomb-stg');
                    if (stgEl) stgEl.textContent = this.bombStage + 1;
                    this.spawnBombCode();
                }
                this.syncProgressToServer(0, liveNetWpm);
            } else {
                this.bombSeconds = Math.max(1, this.bombSeconds - 2);
                this.registerError();
            }
            return;
        }

        // 7. MEMORY TYPE
        if (this.config.slug === 'memory_type') {
            this.memoryBuffer += char;
            if (this.memoryTarget.startsWith(this.memoryBuffer)) {
                this.correctCharsTyped++;
                this.registerHit(20);
                if (this.memoryBuffer === this.memoryTarget) {
                    this.memoryIndex++;
                    this.flashMemoryTarget();
                }
                this.syncProgressToServer(0, liveNetWpm);
            } else {
                this.memoryStrikes++;
                const strEl = document.getElementById('mem-str');
                if (strEl) strEl.textContent = this.memoryStrikes;
                this.registerError();
                if (this.memoryStrikes >= 3) {
                    this.finishGame(false, "Loss: 3 sequence recall strikes reached.");
                    return;
                }
                this.flashMemoryTarget();
            }
            return;
        }

        // 8. KEYBOARD QUEST
        if (this.config.slug === 'keyboard_quest') {
            if (this.questTarget.startsWith(this.questBuffer + char)) {
                this.questBuffer += char;
                this.correctCharsTyped++;
                this.registerHit(15);
                const box = document.getElementById('quest-target-box');
                if (box) {
                    box.innerHTML = `<span class="char correct">${this.questBuffer}</span><span class="char untyped">${this.questTarget.slice(this.questBuffer.length)}</span>`;
                }

                if (this.questBuffer === this.questTarget) {
                    this.questIndex++;
                    this.loadNextQuestTarget();
                }
                this.syncProgressToServer(0, liveNetWpm);
            } else {
                this.registerError();
            }
            return;
        }

        // 9. FALLING WORDS, NINJA, SPACE DEFENDER, ZOMBIE DEFENSE
        const lower = char.toLowerCase();
        if (this.activeTarget) {
            const next = this.activeTarget.word[this.activeTarget.typed.length];
            if (lower === next) {
                this.activeTarget.typed += lower;
                this.correctCharsTyped++;
                this.registerHit(10);
                this.renderEntityTypedHighlight(this.activeTarget);

                if (this.activeTarget.typed === this.activeTarget.word) {
                    this.activeTarget.el.remove();
                    this.entities.splice(this.entities.indexOf(this.activeTarget), 1);
                    this.activeTarget = null;
                }
                this.syncProgressToServer(0, liveNetWpm);
                return;
            }
        }

        const match = this.entities.find(e => e.word.startsWith(lower));
        if (match) {
            this.activeTarget = match;
            this.activeTarget.typed = lower;
            this.correctCharsTyped++;
            this.registerHit(10);
            match.el.classList.add('target-locked');
            this.renderEntityTypedHighlight(match);
            this.syncProgressToServer(0, liveNetWpm);
        } else {
            this.registerError();
        }
    }

    renderEntityTypedHighlight(entity) {
        const prefix = (this.config.slug === 'zombie_defense') ? '🧟 ' : ((this.config.slug === 'space_defender') ? '☄️ ' : '');
        const typedPart = entity.word.substring(0, entity.typed.length);
        const remaining = entity.word.substring(entity.typed.length);
        entity.el.innerHTML = `${prefix}<span class="char correct">${typedPart}</span><span class="char untyped">${remaining}</span>`;
    }

    registerHit(pts) {
        this.combo++;
        if (this.combo > this.maxCombo) this.maxCombo = this.combo;
        const mult = 1 + Math.floor(this.combo / 7) * 0.25;
        this.score += Math.round(pts * mult);

        if (window.soundEngine) window.soundEngine.playKey(false);

        const elapsedMin = Math.max(0.01, (performance.now() - this.startTime) / 60000.0);
        const wpm = Math.round((this.correctCharsTyped / 5.0) / elapsedMin);
        this.updateHUD(this.score, this.combo, wpm);
    }

    registerError() {
        this.combo = 0;
        this.errors++;
        this.score = Math.max(0, this.score - 15); // Score recoil penalty

        if (window.soundEngine) window.soundEngine.playKey(true);

        const elapsedMin = Math.max(0.01, (performance.now() - this.startTime) / 60000.0);
        const wpm = Math.round((this.correctCharsTyped / 5.0) / elapsedMin);
        this.updateHUD(this.score, 0, wpm);
    }

    updateHUD(score, combo, wpm = 0) {
        const sEl = document.getElementById('live-my-stat');
        const cEl = document.getElementById('live-combo-badge');
        const wEl = document.getElementById('live-my-wpm');

        if (sEl) sEl.textContent = `${score} pts`;
        if (cEl) cEl.textContent = `${combo}x`;
        if (wEl) wEl.textContent = `${wpm} WPM`;
    }

    finishGame(didWin, summaryMessage) {
        this.stop();
        const duration = Math.max(1.0, (performance.now() - this.startTime) / 1000.0);
        const netWords = Math.max(0, (this.correctCharsTyped - this.errors) / 5.0);
        const wpm = duration > 0 ? Math.round((netWords / duration) * 60.0) : 0;
        const acc = this.totalCharsTyped > 0 ? Math.round((this.correctCharsTyped / this.totalCharsTyped) * 100.0) : 100;
        const outcome = didWin ? "WIN" : (this.config.playMode === 'solo_practice' ? "FINISHED" : "LOSS");

        const arenaEl = document.getElementById('game-active-arena');
        const resultsEl = document.getElementById('game-results-screen');
        if (arenaEl) arenaEl.style.display = 'none';
        if (resultsEl) resultsEl.style.display = 'block';

        // Snap window immediately to top so the results card is centered (Image 2 Fix)
        window.scrollTo({ top: 0, behavior: 'instant' });

        const badge = document.getElementById('res-outcome-badge');
        const trophy = document.getElementById('res-trophy-symbol');
        const title = document.getElementById('res-headline-title');
        const note = document.getElementById('res-motivational-text');

        if (badge) {
            badge.textContent = outcome;
            if (outcome === 'WIN') {
                badge.style.background = 'var(--success-bg)';
                badge.style.color = 'var(--success)';
            } else if (outcome === 'LOSS') {
                badge.style.background = 'var(--danger-bg)';
                badge.style.color = 'var(--danger)';
            } else {
                badge.style.background = 'var(--accent-glow)';
                badge.style.color = 'var(--accent)';
            }
        }

        if (trophy) trophy.textContent = outcome === 'WIN' ? '🏆' : (outcome === 'LOSS' ? '❌' : '🏁');
        if (title) title.textContent = outcome === 'WIN' ? 'Objective Mastered!' : (outcome === 'LOSS' ? 'Defeat — Recalibrate & Re-engage!' : 'Discipline Concluded');
        if (note) note.textContent = summaryMessage;

        const resScore = document.getElementById('res-score');
        const resWpm = document.getElementById('res-wpm');
        const resAcc = document.getElementById('res-acc');
        const resErr = document.getElementById('res-errors');
        const resCombo = document.getElementById('res-combo');

        if (resScore) resScore.textContent = this.score;
        if (resWpm) resWpm.textContent = `${wpm} WPM`;
        if (resAcc) resAcc.textContent = `${acc}%`;
        if (resErr) resErr.textContent = this.errors;
        if (resCombo) resCombo.textContent = `${this.maxCombo}x`;

        const specBox = document.getElementById('res-specific-stats');
        const avgReaction = this.reactionLatencies.length 
            ? Math.round(this.reactionLatencies.reduce((a, b) => a + b, 0) / this.reactionLatencies.length) 
            : 0;

        if (specBox) {
            specBox.innerHTML = `
                <div style="display:flex; justify-content:space-between;"><span>Flight Discipline:</span><strong>${this.config.slug.replace('_', ' ').toUpperCase()}</strong></div>
                <div style="display:flex; justify-content:space-between;"><span>Difficulty Tier:</span><strong>${this.config.difficulty.toUpperCase()}</strong></div>
                <div style="display:flex; justify-content:space-between;"><span>Session Duration:</span><strong>${Math.round(duration)}s</strong></div>
                ${avgReaction > 0 ? `<div style="display:flex; justify-content:space-between;"><span>Mean Strike Latency:</span><strong style="color:var(--warning);">${avgReaction}ms</strong></div>` : ''}
            `;
        }

        fetch('/games/api/submit-score', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                game_mode: this.config.slug,
                play_type: this.config.playMode,
                outcome: outcome,
                score: this.score,
                net_wpm: wpm,
                accuracy: acc,
                errors: this.errors,
                highest_combo: this.maxCombo,
                reaction_ms: avgReaction,
                duration: duration
            })
        }).catch(() => {});
    }
}

window.arcadeEngine = new ArcadeRuntimeEngine();