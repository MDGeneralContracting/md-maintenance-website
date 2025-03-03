$(document).ready(function() {
    // Initialize DataTables for each table with unique ID
    const tableOptions = {
        "paging": true,
        "searching": true,
        "ordering": true,
        "info": true,
        "scrollX": true,
        "responsive": true,
        "pageLength": 10,
        "lengthMenu": [5, 10, 25, 50],
        "autoWidth": false, // Prevent layout shifts
        "fixedHeader": true // Sticky headers
    };

    $('#latest-boom-table').DataTable(tableOptions);
    $('#full-data-table').DataTable(tableOptions);
    $('#user-summary-table').DataTable(tableOptions);
    $('#builder-summary-table').DataTable(tableOptions);

    // Highlight rows with issues (based on "General Issues" column)
    $('.data-table').each(function() {
        const table = $(this).DataTable();
        table.rows().every(function() {
            const data = this.data();
            const generalIssues = data[data.length - 2]; // "General Issues" is second-to-last in most tables
            if (generalIssues && generalIssues.trim() !== '') {
                $(this.node()).addClass('has-issues');
            }
        });
    });

    // Highlight active nav item
    const currentPath = window.location.pathname.split('/').pop() || 'index.html';
    $('nav a').each(function() {
        const href = $(this).attr('href');
        if (href === currentPath) {
            $(this).addClass('active');
        }
    });

    console.log("M&D General Contracting tables initialized with DataTables.");
});
