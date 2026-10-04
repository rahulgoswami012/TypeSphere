"""
TypeSphere - Typing Controller & Benchmark API
Coordinates standard benchmarks, custom flight studio, AI practice scans,
interactive replay telemetry, and official certificate generation.
"""

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
from flask_login import current_user
import json
import hashlib
from app import db
from app.models.typing import TypingTest, TypingText, TypingDNA
from app.models.user import User
from app.models.challenge import Achievement, UserAchievement, DailyChallenge
from app.services.access_control import PilotCapabilities
from app.services.content_engine import ContentEngine
from app.services.anti_cheat import AntiCheatSystem
from app.services.typing_analyzer import TypingAnalyzer
from app.services.profile_analyzer import ProfileAnalyzer
from app.services.weakness_coach import WeaknessCoach
from app.services.adaptive_training import AdaptiveTrainingService
from app.services.achievement_service import AchievementService
from app.utils.timezone import now_utc, get_ist_hour, ist_today

typing_bp = Blueprint('typing', __name__)


@typing_bp.route('')
@typing_bp.route('/')
@typing_bp.route('/test', endpoint='test_page')
def test_page():
    """
    Renders the Primary Cockpit Speed Benchmark.
    """
    return render_template('typing/test.html')


@typing_bp.route('/custom', endpoint='custom_text_page')
def custom_text_page():
    """
    Renders the Custom Text Practice Studio (1m to 60m / Single Pass).
    """
    return render_template('typing/custom.html')


@typing_bp.route('/practice', endpoint='practice_page')
def practice_page():
    """
    Renders the AI Flight Coach & Biometric Scan.
    """
    dna = None
    weak_keys = []
    top_confusions = []

    if current_user.is_authenticated:
        dna = TypingDNA.query.filter_by(user_id=current_user.id).first()
        if dna:
            stats = dna.get_key_stats()
            confusions = dna.get_confusion_matrix()

            for k, val in stats.items():
                if val.get('total', 0) >= 4 and k.isalpha():
                    err_rate = round((val.get('errors', 0) / val['total']) * 100, 1)
                    if err_rate > 5.0:
                        weak_keys.append((k.upper(), err_rate, val['total']))
            weak_keys.sort(key=lambda x: x[1], reverse=True)
            weak_keys = weak_keys[:5]

            for exp, mapped in confusions.items():
                for got, cnt in mapped.items():
                    if cnt >= 2:
                        top_confusions.append((exp.upper(), got.upper(), cnt))
            top_confusions.sort(key=lambda x: x[2], reverse=True)
            top_confusions = top_confusions[:4]

    curriculum = {
        'home_row': {
            'title': 'Home Row Resting Anchors',
            'keys': 'A S D F J K L ;',
            'description': 'Master finger resting positions on the home row baseline.'
        },
        'top_row': {
            'title': 'Top Row Vertical Reaches',
            'keys': 'Q W E R T Y U I O P',
            'description': 'Train upward reaches without shifting your palm off the desk.'
        },
        'bottom_row': {
            'title': 'Bottom Row Downward Tucks',
            'keys': 'Z X C V B N M , . /',
            'description': 'Develop downward finger curls while maintaining hand stability.'
        },
        'shifts': {
            'title': 'Contralateral Shift Synchronization',
            'keys': 'Left Shift + Right Shift',
            'description': 'Use opposite shift keys for smooth capitalization.'
        },
        'numbers': {
            'title': 'Numeric Row Reaches',
            'keys': '1 2 3 4 5 6 7 8 9 0',
            'description': 'Reach top numbers without looking at the keyboard.'
        },
        'symbols': {
            'title': 'Brackets & Developer Syntax',
            'keys': '{ } [ ] ( ) ; : < >',
            'description': 'Isolate programming syntax symbols and punctuation flow.'
        }
    }

    return render_template(
        'typing/practice.html',
        dna=dna,
        weak_keys=weak_keys,
        top_confusions=top_confusions,
        curriculum=curriculum
    )


@typing_bp.route('/help', endpoint='help_page')
@typing_bp.route('/guide')
def help_page():
    """
    Renders the Flight Operations Manual and Reference Guide.
    """
    return render_template('help/index.html')


