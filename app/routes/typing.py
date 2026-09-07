from flask import Blueprint, render_template, request, jsonify
from flask_login import current_user
import json
import random
import traceback
import hashlib
from datetime import date, datetime
from app import db
from app.models.typing import TypingTest, TypingText
from app.models.challenge import DailyChallenge
from app.services.typing_analyzer import TypingAnalyzer
from app.services.anti_cheat import AntiCheatSystem
from app.services.profile_analyzer import ProfileAnalyzer
from app.services.adaptive_training import AdaptiveTrainingService
from app.services.achievement_service import AchievementService

typing_bp = Blueprint('typing', __name__)

LANGUAGE_WORD_BANKS = {
    'english': [
        "the", "be", "to", "of", "and", "a", "in", "that", "have", "it", "for", "not", "on", "with", "he", "as",
        "you", "do", "at", "this", "but", "his", "by", "from", "they", "we", "say", "her", "she", "or", "an",
        "will", "my", "one", "all", "would", "there", "their", "what", "so", "up", "out", "if", "about", "who",
        "get", "which", "go", "me", "when", "make", "can", "like", "time", "no", "just", "him", "know", "take"
    ],
    'spanish': [
        "de", "la", "que", "el", "en", "y", "a", "los", "se", "del", "las", "un", "por", "con", "no", "una",
        "su", "para", "es", "al", "lo", "como", "mas", "pero", "sus", "le", "ya", "o", "fue", "este", "ha",
        "si", "porque", "esta", "son", "entre", "cuando", "muy", "sin", "sobre", "ser", "tiene", "tambien",
        "me", "hasta", "hay", "donde", "quien", "desde", "todo", "nos", "durante", "todos", "uno", "les", "ni"
    ],
    'french': [
        "de", "la", "le", "et", "les", "des", "en", "un", "du", "une", "que", "est", "pour", "qui", "dans", "a",
        "par", "sur", "pas", "plus", "au", "avec", "ce", "ne", "on", "se", "sont", "comme", "mais", "ou",
        "nous", "sa", "fait", "ses", "tout", "faire", "leur", "aussi", "ces", "deux", "bien", "elle", "si",
        "sans", "peut", "encore", "temps", "tres", "meme", "autre", "apres", "mon", "leur", "sous", "notre"
    ],
    'german': [
        "der", "die", "und", "in", "den", "von", "zu", "das", "mit", "sich", "des", "auf", "fur", "ist", "im",
        "dem", "nicht", "ein", "eine", "als", "auch", "es", "an", "werden", "aus", "er", "hat", "dass", "sie",
        "nach", "wird", "bei", "einer", "um", "am", "sind", "noch", "wie", "einem", "uber", "einen", "so",
        "sie", "zum", "war", "haben", "nur", "oder", "aber", "vor", "zur", "bis", "mehr", "durch", "man", "sein"
    ],
    'italian': [
        "di", "e", "il", "che", "la", "a", "in", "un", "per", "del", "non", "i", "si", "da", "le", "della",
        "con", "sono", "una", "dei", "delle", "come", "al", "ha", "su", "nel", "anche", "piu", "ma", "questo",
        "ed", "dalla", "gli", "nel", "questa", "se", "tutto", "uno", "dopo", "loro", "senza", "quando", "molto"
    ],
    'portuguese': [
        "de", "a", "o", "que", "e", "do", "da", "em", "um", "para", "com", "nao", "uma", "os", "no", "se",
        "na", "por", "mais", "as", "dos", "como", "mas", "foi", "ao", "ele", "das", "tem", "a", "seu", "sua",
        "ou", "ser", "quando", "muito", "ha", "nos", "ja", "estao", "eu", "tambem", "so", "pelo", "pela", "ate"
    ],
    'japanese': [
        "kono", "sono", "ano", "hito", "koto", "toki", "sekai", "kokoro", "hikari", "kaze", "michi", "yume",
        "mirai", "chikara", "shinjitsu", "kotoba", "shizukesa", "hoshi", "sora", "umi", "hana", "tsuki",
        "jibun", "anata", "watashi", "ima", "kinou", "ashita", "tsuyoi", "yasashii", "utsukushii", "subete"
    ]
}

