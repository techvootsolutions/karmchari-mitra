# -*- coding: utf-8 -*-

import logging
from typing import Dict, Optional

_logger = logging.getLogger(__name__)


class TelephonyService:
    """Service for making phone calls via telephony providers"""
    
    def __init__(self, config: Dict):
        """
        Initialize Telephony Service
        
        Args:
            config: Configuration dictionary with telephony settings
        """
        self.config = config
        self.provider = config.get('provider_name', 'omnidimension_ai')
        self.account_sid = config.get('account_sid', '')
        self.auth_token = config.get('auth_token', '')
        self.from_number = config.get('phone_number', '')
        # OmniDimension AI specific
        self.api_endpoint = config.get('api_endpoint', 'https://api.omnidim.io/api/v1')
        self.agent_id = config.get('agent_id', '')
        self.voice_id = config.get('voice_id', '')
    
    def make_call(self, to_number: str, call_params: Dict) -> Dict:
        """
        Make a phone call
        
        Args:
            to_number: Phone number to call (E.164 format)
            call_params: Additional call parameters
            
        Returns:
            Dictionary with call information (call_sid, status, etc.)
        """
        try:
            if self.provider == 'omnidimension_ai':
                return self._make_omnidimension_ai_call(to_number, call_params)
            elif self.provider == 'twilio':
                return self._make_twilio_call(to_number, call_params)
            elif self.provider == 'plivo':
                return self._make_plivo_call(to_number, call_params)
            elif self.provider == 'vonage':
                return self._make_vonage_call(to_number, call_params)
            else:
                _logger.warning(f"Provider {self.provider} not implemented, using tel: protocol")
                return {
                    'status': 'initiated',
                    'method': 'tel_protocol',
                    'to_number': to_number
                }
        except Exception as e:
            _logger.error(f"Error making call: {e}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e),
                'method': 'tel_protocol_fallback'
            }
    
    def _make_omnidimension_ai_call(self, to_number: str, call_params: Dict) -> Dict:
        """Make call via OmniDimension AI API"""
        try:
            from .omnidimension_ai_service import OmniDimensionAIService
            
            ai_config = {
                'api_key': self.account_sid,  # API key stored in account_sid field
                'api_endpoint': self.api_endpoint,
                'agent_id': self.agent_id,
                'voice_id': self.voice_id,
            }
            
            _logger.info(f"Initializing OmniDimension AI service with endpoint: {self.api_endpoint}, agent_id: {self.agent_id}, voice_id: {self.voice_id}")
            
            ai_service = OmniDimensionAIService(ai_config)
            
            # Format conversation flow if provided
            conversation_flow = call_params.get('conversation_flow', [])
            if conversation_flow:
                formatted_flow = ai_service.format_conversation_flow(conversation_flow)
                call_params['conversation_flow'] = formatted_flow
            
            _logger.info(f"Making OmniDimension AI call to: {to_number}")
            call_params['webhook_url'] = self.api_endpoint
            print("call_params>>>>11>>>>>>>>>>>>>>>>..",call_params)

            print("to_number>>>>>>>22>>>>>>>>>>>>>..",to_number)
            result = ai_service.make_call(to_number, call_params)
            
            if result.get('status') == 'error':
                _logger.error(f"OmniDimension AI call failed: {result.get('error', 'Unknown error')}")
            else:
                _logger.info(f"OmniDimension AI call initiated successfully. Call ID: {result.get('call_id', 'N/A')}")
            
            return result
            
        except ImportError as e:
            _logger.error(f"OmniDimension AI service import error: {e}")
            return {
                'status': 'error',
                'error': 'OmniDimension AI service not available',
                'method': 'tel_protocol_fallback'
            }
        except Exception as e:
            _logger.error(f"OmniDimension AI call error: {e}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e),
                'method': 'tel_protocol_fallback'
            }
    
    def _make_twilio_call(self, to_number: str, call_params: Dict) -> Dict:
        """Make call via Twilio API"""
        try:
            # Import Twilio (if available)
            try:
                from twilio.rest import Client
            except ImportError:
                _logger.warning("Twilio library not installed. Install with: pip install twilio")
                return {
                    'status': 'error',
                    'error': 'Twilio library not installed',
                    'method': 'tel_protocol_fallback'
                }
            
            client = Client(self.account_sid, self.auth_token)
            
            # Prepare call parameters
            url = call_params.get('webhook_url', '')
            record = self.config.get('enable_call_recording', True)
            
            call = client.calls.create(
                to=to_number,
                from_=self.from_number,
                url=url,  # TwiML URL for call handling
                record=record,
                status_callback=call_params.get('status_callback', ''),
                status_callback_event=['initiated', 'ringing', 'answered', 'completed']
            )
            
            return {
                'status': 'initiated',
                'call_sid': call.sid,
                'method': 'twilio',
                'to_number': to_number,
                'from_number': self.from_number
            }
        except Exception as e:
            _logger.error(f"Twilio call error: {e}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e),
                'method': 'tel_protocol_fallback'
            }
    
    def _make_plivo_call(self, to_number: str, call_params: Dict) -> Dict:
        """Make call via Plivo API"""
        try:
            try:
                import plivo
            except ImportError:
                _logger.warning("Plivo library not installed. Install with: pip install plivo")
                return {
                    'status': 'error',
                    'error': 'Plivo library not installed',
                    'method': 'tel_protocol_fallback'
                }
            
            # Plivo implementation would go here
            _logger.info(f"Plivo call to {to_number} (not fully implemented)")
            return {
                'status': 'initiated',
                'method': 'plivo',
                'to_number': to_number
            }
        except Exception as e:
            _logger.error(f"Plivo call error: {e}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e),
                'method': 'tel_protocol_fallback'
            }
    
    def _make_vonage_call(self, to_number: str, call_params: Dict) -> Dict:
        """Make call via Vonage (Nexmo) API"""
        try:
            try:
                import vonage
            except ImportError:
                _logger.warning("Vonage library not installed. Install with: pip install vonage")
                return {
                    'status': 'error',
                    'error': 'Vonage library not installed',
                    'method': 'tel_protocol_fallback'
                }
            
            # Vonage implementation would go here
            _logger.info(f"Vonage call to {to_number} (not fully implemented)")
            return {
                'status': 'initiated',
                'method': 'vonage',
                'to_number': to_number
            }
        except Exception as e:
            _logger.error(f"Vonage call error: {e}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e),
                'method': 'tel_protocol_fallback'
            }
    
    def get_call_status(self, call_sid: str) -> Dict:
        """Get status of an ongoing call"""
        try:
            if self.provider == 'twilio':
                try:
                    from twilio.rest import Client
                    client = Client(self.account_sid, self.auth_token)
                    call = client.calls(call_sid).fetch()
                    return {
                        'status': call.status,
                        'duration': call.duration,
                        'recording_url': call.subresource_uris.get('recordings', '') if hasattr(call, 'subresource_uris') else ''
                    }
                except ImportError:
                    return {'status': 'unknown'}
            else:
                return {'status': 'unknown'}
        except Exception as e:
            _logger.error(f"Error getting call status: {e}", exc_info=True)
            return {'status': 'error', 'error': str(e)}

