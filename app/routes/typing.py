from flask import Blueprint, render_template, request, jsonify
from flask_login import current_user
import json
import random
import traceback
import hashlib
from datetime import date, datetime
from app import db
from app.models.typing import TypingTest, TypingText, TypingDNA
from app.models.challenge import DailyChallenge
from app.models.feedback import Announcement
from app.services.typing_analyzer import TypingAnalyzer
from app.services.anti_cheat import AntiCheatSystem
from app.services.profile_analyzer import ProfileAnalyzer
from app.services.weakness_coach import WeaknessCoach
from app.services.achievement_service import AchievementService
from app.services.content_engine import ContentEngine

typing_bp = Blueprint('typing', __name__)

@typing_bp.route('/')
def test_page():
    active_announcement = Announcement.query.filter_by(is_active=True).order_by(Announcement.id.desc()).first()
    return render_template('typing/test.html', announcement=active_announcement)

@typing_bp.route('/custom')
def custom_text_page():
    return render_template('typing/custom.html')

@typing_bp.route('/practice')
def practice_page():
    weak_keys = []
    top_confusions = []
    dna = None
    if current_user.is_authenticated:
        dna = TypingDNA.query.filter_by(user_id=current_user.id).first()
        if dna:
            stats = dna.get_key_stats()
            rates = []
            for k, val in stats.items():
                if val.get('total', 0) >= 4 and k.isalpha():
                    err_rate = val.get('errors', 0) / val['total']
                    rates.append((k.upper(), round(err_rate * 100, 1), val.get('total', 0)))
            rates.sort(key=lambda x: x[1], reverse=True)
            weak_keys = rates[:4]

            conf_dict = dna.get_confusion_matrix()
            for exp, mapped in conf_dict.items():
                for typed, cnt in mapped.items():
                    top_confusions.append((exp.upper(), typed.upper(), cnt))
            top_confusions.sort(key=lambda x: x[2], reverse=True)
            top_confusions = top_confusions[:3]

    return render_template(
        'typing/practice.html',
        curriculum=CURRICULUM_LESSONS,
        weak_keys=weak_keys,
        top_confusions=top_confusions,
        dna=dna
    )

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
    # 1. Lesson from Touch Typing Academy
    lesson_key = request.args.get('lesson')
    if lesson_key and lesson_key in CURRICULUM_LESSONS:
        lesson = CURRICULUM_LESSONS[lesson_key]
        return jsonify({
            'id': 0,
            'content': lesson['content'],
            'category': lesson['title'],
            'is_code': False
        })

    # 2. Retry specific previous test run
    retry_id = request.args.get('retry_test_id')
    if retry_id:
        try:
            prev_test = TypingTest.query.get(int(retry_id))
            if prev_test and prev_test.events_data:
                events = prev_test.get_events()
                if events:
                    max_idx = max((ev.get('char_index', 0) for ev in events), default=0)
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
        except Exception:
            pass

    # 3. Dynamic Multi-Tiered Content Generation
    test_type = request.args.get('test_type', request.args.get('content_type', 'words')).lower()
    difficulty = request.args.get('level', 'moderate').lower()
    code_lang = request.args.get('code_lang', 'python').lower()

    content = ContentEngine.generate_segment(
        test_type=test_type,
        difficulty=difficulty,
        batch_words=60,
        code_lang=code_lang
    )

    category_title = f"{test_type.replace('_', ' ').title()} ({difficulty.title()})"
    return jsonify({
        'id': 0,
        'content': content,
        'category': category_title,
        'is_code': test_type in ['code', 'coding']
    })

@typing_bp.route('/api/adaptive-drill')
def get_adaptive_drill():
    uid = current_user.id if current_user.is_authenticated else None
    drill = WeaknessCoach.generate_targeted_drill(uid)
    return jsonify(drill)

@typing_bp.route('/api/submit', methods=['POST'])
def submit_test():
    try:
        data = request.get_json(force=True) or {}
        events = data.get('events', [])
        duration = max(0.1, float(data.get('duration', 1.0)))
        target_text = data.get('target_text', '')
        mode = data.get('mode', 'timed')
        is_ranked = bool(data.get('is_ranked', False))
        content_category = data.get('content_category', 'General')
        difficulty = data.get('difficulty', 'moderate')

        metrics = TypingAnalyzer.calculate_metrics(events, target_text, duration)
        is_suspicious, reason = AntiCheatSystem.evaluate(events, duration, metrics['wpm'], metrics['accuracy'])

        test = TypingTest(
            user_id=current_user.id if current_user.is_authenticated else None,
            mode=mode,
            is_ranked=is_ranked and not is_suspicious,
            content_category=content_category,
            difficulty=difficulty,
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

    # Synthesize intelligent next-step recommendation
    coach_data = WeaknessCoach.analyze_and_recommend(test.user_id)
    recommendation = coach_data.get('recommendation')

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
        events_json=json.dumps(events),
        recommendation=recommendation
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

CURRICULUM_LESSONS = {
    'home_row': {
        'title': "Stage 1: Home Row Foundation",
        'keys': "A S D F J K L ;",
        'description': "Anchor your muscle memory on the baseline resting keys. Keep index fingers over F and J.",
        'content': "asdf jkl; a fad flask fall glad half dash salad flash salsa jak lad fall glad ask a fad flask fall"
    },
    'top_row': {
        'title': "Stage 2: Upper Row Extensions",
        'keys': "Q W E R T Y U I O P",
        'description': "Train upward vertical reaches without shifting your wrists off the desk.",
        'content': "quite write power tower quote trip your wipe wire pure tyre quiet root weep pore write power tower quote"
    },
    'bottom_row': {
        'title': "Stage 3: Lower Row Transitions",
        'keys': "Z X C V B N M",
        'description': "Practice downward finger tucks while maintaining wrist stability.",
        'content': "cabin van mix zoom bomb zinc exam calm civic move bank comb mimic vanish cabin van mix zoom bomb zinc"
    },
    'number_row': {
        'title': "Stage 4: Top Numeric Row",
        'keys': "1 2 3 4 5 6 7 8 9 0",
        'description': "Drill long upper-row stretches for numbers and data entry without looking at your hands.",
        'content': "102 394 582 710 934 681 205 739 461 820 159 348 726 501 934 682 102 394 582 710 934"
    },
    'symbols': {
        'title': "Stage 5: Developer Syntax & Brackets",
        'keys': "{} [] () <> / \\ ; : ' \"",
        'description': "Master punctuation and nested programming brackets crucial for software engineering.",
        'content': "{ [ ( < > ) ] } ; : \" ' / \\ ( [ { } ] ) < > ; : ' \" { [ ( ) ] } / ; : \" ' < > { [ ( < > ) ] }"
    },
    'ngrams': {
        'title': "Stage 6: Frequent English N-Grams",
        'keys': "the and tha ent ion tio for",
        'description': "Type common multi-character letter clusters as single continuous muscle memory motions.",
        'content': "the there that other their they these them then another rather whether together furthermore therefore the there that"
    }
}