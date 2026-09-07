/**
 * TypeSphere Layout Remapping Engine
 * Maps physical hardware KeyCodes (e.code) to ergonomic target layouts
 * allowing users to type Dvorak, Colemak, Workman, etc. on a standard QWERTY keyboard.
 */

const KEYBOARD_LAYOUTS = {
  qwerty: {
    name: 'QWERTY',
    rows: [
      ["`", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "=", "Backspace"],
      ["Tab", "q", "w", "e", "r", "t", "y", "u", "i", "o", "p", "[", "]", "\\"],
      ["Caps", "a", "s", "d", "f", "g", "h", "j", "k", "l", ";", "'", "Enter"],
      ["Shift", "z", "x", "c", "v", "b", "n", "m", ",", ".", "/", "Shift"],
      ["Space"]
    ],
    homeKeys: ['a', 's', 'd', 'f', 'j', 'k', 'l', ';'],
    // Identity mapping (standard QWERTY)
    map: null
  },

  dvorak: {
    name: 'Dvorak',
    rows: [
      ["`", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "[", "]", "Backspace"],
      ["Tab", "'", ",", ".", "p", "y", "f", "g", "c", "r", "l", "/", "=", "\\"],
      ["Caps", "a", "o", "e", "u", "i", "d", "h", "t", "n", "s", "-", "Enter"],
      ["Shift", ";", "q", "j", "k", "x", "b", "m", "w", "v", "z", "Shift"],
      ["Space"]
    ],
    homeKeys: ['a', 'o', 'e', 'u', 'h', 't', 'n', 's'],
    map: {
      'KeyQ': "'", 'KeyW': ',', 'KeyE': '.', 'KeyR': 'p', 'KeyT': 'y',
      'KeyY': 'f', 'KeyU': 'g', 'KeyI': 'c', 'KeyO': 'r', 'KeyP': 'l',
      'BracketLeft': '/', 'BracketRight': '=',
      'KeyA': 'a', 'KeyS': 'o', 'KeyD': 'e', 'KeyF': 'u', 'KeyG': 'i',
      'KeyH': 'd', 'KeyJ': 'h', 'KeyK': 't', 'KeyL': 'n', 'Semicolon': 's', 'Quote': '-',
      'KeyZ': ';', 'KeyX': 'q', 'KeyC': 'j', 'KeyV': 'k', 'KeyB': 'x',
      'KeyN': 'b', 'KeyM': 'm', 'Comma': 'w', 'Period': 'v', 'Slash': 'z',
      'Minus': '[', 'Equal': ']'
    }
  },

  colemak: {
    name: 'Colemak',
    rows: [
      ["`", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "=", "Backspace"],
      ["Tab", "q", "w", "f", "p", "g", "j", "l", "u", "y", ";", "[", "]", "\\"],
      ["Caps", "a", "r", "s", "t", "d", "h", "n", "e", "i", "o", "'", "Enter"],
      ["Shift", "z", "x", "c", "v", "b", "k", "m", ",", ".", "/", "Shift"],
      ["Space"]
    ],
    homeKeys: ['a', 'r', 's', 't', 'n', 'e', 'i', 'o'],
    map: {
      'KeyE': 'f', 'KeyR': 'p', 'KeyT': 'g', 'KeyY': 'j', 'KeyU': 'l', 'KeyI': 'u', 'KeyO': 'y', 'KeyP': ';',
      'KeyS': 'r', 'KeyD': 's', 'KeyF': 't', 'KeyG': 'd', 'KeyJ': 'n', 'KeyK': 'e', 'KeyL': 'i', 'Semicolon': 'o',
      'KeyN': 'k'
    }
  },

  workman: {
    name: 'Workman',
    rows: [
      ["`", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "=", "Backspace"],
      ["Tab", "q", "d", "r", "w", "b", "j", "f", "u", "p", ";", "[", "]", "\\"],
      ["Caps", "a", "s", "h", "t", "g", "y", "n", "e", "o", "i", "'", "Enter"],
      ["Shift", "z", "x", "m", "c", "v", "k", "l", ",", ".", "/", "Shift"],
      ["Space"]
    ],
    homeKeys: ['a', 's', 'h', 't', 'n', 'e', 'o', 'i'],
    map: {
      'KeyW': 'd', 'KeyE': 'r', 'KeyR': 'w', 'KeyT': 'b', 'KeyY': 'j', 'KeyU': 'f', 'KeyO': 'p', 'KeyP': ';',
      'KeyD': 'h', 'KeyF': 't', 'KeyH': 'y', 'KeyJ': 'n', 'KeyL': 'o', 'Semicolon': 'i',
      'KeyC': 'm', 'KeyV': 'c', 'KeyB': 'v', 'KeyN': 'k', 'KeyM': 'l'
    }
  },

  azerty: {
    name: 'AZERTY',
    rows: [
      ["²", "&", "é", "\"", "'", "(", "-", "è", "_", "ç", "à", ")", "=", "Backspace"],
      ["Tab", "a", "z", "e", "r", "t", "y", "u", "i", "o", "p", "^", "$", "*"],
      ["Caps", "q", "s", "d", "f", "g", "h", "j", "k", "l", "m", "ù", "Enter"],
      ["Shift", "w", "x", "c", "v", "b", "n", ",", ";", ":", "!", "Shift"],
      ["Space"]
    ],
    homeKeys: ['q', 's', 'd', 'f', 'j', 'k', 'l', 'm'],
    map: {
      'KeyQ': 'a', 'KeyW': 'z', 'KeyA': 'q', 'KeyZ': 'w', 'Semicolon': 'm', 'KeyM': ','
    }
  }
};

class LayoutManager {
  constructor() {
    this.activeLayout = 'qwerty';
    this.loadPreference();
  }

  loadPreference() {
    const saved = localStorage.getItem('typesphere_layout');
    if (saved && KEYBOARD_LAYOUTS[saved]) {
      this.activeLayout = saved;
    }
  }

  setLayout(layoutKey) {
    if (KEYBOARD_LAYOUTS[layoutKey]) {
      this.activeLayout = layoutKey;
      localStorage.setItem('typesphere_layout', layoutKey);
      if (window.virtualKeyboard) {
        window.virtualKeyboard.renderForLayout(layoutKey);
      }
    }
  }

  /**
   * Translates a physical keyboard event to the target layout character
   */
  translateEvent(e) {
    if (this.activeLayout === 'qwerty') {
      return e.key;
    }

    const layout = KEYBOARD_LAYOUTS[this.activeLayout];
    if (!layout || !layout.map) {
      return e.key;
    }

    // Lookup physical key code (e.g. 'KeyE')
    let char = layout.map[e.code];
    if (!char) {
      return e.key;
    }

    // Preserve uppercase if Shift is held or CapsLock active
    if (e.shiftKey) {
      char = char.toUpperCase();
    }

    return char;
  }
}

window.layoutManager = new LayoutManager();