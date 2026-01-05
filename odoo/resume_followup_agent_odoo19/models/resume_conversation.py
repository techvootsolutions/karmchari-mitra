# -*- coding: utf-8 -*-

import json
import logging
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class ResumeConversation(models.Model):
    _name = 'resume.conversation'
    _description = 'Resume Follow-Up Conversation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'timestamp desc'

    candidate_id = fields.Many2one(
        'resume.candidate',
        string='Candidate',
        required=True,
        ondelete='cascade',
        tracking=True
    )
    candidate_name = fields.Char(
        related='candidate_id.name',
        string='Candidate Name',
        store=True,
        readonly=True
    )
    position = fields.Char(
        related='candidate_id.position',
        string='Position',
        store=True,
        readonly=True
    )
    
    # Agent information
    agent_name = fields.Char(string='Agent Name', required=True, default='Techvootbot')
    company_name = fields.Char(string='Company Name', required=True)
    job_title = fields.Char(string='Job Title', required=True)
    
    # Conversation data
    conversation_data = fields.Text(
        string='Conversation Data',
        help='JSON formatted conversation messages'
    )
    transcript = fields.Text(string='Call Transcript', help='Full phone call transcript and notes')
    duration = fields.Float(string='Duration (minutes)', default=0.0)
    
    # Collected information
    collected_info = fields.Text(
        string='Collected Information',
        help='JSON formatted collected information'
    )
    brief_introduction = fields.Text(
        string='Brief Introduction',
        help='Brief introduction extracted from conversation'
    )
    introduction = fields.Text(
        string='Introduction',
        help='Full introduction (alias for brief_introduction)'
    )
    current_position = fields.Char(string='Current Position')
    current_salary = fields.Char(string='Current Salary')
    expected_salary = fields.Char(string='Expected Salary')
    notice_period = fields.Char(string='Notice Period')
    
    # Quality and notes
    call_quality = fields.Integer(
        string='Call Quality',
        default=0,
        help='Quality rating from 0 to 5 (0=Poor, 5=Excellent)'
    )
    notes = fields.Text(string='Notes')
    
    # AI Analysis and Statistics
    ai_analysis = fields.Text(
        string='AI Analysis',
        help='AI-generated analysis of the call communication'
    )
    communication_score = fields.Float(
        string='Communication Score',
        digits=(3, 2),
        help='AI-calculated communication quality score (0-10)'
    )
    sentiment_score = fields.Float(
        string='Sentiment Score',
        digits=(3, 2),
        help='AI-calculated sentiment score (-1 to 1, where 1 is positive)'
    )
    engagement_level = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('very_high', 'Very High')
    ], string='Engagement Level', help='AI-determined candidate engagement level')
    response_time_avg = fields.Float(
        string='Average Response Time (seconds)',
        help='Average time candidate took to respond'
    )
    clarity_score = fields.Float(
        string='Clarity Score',
        digits=(3, 2),
        help='AI-calculated clarity of communication (0-10)'
    )
    professionalism_score = fields.Float(
        string='Professionalism Score',
        digits=(3, 2),
        help='AI-calculated professionalism score (0-10)'
    )
    interest_level = fields.Selection([
        ('not_interested', 'Not Interested'),
        ('low', 'Low Interest'),
        ('moderate', 'Moderate Interest'),
        ('high', 'High Interest'),
        ('very_high', 'Very High Interest')
    ], string='Interest Level', help='AI-determined candidate interest level')
    
    # Statistics JSON
    call_statistics = fields.Text(
        string='Call Statistics (JSON)',
        help='Detailed statistics in JSON format'
    )
    
    # Language Detection
    detected_language = fields.Selection([
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
        ('other', 'Other'),
    ], string='Detected Language', help='Language detected from candidate responses during the conversation')
    
    # Call identification and details (matching Google Sheet structure)
    call_id = fields.Char(
        string='Call ID',
        help='OmniDimension call identifier'
    )
    call_request_id = fields.Char(
        string='Call Request ID',
        help='ID of the request that initiated this call'
    )
    call_sid = fields.Char(
        string='Call SID',
        help='Telephony provider call identifier (legacy)'
    )
    
    # Phone numbers
    phone_number = fields.Char(
        string='Phone Number',
        help='Candidate phone number'
    )
    to_number = fields.Char(
        string='To Number',
        help='Phone number that was called'
    )
    from_number = fields.Char(
        string='From Number',
        help='Phone number from which the call was made'
    )
    
    # Call metadata
    bot_name = fields.Char(
        string='Bot Name',
        default='Resume Follow-Up Agent',
        help='Name of the AI agent/bot that made the call'
    )
    call_direction = fields.Selection([
        ('inbound', 'Inbound'),
        ('outbound', 'Outbound')
    ], string='Call Direction', default='outbound', help='Direction of the call')
    call_transfered = fields.Boolean(
        string='Call Transferred',
        default=False,
        help='Whether the call was transferred'
    )
    
    # Call recording
    call_recording_url = fields.Char(
        string='Call Recording URL',
        help='URL to the recorded call audio'
    )
    recording_url = fields.Char(
        string='Recording URL',
        related='call_recording_url',
        store=True,
        help='URL to the call recording (alias for call_recording_url)'
    )
    
    # Conversation summary and sentiment
    summary = fields.Text(
        string='Summary',
        help='Brief summary of the conversation'
    )
    sentiment = fields.Selection([
        ('positive', 'Positive'),
        ('neutral', 'Neutral'),
        ('negative', 'Negative')
    ], string='Sentiment', help='Overall sentiment of the conversation')
    
    # User information
    username = fields.Char(
        string='Username',
        help='Username associated with the call'
    )
    user_name = fields.Char(
        string='User Name',
        help='Full name of the user associated with the call'
    )
    
    # Additional fields from Google Sheet
    job_position = fields.Char(
        string='Job Position',
        help='Job position discussed during the call'
    )
    interaction_count = fields.Integer(
        string='Interaction Count',
        default=0,
        help='Number of interactions/exchanges during the call'
    )
    full_conversation = fields.Text(
        string='Full Conversation',
        help='Complete conversation transcript'
    )
    call_duration_in_minutes = fields.Float(
        string='Call Duration (Minutes)',
        help='Call duration in minutes',
        compute='_compute_call_duration_minutes',
        store=True
    )
    call_duration_in_seconds = fields.Integer(
        string='Call Duration (Seconds)',
        help='Call duration in seconds',
        compute='_compute_call_duration_seconds',
        store=True
    )
    applicant_name = fields.Char(
        string='Applicant Name',
        help='Name of the applicant/candidate',
        related='candidate_name',
        store=True
    )
    
    # Timestamps
    timestamp = fields.Datetime(
        string='Call Date/Time',
        default=fields.Datetime.now,
        required=True,
        readonly=True,
        help='Date and time when the phone call was made'
    )
    call_date = fields.Datetime(
        string='Call Date',
        related='timestamp',
        store=True,
        readonly=True,
        help='Date and time when the phone call was made (alias for timestamp)'
    )
    date = fields.Date(
        string='Date',
        compute='_compute_date_time',
        store=True
    )
    time = fields.Char(
        string='Time',
        compute='_compute_date_time',
        store=True
    )
    
    # Message count
    message_count = fields.Integer(
        string='Message Count',
        compute='_compute_message_count',
        store=False
    )
    
    # Status
    status = fields.Selection([
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='completed', required=True)
    
    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )

    @api.depends('duration')
    def _compute_call_duration_minutes(self):
        """Compute call duration in minutes"""
        for record in self:
            record.call_duration_in_minutes = record.duration or 0.0
    
    @api.depends('duration')
    def _compute_call_duration_seconds(self):
        """Compute call duration in seconds"""
        for record in self:
            record.call_duration_in_seconds = int((record.duration or 0.0) * 60)
    
    @api.depends('timestamp')
    def _compute_date_time(self):
        """Compute date and time from timestamp"""
        for record in self:
            if record.timestamp:
                record.date = record.timestamp.date()
                record.time = record.timestamp.strftime('%H:%M:%S')
            else:
                record.date = False
                record.time = False

    @api.depends('conversation_data')
    def _compute_message_count(self):
        """Compute message count from conversation data"""
        for record in self:
            try:
                if record.conversation_data:
                    data = json.loads(record.conversation_data)
                    record.message_count = len(data) if isinstance(data, list) else 0
                else:
                    record.message_count = 0
            except (json.JSONDecodeError, TypeError):
                record.message_count = 0

    def _create_with_sync(self, vals):
        """Create conversation and sync call data if call_id exists"""
        # Update candidate's last_contacted
        if 'candidate_id' in vals:
            candidate = self.env['resume.candidate'].browse(vals['candidate_id'])
            candidate.write({
                'last_contacted': fields.Datetime.now(),
                'status': 'contacted'
            })
        
        # Parse collected_info and update candidate fields
        if 'collected_info' in vals and vals.get('collected_info'):
            try:
                collected = json.loads(vals['collected_info'])
                if 'candidate_id' in vals:
                    candidate = self.env['resume.candidate'].browse(vals['candidate_id'])
                    candidate.write({
                        'introduction': collected.get('introduction', ''),
                        'current_position': collected.get('current_position', ''),
                        'current_salary': collected.get('current_salary', ''),
                        'expected_salary': collected.get('expected_salary', ''),
                        'notice_period': collected.get('notice_period', ''),
                    })
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Parse collected_info to conversation fields
        if 'collected_info' in vals and vals.get('collected_info'):
            try:
                collected = json.loads(vals['collected_info'])
                if 'introduction' not in vals:
                    vals['introduction'] = collected.get('introduction', '')
                if 'brief_introduction' not in vals:
                    vals['brief_introduction'] = collected.get('introduction', '')
                if 'current_position' not in vals:
                    vals['current_position'] = collected.get('current_position', '')
                if 'current_salary' not in vals:
                    vals['current_salary'] = collected.get('current_salary', '')
                if 'expected_salary' not in vals:
                    vals['expected_salary'] = collected.get('expected_salary', '')
                if 'notice_period' not in vals:
                    vals['notice_period'] = collected.get('notice_period', '')
            except (json.JSONDecodeError, TypeError):
                pass
        
        record = super(ResumeConversation, self).create(vals)
        
        # Auto-sync call data if call_id exists and status is in_progress
        if record.call_id and record.status == 'in_progress':
            # Try to sync immediately, but don't fail if it doesn't work
            try:
                record.action_sync_call_data()
            except Exception as e:
                _logger.warning(f"Auto-sync failed for call_id {record.call_id}: {e}")
        
        return record
    
    @api.model
    def create(self, vals):
        """Override create to update candidate and parse collected info"""
        return self._create_with_sync(vals)

    def get_conversation_messages(self):
        """Get conversation messages as list"""
        self.ensure_one()
        try:
            if self.conversation_data:
                return json.loads(self.conversation_data)
            return []
        except (json.JSONDecodeError, TypeError):
            return []

    def get_collected_info_dict(self):
        """Get collected information as dictionary"""
        self.ensure_one()
        try:
            if self.collected_info:
                return json.loads(self.collected_info)
            return {}
        except (json.JSONDecodeError, TypeError):
            return {}

    def action_view_transcript(self):
        """Action to view full transcript"""
        self.ensure_one()
        return {
            'name': 'Conversation Transcript',
            'type': 'ir.actions.act_window',
            'res_model': 'resume.conversation',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'views': [(False, 'form')],
        }
    
    
    def write(self, vals):
        """Override write to auto-sync when status changes to completed"""
        result = super(ResumeConversation, self).write(vals)
        
        # Auto-sync when status changes to completed
        if 'status' in vals and vals['status'] == 'completed':
            for record in self:
                if record.call_id:
                    try:
                        record.action_sync_call_data()
                    except:
                        pass  # Don't fail write if sync fails
        
        return result
    
    def action_sync_call_data(self):
        """Sync call data from OmniDimension API"""
        self.ensure_one()
        if not self.call_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'No Call ID',
                    'message': 'This conversation does not have a Call ID. Cannot sync data.',
                    'type': 'warning',
                    'sticky': True,
                }
            }
        
        try:
            # Get telephony config
            telephony_config = self.env['resume.telephony.config'].get_default_config()
            if not telephony_config or telephony_config.provider_name != 'omnidimension_ai':
                raise UserError('OmniDimension AI telephony configuration not found.')
            
            from ..services.omnidimension_ai_service import OmniDimensionAIService
            
            config = {
                'api_key': telephony_config.account_sid or '',
                'api_endpoint': telephony_config.api_endpoint,
                'agent_id': telephony_config.agent_id or '',
                'voice_id': telephony_config.voice_id or '',
            }
            
            service = OmniDimensionAIService(config)
            
            # Get call status and details
            call_status = service.get_call_status(self.call_id)
            
            if call_status.get('status') == 'error':
                raise UserError(f"Error fetching call data: {call_status.get('error', 'Unknown error')}")
            
            # Update conversation with fetched data
            update_vals = {}
            
            # Update recording URL if available
            if call_status.get('recording_url'):
                update_vals['call_recording_url'] = call_status.get('recording_url')
                update_vals['recording_url'] = call_status.get('recording_url')
            
            # Update transcript if available
            if call_status.get('transcript'):
                update_vals['transcript'] = call_status.get('transcript')
            
            # Update summary if available
            if call_status.get('summary'):
                update_vals['summary'] = call_status.get('summary', '')
            
            # Update sentiment if available (can be text or score)
            if call_status.get('sentiment'):
                sentiment_text = call_status.get('sentiment', '').lower()
                if 'positive' in sentiment_text:
                    update_vals['sentiment'] = 'positive'
                elif 'negative' in sentiment_text:
                    update_vals['sentiment'] = 'negative'
                else:
                    update_vals['sentiment'] = 'neutral'
            elif call_status.get('sentiment_score') is not None:
                # Convert sentiment score to text
                sentiment_score = call_status.get('sentiment_score', 0)
                if sentiment_score > 0.3:
                    update_vals['sentiment'] = 'positive'
                elif sentiment_score < -0.3:
                    update_vals['sentiment'] = 'negative'
                else:
                    update_vals['sentiment'] = 'neutral'
            
            # Update collected data if available - ENHANCED to capture all fields
            collected_data = call_status.get('collected_data', {})
            if not collected_data:
                # Try alternative keys
                collected_data = call_status.get('collected_info', {}) or call_status.get('data', {}) or call_status.get('metadata', {})
            
            if collected_data:
                # Handle string JSON
                if isinstance(collected_data, str):
                    try:
                        collected_data = json.loads(collected_data)
                    except:
                        try:
                            collected_data = json.loads(json.loads(collected_data))
                        except:
                            collected_data = {}
                
                # Store as JSON
                update_vals['collected_info'] = json.dumps(collected_data)
                
                # Extract specific fields - ensure ALL fields are populated
                if 'introduction' in collected_data or 'brief_introduction' in collected_data:
                    intro = collected_data.get('introduction') or collected_data.get('brief_introduction', '')
                    if intro:
                        update_vals['brief_introduction'] = intro
                        update_vals['introduction'] = intro
                if 'current_position' in collected_data:
                    pos = collected_data.get('current_position', '')
                    if pos:
                        update_vals['current_position'] = pos
                if 'current_salary' in collected_data:
                    sal = collected_data.get('current_salary', '')
                    if sal:
                        update_vals['current_salary'] = sal
                if 'expected_salary' in collected_data:
                    exp_sal = collected_data.get('expected_salary', '')
                    if exp_sal:
                        update_vals['expected_salary'] = exp_sal
                if 'notice_period' in collected_data:
                    notice = collected_data.get('notice_period', '')
                    if notice:
                        update_vals['notice_period'] = notice
                
                # Update detected language if available
                if 'detected_language' in collected_data:
                    update_vals['detected_language'] = collected_data.get('detected_language')
            
            # Update duration if available
            if call_status.get('duration'):
                update_vals['duration'] = call_status.get('duration', 0) / 60.0  # Convert to minutes
            
            # Update status
            call_status_value = call_status.get('status', 'completed')
            if call_status_value == 'completed':
                update_vals['status'] = 'completed'
            elif call_status_value in ['in_progress', 'ringing', 'answered']:
                update_vals['status'] = 'in_progress'
            
            if update_vals:
                self.write(update_vals)
                
                # Update candidate fields with synced data
                if self.candidate_id:
                    candidate_updates = {}
                    if 'introduction' in update_vals:
                        candidate_updates['introduction'] = update_vals['introduction']
                    if 'current_position' in update_vals:
                        candidate_updates['current_position'] = update_vals['current_position']
                    if 'current_salary' in update_vals:
                        candidate_updates['current_salary'] = update_vals['current_salary']
                    if 'expected_salary' in update_vals:
                        candidate_updates['expected_salary'] = update_vals['expected_salary']
                    if 'notice_period' in update_vals:
                        candidate_updates['notice_period'] = update_vals['notice_period']
                    
                    if candidate_updates:
                        self.candidate_id.write(candidate_updates)
                        _logger.info(f"✅ Updated candidate {self.candidate_id.id} with synced data")
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Call Data Synced',
                        'message': f'Successfully synced call data from OmniDimension API. Recording URL: {"Yes" if update_vals.get("call_recording_url") else "No"}',
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'No Updates',
                        'message': 'No new data available from OmniDimension API.',
                        'type': 'info',
                        'sticky': False,
                    }
                }
                
        except Exception as e:
            import logging
            _logger = logging.getLogger(__name__)
            _logger.error(f"Error syncing call data: {e}", exc_info=True)
            raise UserError(f'Failed to sync call data: {str(e)}')

