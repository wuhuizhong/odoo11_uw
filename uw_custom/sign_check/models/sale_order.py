# _*_ coding: utf-8 _*_
from odoo import models, api,fields
from odoo.exceptions import UserError
import datetime


class SignCheckSaleOrder(models.Model):
    _inherit = 'sale.order'

    mutex_sign = fields.Boolean(string='互斥', compute='mutex_set')
    is_sign = fields.Boolean(string='買簽口用')
    is_sign_pay = fields.Boolean(string='簽口')
    partner_sign_total = fields.Float(string='目前簽口金額')
    partner_cost_toal = fields.Float(string='簽口報價單金額')
    partner_payable_total = fields.Float(string='簽口應收金額')
    partner_less_price = fields.Float(string='剩餘簽口金額', compute='compute_sign_used')
    sign_main_id = fields.Many2one(comodel_name='sign.main')

    # @api.multi
    # @api.onchange('partner_id')
    # def onchange_partner_id(self):
    #     res = super(SignCheckSaleOrder, self).onchange_partner_id()
    #     partner = self.env['sign.main'].search([('partner_id', '=', self.partner_id.id)])
    #     if len(partner) == 1:
    #         self.partner_sign_total = partner.last_total
    #     return res

    @api.onchange('is_sign_pay', 'partner_id')
    def onchang_is_sign_pay(self):
        partner = self.env['sign.main'].search([('partner_id', '=', self.partner_id.id)])
        if len(partner) == 1 and self.is_sign_pay is True:
            self.partner_sign_total = partner.last_total
            self.partner_cost_toal = partner.order_total
            self.partner_payable_total = partner.invoice_total
            self.sign_main_id = partner.id

    @api.model
    def create(self, vals):
        res = super(SignCheckSaleOrder, self).create(vals)
        if vals['is_sign_pay'] is True and not vals['sign_main_id']:
            partner = self.env['sign.main'].search([('partner_id', '=', vals['partner_id'])])
            if len(partner) == 0:
                self.env['sign.main'].create({
                    'partner_id': vals['partner_id']
                })
        return res




    # 如果有勾簽口，就新增簽口標籤到發票建立參數。
    @api.multi
    def _prepare_invoice(self):
        res = super(SignCheckSaleOrder,self)._prepare_invoice()
        partner = self.env['sign.main'].search([('partner_id', '=', self.partner_id.id)])
        if self.is_sign_pay is True and len(partner) == 1:
            res['sign_check'] = True
            res['sign_main_id'] = partner.id
        return res


    # 互斥顯示設定
    @api.depends('is_send', 'is_send_out', 'is_sign_pay', 'is_sign')
    def mutex_set(self):
        for line in self:
            if line.is_send is True:
                line.mutex_sign = True
            elif line.is_send_out is True:
                line.mutex_sign = True
            elif line.is_sign_pay is True:
                line.mutex_sign = True
            elif line.is_sign is True:
                line.mutex_sign = True
            elif line.is_send is False:
                line.mutex_sign = False
            elif line.is_send_out is False:
                line.mutex_sign = False
            elif line.is_sign_pay is False:
                line.mutex_sign = False
            elif line.is_sign is False:
                line.mutex_sign = False


    @api.depends('order_line', 'partner_id')
    def compute_sign_used(self):
        for line in self:
            partner = self.env['sign.main'].search([('partner_id', '=', self.partner_id.id)])
            amount_untaxed = amount_tax = 0.0
            for row in line.order_line:
                amount_untaxed += row.price_subtotal
                amount_tax += row.price_tax
            amount_total = amount_untaxed+amount_tax

            if len(partner) > 0:
                line.partner_sign_total = partner.last_total
                line.partner_cost_toal = amount_total
                line.partner_less_price = partner.last_total - amount_total

class SaleOrderLineSignCheck(models.Model):
    _inherit = 'sale.order.line'

    @api.onchange('product_id')
    def filter_product(self):
        if self.order_id.is_sign or self.order_id.is_sign_pay:
            return {
                'domain': {
                    'product_id': [('is_sign_product', '=', True)],
                }}
