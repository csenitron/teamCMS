from datetime import datetime
from ..extensions import db


class ReviewVote(db.Model):
    __tablename__ = 'review_votes'

    id = db.Column(db.Integer, primary_key=True)
    review_id = db.Column(db.Integer, db.ForeignKey('reviews.id', ondelete='CASCADE'), nullable=False)
    voter_key = db.Column(db.String(255), nullable=False)  # customer email или IP для гостя
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('review_id', 'voter_key', name='uq_review_votes_review_voter'),
    )


