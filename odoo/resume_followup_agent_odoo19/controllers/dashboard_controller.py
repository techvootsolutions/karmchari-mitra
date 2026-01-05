# -*- coding: utf-8 -*-

import json
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class DashboardController(http.Controller):

    @http.route('/resume_followup/dashboard', type='http', auth='user', website=True)
    def dashboard(self, **kwargs):
        """Render the modern dashboard page"""
        # Get dashboard statistics
        conversations = request.env['resume.conversation'].search([
            ('status', '=', 'completed')
        ])
        
        # Calculate statistics
        total_interviews = len(conversations)
        positive_count = len(conversations.filtered(lambda c: c.sentiment == 'positive'))
        negative_count = len(conversations.filtered(lambda c: c.sentiment == 'negative'))
        neutral_count = len(conversations.filtered(lambda c: c.sentiment == 'neutral'))
        
        positive_percentage = (positive_count / total_interviews * 100) if total_interviews > 0 else 0
        negative_percentage = (negative_count / total_interviews * 100) if total_interviews > 0 else 0
        neutral_percentage = (neutral_count / total_interviews * 100) if total_interviews > 0 else 0
        
        # Calculate salary statistics
        def parse_salary(salary_str):
            if not salary_str:
                return 0.0
            try:
                cleaned = str(salary_str).replace(',', '').replace(' ', '').strip()
                import re
                numbers = re.findall(r'\d+', cleaned)
                if numbers:
                    return float(numbers[0])
                return 0.0
            except (ValueError, TypeError):
                return 0.0
        
        current_salaries = [parse_salary(c.current_salary) for c in conversations if c.current_salary]
        expected_salaries = [parse_salary(c.expected_salary) for c in conversations if c.expected_salary]
        
        current_salaries = [s for s in current_salaries if s > 0]
        expected_salaries = [s for s in expected_salaries if s > 0]
        
        avg_current_salary = sum(current_salaries) / len(current_salaries) if current_salaries else 0
        min_current_salary = min(current_salaries) if current_salaries else 0
        max_current_salary = max(current_salaries) if current_salaries else 0
        
        avg_expected_salary = sum(expected_salaries) / len(expected_salaries) if expected_salaries else 0
        min_expected_salary = min(expected_salaries) if expected_salaries else 0
        max_expected_salary = max(expected_salaries) if expected_salaries else 0
        
        # Get recent conversations
        recent_conversations = conversations.sorted('timestamp', reverse=True)[:5]
        
        # Calculate average call duration
        durations = [c.duration for c in conversations if c.duration and c.duration > 0]
        avg_duration_minutes = sum(durations) / len(durations) if durations else 0
        minutes = int(avg_duration_minutes)
        seconds = int((avg_duration_minutes % 1) * 60)
        avg_duration_display = f"{minutes}:{seconds:02d}"
        
        # Get active candidates count
        active_candidates = request.env['resume.candidate'].search_count([
            ('status', 'in', ['contacted', 'interviewed'])
        ])
        
        stats = {
            'total_interviews': total_interviews,
            'positive_count': positive_count,
            'negative_count': negative_count,
            'neutral_count': neutral_count,
            'positive_percentage': round(positive_percentage, 1),
            'negative_percentage': round(negative_percentage, 1),
            'neutral_percentage': round(neutral_percentage, 1),
            'avg_current_salary': round(avg_current_salary, 2),
            'min_current_salary': round(min_current_salary, 2),
            'max_current_salary': round(max_current_salary, 2),
            'avg_expected_salary': round(avg_expected_salary, 2),
            'min_expected_salary': round(min_expected_salary, 2),
            'max_expected_salary': round(max_expected_salary, 2),
            'avg_duration_display': avg_duration_display,
            'active_candidates': active_candidates,
            'recent_conversations': recent_conversations,
        }
        
        # Get all candidates for candidates page
        candidates = request.env['resume.candidate'].search([])
        
        # Get all conversations for conversations page (sorted by timestamp desc)
        all_conversations = request.env['resume.conversation'].search([], order='timestamp desc')
        
        # Group conversations by date for display
        from collections import defaultdict
        conversations_by_date = defaultdict(list)
        for conv in all_conversations:
            if conv.timestamp:
                date_key = conv.timestamp.date()
                conversations_by_date[date_key].append(conv)
        
        # Convert to list of tuples (date, conversations) sorted by date desc
        conversations_grouped = sorted(conversations_by_date.items(), key=lambda x: x[0], reverse=True)
        
        # Get agent settings for agent settings page
        agent_settings = request.env['resume.agent.settings'].get_default_settings()
        
        # Get telephony config for telephony config page
        telephony_config = request.env['resume.telephony.config'].get_default_config()
        
        return request.render('resume_followup_agent_odoo19.dashboard_page', {
            'stats': stats,
            'candidates': candidates,
            'all_conversations': all_conversations,
            'conversations_grouped': conversations_grouped,
            'agent_settings': agent_settings,
            'telephony_config': telephony_config,
            'sentiment_data': json.dumps([
                {'name': 'Positive', 'value': positive_count, 'color': '#4CAF50'},
                {'name': 'Neutral', 'value': neutral_count, 'color': '#FF9800'},
                {'name': 'Negative', 'value': negative_count, 'color': '#f44336'},
            ]),
            'salary_data': json.dumps([
                {
                    'name': 'Current',
                    'Average': avg_current_salary,
                    'Minimum': min_current_salary,
                    'Maximum': max_current_salary,
                },
                {
                    'name': 'Expected',
                    'Average': avg_expected_salary,
                    'Minimum': min_expected_salary,
                    'Maximum': max_expected_salary,
                },
            ]),
        })