CODE_SNIPPETS = {
    'python': "def quicksort(arr):\n    if len(arr) <= 1:\n        return arr\n    pivot = arr[len(arr) // 2]\n    left = [x for x in arr if x < pivot]\n    middle = [x for x in arr if x == pivot]\n    right = [x for x in arr if x > pivot]\n    return quicksort(left) + middle + quicksort(right)",
    'javascript': "const calculateCadence = (events) => {\n  return events.reduce((acc, curr, idx, arr) => {\n    if (idx === 0) return acc;\n    return acc + (curr.timestamp - arr[idx - 1].timestamp);\n  }, 0) / (events.length - 1);\n};",
    'sql': "SELECT users.id, users.username, MAX(typing_tests.wpm) as best_wpm\nFROM users\nJOIN typing_tests ON users.id = typing_tests.user_id\nWHERE typing_tests.suspicious = FALSE\nGROUP BY users.id, users.username\nORDER BY best_wpm DESC\nLIMIT 10;",
    'html': "<div class=\"dashboard-card\">\n  <header class=\"card-header\">\n    <h2 class=\"title\">Pilot Metrics</h2>\n  </header>\n  <section class=\"content-body\">\n    <span class=\"badge verified\">Verified</span>\n  </section>\n</div>",
    'css': ".typing-container {\n  display: flex;\n  flex-direction: column;\n  background: var(--bg-card);\n  border: 1px solid var(--accent);\n  border-radius: 8px;\n  padding: 1.5rem;\n  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);\n}",
    'java': "public class BinarySearchTree {\n    private Node root;\n    public boolean search(int val) {\n        Node curr = root;\n        while (curr != null) {\n            if (curr.data == val) return true;\n            curr = (val < curr.data) ? curr.left : curr.right;\n        }\n        return false;\n    }\n}"
}

@typing_bp.route('/')
def test_page():
    return render_template('typing/test.html')

@typing_bp.route('/custom')
def custom_text_page():
    return render_template('typing/custom.html')

@typing_bp.route('/api/daily-text')
def get_daily_text():
    today = date.today()
    challenge = DailyChallenge.query.filter_by(target_date=today).first()
    if not challenge:
        challenge = DailyChallenge(
            target_date=today,
            title="The Kinetic Discipline",
            content="True velocity is not rushed chaos; it is calm, deliberate movement free of hesitation and unnecessary recoil."
        )
        db.session.add(challenge)
        db.session.commit()

    return jsonify({
        'id': challenge.id,
        'title': challenge.title,
        'content': challenge.content.strip(),
        'date': challenge.target_date.strftime('%B %d, %Y')
    })

