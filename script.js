$(document).ready(function() {
    $('.data-table').DataTable({
        "paging": true,
        "searching": true,
        "ordering": true,
        "info": true,
        "scrollX": true,
        "responsive": true,
        "pageLength": 10,
        "lengthMenu": [5, 10, 25, 50]
    });
    console.log("M&D General Contracting tables initialized with DataTables.");
});
