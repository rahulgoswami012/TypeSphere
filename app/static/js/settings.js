/**
 * TypeSphere Global Settings Engine
 * Updates CSS Variables dynamically across all pages and syncs settings.
 */
class SettingsManager {
  constructor() {
    this.defaults = {
      theme: 'dark',
      font_family: 'JetBrains Mono',
      font_size: 20,
      caret_style: 'smooth',
      sound_enabled: true,
      sound_theme: 'mechanical',
      show_keyboard: true
    };
    this.current = Object.assign({}, this.defaults);
    this.loadSettings();
  }

  loadSettings() {
    const local = localStorage.getItem('typesphere_prefs');
    if (local) {
      try {
        this.current = Object.assign({}, this.defaults, JSON.parse(local));
      } catch (e) {}
    }
    this.applyAll();
  }

  applyAll() {
    // 1. Theme
    document.documentElement.setAttribute('data-theme', this.current.theme);

    // 2. CSS Variables for Fonts and Sizes
    document.documentElement.style.setProperty('--font-mono', `"${this.current.font_family}", monospace`);
    document.documentElement.style.setProperty('--typing-font-size', `${this.current.font_size}px`);

    // 3. Caret Style across all carets (test page + preview)
    const carets = document.querySelectorAll('.caret');
    carets.forEach(c => {
      c.className = `caret caret-${this.current.caret_style}`;
    });

    // 4. Sound Engine state
    if (window.soundEngine) {
      window.soundEngine.enabled = this.current.sound_enabled;
      window.soundEngine.theme = this.current.sound_theme;
    }

    // 5. Keyboard Visibility on test page
    const kb = document.getElementById('keyboard-container');
    if (kb) {
      kb.style.display = this.current.show_keyboard ? 'flex' : 'none';
    }

    // 6. Highlight active buttons on the settings page
    this.syncActiveButtons();
  }

  update(key, value) {
    this.current[key] = value;
    localStorage.setItem('typesphere_prefs', JSON.stringify(this.current));
    this.applyAll();

    // Async server persistence
    fetch('/settings/api/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(this.current)
    }).catch(() => {});
  }

  syncActiveButtons() {
    // Highlight Themes
    document.querySelectorAll('[data-theme-btn]').forEach(btn => {
      btn.classList.toggle('active-choice', btn.dataset.themeBtn === this.current.theme);
    });

    // Highlight Fonts
    document.querySelectorAll('[data-font-btn]').forEach(btn => {
      btn.classList.toggle('active-choice', btn.dataset.fontBtn === this.current.font_family);
    });

    // Highlight Carets
    document.querySelectorAll('[data-caret-btn]').forEach(btn => {
      btn.classList.toggle('active-choice', btn.dataset.caretBtn === this.current.caret_style);
    });

    // Highlight Sounds
    document.querySelectorAll('[data-sound-btn]').forEach(btn => {
      btn.classList.toggle('active-choice', btn.dataset.soundBtn === this.current.sound_theme && this.current.sound_enabled);
    });

    // Font size slider & label
    const slider = document.getElementById('font-size-slider');
    const label = document.getElementById('font-size-label');
    if (slider) slider.value = this.current.font_size;
    if (label) label.textContent = `${this.current.font_size}px`;

    // Keyboard button
    const kbBtn = document.getElementById('kb-toggle-btn');
    if (kbBtn) {
      kbBtn.textContent = this.current.show_keyboard ? "Enabled" : "Disabled";
      kbBtn.classList.toggle('btn-primary', this.current.show_keyboard);
    }

    // Sound mute button
    const audioBtn = document.getElementById('audio-toggle-btn');
    if (audioBtn) {
      audioBtn.textContent = this.current.sound_enabled ? "Mute All Sound" : "Sound Muted";
      audioBtn.classList.toggle('active-choice', !this.current.sound_enabled);
    }
  }
}

window.settingsManager = new SettingsManager();
document.addEventListener('DOMContentLoaded', () => {
  window.settingsManager.applyAll();
});