import random

STORIES = [
    "The clockmaker lived on a narrow street where the fog settled early and stayed late into the morning. In his workshop, hundreds of gears moved together in quiet harmony, measuring seconds that no one else seemed to notice. Visitors often asked why he spent years crafting pendulum clocks in an age of digital screens. He would smile, wind a brass key with steady fingers, and tell them that digital time merely counts, while mechanical time breathes.",
    "A solitary satellite drifted through the dark expanse above Earth, observing city lights flickering like scattered embers across the continents. For seven years, its solar panels had absorbed the unshielded glare of the sun, powering instruments that tracked melting glaciers and shifting desert dunes. It sent back terabytes of silent telemetry, an unblinking witness to the quiet transformation of a living world.",
    "The old library was built from limestone that smelled of rain and ancient paper. At its center stood an iron spiral staircase leading to balconies lined with uncatalogued manuscripts. Scholars from distant universities sat at polished walnut desks, turning pages with careful fingertips. Here, ideas written centuries ago waited patiently for minds curious enough to give them new life."
]

ARTICLES = [
    "Modern computational infrastructure increasingly depends on distributed event streaming pipelines to process real-time information. By decoupling data producers from consumer applications through immutable, partitioned logs, high-throughput systems achieve fault tolerance across globally distributed server clusters. When an individual node fails, partition leaders are re-elected automatically, ensuring uninterrupted execution under high volume.",
    "Cognitive ergonomics examines how human perception, memory, and motor responses interact with digital tools. Research demonstrates that tactile feedback and predictable keystroke latency significantly reduce mental fatigue during sustained intellectual tasks. When software interfaces eliminate visual friction and unexpected layout shifts, operators enter a state of sustained focus known as deep flow.",
    "Renewable energy integration into regional electrical grids requires advanced battery storage and predictive demand algorithms. Wind and solar generation fluctuate with atmospheric conditions, necessitating rapid-response balancing reserves. By coordinating distributed inverter systems, municipal utilities maintain uniform voltage and frequency across peak usage hours."
]

REAL_WORLD_OFFICE = [
    "Subject: Project Alpha Deployment Schedule Update. Dear Team, Please review the finalized deployment timeline for the third quarter release. We have completed integration testing on the authentication gateway and resolved all high-priority issue tickets. Final staging validation will take place on Thursday at 14:00 UTC. Please ensure your respective service monitors are active.",
    "MEMORANDUM. To: Department Directors. From: Operations Committee. Date: September 15. Re: Updated Data Retention and Compliance Standards. Effective immediately, all customer interaction records must be archived using encrypted cold storage within thirty days of transaction close. Audit logs must remain accessible for regulatory compliance.",
    "Executive Briefing: Preliminary market indicators show a twelve percent expansion in subscription renewals following the introduction of automated telemetry diagnostics. Resource allocation for the forthcoming fiscal cycle will prioritize infrastructure resilience, API latency optimization, and enterprise support capacity."
]

QUOTES = [
    "Simplicity is prerequisite for reliability. It is not that we have so little time, but that we lose so much. The life we receive is not short, but we make it so.",
    "We are what we repeatedly do. Excellence, then, is not an act, but a habit. The craftsman who respects his tools is already halfway to mastery.",
    "In the middle of difficulty lies opportunity. Do not seek to follow in the footsteps of the wise; seek what they sought with patient persistence."
]

