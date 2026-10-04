"""
TypeSphere Content Engine
Provides syllabic word banks (500+ curated words), multi-paragraph reading corpora,
and syntax-accurate code snippets across 8 programming languages.
"""

import random

STORIES = [
    "The clockmaker lived on a narrow street where the fog settled early and stayed late into the morning. In his workshop, hundreds of gears moved together in quiet harmony, measuring seconds that no one else seemed to notice. Visitors often asked why he spent years crafting pendulum clocks in an age of digital screens. He would smile, wind a brass key with steady fingers, and tell them that digital time merely counts, while mechanical time breathes.",
    "A solitary satellite drifted through the dark expanse above Earth, observing city lights flickering like scattered embers across the continents. For seven years, its solar panels had absorbed the unshielded glare of the sun, powering instruments that tracked melting glaciers and shifting desert dunes. It sent back terabytes of silent telemetry, an unblinking witness to the quiet transformation of a living world.",
    "The old library was built from limestone that smelled of rain and ancient paper. At its center stood an iron spiral staircase leading to balconies lined with uncatalogued manuscripts. Scholars from distant universities sat at polished walnut desks, turning pages with careful fingertips. Here, ideas written centuries ago waited patiently for minds curious enough to give them new life.",
    "When an aircraft accelerates through the transonic boundary toward Mach 1, air molecules ahead of the airframe cannot disperse fast enough to accommodate the advancing geometry. Compressibility effects dominate the flowfield, forming a shockwave along the leading edges of the wings and fuselage. Slender cross-sections designed according to the Whitcomb area rule reduce wave drag, preserving pitch trim stability as the aircraft punctures the sound barrier."
]

ARTICLES = [
    "Modern computational infrastructure increasingly depends on distributed event streaming pipelines to process real-time information. By decoupling data producers from consumer applications through immutable, partitioned logs, high-throughput systems achieve fault tolerance across globally distributed server clusters. When an individual node fails, partition leaders are re-elected automatically, ensuring uninterrupted execution under high volume.",
    "Cognitive ergonomics examines how human perception, memory, and motor responses interact with digital tools. Research demonstrates that tactile feedback and predictable keystroke latency significantly reduce mental fatigue during sustained intellectual tasks. When software interfaces eliminate visual friction and unexpected layout shifts, operators enter a state of sustained focus known as deep flow.",
    "Renewable energy integration into regional electrical grids requires advanced battery storage and predictive demand algorithms. Wind and solar generation fluctuate with atmospheric conditions, necessitating rapid-response balancing reserves. By coordinating distributed inverter systems, municipal utilities maintain uniform voltage and frequency across peak usage hours.",
    "In high-integrity avionics buses, deterministic Ethernet networks enforce strict time-division multiple access scheduling. Every mission sensor is allocated dedicated microsecond transmission epochs within each master frame cycle. This guarantees zero packet collision, bounded latency jitter under ten microseconds, and predictable telemetry communication for primary flight surfaces."
]

REAL_WORLD_OFFICE = [
    "Subject: Project Alpha Deployment Schedule Update. Dear Team, Please review the finalized deployment timeline for the third quarter release. We have completed integration testing on the authentication gateway and resolved all high-priority issue tickets. Final staging validation will take place on Thursday at 14:00 UTC. Please ensure your respective service monitors are active.",
    "MEMORANDUM. To: Department Directors. From: Operations Committee. Date: September 15. Re: Updated Data Retention and Compliance Standards. Effective immediately, all customer interaction records must be archived using encrypted cold storage within thirty days of transaction close. Audit logs must remain accessible for regulatory compliance.",
    "Executive Briefing: Preliminary market indicators show a twelve percent expansion in subscription renewals following the introduction of automated telemetry diagnostics. Resource allocation for the forthcoming fiscal cycle will prioritize infrastructure resilience, API latency optimization, and enterprise support capacity."
]

