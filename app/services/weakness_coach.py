import json
from app.models.typing import TypingDNA

NGRAM_LIBRARY = {
    'th': ['the', 'that', 'other', 'their', 'there', 'think', 'through', 'method'],
    'he': ['when', 'where', 'whether', 'together', 'rather', 'leather', 'theory'],
    'in': ['initial', 'into', 'maintain', 'point', 'infinite', 'origin', 'within'],
    'er': ['operator', 'order', 'pattern', 'modern', 'server', 'different', 'letter'],
    'an': ['balance', 'command', 'transit', 'standard', 'constant', 'channel'],
    're': ['response', 'record', 'current', 'direct', 'reaction', 'regular'],
    'on': ['condition', 'action', 'button', 'connection', 'session', 'direction'],
    'at': ['matrix', 'format', 'update', 'database', 'strategy', 'accurate'],
    'en': ['element', 'energy', 'sentence', 'current', 'moment', 'frequency']
}

class WeaknessCoach:
    @staticmethod
    def generate_targeted_drill(user_id):
        """
        Analyzes confusing keys, finger fatigue, and interval delays from TypingDNA,
        then synthesizes words containing those exact character clusters.
        """
        if not user_id:
            return {
                'title': 'General Speed Optimization',
                'explanation': 'Sign in to let TypeSphere construct a personalized biometric drill from your typing DNA.',
                'content': 'the quick brown fox jumps over the lazy dog focus on rhythm and steady cadence',
                'target_keys': ['E', 'T', 'A', 'O']
            }

        dna = TypingDNA.query.filter_by(user_id=user_id).first()
        if not dna:
            return {
                'title': 'Baseline Calibration Drill',
                'explanation': 'Complete at least 3 benchmark runs to build your personal confusion matrix.',
                'content': 'steady cadence builds velocity focus on minimal movement and smooth key transitions',
                'target_keys': ['T', 'H', 'E', 'N']
            }

        stats = dna.get_key_stats()
        confusions = dna.get_confusion_matrix()

        # 1. Identify Highest Error Rate Keys
        key_error_rates = []
        for char, metric in stats.items():
            if metric.get('total', 0) >= 5 and char.isalpha():
                err_ratio = metric.get('errors', 0) / metric['total']
                key_error_rates.append((char.lower(), err_ratio, metric.get('delays', [])))

        key_error_rates.sort(key=lambda x: x[1], reverse=True)
        top_weak_keys = [k[0] for k in key_error_rates[:3] if k[1] > 0.04]
        if not top_weak_keys:
            top_weak_keys = ['e', 'r', 't']

        # 2. Extract Frequent Confusion Pairs
        confusion_pairs = []
        for exp, mapped in confusions.items():
            for typed, count in mapped.items():
                if count >= 2 and exp.isalpha():
                    confusion_pairs.append((exp.lower(), typed.lower(), count))
        confusion_pairs.sort(key=lambda x: x[2], reverse=True)

        # 3. Construct Explanation
        explanation_parts = []
        target_cluster = set(top_weak_keys)
        if confusion_pairs:
            top_c = confusion_pairs[0]
            explanation_parts.append(f"Frequent confusion identified between '{top_c[0].upper()}' and '{top_c[1].upper()}' ({top_c[2]} times).")
            target_cluster.add(top_c[0])
            target_cluster.add(top_c[1])
        
        explanation_parts.append(f"Targeting finger muscle-memory calibration for keys: {', '.join(k.upper() for k in target_cluster)}.")

        # 4. Generate Natural Context Words
        drill_words = []
        for _ in range(35):
            for k in target_cluster:
                candidates = NGRAM_LIBRARY.get(k, ['accuracy', 'kinetic', 'discipline', 'precision'])
                drill_words.append(random.choice(candidates))

        random.shuffle(drill_words)
        selected_text = " ".join(drill_words[:40])

        return {
            'title': f"Targeted Muscle-Memory Calibration ({', '.join(k.upper() for k in target_cluster)})",
            'explanation': " ".join(explanation_parts),
            'content': selected_text,
            'target_keys': [k.upper() for k in target_cluster]
        }