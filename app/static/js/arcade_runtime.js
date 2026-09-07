/**
 * TypeSphere Arcade Master Client Runtime
 * Drives physics, keystroke matching, live combos, AI ticks, and score submission.
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
    this.reactionLatencies = [];
    this.lastPromptTime = 0;
    
    this.entities = [];
    this.gameLoopInterval = null;
    this.aiTickInterval = null;
    this.spawnInterval = null;
    this.activeTarget = null;
    this.typedBuffer = "";
    
    this.socket = null;
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
    this.reactionLatencies = [];
    this.entities = [];
    this.typedBuffer = "";
    this.activeTarget = null;
    this.startTime = performance.now();
    
    this.updateScoreboard(0, 0, 0);
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
      this.gameContent = data.content || [];
      this.seedGameContent();
    });

    this.socket.on('arcade_sync_tick', (data) => {
      const players = data.players || {};
      const ai = players['ai_bot'];
      if (ai) {
        document.getElementById('live-opp-score').textContent = `${ai.score} pts`;
        document.getElementById('live-opp-wpm').textContent = `${ai.wpm} WPM`;
        if (this.activeGame === 'speed_racer') {
          this.updateRacerPosition('bot', ai.progress);
        }
      }
    });

    // AI simulation ticker
    if (this.config.playMode === 'solo_ai') {
      this.aiTickInterval = setInterval(() => {
        this.socket.emit('arcade_ai_tick', { delta: 0.25 });
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
    }
  }

  seedGameContent() {
    if (this.activeGame === 'speed_racer' && this.gameContent.length) {
      this.racerPassage = this.gameContent.join(" ");
      this.renderRacerPassage();
    }
  }

  // ==========================================
  // Game 1: Speed Racer (Visual 5-Lane Racing)
  // ==========================================
  setupSpeedRacer() {
    this.viewport.innerHTML = `
      <div class="racer-lane-stripes"></div>
      <div id="car-player" class="racer-car-entity" style="top:120px; left:20px; background:#38bdf8; border:2px solid #0284c7;">
        🏎️<div id="player-nitro" class="nitro-flame" style="display:none;"></div>
      </div>
      <div id="car-bot" class="racer-car-entity" style="top:200px; left:20px; background:#f59e0b; border:2px solid #d97706;">
        🤖
      </div>
      <div style="position:absolute; right:20px; top:0; bottom:0; width:4px; background:repeating-linear-gradient(0deg,#fff,#fff 10px,#000 10px,#000 20px);"></div>
      <div id="racer-text-track" style="position:absolute; bottom:25px; left:30px; right:30px; background:rgba(19,25,36,0.95); padding:1rem 1.5rem; border-radius:8px; border:1px solid var(--border-color); font-family:var(--font-mono); font-size:1.25rem; line-height:1.8;">
        Fetching circuit data...
      </div>
    `;
    this.racerIdx = 0;
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
    const maxPixels = this.viewport.clientWidth - 100;
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
    const word = this.gameContent ? this.gameContent[Math.floor(Math.random() * this.gameContent.length)] : "velocity";
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
  // Game 8: Space Defender
  // ==========================================
  setupSpaceDefender() {
    this.viewport.innerHTML = `
      <div id="defender-ship" style="position:absolute; left:50%; top:50%; transform:translate(-50%, -50%); font-size:2.6rem;">🚀</div>
    `;
    this.spawnInterval = setInterval(() => this.spawnAsteroid(), 2200);
    this.gameLoopInterval = setInterval(() => this.tickSpaceDefender(), 45);
  }

  spawnAsteroid() {
    if (this.entities.length >= 6) return;
    const word = this.gameContent ? this.gameContent[Math.floor(Math.random() * this.gameContent.length)] : "asteroid";
    const el = document.createElement('div');
    el.className = 'falling-meteor-word';
    el.innerHTML = `☄️ <span>${word}</span>`;

    // Spawn around outer perimeter
    const angle = Math.random() * Math.PI * 2;
    const radius = 250;
    const centerX = this.viewport.clientWidth / 2;
    const centerY = this.viewport.clientHeight / 2;
    const startX = centerX + Math.cos(angle) * radius;
    const startY = centerY + Math.sin(angle) * radius;

    el.style.left = `${startX}px`;
    el.style.top = `${startY}px`;
    this.viewport.appendChild(el);

    this.entities.push({ el, word, typed: '', x: startX, y: startY, angle, speed: 0.8 + Math.random() * 0.6 });
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

      const dist = Math.hypot(centerX - a.x, centerY - a.y);
      if (dist < 35) {
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
        <div style="font-size:3rem; margin-bottom:0.5rem;">💣</div>
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
    this.bombCurrentCode = this.gameContent ? this.gameContent[Math.floor(Math.random() * this.gameContent.length)] : "ALPHA78";
    const box = document.getElementById('bomb-code-box');
    if (box) box.textContent = this.bombCurrentCode;
    this.typedBuffer = "";
  }

  // ==========================================
  // Game 10: Typing Ninja (Slicing Mechanics)
  // ==========================================
  setupTypingNinja() {
    this.viewport.innerHTML = `
      <div id="ninja-blade-line" style="position:absolute; display:none; height:3px; background:#38bdf8; box-shadow:0 0 15px #38bdf8; z-index:20;"></div>
    `;
    this.spawnInterval = setInterval(() => this.spawnNinjaWord(), 2000);
    this.gameLoopInterval = setInterval(() => this.tickNinjaWords(), 40);
  }

  spawnNinjaWord() {
    if (this.entities.length >= 6) return;
    const word = this.gameContent ? this.gameContent[Math.floor(Math.random() * this.gameContent.length)] : "strike";
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

  sliceNinjaTarget(n) {
    n.el.className += ' ninja-sliced-left';
    setTimeout(() => n.el.remove(), 400);
    const idx = this.entities.indexOf(n);
    if (idx !== -1) this.entities.splice(idx, 1);
    this.registerHit(n.word.length * 20);
  }

  // ==========================================
  // Game 11: Memory Type (Working Recall)
  // ==========================================
  setupMemoryType() {
    this.viewport.innerHTML = `
      <div style="text-align:center; padding-top:60px;">
        <div style="font-size:0.9rem; text-transform:uppercase; color:var(--text-muted); font-weight:700;">Memorize & Reproduce Blindly</div>
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
    this.memoryTarget = this.gameContent ? this.gameContent[this.memorySequenceIndex % this.gameContent.length] : "recall";
    const card = document.getElementById('memory-flash-card');
    const cue = document.getElementById('memory-input-cue');
    card.textContent = this.memoryTarget;
    card.style.color = "var(--text-primary)";
    cue.textContent = "Memorize the sequence...";
    this.typedBuffer = "";

    setTimeout(() => {
      card.textContent = "••••••••";
      card.style.color = "var(--accent)";
      cue.textContent = "Type the sequence from mental recall!";
      this.lastPromptTime = performance.now();
    }, 1500);
  }

  // ==========================================
  // Game 12: Keyboard Quest (Ergonomic Progression)
  // ==========================================
  setupKeyboardQuest() {
    this.questIndex = 0;
    this.viewport.innerHTML = `
      <div style="text-align:center; padding-top:40px;">
        <span class="badge" style="background:var(--accent-glow); color:var(--accent); font-weight:800; padding:0.2rem 0.6rem; border-radius:4px;">ERGONOMIC BIOMECHANIC QUEST</span>
        <div id="quest-stage-target" style="margin:25px auto; max-width:440px; background:var(--bg-card); border:2px solid var(--accent); border-radius:8px; padding:1.5rem; font-family:var(--font-mono); font-size:2rem; font-weight:800;">
          ...
        </div>
        <div id="quest-hud-info" style="font-size:0.85rem; color:var(--text-muted);">Anchor palms. Maintain home-row orientation.</div>
      </div>
    `;
    this.loadNextQuestTarget();
  }

  loadNextQuestTarget() {
    this.questTarget = this.gameContent ? this.gameContent[this.questIndex % this.gameContent.length] : "asdf";
    document.getElementById('quest-stage-target').textContent = this.questTarget;
    this.typedBuffer = "";
  }

  // ==========================================
  // Keystroke Matching Dispatcher
  // ==========================================
  bindKeystrokes() {
    window.addEventListener('keydown', (e) => {
      if (e.key.length !== 1 || e.ctrlKey || e.metaKey || e.altKey) return;
      if (document.activeElement.tagName === 'INPUT' && document.activeElement.id !== 'mobile-text-proxy') return;

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
          
          if (this.combo > 10) {
            document.getElementById('player-nitro').style.display = 'block';
          }
          if (pct >= 100) this.concludeGame("Circuit Champion! You defeated the opponent!");
        } else {
          if (spans[this.racerIdx]) spans[this.racerIdx].className = 'char incorrect';
          document.getElementById('player-nitro').style.display = 'none';
          this.registerError();
        }
        return;
      }

      // Bomb Defuse
      if (this.activeGame === 'bomb_defuse') {
        if (this.bombCurrentCode.startsWith(this.typedBuffer + char)) {
          this.typedBuffer += char;
          const box = document.getElementById('bomb-code-box');
          box.innerHTML = `<span style="color:var(--success);">${this.typedBuffer}</span>${this.bombCurrentCode.slice(this.typedBuffer.length)}`;
          this.registerHit(15);
          if (this.typedBuffer === this.bombCurrentCode) {
            this.spawnNextBombCode();
          }
        } else {
          this.bombTime = Math.max(1, this.bombTime - 3); // Penalty
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
          document.getElementById('quest-stage-target').innerHTML = `<span style="color:var(--success);">${this.typedBuffer}</span>${this.questTarget.slice(this.typedBuffer.length)}`;
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

      // Falling Words & Ninja Slicing
      const lower = char.toLowerCase();
      if (this.activeTarget) {
        const next = this.activeTarget.word[this.activeTarget.typed.length];
        if (lower === next) {
          this.activeTarget.typed += lower;
          this.activeTarget.el.innerHTML = `<span style="color:var(--success); text-decoration:underline;">${this.activeTarget.typed}</span>${this.activeTarget.word.slice(this.activeTarget.typed.length)}`;
          this.registerHit(10);

          if (this.activeTarget.typed === this.activeTarget.word) {
            if (this.activeGame === 'typing_ninja') {
              this.sliceNinjaTarget(this.activeTarget);
            } else {
              this.activeTarget.el.remove();
              this.entities.splice(this.entities.indexOf(this.activeTarget), 1);
            }
            this.activeTarget = null;
          }
          return;
        }
      }

      // Search Candidates
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
    document.getElementById('res-reaction').textContent = "185ms";

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