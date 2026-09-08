from flask import Blueprint, render_template, request
from flask_login import current_user
from datetime import datetime, timedelta
from app.models.user import User
from app.models.typing import TypingTest

leaderboard_bp = Blueprint('leaderboard', __name__)

@leaderboard_bp.route('/')
def index():
    sort_by = request.args.get('sort', 'wpm')
    mode_filter = request.args.get('mode', 'all')
    period_filter = request.args.get('period', 'all')  # 'all', 'month', 'week', 'today'

    # 1. Official Ranked Elo Division Standings
    if mode_filter == 'ranked_elo':
        top_ranked_users = User.query.filter(User.ranked_wins + User.ranked_losses > 0).order_by(User.elo_rating.desc()).limit(50).all()
        return render_template(
            'leaderboard/index.html',
            tests=[],
            podium=[],
            ranked_users=top_ranked_users,
            user_rank_info=None,
            current_sort=sort_by,
            current_mode=mode_filter,
            current_period=period_filter
        )

    # 2. Filter strictly for verified tests (Custom text / Practice tests excluded)
    query = TypingTest.query.filter_by(suspicious=False, is_ranked=True).filter(TypingTest.user_id.isnot(None))

    # Time-Window Aggregations (Weekly & Monthly Cycles)
    now = datetime.utcnow()
    if period_filter == 'today':
        today_start = datetime(now.year, now.month, now.day)
        query = query.filter(TypingTest.completed_at >= today_start)
    elif period_filter == 'week':
        week_cutoff = now - timedelta(days=7)
        query = query.filter(TypingTest.completed_at >= week_cutoff)
    elif period_filter == 'month':
        month_cutoff = now - timedelta(days=30)
        query = query.filter(TypingTest.completed_at >= month_cutoff)

    # Mode Filtering
    if mode_filter == 'timed_60':
        query = query.filter(TypingTest.mode == 'timed_60')
    elif mode_filter == 'timed_30':
        query = query.filter(TypingTest.mode == 'timed_30')
    elif mode_filter == 'timed_15':
        query = query.filter(TypingTest.mode == 'timed_15')
    elif mode_filter == 'timed_120':
        query = query.filter(TypingTest.mode == 'timed_120')

    # Sorting
    if sort_by == 'accuracy':
        query = query.order_by(TypingTest.accuracy.desc(), TypingTest.wpm.desc())
    elif sort_by == 'consistency':
        query = query.order_by(TypingTest.consistency.desc(), TypingTest.wpm.desc())
    else:
        query = query.order_by(TypingTest.wpm.desc(), TypingTest.accuracy.desc())

    top_tests = query.limit(50).all()
    podium = top_tests[:3] if len(top_tests) >= 3 else top_tests

    # 3. Calculate User Standing & Percentile
    user_rank_info = None
    if current_user.is_authenticated:
        user_best_query = TypingTest.query.filter_by(user_id=current_user.id, is_ranked=True, suspicious=False)
        if period_filter == 'today':
            user_best_query = user_best_query.filter(TypingTest.completed_at >= datetime(now.year, now.month, now.day))
        elif period_filter == 'week':
            user_best_query = user_best_query.filter(TypingTest.completed_at >= (now - timedelta(days=7)))
        elif period_filter == 'month':
            user_best_query = user_best_query.filter(TypingTest.completed_at >= (now - timedelta(days=30)))

        user_best = user_best_query.order_by(TypingTest.wpm.desc()).first()
        if user_best:
            total_verified = query.count()
            higher_count = query.filter(TypingTest.wpm > user_best.wpm).count()
            rank = higher_count + 1
            pct = round(((total_verified - rank + 1) / total_verified) * 100.0, 1) if total_verified else 100.0
            user_rank_info = {
                'rank': rank,
                'percentile': pct,
                'best_wpm': user_best.wpm,
                'best_acc': user_best.accuracy
            }

    return render_template(
        'leaderboard/index.html',
        tests=top_tests,
        podium=podium,
        ranked_users=[],
        user_rank_info=user_rank_info,
        current_sort=sort_by,
        current_mode=mode_filter,
        current_period=period_filter
    )