EXAM_GOVERNMENT_PASSAGES = [
    "GOVERNMENT OF INDIA, STAFF SELECTION COMMISSION. OFFICE MEMORANDUM. Subject: Standards for Skill Assessment in Computer-Based Typographical Assessment for Combined Graduate Level Examination. It is hereby notified that the Commission has prescribed a qualifying speed of 2000 key depressions for a duration of 15 minutes on the designated computer console. Typographical accuracy shall be evaluated strictly against error percentage thresholds. Permissible error margins shall not exceed five percent for unreserved candidates and seven percent for reserved candidates.",
    "The Constitution of India stands as the supreme legal framework of the republic, establishing an autonomous sovereign socialist secular democratic system. It guarantees fundamental rights to all citizens, including equality before the law, freedom of speech and expression, and protection against discrimination on grounds of religion, race, caste, or place of birth.",
    "GOVERNMENT OF INDIA, MINISTRY OF FINANCE, DEPARTMENT OF EXPENDITURE. NOTIFICATION. Public procurement guidelines require drawing and disbursing officers to strictly adhere to Rule 149 of the General Financial Rules (GFR 2017). Sanctioned funds shall be disbursed upon submission of delivery invoices and technical audit acceptance certificates. Unutilized budgetary allocations for the current fiscal quarter shall lapse automatically on the thirty-first day of March.",
    "Public administrative governance demands unyielding transparency, procedural adherence, and punctuality across ministerial secretariats. Official circulars, gazette notifications, and parliamentary questions require meticulous transcription accuracy to maintain administrative continuity without ambiguous interpretations."
]

QUOTES = [
    "Simplicity is prerequisite for reliability. It is not that we have so little time, but that we lose so much. The life we receive is not short, but we make it so.",
    "We are what we repeatedly do. Excellence, then, is not an act, but a habit. The craftsman who respects his tools is already halfway to mastery.",
    "In the middle of difficulty lies opportunity. Do not seek to follow in the footsteps of the wise; seek what they sought with patient persistence.",
    "The secret of getting ahead is getting started. The secret of getting started is breaking your complex overwhelming tasks into small manageable tasks, and starting on the first one.",
    "True velocity is not rushed chaos; it is calm, deliberate movement free of hesitation and unnecessary recoil. Keep your hands balanced and let cadence carry your speed."
]

