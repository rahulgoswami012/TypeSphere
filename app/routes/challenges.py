from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from flask_login import current_user
import json
from app import db
from app.models.challenge import DailyChallenge
from app.models.typing import TypingTest
from app.services.content_engine import ContentEngine
from app.services.typing_analyzer import TypingAnalyzer
from app.services.anti_cheat import AntiCheatSystem
from app.services.profile_analyzer import ProfileAnalyzer
from app.services.achievement_service import AchievementService
from app.utils.timezone import ist_today, ist_today_bounds, to_ist, now_utc, get_ist_hour

challenges_bp = Blueprint('challenges', __name__)

MISSIONS_REGISTRY = [
    {
        'slug': 'daily',
        'title': 'Tactical Daily Recon (24H)',
        'badge': 'IST 24H SYNCHRONIZED',
        'badge_color': 'var(--accent)',
        'icon': '🛰️',
        'category': 'Global Reconnaissance',
        'summary': "Synchronized 24-hour tactical flight on today's official briefing text. Evaluated against all pilots worldwide on the daily IST leaderboard.",
        'objective': 'Achieve highest Net Velocity with maximum accuracy before daily reset.',
        'fail_condition': 'Aborted flight or timer expiry before completing text.',
        'duration': 60,
        'mode_type': 'daily'
    },
    {
        'slug': 'survival',
        'title': 'Shield Integrity Survival',
        'badge': '5-UNIT REACTOR CORE',
        'badge_color': 'var(--danger)',
        'icon': '🛡️',
        'category': 'Emergency Hull Defense',
        'summary': 'Cockpit reactor stability is locked to 5 battery shield cells. Every keystroke mistake causes a direct battery overload. Prevent a total reactor breach.',
        'objective': 'Complete the high-pressure flight passage without exhausting your 5 shield battery units.',
        'fail_condition': '5 cumulative keystroke mistakes trigger immediate reactor hull breach.',
        'duration': 90,
        'mode_type': 'survival'
    },
    {
        'slug': 'accuracy',
        'title': 'Zero-Error Precision Gauntlet',
        'badge': '100% MANDATORY',
        'badge_color': 'var(--success)',
        'icon': '🎯',
        'category': 'Calibrated Strike Focus',
        'summary': 'Speed is secondary; absolute precision is non-negotiable. One single errant keystroke compromises mission stealth and triggers instant abort.',
        'objective': 'Execute the entire tactical communication with flawless 100% accuracy.',
        'fail_condition': 'Any typographical error immediately aborts the mission.',
        'duration': 60,
        'mode_type': 'accuracy'
    },
    {
        'slug': 'endurance',
        'title': 'Atmospheric Endurance Marathon',
        'badge': '300-SECOND FLIGHT',
        'badge_color': 'var(--warning)',
        'icon': '⚡',
        'category': 'Cognitive Fatigue Drill',
        'summary': 'A sustained 5-minute continuous flight through shifting vocabulary densities designed to measure neuromuscular stamina and cadence stability under extended stress.',
        'objective': 'Maintain consistent cadence and at least 92% accuracy across the entire 300 seconds.',
        'fail_condition': 'Cadence collapses or flight aborted before 300 seconds elapsed.',
        'duration': 300,
        'mode_type': 'endurance'
    },
    {
        'slug': 'supersonic_sprint',
        'title': 'Supersonic Velocity Intercept',
        'badge': '70+ WPM CHECKPOINT',
        'badge_color': '#ec4899',
        'icon': '🚀',
        'category': 'High-Speed Intercept',
        'summary': 'Rapid intercept sprint. Demands burst acceleration and sustained cruising speed exceeding 70 Net WPM through tight high-frequency bigrams.',
        'objective': 'Cross the mission checkpoint maintaining an average velocity of 70+ Net WPM.',
        'fail_condition': 'Net speed falls below 70 WPM at mission completion.',
        'duration': 45,
        'mode_type': 'speed_sprint'
    },
    {
        'slug': 'exam_standard',
        'title': 'Administrative Clerical Steno (SSC)',
        'badge': 'GOVERNMENT BENCHMARK',
        'badge_color': '#f59e0b',
        'icon': '🏛️',
        'category': 'Civil Service Simulation',
        'summary': 'Statutory civil administration memo following formal Indian examination standards (SSC CGL / CHSL / High Court Clerical) with strict capitalization and legal syntax.',
        'objective': 'Transcribe the official gazette memo with at least 95% accuracy under standardized timing.',
        'fail_condition': 'Accuracy falls below 95% or error rate exceeds threshold.',
        'duration': 120,
        'mode_type': 'exam'
    },
    {
        'slug': 'syntax_infiltration',
        'title': 'Syntax Protocol Infiltration',
        'badge': 'CODE CIPHER BREACH',
        'badge_color': '#38bdf8',
        'icon': '💻',
        'category': 'Technical Cyber Flight',
        'summary': 'Terminal code injection drill requiring nested brackets, variable naming tokens, semicolons, and algorithmic syntax without cognitive hesitation pauses.',
        'objective': 'Inject the full software script without mistyping structural braces or operators.',
        'fail_condition': 'Exhausting allotted mission time before script compilation.',
        'duration': 60,
        'mode_type': 'syntax'
    }
]

