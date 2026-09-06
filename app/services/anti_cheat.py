import statistics

class AntiCheatSystem:
    @staticmethod
    def evaluate(events, duration, wpm, accuracy):
        """
        Detect paste attacks, robotic zero-variance timings, and impossible human speed.
        """
        if not events or len(events) < 5:
            if wpm > 180 and duration < 3:
                return True, "Suspiciously short completion with super-human WPM."
            return False, None

        intervals = []
        for i in range(1, len(events)):
            dt = events[i]['timestamp'] - events[i-1]['timestamp']
            intervals.append(dt)

        # 1. Pasting Detection: 40%+ of characters typed under 12ms
        instant_count = sum(1 for dt in intervals if dt < 0.012)
        if instant_count / len(intervals) > 0.40:
            return True, "Pasted input detected (unrealistic keystroke intervals)."

        # 2. Maximum Human Limit
        if wpm > 250:
            return True, f"WPM of {round(wpm, 1)} exceeds verified physiological human limits."

        # 3. Robotic Consistency: standard deviation is near-zero (autotyper scripts)
        if len(intervals) > 20:
            stdev = statistics.pstdev(intervals)
            if stdev < 0.003:
                return True, f"Suspicious robotic regularity detected (variance: {stdev:.5f})."

        return False, None