@typing_bp.route('/api/text')
def get_text():
    retry_id = request.args.get('retry_test_id')
    if retry_id:
        prev_test = TypingTest.query.get(int(retry_id))
        if prev_test and prev_test.events_data:
            events = prev_test.get_events()
            if events:
                max_idx = max(ev.get('char_index', 0) for ev in events)
                text_chars = [' '] * (max_idx + 1)
                for ev in events:
                    idx = ev.get('char_index', 0)
                    exp = ev.get('expected', '')
                    if 0 <= idx < len(text_chars):
                        text_chars[idx] = exp
                reconstructed = "".join(text_chars).strip()
                if len(reconstructed) > 5:
                    return jsonify({
                        'id': prev_test.id,
                        'content': reconstructed,
                        'category': 'Retry Drill',
                        'is_code': prev_test.mode == 'code'
                    })

    mode = request.args.get('mode', 'timed')
    category = request.args.get('category', 'General')
    language = request.args.get('language', 'english').lower()
    is_code = request.args.get('is_code', 'false') == 'true'
    code_lang = request.args.get('code_lang', 'python').lower()
    word_count = int(request.args.get('words', 25))
    with_punctuation = request.args.get('punctuation', 'false') == 'true'
    with_numbers = request.args.get('numbers', 'false') == 'true'

    if is_code:
        content = CODE_SNIPPETS.get(code_lang, CODE_SNIPPETS['python'])
        return jsonify({
            'id': 0,
            'content': content,
            'category': f'Code: {code_lang.upper()}',
            'is_code': True
        })

    # Multi-language word generation
    if language in LANGUAGE_WORD_BANKS and language != 'english':
        bank = LANGUAGE_WORD_BANKS[language]
        selected_content = " ".join(random.choices(bank, k=word_count))
        category = f"Language: {language.capitalize()}"
    else:
        query = TypingText.query
        if category == 'Quote':
            query = query.filter_by(category='Literature', is_code=False)
        elif category != 'All':
            query = query.filter_by(category=category, is_code=False)

        texts = query.all()
        if not texts:
            bank = LANGUAGE_WORD_BANKS['english']
            selected_content = " ".join(random.choices(bank, k=word_count))
        else:
            selected = random.choice(texts)
            selected_content = selected.content.strip()
            if mode == 'words':
                word_list = selected_content.split()
                selected_content = " ".join(word_list[:word_count]) if len(word_list) >= word_count else " ".join(word_list)

    words = selected_content.split()
    if with_numbers:
        for i in range(len(words)):
            if random.random() < 0.25:
                words[i] = str(random.randint(10, 999))
    if with_punctuation:
        punct_marks = [",", ".", ";", "!", "?"]
        for i in range(len(words)):
            if random.random() < 0.35 and not words[i].endswith(tuple(punct_marks)):
                words[i] = words[i] + random.choice(punct_marks)
            if random.random() < 0.25:
                words[i] = words[i].capitalize()

    final_content = " ".join(words)

    return jsonify({
        'id': 0,
        'content': final_content,
        'category': category,
        'is_code': False
    })

@typing_bp.route('/api/adaptive-drill')
def get_adaptive_drill():
    uid = current_user.id if current_user.is_authenticated else 0
    drill, keys = AdaptiveTrainingService.generate_drill(uid)
    return jsonify({'content': drill, 'focus_keys': keys})

@typing_bp.route('/api/submit', methods=['POST'])
def submit_test():
    try:
        data = request.get_json(force=True) or {}
        events = data.get('events', [])
        duration = max(0.1, float(data.get('duration', 1.0)))
        target_text = data.get('target_text', '')
        mode = data.get('mode', 'timed')

        metrics = TypingAnalyzer.calculate_metrics(events, target_text, duration)
        is_suspicious, reason = AntiCheatSystem.evaluate(events, duration, metrics['wpm'], metrics['accuracy'])

        test = TypingTest(
            user_id=current_user.id if current_user.is_authenticated else None,
            mode=mode,
            duration=duration,
            wpm=metrics['wpm'],
            raw_wpm=metrics['raw_wpm'],
            accuracy=metrics['accuracy'],
            consistency=metrics['consistency'],
            rhythm_score=metrics['rhythm_score'],
            errors=metrics['incorrect_chars'],
            correct_chars=metrics['correct_chars'],
            incorrect_chars=metrics['incorrect_chars'],
            extra_chars=metrics['extra_chars'],
            missed_chars=metrics['missed_chars'],
            suspicious=is_suspicious,
            suspicion_reason=reason,
            timeline_data=json.dumps(data.get('timeline', [])),
            events_data=json.dumps(events)
        )

        db.session.add(test)
        db.session.commit()

        if current_user.is_authenticated:
            try:
                ProfileAnalyzer.update_dna(current_user.id, events)
            except Exception:
                pass

        unlocked = []
        if current_user.is_authenticated:
            try:
                unlocked = AchievementService.check_and_award(current_user)
            except Exception:
                pass

        return jsonify({
            'success': True,
            'test_id': test.id,
            'metrics': metrics,
            'suspicious': is_suspicious,
            'unlocked_badges': unlocked
        })
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 400

