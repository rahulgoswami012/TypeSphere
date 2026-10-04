"""
TypeSphere - Universal Neuromorphic AI Typist Simulation Engine
Models authentic pilot archetypes with natural cadence jitter, hesitation stalls,
typo recoil recovery, and duration fatigue decay.
"""

import random
from typing import Dict, Any, Tuple

AI_PILOT_ARCHETYPES: Dict[str, list] = {
    'easy': [
        {
            'callsign': 'CADET ARROW',
            'archetype': 'steady_learner',
            'base_wpm': 28.0,
            'jitter': 5.0,
            'error_probability': 0.08,
            'hesitation_range_ms': (250, 500),
            'fatigue_factor': 0.03,
            'recovery_rate': 0.85
        },
        {
            'callsign': 'CADET ZEPHYR',
            'archetype': 'cautious_cruiser',
            'base_wpm': 34.0,
            'jitter': 4.0,
            'error_probability': 0.05,
            'hesitation_range_ms': (200, 420),
            'fatigue_factor': 0.02,
            'recovery_rate': 0.95
        }
    ],
    'moderate': [
        {
            'callsign': 'PILOT HORIZON',
            'archetype': 'cadence_cruiser',
            'base_wpm': 58.0,
            'jitter': 7.0,
            'error_probability': 0.045,
            'hesitation_range_ms': (120, 260),
            'fatigue_factor': 0.04,
            'recovery_rate': 0.92
        },
        {
            'callsign': 'PILOT STRIKE',
            'archetype': 'burst_sprinter',
            'base_wpm': 66.0,
            'jitter': 9.0,
            'error_probability': 0.06,
            'hesitation_range_ms': (90, 220),
            'fatigue_factor': 0.07,
            'recovery_rate': 0.88
        }
    ],
    'hard': [
        {
            'callsign': 'ACE VELOCITY',
            'archetype': 'tactical_precision',
            'base_wpm': 88.0,
            'jitter': 8.0,
            'error_probability': 0.02,
            'hesitation_range_ms': (60, 140),
            'fatigue_factor': 0.025,
            'recovery_rate': 0.98
        },
        {
            'callsign': 'ACE HYPERION',
            'archetype': 'aggressive_rusher',
            'base_wpm': 96.0,
            'jitter': 11.0,
            'error_probability': 0.035,
            'hesitation_range_ms': (40, 120),
            'fatigue_factor': 0.05,
            'recovery_rate': 0.90
        }
    ],
    'expert': [
        {
            'callsign': 'COMMANDER APEX',
            'archetype': 'grandmaster_ghost',
            'base_wpm': 122.0,
            'jitter': 10.0,
            'error_probability': 0.008,
            'hesitation_range_ms': (25, 70),
            'fatigue_factor': 0.015,
            'recovery_rate': 0.99
        },
        {
            'callsign': 'COMMANDER CYBERPULSE',
            'archetype': 'esports_machine',
            'base_wpm': 135.0,
            'jitter': 12.0,
            'error_probability': 0.012,
            'hesitation_range_ms': (20, 60),
            'fatigue_factor': 0.02,
            'recovery_rate': 0.98
        }
    ]
}


class AITypistSimulator:
    """
    Neuromorphic AI Typist generating authentic human-like typing telemetry.
    """
    def __init__(self, difficulty: str = 'moderate', player_target_wpm: float = None):
        diff = difficulty.lower() if difficulty and difficulty.lower() in AI_PILOT_ARCHETYPES else 'moderate'
        self.difficulty = diff
        pool = AI_PILOT_ARCHETYPES[self.difficulty]
        self.profile = random.choice(pool).copy()

        if player_target_wpm and player_target_wpm > 15.0:
            shift = random.uniform(-5.0, 5.0)
            self.profile['base_wpm'] = max(22.0, round(player_target_wpm + shift, 1))

        self.callsign = self.profile['callsign']
        self.current_wpm = self.profile['base_wpm']
        self.total_chars_typed = 0.0
        self.errors_count = 0
        self.progress_pct = 0.0
        self.elapsed_seconds = 0.0
        self.burst_cooldown = 0.0

    def step(self, delta_seconds: float, total_chars: int) -> Tuple[float, float]:
        """
        Advances the AI simulation by delta_seconds.
        Returns: (progress_percentage, current_net_wpm)
        """
        if total_chars <= 0:
            return 0.0, round(self.current_wpm, 1)

        if self.progress_pct >= 100.0:
            return 100.0, round(self.current_wpm, 1)

        self.elapsed_seconds += delta_seconds

        # 1. Cadence Jitter
        jitter = random.uniform(-self.profile['jitter'], self.profile['jitter'])

        # 2. Fatigue Decay
        fatigue = min(15.0, self.elapsed_seconds * self.profile['fatigue_factor'])

        # 3. Burst Acceleration
        self.burst_cooldown -= delta_seconds
        burst_bonus = 0.0
        if self.burst_cooldown <= 0.0 and random.random() < 0.14:
            burst_bonus = random.uniform(4.0, 9.0)
            self.burst_cooldown = 4.5

        live_wpm = max(16.0, (self.profile['base_wpm'] + jitter + burst_bonus) - fatigue)

        # 4. Syllable Hesitation Stalls
        if random.random() < self.profile['error_probability'] * 1.5:
            min_ms, max_ms = self.profile['hesitation_range_ms']
            stall_sec = random.uniform(min_ms, max_ms) / 1000.0
            live_wpm = max(8.0, live_wpm * (1.0 - (stall_sec * 1.2)))

        # 5. Typo Recoil Throttle
        if random.random() < self.profile['error_probability'] * delta_seconds * 2:
            self.errors_count += 1
            live_wpm = max(10.0, live_wpm * self.profile['recovery_rate'] * 0.75)

        self.current_wpm = round(live_wpm, 1)

        # Character advancement: 1 Word = 5 Characters
        chars_per_sec = (self.current_wpm * 5.0) / 60.0
        advance = chars_per_sec * delta_seconds

        self.total_chars_typed += advance
        self.progress_pct = min(100.0, (self.total_chars_typed / float(total_chars)) * 100.0)
        return round(self.progress_pct, 2), self.current_wpm

    def reset(self):
        self.total_chars_typed = 0.0
        self.errors_count = 0
        self.progress_pct = 0.0
        self.elapsed_seconds = 0.0
        self.burst_cooldown = 0.0
        self.current_wpm = self.profile['base_wpm']