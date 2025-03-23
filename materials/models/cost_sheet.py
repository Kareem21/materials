from odoo import api, fields, models, _


class CostSheet(models.Model):
    _name = 'project.cost.sheet'
    _description = 'Project Cost Sheet'
    _inherit = ['mail.thread']
    _order = 'date desc, id desc'

    name = fields.Char('Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    project_id = fields.Many2one('project.project', string='Project',   required=True, tracking=True)
    date = fields.Date('Date', default=fields.Date.context_today,      required=True, tracking=True)
    company_id = fields.Many2one('res.company', string='Company',     default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    estimation_id = fields.Char('Estimation Reference')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('done', 'Done')
    ], string='Status', default='draft', tracking=True)
    total_budgeted_cost = fields.Monetary('Total Budgeted Cost', 
                                         compute='_compute_total_costs', store=True)
    line_ids = fields.One2many('project.cost.sheet.line', 'cost_sheet_id', 'Cost Lines')
    message_ids = fields.One2many(
        'mail.message', 'res_id',
        domain=lambda self: [('model', '=', self._name)],
        string='Messages',
        readonly=True)
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('project.cost.sheet') or _('New')
        return super().create(vals_list)
    
    @api.depends('line_ids.budgeted_cost')
    def _compute_total_costs(self):
        for sheet in self:
            sheet.total_budgeted_cost = sum(sheet.line_ids.mapped('budgeted_cost'))
    
    def action_draft(self):
        self.write({'state': 'draft'})
    
    def action_in_progress(self):
        self.write({'state': 'in_progress'})
    
    def action_done(self):
        self.write({'state': 'done'})


class CostSheetLine(models.Model):
    _name = 'project.cost.sheet.line'
    _description = 'Project Cost Sheet Line'
    
    cost_sheet_id = fields.Many2one('project.cost.sheet', 'Cost Sheet', 
                                    required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', 'Product', required=True)
    cost_code = fields.Char('Cost Code')
    cost_type = fields.Selection([
        ('material', 'Material'),
    ], string='Cost Type', default='material', required=True)
    
    # Budget fields
    quantity = fields.Float('Quantity', required=True, default=1.0)
    uom_id = fields.Many2one('uom.uom', 'Unit of Measure', 
                             related='product_id.uom_id', store=True)
    unit_cost = fields.Monetary('Unit Cost', required=True)
    budgeted_cost = fields.Monetary('Budgeted Cost', compute='_compute_costs', store=True)
    
    currency_id = fields.Many2one('res.currency', related='cost_sheet_id.currency_id')
    company_id = fields.Many2one('res.company', related='cost_sheet_id.company_id')
    
    _sql_constraints = [
        ('positive_quantity', 'CHECK(quantity > 0)', 'Quantity must be positive!')
    ]
    
    @api.depends('quantity', 'unit_cost')
    def _compute_costs(self):
        for line in self:
            line.budgeted_cost = line.quantity * line.unit_cost