from flask import Blueprint, render_template
from app import db
from app.models.challenge import DailyChallenge
from app.models.typing import TypingTest
from app.utils.timezone import ist_today, ist_today_bounds, to_ist

challenges_bp = Blueprint('challenges', __name__)

@challenges_bp.route('/')
def index():
    return render_template('challenges/index.html')

@challenges_bp.route('/daily')
def daily():
    today = ist_today()
    challenge = DailyChallenge.query.filter_by(target_date=today).first()
    if not challenge:
        challenge = DailyChallenge(
            target_date=today,
            title="The Kinetic Discipline",
            content="True velocity is not rushed chaos; it is calm, deliberate movement free of hesitation and unnecessary recoil. Keep your hands balanced, breathe smoothly, and allow cadence to carry your speed across the keyboard."
        )
        db.session.add(challenge)
        db.session.commit()

    # Query strictly tests completed during the current IST calendar day
    start_utc, end_utc = ist_today_bounds()
    daily_tests = TypingTest.query.filter(
        TypingTest.mode == 'daily',
        TypingTest.suspicious == False,
        TypingTest.completed_at >= start_utc,
        TypingTest.completed_at < end_utc
    ).order_by(TypingTest.wpm.desc()).limit(25).all()

    # Previous 7 Days Archives
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