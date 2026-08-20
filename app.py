import os
import json
import re
import io
import logging
from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai

# Try importing pypdf, fallback to PyPDF2
try:
    from pypdf import PdfReader
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False

try:
    from PyPDF2 import PdfReader as PyPDF2Reader
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

# --- Configuration ---
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY environment variable not set.")

genai.configure(api_key=api_key)

BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(title="ATS Resume Scanner")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# --- Helper Functions ---
def extract_text_from_pdf(pdf_file_bytes) -> str:
    """Extracts all text from an uploaded PDF file bytes."""
    pdf_file_obj = io.BytesIO(pdf_file_bytes)
    reader = None
    
    if PYPDF_AVAILABLE:
        try:
            reader = PdfReader(pdf_file_obj)
        except Exception:
            pass
            
    if reader is None and PYPDF2_AVAILABLE:
        pdf_file_obj.seek(0)
        try:
            reader = PyPDF2Reader(pdf_file_obj)
        except Exception:
            pass
            
    if reader is None:
        raise ValueError("Could not read PDF. Ensure it is a valid PDF.")

    text_parts = []
    for page in reader.pages:
        try:
            page_text = page.extract_text() or ""
            if page_text.strip():
                text_parts.append(page_text)
        except Exception:
            continue
            
    raw_text = "\n".join(text_parts).strip()
    
    # Basic cleanup for PDF extraction artifacts (removes excess tabs/spaces that break words)
    raw_text = re.sub(r'[ \t]+', ' ', raw_text)
    return raw_text

def clean_llm_response(raw_text):
    """Cleans and extracts the JSON object from the LLM's raw response, handling markdown."""
    if not raw_text:
        return None
        
    # Remove markdown formatting if present
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
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
        # Attempt to fix common JSON issues like trailing commas
        json_str = re.sub(r',\s*([\]}])', r'\1', json_str)
        try:
            json.loads(json_str)
            return json_str
        except Exception:
            return None

def normalize_response(data):
    """Ensure all expected keys exist to prevent UI errors."""
    details = data.get("details", {}) or {}
    contact = details.get("contact_info", {}) or {}
    sections = details.get("sections_analysis", {}) or {}
    
    normalized = {
        "details": {
            "inferred_job_title": details.get("inferred_job_title") or "General Professional",
            "contact_info": {
                "email": contact.get("email"),
                "phone": contact.get("phone"),
                "linkedin": contact.get("linkedin"),
                "github": contact.get("github"),
            },
            "sections_analysis": {
                "Contact": bool(sections.get("Contact", False)),
                "Summary": bool(sections.get("Summary", False)),
                "Experience": bool(sections.get("Experience", False)),
                "Education": bool(sections.get("Education", False)),
                "Skills": bool(sections.get("Skills", False)),
                "Projects": bool(sections.get("Projects", False)),
                "Certifications": bool(sections.get("Certifications", False)),
            },
            "spelling_mistakes": details.get("spelling_mistakes") or [],
            "repetition_words": details.get("repetition_words") or [],
            "missing_keywords": details.get("missing_keywords") or [],
            "ats_unfriendly_elements": details.get("ats_unfriendly_elements") or [],
            "quantify_impact_suggestions": details.get("quantify_impact_suggestions") or [],
            "action_verb_suggestions": details.get("action_verb_suggestions") or [],
            "overall_summary": details.get("overall_summary") or "Analysis complete.",
        }
    }
    return normalized

def calculate_metrics(details, has_job_desc):
    """Calculates all resume scores based on the detailed analysis from the AI."""
    sections = details.get("sections_analysis", {}) or {}
    missing_keywords = details.get("missing_keywords", []) or []
    spelling_mistakes = details.get("spelling_mistakes", []) or []
    repetition_words = details.get("repetition_words", []) or []
    ats_unfriendly_elements = details.get("ats_unfriendly_elements", []) or []
    quantify_impact_suggestions = details.get("quantify_impact_suggestions", []) or []

    section_score = sum(1 for v in sections.values() if v)
    section_completeness = round((section_score / max(len(sections), 1)) * 100)
    
    tailoring = max(0, 100 - min(len(missing_keywords) * 10, 70))
    spelling_grammar = max(0, 100 - min(len(spelling_mistakes) * 10, 60))
    repetition = max(0, 100 - min(len(repetition_words) * 10, 60))
    ats_essentials = max(0, 100 - min(len(ats_unfriendly_elements) * 15, 75))
    quantify_impact = max(0, 100 - min(len(quantify_impact_suggestions) * 15, 75))
    
    # Parse rate defaults to 100, but drops if there are severe ATS issues
    parse_rate = max(50, 100 - min(len(ats_unfriendly_elements) * 10, 50))

    if has_job_desc:
        tailoring = min(100, tailoring + 10)

    score = round(
        (
            tailoring * 0.25
            + quantify_impact * 0.15
            + ats_essentials * 0.2
            + section_completeness * 0.15
            + spelling_grammar * 0.15
            + repetition * 0.1
        )
    )
    
    return {
        "score": min(100, max(0, score)),
        "metrics": {
            "tailoring": tailoring,
            "quantify_impact": quantify_impact,
            "ats_essentials": ats_essentials,
            "section_completeness": section_completeness,
            "spelling_grammar": spelling_grammar,
            "repetition": repetition,
            "ats_parse_rate": parse_rate
        }
    }

