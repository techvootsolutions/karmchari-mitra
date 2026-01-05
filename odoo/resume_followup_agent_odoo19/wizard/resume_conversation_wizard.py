# -*- coding: utf-8 -*-

import json
import sys
import os
import logging
from datetime import datetime, timedelta
from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Add agents and services directories to path
base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
agents_path = os.path.join(base_path, 'agents')
services_path = os.path.join(base_path, 'services')
if os.path.exists(agents_path) and agents_path not in sys.path:
    sys.path.insert(0, base_path)
if os.path.exists(services_path) and services_path not in sys.path:
    sys.path.insert(0, base_path)

try:
    from agents.agent_factory import AgentFactory
    from agents.phone_agent import PhoneAgent
    AGENT_AVAILABLE = True
except (ImportError, Exception) as e:
    AGENT_AVAILABLE = False

try:
    from services.telephony_service import TelephonyService
    from services.ai_call_service import AICallService
    SERVICES_AVAILABLE = True
except (ImportError, Exception) as e:
    SERVICES_AVAILABLE = False


class ResumeConversationWizard(models.TransientModel):
    _name = 'resume.conversation.wizard'
    _description = 'Resume Phone Call Wizard'

    candidate_id = fields.Many2one(
        'resume.candidate',
        string='Candidate',
        required=True,
        readonly=True
    )
    candidate_name = fields.Char(string='Candidate Name', readonly=True)
    candidate_phone = fields.Char(string='Phone Number', readonly=True)
    position = fields.Char(string='Position', readonly=True)
    
    # Agent settings
    agent_settings_id = fields.Many2one(
        'resume.agent.settings',
        string='Agent Settings',
        required=True,
        help='Select agent settings to use for this call'
    )
    agent_name = fields.Char(string='Agent Name', related='agent_settings_id.agent_name', readonly=False, store=True)
    company_name = fields.Char(string='Company Name', related='agent_settings_id.company_name', readonly=True)
    job_title = fields.Char(string='Job Title', required=True)
    
    # Telephony settings
    telephony_config_id = fields.Many2one(
        'resume.telephony.config',
        string='Telephony Configuration',
        help='Telephony provider configuration for automated calls'
    )
    use_ai_agent = fields.Boolean(
        string='Use AI Agent',
        default=True,
        help='Enable AI agent to automatically place and handle calls'
    )
    
    # Dynamic conversation questions (stored as JSON)
    conversation_questions = fields.Text(
        string='Conversation Questions',
        readonly=True,
        help='JSON formatted conversation questions'
    )
    
    # Dynamic collected information (stored as JSON)
    collected_info_json = fields.Text(
        string='Collected Information (JSON)',
        readonly=True,
        help='JSON formatted collected information'
    )
    
    # Phone call information
    call_start_time = fields.Datetime(string='Call Start Time', default=fields.Datetime.now)
    call_end_time = fields.Datetime(string='Call End Time')
    duration = fields.Float(string='Duration (minutes)', compute='_compute_duration', store=False)
    call_duration_display = fields.Char(
        string='Call Duration',
        compute='_compute_call_duration_display',
        store=False,
        help='Formatted call duration (HH:MM:SS)'
    )
    
    # Call tracking
    call_id = fields.Char(string='Call ID', help='OmniDimension call identifier')
    call_sid = fields.Char(string='Call SID', help='Telephony provider call identifier')
    conversation_record_id = fields.Many2one(
        'resume.conversation',
        string='Conversation Record',
        help='Linked conversation record created when call started'
    )
    
    # Collected information from phone call (dynamic fields stored in collected_info_json)
    # Common fields for backward compatibility
    introduction = fields.Text(string='Introduction', help='Brief introduction about the candidate')
    current_position = fields.Char(string='Current Position')
    current_salary = fields.Char(string='Current Salary')
    expected_salary = fields.Char(string='Expected Salary')
    notice_period = fields.Char(string='Notice Period')
    
    # Call notes and quality
    notes = fields.Text(string='Call Notes', help='Additional notes from the phone call')
    call_quality = fields.Integer(
        string='Call Quality',
        default=0,
        help='Quality rating from 0 to 5'
    )
    
    # Status
    call_status = fields.Selection([
        ('not_started', 'Not Started'),
        ('in_progress', 'Call In Progress'),
        ('completed', 'Call Completed')
    ], string='Call Status', default='not_started')
    
    # Phone agent instance (stored as JSON)
    agent_data = fields.Text(string='Agent Data', readonly=True, help='Internal agent state')
    
    # Language selection
    preferred_language = fields.Selection([
        ('auto', 'Auto Detect'),
        ('en', 'English'),
        ('gu', 'Gujarati'),
        ('hi', 'Hindi'),
        ('mr', 'Marathi'),
        ('ta', 'Tamil'),
        ('te', 'Telugu'),
        ('kn', 'Kannada'),
        ('ml', 'Malayalam'),
        ('bn', 'Bengali'),
        ('pa', 'Punjabi'),
    ], string='Preferred Language', default='auto', 
       help='Select language for conversation. "Auto Detect" will detect from candidate response.')

    @api.depends('call_start_time', 'call_end_time')
    def _compute_duration(self):
        """Compute call duration in minutes"""
        for record in self:
            if record.call_start_time and record.call_end_time:
                delta = record.call_end_time - record.call_start_time
                record.duration = delta.total_seconds() / 60.0
            elif record.call_start_time and record.call_status == 'in_progress':
                # Calculate live duration if call is in progress
                delta = fields.Datetime.now() - record.call_start_time
                record.duration = delta.total_seconds() / 60.0
            else:
                record.duration = 0.0
    
    @api.depends('call_start_time', 'call_end_time', 'call_status')
    def _compute_call_duration_display(self):
        """Compute formatted call duration display (HH:MM:SS)"""
        for record in self:
            if record.call_start_time:
                if record.call_end_time:
                    delta = record.call_end_time - record.call_start_time
                elif record.call_status == 'in_progress':
                    # For live calls, calculate from current time
                    delta = fields.Datetime.now() - record.call_start_time
                else:
                    record.call_duration_display = '00:00:00'
                    continue
                
                total_seconds = int(delta.total_seconds())
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                seconds = total_seconds % 60
                record.call_duration_display = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            else:
                record.call_duration_display = '00:00:00'
    
    def _get_call_duration_live(self):
        """Get live call duration for JavaScript updates"""
        self.ensure_one()
        if self.call_start_time and self.call_status == 'in_progress':
            delta = fields.Datetime.now() - self.call_start_time
            total_seconds = int(delta.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return '00:00:00'

    def _get_conversation_questions(self):
        """Get conversation questions from agent settings or wizard with language translation"""
        if self.conversation_questions:
            try:
                flow = json.loads(self.conversation_questions)
            except (json.JSONDecodeError, TypeError):
                flow = []
        else:
            # Load from agent settings with language preference
            if self.agent_settings_id:
                preferred_lang = self.preferred_language if self.preferred_language != 'auto' else None
                flow = self.agent_settings_id.get_conversation_flow(preferred_language=preferred_lang)
            else:
                flow = []
        
        return flow
    
    def _save_conversation_questions(self, questions):
        """Save conversation questions to wizard"""
        self.conversation_questions = json.dumps(questions)
    
    def _get_collected_info_dict(self):
        """Get collected information as dictionary"""
        if self.collected_info_json:
            try:
                return json.loads(self.collected_info_json)
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Build from individual fields for backward compatibility
        collected = {}
        if self.introduction:
            collected['introduction'] = self.introduction
        if self.current_position:
            collected['current_position'] = self.current_position
        if self.current_salary:
            collected['current_salary'] = self.current_salary
        if self.expected_salary:
            collected['expected_salary'] = self.expected_salary
        if self.notice_period:
            collected['notice_period'] = self.notice_period
        
        return collected
    
    def _save_collected_info(self, collected_info):
        """Save collected information to wizard"""
        self.collected_info_json = json.dumps(collected_info)
        # Also update individual fields for backward compatibility
        self.introduction = collected_info.get('introduction', '')
        self.current_position = collected_info.get('current_position', '')
        self.current_salary = collected_info.get('current_salary', '')
        self.expected_salary = collected_info.get('expected_salary', '')
        self.notice_period = collected_info.get('notice_period', '')

    def _initialize_phone_agent(self, restore_state=False):
        """Initialize phone agent with current settings"""
        if not AGENT_AVAILABLE:
            return None
        
        try:
            settings = {
                'agent_name': self.agent_name,
                'company_name': self.company_name,
                'job_title': self.job_title,
            }
            
            # Create phone agent
            agent = AgentFactory.create_agent('phone', settings)
            
            # Load dynamic questions
            questions_list = self._get_conversation_questions()
            if questions_list:
                # Convert to dict format for agent
                questions_dict = {}
                for idx, q in enumerate(questions_list):
                    step_type = q.get('step', q.get('step_type', 'question'))
                    if step_type == 'greeting':
                        questions_dict['question_greeting'] = q.get('message', '')
                    else:
                        # Dynamic questions
                        collect_field = q.get('collect_field', '')
                        if collect_field:
                            questions_dict[f'question_{collect_field}'] = q.get('message', '')
                
                agent.load_conversation_flow(questions_dict)
            
            # Restore state if requested and agent_data exists
            if restore_state and self.agent_data:
                try:
                    agent_data = json.loads(self.agent_data)
                    agent.conversation_history = agent_data.get('conversation_history', [])
                    agent.collected_info = agent_data.get('collected_info', {})
                    agent.current_step = agent_data.get('current_step', 0)
                    # Use call times from wizard if available
                    if self.call_start_time:
                        agent.call_start_time = self.call_start_time
                    if self.call_end_time:
                        agent.call_end_time = self.call_end_time
                except Exception:
                    pass  # Continue if state restoration fails
            
            return agent
        except Exception as e:
            # If agent initialization fails, continue without it
            return None

    @api.onchange('agent_settings_id')
    def _onchange_agent_settings(self):
        """Update fields when agent settings change"""
        if self.agent_settings_id:
            self.agent_name = self.agent_settings_id.agent_name
            self.company_name = self.agent_settings_id.company_name
            # Update job_title from agent settings, but allow override with candidate's position if available
            if self.agent_settings_id.default_job_title:
                self.job_title = self.agent_settings_id.default_job_title
            elif self.position:
                self.job_title = self.position
            
            # Load dynamic questions from agent settings
            flow = self.agent_settings_id.get_conversation_flow()
            if flow:
                self._save_conversation_questions(flow)

    @api.model
    def default_get(self, fields_list):
        """Set default values"""
        res = super(ResumeConversationWizard, self).default_get(fields_list)
        
        # Get agent settings
        settings = self.env['resume.agent.settings'].get_default_settings()
        
        # Initialize with candidate information
        if 'active_id' in self.env.context:
            candidate = self.env['resume.candidate'].browse(self.env.context['active_id'])
            res['candidate_id'] = candidate.id
            res['candidate_name'] = candidate.name
            res['candidate_phone'] = candidate.phone or 'Not provided'
            res['position'] = candidate.position
        
        # Set agent settings
        res['agent_settings_id'] = settings.id
        res['agent_name'] = settings.agent_name
        res['company_name'] = settings.company_name
        res['job_title'] = settings.default_job_title or res.get('position', '')
        res['call_start_time'] = fields.Datetime.now()
        
        # Set telephony config from agent settings
        if settings.telephony_config_id:
            res['telephony_config_id'] = settings.telephony_config_id.id
            res['use_ai_agent'] = settings.telephony_config_id.use_ai_agent
        else:
            # Try to get default telephony config
            telephony_config = self.env['resume.telephony.config'].get_default_config()
            if telephony_config:
                res['telephony_config_id'] = telephony_config.id
                res['use_ai_agent'] = telephony_config.use_ai_agent
        
        # Load dynamic questions from agent settings
        flow = settings.get_conversation_flow()
        if flow:
            res['conversation_questions'] = json.dumps(flow)
        
        return res
    #
    # def action_start_call(self):
    #     """Initiate phone call and mark as started"""
    #     self.ensure_one()
    #
    #     # Validate and clean phone number first (outside try block so it's always available)
    #     if not self.candidate_phone or self.candidate_phone == 'Not provided':
    #         raise UserError('Phone number is required to make a call. Please ensure the candidate has a valid phone number.')
    #
    #     # Clean phone number (remove spaces, dashes, etc. but keep + for international)
    #     phone_number = self.candidate_phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '').replace('.', '').strip()
    #
    #     # Ensure phone number is not empty after cleaning
    #     if not phone_number:
    #         raise UserError('Invalid phone number. Please check the candidate\'s phone number.')
    #
    #     # Ensure phone number is in E.164 format (must start with +)
    #     # If it doesn't start with +, assume it's a local number and might need country code
    #     # For now, we'll require the user to provide the number with country code
    #     if not phone_number.startswith('+'):
    #         # Log warning but don't fail - let the API handle it
    #         _logger.warning(f"Phone number {phone_number} doesn't start with +. OmniDimension AI may require E.164 format (e.g., +1234567890)")
    #
    #     # Log the phone number being used (for debugging)
    #     _logger.info(f"Placing call to phone number: {phone_number}")
    #
    #     try:
    #         # Initialize phone agent
    #         agent = self._initialize_phone_agent()
    #         if agent:
    #             agent.start_call()
    #             # Store agent data
    #             agent_data = agent.get_conversation_data()
    #             self.agent_data = json.dumps(agent_data)
    #
    #         # Update call status first
    #         self.write({
    #             'call_status': 'in_progress',
    #             'call_start_time': fields.Datetime.now()
    #         })
    #     except Exception as e:
    #         # Log error but continue to try opening phone dialer
    #         # Still update call status even if agent fails
    #         try:
    #             self.write({
    #                 'call_status': 'in_progress',
    #                 'call_start_time': fields.Datetime.now()
    #             })
    #         except:
    #             pass
    #
    #     # Try to use telephony service if configured
    #     call_result = None
    #     use_telephony_service = False
    #
    #     if SERVICES_AVAILABLE and self.telephony_config_id and self.use_ai_agent:
    #         try:
    #             telephony_config = {
    #                 'provider_name': self.telephony_config_id.provider_name,
    #                 'account_sid': self.telephony_config_id.account_sid,
    #                 'auth_token': self.telephony_config_id.auth_token,
    #                 'phone_number': self.telephony_config_id.phone_number,
    #                 'enable_call_recording': self.telephony_config_id.enable_call_recording,
    #                 'api_endpoint': self.telephony_config_id.api_endpoint or 'https://api.omnidimension.ai/v1',
    #                 'agent_id': self.telephony_config_id.agent_id or '',
    #                 'voice_id': self.telephony_config_id.voice_id or '',
    #             }
    #
    #             telephony_service = TelephonyService(telephony_config)
    #
    #             # Get conversation flow for OmniDimension AI
    #             questions = self._get_conversation_questions()
    #             formatted_flow = []
    #             for q in questions:
    #                 formatted_flow.append({
    #                     'step_type': q.get('step_type', q.get('step', 'question')),
    #                     'message': q.get('message', ''),
    #                     'collect_field': q.get('collect_field', ''),
    #                     'field_label': q.get('field_label', ''),
    #                 })
    #
    #             call_params = {
    #                 'webhook_url': '',  # Can be configured for call handling
    #                 'status_callback': '',  # Can be configured for status updates
    #                 'conversation_flow': formatted_flow,
    #                 'candidate_name': self.candidate_name,
    #                 'agent_name': self.agent_name,
    #                 'company_name': self.company_name,
    #                 'job_title': self.job_title,
    #                 'record': self.telephony_config_id.enable_call_recording,
    #             }
    #
    #             call_result = telephony_service.make_call(phone_number, call_params)
    #
    #             if call_result and call_result.get('status') == 'initiated':
    #                 # Store call SID for tracking
    #                 call_sid = call_result.get('call_sid') or call_result.get('call_id', '')
    #                 if call_sid:
    #                     self.env['resume.conversation'].sudo().create({
    #                         'candidate_id': self.candidate_id.id,
    #                         'call_sid': call_sid,
    #                         'status': 'in_progress',
    #                     })
    #                 use_telephony_service = True
    #             elif call_result and call_result.get('status') == 'error':
    #                 # Check if it's a DNS error
    #                 error_msg = call_result.get('error', 'Unknown error occurred')
    #                 is_dns_error = any(keyword in error_msg.lower() for keyword in [
    #                     'dns', 'failed to resolve', 'name or service not known',
    #                     'nxdomain', 'cannot resolve domain'
    #                 ])
    #
    #                 if is_dns_error:
    #                     # DNS errors: Show clear error and don't fallback automatically
    #                     # User wants to use OmniDimension, so we should show the error
    #                     _logger.error(f"OmniDimension AI DNS error: {error_msg}")
    #                     detailed_error = (
    #                         f"❌ Cannot connect to OmniDimension AI API\n\n"
    #                         f"The API endpoint '{self.telephony_config_id.api_endpoint}' cannot be reached.\n\n"
    #                         f"🔍 To fix this:\n"
    #                         f"1. Log into your OmniDimension AI dashboard\n"
    #                         f"2. Go to Settings → API or Documentation section\n"
    #                         f"3. Find the correct API endpoint URL\n"
    #                         f"4. Update the 'API Endpoint' field in Telephony Configuration\n\n"
    #                         f"💡 The endpoint might be different from 'api.omnidimension.ai'\n"
    #                         f"   It could be a different subdomain or custom URL provided by OmniDimension.\n\n"
    #                         f"Current endpoint: {self.telephony_config_id.api_endpoint}"
    #                     )
    #                     raise UserError(detailed_error)
    #                 else:
    #                     # Other errors: show to user
    #                     _logger.error(f"OmniDimension AI call error: {error_msg}")
    #                     raise UserError(f'Failed to initiate OmniDimension AI call: {error_msg}')
    #         except UserError:
    #             # Re-raise UserError to show to user (but this shouldn't happen now)
    #             raise
    #         except Exception as e:
    #             # Log error and fall back to tel: protocol if telephony service fails
    #             _logger.error(f"Telephony service error: {e}", exc_info=True)
    #             use_telephony_service = False
    #             # Show error to user but allow fallback
    #             error_msg = str(e)
    #             if len(error_msg) > 100:
    #                 error_msg = error_msg[:100] + "..."
    #             # Note: We'll show a warning but still allow tel: fallback
    #
    #     # If telephony service was used successfully, return success message
    #     if use_telephony_service and call_result and call_result.get('status') == 'initiated':
    #         call_sid = call_result.get('call_sid') or call_result.get('call_id', 'N/A')
    #         return {
    #             'type': 'ir.actions.client',
    #             'tag': 'display_notification',
    #             'params': {
    #                 'title': 'Call Initiated',
    #                 'message': f'AI agent is placing call to {phone_number}. Call ID: {call_sid}',
    #                 'type': 'success',
    #                 'sticky': False,
    #             }
    #         }
    #
    #     # If telephony service failed but we have an error message, show it
    #     if call_result and call_result.get('status') == 'error' and not use_telephony_service:
    #         error_msg = call_result.get('error', 'Unknown error')
    #         # Truncate long error messages for notification
    #         if len(error_msg) > 200:
    #             error_msg = error_msg[:200] + "..."
    #
    #         # Check if it's a DNS error for more specific message
    #         is_dns_error = any(keyword in error_msg.lower() for keyword in [
    #             'dns', 'failed to resolve', 'name or service not known',
    #             'nxdomain', 'cannot resolve domain'
    #         ])
    #
    #         if is_dns_error:
    #             notification_msg = (
    #                 "AI call service unavailable (DNS error). "
    #                 "Opening phone dialer for manual call. "
    #                 "Please verify the API endpoint URL in Telephony Configuration."
    #             )
    #         else:
    #             notification_msg = f"AI call failed: {error_msg[:100]}. Opening phone dialer for manual call."
    #
    #         # Show notification but continue to fallback
    #         # Note: We can't show notification and return action at same time,
    #         # so we'll just proceed to tel: fallback
    #         _logger.info(f"AI call failed, falling back to manual dialer: {error_msg}")
    #
    #     # Always fall back to tel: protocol (opens phone dialer)
    #     # This works on mobile devices and some desktop browsers
    #     # Note: On desktop, this may open a VoIP client or show a message
    #     # Using 'new' target to open in new window/tab
    #     return {
    #         'type': 'ir.actions.act_url',
    #         'url': f'tel:{phone_number}',
    #         'target': 'new',
    #     }


    def action_start_call(self):
        """Initiate phone call and mark as started"""
        self.ensure_one()

        # Validate and clean phone number first (outside try block so it's always available)
        if not self.candidate_phone or self.candidate_phone == 'Not provided':
            raise UserError('Phone number is required to make a call. Please ensure the candidate has a valid phone number.')

        # Clean phone number (remove spaces, dashes, etc. but keep + for international)
        phone_number = self.candidate_phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '').replace('.', '').strip()

        # Ensure phone number is not empty after cleaning
        if not phone_number:
            raise UserError('Invalid phone number. Please check the candidate\'s phone number.')

        # Ensure phone number is in E.164 format (must start with +)
        # If it doesn't start with +, assume it's a local number and might need country code
        # For now, we'll require the user to provide the number with country code
        if not phone_number.startswith('+'):
            # Log warning but don't fail - let the API handle it
            _logger.warning(f"Phone number {phone_number} doesn't start with +. OmniDimension AI may require E.164 format (e.g., +1234567890)")

        # Log the phone number being used (for debugging)
        _logger.info(f"Placing call to phone number: {phone_number}")

        # Update call status immediately (before making call) for faster UI response
        # This makes the UI update instantly while call is being initiated in background
        self.write({
            'call_status': 'in_progress',
            'call_start_time': fields.Datetime.now()
        })
        
        # Initialize phone agent in background (non-blocking) - don't wait for it
        # This improves perceived speed
        try:
            agent = self._initialize_phone_agent()
            if agent:
                agent.start_call()
                agent_data = agent.get_conversation_data()
                self.agent_data = json.dumps(agent_data)
        except Exception as e:
            _logger.warning(f"Agent initialization failed (non-critical): {e}")
            pass  # Continue even if agent fails - not critical for call initiation

        # Try to use telephony service if configured
        call_result = None
        use_telephony_service = False

        # Check prerequisites for AI call
        if not SERVICES_AVAILABLE:
            _logger.warning("Telephony services not available. Check if services/telephony_service.py exists.")
        if not self.telephony_config_id:
            _logger.warning("Telephony configuration not set. Please select a telephony configuration.")
        if not self.use_ai_agent:
            _logger.warning("AI Agent is disabled. Enable 'Use AI Agent' to make calls via OmniDimension.")

        if SERVICES_AVAILABLE and self.telephony_config_id and self.use_ai_agent:
            try:
                telephony_config = {
                    'provider_name': self.telephony_config_id.provider_name,
                    'account_sid': self.telephony_config_id.account_sid,
                    'auth_token': self.telephony_config_id.auth_token,
                    'phone_number': self.telephony_config_id.phone_number,
                    'enable_call_recording': self.telephony_config_id.enable_call_recording,
                    'api_endpoint': self.telephony_config_id.api_endpoint or 'https://api.omnidim.io/api/v1',
                    'agent_id': self.telephony_config_id.agent_id or '',
                    'voice_id': self.telephony_config_id.voice_id or '',
                }

                telephony_service = TelephonyService(telephony_config)

                # Get conversation flow for OmniDimension AI
                questions = self._get_conversation_questions()
                formatted_flow = []
                for q in questions:
                    formatted_flow.append({
                        'step_type': q.get('step_type', q.get('step', 'question')),
                        'message': q.get('message', ''),
                        'collect_field': q.get('collect_field', ''),
                        'field_label': q.get('field_label', ''),
                    })

                # Build webhook URL for automatic data sync after call ends
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', 'http://localhost:8069')
                webhook_url = f"{base_url}/resume_followup/webhook/call_status"
                
                # Add language preference to call params
                preferred_lang = self.preferred_language if self.preferred_language != 'auto' else None
                
                call_params = {
                    'webhook_url': webhook_url,  # Auto-sync data after call ends
                    'status_callback': webhook_url,  # Status updates
                    'conversation_flow': formatted_flow,
                    'candidate_name': self.candidate_name,
                    'agent_name': self.agent_name,
                    'company_name': self.company_name,
                    'job_title': self.job_title,
                    'record': self.telephony_config_id.enable_call_recording,
                    'from_number_name': self.agent_name or 'Recruitment',  # Set caller ID name (removes spam label)
                    'preferred_language': preferred_lang,  # Language preference for AI
                    'enable_language_detection': True,  # Enable automatic language detection
                }
                _logger.info(f"Making call with params (webhook: {webhook_url})")
                # Make call asynchronously if possible, but for now make it faster by reducing logging
                call_result = telephony_service.make_call(phone_number, call_params)
                _logger.info(f"Call initiated: status={call_result.get('status')}, call_id={call_result.get('call_id')}")

                if call_result:
                    _logger.info(f"Call result received: status={call_result.get('status')}, call_id={call_result.get('call_id')}, error={call_result.get('error')}")
                    
                    if call_result.get('status') == 'initiated':
                        # Store call data for tracking
                        call_id = call_result.get('call_id') or call_result.get('call_sid') or call_result.get('id', '')
                        call_sid = call_result.get('call_sid') or call_id
                        
                        _logger.info(f"Call initiated successfully. Call ID: {call_id}, Call SID: {call_sid}")
                        
                        if call_id:
                            # Store call_id and call_sid in wizard for later use
                            self.write({
                                'call_id': call_id,
                                'call_sid': call_sid,
                            })
                            
                            # Create conversation record with all call details
                            conversation_vals = {
                                'candidate_id': self.candidate_id.id,
                                'call_id': call_id,
                                'call_sid': call_sid,
                                'call_request_id': call_result.get('request_id', ''),
                                'phone_number': self.candidate_phone,
                                'to_number': phone_number,
                                'from_number': self.telephony_config_id.phone_number or '' if self.telephony_config_id else '',
                                'bot_name': self.agent_name or 'Resume Follow-Up Agent',
                                'call_direction': 'outbound',
                                'status': 'in_progress',
                                'agent_name': self.agent_name,
                                'company_name': self.company_name,
                                'job_title': self.job_title,
                                'timestamp': fields.Datetime.now(),
                                'username': self.env.user.name or '',
                            }
                            conversation = self.env['resume.conversation'].sudo().create(conversation_vals)
                            # Link conversation to wizard
                            self.write({
                                'conversation_record_id': conversation.id
                            })
                        use_telephony_service = True
                    elif call_result.get('status') == 'error':
                        # Show error to user
                        error_msg = call_result.get('error', 'Unknown error occurred')
                        _logger.error(f"OmniDimension AI call error: {error_msg}")
                        raise UserError(f'Failed to initiate AI call: {error_msg}')
                    else:
                        # Unknown status
                        _logger.warning(f"Call result has unknown status: {call_result.get('status')}")
                        error_msg = call_result.get('error', f"Unknown call status: {call_result.get('status')}")
                        raise UserError(f'Failed to initiate AI call: {error_msg}')
                else:
                    _logger.error("No call result returned from telephony service")
                    raise UserError('Failed to initiate call: No response from telephony service')
            except UserError:
                # Re-raise UserError to show to user
                raise
            except Exception as e:
                # Log error and fall back to tel: protocol if telephony service fails
                _logger.error(f"Telephony service error: {e}", exc_info=True)
                use_telephony_service = False
                # Show error to user but allow fallback
                error_msg = str(e)
                if len(error_msg) > 100:
                    error_msg = error_msg[:100] + "..."
                # Note: We'll show a warning but still allow tel: fallback

        # If telephony service was used successfully, return success message and keep wizard open
        if use_telephony_service and call_result and call_result.get('status') == 'initiated':
            call_sid = call_result.get('call_sid') or call_result.get('call_id', 'N/A')
            # Return action to reload the wizard form to show the call interface
            # The wizard will automatically show the mobile call interface since call_status is now 'in_progress'
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'resume.conversation.wizard',
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
                'views': [(False, 'form')],
                'context': {
                    'default_res_id': self.id,
                }
            }
        
        # If telephony service was attempted but failed, show helpful error
        if not use_telephony_service:
            missing_items = []
            if not SERVICES_AVAILABLE:
                missing_items.append("Telephony services module")
            if not self.telephony_config_id:
                missing_items.append("Telephony Configuration")
            if not self.use_ai_agent:
                missing_items.append("AI Agent enabled")
            
            if missing_items:
                error_msg = f"Cannot make AI call. Missing: {', '.join(missing_items)}.\n\n"
                error_msg += "Please:\n"
                if not self.telephony_config_id:
                    error_msg += "1. Select a Telephony Configuration\n"
                if not self.use_ai_agent:
                    error_msg += "2. Enable 'Use AI Agent' checkbox\n"
                error_msg += "\nFalling back to phone dialer..."
                _logger.warning(error_msg)

        # If telephony service failed but we have an error message, show it
        if call_result and call_result.get('status') == 'error':
            error_msg = call_result.get('error', 'Unknown error')
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Call Failed',
                    'message': f'Failed to initiate AI call: {error_msg}. Falling back to phone dialer.',
                    'type': 'warning',
                    'sticky': True,
                }
            }

        # Always fall back to tel: protocol (opens phone dialer)
        # This works on mobile devices and some desktop browsers
        # Note: On desktop, this may open a VoIP client or show a message
        # Using 'new' target to open in new window/tab
        return {
            'type': 'ir.actions.act_url',
            'url': f'tel:{phone_number}',
            'target': 'new',
        }


    def action_end_call(self):
        """Mark call as ended and automatically save conversation with data sync"""
        self.ensure_one()
        
        # Update call end time immediately
        call_end_time = fields.Datetime.now()
        self.write({
            'call_status': 'completed',
            'call_end_time': call_end_time
        })
        
        # Update phone agent if available (non-blocking)
        if AGENT_AVAILABLE:
            try:
                agent = self._initialize_phone_agent(restore_state=True)
                if agent:
                    agent.end_call()
                    # Update collected info from agent
                    agent_data = agent.get_conversation_data()
                    collected = agent_data.get('collected_info', {})
                    if collected:
                        # Update collected info (dynamic)
                        self._save_collected_info(collected)
                    self.agent_data = json.dumps(agent_data)
            except Exception as e:
                _logger.warning(f"Agent update failed (non-critical): {e}")
        
        # Sync call data from OmniDimension API if call_id exists
        if self.call_id:
            try:
                # Find or create conversation record
                conversation = self.env['resume.conversation'].search([
                    ('call_id', '=', self.call_id)
                ], limit=1)
                
                if conversation:
                    # Sync data immediately
                    conversation.action_sync_call_data()
                    _logger.info(f"✅ Synced call data for conversation {conversation.id}")
                else:
                    # Will be created in action_save_call
                    _logger.info("Conversation will be created in save action")
            except Exception as e:
                _logger.warning(f"Auto-sync failed (will retry in save): {e}")
        
        # Automatically save conversation after call ends
        try:
            # Call action_save_call which returns an action dict to open the conversation
            save_action = self.action_save_call()
            
            # The save_action already opens the conversation, so we can return it directly
            if save_action and save_action.get('res_id'):
                # Sync again after save to ensure all data is captured
                try:
                    conversation = self.env['resume.conversation'].browse(save_action['res_id'])
                    if conversation.call_id:
                        conversation.action_sync_call_data()
                except:
                    pass
                return save_action
            else:
                # If save failed, show wizard with completed status
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'resume.conversation.wizard',
                    'res_id': self.id,
                    'view_mode': 'form',
                    'target': 'new',
                }
        except UserError as e:
            _logger.warning(f"Auto-save validation error: {e}")
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'resume.conversation.wizard',
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
            }
        except Exception as e:
            _logger.error(f"Error auto-saving conversation: {e}", exc_info=True)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Call Ended',
                    'message': f'Call has been ended. Please click "Save Call" to save the conversation. Error: {str(e)}',
                    'type': 'warning',
                    'sticky': True,
                }
            }

    def action_save_call(self):
        """Save the phone call conversation"""
        self.ensure_one()
        
        if not self.candidate_id:
            raise UserError('Candidate is required.')
        
        if not self.call_end_time:
            raise UserError('Please set the call end time before saving.')
        
        # Get collected information (dynamic)
        collected_info = self._get_collected_info_dict()
        
        # Get conversation questions (dynamic)
        questions = self._get_conversation_questions()
        
        # Format questions with actual values for transcript
        formatted_questions = []
        for q in questions:
            try:
                message = q.get('message', '')
                # Format message with placeholders
                formatted_message = message.format(
                    candidate_name=self.candidate_name,
                    agent_name=self.agent_name,
                    company_name=self.company_name,
                    job_title=self.job_title
                )
                formatted_questions.append({
                    'step_type': q.get('step', q.get('step_type', 'question')),
                    'message': formatted_message,
                    'collect_field': q.get('collect_field'),
                    'field_label': q.get('field_label', '')
                })
            except (KeyError, ValueError):
                # If formatting fails, use original message
                formatted_questions.append({
                    'step_type': q.get('step', q.get('step_type', 'question')),
                    'message': q.get('message', ''),
                    'collect_field': q.get('collect_field'),
                    'field_label': q.get('field_label', '')
                })
        
        # Generate transcript from notes, questions, and collected info
        transcript_parts = []
        transcript_parts.append("=== CONVERSATION FLOW ===\n")
        
        question_num = 1
        for q in formatted_questions:
            step_type = q.get('step_type', 'question')
            message = q.get('message', '')
            if step_type == 'greeting':
                transcript_parts.append(f"Greeting: {message}")
            elif step_type == 'purpose':
                transcript_parts.append(f"Purpose: {message}")
            elif step_type == 'explanation':
                transcript_parts.append(f"Explanation: {message}")
            elif step_type == 'closing':
                transcript_parts.append(f"Closing: {message}")
            else:
                # Question
                transcript_parts.append(f"Q{question_num}: {message}")
                question_num += 1
        
        transcript_parts.append("\n=== COLLECTED INFORMATION ===")
        if any(collected_info.values()):
            for key, value in collected_info.items():
                if value:
                    # Try to get field label from questions
                    field_label = key.replace('_', ' ').title()
                    for q in questions:
                        if q.get('collect_field') == key and q.get('field_label'):
                            field_label = q.get('field_label')
                            break
                    transcript_parts.append(f"- {field_label}: {value}")
        
        if self.notes:
            transcript_parts.append(f"\n=== CALL NOTES ===\n{self.notes}")
        
        transcript = "\n".join(transcript_parts) if transcript_parts else "No transcript available."
        
        # Perform AI analysis if available
        ai_analysis_data = {}
        if SERVICES_AVAILABLE and self.use_ai_agent:
            try:
                # Get telephony config for AI settings
                ai_config = {}
                if self.telephony_config_id:
                    ai_config = {
                        'ai_model': self.telephony_config_id.ai_model,
                        'ai_api_key': self.telephony_config_id.ai_api_key,
                        'ai_endpoint': self.telephony_config_id.ai_endpoint,
                    }
                else:
                    # Use default AI config
                    ai_config = {
                        'ai_model': 'openai',
                        'ai_api_key': '',
                        'ai_endpoint': '',
                    }
                
                ai_service = AICallService(ai_config)
                
                # Prepare call data for analysis
                call_data = {
                    'duration': self.duration,
                    'total_questions': len(questions),
                    'questions_answered': len([k for k, v in collected_info.items() if v]),
                    'avg_response_time': 0,  # Can be calculated from agent data if available
                }
                
                # Analyze the call
                ai_analysis_data = ai_service.analyze_call(transcript, call_data)
            except Exception as e:
                # Continue without AI analysis if it fails
                pass
        
        # Create conversation record with all fields matching Google Sheet structure
        conversation_vals = {
            'candidate_id': self.candidate_id.id,
            'agent_name': self.agent_name,
            'company_name': self.company_name,
            'job_title': self.job_title,
            'transcript': transcript,
            'duration': self.duration,
            'collected_info': json.dumps(collected_info),
            'brief_introduction': self.introduction or '',
            'introduction': self.introduction or '',
            'current_position': self.current_position or '',
            'current_salary': self.current_salary or '',
            'expected_salary': self.expected_salary or '',
            'notice_period': self.notice_period or '',
            'call_quality': self.call_quality,
            'notes': self.notes,
            'status': 'completed',
            'timestamp': self.call_start_time,
            'phone_number': self.candidate_phone or '',
            'to_number': self.candidate_phone or '',
            'from_number': self.telephony_config_id.phone_number or '' if self.telephony_config_id else '',
            'bot_name': self.agent_name or 'Resume Follow-Up Agent',
            'call_direction': 'outbound',
            'username': self.env.user.name or '',
        }
        
        # Add call_id and call_sid if available (from call initiation)
        if self.call_id:
            conversation_vals['call_id'] = self.call_id
        if self.call_sid:
            conversation_vals['call_sid'] = self.call_sid
        
        # Add summary if available from AI analysis
        if ai_analysis_data and ai_analysis_data.get('summary'):
            conversation_vals['summary'] = ai_analysis_data.get('summary', '')
        
        # Add sentiment (convert score to text)
        if ai_analysis_data and 'sentiment_score' in ai_analysis_data:
            sentiment_score = ai_analysis_data.get('sentiment_score', 0)
            if sentiment_score > 0.3:
                conversation_vals['sentiment'] = 'positive'
            elif sentiment_score < -0.3:
                conversation_vals['sentiment'] = 'negative'
            else:
                conversation_vals['sentiment'] = 'neutral'
        
        # Add AI analysis if available
        if ai_analysis_data:
            conversation_vals.update({
                'ai_analysis': ai_analysis_data.get('analysis_text', ''),
                'communication_score': ai_analysis_data.get('communication_score', 0.0),
                'sentiment_score': ai_analysis_data.get('sentiment_score', 0.0),
                'engagement_level': ai_analysis_data.get('engagement_level', 'medium'),
                'response_time_avg': ai_analysis_data.get('response_time_avg', 0.0),
                'clarity_score': ai_analysis_data.get('clarity_score', 0.0),
                'professionalism_score': ai_analysis_data.get('professionalism_score', 0.0),
                'interest_level': ai_analysis_data.get('interest_level', 'moderate'),
                'call_statistics': json.dumps(ai_analysis_data.get('statistics', {})),
            })
        
        # Check if conversation already exists (from call initiation)
        existing_conversation = None
        
        # First check if we have a linked conversation record
        if self.conversation_record_id:
            existing_conversation = self.conversation_record_id
        elif self.call_id or self.call_sid:
            # Try to find existing conversation by call_id or call_sid
            domain = []
            if self.call_id:
                domain = [('call_id', '=', self.call_id)]
            elif self.call_sid:
                domain = [('call_sid', '=', self.call_sid)]
            
            if domain:
                existing_conversation = self.env['resume.conversation'].search(domain, limit=1)
        
        if existing_conversation:
            # Update existing conversation with all collected data
            existing_conversation.write(conversation_vals)
            conversation = existing_conversation
            _logger.info(f"✅ Updated existing conversation {conversation.id} with call data")
        else:
            # Create new conversation
            conversation = self.env['resume.conversation'].create(conversation_vals)
            _logger.info(f"✅ Created new conversation {conversation.id}")
        
        # Auto-sync call data from OmniDimension if call_id exists (force sync)
        if conversation.call_id:
            try:
                # Force sync regardless of status to ensure data is captured
                sync_result = conversation.action_sync_call_data()
                _logger.info(f"✅ Auto-synced call data for conversation {conversation.id}")
                
                # Refresh conversation to get latest data
                conversation.invalidate_recordset(['call_recording_url', 'recording_url', 'transcript', 
                                                   'summary', 'sentiment', 'introduction', 'current_position',
                                                   'current_salary', 'expected_salary', 'notice_period', 
                                                   'duration', 'collected_info'])
                conversation.refresh()
                
                # Update wizard fields from synced conversation data
                if conversation.introduction:
                    self.introduction = conversation.introduction
                if conversation.current_position:
                    self.current_position = conversation.current_position
                if conversation.current_salary:
                    self.current_salary = conversation.current_salary
                if conversation.expected_salary:
                    self.expected_salary = conversation.expected_salary
                if conversation.notice_period:
                    self.notice_period = conversation.notice_period
                
                # Update candidate again with synced data
                candidate_updates = {}
                if conversation.introduction:
                    candidate_updates['introduction'] = conversation.introduction
                if conversation.current_position:
                    candidate_updates['current_position'] = conversation.current_position
                if conversation.current_salary:
                    candidate_updates['current_salary'] = conversation.current_salary
                if conversation.expected_salary:
                    candidate_updates['expected_salary'] = conversation.expected_salary
                if conversation.notice_period:
                    candidate_updates['notice_period'] = conversation.notice_period
                
                if candidate_updates:
                    self.candidate_id.write(candidate_updates)
                    _logger.info(f"✅ Updated candidate with synced data from conversation")
                    
            except Exception as e:
                _logger.warning(f"Auto-sync failed for conversation {conversation.id}: {e}", exc_info=True)
                # Don't fail the save if sync fails, but log the error
        
        # Update candidate with all collected information
        candidate_updates = {
            'last_contacted': fields.Datetime.now(),
            'status': 'contacted',
        }
        
        # Update candidate fields from wizard or conversation
        if conversation.introduction:
            candidate_updates['introduction'] = conversation.introduction
        elif self.introduction:
            candidate_updates['introduction'] = self.introduction
            
        if conversation.current_position:
            candidate_updates['current_position'] = conversation.current_position
        elif self.current_position:
            candidate_updates['current_position'] = self.current_position
            
        if conversation.current_salary:
            candidate_updates['current_salary'] = conversation.current_salary
        elif self.current_salary:
            candidate_updates['current_salary'] = self.current_salary
            
        if conversation.expected_salary:
            candidate_updates['expected_salary'] = conversation.expected_salary
        elif self.expected_salary:
            candidate_updates['expected_salary'] = self.expected_salary
            
        if conversation.notice_period:
            candidate_updates['notice_period'] = conversation.notice_period
        elif self.notice_period:
            candidate_updates['notice_period'] = self.notice_period
        
        self.candidate_id.write(candidate_updates)
        _logger.info(f"✅ Updated candidate {self.candidate_id.id} with collected information")
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Phone Call Saved',
            'res_model': 'resume.conversation',
            'res_id': conversation.id,
            'view_mode': 'form',
            'target': 'current',
        }