@typing_bp.route('/result/<int:test_id>', endpoint='result_page')
def result_page(test_id):
    """
    Renders Flight Telemetry Analysis with Keystroke Replay Studio.
    """
    test = TypingTest.query.get_or_404(test_id)

    # Determine Skill Tier
    wpm = test.wpm
    if wpm >= 100:
        skill_tier = "Grandmaster Pilot"
        tier_color = "#ec4899"
    elif wpm >= 75:
        skill_tier = "Sonic Cadence Ace"
        tier_color = "#38bdf8"
    elif wpm >= 50:
        skill_tier = "Cruising Aviator"
        tier_color = "#10b981"
    elif wpm >= 35:
        skill_tier = "Active Pilot"
        tier_color = "#f59e0b"
    else:
        skill_tier = "Cadet Typist"
        tier_color = "#94a3b8"

    events = test.get_events()
    target_text = ""
    difficult_keys = []
    hesitations = []

    if events:
        target_text = "".join(ev.get('expected', '') for ev in events)
        error_map = {}
        for ev in events:
            if not ev.get('correct'):
                k = ev.get('expected', '').upper()
                if k:
                    error_map[k] = error_map.get(k, 0) + 1
        difficult_keys = sorted(error_map.items(), key=lambda x: x[1], reverse=True)[:5]

        for i in range(1, len(events)):
            dt = events[i].get('timestamp', 0) - events[i-1].get('timestamp', 0)
            if dt > 0.45:
                hesitations.append({
                    'char': events[i].get('expected', ''),
                    'delay_ms': int(dt * 1000)
                })
        hesitations = hesitations[:4]

    recommendation = None
    if current_user.is_authenticated and test.user_id == current_user.id:
        rec_data = WeaknessCoach.analyze_and_recommend(current_user.id)
        if rec_data and rec_data.get('has_data'):
            recommendation = rec_data['recommendation']

    certificate_eligible = (
        test.user_id is not None and
        not test.suspicious and
        test.wpm >= 35.0 and
        test.accuracy >= 90.0
    )

    return render_template(
        'typing/result.html',
        test=test,
        skill_tier=skill_tier,
        tier_color=tier_color,
        certificate_eligible=certificate_eligible,
        events_json=test.events_data or '[]',
        target_text=target_text,
        difficult_keys=difficult_keys,
        hesitations=hesitations,
        recommendation=recommendation
    )


@typing_bp.route('/certificate/<int:test_id>', endpoint='certificate_page')
def certificate_page(test_id):
    """
    Renders official verifiable Flight Wings Certificate.
    """
    test = TypingTest.query.get_or_404(test_id)

    if not test.user_id:
        return render_template(
            'typing/certificate_ineligible.html',
            message="Official Flight Certificates require a registered Active Pilot Callsign. Guest sessions are transient.",
            test=test
        )

    if test.suspicious:
        return render_template(
            'typing/certificate_ineligible.html',
            message="This flight test was flagged by anti-cheat telemetry and is ineligible for certification.",
            test=test
        )

    # Certification Thresholds
    wpm = test.wpm
    acc = test.accuracy

    if wpm >= 70.0 and acc >= 98.0:
        cert_tier = "Gold Flight Wings"
        tier_badge = "GOLD WINGS"
        tier_color = "#f59e0b"
    elif wpm >= 50.0 and acc >= 92.0:
        cert_tier = "Silver Flight Wings"
        tier_badge = "SILVER WINGS"
        tier_color = "#94a3b8"
    elif wpm >= 35.0 and acc >= 90.0:
        cert_tier = "Bronze Flight Wings"
        tier_badge = "BRONZE WINGS"
        tier_color = "#d97706"
    else:
        return render_template(
            'typing/certificate_ineligible.html',
            message="Flight benchmarks must meet at least Bronze Wings standards (35+ WPM and 90%+ Accuracy).",
            test=test
        )

    candidate_name = test.user.display_callsign if hasattr(test.user, 'display_callsign') else test.user.username
    hash_source = f"TS-{test.id}-{test.user_id}-{test.wpm}-{test.accuracy}-{test.completed_at.isoformat()}"
    cert_code = f"TS-{hashlib.sha256(hash_source.encode()).hexdigest()[:10].upper()}"

    return render_template(
        'typing/certificate.html',
        test=test,
        candidate_name=candidate_name,
        cert_tier=cert_tier,
        tier_badge=tier_badge,
        tier_color=tier_color,
        cert_code=cert_code
    )


# ==============================================================
# API TELEMETRY ENDPOINTS
# ==============================================================