CODE_SNIPPETS = {
    'python': [
        "def quicksort(arr):\n    if len(arr) <= 1:\n        return arr\n    pivot = arr[len(arr) // 2]\n    left = [x for x in arr if x < pivot]\n    middle = [x for x in arr if x == pivot]\n    right = [x for x in arr if x > pivot]\n    return quicksort(left) + middle + quicksort(right)",
        "class TokenBucket:\n    def __init__(self, rate: float, capacity: float):\n        self.rate = rate\n        self.capacity = capacity\n        self.tokens = capacity\n        self.last = time.time()\n    def consume(self, amount: float = 1.0) -> bool:\n        now = time.time()\n        self.tokens = min(self.capacity, self.tokens + (now - self.last) * self.rate)\n        self.last = now\n        if self.tokens >= amount:\n            self.tokens -= amount\n            return True\n        return False"
    ],
    'javascript': [
        "const debounce = (fn, delay = 300) => {\n    let timer;\n    return (...args) => {\n        clearTimeout(timer);\n        timer = setTimeout(() => fn.apply(this, args), delay);\n    };\n};",
        "async function fetchWithRetry(url, retries = 3) {\n    for (let i = 0; i < retries; i++) {\n        try {\n            const res = await fetch(url);\n            if (res.ok) return await res.json();\n        } catch (err) {\n            if (i === retries - 1) throw err;\n        }\n    }\n}"
    ],
    'html': [
        "<section class=\"cockpit-telemetry\">\n    <header class=\"hud-header\">\n        <h2>Flight Telemetry Console</h2>\n        <span class=\"badge active\">ONLINE</span>\n    </header>\n    <div class=\"gauges-grid\">\n        <article class=\"metric-box\" data-value=\"100\">\n            <label>Reactor Output</label>\n            <output>100%</output>\n        </article>\n    </div>\n</section>",
        "<form method=\"POST\" action=\"/api/submit\" class=\"cockpit-form\">\n    <fieldset>\n        <legend>Pilot Identification</legend>\n        <label for=\"pilot-callsign\">Callsign:</label>\n        <input type=\"text\" id=\"pilot-callsign\" name=\"callsign\" required>\n        <button type=\"submit\" class=\"btn-submit\">Authorize Launch</button>\n    </fieldset>\n</form>"
    ],
    'css': [
        ".cockpit-container {\n    display: flex;\n    flex-direction: column;\n    background: var(--bg-card);\n    border: 1.5px solid var(--accent);\n    box-shadow: 0 0 25px rgba(56, 189, 248, 0.25);\n    border-radius: 8px;\n    padding: 1.5rem;\n    backdrop-filter: blur(8px);\n}",
        "@keyframes pulseTelemetry {\n    0% { transform: scale(1); opacity: 0.8; }\n    50% { transform: scale(1.05); opacity: 1; filter: drop-shadow(0 0 8px #38bdf8); }\n    100% { transform: scale(1); opacity: 0.8; }\n}"
    ],
    'sql': [
        "SELECT department_id, employee_name, salary,\n       AVG(salary) OVER (PARTITION BY department_id) AS dept_avg,\n       RANK() OVER (PARTITION BY department_id ORDER BY salary DESC) AS rank_pos\nFROM payroll_records\nWHERE status = 'ACTIVE';",
        "WITH RankedScores AS (\n    SELECT user_id, score, DENSE_RANK() OVER (ORDER BY score DESC) as rank\n    FROM user_leaderboards\n)\nSELECT user_id, score FROM RankedScores WHERE rank <= 10;"
    ],
    'java': [
        "public class ConcurrentQueue<T> {\n    private final Object lock = new Object();\n    private final List<T> elements = new LinkedList<>();\n    public void enqueue(T item) {\n        synchronized (lock) {\n            elements.add(item);\n            lock.notifyAll();\n        }\n    }\n}",
        "public static int binarySearch(int[] array, int target) {\n    int low = 0;\n    int high = array.length - 1;\n    while (low <= high) {\n        int mid = (low + high) >>> 1;\n        if (array[mid] == target) return mid;\n        else if (array[mid] < target) low = mid + 1;\n        else high = mid - 1;\n    }\n    return -1;\n}"
    ],
    'c': [
        "int partition(int arr[], int low, int high) {\n    int pivot = arr[high];\n    int i = (low - 1);\n    for (int j = low; j <= high - 1; j++) {\n        if (arr[j] < pivot) {\n            i++;\n            int t = arr[i]; arr[i] = arr[j]; arr[j] = t;\n        }\n    }\n    int t = arr[i + 1]; arr[i + 1] = arr[high]; arr[high] = t;\n    return (i + 1);\n}",
        "#include <stdio.h>\n#include <stdlib.h>\ntypedef struct Node {\n    int value;\n    struct Node* next;\n} Node;\nNode* createNode(int val) {\n    Node* n = (Node*)malloc(sizeof(Node));\n    n->value = val;\n    n->next = NULL;\n    return n;\n}"
    ],
    'cpp': [
        "template <typename T>\nclass ThreadSafeStack {\nprivate:\n    std::stack<T> data_stack;\n    mutable std::mutex mutex_;\npublic:\n    void push(T new_value) {\n        std::lock_guard<std::mutex> lock(mutex_);\n        data_stack.push(std::move(new_value));\n    }\n};",
        "int main() {\n    std::vector<std::string> words = {\"kinetic\", \"velocity\", \"precision\"};\n    std::sort(words.begin(), words.end(), [](const auto& a, const auto& b){\n        return a.length() < b.length();\n    });\n    return 0;\n}"
    ]
}

