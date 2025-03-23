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
    total_committed_amount = fields.Monetary('Total Committed Amount',
                                           compute='_compute_total_costs', store=True)
    total_actual_amount = fields.Monetary('Total Actual Amount',
                                         compute='_compute_total_costs', store=True)
    total_remaining_budget = fields.Monetary('Total Remaining Budget',
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

    @api.depends('line_ids.budgeted_cost', 'line_ids.committed_amount', 'line_ids.actual_amount', 'line_ids.remaining_budget')
    def _compute_total_costs(self):
        for sheet in self:
            sheet.total_budgeted_cost = sum(sheet.line_ids.mapped('budgeted_cost'))
            sheet.total_committed_amount = sum(sheet.line_ids.mapped('committed_amount'))
            sheet.total_actual_amount = sum(sheet.line_ids.mapped('actual_amount'))
            sheet.total_remaining_budget = sum(sheet.line_ids.mapped('remaining_budget'))

    def action_draft(self):
        self.write({'state': 'draft'})

    def action_in_progress(self):
        self.write({'state': 'in_progress'})

    def action_done(self):
        self.write({'state': 'done'})
    
    def action_update_actuals(self):
        """Update actual costs from analytic lines"""
        for sheet in self:
            for line in sheet.line_ids:
                line._update_actual_amount()
        return True
    
    def action_update_committed(self):
        """Update committed costs from purchase orders"""
        for sheet in self:
            for line in sheet.line_ids:
                line._update_committed_amount()
        return True


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
    
    # Tracking fields
    committed_quantity = fields.Float('Committed Qty', default=0.0, 
                                     help="Quantity committed in purchase orders")
    committed_amount = fields.Monetary('Committed Amount', default=0.0,
                                      help="Amount committed in purchase orders")
    actual_amount = fields.Monetary('Actual Amount', default=0.0,
                                   help="Actual cost recorded in analytic lines")
    remaining_budget = fields.Monetary('Remaining Budget', compute='_compute_remaining_budget', store=True,
                                      help="Budgeted cost minus committed and actual amounts")
    budget_status = fields.Selection([
        ('ok', 'On Budget'),
        ('warning', 'Warning'),
        ('overrun', 'Overrun')
    ], string='Budget Status', compute='_compute_budget_status', store=True)

    currency_id = fields.Many2one('res.currency', related='cost_sheet_id.currency_id')
    company_id = fields.Many2one('res.company', related='cost_sheet_id.company_id')

    _sql_constraints = [
        ('positive_quantity', 'CHECK(quantity > 0)', 'Quantity must be positive!')
    ]

    @api.depends('quantity', 'unit_cost')
    def _compute_costs(self):
        for line in self:
            line.budgeted_cost = line.quantity * line.unit_cost
            
    @api.depends('budgeted_cost', 'committed_amount', 'actual_amount')
    def _compute_remaining_budget(self):
        for line in self:
            line.remaining_budget = line.budgeted_cost - line.committed_amount - line.actual_amount
            
    @api.depends('budgeted_cost', 'committed_amount', 'actual_amount', 'quantity', 'committed_quantity')
    def _compute_budget_status(self):
        for line in self:
            # Start with 'ok' status
            status = 'ok'
            
            # Check if committed quantity exceeds budgeted quantity
            if line.committed_quantity > line.quantity:
                status = 'overrun'
            # Check if committed + actual amount exceeds budgeted cost
            elif (line.committed_amount + line.actual_amount) > line.budgeted_cost:
                status = 'overrun'
            # Warning at 80% utilization
            elif (line.committed_amount + line.actual_amount) >= (line.budgeted_cost * 0.8):
                status = 'warning'
                
            line.budget_status = status
            
    def _update_actual_amount(self):
        """Update actual amount from analytic lines"""
        for line in self:
            domain = [
                ('project_id', '=', line.cost_sheet_id.project_id.id),
                ('product_id', '=', line.product_id.id),
                ('account_id.cost_type', '=', line.cost_type),
            ]
            if line.cost_code:
                domain.append(('account_id.code', '=', line.cost_code))
                
            analytic_lines = self.env['account.analytic.line'].search(domain)
            line.actual_amount = sum(analytic_lines.mapped('amount'))
            
    def _update_committed_amount(self):
        """Update committed amount from purchase order lines"""
        for line in self:
            domain = [
                ('account_analytic_id.project_id', '=', line.cost_sheet_id.project_id.id),
                ('product_id', '=', line.product_id.id),
                ('order_id.state', 'in', ['purchase', 'done']),
            ]
            if line.cost_code:
                domain.append(('analytic_distribution.cost_code', '=', line.cost_code))
            if line.cost_type:
                domain.append(('analytic_distribution.cost_type', '=', line.cost_type))
                
            po_lines = self.env['purchase.order.line'].search(domain)
            line.committed_quantity = sum(po_lines.mapped('product_qty'))
            line.committed_amount = sum(po_lines.mapped('price_subtotal'))
