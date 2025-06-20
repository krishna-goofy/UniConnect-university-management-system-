from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
import os
from .forms import MaterialForm
from .models import StudyMaterial
from db import db

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/portal', methods=['GET', 'POST'])
def admin_portal():
    form = MaterialForm()
    if form.validate_on_submit():
        material_name = form.title.data
        material_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], material_name)
        if not os.path.exists(material_folder):
            os.makedirs(material_folder)

        if form.files.data:
            for file in form.files.data:
                if file:
                    file_path = os.path.join(material_folder, file.filename)
                    file.save(file_path)

        youtube_links = [link.youtube_link.data for link in form.youtube_links if link.youtube_link.data]

        # Convert list of material types to a string for saving in the database
        material_types_selected = '; '.join(form.material_type.data)

        new_material = StudyMaterial(
            title=form.title.data,
            course=form.course.data,
            subject=form.subject.data,
            semester=form.semester.data,
            material_type=material_types_selected,  # Save as a semicolon-separated string
            description=form.description.data,
            file_path='; '.join([file.filename for file in form.files.data if file]),
            youtube_link='; '.join(youtube_links)
        )

        db.session.add(new_material)
        db.session.commit()
        flash('Study Material uploaded successfully!', 'success')
        return redirect(url_for('admin.admin_portal'))

    return render_template('admin_portal.html', form=form)

