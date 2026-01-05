# -*- coding: utf-8 -*-

from odoo import models, fields, api
from ..utils.language_detector import LanguageDetector


class ResumeAgentSettings(models.Model):
    _name = 'resume.agent.settings'
    _description = 'Resume Follow-Up Agent Settings'
    _rec_name = 'agent_name'

    agent_name = fields.Char(
        string='Agent Name',
        required=True,
        default='Techvootbot',
        help='Name of the AI agent'
    )
    company_name = fields.Char(
        string='Company Name',
        required=True,
        default='Techvoot Solution',
        help='Company name to use in conversations'
    )
    default_job_title = fields.Char(
        string='Default Job Title',
        default='WordPress Developer',
        help='Default job title for conversations'
    )
    
    # Conversation settings
    conversation_mode = fields.Selection([
        ('text', 'Text'),
        ('voice', 'Voice')
    ], string='Conversation Mode', default='text', required=True)
    
    temperature = fields.Float(
        string='Response Temperature',
        default=0.7,
        help='Higher values make responses more creative, lower values make them more focused (0.0 to 1.0)'
    )
    
    # Audio settings (for voice mode)
    voice_gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female')
    ], string='Voice Gender', default='female')
    audio_timeout = fields.Integer(
        string='Audio Timeout (seconds)',
        default=5,
        help='Timeout for audio input'
    )
    silence_threshold = fields.Integer(
        string='Silence Threshold (ms)',
        default=400,
        help='Threshold for detecting silence'
    )
    
    # Conversation flow settings
    max_conversation_length = fields.Integer(
        string='Max Conversation Length',
        default=50,
        help='Maximum number of messages in a conversation'
    )
    response_timeout = fields.Integer(
        string='Response Timeout (seconds)',
        default=30,
        help='Timeout for agent response'
    )
    
    # Telephony configuration
    telephony_config_id = fields.Many2one(
        'resume.telephony.config',
        string='Telephony Configuration',
        help='Telephony provider configuration for automated calls'
    )
    
    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )
    
    active = fields.Boolean(string='Active', default=True)
    
    # Dynamic conversation questions
    question_ids = fields.One2many(
        'resume.conversation.question',
        'agent_settings_id',
        string='Conversation Questions',
        help='Define the conversation flow with dynamic questions'
    )

    @api.model
    def get_default_settings(self):
        """Get default agent settings"""
        settings = self.search([('active', '=', True)], limit=1)
        if not settings:
            settings = self.create({
                'agent_name': 'Techvootbot',
                'company_name': self.env.company.name or 'Techvoot Solution',
                'default_job_title': 'WordPress Developer',
            })
        return settings

    def get_conversation_flow(self, preferred_language=None):
        """
        Get conversation flow steps from dynamic questions with language detection
        
        Args:
            preferred_language: Optional language code (gu, hi, en, etc.) to use for translation
        """
        if self.question_ids:
            # Use dynamic questions
            flow = []
            lang_detector = LanguageDetector()
            
            for question in self.question_ids.filtered(lambda q: q.active):
                message = question.message
                
                # If it's a greeting step, add language preference message
                if question.step_type == 'greeting':
                    # Check if message already contains language preference
                    if 'prefer' not in message.lower() and 'language' not in message.lower():
                        # Add language preference to greeting
                        message = f"{message} Please note that we prefer to conduct this conversation in English, but if you're more comfortable speaking in another language (such as Gujarati, Hindi, or any other language), please feel free to do so, and I'll continue the conversation in the language you prefer."
                
                # Translate message if preferred language is specified
                if preferred_language and preferred_language != 'auto':
                    message = lang_detector.translate_question(message, preferred_language)
                
                flow.append({
                    "step": question.step_type,
                    "step_type": question.step_type,
                    "message": message,
                    "expected_response": question.step_type,
                    "collect_field": question.collect_field if question.collect_field else None,
                    "field_label": question.field_label or (question.collect_field.replace('_', ' ').title() if question.collect_field else ''),
                    "sequence": question.sequence,
                    "language_detection": question.step_type == 'greeting'  # Enable detection after greeting
                })
            # Sort by sequence
            flow.sort(key=lambda x: x.get('sequence', 999))
            return flow
        else:
            # Return default flow if no questions defined
            return self._get_default_conversation_flow(preferred_language=preferred_language)
    
    def _get_default_conversation_flow(self, preferred_language=None):
        """
        Get default conversation flow (fallback)
        
        Args:
            preferred_language: Optional language code (gu, hi, en, etc.) to use for translation
        """
        # Initialize language detector for greeting message
        lang_detector = LanguageDetector()
        greeting_message = lang_detector.get_greeting_message(
            'en',  # Start in English
            '{candidate_name}',
            self.agent_name,
            self.company_name
        )
        
        # Translate greeting if preferred language is specified
        if preferred_language and preferred_language != 'auto':
            greeting_message = lang_detector.translate_question(greeting_message, preferred_language)
        
        return [
            {
                "step": "greeting",
                "step_type": "greeting",
                "message": greeting_message,
                "expected_response": "greeting_confirmation",
                "collect_field": None,
                "language_detection": True  # Enable language detection for this step
            },
            {
                "step": "purpose",
                "step_type": "purpose",
                "message": lang_detector.translate_question(
                    f"I'm calling to follow up on your resume submission for the {self.default_job_title} position. Is now a good time to talk?",
                    preferred_language or 'en'
                ),
                "expected_response": "time_confirmation",
                "collect_field": None
            },
            {
                "step": "explanation",
                "step_type": "explanation",
                "message": lang_detector.translate_question(
                    "Great! I need to gather a few more pieces of information to complete your application. This will help us move forward in the recruitment process. Are you comfortable proceeding?",
                    preferred_language or 'en'
                ),
                "expected_response": "proceed_confirmation",
                "collect_field": None
            },
            {
                "step": "question",
                "step_type": "question",
                "message": lang_detector.translate_question(
                    "Could you please give us a brief introduction about yourself?",
                    preferred_language or 'en'
                ),
                "expected_response": "introduction",
                "collect_field": "introduction"
            },
            {
                "step": "question",
                "step_type": "question",
                "message": lang_detector.translate_question(
                    "Thank you. May I know your current position?",
                    preferred_language or 'en'
                ),
                "expected_response": "current_position",
                "collect_field": "current_position"
            },
            {
                "step": "question",
                "step_type": "question",
                "message": lang_detector.translate_question(
                    "What is your current salary?",
                    preferred_language or 'en'
                ),
                "expected_response": "current_salary",
                "collect_field": "current_salary"
            },
            {
                "step": "question",
                "step_type": "question",
                "message": lang_detector.translate_question(
                    "What would be your expected salary for this role?",
                    preferred_language or 'en'
                ),
                "expected_response": "expected_salary",
                "collect_field": "expected_salary"
            },
            {
                "step": "question",
                "step_type": "question",
                "message": lang_detector.translate_question(
                    "What is your notice period with your current employer?",
                    preferred_language or 'en'
                ),
                "expected_response": "notice_period",
                "collect_field": "notice_period"
            },
            {
                "step": "closing",
                "step_type": "closing",
                "message": lang_detector.translate_question(
                    "Thank you for providing these details. This information helps us proceed with your application. If we need any more information, we'll be in touch. Have a fantastic day!",
                    preferred_language or 'en'
                ),
                "expected_response": "closing",
                "collect_field": None
            }
        ]
    
    def create_default_questions(self):
        """Create default questions for agent settings"""
        if self.question_ids:
            # Questions already exist, skip
            return
        
        # Initialize language detector for greeting message
        lang_detector = LanguageDetector()
        greeting_message = lang_detector.get_greeting_message(
            'en',  # Start in English
            '{candidate_name}',
            self.agent_name,
            self.company_name
        )
        
        default_questions = [
            {'sequence': 10, 'step_type': 'greeting', 'message': greeting_message, 'collect_field': '', 'field_label': ''},
            {'sequence': 20, 'step_type': 'purpose', 'message': f'I\'m calling to follow up on your resume submission for the {{job_title}} position. Is now a good time to talk?', 'collect_field': '', 'field_label': ''},
            {'sequence': 30, 'step_type': 'explanation', 'message': 'Great! I need to gather a few more pieces of information to complete your application. This will help us move forward in the recruitment process. Are you comfortable proceeding?', 'collect_field': '', 'field_label': ''},
            {'sequence': 40, 'step_type': 'question', 'message': 'Could you please give us a brief introduction about yourself?', 'collect_field': 'introduction', 'field_label': 'Introduction'},
            {'sequence': 50, 'step_type': 'question', 'message': 'Thank you. May I know your current position?', 'collect_field': 'current_position', 'field_label': 'Current Position'},
            {'sequence': 60, 'step_type': 'question', 'message': 'What is your current salary?', 'collect_field': 'current_salary', 'field_label': 'Current Salary'},
            {'sequence': 70, 'step_type': 'question', 'message': 'What would be your expected salary for this role?', 'collect_field': 'expected_salary', 'field_label': 'Expected Salary'},
            {'sequence': 80, 'step_type': 'question', 'message': 'What is your notice period with your current employer?', 'collect_field': 'notice_period', 'field_label': 'Notice Period'},
            {'sequence': 90, 'step_type': 'closing', 'message': 'Thank you for providing these details. This information helps us proceed with your application. If we need any more information, we\'ll be in touch. Have a fantastic day!', 'collect_field': '', 'field_label': ''},
        ]
        
        for q_data in default_questions:
            self.env['resume.conversation.question'].create({
                'agent_settings_id': self.id,
                'sequence': q_data['sequence'],
                'step_type': q_data['step_type'],
                'message': q_data['message'],
                'collect_field': q_data.get('collect_field', ''),
                'field_label': q_data.get('field_label', ''),
            })

