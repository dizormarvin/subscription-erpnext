# Copyright (c) 2022, ossphin and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class AreasofOperation(Document):
	def autoname(self):
		place = ', '.join(
			str(name) for name in [self.island, self.region, self.province, self.city__municipality] if name)
		customer = ''.join(word[0] for word in self.customer_name.split(' '))
		
		self.name = f"{customer} {place}"
