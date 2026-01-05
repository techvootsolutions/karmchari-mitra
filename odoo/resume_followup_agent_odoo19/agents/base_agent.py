# -*- coding: utf-8 -*-
"""
Base Agent class for all agent implementations
Adapted for Odoo
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional
import json


class BaseAgent(ABC):
    """Abstract base class for all agents"""
    
    def __init__(self, settings: Dict):
        self.settings = settings
        self.conversation_history = []
        self.current_step = 0
        self.collected_info = {}
        
        # Conversation flow
        self.conversation_flow = self._initialize_conversation_flow()
    
    def _initialize_conversation_flow(self) -> List[Dict]:
        """Initialize the conversation flow"""
        return [
            {
                "step": "greeting",
                "message": f"Hi {{candidate_name}}, this is {self.settings.get('agent_name', 'Agent')} "
                          f"from {self.settings.get('company_name', 'Company')}. "
                          f"I hope I'm not catching you at a bad time.",
                "expected_response": "greeting_confirmation",
                "collect_field": None
            },
            {
                "step": "purpose",
                "message": "I'm calling to follow up on your resume submission for the "
                          f"{self.settings.get('job_title', 'position')} position. Is now a good time to talk?",
                "expected_response": "time_confirmation",
                "collect_field": None
            },
            {
                "step": "explanation",
                "message": "Great! I need to gather a few more pieces of information "
                          "to complete your application. This will help us move forward "
                          "in the recruitment process. Are you comfortable proceeding?",
                "expected_response": "proceed_confirmation",
                "collect_field": None
            },
            {
                "step": "question1",
                "message": "Could you please give us a brief introduction about yourself?",
                "expected_response": "introduction",
                "collect_field": "introduction"
            },
            {
                "step": "question2",
                "message": "Thank you. May I know your current position?",
                "expected_response": "current_position",
                "collect_field": "current_position"
            },
            {
                "step": "question3",
                "message": "What is your current salary?",
                "expected_response": "current_salary",
                "collect_field": "current_salary"
            },
            {
                "step": "question4",
                "message": "What would be your expected salary for this role?",
                "expected_response": "expected_salary",
                "collect_field": "expected_salary"
            },
            {
                "step": "question5",
                "message": "What is your notice period with your current employer?",
                "expected_response": "notice_period",
                "collect_field": "notice_period"
            },
            {
                "step": "closing",
                "message": "Thank you for providing these details. This information helps us "
                          "proceed with your application. If we need any more information, "
                          "we'll be in touch. Have a fantastic day!",
                "expected_response": "closing",
                "collect_field": None
            }
        ]
    
    @abstractmethod
    def process_input(self, user_input: str) -> str:
        """Process user input and return agent response"""
        pass
    
    @abstractmethod
    def initialize_conversation(self, candidate_name: str) -> str:
        """Initialize conversation with candidate"""
        pass
    
    def get_next_message(self) -> str:
        """Get the next message in the conversation flow"""
        if self.current_step < len(self.conversation_flow):
            return self.conversation_flow[self.current_step]["message"]
        return ""
    
    def process_response(self, user_input: str) -> Dict:
        """Process user response and return agent response"""
        response = {
            "agent_message": "",
            "should_continue": True,
            "collected_data": None
        }
        
        if self.current_step >= len(self.conversation_flow):
            response["agent_message"] = "Thank you for the conversation. Have a great day!"
            response["should_continue"] = False
            return response
        
        current_flow = self.conversation_flow[self.current_step]
        
        # Store collected information
        if current_flow.get("collect_field") and user_input:
            self.collected_info[current_flow["collect_field"]] = user_input
        
        # Move to next step
        self.current_step += 1
        
        # Get next message
        if self.current_step < len(self.conversation_flow):
            response["agent_message"] = self.conversation_flow[self.current_step]["message"]
        else:
            response["agent_message"] = "Thank you for the conversation. Have a great day!"
            response["should_continue"] = False
        
        # Add acknowledgement for user input
        if user_input and self.current_step > 0:
            response["agent_message"] = "Thank you for sharing that. " + response["agent_message"]
        
        # Add collected data to response
        if current_flow.get("collect_field") and user_input:
            response["collected_data"] = {
                current_flow["collect_field"]: user_input
            }
        
        return response
    
    def get_conversation_summary(self) -> Dict:
        """Get summary of the conversation"""
        return {
            "total_steps": len(self.conversation_flow),
            "current_step": self.current_step,
            "collected_info": self.collected_info,
            "completion_percentage": (self.current_step / len(self.conversation_flow)) * 100
        }
    
    def reset(self):
        """Reset the agent state"""
        self.current_step = 0
        self.collected_info = {}
        self.conversation_history = []
    
    def format_message(self, message: str, **kwargs) -> str:
        """Format message with provided variables"""
        try:
            return message.format(**kwargs)
        except (KeyError, ValueError):
            return message

