import random
from app.models.arcade_content import ArcadeContentItem
from app.models.typing import TypingDNA

DEFAULT_WORDBANK = {
    'beginner': [
        "cat", "sun", "dog", "run", "sky", "red", "cup", "box", "key", "pen", 
        "map", "hat", "top", "ice", "fly", "car", "sea", "air", "day", "art"
    ],
    'intermediate': [
        "planet", "kinetic", "stream", "rhythm", "velocity", "circuit", "matrix", 
        "focus", "cadence", "tactile", "engine", "quantum", "sphere", "anchor",
        "balance", "command", "transit", "standard", "channel", "motion", "action"
    ],
    'advanced': [
        "algorithm", "asynchronous", "biometric", "cryptographic", "differentiation",
        "electromagnetic", "heterogeneous", "infrastructure", "jurisdiction", 
        "nanotechnology", "neurochemical", "orthogonal", "pharmaceutical", "photosynthesis"
    ],
    'expert': [
        "anachronistic", "circumlocution", "epistemological", "grandiloquent",
        "idiosyncrasy", "juxtaposition", "lexicographical", "metamorphosis",
        "panegyric", "phenomenological", "sesquipedalian", "synchronicity"
    ]
}

CIPHER_SEQUENCES = {
    'level_1': ["7A9F", "B42C", "X98K", "M441", "Q309", "12FF", "A01B"],
    'level_2': ["0x7FA9", "0xDE4B", "0x91C0", "0xAA12", "0xFF00", "0x00A1", "0x33C2"],
    'level_3': ["PORT:443", "AES-256", "HASH#994", "KEY$881", "SYS!110", "TLS/1.3"],
    'level_4': ["const x = 0x4F;", "while(true){}", "db.query()", "git commit -m", "chmod 777"]
}

KEYBOARD_QUEST_CURRICULUM = [
    {"level": 1, "title": "Home Row Anchor", "keys": "asdf jkl;", "targets": ["a", "s", "d", "f", "j", "k", "l", ";", "fad", "glad", "flask", "half"]},
    {"level": 2, "title": "Top Row Reaches", "keys": "qwer tyui op", "targets": ["quit", "wire", "tree", "pure", "power", "tower", "quote", "write"]},
    {"level": 3, "title": "Bottom Row Tucks", "keys": "zxcv bnm", "targets": ["zinc", "calm", "move", "bomb", "cabin", "vanish", "mimic", "comb"]},
    {"level": 4, "title": "Top Row Numbers", "keys": "12345 67890", "targets": ["102", "394", "582", "710", "934", "681", "205", "461"]},
    {"level": 5, "title": "Symbols & Brackets", "keys": "{} [] () <> /", "targets": ["{x}", "[y]", "(z)", "<w>", "a/b", "{[]}", "<()>", "[{}]"]}
]

class ArcadeContentEngine:
    @staticmethod
    def get_content_batch(game_mode, difficulty='intermediate', count=20, user_id=None, extra_filters=None):
        """
        Retrieves curated content from DB or fallbacks, injecting user-weak keys if applicable.
        """
        extra_filters = extra_filters or {}
        difficulty = difficulty.lower()
        
        # 1. Check for weak-key targeting
        weak_keys = []
        if user_id and extra_filters.get('target_weaknesses'):
            dna = TypingDNA.query.filter_by(user_id=user_id).first()
            if dna:
                stats = dna.get_key_stats()
                for k, v in stats.items():
                    if v.get('total', 0) >= 3 and (v.get('errors', 0) / v['total']) > 0.08:
                        weak_keys.append(k.lower())

        # 2. Query DB content items
        items = ArcadeContentItem.query.filter_by(
            game_mode=game_mode, 
            difficulty=difficulty, 
            is_active=True
        ).limit(100).all()

        if items:
            texts = [i.target_text for i in items]
            random.shuffle(texts)
            return texts[:count]

        # 3. Dedicated Game Fallbacks
        if game_mode in ['falling_words', 'speed_racer', 'word_blitz', 'typing_ninja', 'space_defender']:
            pool = DEFAULT_WORDBANK.get(difficulty, DEFAULT_WORDBANK['intermediate'])
            if weak_keys:
                # Prioritize words with weak keys
                matched = [w for w in pool if any(k in w for k in weak_keys)]
                if len(matched) >= count:
                    return random.sample(matched, count)
            return [random.choice(pool) for _ in range(count)]

        elif game_mode == 'bubble_pop':
            target_type = extra_filters.get('bubble_target_type', 'lowercase')
            if target_type == 'uppercase':
                chars = [chr(i) for i in range(65, 91)]
            elif target_type == 'numbers':
                chars = [str(i) for i in range(10)]
            elif target_type == 'symbols':
                chars = list("!@#$%^&*()-_=+[]{}|;:,.<>?/")
            elif target_type == 'weak_keys' and weak_keys:
                chars = [k.upper() for k in weak_keys] * 5
            else:
                chars = [chr(i) for i in range(97, 123)]
            return [random.choice(chars) for _ in range(count)]

        elif game_mode == 'cipher_hacker':
            layer = extra_filters.get('layer', 1)
            layer_key = f"level_{min(4, layer)}"
            return CIPHER_SEQUENCES.get(layer_key, CIPHER_SEQUENCES['level_1'])

        elif game_mode == 'bomb_defuse':
            # Returns progressive codes of increasing length
            codes = []
            for i in range(count):
                length = min(12, 3 + (i // 2))
                pool = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789!@#" if difficulty in ['advanced', 'expert'] else "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
                codes.append("".join(random.choices(pool, k=length)))
            return codes

        elif game_mode == 'keyboard_quest':
            stage = extra_filters.get('stage', 1) - 1
            stage_data = KEYBOARD_QUEST_CURRICULUM[min(len(KEYBOARD_QUEST_CURRICULUM) - 1, max(0, stage))]
            return stage_data['targets']

        elif game_mode == 'memory_type':
            # Flash sequences (words or character strings)
            sequences = []
            length_base = 3 if difficulty == 'beginner' else (5 if difficulty == 'intermediate' else 7)
            for _ in range(count):
                pool = "abcdefghijklmnopqrstuvwxyz" if difficulty != 'expert' else "abcdefghijklmnopqrstuvwxyz0123456789!@#"
                sequences.append("".join(random.choices(pool, k=length_base)))
            return sequences

        # Fallback word generator
        return random.sample(DEFAULT_WORDBANK['intermediate'], min(count, len(DEFAULT_WORDBANK['intermediate'])))