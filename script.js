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

    // Existing Boom Lift Summary logic...

    // Fetch latest hours for validation
    let latestHours = {};
    boomTable.rows().every(function() {
        const data = this.data();
        latestHours[data[boom_columns.indexOf('Boom Lift ID')]] = parseInt(data[boom_columns.indexOf('Hours')]) || 0;
    });

    // Form toggling
    window.toggleForm = function() {
        const role = $('#role').val();
        $('#installer-form').toggle(role === 'installer');
        $('#mechanic-form').toggle(role === 'mechanic');
        if (role === 'installer') {
            $('#installer-name').prop('required', true);
            $('#mechanic-name').prop('required', false);
        } else if (role === 'mechanic') {
            $('#installer-name').prop('required', false);
            $('#mechanic-name').prop('required', true);
        }
    };

    // Builder "Other" toggling
    window.toggleOtherBuilder = function() {
        $('#other-builder').toggle($('#builder').val() === 'Other');
    };
    window.toggleOtherBuilderMechanic = function() {
        $('#mechanic-other-builder').toggle($('#mechanic-builder').val() === 'Other');
    };

    // Maintenance cost toggling
    window.toggleOilChangeCost = function() {
        $('#oil-change-cost').toggle($('#oil-change').is(':checked'));
    };
    window.toggleAnnualInspectionCost = function() {
        $('#annual-inspection-cost').toggle($('#annual-inspection').is(':checked'));
    };
    window.toggleNDTCost = function() {
        $('#ndt-cost').toggle($('#ndt').is(':checked'));
    };
    window.toggleRadiatorRepairCost = function() {
        $('#radiator-repair-cost').toggle($('#radiator-repair').is(':checked'));
    };
    window.toggleOtherWorkCost = function() {
        $('#other-work-cost').toggle($('#other-work').val().trim() !== '');
    };

    // Hours validation
    window.updateHoursValidation = function() {
        const boomId = $('#boom-lift-id').val() || $('#mechanic-boom-lift-id').val();
        const minHours = latestHours[boomId] || 0;
        $('#hours, #mechanic-hours').attr('min', minHours).on('input', function() {
            if (parseInt(this.value) < minHours) {
                this.setCustomValidity(`Hours must be at least ${minHours}`);
            } else {
                this.setCustomValidity('');
            }
        });
    };

    // Geolocation
    window.getGeolocation = function() {
        navigator.geolocation.getCurrentPosition(
            (position) => {
                const { latitude, longitude } = position.coords;
                $('#location').val(`${latitude}, ${longitude}`);
            },
            () => alert('Unable to retrieve location.')
        );
    };
    window.getGeolocationMechanic = function() {
        navigator.geolocation.getCurrentPosition(
            (position) => {
                const { latitude, longitude } = position.coords;
                $('#mechanic-location').val(`${latitude}, ${longitude}`);
            },
            () => alert('Unable to retrieve location.')
        );
    };

    // Form submission
    $('#boom-lift-form').on('submit', function(e) {
        e.preventDefault();
        const role = $('#role').val();
        const completionTimeField = role === 'installer' ? '#completion-time' : '#mechanic-completion-time';
        $(completionTimeField).val(new Date().toISOString());

        $.ajax({
            url: 'https://formspree.io/f/mbldnvgr', // Correct url
            method: 'POST',
            data: $(this).serialize(),
            dataType: 'json',
            success: function() {
                $('#submission-message').show();
                setTimeout(() => $('#submission-message').hide(), 3000);
                $('#boom-lift-form')[0].reset();
                toggleForm();
            },
            error: function() {
                alert('Submission failed. Please try again.');
            }
        });
    });
});

// Define boom_columns (unchanged)
const boom_columns = [
    'Boom Lift ID', 'Completion time', 'Name', 'Hours', 'Oil Level', 'Gas Level',
    'General Issues', 'Last Maintenance', 'Oil Change', 'Hours Since Oil Change', 'Annual Inspection'
];
