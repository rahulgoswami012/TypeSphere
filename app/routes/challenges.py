from flask import Blueprint, render_template, redirect, url_for
from datetime import date
from app import db
from app.models.challenge import DailyChallenge
from app.models.typing import TypingTest

challenges_bp = Blueprint('challenges', __name__)

@challenges_bp.route('/')
def index():
    return render_template('challenges/index.html')

@challenges_bp.route('/daily')
def daily():
    today = date.today()
    challenge = DailyChallenge.query.filter_by(target_date=today).first()
    if not challenge:
        challenge = DailyChallenge(
            target_date=today,
            title="Sovereignty of Focus",
            content="Consistency is the hallmark of the master craftsman. Every accurate strike compounds into pure flow and unmatched velocity."
        )
        db.session.add(challenge)
        db.session.commit()

    # Today's Leaderboard
    daily_tests = TypingTest.query.filter(
        TypingTest.mode == 'daily',
        TypingTest.suspicious == False
    ).order_by(TypingTest.wpm.desc()).limit(20).all()

    # Previous Daily Challenges Archive
    previous_challenges = DailyChallenge.query.filter(
        DailyChallenge.target_date < today
    ).order_by(DailyChallenge.target_date.desc()).limit(7).all()

    return render_template(
        'challenges/daily.html',
        challenge=challenge,
        leaderboard=daily_tests,
        history=previous_challenges
    )