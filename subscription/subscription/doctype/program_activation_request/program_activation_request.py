# Copyright (c) 2022, ossphin and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class ProgramActivationRequest(Document):

	def on_submit(self):
		self.clear_signature_rem()

	def clear_signature_rem(self):
		self.db_set("signature", None)
		self.db_set("remarks", None)
		frappe.db.commit()

	@frappe.whitelist()
	def load_psof_programs(self):
		psof_program = frappe.db.get_list("PSOF Program", {"parent": self.psof},
										  ["subscription_program", "active", "psof", "name", "customer_name",
										   "is_package"])

		for program in psof_program:
			if program.get("is_package"):
				parent_pack = frappe.get_doc("Subscription Program", program.get("subscription_program"))
				for child in parent_pack.get("packaged_programs"):
					self.add_incl_program(program, child, 1)
			else:
				self.add_incl_program(program)

	def add_incl_program(self, psof_program, doc=None, packaged=0):
		self.append("programs", {
			"package_name": psof_program.get("subscription_program") if packaged else None,
			"current_status": psof_program.get("active"),
			"psof": self.psof,
			"psof_program": psof_program.get("name"),
			"customer_name": psof_program.get("customer_name"),
			"from_package": packaged,
			"program": doc.get("program") if packaged else psof_program.get("subscription_program")
		})


@frappe.whitelist()
def test_api(doc, event):
	if (doc.signature or doc.get("user_signature")) and not doc.get("__unsaved"):
		old_doc = doc.get_doc_before_save()
		if not old_doc or (doc.workflow_state in (
				"Draft Request",
				"For Acct Manager Approval",
				"For Billing & Collection Approval",
				"For Sales Coordinator Approval",
				"For AVP Network Approval") and old_doc.workflow_state != doc.workflow_state):
			create_req_signature(doc, "Program Activation Request")
			doc.clear_signature_rem()
			doc.reload()
	elif not (doc.signature or doc.get("user_signature")) and not doc.get("__unsaved"):
		frappe.throw("Please sign first")
	else:
		return


def create_req_signature(doc, dt):
	frappe.get_doc({
		"doctype": "Program Request Signatures",
		"doc_type": dt,
		"user": doc.get("user") or frappe.get_user().name,
		"doc_name": doc.name,
		"work_state": doc.get("workflow_state") or "Submitted",
		"signature": doc.signature,
		"remarks": doc.get("remarks"),
		"sign_type":  "E-Signature" if dt == "Program Activation" else doc.e_signature
	}).save()
