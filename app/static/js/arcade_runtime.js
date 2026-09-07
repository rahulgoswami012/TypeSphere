/**
 * TypeSphere Arcade Master Client Runtime
 * Drives physics, instant content fallbacks, Speed Racer cars, and all 12 games.
 */
class ArcadeRuntimeEngine {
  constructor() {
    this.viewport = null;
    this.activeGame = null;
    this.config = {};
    
    this.score = 0;
    this.errors = 0;
    this.combo = 0;
    this.maxCombo = 0;
    this.startTime = 0;
    this.totalStrokes = 0;
    this.correctStrokes = 0;
    
    this.entities = [];
    this.gameLoopInterval = null;
    this.aiTickInterval = null;
    this.spawnInterval = null;
    this.activeTarget = null;
    this.typedBuffer = "";
    
    this.socket = null;
    this.gameContent = [];
  }

  start(config) {
    this.config = config;
    this.activeGame = config.slug;
    this.viewport = document.getElementById('arcade-viewport');
    this.viewport.innerHTML = '';
    
    this.score = 0;
    this.errors = 0;
    this.combo = 0;
    this.maxCombo = 0;
    this.totalStrokes = 0;
    this.correctStrokes = 0;
    this.entities = [];
    this.typedBuffer = "";
    this.activeTarget = null;
    this.startTime = performance.now();

    // 1. Instant local content fallback so games never sit on "Fetching circuit data..."
    this.gameContent = this.getImmediateFallbackContent(config.slug, config.difficulty);
    
    this.updateScoreboard(0, 0);
    this.initSocket();
    this.initGameMode(config.slug);
    this.bindKeystrokes();
    this.viewport.focus();
  }

  stop() {
    clearInterval(this.gameLoopInterval);
    clearInterval(this.aiTickInterval);
    clearInterval(this.spawnInterval);
    if (this.socket) {
      this.socket.emit('arcade_disconnect');
    }
  }

  getImmediateFallbackContent(slug, diff) {
    const common = ["velocity", "cadence", "rhythm", "precision", "kinetic", "matrix", "stream", "quantum", "tactile", "circuit", "binary", "system", "engine", "pilot", "balance", "command", "transit", "standard", "channel", "motion", "action", "focus"];
    if (slug === 'speed_racer') {
      return ["The open highway stretched across the desert floor under a wide expanse of pale morning sky. High velocity demands relaxed control and steady breathing. When the throttle opens every second compounds into pure forward momentum."];
    }
    if (slug === 'bomb_defuse') {
      return ["ALPHA78", "BRAVO92", "DELTA14", "OMEGA99", "CODE804", "VECTOR51", "HAZARD88"];
    }
    if (slug === 'cipher_hacker') {
      return ["0x7FA9", "0xDE4B", "0x91C0", "PORT:443", "AES-256", "HASH#994", "0xAA12", "0xFF00"];
    }
    if (slug === 'memory_type') {
      return ["recall", "phantom", "quantum", "horizon", "velocity", "kinetic", "matrix"];
    }
    if (slug === 'keyboard_quest') {
      return ["asdf", "jkl;", "glad", "flask", "half", "fall", "quiet", "write", "power", "tower", "cabin", "zinc", "calm"];
    }
    return common;
  }

  initSocket() {
    if (!window.io) return;
    this.socket = io();
    
    this.socket.emit('arcade_init', {
      game_mode: this.config.slug,
      play_mode: this.config.playMode,
      difficulty: this.config.difficulty,
      ai_level: this.config.aiLevel,
      room_code: this.config.roomCode
    });

    this.socket.on('arcade_session_started', (data) => {
      if (data && data.content && data.content.length > 0) {
        this.gameContent = data.content;
        if (this.activeGame === 'speed_racer') {
          this.racerPassage = this.gameContent.join(" ");
          this.renderRacerPassage();
        }
      }
    });

    this.socket.on('arcade_sync_tick', (data) => {
      const players = data.players || {};
      const ai = players['ai_bot'];
      if (ai) {
        const oppScore = document.getElementById('live-opp-score');
        const oppWpm = document.getElementById('live-opp-wpm');
        if (oppScore) oppScore.textContent = `${ai.score} pts`;
        if (oppWpm) oppWpm.textContent = `${Math.round(ai.wpm)} WPM`;
        if (this.activeGame === 'speed_racer') {
          this.updateRacerPosition('bot', ai.progress);
        }
      }
    });

    if (this.config.playMode === 'solo_ai') {
      this.aiTickInterval = setInterval(() => {
        if (this.socket && this.socket.connected) {
          this.socket.emit('arcade_ai_tick', { delta: 0.25 });
        }
      }, 250);
    }
  }

