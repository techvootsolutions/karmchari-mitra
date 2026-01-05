# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResumeConversationQuestion(models.Model):
    _name = 'resume.conversation.question'
    _description = 'Resume Conversation Question'
    _order = 'sequence, id'

    agent_settings_id = fields.Many2one(
        'resume.agent.settings',
        string='Agent Settings',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(string='Sequence', default=10, required=True, help='Order of the question in conversation flow')
    step_type = fields.Selection([
        ('greeting', 'Greeting'),
        ('purpose', 'Purpose'),
        ('explanation', 'Explanation'),
        ('question', 'Question'),
        ('closing', 'Closing')
    ], string='Step Type', required=True, default='question')
    message = fields.Text(
        string='Message/Question',
        required=True,
        help='The message or question to ask. Use {candidate_name}, {agent_name}, {company_name}, {job_title} as placeholders.'
    )
    collect_field = fields.Char(
        string='Collect Field',
        help='Field name to store the response (e.g., introduction, current_position). Leave empty if not collecting data.'
    )
    field_label = fields.Char(
        string='Field Label',
        help='Human-readable label for the collected field (e.g., "Introduction", "Current Position")'
    )
    active = fields.Boolean(string='Active', default=True)

