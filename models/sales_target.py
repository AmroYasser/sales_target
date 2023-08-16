import base64
import xlrd
from odoo import fields, models, api
from odoo.exceptions import ValidationError


class CompanyTarget(models.Model):
    _name = 'company.target'
    _description = 'Company Target'

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    from_date = fields.Date("From", copy=False)
    to_date = fields.Date("To", copy=False)
    target_amount = fields.Float("Target amount", required=True)
    target_qty = fields.Integer("Target quantity", required=True)
    daily_targets = fields.Binary("Daily targets file")
    description = fields.Char()
    state = fields.Selection([('draft', 'Draft'), ('done', 'Done')], default='draft')
    pos_target_ids = fields.One2many('pos.target', 'company_target_id', string='POS', copy=True)

    @api.constrains('target_amount', 'pos_target_ids')
    def check_target_amount(self):
        for rec in self:
            if rec.state not in ['draft']:
                sum_pos_targets = sum(rec.pos_target_ids.mapped('target_amount'))
                if rec.target_amount != sum_pos_targets:
                    raise ValidationError("POS targets amount must be equal to company target amount.")

    @api.constrains('target_qty', 'pos_target_ids')
    def check_target_qty(self):
        for rec in self:
            if rec.state not in ['draft']:
                sum_pos_targets = sum(rec.pos_target_ids.mapped('target_qty'))
                if rec.target_qty != sum_pos_targets:
                    raise ValidationError("POS targets quantity must be equal to company target quantity.")

    @api.constrains('from_date', 'to_date')
    def check_dates(self):
        for rec in self:
            duplicate_dates = self.search(
                [('company_id', '=', rec.company_id.id), ('from_date', '=', rec.from_date),
                 ('to_date', '=', rec.to_date), ('id', '!=', rec.id)]
            )
            if duplicate_dates:
                raise ValidationError("There is already a target for this date.")

    @api.onchange('from_date', 'to_date')
    def check_date(self):
        for rec in self:
            if rec.from_date and rec.to_date:
                domain = [('company_id', '=', rec.company_id.id), ('from_date', '=', rec.from_date),
                          ('to_date', '=', rec.to_date)]
                if rec.id:
                    domain.append(('id', '!=', rec.id))
                duplicate_dates = self.search(domain, limit=1)
                if duplicate_dates:
                    # rec.pos_target_ids = False
                    rec.target_amount = duplicate_dates.target_amount
                    rec.pos_target_ids = duplicate_dates.pos_target_ids
                else:
                    rec.pos_target_ids = rec.target_amount = False

    def action_done(self):
        for rec in self:
            target_amount = rec.target_amount
            target_qty = rec.target_qty
            all_pos_target_amount = sum(self.pos_target_ids.mapped('target_amount'))
            all_pos_target_qty = sum(self.pos_target_ids.mapped('target_qty'))
            if target_amount != all_pos_target_amount or target_qty != all_pos_target_qty:
                raise ValidationError("POS targets must be equal to company target.")
            rec.state = 'done'

    def generate(self):
        for rec in self:
            rb = xlrd.open_workbook(file_contents=base64.decodebytes(rec.daily_targets))
            sheet = rb.sheet_by_index(0)

            date_from = xlrd.xldate.xldate_as_datetime(sheet.cell(1, 3).value, 0).date()
            date_to = xlrd.xldate.xldate_as_datetime(sheet.cell(sheet.nrows-1, 3).value, 0).date()
            rec.from_date = date_from
            rec.to_date = date_to

            total_amount = 0
            total_qty = 0
            data = []
            for row in range(1,sheet.nrows):
                total_amount += sheet.cell(row, 5).value
                total_qty += sheet.cell(row, 4).value
                data.append({"pos": sheet.cell(row, 1).value,
                             "employee": sheet.cell(row, 2).value,
                             "qty": sheet.cell(row, 4).value,
                             "amount": sheet.cell(row, 5).value})

            result = {}

            for d in data:
                pos = d["pos"]
                emp = d["employee"]
                if pos not in result:
                    result[pos] = {}
                if emp not in result[pos]:
                    result[pos][emp] = {"qty": 0, "amount": 0}
                result[pos][emp]["qty"] += d["qty"]
                result[pos][emp]["amount"] += d["amount"]

            for pos in result:
                pos_qty = sum(emp["qty"] for emp in result[pos].values())
                pos_amount = sum(emp["amount"] for emp in result[pos].values())
                result[pos]["pos_qty"] = pos_qty
                result[pos]["pos_amount"] = pos_amount


            rec.target_amount = total_amount
            rec.target_qty = total_qty


            for pos in result:
                pos_id = self.env['pos.config'].search([('name', '=', pos)])
                self.env['pos.target'].create({'pos_id': pos_id.id,
                                               'company_target_id': rec.id,
                                               'target_amount': result[pos]["pos_amount"],
                                               'target_qty': result[pos]["pos_qty"]})

                for emp in result[pos]:
                    if emp not in ['pos_qty', 'pos_amount']:
                        employee_id = self.env['hr.employee'].search([('name', '=', emp)])
                        pos_target_id = self.env['pos.target'].search([('pos_id', '=', pos_id.id),
                                                                       ('company_target_id', '=', rec.id)], limit=1)
                        self.env['employee.target'].create({'employee_id': employee_id.id,
                                                            'pos_target_id': pos_target_id.id,
                                                            'target_amount': result[pos][emp]['amount'],
                                                            'target_qty': result[pos][emp]['qty']})


