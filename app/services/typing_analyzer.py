import statistics

class TypingAnalyzer:
    @staticmethod
    def calculate_metrics(events, target_text, duration):
        """
        Accurate computation of Net WPM, Raw WPM, Accuracy, Consistency, and Rhythm.
        Standard definition: 1 Word = 5 characters (including spaces).
        """
        if duration <= 0:
            duration = 0.1

        correct_chars = 0
        incorrect_chars = 0
        extra_chars = 0
        intervals = []
        confusion_pairs = {}
        last_t = 0

        for ev in events:
            t = ev.get('timestamp', 0)
            if last_t > 0:
                intervals.append(max(0.001, t - last_t))
            last_t = t

            is_correct = ev.get('correct', False)
            expected = ev.get('expected', '')
            typed = ev.get('typed', '')

            if is_correct:
                correct_chars += 1
            else:
                incorrect_chars += 1
                if expected and typed:
                    confusion_pairs.setdefault(expected, {})
                    confusion_pairs[expected][typed] = confusion_pairs[expected].get(typed, 0) + 1

        total_typed = correct_chars + incorrect_chars
        target_len = len(target_text)
        missed_chars = max(0, target_len - total_typed)

        # Standard typing formulas
        minutes = duration / 60.0
        raw_wpm = (total_typed / 5.0) / minutes if minutes > 0 else 0.0
        net_wpm = max(0.0, (correct_chars / 5.0) / minutes if minutes > 0 else 0.0)
        accuracy = (correct_chars / total_typed * 100.0) if total_typed > 0 else 0.0

        # Consistency: 100 - (coefficient of variation of intervals * 100)
        consistency = 100.0
        rhythm_score = 100.0
        hesitation_points = []

        if len(intervals) >= 5:
            mean_i = statistics.mean(intervals)
            std_i = statistics.pstdev(intervals)
            cv = (std_i / mean_i) if mean_i > 0 else 0
            consistency = max(0.0, min(100.0, 100.0 - (cv * 40.0)))
            rhythm_score = round(consistency, 1)

            # Identify hesitations (> 3x mean interval)
            for idx, dt in enumerate(intervals):
                if dt > (mean_i * 3.0) and dt > 0.4:
                    char = events[idx].get('expected', '')
                    hesitation_points.append({'char': char, 'interval': round(dt, 3)})

        return {
            'wpm': round(net_wpm, 1),
            'raw_wpm': round(raw_wpm, 1),
            'accuracy': round(accuracy, 1),
            'consistency': round(consistency, 1),
            'rhythm_score': rhythm_score,
            'correct_chars': correct_chars,
            'incorrect_chars': incorrect_chars,
            'extra_chars': extra_chars,
            'missed_chars': missed_chars,
            'hesitations': hesitation_points,
            'confusion_pairs': confusion_pairs
        }