drawCallback: function () {
    var url = ""
    $('.membership-status').bootstrapSwitch({
        onSwitchChange: function() {
            var memberId = parseInt($(this).attr('value'));
            var status = 'False';
            if($(this).is(':checked')){
                var status = 'True';
            }

            $('#update-membership-status-modal').modal('show');
            //$('#updateStatusUrl').attr("href", "/membership/update-membership-status/"+memberId+"/"+status+"/{{ membership_package.organisation_name }}/"+page);
            url = "/membership/update-membership-status/"+memberId+"/"+status+"/{{ membership_package.organisation_name }}"

        }
    });

    $('#updateStatusUrl').on('click', function () {
        console.log(url)
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