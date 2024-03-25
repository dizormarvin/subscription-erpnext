// Copyright (c) 2022, ossphin and contributors
// For license information, please see license.txt


frappe.ui.form.on('Program Activation Request', {
    //custom material request
    	refresh: function(frm) {
			console.clear()
			show_dialog_box(frm)
	},

    onload: (frm) => {
        if (!frm.doc.docstatus){
			frm.set_value("user", frappe.session.user)
		}
    },

    customer: (frm) => {
        frm.set_query ("psof", () => {
            return {
                query: "subscription.subscription.doctype.psof.psof.get_programs",
                filters: {
                    customer: frm.doc.customer,
                    from_request: 1
                }
            }
        });
    },

    psof: (frm) => {
		frm.clear_table("programs")
		frm.call("load_psof_programs")
		frm.refresh_field('programs')
	},
});



frappe.ui.form.on('Program Activation Request Item', {
    before_programs_remove: (frm, cdt, cdn) => {
        const row = locals[cdt][cdn]

		// ORIGINAL
        // if (row.from_package) {
        //     frappe.throw(`Cannot remove ${row.program} because it belongs to package ${row.package_name}`)
        // }

    },

    action: (frm, cdt, cdn) => {
        const row = locals[cdt][cdn]
        row.request_date = row.request_date ? row.request_date:frappe.datetime.get_today();
        row.remarks = `${row.program} from PSOF: ${row.psof} request to ${row.action} on ${row.request_date}`
        frm.refresh_field('programs')
    }


})

//CUSTOM MATERIAL REQUEST
function make_material_request(selectedPrograms){
	frappe.call({
		method: 'subscription.subscription.doctype.program_activation_request.program_activation_request.make_material_request',
		args: {
			selectedPrograms: selectedPrograms
		},
		callback: function (mr) {
			let a = frappe.model.sync(mr.message)
			frappe.set_route('Form', mr.message.doctype, mr.message.name);
		}

	});
}


