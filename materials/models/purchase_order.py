from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    project_id = fields.Many2one('project.project', string='Project', tracking=True)
    budget_warning = fields.Boolean('Budget Warning', compute='_compute_budget_warning', store=True)
    
    @api.depends('order_line.budget_status')
    def _compute_budget_warning(self):
        for order in self:
            order.budget_warning = any(line.budget_status == 'overrun' for line in order.order_line)
    
    def action_view_budget(self):
        """Open a popup showing only the relevant cost sheet lines for this order"""
        self.ensure_one()
        cost_sheet_lines = self.order_line.mapped('cost_sheet_line_id')

        if not cost_sheet_lines:
            raise UserError(_("No cost sheet lines found for this order. Make sure your order items are linked to cost sheet lines."))

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
    
    @api.onchange('project_id')
    def _onchange_project_id(self):
        """When project changes, reset cost sheet lines on order lines"""
        for line in self.order_line:
            if self.project_id:
                line._onchange_product_project()
            else:
                line.cost_sheet_line_id = False


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    cost_sheet_line_id = fields.Many2one('project.cost.sheet.line', string='Cost Sheet Line')
    project_id = fields.Many2one('project.project', related='order_id.project_id', store=True)
    budget_status = fields.Selection([
        ('ok', 'OK'),
        ('warning', 'Warning'),
        ('overrun', 'Budget Overrun')
    ], string='Budget Status', compute='_compute_budget_status', store=True)

    @api.depends('product_id', 'product_qty', 'price_unit', 'price_subtotal', 'cost_sheet_line_id')
    def _compute_budget_status(self):
        for line in self:
            if not line.cost_sheet_line_id:
                line.budget_status = 'ok'
                continue
                
            cost_line = line.cost_sheet_line_id
            status = 'ok'
            
            # Check if quantities exceed the budgeted quantity
            if line.product_qty > cost_line.quantity:
                status = 'overrun'
            # Check if unit price exceeds the budgeted unit cost
            elif line.price_unit > cost_line.unit_cost:
                status = 'overrun'
            # Check if line untaxed subtotal exceeds the budgeted amount
            elif line.price_subtotal > cost_line.budgeted_cost:
                status = 'overrun'
            # Warning at 80% utilization of budget
            elif line.price_subtotal >= (cost_line.budgeted_cost * 0.8):
                status = 'warning'
                
            line.budget_status = status

    @api.onchange('product_id', 'project_id')
    def _onchange_product_project(self):
        if not self.product_id or not self.project_id:
            return
            
        # Find related cost sheet line
        domain = [
            ('cost_sheet_id.project_id', '=', self.project_id.id),
            ('product_id', '=', self.product_id.id),
            ('cost_sheet_id.state', '=', 'in_progress')
        ]
        cost_sheet_line = self.env['project.cost.sheet.line'].search(domain, limit=1)
        if cost_sheet_line:
            self.cost_sheet_line_id = cost_sheet_line.id
        else:
            self.cost_sheet_line_id = False

    def find_cost_sheet_line(self):
        """Button action to find matching cost sheet line"""
        for line in self:
            domain = [
                ('cost_sheet_id.project_id', '=', line.project_id.id),
                ('product_id', '=', line.product_id.id),
                ('cost_sheet_id.state', '=', 'in_progress')
            ]
            cost_sheet_line = self.env['project.cost.sheet.line'].search(domain, limit=1)
            if cost_sheet_line:
                line.cost_sheet_line_id = cost_sheet_line.id
                # Create a detailed success message
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
                        'sticky': True,
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
