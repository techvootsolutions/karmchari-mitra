# -*- coding: utf-8 -*-
"""
Agent factory for creating different types of agents
Adapted for Odoo
"""

from typing import Dict, Optional
from .phone_agent import PhoneAgent


class AgentFactory:
    """Factory class for creating agents"""
    
    @staticmethod
    def create_agent(agent_type: str, settings: Dict):
        """Create an agent of specified type"""
        if agent_type.lower() == 'voice':
            return PhoneAgent(settings)
        else:
            raise ValueError(f"Unknown agent type: {agent_type}. Supported types: voice")
    
    @staticmethod
    def get_available_agent_types() -> list:
        """Get list of available agent types"""
        return ['phone']
    
    @staticmethod
    def get_agent_capabilities(agent_type: str) -> Dict:
        """Get capabilities of specified agent type"""
        capabilities = {
            'voice': {
                'input_method': 'audio',
                'output_method': 'audio',
                'features': ['speech_to_text', 'text_to_speech', 'real_time_conversation'],
                'requirements': ['microphone', 'speakers']
            }
        }
        
        return capabilities.get(agent_type.lower(), {})

