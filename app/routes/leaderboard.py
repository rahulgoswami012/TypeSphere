from flask import Blueprint, render_template, request
from app.models.user import User
from app.models.typing import TypingTest

leaderboard_bp = Blueprint('leaderboard', __name__)

@leaderboard_bp.route('/')
def index():
    sort_by = request.args.get('sort', 'wpm')
    mode_filter = request.args.get('mode', 'all')

    # Ranked Elo Standings Mode
    if mode_filter == 'ranked_elo':
        top_ranked_users = User.query.filter(User.ranked_wins + User.ranked_losses > 0).order_by(User.elo_rating.desc()).limit(50).all()
        return render_template(
            'leaderboard/index.html',
            tests=[],
            podium=[],
            ranked_users=top_ranked_users,
            current_sort=sort_by,
            current_mode=mode_filter
        )

    query = TypingTest.query.filter_by(suspicious=False).filter(TypingTest.user_id.isnot(None))

    if mode_filter == 'timed_60':
        query = query.filter(TypingTest.mode == 'timed', TypingTest.duration >= 55, TypingTest.duration <= 65)
    elif mode_filter == 'timed_30':
        query = query.filter(TypingTest.mode == 'timed', TypingTest.duration >= 25, TypingTest.duration <= 35)
    elif mode_filter == 'code':
        query = query.filter(TypingTest.mode == 'code')
    elif mode_filter == 'daily':
        query = query.filter(TypingTest.mode == 'daily')

    if sort_by == 'accuracy':
        query = query.order_by(TypingTest.accuracy.desc(), TypingTest.wpm.desc())
    elif sort_by == 'consistency':
        query = query.order_by(TypingTest.consistency.desc(), TypingTest.wpm.desc())
    else:
        query = query.order_by(TypingTest.wpm.desc(), TypingTest.accuracy.desc())

    top_tests = query.limit(50).all()
    podium = top_tests[:3] if len(top_tests) >= 3 else top_tests

    return render_template(
        'leaderboard/index.html',
        tests=top_tests,
        podium=podium,
        ranked_users=[],
        current_sort=sort_by,
        current_mode=mode_filter
    )