from datetime import datetime
from email.policy import default

from ..extensions import db
from .base import BaseModel
from ..models.site_setings import SiteSettings
class Page(BaseModel):
    __tablename__ = 'pages'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), nullable=False, unique=True)
    home_page = db.Column(db.Boolean, default=False)
    meta_title = db.Column(db.String(255))
    meta_keywords = db.Column(db.String(255))
    meta_description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    


    def __repr__(self):
        return f"<Page {self.title} ({self.slug})>"

def getHomePage():
    page_id = SiteSettings.home_page_id
    pages = Page.query.filter_by(id=page_id).first()
    return pages


class PageLayout(BaseModel):
    __tablename__ = 'page_layout'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    page_id = db.Column(db.Integer, db.ForeignKey('pages.id'), nullable=False)
    row_index = db.Column(db.Integer, nullable=False, default=0)  # Номер строки (0, 1, 2...)
    col_index = db.Column(db.Integer, nullable=False, default=0)  # Номер столбца (0..3, если до 4 столбцов)

    col_width = db.Column(db.Integer, nullable=False, default=3)  # Ширина столбца по Bootstrap-сетке (1..12)

    module_instance_id = db.Column(db.Integer, db.ForeignKey('module_instances.id'))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Связи
    page = db.relationship('Page', backref='layout')
    module_instance = db.relationship('ModuleInstance', backref='page_cells', lazy=True)

    def __repr__(self):
        return (f"<PageLayout page={self.page_id} row={self.row_index} col={self.col_index} "
                f"width={self.col_width} module={self.module_instance_id}>")

def getPageLayout(page_id):
    layouts = PageLayout.query.filter_by(page_id=page_id).all()
    return layouts