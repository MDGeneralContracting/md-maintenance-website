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

    // Add warnings and tooltips for Boom Lift Summary
    boomTable.rows().every(function() {
        const data = this.data();

        // Hours Since Oil Change > 250 warning
        const hoursSinceOilChangeIdx = boom_columns.indexOf('Hours Since Oil Change'); // 10th column (index 9)
        const hoursSinceOilChange = data[hoursSinceOilChangeIdx];
        if (hoursSinceOilChange !== 'No Data' && parseInt(hoursSinceOilChange) > 250) {
            const cell = $(this.node()).find(`td:eq(${hoursSinceOilChangeIdx})`);
            cell.addClass('oil-change-warning');
        }

        // Annual Inspection warning and tooltip
        const annualInspectionIdx = boom_columns.indexOf('Annual Inspection'); // 11th column (index 10)
        const annualInspectionDate = data[annualInspectionIdx];
        if (annualInspectionDate !== 'No Data Available') {
            const inspectionDate = new Date(annualInspectionDate);
            const today = new Date();
            const monthsDiff = (today.getFullYear() - inspectionDate.getFullYear()) * 12 +
                              (today.getMonth() - inspectionDate.getMonth());
            const expiryDate = new Date(inspectionDate);
            expiryDate.setFullYear(expiryDate.getFullYear() + 1);
            const daysUntilExpiry = Math.ceil((expiryDate - today) / (1000 * 60 * 60 * 24));
            
            const cell = $(this.node()).find(`td:eq(${annualInspectionIdx})`);
            // Add tooltip for all valid dates
            cell.attr('data-tooltip', `Days until next annual inspection: ${daysUntilExpiry > 0 ? daysUntilExpiry : 'Expired'}`);
            
            // Add warning if > 10 months
            if (monthsDiff > 10) {
                cell.addClass('inspection-warning');
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
    'General Issues', 'Last Maintenance', 'Oil Change', 'Hours Since Oil Change', 'Annual Inspection'
];