@challenges_bp.route('/')
def index():
    return render_template('challenges/index.html', missions=MISSIONS_REGISTRY)

@challenges_bp.route('/daily')
def daily():
    today = ist_today()
    # Point 1: If admin has not published today's challenge yet, do NOT auto-create dummy text.
    # Leave challenge as None so the UI renders the professional Flight Control calibration notice.
    challenge = DailyChallenge.query.filter_by(target_date=today).first()

    # Query tests completed strictly within the current IST calendar day
    start_utc, end_utc = ist_today_bounds()
    daily_tests = TypingTest.query.filter(
        TypingTest.mode == 'daily',
        TypingTest.suspicious == False,
        TypingTest.completed_at >= start_utc,
        TypingTest.completed_at < end_utc
    ).order_by(TypingTest.wpm.desc()).limit(25).all()

    # Historical archives from previous days
    previous_challenges = DailyChallenge.query.filter(
        DailyChallenge.target_date < today
    ).order_by(DailyChallenge.target_date.desc()).limit(7).all()

    return render_template(
        'challenges/daily.html',
        challenge=challenge,
        leaderboard=daily_tests,
        history=previous_challenges,
        to_ist=to_ist
    )

@challenges_bp.route('/mission/<mission_slug>')
def mission_arena(mission_slug):
    mission = next((m for m in MISSIONS_REGISTRY if m['slug'] == mission_slug), None)
    if not mission:
        return redirect(url_for('challenges.index'))

    # Generate initial mission text according to mission type
    today = ist_today()
    if mission['slug'] == 'daily':
        daily_record = DailyChallenge.query.filter_by(target_date=today).first()
        if not daily_record:
            return redirect(url_for('challenges.daily'))
        passage = daily_record.content.strip()
    elif mission['mode_type'] == 'survival':
        passage = "Combat flight demands immediate reflexes and absolute tactile balance. When warning alarms blare through the cockpit, your hands must remain calm over the home anchors. Tension invites friction, and friction bleeds momentum. Maintain your trajectory, breathe smoothly, and never sacrifice precision under pressure."
    elif mission['mode_type'] == 'accuracy':
        passage = "Deliberate movement precedes true velocity. Calm hands strike cleanly and decisively without second-guessing. In high-stakes flight operations, a single miscalculated angle compromises the entire mission. Breathe steadily, observe the flight horizon, and execute every stroke flawlessly."
    elif mission['mode_type'] == 'endurance':
        passage = ContentEngine.generate_segment(test_type='article', difficulty='hard', batch_words=140)
    elif mission['mode_type'] == 'speed_sprint':
        passage = "The afterburners ignited with a deafening roar as the interceptor surged through the sound barrier into open airspace. Fast reactions and kinetic cadence keep the flight path locked on target through supersonic acceleration."
    elif mission['mode_type'] == 'exam':
        passage = ContentEngine.generate_segment(test_type='exam', difficulty='moderate', batch_words=90)
    elif mission['mode_type'] == 'syntax':
        passage = ContentEngine.generate_segment(test_type='code', difficulty='hard', code_lang='python')
    else:
        passage = ContentEngine.generate_segment(test_type='words', difficulty='moderate', batch_words=65)

    return render_template('challenges/mission_arena.html', mission=mission, passage=passage)

@challenges_bp.route('/api/submit-mission', methods=['POST'])
def submit_mission():
    try:
        data = request.get_json(force=True) or {}
        events = data.get('events', [])
        duration = max(0.1, float(data.get('duration', 1.0)))
        target_text = data.get('target_text', '')
        mode = data.get('mode', 'mission')
        outcome = data.get('outcome', 'VICTORY') # 'VICTORY' or 'DEFEAT'
        total_mistakes = int(data.get('total_mistakes', 0))

        metrics = TypingAnalyzer.calculate_metrics(events, target_text, duration)
        is_suspicious, reason = AntiCheatSystem.evaluate(events, duration, metrics['wpm'], metrics['accuracy'])

        test_record = None
        unlocked_badges = []

        # Only register official records in database if user is authenticated
        if current_user.is_authenticated:
            test_record = TypingTest(
                user_id=current_user.id,
                mode=mode,
                is_ranked=(outcome == 'VICTORY') and (not is_suspicious),
                content_category=f"Mission: {mode.replace('mission_', '').title()}",
                difficulty='hard',
                duration=duration,
                wpm=metrics['wpm'],
                raw_wpm=metrics['raw_wpm'],
                accuracy=metrics['accuracy'],
                consistency=metrics['consistency'],
                rhythm_score=metrics['rhythm_score'],
                errors=metrics['incorrect_chars'],
                total_mistakes=max(total_mistakes, metrics['incorrect_chars']),
                uncorrected_errors=metrics['incorrect_chars'],
                correct_chars=metrics['correct_chars'],
                incorrect_chars=metrics['incorrect_chars'],
                time_of_day_ist=get_ist_hour(),
                completed_at=now_utc(),
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

        return jsonify({
            'success': True,
            'outcome': outcome,
            'metrics': metrics,
            'unlocked_badges': unlocked_badges,
            'test_id': test_record.id if test_record else None
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400