function show_dialog_box(frm) {
	var materialRequests;
	frappe.db.get_list('Material Request', {
		fields: ['parent_program_activation'],
		filters: {
			parent_program_activation: frm.doc.name
		}
	}).then(function(result) {
		// Assigning the result to the variable declared outside
		if(result[0]){
			materialRequests = result[0].parent_program_activation;
		}
		var checkMR

		if(materialRequests){
			checkMR = 1
		}
		else {
			checkMR = 0
		}

		// show button
		if (frm.doc.workflow_state == 'For Acct Manager Approval') {
			frm.add_custom_button('Create Material Request', () => {
				if(frm.doc.__unsaved == 1) {
					frappe.throw('Please save the document first')
				}

			// Creating dialog
			var dialog = new frappe.ui.Dialog({
				title: 'Create Material Request',
				fields: [
					{
						fieldname: 'program_for_material_request', fieldtype: 'Table', label: 'Select Programs',
						fields: [
							{
								fieldtype:'Link',
								fieldname:'program_name',
								label: __('Programs'),
								options: 'Subscription Program',
								read_only: 1,
								in_list_view:1
							},
							{
								fieldtype:'Int',
								fieldname:'no_of_months',
								label: __('No of Months (Recovery)'),
								hidden: 1,
								in_list_view:1
							},
						]
					}
				],
				// When submit clicked
				primary_action: function() {
					var program_items = [];
					var program_items_no_componets = []
					var selected_programs = dialog.fields_dict.program_for_material_request.grid.get_selected_children();
					var with_components = []
					var promises = [];

					// Fetch componets for selected programs only
					selected_programs.forEach((program) => {
						var promise = new Promise((resolve, reject) => {
							frappe.call({
								method: 'frappe.client.get',
								args: {
									doctype: 'Subscription Program',
									name: program.program_name
								},
								callback: function(response) {
									var subscriptionProgram = response.message.components;
									if(subscriptionProgram.length >0){
										with_components.push(response.message.program_name)
									}
									if (subscriptionProgram && subscriptionProgram.length > 0) {
										subscriptionProgram.forEach((i) => {
											program_items.push(i.item);
										});
									}
									else {
										program_items_no_componets.push(response.message.name)
									}
									resolve(); // Resolve the promise when done
								}
							});
						});
						promises.push(promise);
					});

					Promise.all(promises).then(() => {
						var programs = program_items;
						var programs_no_componets = program_items_no_componets;
						console.log(selected_programs)
						console.log(programs_no_componets.length)
						if(programs_no_componets.length > 0 && programs.length > 0){
							var msg3 = "Following Program Dont Have Components in <b>Subscription Program:</b> <ul>"
							programs_no_componets.forEach((p)=>{
								msg3 += "<li>" + p + "</li>"
							})
							msg3 += "</ul> <br> Do you want to proceed for program: <br> <ul>"
							with_components.forEach((p)=>{
								msg3 += "<li>" + p + "</li>"
							})
							msg3 += "</ul>"
							frappe.confirm(msg3,
									() => {
										// action to perform if Yes is selected
										  frm.call("make_material_request", selected_programs).then(mr => {
											let a = frappe.model.sync(mr.message);
											frappe.set_route('Form', mr.message.doctype, mr.message.name);
											console.log(mr.message);
										  });
										dialog.hide();
									}, () => {
										// action to perform if No is selected
										dialog.hide();
								})
						}
						else if(programs.length > 0){
							  frm.call("make_material_request", selected_programs).then(mr => {
								let a = frappe.model.sync(mr.message);
								//mr.message.toggle_display(['set_from_warehouse'], false);
								frappe.set_route('Form', mr.message.doctype, mr.message.name);

								console.log(mr.message.name);
							  });
							dialog.hide();
						}
						else {
							if(programs_no_componets.length > 0){
								console.log(programs_no_componets)
								var msg1 = "Following Program Dont Have Components in <b>Subscription Program:</b> <ul>"
								programs_no_componets.forEach((p)=>{
									msg1 += "<li>" + p + "</li>"
									}
								)

								msg1 += "</ul>"
								frappe.msgprint(msg1)
							}
							else {
								frappe.msgprint('Please select atleast one program in the list')
							}

						}

					}).catch((error) => {
						console.error(error);
					});
				}
			});
			// Populate Programs to Dialog table
			function set_program_for_material_request (dialog) {
				var program_for_material_request = dialog.get_value("program_for_material_request");
				let program_items = [];
				frm.doc.programs.forEach((row) => {
					//Push all items dont have material request yet
					if(!row.material_request){
						program_items.push({
							"program_name": row.program,
							"no_of_months": row.no_of_months
						});
					}
				});
				const hasZero = program_items.some(program => program.no_of_months === 0);
				if(hasZero){
					let allZero = program_items.map(obj => {return obj.program_name});
					var msg = "<b>No of Months (Recovery)</b>" + " is required for program below: " + "<br>" + "<ul>"
					allZero.forEach((program) => {
						msg += "<li>" + program + "</li>"
					})
					msg += "</ul>"
					frappe.throw(msg)
				}
				dialog.fields_dict["program_for_material_request"].df.data = program_items;
				dialog.get_field("program_for_material_request").refresh();

			}
			set_program_for_material_request(dialog);
			dialog.get_field("program_for_material_request").refresh();
			if(dialog.get_field("program_for_material_request").df.data.length > 0) {
				dialog.show();
			}
			else {
				frappe.msgprint("All Programs has already Material Request")
			}

		});
	}

	}).catch(function(err) {
		console.error(err);
	});
}



// DELVIN 01-31-24
frappe.ui.form.on('Program Activation Request Item', {
    before_programs_remove: (frm, cdt, cdn) => {
        const row = locals[cdt][cdn];
		let from_package_list = [];
		let from_selected_package_list = []

		frm.doc.programs.forEach(e => {
			if(e.from_package){
				from_package_list.push(row.package_name);
			}
		});

		if(row.from_package){
			frm.doc.programs.forEach(e => {
				if(e.from_package && e.__checked){
					from_selected_package_list.push(row.package_name);
				}

			})
			if(from_package_list.length != from_selected_package_list.length){
				// frappe.throw(`Cannot remove ${row.program} because it belongs to package ${row.package_name}`)
			}
		}
    },
});

