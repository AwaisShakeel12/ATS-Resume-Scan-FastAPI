import os
import json
import re
import io
from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pathlib import Path
from PyPDF2 import PdfReader
import google.generativeai as genai
from dotenv import load_dotenv

# --- Configuration ---
load_dotenv()


from dotenv import load_dotenv

# ---------- Environment ----------
load_dotenv()


# Use environment variable for API key, fallback to the hardcoded key from your original script
api_key = os.getenv("GOOGLE_API_KEY", "your api key")
genai.configure(api_key=api_key)

BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(title="ATS Resume Scanner")





templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# --- Helper Functions ---
def extract_text_from_pdf(pdf_file):
    """Extracts all text from an uploaded PDF file."""
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted + "\n"
    return text.strip()

def clean_llm_response(raw_text):
    """Cleans and extracts the JSON object from the LLM's raw response, handling markdown."""
    match = re.search(r"```json\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
    if match:
        json_str = match.group(1)
    else:
        json_start = raw_text.find('{')
        json_end = raw_text.rfind('}') + 1
        if json_start != -1 and json_end != -1:
            json_str = raw_text[json_start:json_end]
        else:
            return None
    try:
        json.loads(json_str)
        return json_str
    except json.JSONDecodeError:
        return None

def calculate_metrics(details, has_job_desc):
    """Calculates all resume scores based on the detailed analysis from the AI."""
    spelling_errors = len(details.get("spelling_mistakes", []))
    spelling_score = max(0, 100 - (spelling_errors * 10))

    repetition_issues = len(details.get("repetition_words", []))
    repetition_score = max(0, 100 - (repetition_issues * 8))

    section_details = details.get("sections_analysis", {})
    present_sections = sum(1 for found in section_details.values() if found)
    total_possible_sections = len(section_details) if section_details else 7
    section_score = int((present_sections / total_possible_sections) * 100) if total_possible_sections > 0 else 100

    quantify_issues = len(details.get("quantify_impact_suggestions", []))
    quantify_score = max(20, 100 - (quantify_issues * 20))

    ats_issues = len(details.get("ats_unfriendly_elements", []))
    action_verb_issues = len(details.get("action_verb_suggestions", []))
    contact_info = details.get("contact_info", {})
    contact_issues = 0
    if not contact_info.get("email"): contact_issues += 1
    if not contact_info.get("phone"): contact_issues += 1
    ats_essentials_score = max(20, 100 - (ats_issues * 20) - (action_verb_issues * 5) - (contact_issues * 15))

    ats_parse_rate = max(50, 100 - (spelling_errors * 4) - (ats_issues * 10) - (contact_issues * 10))

    missing_kw = len(details.get("missing_keywords", []))
    penalty_per_keyword = 10 if has_job_desc else 7
    tailoring_score = max(20, 100 - (missing_kw * penalty_per_keyword))

    if has_job_desc:
        weights = {"spelling": 0.10, "repetition": 0.05, "section": 0.15, "quantify": 0.20, "ats": 0.15, "tailoring": 0.35}
    else:
        weights = {"spelling": 0.15, "repetition": 0.10, "section": 0.25, "quantify": 0.20, "ats": 0.20, "tailoring": 0.10}
        
    total_score = int(
        spelling_score * weights["spelling"] +
        repetition_score * weights["repetition"] +
        section_score * weights["section"] +
        quantify_score * weights["quantify"] +
        ats_essentials_score * weights["ats"] +
        tailoring_score * weights["tailoring"]
    )
    
    return {
        "score": min(100, max(0, total_score)),
        "metrics": {
            "ats_parse_rate": ats_parse_rate,
            "repetition": repetition_score,
            "spelling_grammar": spelling_score,
            "section_completeness": section_score,
            "ats_essentials": ats_essentials_score,
            "quantify_impact": quantify_score,
            "tailoring": tailoring_score
        }
    }

def generate_total_issues(details):
    """Calculates the total number of improvement points found."""
    section_details = details.get("sections_analysis", {})
    missing_section_count = sum(1 for found in section_details.values() if not found)
    return sum(
        len(details.get(key, [])) for key in [
            "spelling_mistakes", "repetition_words", "missing_keywords",
            "ats_unfriendly_elements", "quantify_impact_suggestions",
            "action_verb_suggestions"
        ]
    ) + missing_section_count

# --- Main FastAPI Views ---
@app.get("/")
async def home():
    # Redirect root URL directly to the ATS scanner
    return RedirectResponse(url="/ats-resume-scan/")

@app.get("/ats-resume-scan/")
async def ats_resume_scan_get(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="ats_resume_scan.html",
        context={"request": request, "title": "ATS Resume Scanner"}
    )

@app.post("/ats-resume-scan/")
async def ats_resume_scan_post(
    request: Request,
    resume: UploadFile = File(...),
    job_description: str = Form("")
):
    resume_analysis_prompt = """
You are a world-class, expert ATS (Applicant Tracking System) and professional resume analyzer.
Your task is to conduct a thorough analysis of the provided resume text and, if available, a job description.
Your response MUST be a single, valid JSON object and nothing else. Do not include any text before or after the JSON object. Do not use markdown formatting like ```json.
**JSON Structure:**
 {
   "details": {
     "inferred_job_title": "Senior Software Engineer",
     "contact_info": {
         "email": "example@email.com",
         "phone": "123-456-7890",
         "linkedin": "[linkedin.com/in/example](https://linkedin.com/in/example)",
         "github": "[github.com/example](https://github.com/example)"
     },
     "sections_analysis": {
       "Contact": true,
       "Summary": true,
       "Experience": true,
       "Education": true,
       "Skills": true,
       "Projects": false,
       "Certifications": false
     },
     "spelling_mistakes": [{"wrong": "experiance", "correct": "experience"}],
     "repetition_words": ["developed", "optimized"],
     "missing_keywords": ["Kubernetes", "CI/CD"],
     "ats_unfriendly_elements": ["Using tables or columns for layout.", "Photo included."],
     "quantify_impact_suggestions": ["'Increased application performance.' -> 'Quantify this. Example: Increased performance by 20%...'"],
     "action_verb_suggestions": ["'Was responsible for...' -> 'Use stronger verbs like: Developed, Engineered, Architected...'"],
     "overall_summary": "A solid resume but needs a projects section and more quantified results."
   }
 }
 **Analysis Instructions:**
 1.  **Strict JSON**: Adhere strictly to the JSON structure. You MUST return ALL keys, even if their value is an empty list `[]`, an empty object `{}`, a `null` value, or `false`.
 2.  **Contact Info**: Scrutinize the text for contact details. Find the email, phone number, and LinkedIn/GitHub URLs. If a specific detail is not found, its value should be `null`. Recognize these details even if they are part of a hyperlink.
 3.  **Section Analysis**: For `sections_analysis`, check for the presence of these standard sections: Contact, Summary, Experience, Education, Skills, Projects, Certifications. Set the value to `true` if present, `false` otherwise.
 4.  **Job Description Context**:
     * If a job description is provided: Use it to find the top 5-7 most important `missing_keywords`. Set `inferred_job_title` to the job title from the description.
     * If NO job description is provided: Infer the most likely job title for `inferred_job_title`. Then, suggest 5-7 crucial `missing_keywords` for that inferred role.
 5.  **Strictness & Detail**: Be extremely strict with spelling and grammar. For `repetition_words`, list non-common action verbs or technical terms used 3 or more times. All feedback in `quantify_impact_suggestions` and `action_verb_suggestions` must be specific and actionable.
 """
    job_desc = job_description.strip()
    raw_response = None
    
    if not resume:
        return templates.TemplateResponse(
            request=request, name="ats_resume_scan.html",
            context={"request": request, "title": "ATS Resume Scanner", "error": "Please upload a resume."}
        )

    if not resume.filename or not resume.filename.lower().endswith(".pdf"):
        return templates.TemplateResponse(
            request=request, name="ats_resume_scan.html",
            context={"request": request, "title": "ATS Resume Scanner", "error": "Only PDF files are allowed."}
        )

    try:
        contents = await resume.read()
        pdf_file_obj = io.BytesIO(contents)
        resume_text = extract_text_from_pdf(pdf_file_obj)
        
        if not resume_text or len(resume_text) < 50:
            return templates.TemplateResponse(
                request=request, name="ats_resume_scan.html",
                context={"request": request, "title": "ATS Resume Scanner", "error": "Could not extract text. Ensure it's a text-based PDF, not an image."}
            )

        # Updated to the latest stable flash model name
        model = genai.GenerativeModel("gemini-flash-latest") 
        
        input_prompt = [resume_analysis_prompt, f"RESUME TEXT:\n{resume_text}"]
        if job_desc:
            input_prompt.append(f"JOB DESCRIPTION:\n{job_desc}")
            
        response = model.generate_content(input_prompt)
        raw_response = response.text
        
        cleaned_json_str = clean_llm_response(raw_response)
        if not cleaned_json_str:
            raise ValueError("AI model did not return a valid JSON object.")
            
        data = json.loads(cleaned_json_str)
        details = data.get("details", {})
        has_job_desc_bool = bool(job_desc)
        
        metrics_data = calculate_metrics(details, has_job_desc_bool)
        
        return templates.TemplateResponse(
            request=request,
            name="ats_resume_scan.html",
            context={
                "request": request,
                "title": "ATS Resume Scanner",
                "score": metrics_data["score"],
                "review": details.get("overall_summary", "Analysis complete."),
                "total_issues": generate_total_issues(details),
                "metrics": metrics_data["metrics"],
                "details": details,
                "has_job_desc": has_job_desc_bool
            }
        )
    except Exception as e:
        return templates.TemplateResponse(
            request=request,
            name="ats_resume_scan.html",
            context={
                "request": request,
                "title": "ATS Resume Scanner",
                "error": f"An error occurred during analysis: {str(e)}",
                "raw_response": raw_response
            }
        )