  initGameMode(slug) {
    switch(slug) {
      case 'speed_racer': this.setupSpeedRacer(); break;
      case 'falling_words': this.setupFallingWords(); break;
      case 'bubble_pop': this.setupBubblePop(); break;
      case 'whack_a_word': this.setupWhackAWord(); break;
      case 'zombie_duel': this.setupZombieDuel(); break;
      case 'word_blitz': this.setupWordBlitz(); break;
      case 'cipher_hacker': this.setupCipherHacker(); break;
      case 'space_defender': this.setupSpaceDefender(); break;
      case 'bomb_defuse': this.setupBombDefuse(); break;
      case 'typing_ninja': this.setupTypingNinja(); break;
      case 'memory_type': this.setupMemoryType(); break;
      case 'keyboard_quest': this.setupKeyboardQuest(); break;
      default: this.setupFallingWords();
    }
  }

  // ==========================================
  // Game 1: Speed Racer (Fixed Cars, No Boxes, Flipped Direction)
  // ==========================================
  setupSpeedRacer() {
    const isSoloAI = (this.config.playMode === 'solo_ai');
    const playerLabel = "You";
    const opponentLabel = isSoloAI ? "CyberPilot (AI)" : (this.config.opponentName || "Opponent");
    const opponentIcon = isSoloAI ? "🤖" : "🏎️"; // In multiplayer between real players, BOTH use cars!

    this.viewport.innerHTML = `
      <div class="racer-lane-stripes"></div>
      
      <!-- Player Car: Enlarged, flipped forward, labeled as You without background box -->
      <div id="car-player" class="racer-car-entity" style="top:110px; left:20px;">
        <div class="racer-car-icon" style="filter: drop-shadow(0 4px 10px rgba(56,189,248,0.7));">🏎️</div>
        <div class="racer-pilot-label" style="border-color:var(--accent); color:var(--accent); font-weight:800;">${playerLabel}</div>
        <div id="player-nitro" class="nitro-flame" style="display:none;"></div>
      </div>

      <!-- Opponent Car: Labeled with name, flipped forward, no background box -->
      <div id="car-bot" class="racer-car-entity" style="top:220px; left:20px;">
        <div class="racer-car-icon" style="${!isSoloAI ? 'filter: drop-shadow(0 4px 10px rgba(244,63,94,0.7));' : ''}">${opponentIcon}</div>
        <div class="racer-pilot-label" style="border-color:var(--warning); color:var(--warning);">${opponentLabel}</div>
      </div>

      <!-- Finish Line -->
      <div style="position:absolute; right:20px; top:0; bottom:0; width:6px; background:repeating-linear-gradient(0deg,#fff,#fff 10px,#000 10px,#000 20px); z-index:3;"></div>
      
      <!-- Text Track Display -->
      <div id="racer-text-track" style="position:absolute; bottom:20px; left:25px; right:25px; background:rgba(19,25,36,0.96); padding:1.1rem 1.5rem; border-radius:8px; border:1px solid var(--border-color); font-family:var(--font-mono); font-size:1.25rem; line-height:2.1; box-shadow:0 10px 25px rgba(0,0,0,0.5);">
      </div>
    `;

    this.racerPassage = this.gameContent[0] || "Speed is nothing without precision. Keep your hands balanced, breathe calmly, and glide across the keys with absolute rhythm.";
    this.racerIdx = 0;
    this.renderRacerPassage();
  }

