require([
    'dojo/_base/declare',
    'dojo/query',
    'dojo/on',
    'dojo/parser',
], function(declare, query, on, parser) {

    parser.parse();

    // We don't enable the input buttons until right now otherwise fast users
    // can trigger the form before the javascript is ready... not ideal
    $("#update_grbevent_form input[type=submit]").attr('disabled', false);
    // Update GRB form
    $("#update_grbevent_form").submit(function(e) {
        e.preventDefault();

        // Get button and disable it to prevent multiple clicks
        var submit_button = $(this).find("input[type=submit]");
        submit_button.attr("disabled", true);

        // Make ajax request - we have to specify a PATCH method here
        // since we can't do it in the HTML
        $.ajax({
            type: 'PATCH',
            url: $(this).attr('action'),
            data: $(this).serialize(),
            success: function(resp) {
                // Don't need to re-enable since we reload the page
                //submit_button.attr("disabled", false);
                location.reload(true);
            },
            error: function(error) {
                //this.button.set("disabled", false);
                var err_msg = "Error " + error.status + ": ";
                if (error.responseText != "") {
                    err_msg += error.responseText;
                } else {
                    err_msg += error.statusText;
                }
                if (error.status == 404) {
                    err_msg += ". Reload the page.";
                }
                alert(err_msg);
                // Re-enable submit button
                submit_button.attr("disabled", false);
            }
        });
    });

});

