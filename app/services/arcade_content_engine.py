import random
from app.models.arcade_content import ArcadeContentItem
from app.models.typing import TypingDNA

DEFAULT_WORDBANKS = {
    'easy': [
        "sun", "cat", "dog", "run", "sky", "red", "cup", "box", "key", "pen",
        "map", "hat", "top", "ice", "fly", "car", "sea", "air", "day", "art",
        "glad", "tree", "fast", "blue", "gold", "wind", "lamp", "book", "ship"
    ],
    'moderate': [
        "planet", "kinetic", "stream", "rhythm", "velocity", "circuit", "matrix",
        "focus", "cadence", "tactile", "engine", "quantum", "sphere", "anchor",
        "balance", "command", "transit", "standard", "channel", "motion", "action",
        "control", "forward", "measure", "pattern", "dynamic", "pressure", "network"
    ],
    'hard': [
        "algorithm", "asynchronous", "biometric", "cryptographic", "differentiation",
        "electromagnetic", "heterogeneous", "infrastructure", "jurisdiction",
        "nanotechnology", "neurochemical", "orthogonal", "pharmaceutical", "photosynthesis",
        "reconciliation", "sophisticated", "synchronization", "unprecedented", "telemetry"
    ],
    'expert': [
        "anachronistic", "antediluvian", "circumlocution", "counterintuitive",
        "crystallization", "deleterious", "disproportionate", "epistemological",
        "existentialism", "grandiloquent", "idiosyncrasy", "juxtaposition",
        "lexicographical", "magnanimous", "metamorphosis", "multidimensional",
        "panegyric", "phenomenological", "sesquipedalian", "synchronicity"
    ]
}

SPEED_RACER_TRACKS = {
    'easy': [
        "The car sped down the sunny track as the green flag waved to start the race.",
        "Smooth turns and steady hands keep the engine cool and the momentum high.",
        "Accelerate past the line with clean shifts and calm focus on every movement."
    ],
    'moderate': [
        "The open highway stretched across the desert floor under a wide expanse of pale morning sky. High velocity demands relaxed control and steady breathing. When the throttle opens every second compounds into pure forward momentum.",
        "Aerodynamic contours slice through the crosswinds while tire grip holds the apex through turn four. Precision steering and rhythmic engine shifts maintain the optimal racing line.",
        "Competitive speed is born from calculated motion. Downshifting before the curve preserves brake integrity and guarantees blistering acceleration down the main straight."
    ],
    'hard': [
        "Turbocharged combustion engines synchronize fuel injection micro-pulses across high-octane cylinders. Navigating high-speed chicanes without losing tire adhesion requires instantaneous neuromuscular reactions and unyielding concentration.",
        "Telemetry monitors indicate optimal differential gear lockup through the banking sequence. Balancing throttle modulation against mechanical slip angles differentiates elite drivers from the rest of the grid."
    ],
    'expert': [
        "Carbon-composite aerodynamic splitters generate tremendous localized downforce, counteracting high-velocity vortex turbulence through asymmetrical chicanes. Maintaining peak mechanical efficiency under extreme thermal dissipation separates champions."
    ]
}

CHARACTER_COLLECTIONS = {
    'letters': [chr(i) for i in range(97, 123)],
    'uppercase': [chr(i) for i in range(65, 91)],
    'numbers': [str(i) for i in range(10)],
    'symbols': list("!@#$%^&*()-_=+[]{}|;:,.<>?/"),
    'punctuation': list(".,;:!?'\"-()")
}

class ArcadeContentEngine:
    @staticmethod
    def get_content_batch(game_mode, difficulty='moderate', count=25, user_id=None, extra_filters=None):
        extra_filters = extra_filters or {}
        diff = difficulty.lower() if difficulty.lower() in DEFAULT_WORDBANKS else 'moderate'
        
        weak_keys = []
        if user_id and extra_filters.get('target_weaknesses'):
            dna = TypingDNA.query.filter_by(user_id=user_id).first()
            if dna:
                stats = dna.get_key_stats()
                for k, v in stats.items():
                    if v.get('total', 0) >= 4 and (v.get('errors', 0) / v['total']) > 0.07:
                        weak_keys.append(k.lower())

        # Speed Racer Passages
        if game_mode == 'speed_racer':
            passages = SPEED_RACER_TRACKS.get(diff, SPEED_RACER_TRACKS['moderate'])
            return [random.choice(passages)]

        # Bubble Pop Single Characters
        if game_mode == 'bubble_pop':
            char_mode = extra_filters.get('char_mode', 'letters')
            if char_mode == 'weak_keys' and weak_keys:
                pool = [k.upper() for k in weak_keys] * 6
            elif char_mode == 'letters_numbers':
                pool = CHARACTER_COLLECTIONS['letters'] + CHARACTER_COLLECTIONS['numbers']
            elif char_mode == 'mixed_all':
                pool = (CHARACTER_COLLECTIONS['letters'] + CHARACTER_COLLECTIONS['uppercase'] + 
                        CHARACTER_COLLECTIONS['numbers'] + CHARACTER_COLLECTIONS['symbols'])
            else:
                pool = CHARACTER_COLLECTIONS.get(char_mode, CHARACTER_COLLECTIONS['letters'])
            return [random.choice(pool) for _ in range(count)]

        # Cipher Hacker Layers
        if game_mode == 'cipher_hacker':
            layer_schemes = {
                'easy': [["0xA1", "0xB2", "0xC3", "0xD4"], ["PORT:80", "SSL:ON", "SYS:OK"], ["HASH_44", "NET_99"]],
                'moderate': [["0x7FA9", "0xDE4B", "0x91C0"], ["AES_256", "SHA_512", "TLS_13"], ["chmod 755", "int main()"]],
                'hard': [["0xDEADBEEF", "0xCAFEBABE"], ["RSA_4096_PKCS", "ECDSA_P384"], ["void* ptr = malloc(sz);"]],
                'expert': [["0xFF00AA55BB66CC77"], ["const auto&& lambda = [](){};"], ["while(asm volatile(\"\")){}"]]
            }
            return layer_schemes.get(diff, layer_schemes['moderate'])

        # Whack-A-Word Targets
        if game_mode == 'whack_a_word':
            target_type = extra_filters.get('target_type', 'words')
            if target_type == 'characters':
                return [random.choice(CHARACTER_COLLECTIONS['letters']) for _ in range(count)]
            if target_type == 'numbers':
                return [str(random.randint(10, 9999)) for _ in range(count)]
            if target_type == 'symbols':
                return [random.choice(CHARACTER_COLLECTIONS['symbols']) for _ in range(count)]
            return random.sample(DEFAULT_WORDBANKS[diff], min(count, len(DEFAULT_WORDBANKS[diff])))

        # Bomb Defuse Codes
        if game_mode == 'bomb_defuse':
            codes = []
            base_len = {'easy': 4, 'moderate': 6, 'hard': 8, 'expert': 10}.get(diff, 6)
            pool = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
            if diff in ['hard', 'expert']:
                pool += "#!$%&*"
            for i in range(count):
                codes.append("".join(random.choices(pool, k=base_len + (i // 2))))
            return codes

        # Generic Word Pool (Falling Words, Zombie Defense, Space Defender, Typing Ninja)
        pool = DEFAULT_WORDBANKS.get(diff, DEFAULT_WORDBANKS['moderate'])
        if weak_keys:
            matched = [w for w in pool if any(k in w for k in weak_keys)]
            if len(matched) >= count:
                return random.sample(matched, count)
        return random.sample(pool, min(count, len(pool)))