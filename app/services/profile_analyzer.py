import json
from datetime import datetime
from app import db
from app.models.typing import TypingDNA

LEFT_HAND_KEYS = set("qwertasdfgzxcvbQWERTASDFGZXCVB12345~!@#$%")
RIGHT_HAND_KEYS = set("yuiophjklnmYUIOPHJKLNM67890^&*()_+{}|:\"<>?`-=[]\\;',./")
PUNCTUATION_KEYS = set("~!@#$%^&*()_+{}|:\"<>?`-=[]\\;',./")
NUMBER_KEYS = set("0123456789")

class ProfileAnalyzer:
    @staticmethod
    def update_dna(user_id, events):
        if not user_id or not events:
            return

        dna = TypingDNA.query.filter_by(user_id=user_id).first()
        if not dna:
            dna = TypingDNA(
                user_id=user_id,
                left_hand_accuracy=100.0,
                right_hand_accuracy=100.0,
                punctuation_accuracy=100.0,
                numbers_accuracy=100.0,
                capitals_accuracy=100.0,
                rhythm_consistency_avg=100.0,
                key_stats_json='{}',
                confusion_matrix_json='{}'
            )
            db.session.add(dna)
            db.session.flush()

        stats = dna.get_key_stats()
        confusions = dna.get_confusion_matrix()

        left_c, left_err = 0, 0
        right_c, right_err = 0, 0
        punct_c, punct_err = 0, 0
        num_c, num_err = 0, 0
        cap_c, cap_err = 0, 0

        for i, ev in enumerate(events):
            exp = ev.get('expected', '')
            typed = ev.get('typed', '')
            correct = ev.get('correct', False)

            if not exp:
                continue

            if exp not in stats:
                stats[exp] = {'total': 0, 'errors': 0, 'delays': []}
            stats[exp]['total'] = stats[exp].get('total', 0) + 1

            if not correct:
                stats[exp]['errors'] = stats[exp].get('errors', 0) + 1
                confusions.setdefault(exp, {})
                confusions[exp][typed] = confusions[exp].get(typed, 0) + 1

            if i > 0:
                dt = ev.get('timestamp', 0) - events[i-1].get('timestamp', 0)
                if 0 < dt < 2.0:
                    stats[exp].setdefault('delays', [])
                    stats[exp]['delays'].append(round(dt, 3))
                    if len(stats[exp]['delays']) > 50:
                        stats[exp]['delays'].pop(0)

            if exp in LEFT_HAND_KEYS:
                left_c += 1
                if not correct: left_err += 1
            if exp in RIGHT_HAND_KEYS:
                right_c += 1
                if not correct: right_err += 1
            if exp in PUNCTUATION_KEYS:
                punct_c += 1
                if not correct: punct_err += 1
            if exp in NUMBER_KEYS:
                num_c += 1
                if not correct: num_err += 1
            if exp.isupper():
                cap_c += 1
                if not correct: cap_err += 1

        def calc_acc(total, err, current_val):
            if total == 0:
                return current_val or 100.0
            session_acc = ((total - err) / total) * 100.0
            base = current_val if current_val is not None else 100.0
            return round((base * 0.7) + (session_acc * 0.3), 1)

        dna.left_hand_accuracy = calc_acc(left_c, left_err, dna.left_hand_accuracy)
        dna.right_hand_accuracy = calc_acc(right_c, right_err, dna.right_hand_accuracy)
        dna.punctuation_accuracy = calc_acc(punct_c, punct_err, dna.punctuation_accuracy)
        dna.numbers_accuracy = calc_acc(num_c, num_err, dna.numbers_accuracy)
        dna.capitals_accuracy = calc_acc(cap_c, cap_err, dna.capitals_accuracy)
        dna.key_stats_json = json.dumps(stats)
        dna.confusion_matrix_json = json.dumps(confusions)
        dna.updated_at = datetime.utcnow()

        db.session.commit()