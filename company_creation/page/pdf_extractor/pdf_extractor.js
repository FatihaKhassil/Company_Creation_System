frappe.pages['pdf-extractor'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Extracteur PDF Universel',
        single_column: true
    });

    make_universal_extractor(page);
};

