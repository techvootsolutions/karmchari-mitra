# -*- coding: utf-8 -*-

import logging
from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResumeDashboard(models.TransientModel):
    _name = 'resume.dashboard'
    _description = 'Resume Follow-Up Dashboard Statistics'
    _log_access = True  # Required for TransientModels

    # Sentiment Statistics
    total_interviews = fields.Integer(string='Total Interviews', compute='_compute_all_stats', store=False)
    positive_count = fields.Integer(string='Positive Interviews', compute='_compute_all_stats', store=False)
    negative_count = fields.Integer(string='Negative Interviews', compute='_compute_all_stats', store=False)
    neutral_count = fields.Integer(string='Neutral Interviews', compute='_compute_all_stats', store=False)
    positive_percentage = fields.Float(string='Positive %', compute='_compute_all_stats', digits=(5, 2), store=False)
    negative_percentage = fields.Float(string='Negative %', compute='_compute_all_stats', digits=(5, 2), store=False)
    neutral_percentage = fields.Float(string='Neutral %', compute='_compute_all_stats', digits=(5, 2), store=False)

    # Salary Statistics
    avg_current_salary = fields.Float(string='Avg Current Salary', compute='_compute_all_stats', digits=(12, 2), store=False)
    avg_expected_salary = fields.Float(string='Avg Expected Salary', compute='_compute_all_stats', digits=(12, 2), store=False)
    min_current_salary = fields.Float(string='Min Current Salary', compute='_compute_all_stats', digits=(12, 2), store=False)
    max_current_salary = fields.Float(string='Max Current Salary', compute='_compute_all_stats', digits=(12, 2), store=False)
    min_expected_salary = fields.Float(string='Min Expected Salary', compute='_compute_all_stats', digits=(12, 2), store=False)
    max_expected_salary = fields.Float(string='Max Expected Salary', compute='_compute_all_stats', digits=(12, 2), store=False)

    @api.model
    def create(self, vals):
        """Auto-compute stats when dashboard record is created"""
        record = super().create(vals or {})
        record._compute_all_stats()
        return record
    
    def _parse_salary(self, salary_str):
        """Parse salary string to float (handles formats like '1,00,000', '50000', etc.)"""
        if not salary_str:
            return 0.0
        try:
            # Remove commas and spaces
            cleaned = str(salary_str).replace(',', '').replace(' ', '').strip()
            # Try to extract number if there's text
            import re
            numbers = re.findall(r'\d+', cleaned)
            if numbers:
                return float(numbers[0])
            return 0.0
        except (ValueError, TypeError):
            return 0.0

    def _compute_all_stats(self):
        """Compute all statistics (sentiment and salary)"""
        conversations = self.env['resume.conversation'].search([
            ('status', '=', 'completed')
        ])
        
        # Sentiment Statistics
        total = len(conversations)
        positive = len(conversations.filtered(lambda c: c.sentiment == 'positive'))
        negative = len(conversations.filtered(lambda c: c.sentiment == 'negative'))
        neutral = len(conversations.filtered(lambda c: c.sentiment == 'neutral'))
        
        # Salary Statistics
        current_salaries = []
        expected_salaries = []
        
        for conv in conversations:
            if conv.current_salary:
                salary = self._parse_salary(conv.current_salary)
                if salary > 0:
                    current_salaries.append(salary)
            
            if conv.expected_salary:
                salary = self._parse_salary(conv.expected_salary)
                if salary > 0:
                    expected_salaries.append(salary)
        
        for record in self:
            # Sentiment stats
            record.total_interviews = total
            record.positive_count = positive
            record.negative_count = negative
            record.neutral_count = neutral
            
            if total > 0:
                record.positive_percentage = (positive / total) * 100
                record.negative_percentage = (negative / total) * 100
                record.neutral_percentage = (neutral / total) * 100
            else:
                record.positive_percentage = 0.0
                record.negative_percentage = 0.0
                record.neutral_percentage = 0.0
            
            # Salary stats
            if current_salaries:
                record.avg_current_salary = sum(current_salaries) / len(current_salaries)
                record.min_current_salary = min(current_salaries)
                record.max_current_salary = max(current_salaries)
            else:
                record.avg_current_salary = 0.0
                record.min_current_salary = 0.0
                record.max_current_salary = 0.0
            
            if expected_salaries:
                record.avg_expected_salary = sum(expected_salaries) / len(expected_salaries)
                record.min_expected_salary = min(expected_salaries)
                record.max_expected_salary = max(expected_salaries)
            else:
                record.avg_expected_salary = 0.0
                record.min_expected_salary = 0.0
                record.max_expected_salary = 0.0
