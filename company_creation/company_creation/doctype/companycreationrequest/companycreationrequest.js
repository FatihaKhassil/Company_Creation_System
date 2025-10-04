// Copyright (c) 2025, Fatiha and contributors
// For license information, please see license.txt
frappe.ui.form.on('CompanyCreationRequest', {
  refresh(frm) {
    toggle_bail(frm);

    // Boutons (DL / RC / TP)
    if (!frm.doc.__islocal) {
      frm.add_custom_button(__('Générer DL'), () => call_pdf(frm, 'generate_dl_pdf'));
      frm.add_custom_button(__('Générer RC'), () => call_pdf(frm, 'generate_rc_pdf'));
      if (frappe.user_roles && frappe.user_roles.includes('Agent Interne')) {
        frm.add_custom_button(__('Générer TP'), () => call_pdf(frm, 'generate_tp_pdf'));
      }
    }

    // Options "raison_sociale"
    set_raison_sociale_options(frm);
  },

  // Affichage de la section Bail
  type_adresse(frm) {
    toggle_bail(frm);
  },

  // MàJ options quand un nom change
  nom_societe_1: set_raison_sociale_options,
  nom_societe_2: set_raison_sociale_options,
  nom_societe_3: set_raison_sociale_options,
});

// --- Helpers ---
function toggle_bail(frm) {
  frm.toggle_display('bail_details', frm.doc.type_adresse === 'Bail');
}

function set_raison_sociale_options(frm) {
  const opts = [frm.doc.nom_societe_1, frm.doc.nom_societe_2, frm.doc.nom_societe_3]
    .filter(Boolean)
    .join('\n');
  frm.set_df_property('raison_sociale', 'options', opts || '');
}

function call_pdf(frm, fn) {
  frappe.call({
    method: `company_creation.utils.pdf_generator.${fn}`,
    args: { docname: frm.doc.name },
    callback(r) {
      if (r.message) {
        frappe.msgprint(__('PDF généré avec succès'));
        window.open(r.message);
      } else {
        frappe.msgprint(__('Erreur lors de la génération du PDF'));
      }
    },
  });
}

