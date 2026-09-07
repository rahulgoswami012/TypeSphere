from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user
from app import db
from app.models.user import User
from app.models.typing import TypingTest, TypingDNA
from app.models.challenge import Achievement, UserAchievement
from app.services.achievement_service import AchievementService

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def index():
    AchievementService.check_and_award(current_user)

    tests = TypingTest.query.filter_by(user_id=current_user.id).order_by(TypingTest.completed_at.desc()).all()
    valid_tests = [t for t in tests if not t.suspicious]

    solo_tests = [t for t in valid_tests if t.mode != 'multiplayer']
    multiplayer_tests = [t for t in valid_tests if t.mode == 'multiplayer']

    total_tests = len(valid_tests)
    avg_wpm = round(sum(t.wpm for t in valid_tests) / total_tests, 1) if total_tests else 0
    best_wpm = max((t.wpm for t in valid_tests), default=0)
    avg_accuracy = round(sum(t.accuracy for t in valid_tests) / total_tests, 1) if total_tests else 0
    total_time_minutes = round(sum(t.duration for t in valid_tests) / 60.0, 1) if total_tests else 0

    achievements = UserAchievement.query.filter_by(user_id=current_user.id).all()

    return render_template(
        'dashboard/index.html',
        total_tests=total_tests,
        avg_wpm=avg_wpm,
        best_wpm=best_wpm,
        avg_accuracy=avg_accuracy,
        total_time_minutes=total_time_minutes,
        recent_tests=solo_tests[:8],
        multiplayer_tests=multiplayer_tests[:8],
        achievements=achievements
    )

@dashboard_bp.route('/achievements')
@login_required
def achievements_showcase():
    AchievementService.check_and_award(current_user)

    all_achievements = Achievement.query.order_by(Achievement.id.asc()).all()
    unlocked_map = {
        ua.achievement_id: ua.unlocked_at 
        for ua in UserAchievement.query.filter_by(user_id=current_user.id).all()
    }

    badge_data = []
    for ach in all_achievements:
        is_unlocked = ach.id in unlocked_map
        badge_data.append({
            'code': ach.code,
            'title': ach.title,
            'description': ach.description,
            'icon': ach.icon,
            'unlocked': is_unlocked,
            'unlocked_at': unlocked_map.get(ach.id)
        })

    unlocked_count = len(unlocked_map)
    total_count = len(all_achievements)
    mastery_pct = round((unlocked_count / total_count * 100.0), 1) if total_count else 0.0

    return render_template(
        'dashboard/achievements.html',
        badges=badge_data,
        unlocked_count=unlocked_count,
        total_count=total_count,
        mastery_pct=mastery_pct
    )

@dashboard_bp.route('/dna')
@login_required
def dna_profile():
    dna = TypingDNA.query.filter_by(user_id=current_user.id).first()
    stats = dna.get_key_stats() if dna else {}
    confusions = dna.get_confusion_matrix() if dna else {}
    return render_template('dashboard/dna.html', dna=dna, stats=stats, confusions=confusions)

@dashboard_bp.route('/analytics')
@login_required
def analytics():
    tests = TypingTest.query.filter_by(user_id=current_user.id, suspicious=False).order_by(TypingTest.completed_at.asc()).all()
    
    total_tests = len(tests)
    total_words = sum(int((t.correct_chars or 0) / 5) for t in tests)
    total_seconds = sum(t.duration for t in tests)
    total_hours = round(total_seconds / 3600.0, 2)
    best_wpm = max((t.wpm for t in tests), default=0)
    avg_wpm = round(sum(t.wpm for t in tests) / total_tests, 1) if total_tests else 0
    avg_accuracy = round(sum(t.accuracy for t in tests) / total_tests, 1) if total_tests else 0
    avg_consistency = round(sum(t.consistency for t in tests) / total_tests, 1) if total_tests else 0

    improvement_rate = 0.0
    if total_tests >= 6:
        early_avg = sum(t.wpm for t in tests[:5]) / 5.0
        recent_avg = sum(t.wpm for t in tests[-5:]) / 5.0
        if early_avg > 0:
            improvement_rate = round(((recent_avg - early_avg) / early_avg) * 100.0, 1)

    data_points = [{
        'date': t.completed_at.strftime('%m-%d %H:%M'),
        'wpm': round(t.wpm, 1),
        'raw_wpm': round(t.raw_wpm, 1),
        'accuracy': round(t.accuracy, 1),
        'consistency': round(t.consistency, 1)
    } for t in tests]

    return render_template(
        'dashboard/analytics.html',
        data_points=data_points,
        total_tests=total_tests,
        total_words=total_words,
        total_hours=total_hours,
        best_wpm=best_wpm,
        avg_wpm=avg_wpm,
        avg_accuracy=avg_accuracy,
        avg_consistency=avg_consistency,
        improvement_rate=improvement_rate
    )

@dashboard_bp.route('/profile/<username>')
def public_profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    tests = TypingTest.query.filter_by(user_id=user.id, suspicious=False).order_by(TypingTest.wpm.desc()).all()
    
    total_tests = len(tests)
    best_test = tests[0] if tests else None
    best_wpm = best_test.wpm if best_test else 0
    avg_wpm = round(sum(t.wpm for t in tests) / total_tests, 1) if total_tests else 0
    avg_accuracy = round(sum(t.accuracy for t in tests) / total_tests, 1) if total_tests else 0
    
    dna = TypingDNA.query.filter_by(user_id=user.id).first()
    achievements = UserAchievement.query.filter_by(user_id=user.id).all()

    return render_template(
        'dashboard/profile.html',
        profile_user=user,
        total_tests=total_tests,
        best_test=best_test,
        best_wpm=best_wpm,
        avg_wpm=avg_wpm,
        avg_accuracy=avg_accuracy,
        dna=dna,
        achievements=achievements
    )