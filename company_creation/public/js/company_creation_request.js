frappe.ui.form.on('CompanyCreationRequest', {
    refresh(frm) {
        if (!frm.doc.__islocal && frappe.user_roles.includes("Agent Interne")) {

            // 📄 Bouton pour générer le TP
            frm.add_custom_button(' Générer TP', () => {
                frappe.call({
                    method: 'company_creation.utils.pdf_generator.generate_tp_pdf',
                    args: { docname: frm.docname },
                    callback(r) {
                        if (r.message) {
                            frappe.msgprint('Document TP généré !');
                            window.open(r.message); // ouvre le PDF généré
                        }
                    }
                });
            });

            // 📄 Bouton pour générer le RC
            frm.add_custom_button('📄 Générer RC', () => {
                frappe.call({
                    method: 'company_creation.utils.pdf_generator.generate_rc_pdf',
                    args: { docname: frm.docname },
                    callback(r) {
                        if (r.message) {
                            frappe.msgprint('Document RC généré !');
                            window.open(r.message); // ouvre le PDF généré
                        }
                    }
                });
            });
            frm.add_custom_button('📄 Générer DL', () => {
                frappe.call({
                    method: 'company_creation.utils.pdf_generator.generate_dl_pdf',
                    args: { docname: frm.doc.name },
                    callback(r) {
                        if (r.message) {
                            frappe.msgprint(__('PDF Dépôt Légal généré avec succès'));
                            window.open(r.message);
                        } else {
                            frappe.msgprint(__('Erreur lors de la génération du PDF'));
                        }
                    }
                });
            });
        }
    }
});


