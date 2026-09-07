import random
import time

AI_LEVEL_PROFILES = {
    'beginner': {
        'target_wpm': 28,
        'variance': 6,
        'error_chance': 0.08,
        'hesitation_chance': 0.15,
        'hesitation_ms': (250, 450)
    },
    'intermediate': {
        'target_wpm': 55,
        'variance': 8,
        'error_chance': 0.04,
        'hesitation_chance': 0.08,
        'hesitation_ms': (150, 280)
    },
    'advanced': {
        'target_wpm': 85,
        'variance': 10,
        'error_chance': 0.02,
        'hesitation_chance': 0.04,
        'hesitation_ms': (80, 160)
    },
    'expert': {
        'target_wpm': 118,
        'variance': 12,
        'error_chance': 0.008,
        'hesitation_chance': 0.015,
        'hesitation_ms': (40, 90)
    },
    'adaptive': {
        'target_wpm': 60,
        'variance': 8,
        'error_chance': 0.03,
        'hesitation_chance': 0.05,
        'hesitation_ms': (100, 200)
    }
}

class AITypistSimulator:
    def __init__(self, level='intermediate', player_target_wpm=None):
        self.level = level if level in AI_LEVEL_PROFILES else 'intermediate'
        self.profile = AI_LEVEL_PROFILES[self.level].copy()
        
        # Adaptive difficulty tunes within 5 WPM of user's typical velocity
        if self.level == 'adaptive' and player_target_wpm:
            self.profile['target_wpm'] = max(30, min(140, player_target_wpm + random.randint(-4, 6)))

        self.current_wpm = self.profile['target_wpm']
        self.total_strokes = 0
        self.errors_made = 0
        self.last_tick = time.time()

    def get_progress_step(self, time_delta, current_progress, total_target_chars):
        """
        Computes the simulated progress increment based on target WPM and human variances.
        """
        if total_target_chars <= 0:
            return 0, self.current_wpm

        # Introduce velocity jitter (mimics human acceleration and deceleration)
        fluctuation = random.uniform(-self.profile['variance'], self.profile['variance'])
        effective_wpm = max(15, self.profile['target_wpm'] + fluctuation)
        self.current_wpm = round(effective_wpm, 1)

        # Characters per second: 1 WPM = 5 chars / 60 sec
        chars_per_sec = (effective_wpm * 5.0) / 60.0
        increment_chars = chars_per_sec * time_delta

        # Micro-hesitations simulation (hesitating on complex keys or syllables)
        if random.random() < self.profile['hesitation_chance']:
            hesitation = random.uniform(*self.profile['hesitation_ms']) / 1000.0
            increment_chars = max(0, increment_chars - (chars_per_sec * hesitation))

        # Error & correction simulation (mistakes temporarily retard progress)
        if random.random() < self.profile['error_chance']:
            self.errors_made += 1
            # Cost of backspacing and re-typing 1-2 characters
            increment_chars = max(0, increment_chars - random.uniform(1.0, 2.5))

        step_pct = (increment_chars / float(total_target_chars)) * 100.0
        new_progress = min(100.0, current_progress + step_pct)

        return round(new_progress, 2), self.current_wpm