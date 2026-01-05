# -*- coding: utf-8 -*-
"""
Phone-based agent implementation for Odoo
Adapted from voice_agent for phone call management
"""

import json
from typing import Dict, Optional
from datetime import datetime

from .base_agent import BaseAgent


class PhoneAgent(BaseAgent):
    """Phone-based agent for managing phone call conversations"""
    
    def __init__(self, settings: Dict):
        super().__init__(settings)
        self.call_start_time = None
        self.call_end_time = None
        self.call_duration = 0.0
        self.is_call_active = False

    def initialize_conversation(self, candidate_name: str) -> str:
        """Initialize phone conversation"""
        self.call_start_time = datetime.now()
        self.is_call_active = True
        welcome_message = self.conversation_flow[0]["message"].format(
            candidate_name=candidate_name,
            agent_name=self.settings.get('agent_name', 'Agent'),
            company_name=self.settings.get('company_name', 'Company')
        )
        return welcome_message

    def process_input(self, user_input: str) -> str:
        """Process user input and return response"""
        response = self.process_response(user_input)
        return response["agent_message"]

    def start_call(self):
        """Start phone call"""
        self.call_start_time = datetime.now()
        self.is_call_active = True
        self.reset()

    def end_call(self):
        """End phone call"""
        if self.call_start_time:
            self.call_end_time = datetime.now()
            delta = self.call_end_time - self.call_start_time
            self.call_duration = delta.total_seconds() / 60.0  # Duration in minutes
        self.is_call_active = False

    def get_call_duration(self) -> float:
        """Get call duration in minutes"""
        if self.call_start_time and self.call_end_time:
            return self.call_duration
        elif self.call_start_time:
            delta = datetime.now() - self.call_start_time
            return delta.total_seconds() / 60.0
        return 0.0

    def get_conversation_data(self) -> Dict:
        """Get conversation data for saving"""
        return {
            'conversation_history': self.conversation_history,
            'collected_info': self.collected_info,
            'call_start_time': self.call_start_time.isoformat() if self.call_start_time else None,
            'call_end_time': self.call_end_time.isoformat() if self.call_end_time else None,
            'call_duration': self.get_call_duration(),
            'current_step': self.current_step,
            'total_steps': len(self.conversation_flow)
        }

    def load_conversation_flow(self, questions: Dict):
        """Load custom conversation flow from questions dictionary or list"""
        if isinstance(questions, list):
            # If questions is a list (from agent settings), use it directly
            self.conversation_flow = []
            for q in questions:
                self.conversation_flow.append({
                    "step": q.get('step', q.get('step_type', 'question')),
                    "message": q.get('message', ''),
                    "expected_response": q.get('expected_response', q.get('step', q.get('step_type', 'question'))),
                    "collect_field": q.get('collect_field')
                })
        elif isinstance(questions, dict):
            # If questions is a dict (legacy format), convert to flow
            self.conversation_flow = []

            # Add greeting if exists
            if 'question_greeting' in questions:
                self.conversation_flow.append({
                    "step": "greeting",
                    "message": questions.get('question_greeting', ''),
                    "expected_response": "greeting_confirmation",
                    "collect_field": None
                })

            # Add dynamic questions (any key starting with 'question_' that's not a standard one)
            standard_questions = ['question_greeting']
            question_keys = [k for k in questions.keys() if k.startswith('question_') and k not in standard_questions]
            for key in sorted(question_keys):
                # Extract field name from key (e.g., 'question_introduction' -> 'introduction')
                field_name = key.replace('question_', '')
                self.conversation_flow.append({
                    "step": "question",
                    "message": questions.get(key, ''),
                    "expected_response": field_name,
                    "collect_field": field_name
                })

            # Add closing if exists
            if 'question_closing' in questions:
                self.conversation_flow.append({
                    "step": "closing",
                    "message": questions.get('question_closing', ''),
                    "expected_response": "closing",
                    "collect_field": None
                })

