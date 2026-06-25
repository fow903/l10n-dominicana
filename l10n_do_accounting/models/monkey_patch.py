from odoo import models, api


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.depends(
        "posted_before",
        "state",
        "journal_id",
        "date",
        "move_type",
        "origin_payment_id",
    )
    def _compute_name(self):
        # Let the standard sequence assignment run first, then assign the
        # Dominican fiscal number (l10n_do_fiscal_number) on internally
        # generated fiscal documents once the move is posted.
        super()._compute_name()

        for move in self.filtered(
            lambda x: x.country_code == "DO"
            and x.l10n_latam_document_type_id
            and not x.l10n_latam_manual_document_number
            and not x.l10n_do_enable_first_sequence
            and x.state == "posted"
            and not x.l10n_do_fiscal_number
        ):
            move.with_context(is_l10n_do_seq=True)._set_next_sequence()
