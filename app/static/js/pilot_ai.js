/**
 * TypeSphere Platform-Wide Dynamic Pilot AI & Pacer Engine
 * Replaces static bots with neuromorphic AI pilot archetypes and calibrated steady pacers.
 * Standardized across Solo Benchmarks, 1v1 Air Grids, and Arcade Flight Arenas.
 */

const AI_PILOT_ARCHETYPES = {
    easy: [
        {
            callsign: "CADET ARROW",
            archetype: "steady_learner",
            baseWpm: 28,
            jitter: 5,
            accuracyRange: [91, 95],
            errorProbability: 0.08,
            hesitationRangeMs: [250, 500],
            fatigueFactor: 0.03,
            recoveryRate: 0.85
        },
        {
            callsign: "CADET ZEPHYR",
            archetype: "cautious_cruiser",
            baseWpm: 34,
            jitter: 4,
            accuracyRange: [94, 98],
            errorProbability: 0.05,
            hesitationRangeMs: [200, 420],
            fatigueFactor: 0.02,
            recoveryRate: 0.95
        }
    ],
    moderate: [
        {
            callsign: "PILOT HORIZON",
            archetype: "cadence_cruiser",
            baseWpm: 58,
            jitter: 7,
            accuracyRange: [94, 97],
            errorProbability: 0.045,
            hesitationRangeMs: [120, 260],
            fatigueFactor: 0.04,
            recoveryRate: 0.92
        },
        {
            callsign: "PILOT STRIKE",
            archetype: "burst_sprinter",
            baseWpm: 66,
            jitter: 9,
            accuracyRange: [92, 96],
            errorProbability: 0.06,
            hesitationRangeMs: [90, 220],
            fatigueFactor: 0.07, // Starts fast, fatigues under pressure
            recoveryRate: 0.88
        }
    ],
    hard: [
        {
            callsign: "ACE VELOCITY",
            archetype: "tactical_precision",
            baseWpm: 88,
            jitter: 8,
            accuracyRange: [96, 99],
            errorProbability: 0.02,
            hesitationRangeMs: [60, 140],
            fatigueFactor: 0.025,
            recoveryRate: 0.98
        },
        {
            callsign: "ACE HYPERION",
            archetype: "aggressive_rusher",
            baseWpm: 96,
            jitter: 11,
            accuracyRange: [93, 97],
            errorProbability: 0.035,
            hesitationRangeMs: [40, 120],
            fatigueFactor: 0.05,
            recoveryRate: 0.90
        }
    ],
    expert: [
        {
            callsign: "COMMANDER APEX",
            archetype: "grandmaster_ghost",
            baseWpm: 122,
            jitter: 10,
            accuracyRange: [97, 99.5],
            errorProbability: 0.008,
            hesitationRangeMs: [25, 70],
            fatigueFactor: 0.015,
            recoveryRate: 0.99
        },
        {
            callsign: "COMMANDER CYBERPULSE",
            archetype: "esports_machine",
            baseWpm: 135,
            jitter: 12,
            accuracyRange: [96, 98.8],
            errorProbability: 0.012,
            hesitationRangeMs: [20, 60],
            fatigueFactor: 0.02,
            recoveryRate: 0.98
        }
    ]
};

/**
 * Dynamic Neuromorphic AI Competitor
 * Models human cadence variations, errors, hesitations, and stamina decay.
 */
class DynamicPilotAISimulator {
    constructor(tier = 'moderate', targetUserWpm = null) {
        this.tier = (tier || 'moderate').toLowerCase();
        const pool = AI_PILOT_ARCHETYPES[this.tier] || AI_PILOT_ARCHETYPES['moderate'];
        
        // Select an individual pilot archetype
        const template = pool[Math.floor(Math.random() * pool.length)];
        this.profile = Object.assign({}, template);

        // Skill-anchored adaptive tuning if target player WPM is provided
        if (targetUserWpm && targetUserWpm > 15) {
            const shift = (Math.random() * 10) - 5;
            this.profile.baseWpm = Math.max(22, Math.round(targetUserWpm + shift));
        }

        this.callsign = this.profile.callsign;
        this.currentWpm = this.profile.baseWpm;
        this.progressChars = 0;
        this.progressPct = 0;
        this.totalMistakes = 0;
        this.elapsedSeconds = 0;
        this.burstCooldown = 0;
        this.isTypoStalled = false;
    }

