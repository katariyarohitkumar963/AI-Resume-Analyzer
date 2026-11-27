
import os
import re
from io import BytesIO

from flask import Flask, render_template, request
from werkzeug.utils import secure_filename
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit
from flask import send_file
from pypdf import PdfReader
from docx import Document


app = Flask(__name__)

# Maximum upload size: 10 MB
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

ALLOWED_EXTENSIONS = {"pdf", "docx"}


# Skills list
SKILLS_LIST = [
    "python",
    "java",
    "c",
    "c++",
    "javascript",
    "html",
    "css",
    "sql",
    "flask",
    "django",
    "react",
    "node.js",
    "machine learning",
    "data analysis",
    "excel",
    "communication",
    "teamwork",
    "problem solving",
    "git",
    "github",
    "linux",
    "php",
    "mongodb",
    "mysql",
    "artificial intelligence"
]


# Check file extension
def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


# Extract text from PDF or DOCX
def extract_resume_text(file, extension):

    file_bytes = file.read()

    if not file_bytes:
        raise ValueError("The uploaded file is empty.")

    if extension == "pdf":

        pdf = PdfReader(BytesIO(file_bytes))

        if pdf.is_encrypted:
            raise ValueError("Password-protected PDF files are not supported.")

        text = ""

        for page in pdf.pages:
            text += (page.extract_text() or "") + "\n"

        return text.strip()

    elif extension == "docx":

        document = Document(BytesIO(file_bytes))

        text = []

        for paragraph in document.paragraphs:
            text.append(paragraph.text)

        # Also read text from tables
        for table in document.tables:
            for row in table.rows:
                for cell in row.cells:
                    text.append(cell.text)

        return "\n".join(text).strip()

    raise ValueError("Unsupported file format.")


# Find skills in resume
def find_skills(text):

    text_lower = text.lower()
    found_skills = []

    for skill in SKILLS_LIST:

        pattern = r"(?<!\w)" + re.escape(skill) + r"(?!\w)"

        if re.search(pattern, text_lower):
            found_skills.append(skill)

    return found_skills


# Find email address
def find_email(text):

    pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"

    match = re.search(pattern, text)

    if match:
        return match.group(0)

    return "Not found"


# Find phone number
def find_phone(text):

    pattern = r"(?<!\d)(?:\+?\d{1,3}[-.\s]?)?\d{10}(?!\d)"

    match = re.search(pattern, text)

    if match:
        return match.group(0)

    return "Not found"


# Find candidate name (basic first-line check)
def find_name(text):

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    if not lines:
        return "Not found"

    first_line = lines[0]

    if len(first_line) <= 60 and not re.search(
        r"resume|curriculum vitae|cv",
        first_line,
        re.IGNORECASE
    ):
        return first_line

    return "Not found"


# Check important resume sections
def check_sections(text):

    text_lower = text.lower()

    sections = {
        "Education": ["education", "qualification", "academic"],
        "Experience": ["experience", "work experience", "employment"],
        "Skills": ["skills", "technical skills"],
        "Projects": ["projects", "project"],
        "Certifications": ["certifications", "certificates"]
    }

    missing_sections = []

    for section, keywords in sections.items():

        found = any(
            keyword in text_lower
            for keyword in keywords
        )

        if not found:
            missing_sections.append(section)

    return missing_sections


# Calculate resume score
def calculate_score(text, skills, missing_sections):

    score = 0

    # Resume content
    if len(text) > 300:
        score += 20
    elif len(text) > 100:
        score += 10

    # Skills
    score += min(len(skills) * 5, 30)

    # Important sections
    score += (5 - len(missing_sections)) * 10

    # Email
    if find_email(text) != "Not found":
        score += 10

    # Phone
    if find_phone(text) != "Not found":
        score += 10

    return min(score, 100)


