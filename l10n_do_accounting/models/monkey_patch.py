from odoo import models, api


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.depends(
        "posted_before",
        "state",
        "journal_id",
        "date",
        "move_type",
    )
    def _compute_name(self):
        """
        Override to handle Dominican fiscal number generation.
        In v18, this method needs to be adapted to the new sequencing logic.
        """
        # Separate Dominican fiscal invoices from regular moves
        l10n_do_moves = self.filtered(
            lambda m: m.country_code == "DO"
            and m.l10n_latam_document_type_id
            and not m.l10n_latam_manual_document_number
            and not m.l10n_do_enable_first_sequence
        )
        
        # Process regular moves first with standard logic
        regular_moves = self - l10n_do_moves
        if regular_moves:
            super(AccountMove, regular_moves)._compute_name()
        
        # Process Dominican fiscal moves
        for move in l10n_do_moves:
            if move.state == "cancel":
                continue
                
            # If already posted and has fiscal number, skip
            if move.state == "posted" and move.l10n_do_fiscal_number:
                # Ensure name is set
                if not move.name or move.name == "/":
                    super(AccountMove, move)._compute_name()
                continue
            
            # For draft moves, compute regular name first
            if move.state == "draft":
                super(AccountMove, move)._compute_name()
                continue
            
            # For posted moves without fiscal number, generate it
            if move.state == "posted" and not move.l10n_do_fiscal_number:
                # First ensure regular name is set
                if not move.name or move.name == "/":
                    super(AccountMove, move)._compute_name()
                
                # Then generate fiscal sequence
                move.with_context(is_l10n_do_seq=True)._set_next_sequence()

    def _set_next_sequence(self):
        """
        Override to handle both regular and fiscal sequences.
        """
        if self._context.get("is_l10n_do_seq", False):
            # Handle fiscal sequence generation
            for move in self:
                if not move.l10n_latam_document_type_id:
                    continue
                    
                last_sequence = move._get_last_sequence()
                new = not last_sequence
                
                if new:
                    last_sequence = (
                        move._get_last_sequence(relaxed=True) 
                        or move._l10n_do_get_formatted_sequence()
                    )
                
                format_str, format_values = move._get_sequence_format_param(last_sequence)
                
                if new:
                    format_values["seq"] = 0
                    
                format_values["seq"] = format_values["seq"] + 1
                
                # Generate and set fiscal number
                fiscal_number = format_str.format(**format_values)
                move.l10n_do_fiscal_number = (
                    move.l10n_latam_document_type_id._format_document_number(fiscal_number)
                )
                move._compute_split_sequence()
        else:
            # Regular sequence generation
            return super()._set_next_sequence()