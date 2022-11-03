# Copyright (c) 2022, ossphin and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ProgramRequestSignatures(Document):
	def after_insert(self):
		if self.doc_type == "Program Request Signatures":
			sig_remarks = frappe.db.get_list("Program Request Signatures", filters={"doc_name": self.doc_name},
											fields=["full_name", "remarks", "creation"])

			req = frappe.get_doc("Program Activation Request", self.doc_name)
			req.db_set("rem_summary", "<ol>" + ''.join([f"<li>[{sig.get('creation')}] ({sig.get('full_name')}): {sig.get('remarks')}</li>" for sig in sig_remarks]) + "</ol>")
			frappe.db.commit()
