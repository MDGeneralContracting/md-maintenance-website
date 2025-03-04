$(document).ready(function() {
    const tableOptions = {
        "paging": true,
        "searching": true,
        "ordering": true,
        "info": true,
        "scrollX": true,
        "responsive": true,
        "pageLength": 10,
        "lengthMenu": [5, 10, 25, 50],
        "autoWidth": false,
        "fixedHeader": true
    };

    const boomTable = $('#latest-boom-table').DataTable(tableOptions);
    $('#full-data-table').DataTable(tableOptions);
    $('#user-summary-table').DataTable(tableOptions);
    $('#builder-summary-table').DataTable(tableOptions);

    // Add warnings for Hours Since Oil Change > 250
    boomTable.rows().every(function() {
        const data = this.data();
        const hoursSinceOilChangeIdx = boom_columns.indexOf('Hours Since Oil Change'); // Match with Python boom_columns
        const hoursSinceOilChange = data[hoursSinceOilChangeIdx];
        if (hoursSinceOilChange !== 'No Data' && parseInt(hoursSinceOilChange) > 250) {
            $(this.node()).addClass('oil-change-warning');
        }

        // Add warnings for Annual Inspection > 10 months
        const annualInspectionIdx = boom_columns.indexOf('Annual Inspection');
        const annualInspectionDate = data[annualInspectionIdx];
        if (annualInspectionDate !== 'No Data Available') {
            const inspectionDate = new Date(annualInspectionDate);
            const today = new Date();
            const monthsDiff = (today.getFullYear() - inspectionDate.getFullYear()) * 12 +
                              (today.getMonth() - inspectionDate.getMonth());
            if (monthsDiff > 10) {
                const cell = $(this.node()).find(`td:eq(${annualInspectionIdx})`);
                cell.addClass('inspection-warning');
                const expiryDate = new Date(inspectionDate);
                expiryDate.setFullYear(expiryDate.getFullYear() + 1);
                const daysUntilExpiry = Math.ceil((expiryDate - today) / (1000 * 60 * 60 * 24));
                cell.attr('data-tooltip', `Expires in ${daysUntilExpiry} days (${expiryDate.toISOString().split('T')[0]})`);
            }
        }
    });

    // Navigation active link
    const currentPath = window.location.pathname.split('/').pop() || 'index.html';
    $('nav a').each(function() {
        const href = $(this).attr('href');
        if (href === currentPath) {
            $(this).addClass('active');
        }
    });

    console.log("M&D General Contracting tables initialized with DataTables.");
});

// Define boom_columns to match Python (for column indexing)
const boom_columns = [
    'Boom Lift ID', 'Completion time', 'Name', 'Hours', 'Oil Level', 'Gas Level',
    'General Issues', 'Last Maintenance', 'Hours Since Oil Change', 'Annual Inspection'
];
