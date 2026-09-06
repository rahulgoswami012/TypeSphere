/**
 * TypeSphere Multi-Profile Web Audio Synthesizer with Master Volume Gain Control
 */
class TypeSphereAudio {
  constructor() {
    this.ctx = null;
    this.masterGain = null;
    this.enabled = true;
    this.theme = 'mechanical'; // 'mechanical', 'bubble', 'beep'
    this.volume = 0.7; // 0.0 to 1.0
  }

  init() {
    if (!this.ctx) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      this.ctx = new AudioCtx();
      this.masterGain = this.ctx.createGain();
      this.masterGain.gain.setValueAtTime(this.volume, this.ctx.currentTime);
      this.masterGain.connect(this.ctx.destination);
    }
    if (this.ctx.state === 'suspended') {
      this.ctx.resume();
    }
  }

  setVolume(val) {
    this.volume = Math.max(0, Math.min(1, parseFloat(val)));
    if (this.masterGain && this.ctx) {
      this.masterGain.gain.setValueAtTime(this.volume, this.ctx.currentTime);
    }
  }

  playKey(isError = false) {
    if (!this.enabled || this.volume <= 0) return;
    this.init();

    try {
      const now = this.ctx.currentTime;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.connect(gain);
      gain.connect(this.masterGain);

      if (isError) {
        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(140, now);
        osc.frequency.exponentialRampToValueAtTime(70, now + 0.08);
        gain.gain.setValueAtTime(0.2, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.08);
        osc.start(now);
        osc.stop(now + 0.08);
        return;
      }

      if (this.theme === 'bubble') {
        osc.type = 'sine';
        const startFreq = 350 + Math.random() * 150;
        osc.frequency.setValueAtTime(startFreq, now);
        osc.frequency.exponentialRampToValueAtTime(startFreq * 2.2, now + 0.05);
        gain.gain.setValueAtTime(0.25, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.05);
        osc.start(now);
        osc.stop(now + 0.05);
      } else if (this.theme === 'beep') {
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(800 + Math.random() * 60, now);
        gain.gain.setValueAtTime(0.12, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.04);
        osc.start(now);
        osc.stop(now + 0.04);
      } else {
        // Mechanical Tactile Switch
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(520 + Math.random() * 80, now);
        osc.frequency.exponentialRampToValueAtTime(110, now + 0.04);
        gain.gain.setValueAtTime(0.22, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.04);
        osc.start(now);
        osc.stop(now + 0.04);
      }
    } catch(e) {
      console.warn("Audio playback exception:", e);
    }
  }
}

window.soundEngine = new TypeSphereAudio();