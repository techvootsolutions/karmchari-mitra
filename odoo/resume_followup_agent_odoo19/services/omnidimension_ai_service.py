# -*- coding: utf-8 -*-

import logging
import requests
import json
from typing import Dict, Optional, List

_logger = logging.getLogger(__name__)

# Try to import the Omnidimension SDK
OMNIDIMENSION_SDK_AVAILABLE = False
OMNIDIMENSION_CLIENT = None

def _check_sdk_availability():
    """Check if SDK is available and import it"""
    global OMNIDIMENSION_SDK_AVAILABLE, OMNIDIMENSION_CLIENT
    
    # If already loaded, return immediately
    if OMNIDIMENSION_SDK_AVAILABLE and OMNIDIMENSION_CLIENT is not None:
        return True
    
    try:
        # Try importing from user site-packages first (common for --user installs)
        import site
        import sys
        user_site = site.getusersitepackages()
        if user_site and user_site not in sys.path:
            sys.path.insert(0, user_site)
            _logger.debug(f"Added user site-packages to path: {user_site}")
        
        # Try to import
        from omnidimension import Client
        OMNIDIMENSION_CLIENT = Client
        OMNIDIMENSION_SDK_AVAILABLE = True
        _logger.info("✅ Omnidimension Python SDK is available and loaded successfully")
        return True
    except ImportError as e:
        OMNIDIMENSION_SDK_AVAILABLE = False
        OMNIDIMENSION_CLIENT = None
        _logger.warning(f"⚠️ Omnidimension Python SDK import failed: {e}")
        _logger.warning(f"Install with: pip install --user omnidimension")
        _logger.warning(f"Current Python path: {sys.path[:3]}...")
        return False
    except Exception as e:
        OMNIDIMENSION_SDK_AVAILABLE = False
        OMNIDIMENSION_CLIENT = None
        _logger.error(f"Error checking SDK availability: {e}", exc_info=True)
        return False

# Try to load SDK at module import
_check_sdk_availability()


