# 📄 ATS Resume Scanner

> **AI-powered resume analysis tool built with FastAPI, Google Gemini, PDF text extraction, and Jinja2.**

The **ATS Resume Scanner** analyzes a candidate's PDF resume and generates an ATS-focused report. Users can optionally provide a job description to receive more targeted keyword and role-matching feedback.

The application extracts text from the uploaded resume, sends the resume content to a Gemini model for structured analysis, calculates ATS metrics, and displays the results through a web interface.

---

## ✨ Features

### 📊 ATS Resume Scoring

Generates an overall resume score from **0–100** based on multiple factors, including:

- ATS parsing
- Resume sections
- Spelling and grammar
- Repeated words
- Quantified achievements
- ATS-friendly formatting
- Keyword matching

### 🔑 Keyword Analysis

The scanner can:

- Identify missing keywords
- Compare the resume against a job description
- Suggest relevant keywords when no job description is provided

### 🧩 Resume Section Analysis

Checks whether the resume contains important sections such as:

- Contact
- Summary
- Experience
- Education
- Skills
- Projects
- Certifications

### ✍️ Writing & Content Feedback

The AI identifies:

- Spelling mistakes
- Repeated words
- Weak action verbs
- Achievements that should be quantified
- Content improvement opportunities

### ⚠️ ATS Formatting Checks

The scanner can identify potentially ATS-unfriendly elements such as:

- Tables
- Columns
- Photos
- Other formatting issues detected by the AI

### 🎯 Job Description Matching

Users can optionally paste a complete job description.

When a job description is provided, the scanner uses it to:

- Infer the target job title
- Identify important missing keywords
- Calculate a tailored keyword score
- Provide role-specific feedback

Without a job description, the application infers a likely job title from the resume and provides general ATS suggestions.

### 📄 PDF Resume Upload

The application accepts PDF resumes and extracts their text using `PyPDF2`.

Scanned/image-only PDFs may not work correctly because the current implementation relies on text extraction rather than OCR.

### 🛡️ Error Monitoring

The application includes Sentry integration for exception monitoring.

A development debug endpoint is also available at:

```text
/sentry-debug
```

---

# 🏗️ How It Works

The application follows this flow:

```text
                    ┌─────────────────────┐
                    │     User uploads    │
                    │       Resume PDF    │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   PDF Text Extract  │
                    │      PyPDF2         │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  Resume + Optional  │
                    │   Job Description   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    Gemini Model     │
                    │   AI Resume Analysis │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Structured JSON     │
                    │ Resume Analysis     │
                    └──────────┬──────────┘
                               │
                    ┌──────────┴──────────┐
                    ▼                     ▼
          ┌──────────────────┐   ┌──────────────────┐
          │ ATS Metrics      │   │ Improvement      │
          │ & Score          │   │ Recommendations  │
          └────────┬─────────┘   └────────┬─────────┘
                   │                      │
                   └──────────┬───────────┘
                              ▼
                    ┌─────────────────────┐
                    │   Jinja2 Web UI     │
                    │   Analysis Results   │
                    └─────────────────────┘
```

---

# 🧰 Tech Stack

| Technology | Purpose |
|---|---|
| **Python** | Application language |
| **FastAPI** | Web framework and API routing |
| **Google Gemini** | AI-powered resume analysis |
| **PyPDF2** | Extract text from PDF resumes |
| **Jinja2** | HTML template rendering |
| **Sentry SDK** | Error monitoring |
| **python-dotenv** | Environment variable management |
| **HTML / CSS / JS** | Frontend interface |

---

# 📁 Project Structure

A typical project structure looks like this:

```text
ats-resume-scanner/
│
├── app.py
├── requirements.txt
├── README.md
├── .env
├── .gitignore
│
├── templates/
│   └── ats_resume_scan.html
│
└── static/
    └── ...
```

### Main files

#### `app.py`

The main FastAPI application.

It handles:

- Resume uploads
- PDF text extraction
- Gemini requests
- JSON parsing
- ATS metric calculations
- Result generation
- Jinja template rendering
- Error handling

