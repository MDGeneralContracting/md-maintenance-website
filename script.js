console.log('script.js file loaded immediately');

$(document).ready(function() {
    console.log('script.js loaded');

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

    let latestHours = {};
    boomTable.rows().every(function() {
        const data = this.data();
        latestHours[data[boom_columns.indexOf('Boom Lift ID')]] = parseInt(data[boom_columns.indexOf('Hours')]) || 0;
    });

    window.toggleForm = function() {
        const role = $('#role').val();
        const installerForm = $('#installer-form');
        const mechanicForm = $('#mechanic-form');
        
        if (role === 'installer') {
            installerForm.show();
            mechanicForm.hide();
            $('#installer-name, #boom-lift-id, #site, #hours, #oil-level, #gas-level, #certify-installer').prop('required', true);
            $('#mechanic-name, #mechanic-boom-lift-id, #mechanic-site, #mechanic-hours, #mechanic-oil-level, #mechanic-gas-level, #certify-mechanic').prop('required', false);
        } else if (role === 'mechanic') {
            installerForm.hide();
            mechanicForm.show();
            $('#installer-name, #boom-lift-id, #site, #hours, #oil-level, #gas-level, #certify-installer').prop('required', false);
            $('#mechanic-name, #mechanic-boom-lift-id, #mechanic-site, #mechanic-hours, #mechanic-oil-level, #mechanic-gas-level, #certify-mechanic').prop('required', true);
        } else {
            installerForm.hide();
            mechanicForm.hide();
        }
    };

    window.toggleOtherBuilder = function() {
        $('#other-builder').toggle($('#builder').val() === 'Other');
    };
    window.toggleOtherBuilderMechanic = function() {
        $('#mechanic-other-builder').toggle($('#mechanic-builder').val() === 'Other');
    };

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

    $(document).on('submit', '#boom-lift-form', function(e) {
    e.preventDefault();
    console.log('Submit button clicked');

    const role = $('#role').val();
    console.log('Selected role:', role);

    const completionTimeField = role === 'installer' ? '#completion-time' : '#mechanic-completion-time';
    $(completionTimeField).val(new Date().toISOString());
    console.log('Completion time set:', $(completionTimeField).val());

    // Log raw input values directly
    const formData = {};
    $(this).find('input, select, textarea').each(function() {
        const name = $(this).attr('name');
        const value = $(this).val();
        if (name) formData[name] = value;
    });
    console.log('Raw form data:', formData);

    const githubToken = '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'; // Replace with your PAT
    const repoOwner = 'MDGeneralContracting';
    const repoName = 'md-maintenance-website';
    const apiUrl = `https://api.github.com/repos/${repoOwner}/${repoName}/dispatches`;
    console.log('API URL:', apiUrl);

    $.ajax({
        url: apiUrl,
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${githubToken}`,
            'Accept': 'application/vnd.github+json',
            'Content-Type': 'application/json'
        },
        data: JSON.stringify({
            event_type: 'form_submission',
            client_payload: formData
        }),
        beforeSend: function() {
            console.log('Sending API request...');
        },
        success: function(response) {
            console.log('API request successful:', response);
            const successMessage = $('<div class="success-message">Submission successful! Redirecting to Home...</div>');
            $('body').append(successMessage);
            successMessage.css({
                position: 'fixed',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                backgroundColor: '#0F4467',
                color: '#ffffff',
                padding: '20px 40px',
                borderRadius: '10px',
                fontSize: '1.5rem',
                boxShadow: '0 4px 15px rgba(0, 0, 0, 0.3)',
                zIndex: 1000
            });
            setTimeout(() => {
                window.location.href = 'index.html';
            }, 2000);
        },
        error: function(xhr, status, error) {
            console.error('API request failed:', {
                status: status,
                error: error,
                response: xhr.responseJSON,
                statusCode: xhr.status
            });
            alert('Submission failed: ' + (xhr.responseJSON?.message || error));
        }
    });
});
    const boom_columns = [
        'Boom Lift ID', 'Completion time', 'Name', 'Hours', 'Oil Level', 'Gas Level',
        'General Issues', 'Last Maintenance', 'Oil Change', 'Hours Since Oil Change', 
        'Annual Inspection', 'NDT', 'Radiator Repair'
    ];
});