class OmniDimensionAIService:
    """Service for OmniDimension AI phone call integration"""
    
    def __init__(self, config: Dict):
        """
        Initialize OmniDimension AI Service
        
        Args:
            config: Configuration dictionary with API settings
                - api_key: OmniDimension AI API key
                - api_endpoint: API endpoint URL
                - agent_id: Agent ID for calls
                - voice_id: Voice ID to use
        """
        self.api_key = config.get('api_key', '')
        self.api_endpoint = config.get('api_endpoint', 'https://api.omnidim.io/api/v1')
        self.agent_id = config.get('agent_id', '')
        self.voice_id = config.get('voice_id', '')
        self.timeout = config.get('timeout', 30)
        
        # Clean endpoint URL (remove trailing slash)
        if self.api_endpoint.endswith('/'):
            self.api_endpoint = self.api_endpoint.rstrip('/')
        
        # Validate required fields
        if not self.api_key:
            _logger.warning("OmniDimension AI API key is not set")
        if not self.agent_id:
            _logger.warning("OmniDimension AI Agent ID is not set")
        if not self.voice_id:
            _logger.warning("OmniDimension AI Voice ID is not set")
        
        # Validate endpoint URL format
        if not self.api_endpoint.startswith(('http://', 'https://')):
            _logger.warning(f"API endpoint should start with http:// or https://. Got: {self.api_endpoint}")
    
    def make_call(self, to_number: str, call_params: Dict) -> Dict:
        """
        Make a phone call using OmniDimension AI

        Args:
            to_number: Phone number to call (E.164 format)
            call_params: Additional call parameters
                - conversation_flow: List of conversation steps/questions
                - candidate_name: Name of the candidate
                - agent_name: Name of the agent
                - company_name: Company name
                - job_title: Job title
                - webhook_url: URL for call status updates

        Returns:
            Dictionary with call information
        """
        # Validate and format phone number (must be E.164 format: +countrycode+number)
        original_number = to_number
        to_number = to_number.strip().replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        
        # If number doesn't start with +, try to add country code
        if not to_number.startswith('+'):
            # Common Indian number pattern (10 digits starting with 6-9)
            if len(to_number) == 10 and to_number[0] in '6789':
                to_number = '+91' + to_number
                _logger.info(f"Added country code +91 to phone number: {original_number} -> {to_number}")
            else:
                _logger.warning(f"Phone number {to_number} doesn't have country code (+). OmniDimension requires E.164 format (e.g., +919016632843)")
                return {
                    'status': 'error',
                    'error': f'Phone number must be in E.164 format with country code. Got: {original_number}\n\n'
                            f'Please format as: +[country code][number]\n'
                            f'Example: +919016632843 (for India) or +1234567890 (for US)',
                    'method': 'omnidimension_ai',
                }
        
        # ALWAYS try SDK first if available (it's more reliable)
        # Re-check SDK availability in case it was installed after module load
        sdk_available = _check_sdk_availability()
        
        _logger.info(f"SDK availability check: {sdk_available}")
        _logger.info(f"Making call to: {to_number} (original: {original_number})")
        
        if sdk_available:
            _logger.info("🚀 Using OmniDimension SDK to make call (recommended method)")
            try:
                result = self._make_call_with_sdk(to_number, call_params)
                # If SDK succeeds, return it
                if result.get('status') == 'initiated':
                    _logger.info("✅ Call initiated successfully using SDK")
                    return result
                # If SDK fails but returns an error, log it
                error_msg = result.get('error', 'Unknown error')
                _logger.error(f"❌ SDK call failed: {error_msg}")
                # Don't fallback to REST API if SDK is available - SDK errors are more informative
                return result
            except Exception as e:
                _logger.error(f"❌ SDK call raised exception: {e}", exc_info=True)
                # Return error instead of falling back to REST API
                return {
                    'status': 'error',
                    'error': f'SDK call failed: {str(e)}\n\nPlease check:\n1. Your API key is correct\n2. Your Agent ID is correct\n3. The SDK is properly installed: pip install --user omnidimension',
                    'method': 'omnidimension_ai',
                }
        
        # Only use REST API if SDK is truly not available
        _logger.error("❌ OmniDimension SDK not available. Attempting REST API (may fail).")
        _logger.error("⚠️  Install SDK with: pip install --user omnidimension")
        _logger.error("⚠️  Then restart Odoo server for changes to take effect")
        return self._make_call_with_rest_api(to_number, call_params)
    
    def _make_call_with_sdk(self, to_number: str, call_params: Dict) -> Dict:
        """Make call using Omnidimension Python SDK"""
        try:
            if not self.api_key:
                return {
                    'status': 'error',
                    'error': 'API key is required to make a call',
                    'method': 'omnidimension_ai',
                }
            
            if not self.agent_id:
                return {
                    'status': 'error',
                    'error': 'Agent ID is required to make a call. Please create an agent first.',
                    'method': 'omnidimension_ai',
                }
            
            # Ensure SDK is available and import Client
            if not _check_sdk_availability():
                return {
                    'status': 'error',
                    'error': 'OmniDimension SDK is not available. Please install it: pip install --user omnidimension',
                    'method': 'omnidimension_ai',
                }
            
            from omnidimension import Client
            client = Client(self.api_key)
            
            # Convert agent_id to int if it's a numeric string (SDK might expect int)
            agent_id = self.agent_id
            try:
                if isinstance(agent_id, str) and agent_id.isdigit():
                    agent_id = int(agent_id)
            except (ValueError, AttributeError):
                pass  # Keep as string if conversion fails
            
            # Prepare call parameters for dispatch_call
            # The SDK dispatch_call signature is: dispatch_call(agent_id, to_number, from_number_id=None, call_context=None)
            
            # Build call_context from metadata and other params
            call_context = {}
            
            # Add metadata if provided
            if call_params.get('candidate_name'):
                call_context['candidate_name'] = call_params.get('candidate_name')
            if call_params.get('agent_name'):
                call_context['agent_name'] = call_params.get('agent_name')
            if call_params.get('company_name'):
                call_context['company_name'] = call_params.get('company_name')
            if call_params.get('job_title'):
                call_context['job_title'] = call_params.get('job_title')
            if call_params.get('conversation_flow'):
                call_context['conversation_flow'] = call_params.get('conversation_flow')
            if call_params.get('webhook_url'):
                call_context['webhook_url'] = call_params.get('webhook_url')
            if call_params.get('record') is not None:
                call_context['record'] = call_params.get('record')
            
            # Add language preferences for AI
            if call_params.get('preferred_language'):
                call_context['preferred_language'] = call_params.get('preferred_language')
            if call_params.get('enable_language_detection'):
                call_context['enable_language_detection'] = call_params.get('enable_language_detection')
            
            # Set caller ID name to remove "spam" label - use agent name (preferred) or generic name
            # Avoid using company name to prevent spam labeling
            if call_params.get('from_number_name'):
                call_context['from_number_name'] = call_params.get('from_number_name')
            elif call_params.get('agent_name'):
                # Use agent name (e.g., "HR Assistant") instead of company name
                call_context['from_number_name'] = call_params.get('agent_name')
            else:
                # Use generic professional name
                call_context['from_number_name'] = 'Recruitment'
            
            # from_number_id is optional - can be None
            from_number_id = call_params.get('from_number_id', None)
            
            # Reduced logging for faster call initiation
            _logger.info(f"Making call to {to_number} with agent_id {agent_id}")
            
            # Make the call using SDK - use dispatch_call method
            response = None
            
            # Try dispatch_call method (the correct SDK method)
            if hasattr(client, 'call') and hasattr(client.call, 'dispatch_call'):
                # Minimal logging for speed
                response = client.call.dispatch_call(
                    agent_id=agent_id,
                    to_number=to_number,
                    from_number_id=from_number_id,
                    call_context=call_context if call_context else None
                )
                _logger.info(f"Call initiated: {type(response)}")
            elif hasattr(client, 'call') and hasattr(client.call, 'create'):
                # Fallback to create if dispatch_call doesn't exist
                _logger.info("Using client.call.create() method (fallback)")
                call_data = {
                    'agent_id': agent_id,
                    'to': to_number,
                    'from_number_id': from_number_id,
                    'call_context': call_context if call_context else None
                }
                response = client.call.create(**call_data)
            else:
                # Log available methods for debugging
                available_attrs = [attr for attr in dir(client) if not attr.startswith('_')]
                _logger.warning(f"SDK client available attributes: {available_attrs}")
                if hasattr(client, 'call'):
                    call_attrs = [attr for attr in dir(client.call) if not attr.startswith('_')]
                    _logger.warning(f"client.call available attributes: {call_attrs}")
                raise AttributeError(
                    f"SDK does not have call dispatch method. "
                    f"Client has: {available_attrs}. "
                    f"client.call has: {call_attrs if hasattr(client, 'call') else 'N/A'}. "
                    f"Please check Omnidimension SDK documentation for the correct method."
                )
            
            # Extract call ID from response - try multiple possible formats
            call_id = None
            if isinstance(response, dict):
                # Try various possible keys
                call_id = (response.get('id') or 
                          response.get('call_id') or 
                          response.get('callId') or
                          response.get('data', {}).get('id') or
                          response.get('data', {}).get('call_id') or
                          response.get('data', {}).get('callId') or
                          response.get('result', {}).get('id') or
                          response.get('result', {}).get('call_id'))
                _logger.info(f"Response dict keys: {list(response.keys())}")
            elif hasattr(response, 'id'):
                call_id = response.id
            elif hasattr(response, 'call_id'):
                call_id = response.call_id
            elif hasattr(response, 'callId'):
                call_id = response.callId
            elif hasattr(response, '__dict__'):
                # Try to get from object attributes
                call_id = getattr(response, 'id', None) or getattr(response, 'call_id', None) or getattr(response, 'callId', None)
                _logger.info(f"Response object attributes: {dir(response)}")
            
            if not call_id:
                _logger.warning(f"Could not extract call_id from response. Full response: {response}")
                # If response is truthy but no call_id, the call might still have been initiated
                # Return success but log the full response for debugging
                if response:
                    _logger.info("Response received but call_id not found. Call may still be processing.")
            
            _logger.info(f"Call initiated successfully. Call ID: {call_id}")
            
            # Even if call_id is empty, if we got a response, the call might have been initiated
            # Return success but include warning if no call_id
            result = {
                'status': 'initiated',
                'call_id': str(call_id) if call_id else '',
                'call_sid': str(call_id) if call_id else '',  # Use call_id as call_sid for compatibility
                'method': 'omnidimension_ai',
                'to_number': to_number,
            }
            
            if not call_id:
                _logger.warning("⚠️ Call initiated but no call_id returned. Check OmniDimension dashboard for call status.")
                result['warning'] = 'Call may have been initiated but no call_id was returned. Please check your OmniDimension dashboard.'
            
            return result
            
        except Exception as e:
            _logger.error(f"Error making call with SDK: {e}", exc_info=True)
            # Re-raise to let the caller handle fallback
            raise
    
    def _make_call_with_rest_api(self, to_number: str, call_params: Dict) -> Dict:
        """Make call using REST API (fallback method)"""
        try:
            if not self.api_key:
                return {
                    'status': 'error',
                    'error': 'API key is required to make a call',
                    'method': 'omnidimension_ai',
                }
            
            if not self.agent_id:
                return {
                    'status': 'error',
                    'error': 'Agent ID is required to make a call. Please create an agent first or set the Agent ID in Telephony Configuration.',
                    'method': 'omnidimension_ai',
                }
            
            # Prepare call payload
            payload = {
                'to': to_number,
                'agent_id': self.agent_id,
            }
            
            # Add optional fields
            if self.voice_id:
                payload['voice_id'] = self.voice_id
            
            if call_params.get('conversation_flow'):
                payload['conversation_flow'] = call_params.get('conversation_flow')
            
            if call_params.get('webhook_url'):
                payload['webhook_url'] = call_params.get('webhook_url')
            
            if call_params.get('record') is not None:
                payload['record'] = call_params.get('record', True)
            
            # Set caller ID name to remove "spam" label - use agent name (preferred) or generic name
            # Avoid using company name to prevent spam labeling
            if call_params.get('from_number_name'):
                payload['from_number_name'] = call_params.get('from_number_name')
            elif call_params.get('agent_name'):
                # Use agent name (e.g., "HR Assistant") instead of company name
                payload['from_number_name'] = call_params.get('agent_name')
            else:
                # Use generic professional name
                payload['from_number_name'] = 'Recruitment'
            
            # Add metadata
            metadata = {}
            if call_params.get('candidate_name'):
                metadata['candidate_name'] = call_params.get('candidate_name')
            if call_params.get('agent_name'):
                metadata['agent_name'] = call_params.get('agent_name')
            if call_params.get('company_name'):
                metadata['company_name'] = call_params.get('company_name')
            if call_params.get('job_title'):
                metadata['job_title'] = call_params.get('job_title')
            
            # Add language preferences for AI
            if call_params.get('preferred_language'):
                metadata['preferred_language'] = call_params.get('preferred_language')
            if call_params.get('enable_language_detection'):
                metadata['enable_language_detection'] = call_params.get('enable_language_detection')
            
            if metadata:
                payload['metadata'] = metadata

            # Make API request
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
            }

            # Try different endpoint paths - the API might use /calls/dispatch or /calls
            # Remove /api/v1 from endpoint if present, we'll construct the path properly
            base_endpoint = self.api_endpoint
            if '/api/v1' in base_endpoint:
                base_endpoint = base_endpoint.replace('/api/v1', '')
            elif base_endpoint.endswith('/api'):
                base_endpoint = base_endpoint[:-4]
            
            # Try /api/v1/calls/dispatch first (per documentation)
            api_urls = [
                f'{base_endpoint}/api/v1/calls/dispatch',
                f'{base_endpoint}/api/v1/calls',
                f'{self.api_endpoint}/calls/dispatch',
                f'{self.api_endpoint}/calls',
            ]
            
            last_error = None
            response = None
            successful_url = None
            
            for api_url in api_urls:
                try:
                    _logger.info(f"Trying API endpoint: {api_url}")
                    response = requests.post(
                        api_url,
                        json=payload,
                        headers=headers,
                        timeout=self.timeout
                    )
                    
                    # If we get a 404, try next URL
                    if response.status_code == 404:
                        _logger.warning(f"Endpoint {api_url} returned 404, trying next...")
                        last_error = f"Endpoint not found: {api_url}"
                        response = None
                        continue
                    
                    # If we get HTML response (like Odoo 404 page), it's wrong endpoint
                    if 'text/html' in response.headers.get('Content-Type', ''):
                        _logger.warning(f"Endpoint {api_url} returned HTML (wrong endpoint), trying next...")
                        last_error = f"Endpoint returned HTML page (not API): {api_url}"
                        response = None
                        continue
                    
                    # If we get here, we have a valid API response
                    successful_url = api_url
                    break
                except requests.exceptions.RequestException as e:
                    _logger.warning(f"Error with endpoint {api_url}: {e}, trying next...")
                    last_error = str(e)
                    response = None
                    continue
            
            if response is None:
                # All endpoints failed - provide clear solution
                error_msg = (
                    f'❌ All REST API endpoints failed. Connection timeout to www.omnidim.io\n\n'
                    f'🔍 The issue: The REST API endpoint is not reachable or incorrect.\n\n'
                    f'✅ SOLUTION: Install the OmniDimension Python SDK\n\n'
                    f'To install the SDK, run this command in your Odoo server environment:\n'
                    f'   pip install omnidimension\n\n'
                    f'Or if using a virtual environment:\n'
                    f'   source /path/to/venv/bin/activate\n'
                    f'   pip install omnidimension\n\n'
                    f'Then restart your Odoo server.\n\n'
                    f'The SDK automatically uses the correct endpoint and is much more reliable.\n\n'
                    f'Last error: {last_error}'
                )
                return {
                    'status': 'error',
                    'error': error_msg,
                    'method': 'omnidimension_ai',
                }

            if response.status_code == 200 or response.status_code == 201:
                result = response.json()
                _logger.info(f"Call initiated successfully via REST API using endpoint: {successful_url}")
                return {
                    'status': 'initiated',
                    'call_id': result.get('call_id', ''),
                    'call_sid': result.get('call_sid', ''),
                    'status_url': result.get('status_url', ''),
                    'recording_url': result.get('recording_url', ''),
                    'method': 'omnidimension_ai',
                    'to_number': to_number,
                }
            else:
                error_text = response.text
                try:
                    error_json = response.json()
                    error_text = error_json.get('message', error_json.get('error', error_text))
                except:
                    pass
                
                _logger.error(f"OmniDimension AI API error: {response.status_code} - {error_text}")
                _logger.error(f"Request URL: {successful_url or api_urls[0]}")
                _logger.error(f"Request payload: {payload}")
                
                if response.status_code == 404 or 'text/html' in response.headers.get('Content-Type', ''):
                    # Check if response is HTML (Odoo 404 page)
                    if '<html' in error_text or '<!DOCTYPE html>' in error_text:
                        error_msg = (
                            f"❌ API endpoint not found - The URL is pointing to a website, not the API\n\n"
                            f"The endpoint '{api_url}' is returning an HTML page (likely an Odoo website), not an API endpoint.\n\n"
                            f"🔍 Solutions:\n"
                            f"1. Install the OmniDimension Python SDK (RECOMMENDED):\n"
                            f"   pip install omnidimension\n\n"
                            f"2. Or verify the correct API endpoint URL in your OmniDimension dashboard:\n"
                            f"   - The endpoint should be an API URL, not a website URL\n"
                            f"   - Common format: https://api.omnidim.io/api/v1\n"
                            f"   - Check Settings → API in your dashboard\n\n"
                            f"3. The REST API endpoint format may have changed\n\n"
                            f"💡 The SDK automatically uses the correct endpoint and is the recommended method."
                        )
                    else:
                        error_msg = (
                            f"❌ API endpoint not found (404)\n\n"
                            f"The endpoint '{api_url}' does not exist.\n\n"
                            f"🔍 Solutions:\n"
                            f"1. Install the OmniDimension Python SDK (RECOMMENDED):\n"
                            f"   pip install omnidimension\n\n"
                            f"2. Verify the correct API endpoint URL in your OmniDimension dashboard\n\n"
                            f"Response: {error_text[:200]}"
                        )
                else:
                    error_msg = f"API error: {response.status_code} - {error_text}"
                
                return {
                    'status': 'error',
                    'error': error_msg,
                    'method': 'omnidimension_ai',
                }

        except requests.exceptions.ConnectionError as e:
            # Handle DNS resolution and connection errors
            error_msg = str(e)
            if 'Failed to resolve' in error_msg or 'Name or service not known' in error_msg or 'NXDOMAIN' in error_msg:
                # Extract domain from endpoint
                try:
                    from urllib.parse import urlparse
                    parsed = urlparse(self.api_endpoint)
                    domain = parsed.netloc or parsed.path.split('/')[0]
                except:
                    domain = self.api_endpoint
                
                user_friendly_error = (
                    f"❌ DNS Resolution Failed: Cannot resolve domain '{domain}'\n\n"
                    f"This means the API endpoint domain does not exist or cannot be reached.\n\n"
                    f"🔍 Troubleshooting Steps:\n"
                    f"1. Verify the API endpoint URL in Telephony Configuration\n"
                    f"   Current endpoint: {self.api_endpoint}\n"
                    f"2. The correct OmniDimension AI endpoint should be from 'omnidim.io' domain\n"
                    f"   Example: https://www.omnidim.io/api/v1 or https://api.omnidim.io/v1\n"
                    f"3. Log into your OmniDimension AI dashboard and check Settings → API section\n"
                    f"4. Verify your server has internet connectivity\n"
                    f"5. Test DNS resolution: Run 'ping {domain}' or 'nslookup {domain}'\n"
                    f"6. Contact OmniDimension AI support if the endpoint is still incorrect\n\n"
                    f"💡 Note: This is NOT an API key issue. The domain itself cannot be found.\n"
                    f"   The old domain 'api.omnidimension.ai' does not exist. Use 'omnidim.io' instead."
                )
            else:
                user_friendly_error = (
                    f"Connection error: {error_msg}\n"
                    f"Please check your network connectivity and API endpoint: {self.api_endpoint}"
                )
            _logger.error(f"OmniDimension AI connection error: {e}")
            return {
                'status': 'error',
                'error': user_friendly_error,
                'method': 'omnidimension_ai',
            }
        except requests.exceptions.Timeout as e:
            _logger.error(f"OmniDimension AI timeout error: {e}")
            return {
                'status': 'error',
                'error': f"Request timeout. The API endpoint {self.api_endpoint} did not respond within {self.timeout} seconds.",
                'method': 'omnidimension_ai',
            }
        except requests.exceptions.RequestException as e:
            _logger.error(f"OmniDimension AI request error: {e}")
            return {
                'status': 'error',
                'error': f"Request failed: {str(e)}\nAPI Endpoint: {self.api_endpoint}",
                'method': 'omnidimension_ai',
            }
        except Exception as e:
            _logger.error(f"OmniDimension AI error: {e}", exc_info=True)
            return {
                'status': 'error',
                'error': f"Unexpected error: {str(e)}",
                'method': 'omnidimension_ai',
            }

    def get_call_status(self, call_id: str) -> Dict:
        """
        Get status of an ongoing call
        
        Args:
            call_id: Call ID from make_call response
            
        Returns:
            Dictionary with call status
        """
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
            }
            
            response = requests.get(
                f'{self.api_endpoint}/calls/{call_id}',
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                # Try multiple possible keys for collected data
                collected_data = (result.get('collected_data') or 
                                result.get('collected_info') or 
                                result.get('data', {}).get('collected_data') or
                                result.get('data', {}).get('collected_info') or {})
                
                return {
                    'status': result.get('status', 'unknown'),
                    'duration': result.get('duration', 0),
                    'recording_url': result.get('recording_url', ''),
                    'transcript': result.get('transcript', ''),
                    'summary': result.get('summary', ''),
                    'sentiment': result.get('sentiment', ''),
                    'sentiment_score': result.get('sentiment_score'),
                    'collected_data': collected_data,
                    'detected_language': result.get('detected_language', ''),
                }
            else:
                return {'status': 'error', 'error': f"API error: {response.status_code}"}
                
        except Exception as e:
            _logger.error(f"Error getting call status: {e}", exc_info=True)
            return {'status': 'error', 'error': str(e)}
    
    def get_call_analytics(self, call_id: str) -> Dict:
        """
        Get analytics for a completed call
        
        Args:
            call_id: Call ID from make_call response
            
        Returns:
            Dictionary with call analytics
        """
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
            }
            
            response = requests.get(
                f'{self.api_endpoint}/calls/{call_id}/analytics',
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {'error': f"API error: {response.status_code}"}
                
        except Exception as e:
            _logger.error(f"Error getting call analytics: {e}", exc_info=True)
            return {'error': str(e)}
    
    def test_connection(self) -> Dict:
        """
        Test connection to the API endpoint
        
        Returns:
            Dictionary with test results
        """
        try:
            from urllib.parse import urlparse
            parsed = urlparse(self.api_endpoint)
            domain = parsed.netloc or parsed.path.split('/')[0]
            
            # Try to resolve DNS first
            import socket
            try:
                socket.gethostbyname(domain)
                dns_status = "✅ DNS resolution successful"
            except socket.gaierror as e:
                dns_status = f"❌ DNS resolution failed: {str(e)}"
                return {
                    'status': 'error',
                    'dns_status': dns_status,
                    'error': f"Cannot resolve domain '{domain}'. Please verify the API endpoint URL is correct.",
                    'endpoint': self.api_endpoint
                }
            
            # Try to connect to the base domain first (more reliable than /api/v1 endpoint)
            # Extract base URL (e.g., https://api.omnidim.io from https://api.omnidim.io/api/v1)
            base_url = f"{parsed.scheme}://{domain}"
            
            # Try connecting to base URL first
            try:
                response = requests.get(
                    base_url,
                    timeout=10,
                    headers={'User-Agent': 'Odoo-ResumeFollowUp/1.0'},
                    allow_redirects=True
                )
                return {
                    'status': 'success',
                    'dns_status': dns_status,
                    'http_status': response.status_code,
                    'endpoint': self.api_endpoint,
                    'base_url': base_url,
                    'message': f"Connection successful. Base domain is reachable (HTTP {response.status_code}). The API endpoint should work when making authenticated requests."
                }
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                # If base URL fails, try the actual endpoint (might require auth, so expect 401/403)
                try:
                    response = requests.get(
                        self.api_endpoint,
                        timeout=10,
                        headers={
                            'User-Agent': 'Odoo-ResumeFollowUp/1.0',
                            'Authorization': f'Bearer {self.api_key}' if self.api_key else ''
                        },
                        allow_redirects=True
                    )
                    # Even if we get 401/403, it means the endpoint exists and is reachable
                    if response.status_code in [200, 401, 403, 404]:
                        return {
                            'status': 'success',
                            'dns_status': dns_status,
                            'http_status': response.status_code,
                            'endpoint': self.api_endpoint,
                            'message': f"Endpoint is reachable (HTTP {response.status_code}). {'Authentication may be required.' if response.status_code in [401, 403] else ''}"
                        }
                except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e2:
                    # Both failed - connection timeout
                    return {
                        'status': 'warning',
                        'dns_status': dns_status,
                        'error': f"Connection timeout: {str(e2)}. DNS resolution works, but cannot connect to the server. This might be due to:\n1. Firewall blocking the connection\n2. The endpoint requires authentication\n3. Network connectivity issues\n\nThe endpoint might still work for authenticated API calls.",
                        'endpoint': self.api_endpoint,
                        'base_url': base_url
                    }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': f"Test failed: {str(e)}",
                'endpoint': self.api_endpoint
            }
    
    def format_conversation_flow(self, questions: List[Dict]) -> List[Dict]:
        """
        Format conversation questions for OmniDimension AI API
        
        Args:
            questions: List of question dictionaries from agent settings
            
        Returns:
            Formatted conversation flow for API
        """
        formatted_flow = []
        
        for q in questions:
            step = {
                'step_type': q.get('step_type', q.get('step', 'question')),
                'message': q.get('message', ''),
                'collect_field': q.get('collect_field', ''),
                'field_label': q.get('field_label', ''),
            }
            formatted_flow.append(step)
        
        return formatted_flow
    
    def create_agent(self, name: str, welcome_message: str, context_breakdown: List[Dict], 
                     call_type: str = 'Outgoing', transcriber: Dict = None, 
                     model: Dict = None, voice: Dict = None) -> Dict:
        """
        Create an OmniDimension AI agent using the Python SDK or REST API
        
        Args:
            name: Agent name
            welcome_message: Welcome message template
            context_breakdown: List of context breakdown dictionaries with title, body, is_enabled
            call_type: Type of call (e.g., 'Outgoing')
            transcriber: Transcriber configuration dict with provider and silence_timeout_ms
            model: Model configuration dict with model and temperature
            voice: Voice configuration dict with provider and voice_id
            
        Returns:
            Dictionary with agent creation result
        """
        # Try using SDK first if available
        if OMNIDIMENSION_SDK_AVAILABLE:
            return self._create_agent_with_sdk(name, welcome_message, context_breakdown, 
                                               call_type, transcriber, model, voice)
        else:
            # Fallback to REST API
            return self._create_agent_with_rest_api(name, welcome_message, context_breakdown,
                                                   call_type, transcriber, model, voice)
    
    def _create_agent_with_sdk(self, name: str, welcome_message: str, context_breakdown: List[Dict], 
                               call_type: str = 'Outgoing', transcriber: Dict = None, 
                               model: Dict = None, voice: Dict = None) -> Dict:
        """Create agent using Omnidimension Python SDK"""
        
        if not self.api_key:
            return {
                'status': 'error',
                'error': 'API key is required to create an agent'
            }
        
        try:
            # Ensure SDK is available
            if not _check_sdk_availability():
                return {
                    'status': 'error',
                    'error': 'OmniDimension SDK is not available. Please install it: pip install --user omnidimension',
                }
            
            # Import Client dynamically
            from omnidimension import Client
            client = Client(self.api_key)
            
            # Prepare transcriber config
            transcriber_config = transcriber or {
                'provider': 'Azure',
                'silence_timeout_ms': 400
            }
            
            # Prepare model config
            model_config = model or {
                'model': 'gpt-4.1-mini',
                'temperature': 0.7
            }
            
            # Prepare voice config
            voice_config = voice or {
                'provider': 'sarvam',
                'voice_id': 'manisha'
            }
            
            # Create agent
            response = client.agent.create(
                name=name,
                welcome_message=welcome_message,
                context_breakdown=context_breakdown,
                call_type=call_type,
                transcriber=transcriber_config,
                model=model_config,
                voice=voice_config,
            )
            
            # Extract agent ID from response
            # The response structure may vary, so we handle different formats
            agent_id = None
            if isinstance(response, dict):
                agent_id = response.get('id') or response.get('agent_id') or response.get('data', {}).get('id')
            elif hasattr(response, 'id'):
                agent_id = response.id
            elif hasattr(response, 'agent_id'):
                agent_id = response.agent_id
            
            _logger.info(f"Agent created successfully: {name} (ID: {agent_id})")
            
            return {
                'status': 'success',
                'agent_id': str(agent_id) if agent_id else None,
                'response': response,
                'message': f'Agent "{name}" created successfully'
            }
            
        except Exception as e:
            _logger.error(f"Error creating agent with SDK: {e}", exc_info=True)
            return {
                'status': 'error',
                'error': f'Failed to create agent: {str(e)}'
            }
    
    def _create_agent_with_rest_api(self, name: str, welcome_message: str, context_breakdown: List[Dict], 
                                   call_type: str = 'Outgoing', transcriber: Dict = None, 
                                   model: Dict = None, voice: Dict = None) -> Dict:
        """Create agent using REST API (fallback when SDK is not available)"""
        if not self.api_key:
            return {
                'status': 'error',
                'error': 'API key is required to create an agent'
            }
        
        try:
            # Prepare transcriber config
            transcriber_config = transcriber or {
                'provider': 'Azure',
                'silence_timeout_ms': 400
            }
            
            # Prepare model config
            model_config = model or {
                'model': 'gpt-4.1-mini',
                'temperature': 0.7
            }
            
            # Prepare voice config
            voice_config = voice or {
                'provider': 'sarvam',
                'voice_id': 'manisha'
            }
            
            # Build payload for agent creation
            payload = {
                'name': name,
                'welcome_message': welcome_message,
                'context_breakdown': context_breakdown,
                'call_type': call_type,
                'transcriber': transcriber_config,
                'model': model_config,
                'voice': voice_config,
            }
            
            # Determine API endpoint path
            # Try /api/v1/agents or /agents depending on endpoint format
            if '/api/v1' in self.api_endpoint:
                api_path = '/agents'
            elif self.api_endpoint.endswith('/api'):
                api_path = '/v1/agents'
            else:
                api_path = '/api/v1/agents'
            
            api_url = f'{self.api_endpoint}{api_path}'
            _logger.info(f"Creating agent via REST API: {api_url}")
            
            # Make API request
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
            }
            
            response = requests.post(
                api_url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                # Extract agent ID from response
                agent_id = result.get('id') or result.get('agent_id') or result.get('data', {}).get('id')
                
                _logger.info(f"Agent created successfully via REST API: {name} (ID: {agent_id})")
                
                return {
                    'status': 'success',
                    'agent_id': str(agent_id) if agent_id else None,
                    'response': result,
                    'message': f'Agent "{name}" created successfully'
                }
            else:
                error_msg = f"API error: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = error_data.get('error', error_data.get('message', error_msg))
                except:
                    error_msg = f"{error_msg} - {response.text[:200]}"
                
                _logger.error(f"Failed to create agent via REST API: {error_msg}")
                return {
                    'status': 'error',
                    'error': f'Failed to create agent: {error_msg}'
                }
                
        except requests.exceptions.ConnectionError as e:
            error_msg = str(e)
            _logger.error(f"Connection error creating agent: {error_msg}", exc_info=True)
            return {
                'status': 'error',
                'error': f'Connection error: {error_msg}. Please check your API endpoint and network connectivity.'
            }
        except requests.exceptions.Timeout as e:
            _logger.error(f"Timeout creating agent: {e}")
            return {
                'status': 'error',
                'error': f'Request timeout. The API endpoint did not respond within {self.timeout} seconds.'
            }
        except Exception as e:
            _logger.error(f"Error creating agent via REST API: {e}", exc_info=True)
            return {
                'status': 'error',
                'error': f'Failed to create agent: {str(e)}'
            }

