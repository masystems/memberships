drawCallback: function () {
    $('.membership-status').bootstrapSwitch({
        onSwitchChange: function() {
            var memberId = parseInt($(this).attr('value'));
            var status = 'False';
            if($(this).is(':checked')){
                var status = 'True';
            }

            $('#update-membership-status-modal').modal('show');
            $('#updateStatusUrl').attr("href", "/membership/update-membership-status/"+memberId+"/"+status+"/{{ membership_package.organisation_name }}");

            $(this).bootstrapSwitch('toggleState', true, true);


        }
    });
},