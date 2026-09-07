from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.models.curriculum import LessonStage, UserLessonProgress

learn_bp = Blueprint('learn', __name__)

DEFAULT_CURRICULUM = [
    (1, "Keyboard Introduction & Posture", "intro", "Learn home row resting position, spinal ergonomics, and finger coordination.", "f j f j f j dk dk sl sl a; a; fj dk sl a;"),
    (2, "Home Row Mastery", "home-row", "Anchor muscle memory exclusively on the baseline index-to-pinky keys.", "asdf jkl; a fad flask fall glad half dash salad flash salsa lad fall"),
    (3, "Top Row Extensions", "top-row", "Train upward vertical reaches without shifting wrists off the desk.", "quit write power tower quote trip your wipe wire pure quiet root weep"),
    (4, "Bottom Row Transitions", "bottom-row", "Practice downward finger tucks while maintaining palm stability.", "cabin van mix zoom bomb zinc exam calm civic move bank comb mimic"),
    (5, "Key Combinations & Shifts", "shifts", "Synchronize contralateral shift-key holds for capital letters.", "The Quick Brown Fox Jumps Over The Lazy Dog London Paris Tokyo"),
    (6, "Common Core Words", "common-words", "Fluency on the top 100 most frequent English building blocks.", "their there would about which could people other first water after"),
    (7, "Complete Sentences", "sentences", "Punctuation rhythms, sentence capitalization, and natural phrase timing.", "Consistent practice builds velocity. Never compromise accuracy for speed."),
    (8, "Numeric Row Reaches", "numbers", "Reach the top number row with correct finger stretches.", "Invoice 8402 total 195 dollars on 2026-09-15 tracking number 7391054"),
    (9, "Complex Punctuation & Symbols", "punctuation", "Hyphens, parentheses, semicolons, quotes, and brackets.", "function(arg) { return [x, y]; } value = 'true'; (check == 100)"),
    (10, "Speed Building Sprints", "speed-building", "Rapid short bursts of frequent bigrams and trigrams.", "the and for that with this from have they which would there their about"),
    (11, "Accuracy Calibration", "accuracy-training", "Zero-error precision drills designed to eliminate stutter pauses.", "Deliberate movement precedes true velocity. Calm hands strike cleanly."),
    (12, "Professional & Workplace Typing", "professional", "Simulated office memos, email correspondence, and technical reports.", "Please review the quarterly engineering deployment roadmap attached.")
]

@learn_bp.route('/')
def index():
    # Seed curriculum if empty
    if LessonStage.query.count() == 0:
        for num, title, slug, desc, practice in DEFAULT_CURRICULUM:
            stage = LessonStage(
                stage_number=num,
                title=title,
                slug=slug,
                description=desc,
                practice_material=practice,
                min_wpm_to_pass=15.0 + (num * 2.0),
                min_accuracy_to_pass=92.0
            )
            db.session.add(stage)
        db.session.commit()

    stages = LessonStage.query.order_by(LessonStage.stage_number.asc()).all()
    user_progress_map = {}
    
    if current_user.is_authenticated:
        records = UserLessonProgress.query.filter_by(user_id=current_user.id).all()
        user_progress_map = {r.stage_id: r for r in records}

    return render_template(
        'learn/index.html',
        stages=stages,
        progress_map=user_progress_map
    )

@learn_bp.route('/stage/<int:stage_number>')
def lesson(stage_number):
    stage = LessonStage.query.filter_by(stage_number=stage_number).first_or_404()
    return render_template('learn/lesson.html', stage=stage)

@learn_bp.route('/api/complete-stage', methods=['POST'])
@login_required
def complete_stage():
    data = request.get_json(force=True) or {}
    stage_id = int(data.get('stage_id', 1))
    wpm = float(data.get('wpm', 0.0))
    accuracy = float(data.get('accuracy', 0.0))

    stage = LessonStage.query.get_or_404(stage_id)
    passed = (wpm >= stage.min_wpm_to_pass and accuracy >= stage.min_accuracy_to_pass)

    progress = UserLessonProgress.query.filter_by(user_id=current_user.id, stage_id=stage.id).first()
    if not progress:
        progress = UserLessonProgress(user_id=current_user.id, stage_id=stage.id)
        db.session.add(progress)

    progress.attempts += 1
    if wpm > progress.best_wpm: progress.best_wpm = wpm
    if accuracy > progress.best_accuracy: progress.best_accuracy = accuracy
    if passed: progress.completed = True

    db.session.commit()
    return jsonify({'success': True, 'passed': passed})