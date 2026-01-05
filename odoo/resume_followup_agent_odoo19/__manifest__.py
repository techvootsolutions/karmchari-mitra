# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Resume Follow-Up Agent',
    'version': '19.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'AI-powered resume follow-up agent for candidate management',
    'description': """
Resume Follow-Up Agent
======================
A comprehensive module for managing candidate follow-up conversations using AI agents.

Features:
---------
* Candidate Management: Add, view, and manage candidates
* Conversation Tracking: Track all follow-up conversations with candidates
* AI Agent System: Automated text-based conversations to collect candidate information
* Analytics Dashboard: View call statistics and performance metrics
* Report Generation: Export conversation reports and analytics
* Agent Settings: Configure agent behavior and conversation flow
    """,
    'author': 'Techvoot Solution',
    'website': 'https://www.techvoot.com',
    'depends': [
        'base',
        'mail',
        'hr',
        'hr_recruitment',
        'web',
        'website',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/resume_followup_data.xml',
        'views/resume_conversation_question_views.xml',
        'views/resume_telephony_config_views.xml',
        'views/resume_candidate_views.xml',
        'views/resume_conversation_views.xml',
        'views/resume_conversation_wizard_views.xml',
        'views/resume_conversation_wizard_call_interface.xml',
        'views/resume_agent_settings_views.xml',
        'views/resume_dashboard_views.xml',
        'views/bulk_cv_upload_wizard_views.xml',
        'views/job_position_views.xml',
        'views/menuitems.xml',
        'views/dashboard_page.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}

