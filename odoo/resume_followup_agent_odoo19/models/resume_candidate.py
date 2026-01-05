# -*- coding: utf-8 -*-

import base64
import io
import json
import logging
import re
from odoo import models, fields, api
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class ResumeCandidate(models.Model):
    _name = 'resume.candidate'
    _description = 'Resume Follow-Up Candidate'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Full Name', required=True, tracking=True)
    email = fields.Char(string='Email', tracking=True)
    phone = fields.Char(string='Phone', tracking=True)
    position = fields.Char(string='Position Applied', required=True, tracking=True)
    job_position_id = fields.Many2one(
        'job.position',
        string='Job Position',
        tracking=True,
        help='Link to job position with hiring criteria'
    )
    linkedin = fields.Char(string='LinkedIn Profile', tracking=True)
    source = fields.Selection([
        ('website', 'Website'),
        ('linkedin', 'LinkedIn'),
        ('referral', 'Referral'),
        ('job_portal', 'Job Portal'),
        ('other', 'Other')
    ], string='Source', default='website', tracking=True)
    status = fields.Selection([
        ('pending', 'Pending'),
        ('contacted', 'Contacted'),
        ('interviewed', 'Interviewed'),
        ('rejected', 'Rejected'),
        ('hired', 'Hired')
    ], string='Status', default='pending', tracking=True, required=True)
    notes = fields.Text(string='Notes')
    added_date = fields.Datetime(string='Date Added', default=fields.Datetime.now, readonly=True)
    last_contacted = fields.Datetime(string='Last Contacted', readonly=True)
    
    # CV Upload
    cv_file = fields.Binary(string='CV File', attachment=True)
    cv_filename = fields.Char(string='CV Filename')
    cv_upload_date = fields.Datetime(string='CV Upload Date', readonly=True)
    
    # Extracted CV Information
    cv_text = fields.Text(string='CV Text Content', readonly=True)
    education = fields.Text(string='Education', widget='text')
    work_experience = fields.Text(string='Work Experience', widget='text')
    skills = fields.Text(string='Skills', widget='text')
    certifications = fields.Text(string='Certifications', widget='text')
    languages = fields.Char(string='Languages')
    years_of_experience = fields.Char(string='Years of Experience')
    address = fields.Text(string='Address')
    date_of_birth = fields.Date(string='Date of Birth')
    
    # ATS Resume Checker - Two-Tier Scoring System
    ats_score_tier1 = fields.Float(
        string='ATS Score - Tier 1 (Content Interpretation)',
        digits=(5, 2),
        default=0.0,
        help='Proportion of content that can be interpreted by ATS (0-100)'
    )
    ats_score_tier2 = fields.Float(
        string='ATS Score - Tier 2 (Content Quality)',
        digits=(5, 2),
        default=0.0,
        help='Content quality score based on achievements and writing quality (0-100)'
    )
    ats_overall_score = fields.Float(
        string='Overall ATS Score',
        digits=(5, 2),
        compute='_compute_ats_overall_score',
        store=True,
        help='Combined ATS score (average of Tier 1 and Tier 2)'
    )
    ats_analysis_date = fields.Datetime(string='ATS Analysis Date', readonly=True)
    ats_interpretable_content_pct = fields.Float(
        string='Interpretable Content %',
        digits=(5, 2),
        default=0.0,
        help='Percentage of resume content that can be interpreted by ATS'
    )
    ats_spelling_errors = fields.Integer(string='Spelling Errors', default=0)
    ats_grammar_errors = fields.Integer(string='Grammar Issues', default=0)
    ats_quantifiable_achievements = fields.Integer(
        string='Quantifiable Achievements',
        default=0,
        help='Number of achievements with numbers/metrics found'
    )
    ats_analysis_details = fields.Text(
        string='ATS Analysis Details',
        readonly=True,
        help='Detailed analysis results in JSON format'
    )
    ats_keywords_found = fields.Text(
        string='Keywords Found',
        widget='text',
        readonly=True,
        help='Relevant keywords identified in the resume'
    )
    ats_missing_sections = fields.Text(
        string='Missing Sections',
        widget='text',
        readonly=True,
        help='Important sections that are missing from the resume'
    )
    ats_recommendations = fields.Text(
        string='Recommendations',
        widget='text',
        readonly=True,
        help='Recommendations to improve ATS score'
    )
    # Detailed scoring breakdown
    ats_tier1_breakdown = fields.Text(
        string='Tier 1 Scoring Breakdown',
        default='',
        readonly=True,
        help='Detailed breakdown of Tier 1 scoring with points for each aspect'
    )
    ats_tier2_breakdown = fields.Text(
        string='Tier 2 Scoring Breakdown',
        default='',
        readonly=True,
        help='Detailed breakdown of Tier 2 scoring with points for each aspect'
    )
    ats_issues_found = fields.Text(
        string='Issues Found',
        default='',
        readonly=True,
        help='Detailed list of all issues found with point deductions'
    )
    ats_achievements_list = fields.Text(
        string='Achievements List',
        default='',
        readonly=True,
        help='List of all quantifiable achievements found'
    )
    
    # Collected information from conversations
    introduction = fields.Text(string='Introduction')
    current_position = fields.Char(string='Current Position')
    current_salary = fields.Char(string='Current Salary')
    expected_salary = fields.Char(string='Expected Salary')
    notice_period = fields.Char(string='Notice Period')
    
    # Relations
    conversation_ids = fields.One2many(
        'resume.conversation',
        'candidate_id',
        string='Conversations'
    )
    conversation_count = fields.Integer(
        string='Conversation Count',
        compute='_compute_conversation_count',
        store=False
    )
    
    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )

    @api.depends('conversation_ids')
    def _compute_conversation_count(self):
        for record in self:
            record.conversation_count = len(record.conversation_ids)
    
    @api.depends('ats_score_tier1', 'ats_score_tier2')
    def _compute_ats_overall_score(self):
        """Compute overall ATS score as average of Tier 1 and Tier 2"""
        for record in self:
            if record.ats_score_tier1 > 0 or record.ats_score_tier2 > 0:
                record.ats_overall_score = (record.ats_score_tier1 + record.ats_score_tier2) / 2.0
            else:
                record.ats_overall_score = 0.0

    def action_start_conversation(self):
        """Action to start a new phone call with candidate"""
        self.ensure_one()
        if not self.phone:
            raise ValidationError('Phone number is required to make a call. Please add the candidate\'s phone number first.')
        return {
            'name': 'Start Phone Call',
            'type': 'ir.actions.act_window',
            'res_model': 'resume.conversation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_candidate_id': self.id,
                'default_candidate_name': self.name,
                'default_position': self.position,
            }
        }

    def action_view_conversations(self):
        """View all conversations for this candidate"""
        self.ensure_one()
        return {
            'name': 'Conversations',
            'type': 'ir.actions.act_window',
            'res_model': 'resume.conversation',
            'view_mode': 'list,form',
            'domain': [('candidate_id', '=', self.id)],
            'context': {'default_candidate_id': self.id}
        }

    def action_evaluate_against_job(self):
        """Evaluate candidate against linked job position"""
        self.ensure_one()
        if not self.job_position_id:
            raise ValidationError('Please link this candidate to a job position first.')
        
        if self.job_position_id.state != 'open':
            raise ValidationError('The linked job position is not open.')
        
        result = self.job_position_id.action_evaluate_candidate(self)
        
        # Show result to user
        if result['matches']:
            message = f"✓ Candidate MATCHES all requirements!\n\n"
            if result['years_found'] is not None:
                message += f"Experience: {result['years_found']} years ✓\n"
            if result['salary_found'] is not None:
                message += f"Salary: {result['salary_found']:,.0f} ✓\n"
            message_type = 'success'
        else:
            message = f"✗ Candidate does NOT match requirements\n\n"
            if result['years_found'] is not None:
                message += f"Experience: {result['years_found']} years "
                message += "✓" if result['experience_matches'] else "✗"
                message += f"\n  Required: {result['min_experience_required']}"
                if result['max_experience_required']:
                    message += f" - {result['max_experience_required']} years"
                else:
                    message += "+ years"
                message += "\n"
            
            if result['salary_found'] is not None or (result['min_salary_required'] or result['max_salary_required']):
                message += f"Salary: {result['salary_found']:,.0f if result['salary_found'] else 'Not found'} "
                message += "✓" if result['salary_matches'] else "✗"
                if result['min_salary_required'] or result['max_salary_required']:
                    message += f"\n  Required: "
                    if result['min_salary_required']:
                        message += f"{result['min_salary_required']:,.0f}+"
                    if result['max_salary_required']:
                        message += f" up to {result['max_salary_required']:,.0f}"
                message += "\n"
            
            message += f"\nReasons:\n{result['reason']}"
            message_type = 'warning'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Job Position Evaluation',
                'message': message,
                'type': message_type,
                'sticky': True,
            }
        }

    def _extract_text_from_pdf(self, file_data):
        """Extract text from PDF file"""
        try:
            import PyPDF2
            pdf_file = io.BytesIO(file_data)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text
        except ImportError:
            _logger.warning("PyPDF2 not installed. Trying pdfplumber...")
            try:
                import pdfplumber
                pdf_file = io.BytesIO(file_data)
                with pdfplumber.open(pdf_file) as pdf:
                    text = ""
                    for page in pdf.pages:
                        text += page.extract_text() + "\n"
                return text
            except ImportError:
                _logger.error("Neither PyPDF2 nor pdfplumber is installed. Please install one of them.")
                return ""
        except Exception as e:
            _logger.error(f"Error extracting text from PDF: {str(e)}")
            return ""

    def _extract_text_from_docx(self, file_data):
        """Extract text from DOCX file"""
        try:
            from docx import Document
            doc_file = io.BytesIO(file_data)
            doc = Document(doc_file)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        except ImportError:
            _logger.error("python-docx is not installed. Please install it to extract text from DOCX files.")
            return ""
        except Exception as e:
            _logger.error(f"Error extracting text from DOCX: {str(e)}")
            return ""

    def _detect_file_type(self, file_data):
        """Detect file type from magic bytes"""
        if not file_data or len(file_data) < 4:
            return None
        
        # PDF magic bytes: %PDF
        if file_data[:4] == b'%PDF':
            return 'pdf'
        # DOCX magic bytes: PK (ZIP format)
        if file_data[:2] == b'PK':
            # Check if it's a DOCX by looking for word/ in the ZIP
            try:
                if b'word/' in file_data[:1000] or b'[Content_Types].xml' in file_data[:2000]:
                    return 'docx'
            except:
                pass
        # Try to decode as text
        try:
            decoded = file_data[:100].decode('utf-8', errors='ignore')
            if all(ord(c) < 128 for c in decoded[:50]):  # Mostly ASCII
                return 'txt'
        except:
            pass
        
        return None

    def _extract_text_from_file(self, file_data, filename):
        """Extract text from uploaded file based on file extension"""
        if not file_data:
            _logger.warning("No file data provided")
            return ""
        
        try:
            # Try to decode base64 if it's a string, otherwise assume it's already bytes
            if isinstance(file_data, str):
                try:
                    decoded_data = base64.b64decode(file_data)
                    _logger.info("Decoded base64 string to bytes")
                except Exception as e:
                    _logger.error(f"Error decoding base64: {e}")
                    return ""
            elif isinstance(file_data, bytes):
                decoded_data = file_data
                _logger.info("File data is already bytes")
            else:
                _logger.error(f"Unexpected file_data type: {type(file_data)}")
                return ""
            
            if len(decoded_data) == 0:
                _logger.error("Decoded file data is empty")
                return ""
                
            _logger.info(f"File data size: {len(decoded_data)} bytes")
        except Exception as e:
            _logger.error(f"Error processing file data: {e}", exc_info=True)
            return ""
        
        # Get file extension from filename or detect from content
        file_ext = None
        if filename:
            file_ext = filename.lower().split('.')[-1] if '.' in filename else ''
            _logger.info(f"File extension from filename: {file_ext}")
        
        # If no extension from filename, try to detect from content
        if not file_ext:
            detected_type = self._detect_file_type(decoded_data)
            if detected_type:
                file_ext = detected_type
                _logger.info(f"Detected file type from content: {file_ext}")
            else:
                _logger.warning("Could not determine file type from filename or content")
        
        if not file_ext:
            # Try all supported formats
            _logger.info("Trying to extract as PDF...")
            text = self._extract_text_from_pdf(decoded_data)
            if text and len(text.strip()) > 10:
                _logger.info("Successfully extracted as PDF")
                return text
            
            _logger.info("Trying to extract as DOCX...")
            text = self._extract_text_from_docx(decoded_data)
            if text and len(text.strip()) > 10:
                _logger.info("Successfully extracted as DOCX")
                return text
            
            _logger.info("Trying to extract as TXT...")
            try:
                text = decoded_data.decode('utf-8')
                if text and len(text.strip()) > 10:
                    _logger.info("Successfully extracted as TXT")
                    return text
            except:
                try:
                    text = decoded_data.decode('latin-1')
                    if text and len(text.strip()) > 10:
                        _logger.info("Successfully extracted as TXT (latin-1)")
                        return text
                except:
                    pass
            
            _logger.error("Failed to extract text from file using any method")
            return ""
        
        # Extract based on detected extension
        if file_ext == 'pdf':
            text = self._extract_text_from_pdf(decoded_data)
            if not text or len(text.strip()) < 10:
                _logger.warning("PDF extraction returned empty or very short text")
            else:
                _logger.info(f"Successfully extracted {len(text)} characters from PDF")
            return text
        elif file_ext in ['docx', 'doc']:
            text = self._extract_text_from_docx(decoded_data)
            if not text or len(text.strip()) < 10:
                _logger.warning("DOCX extraction returned empty or very short text")
            else:
                _logger.info(f"Successfully extracted {len(text)} characters from DOCX")
            return text
        elif file_ext == 'txt':
            try:
                text = decoded_data.decode('utf-8')
                _logger.info(f"Successfully extracted {len(text)} characters from TXT")
                return text
            except:
                try:
                    text = decoded_data.decode('latin-1')
                    _logger.info(f"Successfully extracted {len(text)} characters from TXT (latin-1)")
                    return text
                except Exception as e:
                    _logger.error(f"Failed to decode text file: {e}")
                    return ""
        else:
            _logger.warning(f"Unsupported file type: {file_ext}. Supported: pdf, docx, doc, txt")
            return ""

    def _extract_cv_data(self, cv_text):
        """Extract structured data from CV text using pattern matching and AI-like extraction"""
        extracted_data = {
            'education': '',
            'work_experience': '',
            'skills': '',
            'certifications': '',
            'languages': '',
            'years_of_experience': '',
            'address': '',
            'date_of_birth': '',
            'email': '',
            'phone': '',
        }
        
        if not cv_text:
            return extracted_data
        
        lines = cv_text.split('\n')
        cv_lower = cv_text.lower()
        
        # Extract email
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, cv_text)
        if emails:
            extracted_data['email'] = emails[0]
        
        # Extract phone
        phone_patterns = [
            r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
            r'\+?\d{10,15}',
        ]
        for pattern in phone_patterns:
            phones = re.findall(pattern, cv_text)
            if phones:
                extracted_data['phone'] = phones[0] if isinstance(phones[0], str) else ''.join(phones[0])
                break
        
        # Extract sections
        sections = {
            'education': ['education', 'academic', 'qualification', 'degree', 'university', 'college'],
            'work_experience': ['experience', 'employment', 'work history', 'professional experience', 'career'],
            'skills': ['skills', 'technical skills', 'competencies', 'abilities', 'expertise'],
            'certifications': ['certification', 'certificate', 'license', 'credentials'],
            'languages': ['language', 'languages', 'linguistic'],
        }
        
        current_section = None
        section_content = []
        
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            
            # Check if this line is a section header
            for section_key, keywords in sections.items():
                if any(keyword in line_lower for keyword in keywords) and len(line.strip()) < 100:
                    # Save previous section
                    if current_section and section_content:
                        extracted_data[current_section] = '\n'.join(section_content)
                    # Start new section
                    current_section = section_key
                    section_content = []
                    break
            else:
                # Add to current section if we're in one
                if current_section and line.strip():
                    section_content.append(line.strip())
        
        # Save last section
        if current_section and section_content:
            extracted_data[current_section] = '\n'.join(section_content)
        
        # Extract years of experience
        exp_patterns = [
            r'(\d+)\s*(?:years?|yrs?)\s*(?:of\s*)?(?:experience|exp)',
            r'experience[:\s]+(\d+)\s*(?:years?|yrs?)',
        ]
        for pattern in exp_patterns:
            match = re.search(pattern, cv_lower)
            if match:
                extracted_data['years_of_experience'] = match.group(1)
                break
        
        # Extract address (look for common address patterns)
        address_keywords = ['street', 'avenue', 'road', 'city', 'state', 'zip', 'postal', 'address']
        address_lines = []
        for i, line in enumerate(lines):
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in address_keywords) and len(line.strip()) < 200:
                address_lines.append(line.strip())
                # Also check next few lines
                for j in range(1, 3):
                    if i + j < len(lines) and lines[i + j].strip():
                        address_lines.append(lines[i + j].strip())
                break
        if address_lines:
            extracted_data['address'] = '\n'.join(address_lines[:3])
        
        return extracted_data

    def _extract_and_populate_cv_data(self):
        """Extract data from CV and populate fields"""
        self.ensure_one()
        if not self.cv_file:
            _logger.warning("No CV file to extract")
            raise ValidationError('No CV file uploaded. Please upload a CV file first.')
        
        # Try to get filename if not set
        filename = self.cv_filename
        if not filename:
            filename = self._get_cv_filename()
            if filename:
                self.cv_filename = filename
                _logger.info(f"Retrieved filename from attachment: {filename}")
            else:
                _logger.warning("CV filename not set and could not retrieve from attachment")
        
        # Extract text from CV
        _logger.info(f"Starting CV extraction for file: {filename or 'unknown'}")
        try:
            cv_text = self._extract_text_from_file(self.cv_file, filename)
        except Exception as e:
            _logger.error(f"Exception during text extraction: {e}", exc_info=True)
            raise ValidationError(f'Error extracting text from CV: {str(e)}')
        
        if not cv_text or len(cv_text.strip()) < 10:
            # Get diagnostics
            diagnostics = self._diagnose_cv_file()
            
            # Check if libraries are installed
            missing_libs = self._check_required_libraries()
            
            error_msg = f'Could not extract text from the uploaded CV file ({filename or "unknown"}).\n\n'
            error_msg += 'Diagnostics:\n'
            error_msg += '\n'.join([f'  {d}' for d in diagnostics])
            error_msg += '\n\n'
            
            if missing_libs:
                error_msg += f'❌ Missing required libraries: {", ".join(missing_libs)}\n'
                error_msg += '📦 Please install them using:\n'
                error_msg += '   pip install PyPDF2 python-docx\n'
                error_msg += '   OR\n'
                error_msg += '   pip install -r requirements.txt\n\n'
            
            error_msg += 'Please ensure:\n'
            error_msg += '1. ✅ The file is a valid PDF, DOCX, or TXT file\n'
            error_msg += '2. ✅ The file is not password protected\n'
            error_msg += '3. ✅ The file is not corrupted\n'
            error_msg += '4. ✅ The file contains readable text (not just images/scans)\n'
            error_msg += '5. ✅ Required Python libraries are installed (see above)'
            
            _logger.error(error_msg)
            raise ValidationError(error_msg)
        
        _logger.info(f"Successfully extracted {len(cv_text)} characters from CV")
        
        # Store raw CV text
        self.cv_text = cv_text
        
        # Extract structured data
        extracted_data = self._extract_cv_data(cv_text)
        
        # Extract name from CV if not set (look for name patterns at the beginning)
        if not self.name and cv_text:
            lines = cv_text.split('\n')
            # First few non-empty lines are often the name
            for line in lines[:5]:
                line = line.strip()
                if line and len(line) < 100 and not any(char.isdigit() for char in line[:10]):
                    # Check if it looks like a name (has letters, spaces, maybe some special chars)
                    if any(c.isalpha() for c in line) and len(line.split()) <= 5:
                        self.name = line
                        break
        
        # Populate fields (only if they're empty to avoid overwriting existing data)
        if extracted_data.get('email') and not self.email:
            self.email = extracted_data['email']
        if extracted_data.get('phone') and not self.phone:
            self.phone = extracted_data['phone']
        if extracted_data.get('education') and not self.education:
            self.education = extracted_data['education']
        if extracted_data.get('work_experience') and not self.work_experience:
            self.work_experience = extracted_data['work_experience']
        if extracted_data.get('skills') and not self.skills:
            self.skills = extracted_data['skills']
        if extracted_data.get('certifications') and not self.certifications:
            self.certifications = extracted_data['certifications']
        if extracted_data.get('languages') and not self.languages:
            self.languages = extracted_data['languages']
        if extracted_data.get('years_of_experience') and not self.years_of_experience:
            self.years_of_experience = extracted_data['years_of_experience']
        if extracted_data.get('address') and not self.address:
            self.address = extracted_data['address']
        
        # Update CV upload date
        self.cv_upload_date = fields.Datetime.now()

    def _check_required_libraries(self):
        """Check if required libraries are installed"""
        missing = []
        try:
            import PyPDF2
        except ImportError:
            try:
                import pdfplumber
            except ImportError:
                missing.append("PyPDF2 or pdfplumber (for PDF files)")
        
        try:
            from docx import Document
        except ImportError:
            missing.append("python-docx (for DOCX files)")
        
        return missing

    def _diagnose_cv_file(self):
        """Diagnose CV file issues and return helpful information"""
        diagnostics = []
        
        if not self.cv_file:
            diagnostics.append("❌ No CV file uploaded")
            return diagnostics
        
        diagnostics.append(f"✅ CV file is present")
        
        # Check filename
        if not self.cv_filename:
            filename = self._get_cv_filename()
            if filename:
                diagnostics.append(f"✅ Filename retrieved from attachment: {filename}")
            else:
                diagnostics.append("⚠️ Filename not set and could not be retrieved")
        else:
            diagnostics.append(f"✅ Filename: {self.cv_filename}")
        
        # Check file data
        try:
            if isinstance(self.cv_file, str):
                decoded = base64.b64decode(self.cv_file)
                diagnostics.append(f"✅ File data is base64 encoded, size: {len(decoded)} bytes")
            elif isinstance(self.cv_file, bytes):
                diagnostics.append(f"✅ File data is bytes, size: {len(self.cv_file)} bytes")
            else:
                diagnostics.append(f"⚠️ File data type: {type(self.cv_file)}")
        except Exception as e:
            diagnostics.append(f"❌ Error processing file data: {e}")
        
        # Check libraries
        missing_libs = self._check_required_libraries()
        if missing_libs:
            diagnostics.append(f"❌ Missing libraries: {', '.join(missing_libs)}")
        else:
            diagnostics.append("✅ Required libraries are installed")
        
        return diagnostics

    def action_extract_cv_data(self):
        """Manual action to extract data from CV"""
        self.ensure_one()
        if not self.cv_file:
            raise ValidationError('Please upload a CV file first.')
        
        # Check for missing libraries first
        missing_libs = self._check_required_libraries()
        if missing_libs:
            lib_msg = '\n'.join([f"- {lib}" for lib in missing_libs])
            raise ValidationError(
                f'Required libraries are not installed:\n{lib_msg}\n\n'
                f'Please install them using:\npip install PyPDF2 python-docx\n\n'
                f'Or install from requirements.txt:\npip install -r requirements.txt'
            )
        
        try:
            self._extract_and_populate_cv_data()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success',
                    'message': 'CV data extracted successfully!',
                    'type': 'success',
                    'sticky': False,
                }
            }
        except ValidationError:
            # Re-raise ValidationError as-is
            raise
        except Exception as e:
            _logger.error(f"Unexpected error extracting CV data: {e}", exc_info=True)
            raise ValidationError(f'Error extracting CV data: {str(e)}')

    def _get_cv_filename(self):
        """Get CV filename from attachment if not set in field"""
        if self.cv_filename:
            return self.cv_filename
        
        # Try to get filename from attachment
        if self.id:
            # Search for any recent attachment related to this record
            attachment = self.env['ir.attachment'].search([
                ('res_model', '=', 'resume.candidate'),
                ('res_id', '=', self.id),
            ], limit=1, order='create_date desc')
            
            if attachment:
                _logger.info(f"Found attachment: {attachment.name}")
                return attachment.name
            else:
                _logger.warning(f"No attachment found for resume.candidate {self.id}")
        
        return None

    @api.onchange('cv_file')
    def _onchange_cv_file(self):
        """Automatically extract data when CV is uploaded"""
        if self.cv_file:
            # Ensure filename is set
            if not self.cv_filename:
                filename = self._get_cv_filename()
                if filename:
                    self.cv_filename = filename
            
            try:
                self._extract_and_populate_cv_data()
                # Auto-evaluate against job position if linked
                if self.job_position_id and self.job_position_id.state == 'open':
                    self._auto_evaluate_job_position()
            except Exception as e:
                _logger.error(f"Error extracting CV data: {str(e)}", exc_info=True)
                # Don't raise exception in onchange, just log it
                return {
                    'warning': {
                        'title': 'CV Extraction Warning',
                        'message': f'CV uploaded but data extraction encountered an issue: {str(e)}. You can use the "Extract CV Data" button to try again.'
                    }
                }

    @api.onchange('job_position_id')
    def _onchange_job_position_id(self):
        """Auto-evaluate candidate when linked to job position"""
        if self.job_position_id and self.job_position_id.state == 'open' and self.cv_text:
            self._auto_evaluate_job_position()

    def _auto_evaluate_job_position(self):
        """Automatically evaluate candidate against job position criteria (experience and salary)"""
        if not self.job_position_id or self.job_position_id.state != 'open':
            return
        
        job = self.job_position_id
        if not job.auto_approve_matching and not job.auto_reject_non_matching:
            return
        
        exp_matches, years = job._candidate_matches_experience(self)
        sal_matches, salary = job._candidate_matches_salary(self)
        
        # Candidate matches if BOTH experience and salary match (if salary is required)
        overall_matches = exp_matches and sal_matches
        
        if overall_matches and job.auto_approve_matching and self.status in ['pending', 'contacted']:
            # Check if positions are still available
            if job.positions_remaining > 0:
                reasons = []
                if exp_matches and years is not None:
                    reasons.append(f'Experience: {years} years')
                if sal_matches and salary is not None:
                    reasons.append(f'Salary: {salary:,.0f}')
                
                self.status = 'interviewed'
                note = f'\n[Auto-approved] Matches requirements ({", ".join(reasons)})'
                self.notes = (self.notes or '') + note
                _logger.info(f"Auto-approved candidate {self.id} for job {job.id}")
        elif not overall_matches and job.auto_reject_non_matching and self.status in ['pending', 'contacted']:
            reasons = []
            
            # Experience reasons
            if not exp_matches:
                if years is None:
                    reasons.append('Could not determine experience')
                elif years < job.min_experience_years:
                    reasons.append(f'Experience too low ({years} years, required: {job.min_experience_years}+)')
                elif job.max_experience_years and years > job.max_experience_years:
                    reasons.append(f'Experience too high ({years} years, max: {job.max_experience_years})')
            
            # Salary reasons (only if salary is required)
            if (job.min_salary or job.max_salary) and not sal_matches:
                if salary is None:
                    reasons.append('Could not determine salary')
                elif job.min_salary and salary < job.min_salary:
                    reasons.append(f'Salary too low ({salary:,.0f}, required: {job.min_salary:,.0f}+)')
                elif job.max_salary and salary > job.max_salary:
                    reasons.append(f'Salary too high ({salary:,.0f}, max: {job.max_salary:,.0f})')
            
            reason = ' | '.join(reasons) if reasons else 'Does not match requirements'
            
            self.status = 'rejected'
            note = f'\n[Auto-rejected] {reason}'
            self.notes = (self.notes or '') + note
            _logger.info(f"Auto-rejected candidate {self.id} for job {job.id}: {reason}")

    # ========== ATS Resume Checker Methods ==========
    
    def _analyze_ats_tier1(self, cv_text):
        """
        Tier 1 Analysis: Proportion of content that can be interpreted by ATS
        Similar to an ATS, we analyze and attempt to comprehend the resume.
        """
        if not cv_text:
            return {
                'score': 0.0,
                'interpretable_pct': 0.0,
                'parsed_sections': [],
                'missing_sections': [],
                'keywords_found': [],
                'details': {}
            }
        
        # Required sections for ATS parsing
        required_sections = {
            'contact': ['email', 'phone', 'address', 'contact'],
            'experience': ['experience', 'employment', 'work history', 'career', 'professional'],
            'education': ['education', 'academic', 'qualification', 'degree', 'university', 'college'],
            'skills': ['skills', 'technical skills', 'competencies', 'abilities', 'expertise'],
        }
        
        cv_lower = cv_text.lower()
        parsed_sections = []
        missing_sections = []
        keywords_found = []
        
        # Check for each required section
        for section_name, keywords in required_sections.items():
            found = any(keyword in cv_lower for keyword in keywords)
            if found:
                parsed_sections.append(section_name)
            else:
                missing_sections.append(section_name)
        
        # Extract structured data (name, email, phone, etc.)
        structured_data_score = 0
        structured_data = {}
        
        # Name detection
        if self.name and len(self.name.strip()) > 0:
            structured_data['name'] = True
            structured_data_score += 1
        
        # Email detection
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        if re.search(email_pattern, cv_text):
            structured_data['email'] = True
            structured_data_score += 1
        
        # Phone detection
        phone_patterns = [
            r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
            r'\+?\d{10,15}',
        ]
        if any(re.search(pattern, cv_text) for pattern in phone_patterns):
            structured_data['phone'] = True
            structured_data_score += 1
        
        # Date detection (for experience/education dates)
        date_patterns = [
            r'\d{4}',  # Years
            r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{4}',
        ]
        dates_found = len(re.findall('|'.join(date_patterns), cv_lower))
        structured_data['dates'] = dates_found
        
        # Calculate interpretable content percentage
        # Base score: sections found (40%) + structured data (30%) + dates (20%) + keywords (10%)
        section_score = (len(parsed_sections) / len(required_sections)) * 40
        structured_score = (structured_data_score / 3) * 30
        date_score = min((dates_found / 10) * 20, 20)  # Cap at 20 points
        keyword_score = min((len(keywords_found) / 20) * 10, 10)  # Cap at 10 points
        
        interpretable_pct = section_score + structured_score + date_score + keyword_score
        tier1_score = min(interpretable_pct, 100.0)
        
        # Extract common keywords
        common_keywords = [
            'experience', 'skills', 'education', 'certification', 'achievement',
            'project', 'leadership', 'management', 'development', 'analysis',
            'communication', 'team', 'result', 'improve', 'increase', 'decrease'
        ]
        keywords_found = [kw for kw in common_keywords if kw in cv_lower]
        
        # Create detailed breakdown text
        breakdown_lines = [
            "=== TIER 1 SCORING BREAKDOWN ===",
            "",
            f"1. SECTIONS FOUND: {section_score:.2f}/40.0 points",
            f"   • Found sections: {', '.join(parsed_sections) if parsed_sections else 'None'}",
            f"   • Missing sections: {', '.join(missing_sections) if missing_sections else 'None'}",
            f"   • Points: {len(parsed_sections)}/{len(required_sections)} sections × 10 points each",
            "",
            f"2. STRUCTURED DATA: {structured_score:.2f}/30.0 points",
            f"   • Name: {'✓ Found' if structured_data.get('name') else '✗ Missing'} (+10 points if found)",
            f"   • Email: {'✓ Found' if structured_data.get('email') else '✗ Missing'} (+10 points if found)",
            f"   • Phone: {'✓ Found' if structured_data.get('phone') else '✗ Missing'} (+10 points if found)",
            f"   • Total: {structured_data_score}/3 items found",
            "",
            f"3. DATES FOUND: {date_score:.2f}/20.0 points",
            f"   • Dates detected: {dates_found}",
            f"   • Points: {min(dates_found, 10)} dates × 2 points each (max 20 points)",
            "",
            f"4. KEYWORDS: {keyword_score:.2f}/10.0 points",
            f"   • Keywords found: {len(keywords_found)}",
            f"   • Points: {len(keywords_found)} keywords × 0.5 points each (max 10 points)",
            "",
            f"TOTAL TIER 1 SCORE: {tier1_score:.2f}/100.0",
            f"Interpretable Content: {interpretable_pct:.2f}%"
        ]
        
        return {
            'score': tier1_score,
            'interpretable_pct': interpretable_pct,
            'parsed_sections': parsed_sections,
            'missing_sections': missing_sections,
            'keywords_found': keywords_found,
            'structured_data': structured_data,
            'dates_found': dates_found,
            'breakdown_text': '\n'.join(breakdown_lines),
            'details': {
                'section_score': section_score,
                'structured_score': structured_score,
                'date_score': date_score,
                'keyword_score': keyword_score,
                'section_details': {
                    'found': parsed_sections,
                    'missing': missing_sections,
                    'points': section_score
                },
                'structured_details': {
                    'name': structured_data.get('name', False),
                    'email': structured_data.get('email', False),
                    'phone': structured_data.get('phone', False),
                    'points': structured_score
                },
                'date_details': {
                    'count': dates_found,
                    'points': date_score
                },
                'keyword_details': {
                    'count': len(keywords_found),
                    'keywords': keywords_found,
                    'points': keyword_score
                }
            }
        }
    
    def _check_spelling_grammar(self, cv_text):
        """Check spelling and grammar errors in CV text"""
        spelling_errors = 0
        grammar_issues = 0
        errors = []
        
        if not cv_text:
            return {
                'spelling_errors': 0,
                'grammar_issues': 0,
                'errors': []
            }
        
        try:
            # Try to use pyspellchecker if available
            try:
                from spellchecker import SpellChecker
                spell = SpellChecker()
                
                # Split text into words and check spelling
                words = re.findall(r'\b[a-zA-Z]{2,}\b', cv_text.lower())
                misspelled = spell.unknown(words)
                spelling_errors = len(misspelled)
                
                if misspelled:
                    errors.extend([f"Possible spelling: {word}" for word in list(misspelled)[:10]])
            except ImportError:
                # Fallback: basic spell checking using common word list
                common_words = {
                    'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i',
                    'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
                    'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she',
                    'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there', 'their',
                    'experience', 'education', 'skills', 'project', 'management', 'development'
                }
                words = re.findall(r'\b[a-zA-Z]{3,}\b', cv_text.lower())
                # Simple check: words that are too long or contain unusual patterns
                unusual_words = [w for w in words if len(w) > 15 and w not in common_words]
                spelling_errors = min(len(unusual_words), 50)  # Cap at 50
        except Exception as e:
            _logger.warning(f"Spell checking error: {e}")
        
        # Basic grammar checks
        grammar_patterns = [
            (r'\bi\s+[a-z]', 'Lowercase "i" should be capitalized'),
            (r'\.{2,}', 'Multiple periods'),
            (r'\s{2,}', 'Multiple spaces'),
            (r'[a-z][A-Z]', 'Missing space between words'),
        ]
        
        for pattern, issue in grammar_patterns:
            matches = re.findall(pattern, cv_text)
            if matches:
                grammar_issues += len(matches)
                errors.append(f"{issue}: {len(matches)} instances")
        
        return {
            'spelling_errors': spelling_errors,
            'grammar_issues': grammar_issues,
            'errors': errors[:20]  # Limit to 20 errors
        }
    
    def _extract_quantifiable_achievements(self, cv_text):
        """
        Extract quantifiable achievements - numbers, percentages, metrics
        These are important for Tier 2 scoring
        """
        if not cv_text:
            return {
                'count': 0,
                'achievements': [],
                'metrics_found': []
            }
        
        # Patterns for quantifiable achievements
        achievement_patterns = [
            r'increased\s+by\s+(\d+%?|\d+\.\d+%)',
            r'decreased\s+by\s+(\d+%?|\d+\.\d+%)',
            r'improved\s+by\s+(\d+%?|\d+\.\d+%)',
            r'(\d+%?)\s+increase',
            r'(\d+%?)\s+decrease',
            r'(\d+%?)\s+improvement',
            r'managed\s+(\d+)\s+',
            r'led\s+(\d+)\s+',
            r'team\s+of\s+(\d+)',
            r'(\d+)\s+years?\s+of\s+experience',
            r'(\d+)\s+projects?',
            r'(\d+)\s+customers?',
            r'(\d+)\s+clients?',
            r'(\d+)\s+employees?',
            r'budget\s+of\s+[\$€£]?(\d+[KMB]?)',
            r'[\$€£](\d+[KMB]?)\s+',
            r'(\d+)\s+%',
        ]
        
        achievements = []
        metrics_found = []
        
        for pattern in achievement_patterns:
            matches = re.finditer(pattern, cv_text, re.IGNORECASE)
            for match in matches:
                value = match.group(1) if match.groups() else match.group(0)
                context_start = max(0, match.start() - 50)
                context_end = min(len(cv_text), match.end() + 50)
                context = cv_text[context_start:context_end].strip()
                
                achievements.append({
                    'value': value,
                    'context': context,
                    'pattern': pattern
                })
                metrics_found.append(value)
        
        # Remove duplicates based on value
        unique_achievements = []
        seen_values = set()
        for ach in achievements:
            if ach['value'] not in seen_values:
                unique_achievements.append(ach)
                seen_values.add(ach['value'])
        
        return {
            'count': len(unique_achievements),
            'achievements': unique_achievements[:20],  # Limit to 20
            'metrics_found': list(set(metrics_found))[:30]
        }
    
    def _analyze_ats_tier2(self, cv_text):
        """
        Tier 2 Analysis: Content quality, spelling, and quantifiable achievements
        Although an ATS doesn't look for spelling mistakes and poorly crafted content,
        recruitment managers certainly do.
        """
        if not cv_text:
            return {
                'score': 0.0,
                'spelling_errors': 0,
                'grammar_issues': 0,
                'achievements_count': 0,
                'details': {}
            }
        
        # Check spelling and grammar
        spell_grammar = self._check_spelling_grammar(cv_text)
        
        # Extract quantifiable achievements
        achievements = self._extract_quantifiable_achievements(cv_text)
        
        # Calculate Tier 2 score
        # Base: 50 points
        # Achievements: up to 30 points (1 point per achievement, max 30)
        # Spelling: -2 points per error (max -30)
        # Grammar: -1 point per issue (max -20)
        
        base_score = 50.0
        achievement_score = min(achievements['count'] * 1.5, 30.0)
        spelling_penalty = min(spell_grammar['spelling_errors'] * 2, 30.0)
        grammar_penalty = min(spell_grammar['grammar_issues'] * 1, 20.0)
        
        tier2_score = base_score + achievement_score - spelling_penalty - grammar_penalty
        tier2_score = max(0.0, min(100.0, tier2_score))  # Clamp between 0 and 100
        
        # Create detailed breakdown text
        breakdown_lines = [
            "=== TIER 2 SCORING BREAKDOWN ===",
            "",
            f"1. BASE SCORE: {base_score:.2f}/50.0 points",
            "   • Starting score for all resumes",
            "",
            f"2. ACHIEVEMENTS: +{achievement_score:.2f} points (max +30.0)",
            f"   • Quantifiable achievements found: {achievements['count']}",
            f"   • Points: {achievements['count']} achievements × 1.5 points each",
            f"   • Examples: {', '.join([a['value'] for a in achievements['achievements'][:5]]) if achievements['achievements'] else 'None'}",
            "",
            f"3. SPELLING ERRORS: -{spelling_penalty:.2f} points (max -30.0)",
            f"   • Spelling errors found: {spell_grammar['spelling_errors']}",
            f"   • Points deducted: {spell_grammar['spelling_errors']} errors × 2 points each",
            "",
            f"4. GRAMMAR ISSUES: -{grammar_penalty:.2f} points (max -20.0)",
            f"   • Grammar issues found: {spell_grammar['grammar_issues']}",
            f"   • Points deducted: {spell_grammar['grammar_issues']} issues × 1 point each",
            "",
            f"TOTAL TIER 2 SCORE: {tier2_score:.2f}/100.0",
            f"Calculation: {base_score:.2f} (base) + {achievement_score:.2f} (achievements) - {spelling_penalty:.2f} (spelling) - {grammar_penalty:.2f} (grammar)"
        ]
        
        # Create issues list
        issues_list = []
        if spell_grammar['spelling_errors'] > 0:
            issues_list.append(f"SPELLING ERRORS ({spell_grammar['spelling_errors']} found, -{spelling_penalty:.2f} points):")
            for error in spell_grammar['errors'][:10]:
                if 'spelling' in error.lower():
                    issues_list.append(f"  • {error}")
        
        if spell_grammar['grammar_issues'] > 0:
            issues_list.append(f"\nGRAMMAR ISSUES ({spell_grammar['grammar_issues']} found, -{grammar_penalty:.2f} points):")
            for error in spell_grammar['errors'][:10]:
                if 'grammar' in error.lower() or 'space' in error.lower() or 'period' in error.lower():
                    issues_list.append(f"  • {error}")
        
        if achievements['count'] == 0:
            issues_list.append(f"\nMISSING ACHIEVEMENTS:")
            issues_list.append("  • No quantifiable achievements found (add numbers, percentages, metrics)")
        
        return {
            'score': tier2_score,
            'spelling_errors': spell_grammar['spelling_errors'],
            'grammar_issues': spell_grammar['grammar_issues'],
            'achievements_count': achievements['count'],
            'achievements': achievements['achievements'],
            'spelling_errors_list': spell_grammar['errors'],
            'breakdown_text': '\n'.join(breakdown_lines),
            'issues_text': '\n'.join(issues_list) if issues_list else 'No major issues found.',
            'achievements_text': '\n'.join([
                f"• {ach['value']}: {ach['context'][:100]}..." 
                for ach in achievements['achievements'][:20]
            ]) if achievements['achievements'] else 'No quantifiable achievements found.',
            'details': {
                'base_score': base_score,
                'achievement_score': achievement_score,
                'spelling_penalty': spelling_penalty,
                'grammar_penalty': grammar_penalty,
                'spelling_details': {
                    'count': spell_grammar['spelling_errors'],
                    'errors': spell_grammar['errors'][:20],
                    'points_deducted': spelling_penalty
                },
                'grammar_details': {
                    'count': spell_grammar['grammar_issues'],
                    'issues': [e for e in spell_grammar['errors'] if 'grammar' in e.lower() or 'space' in e.lower()][:20],
                    'points_deducted': grammar_penalty
                },
                'achievement_details': {
                    'count': achievements['count'],
                    'achievements': achievements['achievements'][:20],
                    'points_added': achievement_score
                }
            }
        }
    
    def action_run_ats_analysis(self):
        """Run complete ATS analysis on the CV"""
        self.ensure_one()
        
        if not self.cv_text:
            raise ValidationError(
                'CV text content is required for ATS analysis. '
                'Please upload and extract CV data first using the "Extract CV Data" button.'
            )
        
        _logger.info(f"Starting ATS analysis for candidate {self.id}")
        
        try:
            # Tier 1 Analysis: Content Interpretation
            tier1_results = self._analyze_ats_tier1(self.cv_text)
            
            # Tier 2 Analysis: Content Quality
            tier2_results = self._analyze_ats_tier2(self.cv_text)
            
            # Prepare recommendations
            recommendations = []
            
            # Tier 1 recommendations
            if tier1_results['missing_sections']:
                recommendations.append(
                    f"Add missing sections: {', '.join(tier1_results['missing_sections'])}"
                )
            if tier1_results['dates_found'] < 3:
                recommendations.append("Add more dates to experience and education sections")
            if len(tier1_results['keywords_found']) < 10:
                recommendations.append("Include more relevant keywords related to your field")
            
            # Tier 2 recommendations
            if tier2_results['spelling_errors'] > 0:
                recommendations.append(
                    f"Fix {tier2_results['spelling_errors']} spelling error(s)"
                )
            if tier2_results['grammar_issues'] > 0:
                recommendations.append(
                    f"Fix {tier2_results['grammar_issues']} grammar issue(s)"
                )
            if tier2_results['achievements_count'] < 3:
                recommendations.append(
                    "Add more quantifiable achievements with numbers and metrics"
                )
            
            if not recommendations:
                recommendations.append("Resume looks good! Keep up the great work.")
            
            # Prepare analysis details JSON
            analysis_details = {
                'tier1': tier1_results,
                'tier2': tier2_results,
                'analysis_date': fields.Datetime.now().isoformat(),
            }
            
            # Update fields - use safe write to handle missing columns
            update_vals = {
                'ats_score_tier1': tier1_results['score'],
                'ats_score_tier2': tier2_results['score'],
                'ats_interpretable_content_pct': tier1_results['interpretable_pct'],
                'ats_spelling_errors': tier2_results['spelling_errors'],
                'ats_grammar_errors': tier2_results['grammar_issues'],
                'ats_quantifiable_achievements': tier2_results['achievements_count'],
                'ats_analysis_date': fields.Datetime.now(),
                'ats_analysis_details': json.dumps(analysis_details, indent=2),
                'ats_keywords_found': ', '.join(tier1_results['keywords_found'][:30]),
                'ats_missing_sections': ', '.join(tier1_results['missing_sections']),
                'ats_recommendations': '\n'.join([f"• {rec}" for rec in recommendations]),
            }
            
            # Add new fields only if they exist in the model (after module upgrade)
            model_fields = self._fields.keys()
            if 'ats_tier1_breakdown' in model_fields:
                update_vals['ats_tier1_breakdown'] = tier1_results.get('breakdown_text', '')
            if 'ats_tier2_breakdown' in model_fields:
                update_vals['ats_tier2_breakdown'] = tier2_results.get('breakdown_text', '')
            if 'ats_issues_found' in model_fields:
                update_vals['ats_issues_found'] = tier2_results.get('issues_text', 'No issues found.')
            if 'ats_achievements_list' in model_fields:
                update_vals['ats_achievements_list'] = tier2_results.get('achievements_text', 'No achievements found.')
            
            # Write with error handling in case columns don't exist in DB yet
            try:
                self.write(update_vals)
            except Exception as e:
                # If new fields cause error, write without them
                if 'ats_tier1_breakdown' in str(e) or 'ats_tier2_breakdown' in str(e) or 'ats_issues_found' in str(e) or 'ats_achievements_list' in str(e):
                    _logger.warning("New ATS fields not available in database yet. Please upgrade the module.")
                    # Remove new fields and write again
                    safe_vals = {k: v for k, v in update_vals.items() 
                                if k not in ['ats_tier1_breakdown', 'ats_tier2_breakdown', 'ats_issues_found', 'ats_achievements_list']}
                    self.write(safe_vals)
                else:
                    raise
            
            _logger.info(
                f"ATS analysis completed: Tier1={tier1_results['score']:.1f}, "
                f"Tier2={tier2_results['score']:.1f}, Overall={self.ats_overall_score:.1f}"
            )
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'ATS Analysis Complete',
                    'message': f'ATS Score: {self.ats_overall_score:.1f}/100\n'
                              f'Tier 1 (Interpretation): {tier1_results["score"]:.1f}/100\n'
                              f'Tier 2 (Quality): {tier2_results["score"]:.1f}/100',
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            _logger.error(f"Error running ATS analysis: {e}", exc_info=True)
            raise ValidationError(f'Error running ATS analysis: {str(e)}')

