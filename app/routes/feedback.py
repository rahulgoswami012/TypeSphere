from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from app import db
from app.models.feedback import ContactMessage, FeedbackItem, RatingReview

feedback_bp = Blueprint('feedback', __name__)

@feedback_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        subject = request.form.get('subject', '').strip()
        message = request.form.get('message', '').strip()

        if not name or not email or not message:
            flash('Please complete all required fields.', 'danger')
            return redirect(url_for('feedback.contact'))

        # Anti-spam check: prevent duplicate submissions within 2 minutes from same email
        recent_msg = ContactMessage.query.filter_by(email=email).order_by(ContactMessage.id.desc()).first()
        if recent_msg and (datetime.utcnow() - recent_msg.created_at) < timedelta(minutes=2):
            flash('Message already received. Please wait before submitting another inquiry.', 'warning')
            return redirect(url_for('feedback.contact'))

        msg_record = ContactMessage(name=name, email=email, subject=subject, message=message)
        db.session.add(msg_record)
        db.session.commit()

        flash('Your message has been received! Our team will respond shortly.', 'success')
        return redirect(url_for('feedback.contact'))

    return render_template('feedback/contact.html')

@feedback_bp.route('/submit', methods=['GET', 'POST'])
def submit_feedback():
    if request.method == 'POST':
        if not current_user.is_authenticated:
            flash('You must be signed in to submit platform feedback.', 'warning')
            return redirect(url_for('auth.login', next=url_for('feedback.submit_feedback')))

        category = request.form.get('category', 'General')
        title = request.form.get('title', '').strip()
        message = request.form.get('message', '').strip()

        if not title or not message:
            flash('Please provide both a title and message description.', 'danger')
            return redirect(url_for('feedback.submit_feedback'))

        fb = FeedbackItem(user_id=current_user.id, category=category, title=title, message=message)
        db.session.add(fb)
        db.session.commit()

        flash('Thank you! Your feedback has been recorded for our engineering team.', 'success')
        return redirect(url_for('feedback.submit_feedback'))

    user_submissions = []
    if current_user.is_authenticated:
        user_submissions = FeedbackItem.query.filter_by(user_id=current_user.id).order_by(FeedbackItem.id.desc()).all()

    return render_template('feedback/feedback.html', user_submissions=user_submissions)

@feedback_bp.route('/ratings', methods=['GET', 'POST'])
def ratings():
    if request.method == 'POST':
        if not current_user.is_authenticated:
            flash('You must be signed in to leave a platform rating & review.', 'warning')
            return redirect(url_for('auth.login', next=url_for('feedback.ratings')))

        try:
            rating_val = int(request.form.get('rating', 5))
            rating_val = max(1, min(5, rating_val))
        except (ValueError, TypeError):
            rating_val = 5

        title = request.form.get('review_title', '').strip()
        text_content = request.form.get('review_text', '').strip()

        if not title or not text_content:
            flash('Please provide a title and review explanation.', 'danger')
            return redirect(url_for('feedback.ratings'))

        # Check existing review to allow update rather than spamming
        existing_review = RatingReview.query.filter_by(user_id=current_user.id).first()
        if existing_review:
            existing_review.rating = rating_val
            existing_review.review_title = title
            existing_review.review_text = text_content
            existing_review.updated_at = datetime.utcnow()
            flash('Your review has been updated successfully!', 'success')
        else:
            new_rev = RatingReview(
                user_id=current_user.id,
                rating=rating_val,
                review_title=title,
                review_text=text_content
            )
            db.session.add(new_rev)
            flash('Thank you for your rating and review!', 'success')

        db.session.commit()
        return redirect(url_for('feedback.ratings'))

    # Load approved reviews
    all_reviews = RatingReview.query.filter_by(is_approved=True).order_by(RatingReview.id.desc()).limit(30).all()
    avg_rating = 0.0
    if all_reviews:
        avg_rating = round(sum(r.rating for r in all_reviews) / len(all_reviews), 1)

    user_review = None
    if current_user.is_authenticated:
        user_review = RatingReview.query.filter_by(user_id=current_user.id).first()

    return render_template(
        'feedback/ratings.html',
        reviews=all_reviews,
        avg_rating=avg_rating,
        total_reviews=len(all_reviews),
        user_review=user_review
    )