# -*- coding: utf-8 -*-

import logging
from odoo import models, fields, api
from odoo.exceptions import UserError
from ..utils.language_detector import LanguageDetector

_logger = logging.getLogger(__name__)


class ResumeTelephonyConfig(models.Model):
    _name = 'resume.telephony.config'
    _description = 'Telephony Configuration for AI Calls'
    _rec_name = 'provider_name'

    provider_name = fields.Selection([
        ('omnidimension_ai', 'OmniDimension AI'),
        ('twilio', 'Twilio'),
        ('plivo', 'Plivo'),
        ('vonage', 'Vonage (Nexmo)'),
        ('custom', 'Custom API')
    ], string='Telephony Provider', required=True, default='omnidimension_ai')
    
    account_sid = fields.Char(
        string='Account SID / API Key',
        required=True,
        help='Your telephony provider account identifier or OmniDimension AI API Key'
    )
    auth_token = fields.Char(
        string='Auth Token / API Secret',
        help='Your telephony provider authentication token (not required for OmniDimension AI)'
    )
    phone_number = fields.Char(
        string='From Phone Number',
        help='Phone number to make calls from (E.164 format: +1234567890). Not required for OmniDimension AI.'
    )
    
    # OmniDimension AI specific fields
    api_endpoint = fields.Char(
        string='API Endpoint',
        default='https://api.omnidim.io/api/v1',
        help='OmniDimension AI API endpoint URL. Default: https://api.omnidim.io/api/v1'
    )
    agent_id = fields.Char(
        string='Agent ID',
        help='OmniDimension AI Agent ID for calls'
    )
    voice_id = fields.Char(
        string='Voice ID',
        help='OmniDimension AI Voice ID to use for calls'
    )
    
    # Agent Creation Fields
    agent_name = fields.Char(
        string='Agent Name',
        default='Resume Follow-Up Agent',
        help='Name for the OmniDimension AI agent'
    )
    welcome_message = fields.Text(
        string='Welcome Message',
        default='Hi [user_name], this is [Techvootbot] from [Techvoot Solution] calling to follow up on your resume submission for the [job Title] developer position. Please note that we prefer to conduct this conversation in English, but if you\'re more comfortable speaking in another language (such as Gujarati, Hindi, or any other language), please feel free to do so, and I\'ll continue the conversation in the language you prefer.',
        help='Welcome message template for the agent. Use placeholders like [user_name], [agent_name], [company_name], [job Title]. The system will automatically detect the candidate\'s language and continue in that language.'
    )
    agent_model = fields.Selection([
        ('gpt-4.1-mini', 'GPT-4.1 Mini'),
        ('gpt-4', 'GPT-4'),
        ('gpt-3.5-turbo', 'GPT-3.5 Turbo'),
        ('claude-3', 'Claude 3'),
    ], string='Agent Model', default='gpt-4.1-mini', help='AI model to use for the agent')
    agent_temperature = fields.Float(
        string='Agent Temperature',
        default=0.7,
        help='Temperature setting for the agent (0.0 to 1.0)'
    )
    transcriber_provider = fields.Selection([
        ('Azure', 'Azure'),
        ('Google', 'Google'),
        ('Deepgram', 'Deepgram'),
    ], string='Transcriber Provider', default='Azure', help='Speech-to-text provider')
    silence_timeout_ms = fields.Integer(
        string='Silence Timeout (ms)',
        default=400,
        help='Silence timeout in milliseconds for the transcriber'
    )
    
    # AI Configuration
    use_ai_agent = fields.Boolean(
        string='Use AI Agent for Calls',
        default=True,
        help='Enable AI agent to automatically place and handle calls'
    )
    ai_model = fields.Selection([
        ('openai', 'OpenAI GPT'),
        ('anthropic', 'Anthropic Claude'),
        ('local', 'Local LLM'),
        ('custom', 'Custom AI Service')
    ], string='AI Model', default='openai')
    ai_api_key = fields.Char(
        string='AI API Key',
        help='API key for AI service (if required)'
    )
    ai_endpoint = fields.Char(
        string='AI Endpoint',
        help='Custom AI service endpoint URL'
    )
    
    # Call Settings
    max_call_duration = fields.Integer(
        string='Max Call Duration (minutes)',
        default=30,
        help='Maximum duration for automated calls'
    )
    enable_call_recording = fields.Boolean(
        string='Enable Call Recording',
        default=True,
        help='Record calls for analysis'
    )
    enable_sentiment_analysis = fields.Boolean(
        string='Enable Sentiment Analysis',
        default=True,
        help='Analyze candidate sentiment during call'
    )
    
    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )
    
    active = fields.Boolean(string='Active', default=True)

    @api.model
    def get_default_config(self):
        """Get default telephony configuration"""
        config = self.search([('active', '=', True)], limit=1)
        return config
    
    def action_test_connection(self):
        """Test connection to the API endpoint"""
        self.ensure_one()
        
        if self.provider_name != 'omnidimension_ai':
            raise UserError('Connection test is only available for OmniDimension AI provider.')
        
        if not self.api_endpoint:
            raise UserError('Please enter an API Endpoint URL first.')
        
        try:
            from ..services.omnidimension_ai_service import OmniDimensionAIService
            
            config = {
                'api_key': self.account_sid or '',
                'api_endpoint': self.api_endpoint,
                'agent_id': self.agent_id or '',
                'voice_id': self.voice_id or '',
            }
            
            service = OmniDimensionAIService(config)
            result = service.test_connection()
            
            status = result.get('status', 'error')
            
            if status == 'success':
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Connection Test Successful',
                        'message': f"✅ Successfully connected to {self.api_endpoint}\n{result.get('message', '')}",
                        'type': 'success',
                        'sticky': True,
                    }
                }
            elif status == 'warning':
                # DNS works but connection timed out - this might still work for authenticated calls
                error_msg = result.get('error', 'Unknown error')
                dns_status = result.get('dns_status', '')
                
                detailed_msg = f"⚠️ Connection Test Warning\n\n"
                if dns_status:
                    detailed_msg += f"{dns_status}\n\n"
                detailed_msg += f"Note: {error_msg}\n\n"
                detailed_msg += f"Endpoint: {self.api_endpoint}\n\n"
                detailed_msg += (
                    "💡 The endpoint might still work for authenticated API calls.\n"
                    "The connection timeout could be due to:\n"
                    "1. Firewall restrictions\n"
                    "2. The endpoint requiring authentication\n"
                    "3. Network connectivity issues\n\n"
                    "Try making an actual API call (e.g., create agent) to verify if it works.\n\n"
                    "If you continue to have issues:\n"
                    "1. Log into your OmniDimension AI dashboard\n"
                    "2. Check Settings → API or Documentation section\n"
                    "3. Verify the correct API endpoint URL\n"
                    "4. Update the 'API Endpoint' field if needed"
                )
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Connection Test Warning',
                        'message': detailed_msg,
                        'type': 'warning',
                        'sticky': True,
                    }
                }
            else:
                # Actual error
                error_msg = result.get('error', 'Unknown error')
                dns_status = result.get('dns_status', '')
                
                detailed_msg = f"❌ Connection Test Failed\n\n"
                if dns_status:
                    detailed_msg += f"{dns_status}\n\n"
                detailed_msg += f"Error: {error_msg}\n\n"
                detailed_msg += f"Endpoint: {self.api_endpoint}\n\n"
                detailed_msg += (
                    "🔍 To fix this:\n"
                    "1. Log into your OmniDimension AI dashboard\n"
                    "2. Go to Settings → API or Documentation section\n"
                    "3. Find the correct API endpoint URL\n"
                    "4. Update the 'API Endpoint' field above\n\n"
                    "💡 Common endpoints:\n"
                    "   - https://api.omnidim.io/api/v1\n"
                    "   - https://www.omnidim.io/api/v1\n"
                    "   Check your dashboard for the exact endpoint."
                )
                
                raise UserError(detailed_msg)
                
        except ImportError:
            raise UserError('OmniDimension AI service is not available. Please check the module installation.')
        except Exception as e:
            _logger.error(f"Connection test error: {e}", exc_info=True)
            raise UserError(f'Connection test failed: {str(e)}')
    
    def action_create_agent(self):
        """Create an OmniDimension AI agent using the Python SDK"""
        self.ensure_one()
        
        if self.provider_name != 'omnidimension_ai':
            raise UserError('Agent creation is only available for OmniDimension AI provider.')
        
        if not self.account_sid:
            raise UserError('Please enter your API Key first.')
        
        try:
            from ..services.omnidimension_ai_service import OmniDimensionAIService
            
            config = {
                'api_key': self.account_sid or '',
                'api_endpoint': self.api_endpoint,
            }
            
            service = OmniDimensionAIService(config)
            
            # Get agent settings for context breakdown
            agent_settings = self.env['resume.agent.settings'].get_default_settings()
            
            # Build context breakdown from agent settings
            context_breakdown = self._build_context_breakdown(agent_settings)
            
            # Create agent
            result = service.create_agent(
                name=self.agent_name or 'Resume Follow-Up Agent',
                welcome_message=self.welcome_message or '',
                context_breakdown=context_breakdown,
                call_type='Outgoing',
                transcriber={
                    'provider': self.transcriber_provider or 'Azure',
                    'silence_timeout_ms': self.silence_timeout_ms or 400
                },
                model={
                    'model': self.agent_model or 'gpt-4.1-mini',
                    'temperature': self.agent_temperature or 0.7
                },
                voice={
                    'provider': 'sarvam',
                    'voice_id': self.voice_id or 'manisha'
                }
            )
            
            if result.get('status') == 'success':
                # Update agent_id with the created agent ID
                agent_id = result.get('agent_id')
                if agent_id:
                    self.agent_id = agent_id
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Agent Created Successfully',
                        'message': f"✅ Agent '{self.agent_name}' created successfully!\nAgent ID: {agent_id}\n\nThe Agent ID has been automatically saved to your configuration.",
                        'type': 'success',
                        'sticky': True,
                    }
                }
            else:
                error_msg = result.get('error', 'Unknown error')
                raise UserError(f'Failed to create agent: {error_msg}')
                
        except ImportError as e:
            if 'omnidimension' in str(e):
                # This should not happen anymore as we have REST API fallback
                # But if it does, provide helpful message
                raise UserError(
                    'Omnidimension Python SDK is not installed.\n\n'
                    'The system will attempt to use REST API instead.\n\n'
                    'To use the SDK (optional, for better performance):\n'
                    'pip install omnidimension\n\n'
                    'Or add it to your requirements.txt file.'
                )
            raise UserError(f'Import error: {str(e)}')
        except Exception as e:
            _logger.error(f"Agent creation error: {e}", exc_info=True)
            raise UserError(f'Failed to create agent: {str(e)}')
    
    def _build_context_breakdown(self, agent_settings):
        """Build context breakdown from agent settings"""
        context_breakdown = [
            {
                "title": "Agent Role & Context (MANDATORY for Outbound agents)",
                "body": f"You are a representative from {agent_settings.company_name or '[company_name]'} calling individuals who submitted a form expressing interest in the {agent_settings.default_job_title or '[position]'}. Your goal is to collect additional information from these individuals to complete their application. You are contacting recent form submitters (users) who are interested in pursuing a job at your company.",
                "is_enabled": True
            },
            {
                "title": "Introduction",
                "body": f"Introduce yourself by name and clarify your role: 'Hi [user_name], this is {agent_settings.agent_name or '[agent_name]'} from {agent_settings.company_name or '[company_name]'}. I hope I'm not catching you at a bad time. Please note that we prefer to conduct this conversation in English, but if you're more comfortable speaking in another language (such as Gujarati, Hindi, or any other language), please feel free to do so, and I'll continue the conversation in the language you prefer.' Then state your purpose: 'I'm reaching out to follow up on the resume you submitted for the {agent_settings.default_job_title or '[job_title]'} position.' Wait for confirmation that it's a good time to talk. IMPORTANT LANGUAGE DETECTION: After the candidate responds, automatically detect the language they are speaking (Gujarati, Hindi, English, or any other language) and continue the ENTIRE conversation in that detected language. If they respond in Gujarati, respond in Gujarati for ALL subsequent questions. If they respond in Hindi, respond in Hindi for ALL subsequent questions. If they respond in English, continue in English. Adapt your language immediately based on their first response and maintain that language throughout the entire conversation. If a 'preferred_language' is specified in the call_context metadata, use that language from the start instead of English.",
                "is_enabled": True
            },
            {
                "title": "Purpose Statement",
                "body": "Explain the purpose clearly: 'We need to gather a few more pieces of information to complete your application. This will help us move forward in the recruitment process.' Ensure the user is comfortable with this call and confirm their willingness to proceed with the questions.",
                "is_enabled": True
            },
            {
                "title": "Information Gathering",
                "body": "Politely and clearly ask each of the following questions, allowing time for the user to answer each one:\n- 'Could you please give us a brief introduction about yourself?'\n- 'May I know your current position?'\n- 'What is your current salary?'\n- 'What would be your expected salary for this role?'\n- 'What is your notice period with your current employer?' Acknowledge each response: 'Thank you for sharing that information.'",
                "is_enabled": True
            },
            {
                "title": "Language Detection and Multi-Language Support",
                "body": "CRITICAL LANGUAGE DETECTION INSTRUCTIONS: After the candidate responds to your greeting, automatically detect the language they are speaking. The candidate may respond in English, Gujarati, Hindi, or any other language. You MUST:\n1. Detect the language from their first response (listen for Gujarati script, Hindi/Devanagari script, or English)\n2. Immediately switch to speaking in the SAME language they used\n3. Continue the ENTIRE conversation in that detected language\n4. If they speak in Gujarati, respond in Gujarati for all subsequent messages\n5. If they speak in Hindi, respond in Hindi for all subsequent messages\n6. If they speak in English, continue in English\n7. Do NOT ask which language they prefer - just detect and adapt automatically\n8. Maintain the same professional tone and information gathering goals regardless of language\n9. Translate all your questions and responses to match their language preference\n10. If a preferred_language is provided in call_context, use that language from the start\n11. If preferred_language is 'auto' or not provided, detect from candidate's first response\n12. Store the detected language in the conversation metadata as 'detected_language'",
                "is_enabled": True
            },
            {
                "title": "Conclusion and Closing",
                "body": "Thank the user for their time and provide closure: 'Thank you for providing these details. This information helps us proceed with your application process. If we need any more information, we'll be in touch. Have a fantastic day!' Remember to use the same language the candidate has been using throughout the conversation.",
                "is_enabled": True
            }
        ]
        
        return context_breakdown

