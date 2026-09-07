/**
 * TypeSphere Unified Settings & Telemetry Manager
 * Distinctly separates Default Settings, Anonymous Session Settings, and User Profile Settings.
 */
class SettingsManager {
  constructor() {
    this.defaultSettings = {
      theme: 'dark',
      font_family: 'JetBrains Mono',
      font_size: 22,
      caret_style: 'smooth',
      sound_enabled: true,
      sound_theme: 'mechanical',
      sound_volume: 0.7,
      show_keyboard: true,
      default_duration: 60,
      default_content: 'words',
      default_level: 'moderate',
      blind_mode: true,   // Default: ON
      ghost_mode: false   // Default: OFF
    };

    this.current = Object.assign({}, this.defaultSettings);
    this.initSettings();
  }

  initSettings() {
    // Check if user is authenticated via server injection
    const authElement = document.getElementById('user-auth-meta');
    const isAuthenticated = authElement ? authElement.dataset.authenticated === 'true' : false;

    if (isAuthenticated) {
      // Profile Settings: stored in database or localized profile cache
      const stored = localStorage.getItem('typesphere_user_profile_prefs');
      if (stored) {
        try {
          this.current = Object.assign({}, this.defaultSettings, JSON.parse(stored));
        } catch {}
      }
    } else {
      // Anonymous Users: Session settings only. Refreshing restores default settings
      const sessionData = sessionStorage.getItem('typesphere_anon_session_prefs');
      if (sessionData) {
        try {
          this.current = Object.assign({}, this.defaultSettings, JSON.parse(sessionData));
        } catch {}
      } else {
        this.current = Object.assign({}, this.defaultSettings);
      }
    }

    this.applyAll();
  }

  applyAll() {
    // 1. Theme
    document.documentElement.setAttribute('data-theme', this.current.theme);

    // 2. CSS Variables
    document.documentElement.style.setProperty('--font-mono', `"${this.current.font_family}", monospace`);
    document.documentElement.style.setProperty('--typing-font-size', `${this.current.font_size}px`);

    // 3. Caret Style
    const carets = document.querySelectorAll('.caret');
    carets.forEach(c => {
      c.className = `caret caret-${this.current.caret_style}`;
    });

    // 4. Audio Engine
    if (window.soundEngine) {
      window.soundEngine.enabled = this.current.sound_enabled;
      window.soundEngine.theme = this.current.sound_theme;
      window.soundEngine.setVolume(this.current.sound_volume);
    }

    // 5. On-screen Keyboard Toggle
    const kb = document.getElementById('keyboard-container');
    if (kb) {
      kb.style.display = this.current.show_keyboard ? 'flex' : 'none';
    }

    // Sync Engine Defaults if test page active
    if (window.typingEngine) {
      window.typingEngine.durationLimit = this.current.default_duration;
      window.typingEngine.contentType = this.current.default_content;
      window.typingEngine.level = this.current.default_level;
      window.typingEngine.blindModeActive = this.current.blind_mode;
      window.typingEngine.ghostEnabled = this.current.ghost_mode;
      window.typingEngine.updateControlsUI();
    }
  }

  update(key, value) {
    this.current[key] = value;
    this.applyAll();

    const authElement = document.getElementById('user-auth-meta');
    const isAuthenticated = authElement ? authElement.dataset.authenticated === 'true' : false;

    if (isAuthenticated) {
      localStorage.setItem('typesphere_user_profile_prefs', JSON.stringify(this.current));
      // Save to database
      fetch('/settings/api/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(this.current)
      }).catch(() => {});
    } else {
      sessionStorage.setItem('typesphere_anon_session_prefs', JSON.stringify(this.current));
    }
  }

  resetToDefaults() {
    this.current = Object.assign({}, this.defaultSettings);
    sessionStorage.removeItem('typesphere_anon_session_prefs');
    localStorage.removeItem('typesphere_user_profile_prefs');
    this.applyAll();

    // Call server to reset database settings if signed in
    fetch('/settings/api/reset-defaults', { method: 'POST' }).catch(() => {});

    alert('Settings successfully restored to system defaults!');
    window.location.reload();
  }
}

window.settingsManager = new SettingsManager();
document.addEventListener('DOMContentLoaded', () => {
  window.settingsManager.initSettings();
});