  renderRacerPassage() {
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

  updateRacerPosition(target, pct) {
    const maxPixels = this.viewport.clientWidth - 110;
    const offset = (pct / 100.0) * maxPixels;
    const car = document.getElementById(target === 'player' ? 'car-player' : 'car-bot');
    if (car) car.style.left = `${Math.max(20, offset)}px`;
  }

  // ==========================================
  // Game 2: Falling Words
  // ==========================================
  setupFallingWords() {
    this.viewport.innerHTML = `
      <div style="position:absolute; bottom:40px; left:0; right:0; height:2px; background:var(--danger); opacity:0.6;"></div>
    `;
    this.spawnInterval = setInterval(() => this.spawnFallingWord(), 2000);
    this.gameLoopInterval = setInterval(() => this.tickFallingWords(), 45);
  }

  spawnFallingWord() {
    if (this.entities.length >= 8) return;
    const word = this.gameContent[Math.floor(Math.random() * this.gameContent.length)];
    const el = document.createElement('div');
    el.className = 'falling-meteor-word';
    el.textContent = word;
    el.style.left = `${Math.random() * (this.viewport.clientWidth - 120) + 15}px`;
    el.style.top = '0px';
    this.viewport.appendChild(el);

    this.entities.push({ el, word, typed: '', y: 0, speed: 1.2 + Math.random() * 1.2 });
  }

  tickFallingWords() {
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

  // ==========================================
  // Game 3: Bubble Pop
  // ==========================================
  setupBubblePop() {
    this.viewport.innerHTML = `
      <div style="position:absolute; top:35px; left:0; right:0; height:2px; background:var(--danger); opacity:0.5;"></div>
    `;
    this.bubbleChars = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z"];
    this.spawnInterval = setInterval(() => this.spawnBubble(), 1400);
    this.gameLoopInterval = setInterval(() => this.tickBubbles(), 40);
  }

  spawnBubble() {
    if (this.entities.length >= 10) return;
    const char = this.bubbleChars[Math.floor(Math.random() * this.bubbleChars.length)];
    const el = document.createElement('div');
    el.className = 'arcade-char-bubble';
    el.textContent = char;
    el.style.left = `${Math.random() * (this.viewport.clientWidth - 70) + 15}px`;
    el.style.bottom = '0px';
    this.viewport.appendChild(el);

    this.entities.push({ el, char, y: 0, speed: 1.3 + Math.random() });
  }

  tickBubbles() {
    for (let i = this.entities.length - 1; i >= 0; i--) {
      const b = this.entities[i];
      b.y += b.speed;
      b.el.style.bottom = `${b.y}px`;

      if (b.y >= this.viewport.clientHeight - 60) {
        b.el.remove();
        this.entities.splice(i, 1);
        this.registerError();
      }
    }
  }

  // ==========================================
  // Game 4: Whack-A-Word
  // ==========================================
  setupWhackAWord() {
    this.viewport.innerHTML = `
      <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:1rem; max-width:620px; margin:40px auto;">
        ${[0,1,2,3,4,5,6,7,8].map(i => `
          <div id="hole-${i}" style="height:90px; background:var(--bg-card); border:2px solid var(--border-color); border-radius:8px; display:flex; align-items:center; justify-content:center; font-family:var(--font-mono); font-weight:800; font-size:1.15rem; color:var(--text-muted);"></div>
        `).join('')}
      </div>
    `;
    this.whackScore = 0;
    this.spawnNextMole();
  }

  spawnNextMole() {
    if (this.moleTimeout) clearTimeout(this.moleTimeout);
    if (this.currentHoleIdx !== undefined) {
      const prev = document.getElementById(`hole-${this.currentHoleIdx}`);
      if (prev) {
        prev.textContent = '';
        prev.style.borderColor = 'var(--border-color)';
        prev.style.background = 'var(--bg-card)';
      }
    }
    this.currentHoleIdx = Math.floor(Math.random() * 9);
    this.currentMoleWord = this.gameContent[Math.floor(Math.random() * this.gameContent.length)];
    this.moleTyped = "";

    const hole = document.getElementById(`hole-${this.currentHoleIdx}`);
    if (hole) {
      hole.textContent = this.currentMoleWord;
      hole.style.borderColor = 'var(--accent)';
      hole.style.color = 'var(--text-primary)';
    }

    this.moleTimeout = setTimeout(() => {
      this.registerError();
      this.spawnNextMole();
    }, 2500);
  }

  // ==========================================
  // Game 5: Zombie Duel (1v1 Combat HP Battle)
  // ==========================================
  setupZombieDuel() {
    this.playerHp = 100;
    this.opponentHp = 100;
    this.viewport.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center; padding:1.5rem 2rem;">
        <div style="text-align:left;">
          <div style="font-size:1.8rem;">🧙‍♂️ <strong style="font-size:1.1rem; color:var(--accent);">You</strong></div>
          <div style="background:var(--bg-card); width:180px; height:16px; border-radius:8px; overflow:hidden; border:1px solid var(--border-color); margin-top:0.4rem;">
            <div id="duel-player-hp" style="width:100%; height:100%; background:var(--success); transition:width 0.2s;"></div>
          </div>
        </div>

        <div style="font-size:2rem; font-weight:900; color:var(--warning);">VS</div>

        <div style="text-align:right;">
          <div style="font-size:1.8rem;"><strong style="font-size:1.1rem; color:var(--danger);">Opponent</strong> 🧟</div>
          <div style="background:var(--bg-card); width:180px; height:16px; border-radius:8px; overflow:hidden; border:1px solid var(--border-color); margin-top:0.4rem;">
            <div id="duel-opp-hp" style="width:100%; height:100%; background:var(--danger); transition:width 0.2s;"></div>
          </div>
        </div>
      </div>

      <div style="text-align:center; margin-top:40px;">
        <div style="font-size:0.8rem; text-transform:uppercase; color:var(--text-muted); font-weight:700;">Strike Spell Word:</div>
        <div id="duel-spell-word" style="font-family:var(--font-mono); font-size:2.4rem; font-weight:800; color:var(--text-primary); margin:10px 0;">
          ATTACK
        </div>
      </div>
    `;
    this.spawnDuelSpell();

    // AI opponent attacks every 3 seconds
    this.aiAttackTimer = setInterval(() => {
      if (this.playerHp <= 0 || this.opponentHp <= 0) return;
      this.playerHp = Math.max(0, this.playerHp - 15);
      const hpBar = document.getElementById('duel-player-hp');
      if (hpBar) hpBar.style.width = `${this.playerHp}%`;
      if (this.playerHp <= 0) {
        clearInterval(this.aiAttackTimer);
        this.concludeGame("Defeat! Your defense barrier collapsed under attack.");
      }
    }, 3200);
  }

  spawnDuelSpell() {
    this.duelTarget = this.gameContent[Math.floor(Math.random() * this.gameContent.length)];
    const el = document.getElementById('duel-spell-word');
    if (el) el.textContent = this.duelTarget;
    this.duelTyped = "";
  }

  // ==========================================
  // Game 6: Word Blitz (60s Frenzy)
  // ==========================================
  setupWordBlitz() {
    this.blitzRemaining = 60;
    this.viewport.innerHTML = `
      <div style="text-align:center; padding-top:50px;">
        <div style="font-size:0.9rem; text-transform:uppercase; color:var(--text-muted); font-weight:700;">60-Second Blitz Clock: <span id="blitz-clock" style="color:var(--danger);">60s</span></div>
        <div id="blitz-word-target" style="margin:25px auto; max-width:480px; background:var(--bg-card); border:2px solid var(--accent); border-radius:8px; padding:2rem; font-family:var(--font-mono); font-size:3rem; font-weight:900; letter-spacing:0.08em;">
          BLITZ
        </div>
      </div>
    `;
    this.spawnBlitzWord();
    this.spawnInterval = setInterval(() => {
      this.blitzRemaining--;
      const clk = document.getElementById('blitz-clock');
      if (clk) clk.textContent = `${this.blitzRemaining}s`;
      if (this.blitzRemaining <= 0) {
        this.concludeGame(`Time up! Word Blitz completed with ${this.score} points.`);
      }
    }, 1000);
  }

  spawnBlitzWord() {
    this.blitzTarget = this.gameContent[Math.floor(Math.random() * this.gameContent.length)];
    const el = document.getElementById('blitz-word-target');
    if (el) el.textContent = this.blitzTarget.toUpperCase();
    this.blitzTyped = "";
  }

  // ==========================================
  // Game 7: Cipher Hacker
  // ==========================================
  setupCipherHacker() {
    this.cipherTime = 35;
    this.viewport.innerHTML = `
      <div style="text-align:center; padding-top:40px;">
        <div style="color:var(--success); font-family:var(--font-mono); font-size:1.1rem; margin-bottom:10px;">// SYSTEM CIPHER DECRYPTION MATRIX</div>
        <div id="cipher-code-display" style="margin:15px auto; max-width:460px; background:#05050d; border:2px solid var(--success); border-radius:8px; padding:1.75rem; font-family:var(--font-mono); font-size:2.4rem; font-weight:800; color:var(--success);">
          0x7FA9
        </div>
        <div style="color:var(--text-muted); font-size:0.85rem;">Security lockdown in: <span id="cipher-timer" style="color:var(--danger); font-weight:700;">35s</span></div>
      </div>
    `;
    this.spawnCipherTarget();
    this.spawnInterval = setInterval(() => {
      this.cipherTime--;
      const el = document.getElementById('cipher-timer');
      if (el) el.textContent = `${this.cipherTime}s`;
      if (this.cipherTime <= 0) {
        this.concludeGame("Security lockdown triggered! Terminal intrusion failed.");
      }
    }, 1000);
  }

  spawnCipherTarget() {
    this.cipherTarget = this.gameContent[Math.floor(Math.random() * this.gameContent.length)];
    const el = document.getElementById('cipher-code-display');
    if (el) el.textContent = this.cipherTarget;
    this.cipherTyped = "";
  }

  // ==========================================
  // Game 8: Space Defender
  // ==========================================
  setupSpaceDefender() {
    this.viewport.innerHTML = `
      <div style="position:absolute; left:50%; top:50%; transform:translate(-50%, -50%); font-size:2.8rem;">🚀</div>
    `;
    this.spawnInterval = setInterval(() => this.spawnAsteroid(), 2200);
    this.gameLoopInterval = setInterval(() => this.tickSpaceDefender(), 45);
  }

  spawnAsteroid() {
    if (this.entities.length >= 6) return;
    const word = this.gameContent[Math.floor(Math.random() * this.gameContent.length)];
    const el = document.createElement('div');
    el.className = 'falling-meteor-word';
    el.innerHTML = `☄️ <span>${word}</span>`;

    const angle = Math.random() * Math.PI * 2;
    const radius = 220;
    const centerX = this.viewport.clientWidth / 2;
    const centerY = this.viewport.clientHeight / 2;
    const startX = centerX + Math.cos(angle) * radius;
    const startY = centerY + Math.sin(angle) * radius;

    el.style.left = `${startX}px`;
    el.style.top = `${startY}px`;
    this.viewport.appendChild(el);

    this.entities.push({ el, word, typed: '', x: startX, y: startY, angle, speed: 0.9 + Math.random() * 0.6 });
  }

  tickSpaceDefender() {
    const centerX = this.viewport.clientWidth / 2;
    const centerY = this.viewport.clientHeight / 2;

    for (let i = this.entities.length - 1; i >= 0; i--) {
      const a = this.entities[i];
      a.x -= Math.cos(a.angle) * a.speed;
      a.y -= Math.sin(a.angle) * a.speed;
      a.el.style.left = `${a.x}px`;
      a.el.style.top = `${a.y}px`;

      if (Math.hypot(centerX - a.x, centerY - a.y) < 35) {
        a.el.remove();
        this.entities.splice(i, 1);
        if (this.activeTarget === a) this.activeTarget = null;
        this.registerError();
      }
    }
  }

  // ==========================================
  // Game 9: Bomb Defuse
  // ==========================================
  setupBombDefuse() {
    this.bombTime = 40;
    this.viewport.innerHTML = `
      <div style="text-align:center; padding-top:40px;">
        <div style="font-size:3rem; margin-bottom:0.4rem;">💣</div>
        <div id="bomb-countdown" class="bomb-timer-display">00:40</div>
        <div id="bomb-code-box" style="margin:25px auto; max-width:440px; background:var(--bg-card); border:2px solid var(--accent); border-radius:8px; padding:1.25rem; font-family:var(--font-mono); font-size:1.8rem; letter-spacing:0.15em;">
          INITIALIZING...
        </div>
      </div>
    `;
    this.spawnNextBombCode();
    this.spawnInterval = setInterval(() => {
      this.bombTime--;
      const el = document.getElementById('bomb-countdown');
      if (el) el.textContent = `00:${this.bombTime < 10 ? '0' : ''}${this.bombTime}`;
      if (this.bombTime <= 0) {
        this.concludeGame("Detonation Triggered! Bomb exploded before defusal sequence.");
      }
    }, 1000);
  }

  spawnNextBombCode() {
    this.bombCurrentCode = this.gameContent[Math.floor(Math.random() * this.gameContent.length)];
    const box = document.getElementById('bomb-code-box');
    if (box) box.textContent = this.bombCurrentCode;
    this.typedBuffer = "";
  }

  // ==========================================
  // Game 10: Typing Ninja (Slicing Mechanics)
  // ==========================================
  setupTypingNinja() {
    this.spawnInterval = setInterval(() => this.spawnNinjaWord(), 1900);
    this.gameLoopInterval = setInterval(() => this.tickNinjaWords(), 40);
  }

  spawnNinjaWord() {
    if (this.entities.length >= 6) return;
    const word = this.gameContent[Math.floor(Math.random() * this.gameContent.length)];
    const el = document.createElement('div');
    el.className = 'falling-meteor-word';
    el.textContent = word;
    const startX = Math.random() * (this.viewport.clientWidth - 150) + 30;
    el.style.left = `${startX}px`;
    el.style.top = `${this.viewport.clientHeight - 40}px`;
    this.viewport.appendChild(el);

    this.entities.push({ el, word, typed: '', x: startX, y: this.viewport.clientHeight - 40, vy: -6 - Math.random() * 3, vx: (Math.random() - 0.5) * 2 });
  }

  tickNinjaWords() {
    for (let i = this.entities.length - 1; i >= 0; i--) {
      const n = this.entities[i];
      n.vy += 0.15; // Gravity
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

  // ==========================================
  // Game 11: Memory Type
  // ==========================================
  setupMemoryType() {
    this.viewport.innerHTML = `
      <div style="text-align:center; padding-top:60px;">
        <div style="font-size:0.85rem; text-transform:uppercase; color:var(--text-muted); font-weight:700;">Memorize & Reproduce Blindly</div>
        <div id="memory-flash-card" style="margin:25px auto; max-width:440px; background:var(--bg-card); border:2px solid var(--accent); border-radius:8px; padding:2rem; font-family:var(--font-mono); font-size:2.5rem; letter-spacing:0.15em;">
          READY
        </div>
        <div id="memory-input-cue" style="color:var(--text-muted); font-size:0.9rem;">Sequence will vanish in 1.5s...</div>
      </div>
    `;
    this.memorySequenceIndex = 0;
    setTimeout(() => this.triggerMemoryFlash(), 800);
  }

  triggerMemoryFlash() {
    this.memoryTarget = this.gameContent[this.memorySequenceIndex % this.gameContent.length];
    const card = document.getElementById('memory-flash-card');
    const cue = document.getElementById('memory-input-cue');
    if (!card) return;
    card.textContent = this.memoryTarget;
    card.style.color = "var(--text-primary)";
    if (cue) cue.textContent = "Memorize the sequence...";
    this.typedBuffer = "";

    setTimeout(() => {
      if (card) {
        card.textContent = "••••••••";
        card.style.color = "var(--accent)";
      }
      if (cue) cue.textContent = "Type the sequence from mental recall!";
    }, 1500);
  }

  // ==========================================
  // Game 12: Keyboard Quest
  // ==========================================
  setupKeyboardQuest() {
    this.questIndex = 0;
    this.viewport.innerHTML = `
      <div style="text-align:center; padding-top:40px;">
        <span class="badge" style="background:var(--accent-glow); color:var(--accent); font-weight:800; padding:0.2rem 0.6rem; border-radius:4px;">ERGONOMIC STAGE QUEST</span>
        <div id="quest-stage-target" style="margin:25px auto; max-width:440px; background:var(--bg-card); border:2px solid var(--accent); border-radius:8px; padding:1.5rem; font-family:var(--font-mono); font-size:2rem; font-weight:800;">
          ...
        </div>
        <div style="font-size:0.85rem; color:var(--text-muted);">Anchor palms. Maintain home-row alignment.</div>
      </div>
    `;
    this.loadNextQuestTarget();
  }

  loadNextQuestTarget() {
    this.questTarget = this.gameContent[this.questIndex % this.gameContent.length];
    const el = document.getElementById('quest-stage-target');
    if (el) el.textContent = this.questTarget;
    this.typedBuffer = "";
  }

  // ==========================================
  // Keystroke Matcher Engine
  // ==========================================
  bindKeystrokes() {
    window.addEventListener('keydown', (e) => {
      if (e.key.length !== 1 || e.ctrlKey || e.metaKey || e.altKey) return;
      e.preventDefault();

      const char = e.key;
      this.totalStrokes++;

      // Speed Racer
      if (this.activeGame === 'speed_racer') {
        const expected = this.racerPassage[this.racerIdx];
        const spans = document.querySelectorAll('#racer-text-track .char');
        if (char === expected) {
          if (spans[this.racerIdx]) spans[this.racerIdx].className = 'char correct';
          this.racerIdx++;
          this.correctStrokes++;
          const pct = Math.min(100, (this.racerIdx / this.racerPassage.length) * 100);
          this.updateRacerPosition('player', pct);
          this.registerHit(10);
          
          if (this.combo > 8) {
            const nitro = document.getElementById('player-nitro');
            if (nitro) nitro.style.display = 'block';
          }
          if (pct >= 100) this.concludeGame("Circuit Champion! You crossed the finish line!");
        } else {
          if (spans[this.racerIdx]) spans[this.racerIdx].className = 'char incorrect';
          const nitro = document.getElementById('player-nitro');
          if (nitro) nitro.style.display = 'none';
          this.registerError();
        }
        return;
      }

      // Bubble Pop
      if (this.activeGame === 'bubble_pop') {
        const lower = char.toLowerCase();
        const match = this.entities.find(b => b.char === lower);
        if (match) {
          match.el.remove();
          this.entities.splice(this.entities.indexOf(match), 1);
          this.registerHit(15);
        } else {
          this.registerError();
        }
        return;
      }

      // Whack-A-Word
      if (this.activeGame === 'whack_a_word') {
        const lower = char.toLowerCase();
        if (this.currentMoleWord && this.currentMoleWord.startsWith(this.moleTyped + lower)) {
          this.moleTyped += lower;
          const hole = document.getElementById(`hole-${this.currentHoleIdx}`);
          if (hole) hole.innerHTML = `<span style="color:var(--success); text-decoration:underline;">${this.moleTyped}</span>${this.currentMoleWord.slice(this.moleTyped.length)}`;

          if (this.moleTyped === this.currentMoleWord) {
            this.registerHit(25);
            this.spawnNextMole();
          }
        } else {
          this.registerError();
        }
        return;
      }

      // Zombie Duel
      if (this.activeGame === 'zombie_duel') {
        const lower = char.toLowerCase();
        if (this.duelTarget && this.duelTarget.startsWith(this.duelTyped + lower)) {
          this.duelTyped += lower;
          const el = document.getElementById('duel-spell-word');
          if (el) el.innerHTML = `<span style="color:var(--success); text-decoration:underline;">${this.duelTyped}</span>${this.duelTarget.slice(this.duelTyped.length)}`;

          if (this.duelTyped === this.duelTarget) {
            this.opponentHp = Math.max(0, this.opponentHp - 25);
            const oppBar = document.getElementById('duel-opp-hp');
            if (oppBar) oppBar.style.width = `${this.opponentHp}%`;
            this.registerHit(20);

            if (this.opponentHp <= 0) {
              clearInterval(this.aiAttackTimer);
              this.concludeGame("Duel Victory! You defeated the enemy!");
            } else {
              this.spawnDuelSpell();
            }
          }
        } else {
          this.registerError();
        }
        return;
      }

      // Word Blitz
      if (this.activeGame === 'word_blitz') {
        const lower = char.toLowerCase();
        if (this.blitzTarget && this.blitzTarget.startsWith(this.blitzTyped + lower)) {
          this.blitzTyped += lower;
          const el = document.getElementById('blitz-word-target');
          if (el) el.innerHTML = `<span style="color:var(--success);">${this.blitzTyped.toUpperCase()}</span>${this.blitzTarget.slice(this.blitzTyped.length).toUpperCase()}`;

          if (this.blitzTyped === this.blitzTarget) {
            this.registerHit(15);
            this.spawnBlitzWord();
          }
        } else {
          this.registerError();
        }
        return;
      }

      // Cipher Hacker
      if (this.activeGame === 'cipher_hacker') {
        if (this.cipherTarget && this.cipherTarget.startsWith(this.cipherTyped + char)) {
          this.cipherTyped += char;
          const el = document.getElementById('cipher-code-display');
          if (el) el.innerHTML = `<span style="color:var(--accent);">${this.cipherTyped}</span>${this.cipherTarget.slice(this.cipherTyped.length)}`;

          if (this.cipherTyped === this.cipherTarget) {
            this.registerHit(25);
            this.cipherTime = Math.min(45, this.cipherTime + 3);
            this.spawnCipherTarget();
          }
        } else {
          this.registerError();
        }
        return;
      }

      // Bomb Defuse
      if (this.activeGame === 'bomb_defuse') {
        if (this.bombCurrentCode.startsWith(this.typedBuffer + char)) {
          this.typedBuffer += char;
          const box = document.getElementById('bomb-code-box');
          if (box) box.innerHTML = `<span style="color:var(--success);">${this.typedBuffer}</span>${this.bombCurrentCode.slice(this.typedBuffer.length)}`;
          this.registerHit(15);
          if (this.typedBuffer === this.bombCurrentCode) {
            this.spawnNextBombCode();
          }
        } else {
          this.bombTime = Math.max(1, this.bombTime - 3);
          this.registerError();
        }
        return;
      }

      // Memory Type
      if (this.activeGame === 'memory_type') {
        this.typedBuffer += char;
        if (this.memoryTarget.startsWith(this.typedBuffer)) {
          this.registerHit(20);
          if (this.typedBuffer === this.memoryTarget) {
            this.memorySequenceIndex++;
            this.triggerMemoryFlash();
          }
        } else {
          this.registerError();
          this.triggerMemoryFlash();
        }
        return;
      }

      // Keyboard Quest
      if (this.activeGame === 'keyboard_quest') {
        if (this.questTarget.startsWith(this.typedBuffer + char)) {
          this.typedBuffer += char;
          const targetEl = document.getElementById('quest-stage-target');
          if (targetEl) targetEl.innerHTML = `<span style="color:var(--success);">${this.typedBuffer}</span>${this.questTarget.slice(this.typedBuffer.length)}`;
          this.registerHit(15);
          if (this.typedBuffer === this.questTarget) {
            this.questIndex++;
            this.loadNextQuestTarget();
          }
        } else {
          this.registerError();
        }
        return;
      }

      // Falling Words, Ninja Slicing, Space Defender
      const lower = char.toLowerCase();
      if (this.activeTarget) {
        const next = this.activeTarget.word[this.activeTarget.typed.length];
        if (lower === next) {
          this.activeTarget.typed += lower;
          this.activeTarget.el.innerHTML = `<span style="color:var(--success); text-decoration:underline;">${this.activeTarget.typed}</span>${this.activeTarget.word.slice(this.activeTarget.typed.length)}`;
          this.registerHit(10);

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
        this.activeTarget.el.classList.add('target-locked');
        this.activeTarget.el.innerHTML = `<span style="color:var(--success); text-decoration:underline;">${lower}</span>${match.word.slice(1)}`;
        this.registerHit(10);
      } else {
        this.registerError();
      }
    });
  }

  registerHit(pts) {
    this.combo++;
    if (this.combo > this.maxCombo) this.maxCombo = this.combo;
    const multiplier = 1 + Math.floor(this.combo / 6) * 0.25;
    this.score += Math.round(pts * multiplier);
    this.correctStrokes++;
    if (window.soundEngine) window.soundEngine.playKey(false);
    this.updateScoreboard(this.score, this.combo);
  }

  registerError() {
    this.combo = 0;
    this.errors++;
    if (window.soundEngine) window.soundEngine.playKey(true);
    this.updateScoreboard(this.score, 0);
  }

  updateScoreboard(score, combo) {
    const sEl = document.getElementById('live-my-score');
    const cEl = document.getElementById('live-combo-badge');
    if (sEl) sEl.textContent = `${score} pts`;
    if (cEl) cEl.textContent = `${combo}x`;
  }

  concludeGame(summaryText) {
    this.stop();
    const duration = (performance.now() - this.startTime) / 1000.0;
    const netWords = Math.max(0, (this.correctStrokes - this.errors) / 5.0);
    const wpm = duration > 0 ? Math.round((netWords / duration) * 60.0) : 0;
    const acc = this.totalStrokes > 0 ? Math.round((this.correctStrokes / this.totalStrokes) * 100.0) : 100;

    document.getElementById('game-active-arena').style.display = 'none';
    document.getElementById('game-results-screen').style.display = 'block';

    document.getElementById('results-summary').textContent = summaryText;
    document.getElementById('res-score').textContent = this.score;
    document.getElementById('res-wpm').textContent = wpm;
    document.getElementById('res-acc').textContent = `${acc}%`;
    document.getElementById('res-combo').textContent = `${this.maxCombo}x`;
    document.getElementById('res-reaction').textContent = "180ms";

    fetch('/games/api/submit-score', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        game_mode: this.activeGame,
        play_type: this.config.playMode,
        score: this.score,
        net_wpm: wpm,
        accuracy: acc,
        errors: this.errors,
        highest_combo: this.maxCombo,
        duration: duration
      })
    }).catch(() => {});
  }
}

window.arcadeEngine = new ArcadeRuntimeEngine();