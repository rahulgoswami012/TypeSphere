import random
from app.models.typing import TypingDNA

COMMON_NGRAMS = {
    'th': ['the', 'that', 'with', 'other', 'their', 'there', 'think', 'method'],
    'he': ['when', 'where', 'whether', 'together', 'rather', 'leather', 'theory'],
    'in': ['into', 'point', 'maintain', 'infinite', 'origin', 'within', 'train'],
    'er': ['operator', 'order', 'pattern', 'modern', 'server', 'different', 'letter'],
    'an': ['balance', 'command', 'transit', 'standard', 'constant', 'channel'],
    're': ['response', 'record', 'current', 'direct', 'reaction', 'regular'],
    'on': ['condition', 'action', 'button', 'connection', 'session', 'direction'],
    'at': ['matrix', 'format', 'update', 'database', 'strategy', 'accurate'],
    'ed': ['started', 'loaded', 'executed', 'streamed', 'controlled', 'proceed']
}

class WeaknessCoach:
    @staticmethod
    def analyze_and_recommend(user_id):
        """
        Transforms abstract key telemetry into immediate next-step actions across
        the Academy, specific practice drills, and arcade games.
        """
        if not user_id:
            return {
                'has_data': False,
                'weak_keys': ['E', 'T', 'O', 'N'],
                'recommendation': {
                    'title': 'Calibration Drill',
                    'reason': 'Sign in and complete 3 standard tests to generate a personalized fingerprint.',
                    'action_label': 'Start Practice',
                    'action_url': '/typing/?mode=timed&duration=60',
                    'stage_recommendation': 'Stage 1: Home Row',
                    'game_recommendation': 'Speed Racer'
                }
            }

        dna = TypingDNA.query.filter_by(user_id=user_id).first()
        if not dna:
            return {
                'has_data': False,
                'weak_keys': ['A', 'S', 'D', 'F'],
                'recommendation': {
                    'title': 'Establish Baseline',
                    'reason': 'Your typing DNA requires at least one benchmark test to pinpoint hesitations.',
                    'action_label': 'Take Benchmark Test',
                    'action_url': '/typing/?mode=timed&duration=60',
                    'stage_recommendation': 'Stage 1: Home Row',
                    'game_recommendation': 'Falling Words'
                }
            }

        stats = dna.get_key_stats()
        confusions = dna.get_confusion_matrix()

        # 1. Identify slow & error-prone keys
        scored_keys = []
        for char, data in stats.items():
            if data.get('total', 0) >= 5 and char.isalpha():
                err_rate = data.get('errors', 0) / data['total']
                delays = data.get('delays', [0.15])
                avg_delay = sum(delays) / len(delays) if delays else 0.15
                # Composite score: Error rate weighted 70%, latency delay weighted 30%
                severity = (err_rate * 0.7) + (min(avg_delay, 0.5) * 0.3)
                scored_keys.append((char.lower(), err_rate, avg_delay, severity))

        scored_keys.sort(key=lambda x: x[3], reverse=True)
        top_weak = [k[0] for k in scored_keys[:4]] if scored_keys else ['e', 'r', 't']

        # 2. Check Punctuation & Numeric Imbalances
        punct_acc = dna.punctuation_accuracy or 100.0
        num_acc = dna.numbers_accuracy or 100.0

        if punct_acc < 90.0:
            rec = {
                'title': 'Punctuation Cadence Imbalance',
                'reason': f'Your punctuation accuracy ({punct_acc:.1f}%) is noticeably lower than your baseline speed.',
                'action_label': 'Drill Punctuation',
                'action_url': '/typing/?content_type=punctuation&duration=60',
                'stage_recommendation': 'Stage 9: Punctuation & Symbols',
                'game_recommendation': 'Bubble Pop (Symbols Mode)'
            }
        elif num_acc < 88.0:
            rec = {
                'title': 'Numeric Row Reaches',
                'reason': f'Your number row accuracy ({num_acc:.1f}%) causes significant hesitations during typing.',
                'action_label': 'Drill Numeric Reaches',
                'action_url': '/typing/?content_type=numbers&duration=60',
                'stage_recommendation': 'Stage 8: Number Row Reaches',
                'game_recommendation': 'Bomb Defuse'
            }
        elif top_weak:
            top_char = top_weak[0].upper()
            rec = {
                'title': f"Targeting Weak Keys: {', '.join(k.upper() for k in top_weak)}",
                'reason': f"Frequent mistypes and hesitations detected on key '{top_char}' during velocity bursts.",
                'action_label': 'Launch Adaptive Drill',
                'action_url': '/typing/?mode=adaptive',
                'stage_recommendation': 'Stage 5: Key Combinations',
                'game_recommendation': 'Typing Ninja'
            }
        else:
            rec = {
                'title': 'Velocity & Flow Maintenance',
                'reason': 'Your finger balance is stable across the home row. Focus on increasing raw speed.',
                'action_label': 'Enter 60s Speed Sprint',
                'action_url': '/typing/?mode=timed&duration=60',
                'stage_recommendation': 'Stage 10: Speed Building',
                'game_recommendation': 'Speed Racer'
            }

        return {
            'has_data': True,
            'weak_keys': [k.upper() for k in top_weak],
            'recommendation': rec
        }