@typing_bp.route('/api/text')
def get_prompt_text():
    """
    Feeds authentic text prompts from ContentEngine.
    """
    content_type = request.args.get('content_type', 'words')
    level = request.args.get('level', 'moderate')
    code_lang = request.args.get('code_lang', 'python')
    batch_size = request.args.get('batch_size', 55, type=int)

    segment = ContentEngine.generate_segment(
        test_type=content_type,
        difficulty=level,
        batch_words=batch_size,
        code_lang=code_lang
    )
    return jsonify({'content': segment})


@typing_bp.route('/api/daily-text')
def get_daily_text():
    """
    Returns today's synchronized 24-hour challenge briefing.
    """
    today = ist_today()
    challenge = DailyChallenge.query.filter_by(target_date=today).first()
    if challenge:
        return jsonify({'content': challenge.content, 'title': challenge.title})
    return jsonify({
        'content': "When an aircraft accelerates through the transonic boundary toward Mach 1, air molecules ahead of the airframe cannot disperse fast enough to accommodate the advancing geometry.",
        'title': "Supersonic Transonic Flight"
    })


@typing_bp.route('/api/adaptive-drill')
def get_adaptive_drill():
    """
    Generates personalized drill isolating the pilot's weak keys.
    """
    uid = current_user.id if current_user.is_authenticated else None
    drill_text, weak_keys = AdaptiveTrainingService.generate_drill(uid)
    return jsonify({'drill_text': drill_text, 'weak_keys': weak_keys})


@typing_bp.route('/api/ghost/<int:test_id>')
def get_ghost_telemetry(test_id):
    """
    Provides target pacing telemetry from a previous test run.
    """
    target = TypingTest.query.get_or_404(test_id)
    return jsonify({
        'wpm': target.wpm,
        'accuracy': target.accuracy,
        'duration': target.duration
    })


@typing_bp.route('/api/submit', methods=['POST'])
def submit_flight():
    """
    Processes, validates, and stores flight telemetry.
    Differentiates Total Mistakes from Uncorrected Errors.
    """
    try:
        data = request.get_json(force=True) or {}
        events = data.get('events', [])
        duration = max(0.1, float(data.get('duration', 1.0)))
        target_text = data.get('target_text', '')
        mode = data.get('mode', 'timed_60')
        is_ranked = bool(data.get('is_ranked', False))
        content_category = data.get('content_category', 'words')
        difficulty = data.get('difficulty', 'moderate')
        total_mistakes = int(data.get('total_mistakes', 0))
        uncorrected_errors = int(data.get('uncorrected_errors', 0))

        metrics = TypingAnalyzer.calculate_metrics(events, target_text, duration)
        is_suspicious, reason = AntiCheatSystem.evaluate(events, duration, metrics['wpm'], metrics['accuracy'])

        test_record = None
        unlocked_badges = []

        if current_user.is_authenticated:
            test_record = TypingTest(
                user_id=current_user.id,
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
                errors=uncorrected_errors,
                total_mistakes=max(total_mistakes, metrics['incorrect_chars']),
                uncorrected_errors=uncorrected_errors,
                correct_chars=metrics['correct_chars'],
                incorrect_chars=metrics['incorrect_chars'],
                extra_chars=metrics['extra_chars'],
                missed_chars=metrics['missed_chars'],
                completed_at=now_utc(),
                time_of_day_ist=get_ist_hour(),
                suspicious=is_suspicious,
                suspicion_reason=reason,
                timeline_data=json.dumps(data.get('timeline', [])),
                events_data=json.dumps(events)
            )
            db.session.add(test_record)
            db.session.commit()

            try:
                ProfileAnalyzer.update_dna(current_user.id, events)
            except Exception:
                pass

            try:
                unlocked_badges = AchievementService.check_and_award(current_user)
            except Exception:
                pass
        else:
            # Guest Flight Session
            guest_runs = session.get('guest_runs', [])
            guest_runs.append({
                'wpm': metrics['wpm'],
                'accuracy': metrics['accuracy'],
                'duration': duration,
                'total_mistakes': total_mistakes,
                'uncorrected_errors': uncorrected_errors
            })
            session['guest_runs'] = guest_runs[-10:]
            session.modified = True

        return jsonify({
            'success': True,
            'test_id': test_record.id if test_record else None,
            'metrics': metrics,
            'is_ranked': is_ranked and not is_suspicious,
            'unlocked_badges': unlocked_badges,
            'is_guest': not current_user.is_authenticated
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400