"""
TypeSphere - Autonomous Dynamic AI Flight Coach Engine
Inspects user TypingDNA telemetry, diagnoses neuromuscular faults,
and dynamically queries matching passages from the database library
to formulate personalized training classes without manual CMS overhead.
"""

import re
import random
from typing import Tuple, List, Dict, Any


class AdaptiveTrainingService:
    @staticmethod
    def diagnose_pilot(user_id: int) -> Dict[str, Any]:
        """
        Performs a full diagnostic evaluation of the pilot's telemetry history.
        """
        from app.models.typing import TypingDNA, TypingTest

        if not user_id:
            return {
                'has_data': False,
                'status': 'uncalibrated',
                'weak_keys': ['E', 'T', 'A', 'O'],
                'top_confusions': [],
                'hand_imbalance': None,
                'avg_wpm': 45.0,
                'avg_acc': 95.0,
                'primary_fault': 'baseline_calibration'
            }

        dna = TypingDNA.query.filter_by(user_id=user_id).first()
        recent_tests = TypingTest.query.filter_by(
            user_id=user_id,
            suspicious=False
        ).order_by(TypingTest.completed_at.desc()).limit(10).all()

        if not dna or not recent_tests:
            return {
                'has_data': False,
                'status': 'uncalibrated',
                'weak_keys': ['E', 'R', 'T'],
                'top_confusions': [],
                'hand_imbalance': None,
                'avg_wpm': 40.0,
                'avg_acc': 94.0,
                'primary_fault': 'baseline_calibration'
            }

        # Calculate fleet averages for this pilot
        avg_wpm = round(sum(t.wpm for t in recent_tests) / len(recent_tests), 1)
        avg_acc = round(sum(t.accuracy for t in recent_tests) / len(recent_tests), 1)

        # 1. Identify slow and error-prone keys from DNA stats
        stats = dna.get_key_stats()
        scored_keys = []
        for char, data in stats.items():
            if data.get('total', 0) >= 4 and char.isalpha():
                err_rate = data.get('errors', 0) / data['total']
                delays = data.get('delays', [0.15])
                avg_delay = sum(delays) / len(delays) if delays else 0.15
                severity = (err_rate * 0.7) + (min(avg_delay, 0.5) * 0.3)
                if err_rate > 0.05 or avg_delay > 0.28:
                    scored_keys.append((char.lower(), err_rate, avg_delay, severity))

        scored_keys.sort(key=lambda x: x[3], reverse=True)
        weak_keys = [k[0] for k in scored_keys[:4]]

        # 2. Extract top confusion pairs
        confusions = dna.get_confusion_matrix()
        top_confusions = []
        for exp, mapped in confusions.items():
            for got, cnt in mapped.items():
                if cnt >= 2 and exp.isalpha() and got.isalpha():
                    top_confusions.append((exp.upper(), got.upper(), cnt))
        top_confusions.sort(key=lambda x: x[2], reverse=True)

        # 3. Detect Bilateral Hand & Category Imbalances
        left_acc = dna.left_hand_accuracy or 100.0
        right_acc = dna.right_hand_accuracy or 100.0
        punct_acc = dna.punctuation_accuracy or 100.0
        num_acc = dna.numbers_accuracy or 100.0

        hand_diff = round(abs(left_acc - right_acc), 1)
        hand_imbalance = None
        if hand_diff >= 4.5:
            weaker_hand = "Left" if left_acc < right_acc else "Right"
            hand_imbalance = {
                'weaker_hand': weaker_hand,
                'diff': hand_diff,
                'left_acc': left_acc,
                'right_acc': right_acc
            }

        # 4. Determine Primary Flight Fault
        if punct_acc < 90.0:
            primary_fault = 'punctuation_deficit'
        elif num_acc < 88.0:
            primary_fault = 'numeric_deficit'
        elif hand_imbalance:
            primary_fault = 'bilateral_imbalance'
        elif weak_keys:
            primary_fault = 'weak_keys'
        elif avg_acc >= 97.0 and avg_wpm >= 50.0:
            primary_fault = 'velocity_expansion'
        else:
            primary_fault = 'cadence_flow'

        return {
            'has_data': True,
            'status': 'calibrated',
            'weak_keys': [k.upper() for k in weak_keys],
            'top_confusions': top_confusions[:3],
            'hand_imbalance': hand_imbalance,
            'punct_acc': punct_acc,
            'num_acc': num_acc,
            'avg_wpm': avg_wpm,
            'avg_acc': avg_acc,
            'primary_fault': primary_fault
        }

    @staticmethod
    def generate_drill(user_id: int) -> Tuple[str, List[str], Dict[str, Any]]:
        """
        Dynamically formulates an AI flight class by querying the existing
        database library for passages that naturally reinforce the diagnosed weakness.
        """
        from app.models.typing import TypingText

        diag = AdaptiveTrainingService.diagnose_pilot(user_id)
        fault = diag.get('primary_fault', 'baseline_calibration')
        weak_keys = diag.get('weak_keys', ['E', 'R', 'T'])
        avg_wpm = diag.get('avg_wpm', 45.0)

        active_passages = TypingText.query.filter(
            (TypingText.is_active == True) &
            ((TypingText.status == 'published') | (TypingText.status == None))
        ).all()

        class_profile = {
            'class_code': 'FC-101',
            'class_name': 'Foundational Flight Calibration',
            'target_wpm': max(25, round(avg_wpm + 3)),
            'target_accuracy': 96.0,
            'focus_tokens': weak_keys,
            'diagnostic_reason': 'Establish baseline rhythm across standard high-frequency English vocabulary.',
            'matched_passage_title': 'General Aviation Corpus'
        }

        # Fault A: Punctuation Deficit
        if fault == 'punctuation_deficit':
            candidates = [p for p in active_passages if p.category in ['exam', 'professional', 'punctuation'] or p.is_code]
            if not candidates:
                candidates = active_passages

            selected = random.choice(candidates) if candidates else None
            drill_text = selected.content.strip() if selected else (
                "Official public communications require scrupulous adherence to statutory punctuation; semicolons, colons, and quotation marks establish administrative clarity."
            )
            class_profile.update({
                'class_code': 'P-101',
                'class_name': 'Class P-1: Punctuation & Syntax Realignment',
                'target_wpm': max(20, round(avg_wpm - 2)),
                'target_accuracy': 98.0,
                'focus_tokens': [';', ':', '"', ',', '.'],
                'diagnostic_reason': f"Your punctuation accuracy ({diag.get('punct_acc')}%) lags behind your base speed. This class exercises edge punctuation anchors.",
                'matched_passage_title': selected.title if selected else 'Administrative Gazette'
            })
            return drill_text, [';', ':', '"'], class_profile

        # Fault B: Numeric Reach Deficit
        elif fault == 'numeric_deficit':
            candidates = [p for p in active_passages if p.category in ['numbers', 'data_entry'] or any(c.isdigit() for c in p.content)]
            selected = random.choice(candidates) if candidates else None
            drill_text = selected.content.strip() if selected else (
                "Invoice 8402 total 195 dollars on 2026-09-15 tracking number 7391054 with 42 units dispatched across sector 10."
            )
            class_profile.update({
                'class_code': 'N-201',
                'class_name': 'Class N-1: Top-Row Numeric Trajectory',
                'target_wpm': max(22, round(avg_wpm - 4)),
                'target_accuracy': 97.0,
                'focus_tokens': ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
                'diagnostic_reason': f"Your number row accuracy ({diag.get('num_acc')}%) causes hesitation spikes. This class trains upward vertical reaches without wrist shifting.",
                'matched_passage_title': selected.title if selected else 'Data Telemetry Ledger'
            })
            return drill_text, ['1', '2', '3', '8', '9'], class_profile

        # Fault C: Bilateral Hand Imbalance
        elif fault == 'bilateral_imbalance' and diag.get('hand_imbalance'):
            imb = diag['hand_imbalance']
            weaker = imb['weaker_hand']
            class_profile.update({
                'class_code': 'H-301',
                'class_name': f'Class H-1: Bilateral Cadence Balance ({weaker} Hand Focus)',
                'target_wpm': round(avg_wpm),
                'target_accuracy': 97.5,
                'focus_tokens': ['ASDF', 'JKL;'],
                'diagnostic_reason': f"A {imb['diff']}% accuracy gap was detected between hands ({imb['left_acc']}% L vs {imb['right_acc']}% R). This class restores equilibrium.",
                'matched_passage_title': 'Balanced Aeronautical Corpus'
            })
            candidates = [p for p in active_passages if p.category in ['Literature', 'Daily Life', 'paragraphs', 'words']]
            selected = random.choice(candidates) if candidates else None
            drill_text = selected.content.strip() if selected else (
                "Calm hands strike cleanly and decisively without second-guessing. Breathe steadily and let cadence carry velocity across both sides of the keyboard."
            )
            return drill_text, weak_keys, class_profile

        # Fault D: Specific Weak Keys
        elif fault == 'weak_keys' and weak_keys:
            scored = []
            for p in active_passages:
                content_lower = p.content.lower()
                matches = sum(content_lower.count(k.lower()) for k in weak_keys)
                density = matches / max(1, p.word_count)
                scored.append((p, density))

            scored.sort(key=lambda x: x[1], reverse=True)
            best_passage = scored[0][0] if scored else None

            drill_text = best_passage.content.strip() if best_passage else (
                "Continuous deliberate movement compounds into unstoppable tactile velocity under intense pressure. Keep your resting fingers anchored firmly."
            )

            words = drill_text.split()
            if len(words) > 80:
                drill_text = " ".join(words[:80])

            class_profile.update({
                'class_code': f"K-{len(weak_keys)}01",
                'class_name': f"Class K-{len(weak_keys)}: Precision Realignment on [{', '.join(weak_keys)}]",
                'target_wpm': max(25, round(avg_wpm + 2)),
                'target_accuracy': 97.0,
                'focus_tokens': weak_keys,
                'diagnostic_reason': f"Sensors isolated latency spikes and errant strikes on [{', '.join(weak_keys)}]. This class queries library passages rich in these specific n-grams.",
                'matched_passage_title': best_passage.title if best_passage else 'Targeted Corpus'
            })
            return drill_text, weak_keys, class_profile

        # Fault E: Velocity Expansion
        elif fault == 'velocity_expansion':
            candidates = [p for p in active_passages if p.difficulty in ['hard', 'expert'] or p.category in ['Technology', 'Science', 'professional']]
            selected = random.choice(candidates) if candidates else None
            drill_text = selected.content.strip() if selected else (
                "The afterburners ignited with a deafening roar as the interceptor surged through the sound barrier into open airspace. Fast reactions lock trajectory on target."
            )
            class_profile.update({
                'class_code': 'V-501',
                'class_name': 'Class V-1: Supersonic Cruising Velocity Expansion',
                'target_wpm': max(50, round(avg_wpm + 8)),
                'target_accuracy': 95.0,
                'focus_tokens': ['Sprint Cadence'],
                'diagnostic_reason': f"Flawless accuracy ({avg_acc}%) achieved on recent flights. The coach is lifting your speed ceiling into the next division.",
                'matched_passage_title': selected.title if selected else 'Supersonic Intercept'
            })
            return drill_text, [], class_profile

        # Default Fallback: Balanced Prose
        selected = random.choice(active_passages) if active_passages else None
        drill_text = selected.content.strip() if selected else (
            "Consistency is the hallmark of the master pilot. Every accurate strike compounds into pure flow and unmatched tactile velocity."
        )
        class_profile['matched_passage_title'] = selected.title if selected else 'Core Library'
        return drill_text, weak_keys, class_profile


__all__ = ['AdaptiveTrainingService']