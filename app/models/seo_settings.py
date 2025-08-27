from ..extensions import db
from .base import BaseModel

class SEOSettings(BaseModel):
    __tablename__ = 'seo_settings'

    page_type = db.Column(db.String(50), nullable=False)
    page_id = db.Column(db.Integer, nullable=False)
    meta_title = db.Column(db.String(255))
    meta_description = db.Column(db.Text)
    meta_keywords = db.Column(db.String(255))
    slug = db.Column(db.String(255), unique=True)

    def __init__(self, page_type, page_id, meta_title=None, meta_description=None, meta_keywords=None, slug=None):
        self.page_type = page_type
        self.page_id = page_id
        self.meta_title = meta_title
        self.meta_description = meta_description
        self.meta_keywords = meta_keywords
        self.slug = slug

def getSEO(page_type, id):
    seo = SEOSettings.query.filter_by(page_type=page_type, page_id=id).first()
    return seo