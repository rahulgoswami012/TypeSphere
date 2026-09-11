/**
 * TypeSphere Platform-Wide Dynamic Pilot AI System
 * Replaces fixed-WPM bots with dynamic, neuromorphic AI pilot profiles.
 * Calibrated against realistic human typing expectations for Indian and global pilots.
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
            archetype: "slow_and_consistent",
            baseWpm: 34,
            jitter: 4,
            accuracyRange: [94, 98],
            errorProbability: 0.05,
            hesitationRangeMs: [200, 400],
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
            fatigueFactor: 0.07, // Starts fast, fatigues later
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
            recoveryRate: 0.9
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

class DynamicPilotAISimulator {
    constructor(tier = 'moderate', targetUserWpm = null) {
        this.tier = (tier || 'moderate').toLowerCase();
        const pool = AI_PILOT_ARCHETYPES[this.tier] || AI_PILOT_ARCHETYPES['moderate'];
        
        // Select profile
        const template = pool[Math.floor(Math.random() * pool.length)];
        this.profile = Object.assign({}, template);

        // Adaptive Calibration: tune near user's skill if available
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
        this.inHesitation = false;
        this.burstCooldown = 0;
    }

    /**
     * Advance simulation tick (called every 100ms - 250ms).
     * @param {number} deltaSeconds - Time elapsed since last tick.
     * @param {number} totalTextLength - Total characters of the benchmark passage.
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

        // 1. Calculate natural Cadence Jitter
        const jitterVariance = (Math.random() * 2 - 1) * this.profile.jitter;
        
        // 2. Fatigue Decay (longer flights slightly erode initial burst)
        const fatigueDrop = Math.min(15, this.elapsedSeconds * this.profile.fatigueFactor);

        // 3. Spurt / Burst behavior
        this.burstCooldown -= deltaSeconds;
        let burstBonus = 0;
        if (this.burstCooldown <= 0 && Math.random() < 0.12) {
            burstBonus = (Math.random() * 8) + 4;
            this.burstCooldown = 4.0; // Next burst interval
        }

        let liveWpm = Math.max(16, (this.profile.baseWpm + jitterVariance + burstBonus) - fatigueDrop);

        // 4. Hesitation Stalls
        if (Math.random() < this.profile.errorProbability * 1.5) {
            const stallSec = (Math.random() * (this.profile.hesitationRangeMs[1] - this.profile.hesitationRangeMs[0]) + this.profile.hesitationRangeMs[0]) / 1000.0;
            liveWpm = Math.max(8, liveWpm * (1.0 - (stallSec * 1.2)));
        }

        // 5. Typo simulation & recoil recovery
        if (Math.random() < this.profile.errorProbability) {
            this.totalMistakes++;
            liveWpm = Math.max(10, liveWpm * this.profile.recoveryRate * 0.7); // Temporary throttle drop
        }

        this.currentWpm = liveWpm;

        // Characters typed in this tick (1 Word = 5 Chars)
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
        this.currentWpm = this.profile.baseWpm;
    }
}

window.DynamicPilotAISimulator = DynamicPilotAISimulator;