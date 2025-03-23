#hi !
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockRequestLine(models.Model):
    _name = 'stock.request.line'
    _description = 'Stock Request Line'
    
    name = fields.Char('Description')
    request_id = fields.Many2one('stock.request', 'Request', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', 'Product', required=True)
    quantity = fields.Float('Quantity', required=True)
    uom_id = fields.Many2one('uom.uom', 'Unit of Measure', related='product_id.uom_id')
    project_id = fields.Many2one('project.project', related='request_id.project_id', store=True)
    cost_sheet_line_id = fields.Many2one('project.cost.sheet.line', 'Cost Sheet Line')
    qty_in_progress = fields.Float('Qty In Progress', default=0.0)
    qty_done = fields.Float('Qty Done', default=0.0)
    budget_status = fields.Selection([
        ('ok', 'OK'),
        ('overrun', 'Budget Overrun')
    ], string='Budget Status', compute='_compute_budget_status', store=True)
    
    @api.depends('quantity', 'cost_sheet_line_id.quantity')
    def _compute_budget_status(self):
        for line in self:
            if line.cost_sheet_line_id and line.quantity > line.cost_sheet_line_id.quantity:
                line.budget_status = 'overrun'
            else:
                line.budget_status = 'ok'

    @api.onchange('product_id', 'project_id')
    def _onchange_product_project(self):
        if self.product_id and self.project_id:
            # Find related cost sheet line
            domain = [
                ('cost_sheet_id.project_id', '=', self.project_id.id),
                ('product_id', '=', self.product_id.id),
                ('cost_sheet_id.state', '=', 'in_progress')
            ]
            cost_sheet_line = self.env['project.cost.sheet.line'].search(domain, limit=1)
            if cost_sheet_line:
                self.cost_sheet_line_id = cost_sheet_line.id
                # Set description from product name if empty
                if not self.name:
                    self.name = self.product_id.name
            else:
                # Notify user that no matching cost sheet line was found
                return {
                    'warning': {
                        'title': _('No Cost Sheet Line Found'),
                        'message': _('No matching cost sheet line found for this product and project. Please create one first.')
                    }
                }

    def find_cost_sheet_line(self):
        for line in self:
            domain = [
                ('cost_sheet_id.project_id', '=', line.project_id.id),
                ('product_id', '=', line.product_id.id),
                ('cost_sheet_id.state', '=', 'in_progress')
            ]
            cost_sheet_line = self.env['project.cost.sheet.line'].search(domain, limit=1)
            if cost_sheet_line:
                line.cost_sheet_line_id = cost_sheet_line.id
                # Create a detailed success message with specific cost sheet line information
                message = _(
                    "Cost sheet line linked successfully!\n"
                    "Product: %s\n"
                    "Cost Sheet: %s\n"
                    "Budget Quantity: %s %s\n"
                    "Unit Cost: %s\n"
                    "Total Budget: %s"
                ) % (
                    cost_sheet_line.product_id.name,
                    cost_sheet_line.cost_sheet_id.name,
                    cost_sheet_line.quantity,
                    cost_sheet_line.uom_id.name,
                    format(cost_sheet_line.unit_cost, '.2f'),
                    format(cost_sheet_line.budgeted_cost, '.2f')
                )
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': message,
                        'type': 'success',
                        'sticky': True,  # Make it sticky since it contains more details
                    }
                }
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': _("No matching cost sheet line found. Make sure you have a cost sheet in 'In Progress' state with this product."),
                        'type': 'warning',
                        'sticky': False,
                    }
                }


class StockRequest(models.Model):
    _name = 'stock.request'
    _description = 'Stock Request'
    _inherit = ['mail.thread']
    _order = 'date desc, id desc'
    
    name = fields.Char('Reference', required=True, copy=False, 
                       readonly=True, default=lambda self: _('New'))
    date = fields.Date('Date', default=fields.Date.context_today, required=True)
    project_id = fields.Many2one('project.project', 'Project', required=True, tracking=True)
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse',   default=lambda self: self.env['stock.warehouse'].search([], limit=1))
    location_id = fields.Many2one('stock.location', 'Location')
    expected_date = fields.Datetime('Expected Date')
    shipping_policy = fields.Selection([
        ('direct', 'Receive each product when available'),
        ('one', 'Receive all products at once')
    ], string='Shipping Policy', default='direct')
    route_id = fields.Many2one('stock.route', 'Route')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)
    line_ids = fields.One2many('stock.request.line', 'request_id', 'Items')
    budget_warning = fields.Boolean('Budget Warning', compute='_compute_budget_warning', store=True)
    message_ids = fields.One2many(
        'mail.message', 'res_id',
        domain=lambda self: [('model', '=', self._name)],
        string='Messages',
        readonly=True)
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('stock.request') or _('New')
        return super().create(vals_list)
    
    @api.depends('line_ids.budget_status')
    def _compute_budget_warning(self):
        for request in self:
            request.budget_warning = any(line.budget_status == 'overrun' for line in request.line_ids)

    
    
    def action_submit(self):
        self.write({'state': 'submitted'})
    
    def action_in_progress(self):
        self.write({'state': 'in_progress'})
    
    def action_done(self):
        self.write({'state': 'done'})
        
    def action_cancel(self):
        self.write({'state': 'cancelled'})
    
    def action_view_budget(self):
            """Open a popup showing only the relevant cost sheet lines for this request"""
            self.ensure_one()
            cost_sheet_lines = self.line_ids.mapped('cost_sheet_line_id')
            
            if not cost_sheet_lines:
                raise UserError(_("No cost sheet lines found for this request. Make sure your request items are linked to cost sheet lines."))
                
            action = {
                'name': _('Budget Lines'),
                'type': 'ir.actions.act_window',
                'res_model': 'project.cost.sheet.line',
                'view_mode': 'list,form',
                'domain': [('id', 'in', cost_sheet_lines.ids)],
                'target': 'new',  # This makes it appear as a popup
                'context': {'create': False}  # Disable create option
            }
            return action