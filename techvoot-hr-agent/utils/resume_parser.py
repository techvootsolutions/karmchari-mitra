import re
import os
import PyPDF2
from docx import Document
import io

def extract_text_from_pdf(file_stream):
    try:
        reader = PyPDF2.PdfReader(file_stream)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return ""

def extract_text_from_docx(file_stream):
    try:
        doc = Document(file_stream)
        text = ""
        for para in doc.paragraphs:
            text += para.text + "\n"
        return text
    except Exception as e:
        print(f"Error reading DOCX: {e}")
        return ""

def parse_resume(file_stream, filename):
    """
    Parses a resume file and extracts structured data.
    """
    ext = filename.lower().split('.')[-1]
    text = ""
    
    if ext == 'pdf':
        text = extract_text_from_pdf(file_stream)
    elif ext in ['docx', 'doc']:
        text = extract_text_from_docx(file_stream)
    else:
        return {"error": "Unsupported file format. Please upload PDF or DOCX."}
        
    text = text.strip()
    if not text:
        return {"error": "Could not extract text from file."}

    # --- Extraction Logic ---
    data = {}

    # Pre-clean text for Email/Phone extraction
    # Remove null bytes or weird invisible chars
    clean_text = text.replace('\x00', '')
    
    # 1. Email
    # Sometimes emails have spaces in PDFs: "name @ domain.com" or "na me@domain.com"
    # Strategy: Find the @, grab surrounding chars, ignore spaces
    # Regex: Look for non-whitespace sequence containing @
    # But first, let's try to fix broken emails by looking for " @ " and removing spaces
    email_text = re.sub(r'\s*@\s*', '@', clean_text)
    # Also remove spaces in the part before @ if it looks fragmented? Hard.
    # Let's use a standard greedy regex on the cleaner text
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_pattern, email_text)
    data['email'] = emails[0] if emails else ""

    # 2. Phone
    # Clean up phone number: remove all non-digit/non-plus chars first to see if we find a sequence
    # OR stick to the regex that worked but extend it
    phone_pattern = r'(\+?\d[\d -]{9,15}\d)'
    phones = re.findall(phone_pattern, clean_text)
    if phones:
        # Clean up spaces and dashes from the phone number
        data['phone'] = phones[0].replace(' ', '').replace('-', '').strip()
    else:
        data['phone'] = ""

    # 3. Name (Heuristic)
    lines = [l.strip() for l in clean_text.split('\n') if l.strip()]
    ignore_words = ["resume", "curriculum", "vitae", "cv", "profile", "contact", "email", "phone"]
    
    candidate_name = ""
    for line in lines[:20]: # Check first 20 lines (sometimes headers are logo/text)
        if len(line) > 50: continue 
        if any(w in line.lower() for w in ignore_words): continue
        if "@" in line: continue
        if re.search(r'\d', line): continue
        
        # Heuristic 4: "K ar tik" -> "Kartik"
        # Strategy: Remove space if followed by a LOWERCASE letter.
        # "K a" -> "Ka". "a r" -> "ar". "r t" -> "rt".
        # "Kartik G" -> "k" space "G". Keep space.
        fixed_line = re.sub(r'(?<=[a-zA-Z])\s+(?=[a-z])', '', line)
        
        # If the result is a valid-looking name (2-3 words, mostly alpha)
        if len(fixed_line.split()) in [1, 2, 3] and len(fixed_line) > 3:
             candidate_name = fixed_line
             break
        
    data['name'] = candidate_name

    # 4. Job Title (Expanded)
    roles = {
        'Laravel Developer': ['laravel', 'php', 'artisan', 'eloquent'],
        'WordPress Developer': ['wordpress', 'wp', 'plugin', 'themes'],
        'React Developer': ['react', 'reactjs', 'redux', 'frontend', 'jsx'],
        'Python Developer': ['python', 'django', 'flask', 'fastapi', 'pandas'],
        'Web Developer': ['html', 'css', 'javascript', 'web', 'frontend', 'backend'],
        'Sales Executive': ['sales', 'marketing', 'bde', 'business development']
    }
    
    detected_role = "Candidate"
    max_matches = 0
    
    lower_text = clean_text.lower()
    for role, keywords in roles.items():
        matches = sum(1 for k in keywords if k in lower_text)
        # Weight title matches higher (exact 'laravel developer' in text)
        if role.lower() in lower_text:
            matches += 10
            
        if matches > max_matches:
            max_matches = matches
            detected_role = role
            
    data['job_title'] = detected_role
    
    return data