COMMON_LEXICON = {
    'easy': [
        "about", "after", "again", "almost", "always", "another", "answer", "around", "became", "become",
        "before", "better", "between", "black", "called", "change", "children", "circle", "clean", "color",
        "could", "differ", "during", "early", "earth", "every", "family", "father", "first", "follow",
        "friend", "great", "group", "house", "large", "learn", "letter", "light", "little", "mother",
        "never", "number", "often", "other", "people", "place", "point", "right", "school", "second",
        "small", "sound", "still", "study", "their", "there", "these", "thing", "think", "three",
        "through", "under", "until", "water", "where", "which", "while", "white", "without", "world"
    ],
    'moderate': [
        "account", "accurate", "addition", "address", "advance", "advantage", "analysis", "approach",
        "balance", "baseline", "building", "business", "cadence", "capacity", "certain", "channel",
        "cognitive", "command", "company", "complete", "condition", "consider", "constant", "control",
        "decision", "describe", "develop", "direction", "discipline", "economy", "element", "energy",
        "evidence", "example", "exercise", "experience", "feature", "frequency", "general", "history",
        "important", "industry", "interest", "language", "material", "movement", "national", "natural",
        "observe", "operation", "pattern", "position", "practice", "pressure", "problem", "process",
        "produce", "program", "progress", "purpose", "reaction", "regular", "require", "standard",
        "strategy", "structure", "system", "technique", "together", "understand", "variety", "velocity"
    ],
    'hard': [
        "accomplishment", "algorithmic", "approximate", "architectural", "asynchronous", "authenticated",
        "biochemical", "characteristic", "chronological", "circumstance", "communication", "compensate",
        "comprehensive", "computational", "configuration", "consequential", "contemporary", "correspondence",
        "differentiation", "electromagnetic", "enthusiastic", "environmental", "extraordinary", "fundamental",
        "heterogeneous", "implementation", "inconvenience", "infrastructure", "instrumentation", "insufficient",
        "intelligence", "intermittent", "jurisdiction", "lexicographical", "mathematical", "methodology",
        "miscellaneous", "nanotechnology", "neurochemical", "organization", "parliamentary", "pharmaceutical",
        "phenomenon", "philosophical", "photosynthesis", "physiological", "psychological", "reconciliation",
        "reinforcement", "representative", "sophisticated", "subterranean", "synchronization", "telemetry"
    ],
    'expert': [
        "anachronistic", "antediluvian", "circumlocution", "counterintuitive", "crystallization", "deleterious",
        "disproportionate", "epistemological", "existentialism", "grandiloquent", "idiosyncrasy", "incommensurable",
        "indistinguishable", "juxtaposition", "lexicographical", "magnanimous", "metamorphosis", "multidimensional",
        "obfuscation", "panegyric", "phenomenological", "quintessential", "sesquipedalian", "synchronicity",
        "unprecedented", "verisimilitude", "vicissitude", "zeitgeist", "labyrinthine", "perspicacious"
    ]
}

DATA_ENTRY_POOL = [
    "INV-84029 | Sophia Chen | 10880 Wilshire Blvd, Los Angeles, CA 90024 | +1 (310) 555-0194 | $3,420.50 | 2026-04-12",
    "INV-84030 | Marcus Sterling | 742 Evergreen Terr, Springfield, IL 62704 | +1 (217) 555-0142 | $1,180.00 | 2026-04-14",
    "INV-84031 | Elena Rostova | 19 Baker Street, London, UK NW1 6XE | +44 20 7946 0912 | £2,750.80 | 2026-04-15",
    "INV-84032 | Liam O'Connor | 452 Kingfisher Lane, Seattle, WA 98101 | +1 (206) 555-0188 | $4,915.25 | 2026-04-18",
    "INV-84033 | Chloe Dubois | 804 Industrial Pkwy, Austin, TX 78701 | +1 (512) 555-0163 | $890.00 | 2026-04-19"
]

class ContentEngine:
    @staticmethod
    def generate_segment(test_type='speed', difficulty='moderate', batch_words=55, code_lang='python'):
        diff = difficulty.lower() if difficulty.lower() in COMMON_LEXICON else 'moderate'

        if test_type == 'story':
            return random.choice(STORIES)

        if test_type == 'article':
            return random.choice(ARTICLES)

        if test_type == 'professional':
            return random.choice(REAL_WORLD_OFFICE)

        if test_type == 'quote':
            return random.choice(QUOTES)

        if test_type == 'data_entry':
            return "\n".join(random.sample(DATA_ENTRY_POOL, k=min(4, len(DATA_ENTRY_POOL))))

        if test_type == 'numbers':
            nums = [str(random.randint(10, 99999)) for _ in range(batch_words)]
            return " ".join(nums)

        if test_type in ['numbers_text', 'numbers_plus']:
            words = [random.choice(COMMON_LEXICON[diff]) for _ in range(batch_words)]
            for i in range(len(words)):
                if random.random() < 0.22:
                    words[i] = str(random.randint(1, 9999))
            return " ".join(words)

        if test_type == 'punctuation':
            words = [random.choice(COMMON_LEXICON[diff]) for _ in range(batch_words)]
            puncts = [",", ".", ";", ":", "!", "?", "\"", "'", "-", "--", "(", ")"]
            for i in range(len(words)):
                p = random.choice(puncts)
                if p in ["\"", "'", "("]:
                    words[i] = f"{p}{words[i]}{')' if p=='(' else p}"
                else:
                    words[i] = f"{words[i]}{p}"
                if random.random() < 0.35:
                    words[i] = words[i].capitalize()
            return " ".join(words)

        # Default Flowing Passages (Speed, Practice, Full Passage)
        lex = COMMON_LEXICON[diff]
        chosen = [random.choice(lex) for _ in range(batch_words)]
        
        # Structure into natural syntax
        for i in range(0, len(chosen), 7):
            chosen[i] = chosen[i].capitalize()
            if i > 0 and not chosen[i-1].endswith('.'):
                chosen[i-1] = f"{chosen[i-1]}."
        
        return " ".join(chosen)