@typing_bp.route('/result/<int:test_id>')
def result_page(test_id):
    test = TypingTest.query.get_or_404(test_id)
    pb_wpm = 0
    avg_wpm = 0
    if test.user_id:
        user_tests = TypingTest.query.filter_by(user_id=test.user_id, suspicious=False).all()
        if user_tests:
            pb_wpm = max((t.wpm for t in user_tests), default=0)
            avg_wpm = round(sum(t.wpm for t in user_tests) / len(user_tests), 1)

    wpm = test.wpm
    if wpm >= 100:
        skill_tier = "Olympian Master"
        tier_color = "#a371f7"
    elif wpm >= 75:
        skill_tier = "Pro Typist"
        tier_color = "var(--accent)"
    elif wpm >= 50:
        skill_tier = "Fluent Typist"
        tier_color = "var(--success)"
    elif wpm >= 30:
        skill_tier = "Intermediate"
        tier_color = "var(--warning)"
    else:
        skill_tier = "Novice Apprentice"
        tier_color = "var(--text-muted)"

    xp_earned = int((test.wpm * (test.accuracy / 100.0)) * (test.duration / 10.0))

    events = test.get_events()
    difficult_keys = {}
    hesitations = []
    
    max_idx = max((ev.get('char_index', 0) for ev in events), default=0)
    text_chars = [' '] * (max_idx + 1)

    for i, ev in enumerate(events):
        idx = ev.get('char_index', 0)
        exp = ev.get('expected', '')
        if 0 <= idx < len(text_chars):
            text_chars[idx] = exp

        if not ev.get('correct', True) and exp:
            difficult_keys[exp] = difficult_keys.get(exp, 0) + 1
        
        if i > 0:
            dt = ev.get('timestamp', 0) - events[i-1].get('timestamp', 0)
            if dt > 0.45 and exp.strip():
                hesitations.append({
                    'char': exp,
                    'delay_ms': int(dt * 1000)
                })

    reconstructed_text = "".join(text_chars).strip()
    sorted_difficult_keys = sorted(difficult_keys.items(), key=lambda x: x[1], reverse=True)[:5]
    top_hesitations = sorted(hesitations, key=lambda x: x['delay_ms'], reverse=True)[:4]

    return render_template(
        'typing/result.html',
        test=test,
        pb_wpm=pb_wpm,
        avg_wpm=avg_wpm,
        skill_tier=skill_tier,
        tier_color=tier_color,
        xp_earned=xp_earned,
        difficult_keys=sorted_difficult_keys,
        hesitations=top_hesitations,
        target_text=reconstructed_text,
        events_json=json.dumps(events)
    )

@typing_bp.route('/certificate/<int:test_id>')
def certificate_page(test_id):
    test = TypingTest.query.get_or_404(test_id)
    
    if current_user.is_authenticated:
        AchievementService.award_code(current_user, 'certified_typist')

    if test.wpm >= 70 and test.accuracy >= 98.0:
        cert_tier = "Gold Certificate"
        tier_badge = "GOLD"
        tier_color = "#f59e0b"
    elif test.wpm >= 50 and test.accuracy >= 90.0:
        cert_tier = "Silver Certificate"
        tier_badge = "SILVER"
        tier_color = "#94a3b8"
    else:
        cert_tier = "Bronze Certificate"
        tier_badge = "BRONZE"
        tier_color = "#b45309"

    cert_hash_input = f"{test.id}-{test.wpm}-{test.accuracy}-{test.completed_at}"
    cert_code = "TS-" + hashlib.sha256(cert_hash_input.encode()).hexdigest()[:10].upper()
    candidate_name = test.user.username if test.user else "Verified Guest Typist"

    return render_template(
        'typing/certificate.html',
        test=test,
        cert_tier=cert_tier,
        tier_badge=tier_badge,
        tier_color=tier_color,
        cert_code=cert_code,
        candidate_name=candidate_name
    )

@typing_bp.route('/api/ghost/<int:test_id>')
def ghost_data(test_id):
    test = TypingTest.query.get_or_404(test_id)
    return jsonify({
        'test_id': test.id,
        'wpm': test.wpm,
        'events': test.get_events(),
        'timeline': test.get_timeline()
    })