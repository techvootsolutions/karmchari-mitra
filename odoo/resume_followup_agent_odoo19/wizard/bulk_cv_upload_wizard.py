# -*- coding: utf-8 -*-

import base64
import logging
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class BulkCVUploadWizard(models.TransientModel):
    _name = 'bulk.cv.upload.wizard'
    _description = 'Bulk CV Upload and ATS Analysis Wizard'

    name = fields.Char(string='Batch Name', default='Bulk CV Upload', required=True)
    cv_files = fields.Many2many(
        'ir.attachment',
        'bulk_cv_upload_attachment_rel',
        'wizard_id',
        'attachment_id',
        string='CV Files',
        help='Select multiple CV files to upload and analyze. Upload files first using the attachment button.'
    )
    auto_extract = fields.Boolean(
        string='Auto Extract CV Data',
        default=True,
        help='Automatically extract data from CVs after upload'
    )
    auto_analyze_ats = fields.Boolean(
        string='Auto Run ATS Analysis',
        default=True,
        help='Automatically run ATS analysis after extraction'
    )
    position = fields.Char(
        string='Position Applied',
        help='Default position for all candidates (can be overridden per candidate)'
    )
    job_position_id = fields.Many2one(
        'job.position',
        string='Job Position',
        help='Link candidates to a job position for automatic filtering'
    )
    source = fields.Selection([
        ('website', 'Website'),
        ('linkedin', 'LinkedIn'),
        ('referral', 'Referral'),
        ('job_portal', 'Job Portal'),
        ('other', 'Other')
    ], string='Source', default='website')
    
    # Results
    total_files = fields.Integer(string='Total Files', compute='_compute_results', store=False)
    processed_count = fields.Integer(string='Processed', compute='_compute_results', store=False)
    success_count = fields.Integer(string='Successful', compute='_compute_results', store=False)
    error_count = fields.Integer(string='Errors', compute='_compute_results', store=False)
    candidate_ids = fields.Many2many(
        'resume.candidate',
        'bulk_cv_upload_candidate_rel',
        'wizard_id',
        'candidate_id',
        string='Created Candidates',
        readonly=True
    )
    processing_log = fields.Text(
        string='Processing Log',
        readonly=True,
        help='Detailed log of processing results'
    )

    @api.depends('candidate_ids')
    def _compute_results(self):
        """Compute processing results"""
        for record in self:
            record.total_files = len(record.cv_files)
            record.processed_count = len(record.candidate_ids)
            # Count successful (have CV text extracted)
            record.success_count = len(record.candidate_ids.filtered(lambda c: c.cv_text))
            record.error_count = record.total_files - record.processed_count

    def action_upload_and_process(self):
        """Upload CVs and process them"""
        self.ensure_one()
        
        if not self.cv_files:
            raise ValidationError('Please select at least one CV file to upload.')
        
        created_candidates = self.env['resume.candidate']
        log_lines = [f"=== BULK CV UPLOAD PROCESSING ===", f"Batch: {self.name}", ""]
        
        for attachment in self.cv_files:
            try:
                # Extract filename
                filename = attachment.name or 'unknown.pdf'
                file_data = attachment.datas
                
                # Try to extract name from filename (remove extension)
                candidate_name = filename.rsplit('.', 1)[0].replace('_', ' ').replace('-', ' ').title()
                
                # Create candidate
                candidate_vals = {
                    'name': candidate_name,
                    'position': self.position or 'Not Specified',
                    'source': self.source,
                    'cv_file': file_data,
                    'cv_filename': filename,
                    'job_position_id': self.job_position_id.id if self.job_position_id else False,
                }
                
                candidate = self.env['resume.candidate'].create(candidate_vals)
                created_candidates |= candidate
                
                log_lines.append(f"✓ Created candidate: {candidate_name} (ID: {candidate.id})")
                
                # Auto extract if enabled
                if self.auto_extract:
                    try:
                        candidate._extract_and_populate_cv_data()
                        log_lines.append(f"  ✓ Extracted CV data for {candidate_name}")
                        
                        # Auto evaluate against job position if linked
                        if self.job_position_id and self.job_position_id.state == 'open':
                            try:
                                candidate._auto_evaluate_job_position()
                                if candidate.status == 'interviewed':
                                    log_lines.append(f"  ✓ Auto-approved {candidate_name} (matches criteria)")
                                elif candidate.status == 'rejected':
                                    log_lines.append(f"  ✗ Auto-rejected {candidate_name} (does not match criteria)")
                            except Exception as e:
                                log_lines.append(f"  ⚠ Evaluation failed for {candidate_name}: {str(e)}")
                        
                        # Auto analyze if enabled
                        if self.auto_analyze_ats and candidate.cv_text:
                            try:
                                candidate.action_run_ats_analysis()
                                log_lines.append(f"  ✓ Ran ATS analysis for {candidate_name} (Score: {candidate.ats_overall_score:.1f})")
                            except Exception as e:
                                log_lines.append(f"  ✗ ATS analysis failed for {candidate_name}: {str(e)}")
                    except Exception as e:
                        log_lines.append(f"  ✗ Extraction failed for {candidate_name}: {str(e)}")
                
            except Exception as e:
                log_lines.append(f"✗ Error processing {attachment.name}: {str(e)}")
                _logger.error(f"Error processing attachment {attachment.id}: {e}", exc_info=True)
        
        # Update wizard with results
        self.write({
            'candidate_ids': [(6, 0, created_candidates.ids)],
            'processing_log': '\n'.join(log_lines)
        })
        
        # Return action to view created candidates
        return {
            'type': 'ir.actions.act_window',
            'name': f'Bulk Upload Results - {self.name}',
            'res_model': 'resume.candidate',
            'view_mode': 'list,form',
            'domain': [('id', 'in', created_candidates.ids)],
            'context': {'create': False},
        }

    def action_view_candidates(self):
        """View created candidates"""
        self.ensure_one()
        if not self.candidate_ids:
            raise UserError('No candidates have been created yet.')
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'Candidates - {self.name}',
            'res_model': 'resume.candidate',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.candidate_ids.ids)],
            'context': {'create': False},
        }
