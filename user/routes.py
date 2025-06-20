from flask import Blueprint, render_template, request
from admin.models import StudyMaterial
from .forms import SearchForm  # Import the search form


user_bp = Blueprint('user', __name__)

@user_bp.route('/portal', methods=['GET', 'POST'])
def user_portal():
    form = SearchForm()  # Create an instance of the SearchForm
    # Fetch distinct values for courses, semesters, and subjects for the dropdowns
    courses = StudyMaterial.query.with_entities(StudyMaterial.course).distinct().all()
    semesters = StudyMaterial.query.with_entities(StudyMaterial.semester).distinct().all()
    subjects = StudyMaterial.query.with_entities(StudyMaterial.subject).distinct().all()

    # Handle the search/filter request
    selected_course = request.form.get('course')
    selected_semester = request.form.get('semester')
    selected_subject = request.form.get('subject')

    # Filter materials based on the selected values
    materials = StudyMaterial.query
    if selected_course:
        materials = materials.filter_by(course=selected_course)
    if selected_semester:
        materials = materials.filter_by(semester=selected_semester)
    if selected_subject:
        materials = materials.filter_by(subject=selected_subject)

    materials = materials.all()
    
    return render_template('user_portal.html', materials=materials, courses=courses, semesters=semesters, subjects=subjects, form=form)

@user_bp.route('/material/<int:material_id>')
def material_detail(material_id):
    material = StudyMaterial.query.get_or_404(material_id)
    print("Material:", material.title, "YouTube Link:", material.youtube_link)  # Debug line
    return render_template('material_detail.html', material=material)

