# -*- coding: utf-8 -*-

import logging
import re
from odoo import models, fields, api
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class JobPosition(models.Model):
    _name = 'job.position'
    _description = 'Job Position with Hiring Criteria'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Job Title',
        required=True,
        tracking=True,
        help='Name of the job position (e.g., Senior Software Engineer)'
    )
    code = fields.Char(
        string='Job Code',
        help='Internal job code or reference number'
    )
    description = fields.Text(
        string='Job Description',
        help='Detailed job description'
    )
    
    # Hiring Criteria
    positions_to_fill = fields.Integer(
        string='Positions to Fill',
        required=True,
        default=1,
        tracking=True,
        help='Number of positions available for this job'
    )
    positions_filled = fields.Integer(
        string='Positions Filled',
        compute='_compute_positions_filled',
        store=True,
        help='Number of positions already filled'
    )
    positions_remaining = fields.Integer(
        string='Positions Remaining',
        compute='_compute_positions_remaining',
        store=True,
        help='Number of positions still available'
    )
    
    # Experience Requirements
    min_experience_years = fields.Float(
        string='Minimum Experience (Years)',
        required=True,
        default=0.0,
        digits=(3, 1),
        tracking=True,
        help='Minimum years of experience required'
    )
    max_experience_years = fields.Float(
        string='Maximum Experience (Years)',
        digits=(3, 1),
        tracking=True,
        help='Maximum years of experience (leave empty for no maximum)'
    )
    
    # Salary Requirements
    min_salary = fields.Float(
        string='Minimum Expected Salary',
        digits=(12, 2),
        tracking=True,
        help='Minimum expected salary (leave empty if not required)'
    )
    max_salary = fields.Float(
        string='Maximum Expected Salary',
        digits=(12, 2),
        tracking=True,
        help='Maximum expected salary (leave empty if not required)'
    )
    salary_currency = fields.Char(
        string='Salary Currency',
        default='USD',
        tracking=True,
        help='Currency for salary range (e.g., USD, EUR, INR)'
    )
    
    # Auto-filtering settings
    auto_approve_matching = fields.Boolean(
        string='Auto-Approve Matching Candidates',
        default=True,
        tracking=True,
        help='Automatically approve candidates who match the experience criteria'
    )
    auto_reject_non_matching = fields.Boolean(
        string='Auto-Reject Non-Matching Candidates',
        default=True,
        tracking=True,
        help='Automatically reject candidates who do not match the experience criteria'
    )
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Open'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', required=True, tracking=True)
    
    # Related candidates
    candidate_ids = fields.One2many(
        'resume.candidate',
        'job_position_id',
        string='Candidates',
        help='Candidates who applied for this position'
    )
    candidate_count = fields.Integer(
        string='Total Candidates',
        compute='_compute_candidate_stats',
        store=False
    )
    approved_candidates = fields.Integer(
        string='Approved Candidates',
        compute='_compute_candidate_stats',
        store=False
    )
    rejected_candidates = fields.Integer(
        string='Rejected Candidates',
        compute='_compute_candidate_stats',
        store=False
    )
    pending_candidates = fields.Integer(
        string='Pending Candidates',
        compute='_compute_candidate_stats',
        store=False
    )
    
    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )
    
    # Dates
    date_open = fields.Date(string='Opening Date')
    date_close = fields.Date(string='Closing Date')
    create_date = fields.Datetime(string='Created On', readonly=True)

    @api.depends('candidate_ids', 'candidate_ids.status')
    def _compute_candidate_stats(self):
        """Compute candidate statistics"""
        for record in self:
            candidates = record.candidate_ids
            record.candidate_count = len(candidates)
            record.approved_candidates = len(candidates.filtered(lambda c: c.status == 'hired'))
            record.rejected_candidates = len(candidates.filtered(lambda c: c.status == 'rejected'))
            record.pending_candidates = len(candidates.filtered(lambda c: c.status == 'pending'))

    @api.depends('candidate_ids', 'candidate_ids.status')
    def _compute_positions_filled(self):
        """Compute number of positions filled"""
        for record in self:
            # Count candidates with 'hired' status
            record.positions_filled = len(record.candidate_ids.filtered(lambda c: c.status == 'hired'))

    @api.depends('positions_to_fill', 'positions_filled')
    def _compute_positions_remaining(self):
        """Compute remaining positions"""
        for record in self:
            record.positions_remaining = max(0, record.positions_to_fill - record.positions_filled)

    @api.constrains('min_experience_years', 'max_experience_years')
    def _check_experience_range(self):
        """Validate experience range"""
        for record in self:
            if record.max_experience_years and record.min_experience_years > record.max_experience_years:
                raise ValidationError(
                    'Minimum experience cannot be greater than maximum experience.'
                )
    
    @api.constrains('min_salary', 'max_salary')
    def _check_salary_range(self):
        """Validate salary range"""
        for record in self:
            if record.min_salary and record.max_salary and record.min_salary > record.max_salary:
                raise ValidationError(
                    'Minimum salary cannot be greater than maximum salary.'
                )

    def _extract_years_from_text(self, text):
        """Extract years of experience from text"""
        if not text:
            return None
        
        # Patterns to match years of experience
        patterns = [
            r'(\d+(?:\.\d+)?)\s*(?:years?|yrs?)\s*(?:of\s*)?(?:experience|exp)',
            r'experience[:\s]+(\d+(?:\.\d+)?)\s*(?:years?|yrs?)',
            r'(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)\s*(?:of\s*)?(?:experience|exp)',
            r'(\d+(?:\.\d+)?)\s*(?:years?|yrs?)',
        ]
        
        text_lower = text.lower()
        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    years = float(match.group(1))
                    return years
                except (ValueError, IndexError):
                    continue
        
        return None

    def _get_candidate_experience(self, candidate):
        """Get candidate's years of experience"""
        # Try to get from years_of_experience field
        if candidate.years_of_experience:
            try:
                # Try to extract number from string
                years_match = re.search(r'(\d+(?:\.\d+)?)', str(candidate.years_of_experience))
                if years_match:
                    return float(years_match.group(1))
            except (ValueError, AttributeError):
                pass
        
        # Try to extract from work_experience field
        if candidate.work_experience:
            years = self._extract_years_from_text(candidate.work_experience)
            if years is not None:
                return years
        
        # Try to extract from CV text
        if candidate.cv_text:
            years = self._extract_years_from_text(candidate.cv_text)
            if years is not None:
                return years
        
        return None

    def _extract_salary_from_text(self, text):
        """Extract salary from text"""
        if not text:
            return None
        
        # Patterns to match salary (various formats)
        patterns = [
            r'[\$€£₹]?\s*(\d{1,3}(?:[,\s]\d{3})*(?:\.\d{2})?)\s*(?:K|k|thousand|L|lakh|million|M)?',
            r'salary[:\s]+[\$€£₹]?\s*(\d{1,3}(?:[,\s]\d{3})*(?:\.\d{2})?)',
            r'expected\s+salary[:\s]+[\$€£₹]?\s*(\d{1,3}(?:[,\s]\d{3})*(?:\.\d{2})?)',
            r'current\s+salary[:\s]+[\$€£₹]?\s*(\d{1,3}(?:[,\s]\d{3})*(?:\.\d{2})?)',
            r'(\d{1,3}(?:[,\s]\d{3})*(?:\.\d{2})?)\s*(?:K|k|thousand|L|lakh)',
        ]
        
        text_lower = text.lower()
        for pattern in patterns:
            matches = re.finditer(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                try:
                    salary_str = match.group(1).replace(',', '').replace(' ', '')
                    salary = float(salary_str)
                    
                    # Check for multipliers (K = thousand, L = lakh, M = million)
                    multiplier = 1
                    if 'k' in match.group(0).lower() or 'thousand' in match.group(0).lower():
                        multiplier = 1000
                    elif 'l' in match.group(0).lower() or 'lakh' in match.group(0).lower():
                        multiplier = 100000
                    elif 'm' in match.group(0).lower() or 'million' in match.group(0).lower():
                        multiplier = 1000000
                    
                    return salary * multiplier
                except (ValueError, IndexError):
                    continue
        
        return None

    def _get_candidate_salary(self, candidate):
        """Get candidate's expected salary"""
        # Try to get from expected_salary field
        if candidate.expected_salary:
            try:
                # Try to extract number from string
                salary_match = re.search(r'(\d{1,3}(?:[,\s]\d{3})*(?:\.\d{2})?)', str(candidate.expected_salary))
                if salary_match:
                    salary_str = salary_match.group(1).replace(',', '').replace(' ', '')
                    return float(salary_str)
            except (ValueError, AttributeError):
                pass
        
        # Try to extract from collected_info (from conversations)
        if candidate.expected_salary:
            salary = self._extract_salary_from_text(candidate.expected_salary)
            if salary is not None:
                return salary
        
        # Try to extract from CV text
        if candidate.cv_text:
            salary = self._extract_salary_from_text(candidate.cv_text)
            if salary is not None:
                return salary
        
        return None

    def _candidate_matches_experience(self, candidate):
        """Check if candidate matches experience requirements"""
        candidate_years = self._get_candidate_experience(candidate)
        
        if candidate_years is None:
            # If we can't determine experience, consider it as not matching
            return False, candidate_years
        
        # Check if within range
        matches_min = candidate_years >= self.min_experience_years
        matches_max = not self.max_experience_years or candidate_years <= self.max_experience_years
        
        matches = matches_min and matches_max
        return matches, candidate_years

    def _candidate_matches_salary(self, candidate):
        """Check if candidate matches salary requirements"""
        # If no salary requirements, consider it as matching
        if not self.min_salary and not self.max_salary:
            return True, None
        
        candidate_salary = self._get_candidate_salary(candidate)
        
        if candidate_salary is None:
            # If we can't determine salary and salary is required, consider it as not matching
            if self.min_salary or self.max_salary:
                return False, None
            return True, None
        
        # Check if within range
        matches_min = not self.min_salary or candidate_salary >= self.min_salary
        matches_max = not self.max_salary or candidate_salary <= self.max_salary
        
        matches = matches_min and matches_max
        return matches, candidate_salary

    def action_evaluate_candidate(self, candidate):
        """Evaluate a candidate against this job position criteria (experience and salary)"""
        self.ensure_one()
        candidate.ensure_one()
        
        exp_matches, years = self._candidate_matches_experience(candidate)
        sal_matches, salary = self._candidate_matches_salary(candidate)
        
        # Candidate matches if BOTH experience and salary match (if salary is required)
        overall_matches = exp_matches and sal_matches
        
        result = {
            'matches': overall_matches,
            'experience_matches': exp_matches,
            'salary_matches': sal_matches,
            'years_found': years,
            'salary_found': salary,
            'min_experience_required': self.min_experience_years,
            'max_experience_required': self.max_experience_years,
            'min_salary_required': self.min_salary,
            'max_salary_required': self.max_salary,
            'reasons': []
        }
        
        # Experience evaluation
        if years is None:
            result['reasons'].append('Could not determine candidate experience from CV')
        elif not exp_matches:
            if years < self.min_experience_years:
                result['reasons'].append(f'Experience too low: {years} years (required: {self.min_experience_years}+)')
            elif self.max_experience_years and years > self.max_experience_years:
                result['reasons'].append(f'Experience too high: {years} years (max: {self.max_experience_years})')
        else:
            result['reasons'].append(f'✓ Experience matches: {years} years')
        
        # Salary evaluation (only if salary is required)
        if self.min_salary or self.max_salary:
            if salary is None:
                result['reasons'].append('Could not determine candidate salary from CV')
            elif not sal_matches:
                if self.min_salary and salary < self.min_salary:
                    result['reasons'].append(f'Salary too low: {salary:,.0f} (required: {self.min_salary:,.0f}+)')
                elif self.max_salary and salary > self.max_salary:
                    result['reasons'].append(f'Salary too high: {salary:,.0f} (max: {self.max_salary:,.0f})')
            else:
                result['reasons'].append(f'✓ Salary matches: {salary:,.0f}')
        
        result['reason'] = ' | '.join(result['reasons'])
        
        return result

    def action_auto_filter_candidates(self):
        """Automatically filter all candidates for this position (experience and salary)"""
        self.ensure_one()
        
        if not self.auto_approve_matching and not self.auto_reject_non_matching:
            raise ValidationError('Please enable at least one auto-filtering option.')
        
        candidates = self.candidate_ids.filtered(lambda c: c.status in ['pending', 'contacted'])
        processed = 0
        approved = 0
        rejected = 0
        
        for candidate in candidates:
            exp_matches, years = self._candidate_matches_experience(candidate)
            sal_matches, salary = self._candidate_matches_salary(candidate)
            
            # Candidate matches if BOTH experience and salary match (if salary is required)
            overall_matches = exp_matches and sal_matches
            
            if overall_matches and self.auto_approve_matching:
                # Check if positions are still available
                if self.positions_remaining > 0:
                    reasons = []
                    if exp_matches and years is not None:
                        reasons.append(f'Experience: {years} years')
                    if sal_matches and salary is not None:
                        reasons.append(f'Salary: {salary:,.0f}')
                    
                    candidate.write({
                        'status': 'interviewed',  # Approve by moving to interviewed
                        'notes': (candidate.notes or '') + f'\n[Auto-approved] Matches requirements ({", ".join(reasons)})'
                    })
                    approved += 1
                else:
                    candidate.write({
                        'notes': (candidate.notes or '') + f'\n[Note] Matches criteria but all positions are filled'
                    })
            elif not overall_matches and self.auto_reject_non_matching:
                reasons = []
                
                # Experience reasons
                if not exp_matches:
                    if years is None:
                        reasons.append('Could not determine experience')
                    elif years < self.min_experience_years:
                        reasons.append(f'Experience too low ({years} years, required: {self.min_experience_years}+)')
                    elif self.max_experience_years and years > self.max_experience_years:
                        reasons.append(f'Experience too high ({years} years, max: {self.max_experience_years})')
                
                # Salary reasons (only if salary is required)
                if (self.min_salary or self.max_salary) and not sal_matches:
                    if salary is None:
                        reasons.append('Could not determine salary')
                    elif self.min_salary and salary < self.min_salary:
                        reasons.append(f'Salary too low ({salary:,.0f}, required: {self.min_salary:,.0f}+)')
                    elif self.max_salary and salary > self.max_salary:
                        reasons.append(f'Salary too high ({salary:,.0f}, max: {self.max_salary:,.0f})')
                
                reason = ' | '.join(reasons) if reasons else 'Does not match requirements'
                
                candidate.write({
                    'status': 'rejected',
                    'notes': (candidate.notes or '') + f'\n[Auto-rejected] {reason}'
                })
                rejected += 1
            
            processed += 1
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Auto-Filtering Complete',
                'message': f'Processed {processed} candidates: {approved} approved, {rejected} rejected',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_view_candidates(self):
        """View all candidates for this position"""
        self.ensure_one()
        return {
            'name': f'Candidates - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'resume.candidate',
            'view_mode': 'list,form',
            'domain': [('job_position_id', '=', self.id)],
            'context': {'default_job_position_id': self.id}
        }

    def action_open(self):
        """Open the job position"""
        self.write({'state': 'open', 'date_open': fields.Date.today()})

    def action_close(self):
        """Close the job position"""
        self.write({'state': 'closed', 'date_close': fields.Date.today()})

    def action_cancel(self):
        """Cancel the job position"""
        self.write({'state': 'cancelled'})