# Generate improvement suggestions
def generate_suggestions(skills, missing_sections):

    suggestions = []

    if not skills:
        suggestions.append(
            "Add relevant technical and professional skills."
        )

    if missing_sections:
        suggestions.append(
            "Consider adding these sections: "
            + ", ".join(missing_sections)
        )

    if not suggestions:
        suggestions.append(
            "Your resume contains the main sections. "
            "Keep your information clear and updated."
        )

    suggestions.append(
        "Use clear headings and simple formatting."
    )

    suggestions.append(
        "Add relevant projects and achievements wherever possible."
    )

    return suggestions


# Home page
@app.route("/")
def home():

    return render_template("index.html")


# Resume analysis page
@app.route("/analyze", methods=["POST"])
def analyze():

    if "resume" not in request.files:
        return "No file was uploaded. Please go back and select a resume."

    file = request.files["resume"]

    if file.filename == "":
        return "Please select a resume file."

    if not allowed_file(file.filename):
        return "Invalid file format. Please upload a PDF or DOCX file."

    filename = secure_filename(file.filename)
    extension = filename.rsplit(".", 1)[1].lower()

    try:

        # Extract resume text
        extracted_text = extract_resume_text(file, extension)

        if not extracted_text:
            return (
                "No readable text found in the resume. "
                "Please upload a text-based PDF or DOCX file."
            )

        # Analyze resume
        skills = find_skills(extracted_text)

        candidate_name = find_name(extracted_text)
        email = find_email(extracted_text)
        phone = find_phone(extracted_text)

        missing_sections = check_sections(extracted_text)

        score = calculate_score(
            extracted_text,
            skills,
            missing_sections
        )

        suggestions = generate_suggestions(
            skills,
            missing_sections
        )

        # Show result page
        return render_template(
            "result.html",
            filename=filename,
            candidate_name=candidate_name,
            email=email,
            phone=phone,
            score=score,
            skills=skills,
            missing_sections=missing_sections,
            suggestions=suggestions,
            extracted_text=extracted_text
        )

    except Exception as error:

        app.logger.exception("Resume analysis failed")

        return (
            "Unable to analyze this file. "
            "Please check the file and try again."
        ), 400


# Handle files larger than 10 MB
@app.errorhandler(413)
def file_too_large(error):

    return "File is too large. Please upload a file under 10 MB.", 413
@app.route("/download-report", methods=["POST"])
def download_report():

    filename = request.form.get("filename", "Resume")
    candidate_name = request.form.get("candidate_name", "Not found")
    email = request.form.get("email", "Not found")
    phone = request.form.get("phone", "Not found")
    score = request.form.get("score", "0")
    skills = request.form.getlist("skills")
    missing_sections = request.form.getlist("missing_sections")
    suggestions = request.form.getlist("suggestions")

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)

    width, height = A4
    y = height - 50

    def add_line(text):
        nonlocal y

        lines = simpleSplit(str(text), "Helvetica", 10, width - 100)

        for line in lines:
            if y < 50:
                pdf.showPage()
                y = height - 50

            pdf.drawString(50, y, line)
            y -= 18

    pdf.setTitle("Resume Analysis Report")

    pdf.setFont("Helvetica-Bold", 18)
    add_line("AI RESUME ANALYSIS REPORT")

    pdf.setFont("Helvetica", 10)
    add_line("Resume: " + filename)
    add_line("Candidate: " + candidate_name)
    add_line("Email: " + email)
    add_line("Phone: " + phone)
    add_line("Resume Score: " + str(score) + "/100")

    add_line("")
    add_line("SKILLS FOUND")

    for skill in skills:
        add_line("- " + skill)

    add_line("")
    add_line("MISSING SECTIONS")

    for section in missing_sections:
        add_line("- " + section)

    add_line("")
    add_line("SUGGESTIONS")

    for suggestion in suggestions:
        add_line("- " + suggestion)

    pdf.save()
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="Resume_Analysis_Report.pdf",
        mimetype="application/pdf"
    )

# Run Flask application
if __name__ == "__main__":

    app.run(debug=True)