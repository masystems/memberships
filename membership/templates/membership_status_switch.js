drawCallback: function () {
    var url = ""
    var activeSwitch = ""
    $('.membership-status').bootstrapSwitch({
        onSwitchChange: function() {
            var memberId = parseInt($(this).attr('value'));
            activeSwitch = $(this).attr('id');
            var status = 'False';
            if($(this).is(':checked')){
                var status = 'True';
            }

            $('#update-membership-status-modal').modal('show');
            //$('#updateStatusUrl').attr("href", "/membership/update-membership-status/"+memberId+"/"+status+"/{{ membership_package.organisation_name }}/"+page);
            url = "/membership/update-membership-status/"+memberId+"/"+status+"/{{ membership_package.organisation_name }}"

        }
    });

    $('#cancelStatusModal').on('click', function () {
        memberSwitch = $('#'+activeSwitch).bootstrapSwitch()
        if(memberSwitch.is(':checked')){
            memberSwitch.bootstrapSwitch('state', false);
        } else {
            memberSwitch.bootstrapSwitch('state', true);
        }
    });

    $('#updateStatusUrl').on('click', function () {
        $.ajax({
            url: url,
            type: 'POST',
            dataType: 'text',
            headers: {'X-CSRFToken': '{{ csrf_token }}'},
            data: '',
            beforeSend: function() {
            },
            success: function(data) {
                $('#update-membership-status-modal').modal('hide');
                var result = JSON.parse(data);
                if (result['status'] == "fail") {
                    errorMsg(result['message']);
                } else {
                    infoMsg(result['message']);
                }
             },
            error: function(jqXHR, textStatus, errorThrown){
            }
        });
    })
},