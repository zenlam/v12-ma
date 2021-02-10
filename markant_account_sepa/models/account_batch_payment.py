import random
import time
from lxml import etree

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class AccountBatchPayment(models.Model):
    _inherit = 'account.batch.payment'

    sepa_batch_booking_tag = fields.Selection([('true', 'True'),
                                               ('false', 'False')],
                                              'SEPA Booking Tag',
                                              default='true')

    def _create_iso20022_credit_transfer(self, Document, doc_payments):
        CstmrCdtTrfInitn = etree.SubElement(Document, "CstmrCdtTrfInitn")

        # Create the GrpHdr XML block
        GrpHdr = etree.SubElement(CstmrCdtTrfInitn, "GrpHdr")
        MsgId = etree.SubElement(GrpHdr, "MsgId")
        val_MsgId = str(int(time.time() * 100))[-10:]
        val_MsgId = self._sanitize_communication(self.journal_id.company_id.name[-15:]) + val_MsgId
        val_MsgId = str(random.random()) + val_MsgId
        val_MsgId = val_MsgId[-30:]
        MsgId.text = val_MsgId
        CreDtTm = etree.SubElement(GrpHdr, "CreDtTm")
        CreDtTm.text = time.strftime("%Y-%m-%dT%H:%M:%S")
        NbOfTxs = etree.SubElement(GrpHdr, "NbOfTxs")
        val_NbOfTxs = str(len(doc_payments))
        if len(val_NbOfTxs) > 15:
            raise ValidationError(_("Too many transactions for a single file."))
        if not self.journal_id.bank_account_id.bank_bic:
            raise UserError(_("There is no Bank Identifier Code recorded for bank account '%s' of journal '%s'") % (self.journal_id.bank_account_id.acc_number, self.journal_id.name))
        NbOfTxs.text = val_NbOfTxs
        CtrlSum = etree.SubElement(GrpHdr, "CtrlSum")
        CtrlSum.text = self._get_CtrlSum(doc_payments)
        GrpHdr.append(self._get_InitgPty())

        # Create one PmtInf XML block per execution date
        payments_date_wise = {}
        for payment in doc_payments:
            if payment.payment_date not in payments_date_wise:
                payments_date_wise[payment.payment_date] = []
            payments_date_wise[payment.payment_date].append(payment)
        count = 0
        for payment_date, payments_list in payments_date_wise.items():
            count += 1
            PmtInf = etree.SubElement(CstmrCdtTrfInitn, "PmtInf")
            PmtInfId = etree.SubElement(PmtInf, "PmtInfId")
            PmtInfId.text = (val_MsgId + str(self.journal_id.id) + str(count))[-30:]
            PmtMtd = etree.SubElement(PmtInf, "PmtMtd")
            PmtMtd.text = 'TRF'
            BtchBookg = etree.SubElement(PmtInf, "BtchBookg")
            BtchBookg.text = self.sepa_batch_booking_tag
            NbOfTxs = etree.SubElement(PmtInf, "NbOfTxs")
            NbOfTxs.text = str(len(payments_list))
            CtrlSum = etree.SubElement(PmtInf, "CtrlSum")
            CtrlSum.text = self._get_CtrlSum(payments_list)
            PmtInf.append(self._get_PmtTpInf())
            ReqdExctnDt = etree.SubElement(PmtInf, "ReqdExctnDt")
            ReqdExctnDt.text = fields.Date.to_string(payment_date)
            PmtInf.append(self._get_Dbtr())
            PmtInf.append(self._get_DbtrAcct())
            DbtrAgt = etree.SubElement(PmtInf, "DbtrAgt")
            FinInstnId = etree.SubElement(DbtrAgt, "FinInstnId")
            BIC = etree.SubElement(FinInstnId, "BIC")
            BIC.text = self.journal_id.bank_account_id.bank_bic.replace(' ', '')

            # One CdtTrfTxInf per transaction
            for payment in payments_list:
                PmtInf.append(self._get_CdtTrfTxInf(PmtInfId, payment))

        return etree.tostring(Document, pretty_print=True, xml_declaration=True, encoding='utf-8')
