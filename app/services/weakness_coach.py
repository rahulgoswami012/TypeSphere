"""
TypeSphere - Weakness Coach Diagnostic Analyzer
Synthesizes user biometric telemetry into concrete operational prescriptions,
identifying which academy track and arcade discipline will best overcome their fault.
"""

from typing import Dict, Any


class WeaknessCoach:
    @staticmethod
    def analyze_and_recommend(user_id: int) -> Dict[str, Any]:
        """
        Synthesizes biometric telemetry into immediate actionable recommendations.
        Safe scoped import eliminates circular import locks during application boot.
        """
        from app.services.adaptive_training import AdaptiveTrainingService

        diag = AdaptiveTrainingService.diagnose_pilot(user_id)
        fault = diag.get('primary_fault', 'baseline_calibration')
        weak_keys = diag.get('weak_keys', ['E', 'T', 'O', 'N'])

        if not diag.get('has_data'):
            return {
                'has_data': False,
                'weak_keys': ['A', 'S', 'D', 'F'],
                'recommendation': {
                    'title': 'Establish Biometric Baseline',
                    'reason': 'Your typing DNA requires at least one benchmark flight to pinpoint hesitations and latency spikes.',
                    'action_label': 'Take Benchmark Flight',
                    'action_url': '/typing/?mode=timed&duration=60',
                    'stage_recommendation': 'Stage 1: Home Row Mastery',
                    'game_recommendation': 'Falling Words'
                }
            }

        # Case 1: Punctuation Deficit
        if fault == 'punctuation_deficit':
            rec = {
                'title': 'Punctuation Cadence Imbalance',
                'reason': f"Your punctuation accuracy ({diag.get('punct_acc')}%) is significantly below cruising speed. Complex brackets and sentence endings cause hesitation pauses.",
                'action_label': 'Engage Class P-1 Drill',
                'action_url': '/typing/?mode=adaptive',
                'stage_recommendation': 'Stage 9: Complex Symbols & Brackets',
                'game_recommendation': 'Bubble Pop (Symbols Mode)'
            }

        # Case 2: Numeric Row Deficit
        elif fault == 'numeric_deficit':
            rec = {
                'title': 'Numeric Row Vertical Reaches',
                'reason': f"Your number row accuracy ({diag.get('num_acc')}%) produces severe micro-hesitation stalls (>400ms). Training upward reaches will smooth your cadence.",
                'action_label': 'Engage Class N-1 Drill',
                'action_url': '/typing/?mode=adaptive',
                'stage_recommendation': 'Stage 8: Top Number Row Reaches',
                'game_recommendation': 'Bomb Defuse'
            }

        # Case 3: Bilateral Hand Imbalance
        elif fault == 'bilateral_imbalance' and diag.get('hand_imbalance'):
            imb = diag['hand_imbalance']
            rec = {
                'title': f"Bilateral Equilibrium Fault ({imb['weaker_hand']} Hand)",
                'reason': f"Sensors detected a {imb['diff']}% accuracy variance between hands ({imb['left_acc']}% Left vs {imb['right_acc']}% Right). Equilibrium drills will eliminate tension.",
                'action_label': 'Engage Class H-1 Drill',
                'action_url': '/typing/?mode=adaptive',
                'stage_recommendation': 'Stage 5: Contralateral Shift Synchronization',
                'game_recommendation': 'Zombie Duel'
            }

        # Case 4: Weak Keys Isolated
        elif fault == 'weak_keys' and weak_keys:
            top_char = weak_keys[0]
            rec = {
                'title': f"Targeting Precision Locks: [{', '.join(weak_keys)}]",
                'reason': f"Frequent mistypes and deceleration detected on key '{top_char}' during high-velocity bursts. The coach has queried passages targeting these n-grams.",
                'action_label': 'Launch Adaptive Class Drill',
                'action_url': '/typing/?mode=adaptive',
                'stage_recommendation': 'Stage 10: High-Speed N-Gram Sprints',
                'game_recommendation': 'Speed Racer'
            }

        # Case 5: Velocity Expansion
        elif fault == 'velocity_expansion':
            rec = {
                'title': 'Velocity Ceiling Expansion',
                'reason': f"Flawless stability maintained ({diag.get('avg_acc')}% accuracy). You are ready to accelerate cruising velocity by 8+ WPM without compromising accuracy.",
                'action_label': 'Launch Supersonic Sprint',
                'action_url': '/challenges/mission/supersonic_sprint',
                'stage_recommendation': 'Stage 12: Grandmaster Endurance Sprint',
                'game_recommendation': 'Speed Racer'
            }

        # Default: Flow & Cadence
        else:
            rec = {
                'title': 'Cadence Stability Maintenance',
                'reason': 'Your finger balance is stable across the home anchors. Continue sustaining consistent kinetic rhythm without second-guessing.',
                'action_label': 'Launch 60s Speed Sprint',
                'action_url': '/typing/?mode=timed&duration=60',
                'stage_recommendation': 'Stage 7: Complete Sentence Cadence',
                'game_recommendation': 'Typing Ninja'
            }

        return {
            'has_data': True,
            'weak_keys': weak_keys,
            'recommendation': rec
        }


__all__ = ['WeaknessCoach']