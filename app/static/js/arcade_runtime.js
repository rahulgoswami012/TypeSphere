/**
 * TypeSphere Arcade Unified Client Runtime Engine
 * 
 * Drives all 12 educational typing games with:
 * - Speed Racer forward momentum & mistake recoil (never stuck on typos)
 * - Single-character Bubble Pop
 * - 3x3 Whack-A-Word spatial reactions
 * - Zombie Defense (waves) vs Zombie Duel (1v1 HP combat)
 * - Multi-layer Cipher Hacker
 * - Space Defender, Bomb Defuse, Typing Ninja, Memory Type, Keyboard Quest
 * - Definite WIN, LOSS, or DRAW evaluation
 */
class ArcadeRuntimeEngine {
  constructor() {
    this.viewport = null;
    this.config = {};
    this.socket = null;
    
    // Core Session Metrics
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
    this.contentBatch = [];

    this.keydownHandler = (e) => this.handleKeystroke(e);
  }

  start(config) {
    this.stop();
    this.config = config;
    this.viewport = document.getElementById('arcade-viewport');
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
    this.startTime = performance.now();
    this.lastActionTimestamp = this.startTime;

    this.updateHUD(0, 0);
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
    window.removeEventListener('keydown', this.keydownHandler);
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
  }

  getFallbackBatch(slug, diff, charMode) {
    const common = ["velocity", "cadence", "rhythm", "kinetic", "precision", "matrix", "stream", "quantum", "tactile", "circuit", "binary", "system", "engine", "pilot", "balance", "command", "transit", "standard", "channel", "motion", "action", "focus"];
    if (slug === 'speed_racer') {
      return ["The open highway stretched across the desert floor under a wide expanse of pale morning sky. High velocity demands relaxed control and steady breathing. When the throttle opens every second compounds into pure forward momentum."];
    }
    if (slug === 'bubble_pop') {
      const sets = {
        'uppercase': [..."ABCDEFGHIJKLMNOPQRSTUVWXYZ"],
        'numbers': [..."0123456789"],
        'symbols': [..."!@#$%^&*()-_=+[]{}|;:,.<>?/"],
        'punctuation': [...".,;:!?'\"-()"]
      };
      return sets[charMode] || [..."abcdefghijklmnopqrstuvwxyz"];
    }
    if (slug === 'cipher_hacker') {
      return [["0x7FA9", "0xDE4B", "0x91C0"], ["AES_256", "SHA_512", "TLS_13"], ["chmod 755", "int main()"], ["0xFF00AA55BB66CC77"]];
    }
    if (slug === 'bomb_defuse') {
      return ["ALPHA78", "DELTA94", "OMEGA12", "BRAVO33", "HAZARD8", "VECTOR0"];
    }
    if (slug === 'memory_type') {
      return ["recall", "phantom", "quantum", "horizon", "velocity", "kinetic", "matrix"];
    }
    if (slug === 'keyboard_quest') {
      return ["asdf", "jkl;", "glad", "flask", "half", "fall", "quiet", "write", "power", "tower", "cabin", "zinc", "calm"];
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
      }
    });

    this.socket.on('arcade_live_telemetry', (data) => {
      const players = data.players || {};
      const ai = players['ai_bot'];
      if (ai) {
        document.getElementById('live-opp-stat').textContent = `${Math.round(ai.score)} pts`;
        document.getElementById('live-opp-wpm').textContent = `${Math.round(ai.wpm)} WPM`;
        if (this.config.slug === 'speed_racer') {
          this.updateSpeedRacerPosition('bot', ai.progress);
        }
      }
    });

    if (this.config.playMode === 'solo_ai') {
      this.aiLoopTimer = setInterval(() => {
        if (this.socket && this.isRunning) {
          this.socket.emit('arcade_ai_tick', { delta: 0.25, total_chars: 280 });
        }
      }, 250);
    }
  }

  initGameMode(slug) {
    switch (slug) {
      case 'speed_racer': this.initSpeedRacer(); break;
      case 'falling_words': this.initFallingWords(); break;
      case 'bubble_pop': this.initBubblePop(); break;
      case 'whack_a_word': this.initWhackAWord(); break;
      case 'zombie_defense': this.initZombieDefense(); break;
      case 'zombie_duel': this.initZombieDuel(); break;
      case 'cipher_hacker': this.initCipherHacker(); break;
      case 'space_defender': this.initSpaceDefender(); break;
      case 'bomb_defuse': this.initBombDefuse(); break;
      case 'typing_ninja': this.initTypingNinja(); break;
      case 'memory_type': this.initMemoryType(); break;
      case 'keyboard_quest': this.initKeyboardQuest(); break;
      default: this.initFallingWords();
    }
  }

  // ==========================================================
  // 1. SPEED RACER: Forward Acceleration + Recoil Without Sticking
  // ==========================================================
  initSpeedRacer() {
    const isMultiplayer = (this.config.playMode !== 'solo_ai' && this.config.playMode !== 'solo_practice');
    const oppIcon = isMultiplayer ? "🏎️" : "🤖";
    const oppLabel = isMultiplayer ? "Opponent" : "CyberBot (AI)";

    this.viewport.innerHTML = `
      <div class="racer-track-surface"></div>
      <div class="racer-lane-divider" style="top:33%;"></div>
      <div class="racer-lane-divider" style="top:66%;"></div>
      <div class="racer-finish-gate"></div>

      <!-- Player Car -->
      <div id="car-player" class="racer-vehicle-node" style="top:75px; left:25px;">
        <div class="racer-vehicle-icon" style="filter:drop-shadow(0 4px 10px rgba(56,189,248,0.8));">🏎️</div>
        <div class="racer-hud-tag" style="border-color:var(--accent); color:var(--accent);">You</div>
        <div id="player-nitro" class="nitro-exhaust-burn" style="display:none;"></div>
      </div>

      <!-- Opponent Car -->
      <div id="car-bot" class="racer-vehicle-node" style="top:210px; left:25px; ${this.config.playMode === 'solo_practice' ? 'display:none;' : ''}">
        <div class="racer-vehicle-icon" style="${isMultiplayer ? 'filter:drop-shadow(0 4px 10px rgba(244,63,94,0.8));' : ''}">${oppIcon}</div>
        <div class="racer-hud-tag" style="border-color:var(--warning); color:var(--warning);">${oppLabel}</div>
      </div>

      <div id="racer-text-track" style="position:absolute; bottom:15px; left:25px; right:25px; background:rgba(19,25,36,0.96); padding:1rem 1.4rem; border-radius:8px; border:1px solid var(--border-color); font-family:var(--font-mono); font-size:1.25rem; line-height:2.1; box-shadow:0 10px 25px rgba(0,0,0,0.6);"></div>
    `;

    this.racerPassage = this.contentBatch[0] || "Speed is nothing without precision. Keep your hands balanced, breathe calmly, and glide across the keys with absolute rhythm.";
    this.racerIdx = 0;
    this.playerDistanceMeters = 0;
    this.targetDistanceMeters = parseInt(this.config.objectiveVal) || 500;
    this.renderRacerSpans();
  }

  renderRacerSpans() {
    const box = document.getElementById('racer-text-track');
    if (!box) return;
    box.innerHTML = '';
    for (let i = 0; i < this.racerPassage.length; i++) {
      const s = document.createElement('span');
      s.className = 'char';
      s.textContent = this.racerPassage[i];
      box.appendChild(s);
    }
  }

  updateSpeedRacerPosition(target, pct) {
    const maxPixels = this.viewport.clientWidth - 110;
    const offset = Math.max(25, (pct / 100.0) * maxPixels);
    const car = document.getElementById(target === 'player' ? 'car-player' : 'car-bot');
    if (car) car.style.left = `${offset}px`;
  }

  // ==========================================================
  // 2. BUBBLE POP: Single Character Master
  // ==========================================================
  initBubblePop() {
    this.viewport.innerHTML = `
      <div style="position:absolute; top:35px; left:0; right:0; height:2px; background:var(--danger); opacity:0.6;"></div>
    `;
    this.bubbleLives = 3;
    this.spawnTimer = setInterval(() => this.spawnCharBubble(), 1200);
    this.gameLoopTimer = setInterval(() => this.tickBubbles(), 40);
  }

  spawnCharBubble() {
    if (this.entities.length >= 10 || !this.isRunning) return;
    const char = this.contentBatch[Math.floor(Math.random() * this.contentBatch.length)] || 'a';
    const el = document.createElement('div');
    el.className = 'arcade-char-bubble';
    el.textContent = char;
    el.style.left = `${Math.random() * (this.viewport.clientWidth - 70) + 15}px`;
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
          this.finishGame(false, "Loss: Allowed 3 bubbles to cross the ceiling barrier.");
          break;
        }
      }
    }
  }

  // ==========================================================
  // 3. WHACK-A-WORD: 3x3 Reaction Grid
  // ==========================================================
  initWhackAWord() {
    this.viewport.innerHTML = `
      <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:1rem; max-width:620px; margin:40px auto;">
        ${[0,1,2,3,4,5,6,7,8].map(i => `
          <div id="hole-${i}" style="height:90px; background:var(--bg-card); border:2px solid var(--border-color); border-radius:8px; display:flex; align-items:center; justify-content:center; font-family:var(--font-mono); font-weight:800; font-size:1.15rem; color:var(--text-muted);"></div>
        `).join('')}
      </div>
    `;
    this.whackTarget = "";
    this.whackBuffer = "";
    this.currentHole = -1;
    this.missedHoles = 0;
    this.spawnNextMole();
  }

  spawnNextMole() {
    if (this.moleWindowTimer) clearTimeout(this.moleWindowTimer);
    if (!this.isRunning) return;

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
      hole.textContent = this.whackTarget;
      hole.style.borderColor = 'var(--accent)';
      hole.style.color = 'var(--text-primary)';
    }

    const windowMs = {'easy': 2400, 'moderate': 1800, 'hard': 1300, 'expert': 900}[this.config.difficulty] || 1800;
    this.moleWindowTimer = setTimeout(() => {
      this.missedHoles++;
      this.registerError();
      if (this.missedHoles >= 5) {
        this.finishGame(false, "Loss: Missed 5 reaction windows.");
      } else {
        this.spawnNextMole();
      }
    }, windowMs);
  }

  // ==========================================================
  // 4. ZOMBIE DUEL: 1v1 Combat HP Battle
  // ==========================================================
  initZombieDuel() {
    this.playerHP = 100;
    this.opponentHP = 100;
    const oppName = (this.config.playMode === 'solo_ai') ? "CyberZombie (AI)" : "Opponent";

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
          <div style="font-size:1.6rem;"><strong style="font-size:1.05rem; color:var(--danger);">${oppName}</strong> 🧟</div>
          <div class="duel-hp-bar-container">
            <div id="duel-opp-hp" class="duel-hp-fill" style="width:100%; background:var(--danger);"></div>
          </div>
          <span id="opp-hp-label" style="font-family:var(--font-mono); font-size:0.8rem;">100 / 100 HP</span>
        </div>
      </div>

      <div style="text-align:center; margin-top:35px;">
        <div style="font-size:0.85rem; text-transform:uppercase; color:var(--text-muted); font-weight:700;">Strike Spell Word:</div>
        <div id="duel-spell-box" style="font-family:var(--font-mono); font-size:2.6rem; font-weight:900; color:var(--text-primary); margin:12px 0;">ATTACK</div>
      </div>
    `;
    this.spawnDuelTarget();

    // AI periodic counter-attack
    if (this.config.playMode === 'solo_ai') {
      const intervalMs = {'easy': 3800, 'moderate': 2800, 'hard': 1900, 'expert': 1300}[this.config.difficulty] || 2800;
      this.aiLoopTimer = setInterval(() => {
        if (!this.isRunning) return;
        this.playerHP = Math.max(0, this.playerHP - 15);
        document.getElementById('duel-player-hp').style.width = `${this.playerHP}%`;
        document.getElementById('player-hp-label').textContent = `${this.playerHP} / 100 HP`;
        if (window.soundEngine) window.soundEngine.playKey(true);

        if (this.playerHP <= 0) {
          this.finishGame(false, "Loss: Your combat barrier collapsed under attack.");
        }
      }, intervalMs);
    }
  }

  spawnDuelTarget() {
    this.duelTarget = this.contentBatch[Math.floor(Math.random() * this.contentBatch.length)] || "strike";
    this.duelBuffer = "";
    document.getElementById('duel-spell-box').textContent = this.duelTarget;
  }

  // ==========================================================
  // 5. CIPHER HACKER: Multi-Layer Security Breach
  // ==========================================================
  initCipherHacker() {
    this.currentLayer = 1;
    this.totalLayers = parseInt(this.config.objectiveVal) || 3;
    this.layerTokens = this.contentBatch[0] || ["0x7FA9", "0xDE4B", "0x91C0"];
    this.tokenIdx = 0;

    this.viewport.innerHTML = `
      <div style="text-align:center; padding-top:40px;">
        <div class="cipher-layer-badge" id="cipher-layer-title">SECURITY LAYER 1 / ${this.totalLayers}</div>
        <div class="cipher-terminal-window" style="max-width:480px; margin:0 auto 1.5rem;">
          <div id="cipher-target-token" style="font-size:2.5rem; font-weight:900; color:#10b981; word-break:break-all;">...</div>
        </div>
        <div style="color:var(--text-muted); font-size:0.85rem;">Decrypt all tokens to breach clearance.</div>
      </div>
    `;
    this.loadNextCipherToken();
  }

  loadNextCipherToken() {
    this.cipherTarget = this.layerTokens[this.tokenIdx % this.layerTokens.length] || "0x7FA9";
    this.cipherBuffer = "";
    document.getElementById('cipher-target-token').textContent = this.cipherTarget;
  }

  // ==========================================================
  // 6. FALLING WORDS
  // ==========================================================
  initFallingWords() {
    this.viewport.innerHTML = `
      <div style="position:absolute; bottom:40px; left:0; right:0; height:2px; background:var(--danger); opacity:0.6;"></div>
    `;
    this.wave = 1;
    this.maxWaves = parseInt(this.config.objectiveVal) || 5;
    this.spawnTimer = setInterval(() => this.spawnFallingNode(), 1800);
    this.gameLoopTimer = setInterval(() => this.tickFallingNodes(), 40);
  }

  spawnFallingNode() {
    if (this.entities.length >= 7 || !this.isRunning) return;
    const word = this.contentBatch[Math.floor(Math.random() * this.contentBatch.length)] || "velocity";
    const el = document.createElement('div');
    el.className = 'falling-meteor-word';
    el.textContent = word;
    el.style.left = `${Math.random() * (this.viewport.clientWidth - 130) + 15}px`;
    el.style.top = '0px';
    this.viewport.appendChild(el);
    this.entities.push({ el, word, typed: '', y: 0, speed: 1.1 + (this.wave * 0.2) });
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
        this.registerError();
      }
    }
  }

  // ==========================================================
  // 7. ZOMBIE DEFENSE (Wave Base Survival)
  // ==========================================================
  initZombieDefense() {
    this.baseHP = 100;
    this.viewport.innerHTML = `
      <div style="position:absolute; right:35px; top:0; bottom:0; width:6px; background:var(--accent); opacity:0.7;"></div>
      <div style="position:absolute; right:50px; top:20px; font-family:var(--font-mono); font-weight:800; color:var(--accent);">
        Base Barrier: <span id="defense-hp">100%</span>
      </div>
    `;
    this.spawnTimer = setInterval(() => this.spawnZombieDefenseUnit(), 2100);
    this.gameLoopTimer = setInterval(() => this.tickZombieDefense(), 45);
  }

  spawnZombieDefenseUnit() {
    if (this.entities.length >= 6 || !this.isRunning) return;
    const word = this.contentBatch[Math.floor(Math.random() * this.contentBatch.length)] || "stalker";
    const el = document.createElement('div');
    el.className = 'falling-meteor-word';
    el.innerHTML = `🧟 <span>${word}</span>`;
    el.style.left = '0px';
    el.style.top = `${Math.random() * (this.viewport.clientHeight - 70) + 15}px`;
    el.style.borderColor = 'var(--danger)';
    this.viewport.appendChild(el);
    this.entities.push({ el, word, typed: '', x: 0, speed: 1.1 + Math.random() * 0.8 });
  }

  tickZombieDefense() {
    for (let i = this.entities.length - 1; i >= 0; i--) {
      const z = this.entities[i];
      z.x += z.speed;
      z.el.style.left = `${z.x}px`;
      if (z.x >= this.viewport.clientWidth - 100) {
        z.el.remove();
        this.entities.splice(i, 1);
        this.baseHP -= 20;
        document.getElementById('defense-hp').textContent = `${Math.max(0, this.baseHP)}%`;
        this.registerError();
        if (this.baseHP <= 0) {
          this.finishGame(false, "Loss: Perimeter breached. Base collapsed.");
          break;
        }
      }
    }
  }

  // ==========================================================
  // 8. SPACE DEFENDER
  // ==========================================================
  initSpaceDefender() {
    this.viewport.innerHTML = `
      <div style="position:absolute; left:50%; top:50%; transform:translate(-50%, -50%); font-size:3rem;">🚀</div>
    `;
    this.shields = 100;
    this.spawnTimer = setInterval(() => this.spawnAsteroidUnit(), 2000);
    this.gameLoopTimer = setInterval(() => this.tickAsteroids(), 40);
  }

  spawnAsteroidUnit() {
    if (this.entities.length >= 6 || !this.isRunning) return;
    const word = this.contentBatch[Math.floor(Math.random() * this.contentBatch.length)] || "orbit";
    const el = document.createElement('div');
    el.className = 'falling-meteor-word';
    el.innerHTML = `☄️ <span>${word}</span>`;

    const angle = Math.random() * Math.PI * 2;
    const radius = 230;
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
        this.registerError();
        if (this.shields <= 0) {
          this.finishGame(false, "Loss: Starship shields vaporized under asteroid barrage.");
          break;
        }
      }
    }
  }

  // ==========================================================
  // 9. BOMB DEFUSE
  // ==========================================================
  initBombDefuse() {
    this.bombSeconds = 40;
    this.viewport.innerHTML = `
      <div style="text-align:center; padding-top:40px;">
        <div style="font-size:3rem; margin-bottom:0.4rem;">💣</div>
        <div id="bomb-digital-clock" class="bomb-timer-display">00:40</div>
        <div id="bomb-code-box" style="margin:25px auto; max-width:440px; background:var(--bg-card); border:2px solid var(--accent); border-radius:8px; padding:1.25rem; font-family:var(--font-mono); font-size:1.8rem; letter-spacing:0.15em;">
          INIT...
        </div>
      </div>
    `;
    this.bombStage = 0;
    this.spawnBombCode();
    this.objectiveCountdownTimer = setInterval(() => {
      this.bombSeconds--;
      const el = document.getElementById('bomb-digital-clock');
      if (el) el.textContent = `00:${this.bombSeconds < 10 ? '0' : ''}${this.bombSeconds}`;
      if (this.bombSeconds <= 0) {
        this.finishGame(false, "Loss: Countdown reached 00:00. Bomb detonated.");
      }
    }, 1000);
  }

  spawnBombCode() {
    this.bombTarget = this.contentBatch[this.bombStage % this.contentBatch.length] || "ALPHA7";
    this.bombBuffer = "";
    document.getElementById('bomb-code-box').textContent = this.bombTarget;
  }

  // ==========================================================
  // 10. TYPING NINJA
  // ==========================================================
  initTypingNinja() {
    this.spawnTimer = setInterval(() => this.spawnNinjaTarget(), 2000);
    this.gameLoopTimer = setInterval(() => this.tickNinjaTargets(), 40);
  }

  spawnNinjaTarget() {
    if (this.entities.length >= 6 || !this.isRunning) return;
    const word = this.contentBatch[Math.floor(Math.random() * this.contentBatch.length)] || "strike";
    const el = document.createElement('div');
    el.className = 'falling-meteor-word';
    el.textContent = word;
    const startX = Math.random() * (this.viewport.clientWidth - 150) + 30;
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
      }
    }
  }

  // ==========================================================
  // 11. MEMORY TYPE
  // ==========================================================
  initMemoryType() {
    this.memoryIndex = 0;
    this.viewport.innerHTML = `
      <div style="text-align:center; padding-top:60px;">
        <span class="badge" style="background:var(--accent-glow); color:var(--accent); font-weight:800; padding:0.2rem 0.6rem; border-radius:4px;">RECALL DRILL</span>
        <div id="memory-box" style="margin:25px auto; max-width:440px; background:var(--bg-card); border:2px solid var(--accent); border-radius:8px; padding:2rem; font-family:var(--font-mono); font-size:2.5rem; letter-spacing:0.15em;">
          READY
        </div>
        <div id="memory-hint" style="font-size:0.85rem; color:var(--text-muted);">Sequence flashes for 1.5 seconds...</div>
      </div>
    `;
    setTimeout(() => this.flashMemoryTarget(), 800);
  }

  flashMemoryTarget() {
    if (!this.isRunning) return;
    this.memoryTarget = this.contentBatch[this.memoryIndex % this.contentBatch.length] || "recall";
    const box = document.getElementById('memory-box');
    const hint = document.getElementById('memory-hint');
    box.textContent = this.memoryTarget;
    box.style.color = "var(--text-primary)";
    hint.textContent = "Memorize the sequence...";
    this.memoryBuffer = "";

    setTimeout(() => {
      box.textContent = "••••••••";
      box.style.color = "var(--accent)";
      hint.textContent = "Type the sequence completely from recall!";
    }, 1500);
  }

  // ==========================================================
  // 12. KEYBOARD QUEST
  // ==========================================================
  initKeyboardQuest() {
    this.questIndex = 0;
    this.viewport.innerHTML = `
      <div style="text-align:center; padding-top:50px;">
        <span class="badge" style="background:var(--accent-glow); color:var(--accent); font-weight:800; padding:0.2rem 0.6rem; border-radius:4px;">QUEST STAGE 1</span>
        <div id="quest-target-box" style="margin:25px auto; max-width:440px; background:var(--bg-card); border:2px solid var(--accent); border-radius:8px; padding:1.75rem; font-family:var(--font-mono); font-size:2.2rem; font-weight:800;">
          ...
        </div>
        <div style="font-size:0.85rem; color:var(--text-muted);">Anchor palms on home-row. Strike cleanly.</div>
      </div>
    `;
    this.loadNextQuestTarget();
  }

  loadNextQuestTarget() {
    this.questTarget = this.contentBatch[this.questIndex % this.contentBatch.length] || "asdf";
    this.questBuffer = "";
    document.getElementById('quest-target-box').textContent = this.questTarget;
  }

  // ==========================================================
  // GLOBAL KEYSTROKE ROUTER (NO PERMANENT STICKING)
  // ==========================================================
  handleKeystroke(e) {
    if (!this.isRunning) return;
    if (e.key === 'Backspace' && !this.config.backspaceAllowed) {
      e.preventDefault();
      return;
    }
    if (e.key.length !== 1 || e.ctrlKey || e.metaKey || e.altKey) return;
    e.preventDefault();

    const char = e.key;
    this.totalCharsTyped++;

    // 1. SPEED RACER: Forward velocity on correct, Recoil penalty on typo (Never stuck!)
    if (this.config.slug === 'speed_racer') {
      const expected = this.racerPassage[this.racerIdx];
      const spans = document.querySelectorAll('#racer-text-track .char');

      if (char === expected) {
        if (spans[this.racerIdx]) spans[this.racerIdx].className = 'char correct';
        this.racerIdx++;
        this.correctCharsTyped++;
        this.registerHit(10);
        
        // Progress forward
        this.playerDistanceMeters += 2.5;
        if (this.combo > 8) {
          this.playerDistanceMeters += 1.5; // Nitro burst bonus
          document.getElementById('player-nitro').style.display = 'block';
        }
      } else {
        // ERROR: Register error, apply speed loss/recoil, but ADVANCE target so player never gets stuck!
        if (spans[this.racerIdx]) spans[this.racerIdx].className = 'char incorrect';
        this.racerIdx++; // Advances to next character immediately!
        this.playerDistanceMeters = Math.max(0, this.playerDistanceMeters - 1.2); // Controlled backward penalty
        const nitro = document.getElementById('player-nitro');
        if (nitro) nitro.style.display = 'none';
        this.registerError();
      }

      const pct = Math.min(100, (this.playerDistanceMeters / this.targetDistanceMeters) * 100);
      this.updateSpeedRacerPosition('player', pct);

      if (pct >= 100) {
        this.finishGame(true, "VICTORY! You crossed the finish line ahead of your opponent!");
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
        if (hole) hole.innerHTML = `<span style="color:var(--success); text-decoration:underline;">${this.whackBuffer}</span>${this.whackTarget.slice(this.whackBuffer.length)}`;

        if (this.whackBuffer === this.whackTarget) {
          this.spawnNextMole();
        }
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
        document.getElementById('duel-spell-box').innerHTML = `<span style="color:var(--success);">${this.duelBuffer}</span>${this.duelTarget.slice(this.duelBuffer.length)}`;

        if (this.duelBuffer === this.duelTarget) {
          this.opponentHP = Math.max(0, this.opponentHP - 25);
          document.getElementById('duel-opp-hp').style.width = `${this.opponentHP}%`;
          document.getElementById('opp-hp-label').textContent = `${this.opponentHP} / 100 HP`;
          if (this.opponentHP <= 0) {
            this.finishGame(true, "VICTORY! You knocked out your opponent in the duel!");
          } else {
            this.spawnDuelTarget();
          }
        }
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
        document.getElementById('cipher-target-token').innerHTML = `<span style="color:var(--accent);">${this.cipherBuffer}</span>${this.cipherTarget.slice(this.cipherBuffer.length)}`;

        if (this.cipherBuffer === this.cipherTarget) {
          this.tokenIdx++;
          if (this.tokenIdx >= this.layerTokens.length) {
            this.currentLayer++;
            if (this.currentLayer > this.totalLayers) {
              this.finishGame(true, "VICTORY! Final root clearance decrypted. System breached!");
              return;
            }
            this.tokenIdx = 0;
            this.layerTokens = this.contentBatch[Math.min(this.contentBatch.length - 1, this.currentLayer - 1)];
            document.getElementById('cipher-layer-title').textContent = `SECURITY LAYER ${this.currentLayer} / ${this.totalLayers}`;
          }
          this.loadNextCipherToken();
        }
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
        document.getElementById('bomb-code-box').innerHTML = `<span style="color:var(--success);">${this.bombBuffer}</span>${this.bombTarget.slice(this.bombBuffer.length)}`;

        if (this.bombBuffer === this.bombTarget) {
          this.bombStage++;
          if (this.bombStage >= parseInt(this.config.objectiveVal)) {
            this.finishGame(true, "VICTORY! All sequence stages decrypted. Bomb safely defused!");
            return;
          }
          this.spawnBombCode();
        }
      } else {
        this.bombSeconds = Math.max(1, this.bombSeconds - 2); // Error penalty
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
          if (this.memoryIndex >= parseInt(this.config.objectiveVal)) {
            this.finishGame(true, "VICTORY! You mastered all memory recall rounds!");
            return;
          }
          this.flashMemoryTarget();
        }
      } else {
        this.registerError();
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
        document.getElementById('quest-target-box').innerHTML = `<span style="color:var(--success);">${this.questBuffer}</span>${this.questTarget.slice(this.questBuffer.length)}`;

        if (this.questBuffer === this.questTarget) {
          this.questIndex++;
          this.loadNextQuestTarget();
        }
      } else {
        this.registerError();
      }
      return;
    }

    // 9. FALLING WORDS, NINJA SLICING, SPACE DEFENDER
    const lower = char.toLowerCase();
    if (this.activeTarget) {
      const next = this.activeTarget.word[this.activeTarget.typed.length];
      if (lower === next) {
        this.activeTarget.typed += lower;
        this.correctCharsTyped++;
        this.registerHit(10);
        this.activeTarget.el.innerHTML = `<span style="color:var(--success); text-decoration:underline;">${this.activeTarget.typed}</span>${this.activeTarget.word.slice(this.activeTarget.typed.length)}`;

        if (this.activeTarget.typed === this.activeTarget.word) {
          this.activeTarget.el.remove();
          this.entities.splice(this.entities.indexOf(this.activeTarget), 1);
          this.activeTarget = null;
        }
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
      match.el.innerHTML = `<span style="color:var(--success); text-decoration:underline;">${lower}</span>${match.word.slice(1)}`;
    } else {
      this.registerError();
    }
  }

  registerHit(pts) {
    this.combo++;
    if (this.combo > this.maxCombo) this.maxCombo = this.combo;
    const mult = 1 + Math.floor(this.combo / 7) * 0.25;
    this.score += Math.round(pts * mult);
    if (window.soundEngine) window.soundEngine.playKey(false);
    this.updateHUD(this.score, this.combo);
  }

  registerError() {
    this.combo = 0;
    this.errors++;
    if (window.soundEngine) window.soundEngine.playKey(true);
    this.updateHUD(this.score, 0);
  }

  updateHUD(score, combo) {
    const sEl = document.getElementById('live-my-stat');
    const cEl = document.getElementById('live-combo-badge');
    if (sEl) sEl.textContent = `${score} pts`;
    if (cEl) cEl.textContent = `${combo}x`;
  }

  finishGame(didWin, summaryMessage) {
    this.stop();
    const duration = Math.max(1.0, (performance.now() - this.startTime) / 1000.0);
    const netWords = Math.max(0, (this.correctCharsTyped - this.errors) / 5.0);
    const wpm = duration > 0 ? Math.round((netWords / duration) * 60.0) : 0;
    const acc = this.totalCharsTyped > 0 ? Math.round((this.correctCharsTyped / this.totalCharsTyped) * 100.0) : 100;
    const outcome = didWin ? "WIN" : (this.config.playMode === 'solo_practice' ? "FINISHED" : "LOSS");

    document.getElementById('game-active-arena').style.display = 'none';
    document.getElementById('game-results-screen').style.display = 'block';

    const badge = document.getElementById('res-outcome-badge');
    const trophy = document.getElementById('res-trophy-symbol');
    const title = document.getElementById('res-headline-title');
    const note = document.getElementById('res-motivational-text');

    badge.textContent = outcome;
    if (outcome === 'WIN') {
      badge.style.background = 'var(--success-bg)';
      badge.style.color = 'var(--success)';
      trophy.textContent = '🏆';
      title.textContent = 'Victory! Objective Mastered!';
      note.textContent = summaryMessage;
    } else if (outcome === 'LOSS') {
      badge.style.background = 'var(--danger-bg)';
      badge.style.color = 'var(--danger)';
      trophy.textContent = '❌';
      title.textContent = 'Defeat - Practice Makes Velocity!';
      note.textContent = summaryMessage;
    } else {
      badge.style.background = 'var(--accent-glow)';
      badge.style.color = 'var(--accent)';
      trophy.textContent = '🏁';
      title.textContent = 'Practice Concluded';
      note.textContent = summaryMessage;
    }

    document.getElementById('res-score').textContent = this.score;
    document.getElementById('res-wpm').textContent = `${wpm} WPM`;
    document.getElementById('res-acc').textContent = `${acc}%`;
    document.getElementById('res-errors').textContent = this.errors;
    document.getElementById('res-combo').textContent = `${this.maxCombo}x`;

    // Telemetry specifics
    const specBox = document.getElementById('res-specific-stats');
    const avgReaction = this.reactionLatencies.length 
      ? Math.round(this.reactionLatencies.reduce((a, b) => a + b, 0) / this.reactionLatencies.length) 
      : 0;
    
    specBox.innerHTML = `
      <div style="display:flex; justify-content:space-between;"><span>Game Discipline:</span><strong>${this.config.slug.replace('_', ' ').toUpperCase()}</strong></div>
      <div style="display:flex; justify-content:space-between;"><span>Difficulty Tier:</span><strong>${this.config.difficulty.toUpperCase()}</strong></div>
      <div style="display:flex; justify-content:space-between;"><span>Session Duration:</span><strong>${Math.round(duration)}s</strong></div>
      ${avgReaction > 0 ? `<div style="display:flex; justify-content:space-between;"><span>Mean Reaction Latency:</span><strong style="color:var(--warning);">${avgReaction}ms</strong></div>` : ''}
    `;

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