#### `requirements.txt`

Contains the Python packages required by the project.

Install them with:

```bash
pip install -r requirements.txt
```

#### `templates/ats_resume_scan.html`

The frontend template used to display the ATS scanner and analysis results.

---

# 🚀 Installation

## 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
```

Enter the project:

```bash
cd ats-resume-scanner
```

---

## 2. Create a virtual environment

### Windows

```bash
python -m venv venv
```

Activate it:

```bash
venv\Scripts\activate
```

### Linux / macOS

```bash
python3 -m venv venv
```

Activate it:

```bash
source venv/bin/activate
```

---

# 📦 3. Install Requirements

Install all dependencies from `requirements.txt`:

```bash
pip install -r requirements.txt
```

This is the recommended installation method because the project keeps its dependencies in the requirements file.

If you need to update the requirements after installing or changing packages:

```bash
pip freeze > requirements.txt
```

---

# 🔐 4. Configure Environment Variables

Create a `.env` file in the project root:

```text
GOOGLE_API_KEY=your_gemini_api_key
SENTRY_DSN=your_sentry_dsn
```

The application uses `python-dotenv` to load environment variables.

## Gemini API Key

The application uses the Gemini API to analyze resume content.

Set:

```text
GOOGLE_API_KEY=your_gemini_api_key
```

## Sentry

Sentry is optional for local development.

If you don't want Sentry monitoring, you can leave the DSN empty:

```text
SENTRY_DSN=
```

---

# ⚠️ API Key Security

Never commit a real API key to GitHub.

Your `.gitignore` should contain:

```text
.env
venv/
__pycache__/
*.pyc
```

The application should use:

```python
os.getenv("GOOGLE_API_KEY")
```

rather than storing production credentials directly inside source code.

---

# ▶️ 5. Run the Application

Start the FastAPI development server:

```bash
uvicorn app:app --reload
```

You should see something similar to:

```text
Uvicorn running on http://127.0.0.1:8000
```

Open:

```text
http://127.0.0.1:8000
```

The root route redirects to:

```text
/ats-resume-scan/
```

You can also open the scanner directly:

```text
http://127.0.0.1:8000/ats-resume-scan/
```

---

# 🔄 Application Routes

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/` | Redirects to ATS scanner |
| `GET` | `/ats-resume-scan/` | Displays scanner page |
| `POST` | `/ats-resume-scan/` | Uploads and analyzes resume |
| `GET` | `/sentry-debug` | Test Sentry exception reporting |

---

# 📄 Using the Scanner

## Step 1 — Upload Resume

Upload a resume in:

```text
PDF
```

format.

The application rejects non-PDF files.

---

## Step 2 — Add Job Description

The job description is optional.

### Without a job description

The AI:

1. Reads the resume
2. Infers the likely job title
3. Suggests important keywords
4. Performs general ATS analysis

### With a job description

The AI:

1. Reads the resume
2. Reads the job description
3. Identifies the target role
4. Finds important missing keywords
5. Calculates a tailored keyword score
6. Generates role-specific recommendations

For the best results, paste the complete job description.

---

# 📊 ATS Metrics

The application calculates several metrics from the AI analysis.

### ATS Parse Rate

Estimates how well the resume may be parsed based on detected issues.

### Repetition

Checks for repeated words and reduces the score when excessive repetition is detected.

### Spelling & Grammar

The score decreases when spelling mistakes are detected.

### Section Completeness

Checks the presence of standard resume sections.

### ATS Essentials

Considers ATS formatting issues, action verbs, and missing contact information.

### Quantify Impact

Checks whether achievements contain measurable results.

### Keyword Tailoring

Measures keyword alignment between the resume and job description.

When a job description is not provided, this metric is based on suggested keywords for the inferred role.

---

# 🧠 AI Analysis

The application asks Gemini to return a structured JSON object containing information such as:

```json
{
  "details": {
    "inferred_job_title": "Software Engineer",
    "contact_info": {},
    "sections_analysis": {},
    "spelling_mistakes": [],
    "repetition_words": [],
    "missing_keywords": [],
    "ats_unfriendly_elements": [],
    "quantify_impact_suggestions": [],
    "action_verb_suggestions": [],
    "overall_summary": "..."
  }
}
```

