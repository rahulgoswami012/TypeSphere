import random
from app.models.typing import TypingDNA

WORD_BANK = {
    'e': ['elephant', 'energy', 'experience', 'every', 'element', 'evening'],
    'r': ['remember', 'regular', 'rhythm', 'running', 'reactive', 'reason'],
    't': ['together', 'target', 'thought', 'transit', 'training', 'total'],
    'o': ['opinion', 'operation', 'outcome', 'original', 'observe', 'option'],
    'i': ['initial', 'insight', 'infinite', 'imagine', 'install', 'improve'],
    'p': ['practice', 'pattern', 'process', 'program', 'purpose', 'profile'],
    'c': ['concentrate', 'current', 'constant', 'clarity', 'circuit', 'custom'],
    's': ['system', 'standard', 'steady', 'speed', 'stream', 'syntax'],
    'n': ['network', 'number', 'normal', 'notation', 'nature', 'nuance']
}

class AdaptiveTrainingService:
    @staticmethod
    def generate_drill(user_id):
        """
        Analyzes the user's DNA profile to find top 3 error-prone keys and generates a targeted drill.
        """
        dna = TypingDNA.query.filter_by(user_id=user_id).first()
        weak_keys = []

        if dna:
            stats = dna.get_key_stats()
            # Calculate error rate per key
            rates = []
            for k, val in stats.items():
                if val['total'] >= 5 and k.isalpha():
                    err_rate = val['errors'] / val['total']
                    rates.append((k.lower(), err_rate))
            rates.sort(key=lambda x: x[1], reverse=True)
            weak_keys = [k for k, r in rates[:3] if r > 0.05]

        if not weak_keys:
            weak_keys = ['e', 'r', 't', 'p']

        # Compose drill focusing on weak letter frequencies
        drill_words = []
        for _ in range(25):
            chosen_key = random.choice(weak_keys)
            words_for_key = WORD_BANK.get(chosen_key, ['quick', 'focus', 'accuracy', 'sphere'])
            drill_words.append(random.choice(words_for_key))

        random.shuffle(drill_words)
        return " ".join(drill_words), weak_keys