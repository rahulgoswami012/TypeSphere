import random
import time

AI_DIFFICULTY_PROFILES = {
    'easy': {
        'target_wpm': 32,
        'variance': 7,
        'error_chance': 0.12,
        'hesitation_chance': 0.18,
        'hesitation_range_ms': (220, 500)
    },
    'moderate': {
        'target_wpm': 62,
        'variance': 9,
        'error_chance': 0.05,
        'hesitation_chance': 0.09,
        'hesitation_range_ms': (140, 300)
    },
    'hard': {
        'target_wpm': 94,
        'variance': 11,
        'error_chance': 0.02,
        'hesitation_chance': 0.04,
        'hesitation_range_ms': (60, 160)
    },
    'expert': {
        'target_wpm': 128,
        'variance': 12,
        'error_chance': 0.006,
        'hesitation_chance': 0.015,
        'hesitation_range_ms': (30, 80)
    }
}

class AITypistSimulator:
    def __init__(self, difficulty='moderate', player_target_wpm=None):
        diff = difficulty.lower()
        self.difficulty = diff if diff in AI_DIFFICULTY_PROFILES else 'moderate'
        self.profile = AI_DIFFICULTY_PROFILES[self.difficulty].copy()

        if player_target_wpm:
            self.profile['target_wpm'] = max(25, min(145, player_target_wpm + random.randint(-5, 6)))

        self.current_wpm = self.profile['target_wpm']
        self.total_chars_typed = 0
        self.errors_count = 0
        self.progress_pct = 0.0

    def step(self, delta_seconds, total_chars):
        if total_chars <= 0:
            return 0.0, self.current_wpm

        jitter = random.uniform(-self.profile['variance'], self.profile['variance'])
        live_speed = max(18.0, self.profile['target_wpm'] + jitter)
        self.current_wpm = round(live_speed, 1)

        chars_per_sec = (live_speed * 5.0) / 60.0
        advance = chars_per_sec * delta_seconds

        if random.random() < self.profile['hesitation_chance']:
            delay_sec = random.uniform(*self.profile['hesitation_range_ms']) / 1000.0
            advance = max(0.0, advance - (chars_per_sec * delay_sec))

        if random.random() < self.profile['error_chance']:
            self.errors_count += 1
            advance = max(0.0, advance - random.uniform(1.0, 2.5))

        self.total_chars_typed += advance
        self.progress_pct = min(100.0, (self.total_chars_typed / float(total_chars)) * 100.0)
        return round(self.progress_pct, 2), self.current_wpm