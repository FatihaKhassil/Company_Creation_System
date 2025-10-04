frappe.web_form.on('forme_juridique', (field, value) => {
    // Masquer tous les champs dépendants au départ
    frappe.web_form.set_df_property('associes', 'hidden', 1);
    frappe.web_form.set_df_property('capital_social', 'hidden', 1);

    if (['SARL', 'SAS', 'SNC', 'SCS'].includes(value)) {
        frappe.web_form.set_df_property('associes', 'hidden', 0);
        frappe.web_form.set_df_property('capital_social', 'hidden', 0);
    }

    if (value === 'SARL AU') {
        frappe.web_form.set_df_property('associes', 'hidden', 0); // 1 associé
        frappe.web_form.set_df_property('capital_social', 'hidden', 0);
    }

    if (value === 'SA') {
        frappe.web_form.set_df_property('associes', 'hidden', 0);
        frappe.web_form.set_df_property('capital_social', 'hidden', 0);
    }

    if (value === 'EI') {
        frappe.web_form.set_df_property('associes', 'hidden', 1);
        frappe.web_form.set_df_property('capital_social', 'hidden', 1);
    }
});
frappe.web_form.validate = () => {
    const forme = frappe.web_form.get_value('forme_juridique');
    const associes = frappe.web_form.get_value('associes') || [];
    const capital = frappe.web_form.get_value('capital_social') || 0;

    // Vérification du nombre d'associés
    if (['SARL', 'SAS', 'SNC', 'SCS'].includes(forme)) {
        if (associes.length < 2) {
            frappe.throw("Il faut au moins 2 associés pour la forme juridique sélectionnée.");
        }
    }

    if (['SARL AU', 'EI'].includes(forme)) {
        if (associes.length !== 1) {
            frappe.throw("Cette forme juridique n'autorise qu’un seul associé.");
        }
    }

    // Vérification du capital pour SA
    if (forme === 'SA' && capital < 300000) {
        frappe.throw("Le capital minimum pour une SA est de 300 000 MAD.");
    }
};


frappe.web_form.on('type_adresse', (field, value) => {
    const bailFields = ['nom_proprietaire', 'cin_proprietaire', 'loyer', 'duree_bail', 'bail_pdf'];
    if (value === 'Bail') {
        bailFields.forEach(fieldname => {
            frappe.web_form.set_df_property(fieldname, 'hidden', 0);
        });
    } else {
        bailFields.forEach(fieldname => {
            frappe.web_form.set_df_property(fieldname, 'hidden', 1);
        });
    }
});