class PosTarget(models.Model):
    _name = 'pos.target'
    _description = "POS Target"

    pos_id = fields.Many2one('pos.config', string='POS', required=True)
    target_amount = fields.Float("Target amount")
    target_qty = fields.Integer("Target quantity", required=True)
    company_target_id = fields.Many2one('company.target', readonly=True, ondelete="cascade")
    employee_target_ids = fields.One2many('employee.target', 'pos_target_id', string='Employees', copy=True)

    @api.constrains('target_amount', 'employee_target_ids')
    def check_target_amount(self):
        for rec in self:
            if rec.company_target_id.state not in ['draft']:
                sum_employee_targets = sum(rec.employee_target_ids.mapped('target_amount'))
                if rec.target_amount != sum_employee_targets:
                    raise ValidationError("Employees targets must be equal to POS target amount.")

    @api.constrains('target_qty', 'employee_target_ids')
    def check_target_qty(self):
        for rec in self:
            if rec.company_target_id.state not in ['draft']:
                sum_employee_targets = sum(rec.employee_target_ids.mapped('target_qty'))
                if rec.target_qty != sum_employee_targets:
                    raise ValidationError("Employees targets quantity must be equal to POS target quantity.")

    @api.constrains('pos_id', 'company_target_id')
    def check_pos(self):
        for rec in self:
            duplicate_pos = self.env['pos.target'].search(
                [('pos_id', '=', rec.pos_id.id),
                 ('company_target_id', '=', rec.company_target_id.id), ('id', '!=', rec.id)]
            )
            if duplicate_pos:
                raise ValidationError(
                    "POS {name} already exists".format(name=rec.pos_id.name)
                )


class EmployeeTarget(models.Model):
    _name = 'employee.target'
    _description = 'Employee Target'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    target_amount = fields.Float('Target amount')
    target_qty = fields.Integer("Target quantity", required=True)
    pos_target_id = fields.Many2one('pos.target', readonly=True, ondelete="cascade")

    @api.constrains('employee_id', 'pos_target_id')
    def check_employee(self):
        for rec in self:
            duplicate_employee = self.env['employee.target'].search(
                [('employee_id', '=', rec.employee_id.id),
                 ('pos_target_id.company_target_id', '=', rec.pos_target_id.company_target_id.id), ('id', '!=', rec.id)]
            )
            if duplicate_employee:
                raise ValidationError(
                    "Employee {name} is already assigned to a target".format(name=rec.employee_id.name)
                )
