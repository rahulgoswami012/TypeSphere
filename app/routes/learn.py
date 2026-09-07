from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.models.curriculum import LessonStage, UserLessonProgress
from app.models.typing import TypingTest

learn_bp = Blueprint('learn', __name__)

CURRICULUM_TRACKS = [
    # 1. BEGINNER TRACK (0 - 40 WPM)
    ('beginner', 1, "Keyboard Orientation & Posture", "intro", "Learn home row resting anchors, hand ergonomics, and finger coordination.", "f j f j f j dk dk sl sl a; a; fj dk sl a;", 15.0, 90.0, 2),
    ('beginner', 2, "Home Row Mastery", "home-row", "Anchor muscle memory exclusively on the baseline resting keys.", "asdf jkl; a fad flask fall glad half dash salad flash salsa lad fall", 20.0, 92.0, 2),
    ('beginner', 3, "Top Row Extensions", "top-row", "Train upward vertical reaches without shifting wrists off the desk.", "quit write power tower quote trip your wipe wire pure quiet root weep", 25.0, 92.0, 2),
    ('beginner', 4, "Bottom Row Transitions", "bottom-row", "Practice downward finger tucks while maintaining palm stability.", "cabin van mix zoom bomb zinc exam calm civic move bank comb mimic", 28.0, 92.0, 2),

    # 2. INTERMEDIATE TRACK (40 - 70 WPM)
    ('intermediate', 1, "Contralateral Shift Synchronization", "shifts", "Synchronize shift-key holds for effortless capitalization.", "The Quick Brown Fox Jumps Over The Lazy Dog London Paris Tokyo", 38.0, 94.0, 2),
    ('intermediate', 2, "High-Frequency Core Vocabulary", "core-words", "Fluid execution on the top 100 most frequent English building blocks.", "their there would about which could people other first water after", 45.0, 94.0, 2),
    ('intermediate', 3, "Complete Sentence Cadence", "sentences", "Punctuation rhythms, sentence capitalization, and natural phrase timing.", "Consistent practice builds velocity. Never compromise accuracy for speed.", 52.0, 95.0, 2),
    ('intermediate', 4, "Top Number Row Reaches", "numbers", "Reach the top number row with correct finger stretches without looking.", "Invoice 8402 total 195 dollars on 2026-09-15 tracking number 7391054", 42.0, 92.0, 2),

    # 3. ADVANCED TRACK (70 - 100 WPM)
    ('advanced', 1, "Complex Symbols & Brackets", "symbols", "Master hyphens, parentheses, semicolons, quotes, and code brackets.", "function(arg) { return [x, y]; } value = 'true'; (check == 100)", 60.0, 95.0, 2),
    ('advanced', 2, "High-Speed N-Gram Sprints", "ngrams", "Rapid bursts of frequent bigrams and trigrams (the, ing, tion, ment).", "the and for that with this from have they which would there their about", 72.0, 95.0, 2),
    ('advanced', 3, "Zero-Error Precision Gauntlet", "precision", "Eliminate stutter pauses with strict 98% accuracy thresholds.", "Deliberate movement precedes true velocity. Calm hands strike cleanly.", 78.0, 98.0, 3),

    # 4. EXPERT TRACK (100+ WPM)
    ('expert', 1, "Professional Workplace Execution", "professional", "Simulated office memos, executive briefings, and technical reports.", "Please review the quarterly engineering deployment roadmap attached.", 95.0, 96.0, 3),
    ('expert', 2, "Grandmaster Endurance Sprint", "grandmaster", "Sustained high-velocity paragraphs demanding flawless cognitive stamina.", "Synchronized kinetic movement compounds into unstoppable tactile velocity under intense pressure.", 105.0, 97.0, 3)
]

@learn_bp.route('/')
def index():
    # Auto-seed multi-track stages if empty
    if LessonStage.query.count() == 0:
        for track, num, title, slug, desc, practice, min_w, min_a, req_att in CURRICULUM_TRACKS:
            stage = LessonStage(
                track=track,
                stage_number=num,
                title=title,
                slug=slug,
                description=desc,
                practice_material=practice,
                min_wpm_to_pass=min_w,
                min_accuracy_to_pass=min_a,
                required_attempts=req_att
            )
            db.session.add(stage)
        db.session.commit()

    active_track = request.args.get('track', 'beginner').lower()
    stages = LessonStage.query.filter_by(track=active_track).order_by(LessonStage.stage_number.asc()).all()
    
    user_progress_map = {}
    if current_user.is_authenticated:
        records = UserLessonProgress.query.filter_by(user_id=current_user.id).all()
        user_progress_map = {r.stage_id: r for r in records}

    return render_template(
        'learn/index.html',
        stages=stages,
        active_track=active_track,
        progress_map=user_progress_map
    )

@learn_bp.route('/stage/<slug>')
def lesson(slug):
    stage = LessonStage.query.filter_by(slug=slug).first_or_404()
    return render_template('learn/lesson.html', stage=stage)

@learn_bp.route('/assessment')
def skill_assessment():
    return render_template('learn/assessment.html')

@learn_bp.route('/api/complete-stage', methods=['POST'])
@login_required
def complete_stage():
    data = request.get_json(force=True) or {}
    stage_id = int(data.get('stage_id', 1))
    wpm = float(data.get('wpm', 0.0))
    accuracy = float(data.get('accuracy', 0.0))

    stage = LessonStage.query.get_or_404(stage_id)
    passed_attempt = (wpm >= stage.min_wpm_to_pass and accuracy >= stage.min_accuracy_to_pass)

    progress = UserLessonProgress.query.filter_by(user_id=current_user.id, stage_id=stage.id).first()
    if not progress:
        progress = UserLessonProgress(user_id=current_user.id, stage_id=stage.id)
        db.session.add(progress)

    progress.total_attempts += 1
    if passed_attempt:
        progress.successful_attempts += 1
    
    if wpm > progress.best_wpm: progress.best_wpm = wpm
    if accuracy > progress.best_accuracy: progress.best_accuracy = accuracy
    
    # Require multiple successful attempts to prevent lucky one-offs
    if progress.successful_attempts >= (stage.required_attempts or 2):
        progress.completed = True

    db.session.commit()
    return jsonify({
        'success': True,
        'passed_attempt': passed_attempt,
        'stage_completed': progress.completed,
        'successful_attempts': progress.successful_attempts,
        'required_attempts': stage.required_attempts or 2
    })