def generate_total_issues(details):
    """Calculates the total number of improvement points found."""
    total = 0
    total += len(details.get("missing_keywords", []) or [])
    total += len(details.get("spelling_mistakes", []) or [])
    total += len(details.get("repetition_words", []) or [])
    total += len(details.get("ats_unfriendly_elements", []) or [])
    total += len(details.get("quantify_impact_suggestions", []) or [])
    total += len(details.get("action_verb_suggestions", []) or [])
    return total

# --- Main FastAPI Views ---
@app.get("/")
async def home():
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
Your task is to conduct a thorough, balanced, and practical analysis of the provided resume text and, if available, a job description.
Your response MUST be a single, valid JSON object and nothing else. Do not include any text before or after the JSON object. Do not use markdown formatting like ```json.

**JSON Structure:**
{
  "details": {
    "inferred_job_title": "string",
    "contact_info": {
        "email": "string or null",
        "phone": "string or null",
        "linkedin": "string or null",
        "github": "string or null"
    },
    "sections_analysis": {
      "Contact": true/false,
      "Summary": true/false,
      "Experience": true/false,
      "Education": true/false,
      "Skills": true/false,
      "Projects": true/false,
      "Certifications": true/false
    },
    "spelling_mistakes": [{"wrong": "string", "correct": "string"}],
    "repetition_words": ["string"],
    "missing_keywords": ["string"],
    "ats_unfriendly_elements": ["string"],
    "quantify_impact_suggestions": ["string"],
    "action_verb_suggestions": ["string"],
    "overall_summary": "string"
  }
}

**Analysis Instructions & Rules (STRICTLY FOLLOW):**
1. **Strict JSON**: Adhere strictly to the JSON structure. You MUST return ALL keys, even if their value is an empty list `[]`, an empty object `{}`, a `null` value, or `false`.
2. **Balanced & Practical Screening**: Do NOT be overly pedantic or hallucinate errors. 
   - **PDF Artifacts**: PDF extraction often splits words with spaces (e.g., "Develope r", "owner ship", "full -stack"). DO NOT flag these as spelling mistakes. If you see these, either ignore them or flag them gently under `ats_unfriendly_elements` as "PDF parsing artifacts detected".
   - **Spelling**: Only flag actual, undeniable spelling errors. 
3. **Contact Info**: Scrutinize the text for contact details. If a specific detail is not found, its value should be `null`.
4. **Section Analysis**: Check for the presence of standard sections. Set `true` if present, `false` otherwise.
5. **Job Description Context**:
   - If provided: Use it to find top 5-7 important `missing_keywords`. Set `inferred_job_title` from the description.
   - If NOT provided: Infer the most likely job title. Suggest 5-7 crucial `missing_keywords` for that inferred role.
6. **Repetition Words**: List non-common action verbs or technical terms used excessively (3 or more times).
7. **ATS Unfriendly Elements**: Point out actual bad practices (tables, images, missing standard headings). Do not penalize for normal text formatting.
8. **Suggestions**: All feedback in `quantify_impact_suggestions` and `action_verb_suggestions` must be specific, actionable, and encouraging. Provide examples.
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
        resume_text = extract_text_from_pdf(contents)
        
        if not resume_text or len(resume_text) < 50:
            return templates.TemplateResponse(
                request=request, name="ats_resume_scan.html",
                context={"request": request, "title": "ATS Resume Scanner", "error": "Could not extract text. Ensure it's a text-based PDF, not an image."}
            )

        # Use a stable, high-quality model with temperature 0 for consistency
        model = genai.GenerativeModel("gemini-3.6-flash", generation_config={"temperature": 0.0}) 
        
        input_prompt = [resume_analysis_prompt, f"RESUME TEXT:\n{resume_text}"]
        if job_desc:
            input_prompt.append(f"JOB DESCRIPTION:\n{job_desc}")
            
        response = model.generate_content(input_prompt)
        raw_response = response.text
        
        cleaned_json_str = clean_llm_response(raw_response)
        if not cleaned_json_str:
            raise ValueError("AI model did not return a valid JSON object.")
            
        data = json.loads(cleaned_json_str)
        normalized_data = normalize_response(data)
        details = normalized_data["details"]
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
        logger.exception("Error during ATS analysis")
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