The application then parses this response and calculates the final ATS score.

---

# 🧮 Score Calculation

The final score is calculated from multiple categories.

When a job description is provided, keyword tailoring receives more weight because matching the target job becomes more important.

When no job description is provided, the score puts more emphasis on general resume quality and ATS readiness.

The final score is constrained to:

```text
0 - 100
```

---

# 🛑 Common Errors

## Only PDF files are allowed

If you upload another file type, the application returns:

```text
Only PDF files are allowed.
```

---

## PDF text cannot be extracted

If the PDF contains little or no extractable text, the application returns an error.

This commonly happens with scanned/image-based resumes.

The current application does **not** perform OCR.

For best results, use a text-based PDF.

---

## Gemini API Error

If Gemini fails, check:

```text
GOOGLE_API_KEY
```

and make sure your API key is valid and the selected model is available.

---

## Invalid Gemini JSON

The application expects Gemini to return structured JSON.

A helper function extracts JSON from the response and validates it before processing.

If valid JSON cannot be obtained, the application reports an analysis error instead of calculating an invalid result.

---

# 🔍 Development

Run the server with automatic reload:

```bash
uvicorn app:app --reload
```

For a different port:

```bash
uvicorn app:app --reload --port 8080
```

For local network access:

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

---

# 🌐 Production Deployment

For production, you can run FastAPI behind a production web server such as:

```text
Nginx
   ↓
Gunicorn / Uvicorn
   ↓
FastAPI
   ↓
Gemini API
```

A typical production command can be:

```bash
gunicorn app:app -k uvicorn.workers.UvicornWorker
```

You should also configure:

- HTTPS
- Environment variables
- Production Sentry configuration
- Secure file handling
- Request/file-size limits
- Authentication if required
- Production logging
- Reverse proxy configuration

---

# 🔒 Privacy & Security Considerations

This application processes uploaded resume content and sends extracted resume text to the configured AI provider for analysis.

Before deploying publicly, review your privacy requirements and make sure your application's privacy policy accurately explains:

- What resume data is processed
- Which third-party AI service receives the content
- Whether any data is stored
- How long data is retained
- How users can request deletion, if applicable

Also consider adding:

- File size limits
- Rate limiting
- Abuse protection
- Secure temporary file handling
- Input validation
- Production authentication where appropriate

---

# 🚧 Future Improvements

Possible future improvements include:

- [ ] OCR support for scanned resumes
- [ ] Resume-to-job-description match percentage
- [ ] Better keyword ranking
- [ ] Resume rewriting suggestions
- [ ] AI-powered resume improvement
- [ ] Downloadable PDF reports
- [ ] Resume history
- [ ] User accounts
- [ ] Multiple resume versions
- [ ] Cover letter generation
- [ ] LinkedIn profile optimization
- [ ] Resume section-by-section scoring
- [ ] More advanced ATS simulation
- [ ] Paid premium AI analysis
- [ ] Analytics dashboard

---

# 💡 Project Use Case

This project can be used as the foundation for a larger AI resume optimization platform.

A possible product flow:

```text
Upload Resume
      ↓
Add Job Description
      ↓
AI Analysis
      ↓
ATS Score
      ↓
Missing Keywords
      ↓
Formatting Problems
      ↓
Content Improvements
      ↓
Actionable Recommendations
      ↓
Optional Premium AI Optimization
```

---

# 🤝 Contributing

Contributions are welcome.

Typical workflow:

```bash
git checkout -b feature/my-feature
```

Make your changes, test the application, then commit:

```bash
git add .
git commit -m "Add new feature"
git push origin feature/my-feature
```

Then open a pull request.

---

# 📜 License

Add your preferred license here, for example:

```text
MIT License
```

if you intend to release the project under MIT.

---

# ⭐ Support

If this project helped you build or test an ATS resume analysis application, consider giving the repository a ⭐.

**Built with Python + FastAPI + Gemini + AI. 🤖**
