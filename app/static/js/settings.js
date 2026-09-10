/**
 * TypeSphere Unified Settings & Cockpit Personalization Dispatcher
 * Strictly separates Default Settings, Guest Session Settings, and User Profile Settings.
 */
class SettingsManager {
    constructor() {
        this.defaultSettings = {
            theme: 'Dark',
            font_family: 'JetBrains Mono',
            font_size: 22,
            caret_style: 'smooth',
            typing_area_style: 'modern',
            keyboard_display: 'heatmap',
            sound_enabled: true,
            sound_theme: 'mechanical',
            sound_volume: 0.7,
            game_sound_volume: 0.7,
            game_sound_theme: 'retro',
            show_keyboard: true,
            reduce_motion: false,
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
        const authElement = document.getElementById('user-auth-meta');
        const isAuthenticated = authElement ? authElement.dataset.authenticated === 'true' : false;

        if (isAuthenticated) {
            // Authenticated Pilot: Read from localStorage or initial database injection
            const stored = localStorage.getItem('typesphere_user_profile_prefs');
            if (stored) {
                try {
                    this.current = Object.assign({}, this.defaultSettings, JSON.parse(stored));
                } catch {}
            }
        } else {
            // Anonymous Guest: Temporary session storage only; refreshes revert to system defaults
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
        // 1. Theme Palette
        document.documentElement.setAttribute('data-theme', this.current.theme || 'dark');

        // 2. Reduced Motion Preference
        if (this.current.reduce_motion) {
            document.documentElement.setAttribute('data-reduce-motion', 'true');
        } else {
            document.documentElement.removeAttribute('data-reduce-motion');
        }

        // 3. Typography & Sizing CSS Variables
        document.documentElement.style.setProperty('--font-mono', `"${this.current.font_family}", monospace`);
        document.documentElement.style.setProperty('--typing-font-size', `${this.current.font_size}px`);

        // 4. Caret Styles
        const carets = document.querySelectorAll('.caret');
        carets.forEach(c => {
            if (!c.classList.contains('ghost-caret')) {
                c.className = `caret caret-${this.current.caret_style}`;
            }
        });

        // 5. Typing Container Visual Style
        const typingBox = document.getElementById('typing-box');
        if (typingBox && this.current.typing_area_style) {
            typingBox.className = `typing-container focus-ring style-${this.current.typing_area_style}`;
        }

        // 6. Sound Synthesizer
        if (window.soundEngine) {
            window.soundEngine.enabled = this.current.sound_enabled;
            window.soundEngine.theme = this.current.sound_theme;
            window.soundEngine.setVolume(this.current.sound_volume);
        }

        // 7. On-Screen Virtual Keyboard Visibility
        const kbWrapper = document.getElementById('keyboard-container');
        if (kbWrapper) {
            kbWrapper.style.display = (this.current.keyboard_display === 'hidden') ? 'none' : 'flex';
        }

        // 8. Synchronize Live Typing Engine Controls if Present
        if (window.typingEngine) {
            window.typingEngine.durationLimit = this.current.default_duration;
            window.typingEngine.contentType = this.current.default_content;
            window.typingEngine.level = this.current.default_level;
            window.typingEngine.blindModeActive = this.current.blind_mode;
            window.typingEngine.ghostEnabled = this.current.ghost_mode;
            window.typingEngine.updateControlsUI();
        }

        // 9. Synchronize Active UI Button States on /settings/
        this.highlightSettingsPageUI();
    }

    highlightSettingsPageUI() {
        // Theme Buttons
        document.querySelectorAll('[data-cfg-theme]').forEach(btn => {
            btn.classList.toggle('active-choice', btn.dataset.cfgTheme === this.current.theme);
        });

        // Typing Style Buttons
        document.querySelectorAll('[data-cfg-style]').forEach(btn => {
            btn.classList.toggle('active-choice', btn.dataset.cfgStyle === this.current.typing_area_style);
        });

        // Font Family Buttons
        document.querySelectorAll('[data-cfg-font]').forEach(btn => {
            btn.classList.toggle('active-choice', btn.dataset.cfgFont === this.current.font_family);
        });

        // Caret Style Buttons
        document.querySelectorAll('[data-cfg-caret]').forEach(btn => {
            btn.classList.toggle('active-choice', btn.dataset.cfgCaret === this.current.caret_style);
        });

        // Sound Theme Buttons
        document.querySelectorAll('[data-cfg-sound]').forEach(btn => {
            btn.classList.toggle('active-choice', btn.dataset.cfgSound === this.current.sound_theme);
        });

        // Keyboard Display Buttons
        document.querySelectorAll('[data-cfg-kb]').forEach(btn => {
            btn.classList.toggle('active-choice', btn.dataset.cfgKb === this.current.keyboard_display);
        });

        // Sliders & Labels
        const fSlider = document.getElementById('font-size-slider');
        const fLabel = document.getElementById('font-size-label');
        if (fSlider) fSlider.value = this.current.font_size;
        if (fLabel) fLabel.textContent = `${this.current.font_size}px`;

        const sSlider = document.getElementById('sound-volume-slider');
        const sLabel = document.getElementById('sound-volume-label');
        if (sSlider) sSlider.value = Math.round(this.current.sound_volume * 100);
        if (sLabel) sLabel.textContent = `${Math.round(this.current.sound_volume * 100)}%`;

        // Toggles & Dropdowns
        const muteBtn = document.getElementById('btn-sound-mute-toggle');
        if (muteBtn) {
            muteBtn.textContent = this.current.sound_enabled ? 'Sound: ON' : 'Sound: MUTED';
            muteBtn.classList.toggle('active-choice', this.current.sound_enabled);
        }

        const motionBtn = document.getElementById('btn-motion-toggle');
        if (motionBtn) {
            motionBtn.textContent = this.current.reduce_motion ? 'Reduced Motion: ON' : 'Reduced Motion: OFF';
            motionBtn.classList.toggle('active-choice', this.current.reduce_motion);
        }

        const blindBtn = document.getElementById('btn-default-blind-toggle');
        if (blindBtn) {
            blindBtn.textContent = this.current.blind_mode ? 'Default Blind Mode: ON' : 'Default Blind Mode: OFF';
            blindBtn.classList.toggle('active-choice', this.current.blind_mode);
        }

        const ghostBtn = document.getElementById('btn-default-ghost-toggle');
        if (ghostBtn) {
            ghostBtn.textContent = this.current.ghost_mode ? 'Default Ghost Pacer: ON' : 'Default Ghost Pacer: OFF';
            ghostBtn.classList.toggle('active-choice', this.current.ghost_mode);
        }

        const durSelect = document.getElementById('cfg-default-duration-select');
        if (durSelect) durSelect.value = this.current.default_duration.toString();

        const contSelect = document.getElementById('cfg-default-content-select');
        if (contSelect) contSelect.value = this.current.default_content;

        const diffSelect = document.getElementById('cfg-default-level-select');
        if (diffSelect) diffSelect.value = this.current.default_level;
    }

    update(key, value) {
        this.current[key] = value;
        this.applyAll();

        const authElement = document.getElementById('user-auth-meta');
        const isAuthenticated = authElement ? authElement.dataset.authenticated === 'true' : false;

        if (isAuthenticated) {
            localStorage.setItem('typesphere_user_profile_prefs', JSON.stringify(this.current));
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

        fetch('/settings/api/reset-defaults', { method: 'POST' }).catch(() => {});
        alert('All preferences successfully restored to factory defaults!');
        window.location.reload();
    }
}

window.settingsManager = new SettingsManager();
document.addEventListener('DOMContentLoaded', () => {
    window.settingsManager.initSettings();
});