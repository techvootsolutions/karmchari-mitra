# -*- coding: utf-8 -*-

import json
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class WebhookController(http.Controller):
    """Webhook controller for receiving call status updates from OmniDimension AI"""
    
    @http.route('/resume_followup/webhook/call_status', type='json', auth='public', methods=['POST'], csrf=False)
    def webhook_call_status(self, **kwargs):
        """
        Webhook endpoint for OmniDimension AI call status updates
        This endpoint receives call data when a call ends
        """
        try:
            # Get JSON data from request
            data = request.jsonrequest or {}
            _logger.info(f"📥 Webhook received: {json.dumps(data, indent=2)}")
            
            # Extract call_id from various possible keys
            call_id = (data.get('call_id') or 
                      data.get('callId') or 
                      data.get('id') or
                      data.get('data', {}).get('call_id') or
                      data.get('data', {}).get('id') or '')
            
            if not call_id:
                _logger.warning("Webhook received but no call_id found")
                return {'status': 'error', 'message': 'No call_id provided'}
            
            # Find conversation by call_id
            conversation = request.env['resume.conversation'].sudo().search([
                ('call_id', '=', str(call_id))
            ], limit=1)
            
            if not conversation:
                _logger.warning(f"Conversation not found for call_id: {call_id}")
                return {'status': 'error', 'message': 'Conversation not found'}
            
            # Update conversation with webhook data
            update_vals = {}
            
            # Update status
            call_status = data.get('status', '')
            if call_status == 'completed':
                update_vals['status'] = 'completed'
            elif call_status in ['in_progress', 'ringing', 'answered']:
                update_vals['status'] = 'in_progress'
            
            # Update transcript
            if data.get('transcript'):
                update_vals['transcript'] = data.get('transcript')
            
            # Update summary
            if data.get('summary'):
                update_vals['summary'] = data.get('summary')
            
            # Update sentiment
            if data.get('sentiment'):
                sentiment_text = str(data.get('sentiment', '')).lower()
                if 'positive' in sentiment_text:
                    update_vals['sentiment'] = 'positive'
                elif 'negative' in sentiment_text:
                    update_vals['sentiment'] = 'negative'
                else:
                    update_vals['sentiment'] = 'neutral'
            
            # Update collected data - CRITICAL
            collected_data = (data.get('collected_data') or 
                            data.get('collected_info') or 
                            data.get('data', {}).get('collected_data') or {})
            
            if collected_data:
                if isinstance(collected_data, str):
                    try:
                        collected_data = json.loads(collected_data)
                    except:
                        collected_data = {}
                
                # Store as JSON
                update_vals['collected_info'] = json.dumps(collected_data)
                
                # Extract individual fields
                if collected_data.get('introduction'):
                    update_vals['introduction'] = collected_data.get('introduction')
                    update_vals['brief_introduction'] = collected_data.get('introduction')
                if collected_data.get('current_position'):
                    update_vals['current_position'] = collected_data.get('current_position')
                if collected_data.get('current_salary'):
                    update_vals['current_salary'] = collected_data.get('current_salary')
                if collected_data.get('expected_salary'):
                    update_vals['expected_salary'] = collected_data.get('expected_salary')
                if collected_data.get('notice_period'):
                    update_vals['notice_period'] = collected_data.get('notice_period')
            
            # Update duration
            if data.get('duration'):
                update_vals['duration'] = float(data.get('duration', 0)) / 60.0  # Convert to minutes
            
            # Update recording URL
            if data.get('recording_url'):
                update_vals['call_recording_url'] = data.get('recording_url')
                update_vals['recording_url'] = data.get('recording_url')
            
            # Update detected language
            if data.get('detected_language'):
                update_vals['detected_language'] = data.get('detected_language')
            
            # Write updates
            if update_vals:
                conversation.write(update_vals)
                _logger.info(f"✅ Webhook updated conversation {conversation.id} with fields: {list(update_vals.keys())}")
            
            return {'status': 'success', 'message': 'Webhook processed successfully'}
            
        except Exception as e:
            _logger.error(f"Error processing webhook: {e}", exc_info=True)
            return {'status': 'error', 'message': str(e)}
