# Copyright 2018 - Today Sylvain LE GAL (https://twitter.com/legalsylvain)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class PosOrder(models.Model):
    _inherit = "pos.order"

    has_picking_delayed = fields.Boolean(
        default=False,
        help="This checkbox is checked if the generation of"
        " the picking has been delayed. The picking will be created by cron.",
    )

    # Overload Section
    @api.model
    def create_from_ui(self, orders, draft=False):
        PosSession = self.env["pos.session"]
        for order_data in orders:
            session_id = order_data.get("data").get("pos_session_id")
            session = PosSession.browse(session_id)
            order_data["data"]["has_picking_delayed"] = (
                session.config_id.picking_creation_delayed
                and not session.update_stock_at_closing
            )
        return super(PosOrder, self.with_context(create_from_ui=True)).create_from_ui(
            orders, draft=draft
        )

    @api.model
    def _delayed_picking_job_kwargs(self):
        return {}

    def _create_order_picking(self):
        if self.env.context.get("create_from_ui", False):
            orders = self.filtered(lambda x: not x.has_picking_delayed)
            delayed_orders = self.filtered(lambda x: x.has_picking_delayed)
            if delayed_orders:
                kw = self._delayed_picking_job_kwargs()
                delayed_orders.with_delay(**kw)._create_delayed_picking()
        else:
            orders = self

        if not orders:
            return

        super(PosOrder, orders)._create_order_picking()
        orders.write({"has_picking_delayed": False})

    @api.model
    def _order_fields(self, ui_order):
        res = super(PosOrder, self)._order_fields(ui_order)
        res["has_picking_delayed"] = ui_order["has_picking_delayed"]
        return res

    # Custom Section
    def _create_delayed_picking(self):
        # make the function idempotent
        orders = self.filtered(lambda x: x.has_picking_delayed)
        super(PosOrder, orders)._create_order_picking()
        orders.write({"has_picking_delayed": False})