    /**
     * Advances simulation tick (typically called every 80ms - 200ms).
     * @param {number} deltaSeconds - Delta time since last tick.
     * @param {number} totalTextLength - Passage total characters.
     * @returns {Object} Telemetry state snapshot.
     */
    tick(deltaSeconds, totalTextLength) {
        if (totalTextLength <= 0 || this.progressPct >= 100) {
            return {
                wpm: Math.round(this.currentWpm),
                progressPct: 100,
                progressChars: totalTextLength,
                mistakes: this.totalMistakes,
                callsign: this.callsign
            };
        }

        this.elapsedSeconds += deltaSeconds;

        // 1. Natural Cadence Jitter (+/- jitter variance)
        const jitter = (Math.random() * 2 - 1) * this.profile.jitter;

        // 2. Progressive Fatigue Decay over long flights
        const fatigue = Math.min(16, this.elapsedSeconds * this.profile.fatigueFactor);

        // 3. Spurt / Burst Acceleration
        this.burstCooldown -= deltaSeconds;
        let burstBonus = 0;
        if (this.burstCooldown <= 0 && Math.random() < 0.14) {
            burstBonus = (Math.random() * 9) + 4;
            this.burstCooldown = 4.5;
        }

        let liveWpm = Math.max(16, (this.profile.baseWpm + jitter + burstBonus) - fatigue);

        // 4. Syllable Hesitation Stalls
        if (Math.random() < this.profile.errorProbability * 1.6) {
            const minMs = this.profile.hesitationRangeMs[0];
            const maxMs = this.profile.hesitationRangeMs[1];
            const stallSec = (Math.random() * (maxMs - minMs) + minMs) / 1000.0;
            liveWpm = Math.max(8, liveWpm * (1.0 - (stallSec * 1.3)));
        }

        // 5. Simulated Typo & Throttle Recoil
        if (Math.random() < this.profile.errorProbability * deltaSeconds * 2) {
            this.totalMistakes++;
            liveWpm = Math.max(10, liveWpm * this.profile.recoveryRate * 0.75);
        }

        this.currentWpm = liveWpm;

        // Advance characters (1 Word = 5 Characters)
        const charsPerSecond = (this.currentWpm * 5.0) / 60.0;
        const charsAdvanced = charsPerSecond * deltaSeconds;

        this.progressChars = Math.min(totalTextLength, this.progressChars + charsAdvanced);
        this.progressPct = Math.min(100.0, (this.progressChars / totalTextLength) * 100.0);

        return {
            wpm: Math.round(this.currentWpm),
            progressPct: parseFloat(this.progressPct.toFixed(2)),
            progressChars: Math.floor(this.progressChars),
            mistakes: this.totalMistakes,
            callsign: this.callsign
        };
    }

    reset() {
        this.progressChars = 0;
        this.progressPct = 0;
        this.totalMistakes = 0;
        this.elapsedSeconds = 0;
        this.burstCooldown = 0;
        this.currentWpm = this.profile.baseWpm;
    }

    // ==========================================================
    // DISCIPLINE-SPECIFIC BEHAVIOR TRANSLATION HELPERS
    // ==========================================================

    /**
     * Speed Racer: returns distance advancement factoring throttle and recoil.
     */
    getSpeedRacerThrottle(deltaSeconds) {
        const charsPerSec = (this.currentWpm * 5.0) / 60.0;
        let meters = (charsPerSec * 2.2) * deltaSeconds;
        // Minor recoil if a simulated mistake occurs
        if (Math.random() < this.profile.errorProbability * deltaSeconds) {
            meters = Math.max(0, meters - 1.5);
        }
        return meters;
    }

    /**
     * Zombie Duel: determines whether AI finishes a combat attack spell.
     */
    canCastDuelSpell(wordLength, elapsedInterval) {
        const neededSeconds = (wordLength / ((this.currentWpm * 5.0) / 60.0));
        return elapsedInterval >= neededSeconds;
    }

    /**
     * Whack-A-Word / Bubble Pop: returns calibrated reaction strike delay in ms.
     */
    getReactionLatencyMs() {
        const baseLatency = {
            'easy': 580,
            'moderate': 380,
            'hard': 220,
            'expert': 140
        }[this.tier] || 380;
        const jitter = (Math.random() * 80) - 40;
        return Math.max(90, Math.round(baseLatency + jitter));
    }

    /**
     * Cipher Hacker: simulates token decryption duration in seconds.
     */
    getTokenDecryptionTime(tokenLength) {
        const netCharsPerSec = Math.max(1.5, (this.currentWpm * 5.0) / 60.0);
        const retryPenalty = (Math.random() < this.profile.errorProbability) ? 0.75 : 0;
        return (tokenLength / netCharsPerSec) + retryPenalty;
    }
}

/**
 * Calibrated Steady Pacer
 * Strictly unvarying, user-calibrated target line for ghost benchmarking.
 * Does not suffer typos, fatigue, or random jitter.
 */
class SteadyPacerSimulator {
    constructor(targetWpm = 60, callsign = "PACER GHOST") {
        this.targetWpm = Math.max(10, parseFloat(targetWpm) || 60);
        this.callsign = callsign;
        this.progressChars = 0;
        this.progressPct = 0;
        this.elapsedSeconds = 0;
    }

    tick(deltaSeconds, totalTextLength) {
        if (totalTextLength <= 0 || this.progressPct >= 100) {
            return {
                wpm: Math.round(this.targetWpm),
                progressPct: 100,
                progressChars: totalTextLength,
                mistakes: 0,
                callsign: this.callsign
            };
        }

        this.elapsedSeconds += deltaSeconds;
        const charsPerSec = (this.targetWpm * 5.0) / 60.0;
        const charsAdvanced = charsPerSec * deltaSeconds;

        this.progressChars = Math.min(totalTextLength, this.progressChars + charsAdvanced);
        this.progressPct = Math.min(100.0, (this.progressChars / totalTextLength) * 100.0);

        return {
            wpm: Math.round(this.targetWpm),
            progressPct: parseFloat(this.progressPct.toFixed(2)),
            progressChars: Math.floor(this.progressChars),
            mistakes: 0,
            callsign: this.callsign
        };
    }

    reset() {
        this.progressChars = 0;
        this.progressPct = 0;
        this.elapsedSeconds = 0;
    }
}

// Global Export bindings
window.DynamicPilotAISimulator = DynamicPilotAISimulator;
window.SteadyPacerSimulator = SteadyPacerSimulator;