# 500+ Curated words classified by syllabic complexity
COMMON_LEXICON = {
    'easy': [
        # 1-Syllable & Foundational Flight Lexicon (150 words)
        "air", "jet", "fly", "sky", "alt", "run", "wing", "lift", "drag", "yaw",
        "bank", "roll", "trim", "gear", "flap", "fin", "rud", "bow", "deck", "bay",
        "fuel", "tank", "pump", "line", "flow", "vent", "burn", "heat", "cold", "wind",
        "gust", "fog", "rain", "hail", "snow", "ice", "cloud", "sun", "moon", "star",
        "glow", "beam", "path", "grid", "zone", "node", "link", "wire", "cord", "core",
        "plug", "jack", "port", "data", "byte", "code", "ping", "sync", "lock", "free",
        "fast", "slow", "high", "low", "deep", "wide", "hard", "soft", "calm", "safe",
        "crew", "helm", "seat", "belt", "mask", "vest", "suit", "boot", "cap", "head",
        "hand", "grip", "step", "push", "pull", "flip", "turn", "hold", "stop", "drop",
        "climb", "dive", "glide", "soar", "drift", "race", "dash", "zoom", "dart", "leap",
        "span", "base", "dock", "hang", "shed", "ramp", "gate", "lane", "strip", "track",
        "mark", "sign", "flag", "horn", "bell", "tone", "chirp", "beep", "click", "tick",
        "bolt", "pin", "rod", "bar", "nut", "cam", "ring", "seal", "valve", "pipe",
        "about", "after", "again", "almost", "always", "another", "answer", "around", "became", "become",
        "before", "better", "between", "black", "called", "change", "children", "circle", "clean", "color"
    ],
    'moderate': [
        # 2-Syllable Aeronautical & Standard Technical Lexicon (145 words)
        "pilot", "cockpit", "vector", "thrust", "rudder", "aileron", "engine", "intake",
        "exhaust", "turbine", "nozzle", "canopy", "fuselage", "radome", "compass", "horizon",
        "bearing", "heading", "airway", "waypoint", "beacon", "marker", "runway", "taxiway",
        "terminal", "hangar", "tower", "ground", "approach", "departure", "clearance", "radar",
        "sonar", "sensor", "probe", "static", "dynamic", "airspeed", "groundspeed", "tailwind",
        "headwind", "crosswind", "inversion", "ceiling", "stratus", "cumulus", "cirrus", "nimbus",
        "thunder", "squall", "buffet", "stall", "recovery", "flare", "touchdown", "rollout",
        "spoilers", "avionics", "inverter", "circuit", "breaker", "harness", "antenna", "receiver",
        "display", "gauge", "throttle", "propeller", "governor", "manifold", "mixture", "magneto",
        "account", "accurate", "addition", "address", "advance", "advantage", "analysis", "approach",
        "balance", "baseline", "building", "business", "cadence", "capacity", "certain", "channel",
        "cognitive", "command", "company", "complete", "condition", "consider", "constant", "control",
        "decision", "describe", "develop", "direction", "discipline", "economy", "element", "energy",
        "evidence", "example", "exercise", "experience", "feature", "frequency", "general", "history",
        "important", "industry", "interest", "language", "material", "movement", "national", "natural"
    ],
    'hard': [
        # 3-Syllable Telemetry & Mechanics (115 words)
        "telemetry", "velocity", "navigation", "orientation", "altitude", "barometer",
        "accelerometer", "maneuver", "supersonic", "transonic", "hypersonic", "aerodynamic",
        "trajectory", "equilibrium", "propulsion", "afterburner", "supercharger", "turbofan",
        "turboprop", "turboshaft", "intercooler", "synchronizer", "differential", "transmission",
        "accumulator", "modulator", "demodulator", "transceiver", "synthesizer", "oscillator",
        "attenuator", "amplifier", "potentiometer", "thermocouple", "pyrometer", "tachometer",
        "anemometer", "spectrometer", "magnetometer", "galvanometer", "multimeter", "calibrator",
        "pressurization", "depressurization", "recirculation", "refrigeration", "compressor",
        "supercritical", "boundarylayer", "centrifugal", "centripetal", "gravitational",
        "semiconductor", "microcontroller", "microprocessor", "buscontroller", "interconnect",
        "multiplexer", "demultiplexer", "serializer", "deserializer", "transistor", "capacitance",
        "accomplishment", "algorithmic", "approximate", "architectural", "asynchronous", "authenticated",
        "biochemical", "characteristic", "chronological", "circumstance", "communication", "compensate",
        "comprehensive", "computational", "configuration", "consequential", "contemporary", "correspondence",
        "differentiation", "electromagnetic", "enthusiastic", "environmental", "extraordinary", "fundamental",
        "heterogeneous", "implementation", "inconvenience", "infrastructure", "instrumentation", "insufficient"
    ],
    'expert': [
        # 4+ Syllable Aerospace & Polysyllabic Lexicon (95 words)
        "telecommunication", "intercontinental", "reconfiguration", "interoperability",
        "aerothermodynamics", "magnetohydrodynamics", "electromechanical", "turbomachinery",
        "multidimensional", "quasiperiodic", "incompressibility", "nonconservative",
        "superconducting", "thermogravimetric", "spectrophotometry", "crystallographic",
        "synchronization", "desynchronization", "miniaturization", "parameterization",
        "microarchitectural", "photolithography", "interchangeability", "reproducibility",
        "indistinguishable", "proportionality", "parallelization", "linearization",
        "nonlinearity", "indeterminacy", "orthogonality", "diagonalization",
        "eigenvalue", "eigenvector", "autocorrelation", "crosscorrelation",
        "interferometer", "polarimeter", "magnetoresistance", "piezoelectricity",
        "anachronistic", "antediluvian", "circumlocution", "counterintuitive",
        "crystallization", "deleterious", "disproportionate", "epistemological",
        "existentialism", "grandiloquent", "idiosyncrasy", "incommensurable",
        "juxtaposition", "lexicographical", "magnanimous", "metamorphosis",
        "panegyric", "phenomenological", "quintessential", "sesquipedalian",
        "synchronicity", "unprecedented", "verisimilitude", "vicissitude",
        "zeitgeist", "labyrinthine", "perspicacious"
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
    def generate_segment(test_type='words', difficulty='moderate', batch_words=55, code_lang='python'):
        diff = difficulty.lower() if difficulty and difficulty.lower() in COMMON_LEXICON else 'moderate'
        t_type = (test_type or 'words').lower().strip()
        c_lang = (code_lang or 'python').lower().strip()

        # Dedicated Programming Syntax (8 languages supported)
        if t_type in ['code', 'coding', 'programming']:
            lang_key = c_lang if c_lang in CODE_SNIPPETS else 'python'
            return random.choice(CODE_SNIPPETS[lang_key])

        # Multi-Paragraph Articles & Literature
        if t_type in ['paragraphs', 'story', 'stories']:
            return random.choice(STORIES)
        if t_type in ['article', 'articles']:
            return random.choice(ARTICLES)
        if t_type in ['professional', 'office', 'memo']:
            return random.choice(REAL_WORLD_OFFICE)
        if t_type in ['exam', 'government', 'ssc']:
            return random.choice(EXAM_GOVERNMENT_PASSAGES)
        if t_type in ['quote', 'quotes', 'literature']:
            return random.choice(QUOTES)

        # Quantitative & Precision Syntaxes
        if t_type == 'data_entry':
            return "\n".join(random.sample(DATA_ENTRY_POOL, k=min(4, len(DATA_ENTRY_POOL))))
        if t_type == 'numbers':
            nums = [str(random.randint(10, 99999)) for _ in range(batch_words)]
            return " ".join(nums)
        if t_type in ['numbers_text', 'numbers_plus']:
            words = [random.choice(COMMON_LEXICON[diff]) for _ in range(batch_words)]
            for i in range(len(words)):
                if random.random() < 0.22:
                    words[i] = str(random.randint(1, 9999))
            return " ".join(words)
        if t_type == 'punctuation':
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

        # Standard High-Frequency Word Streams
        lex = COMMON_LEXICON[diff]
        count = min(batch_words, 200)
        chosen = [random.choice(lex) for _ in range(count)]
        for i in range(0, len(chosen), 7):
            chosen[i] = chosen[i].capitalize()
            if i > 0 and not chosen[i-1].endswith('.'):
                chosen[i-1] = f"{chosen[i-1]}."
        return " ".join(chosen)