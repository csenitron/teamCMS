from flask import Blueprint, render_template
import datetime

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
def admin_index():
    return render_template('admin/index.html', datetime=datetime)
