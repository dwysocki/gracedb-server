require([
    'dojo/_base/declare',
    'dojo/query',
    'dojo/on',
    'dojo/parser',
    'dojo/dom',
    'dojo/dom-construct',
    'dojo/dom-style',
    'dojo/request',
    'dojo/store/Memory',
    'dojo/data/ObjectStore',
    'dstore/Rest',
    'dstore/RequestMemory',
    'dgrid/Grid',
    'dgrid/extensions/DijitRegistry',
    'put-selector/put',
    'dijit/TitlePane',
    'dijit/form/Form',        
    'dijit/form/Button',
    'dijit/form/TextBox',
    'dijit/form/ComboBox',
    'dijit/form/Select',
    'dijit/Tooltip',
    'dijit/Dialog',
    'dijit/Editor',
    'dojox/editor/plugins/Save',
    'dojox/editor/plugins/Preview',
    'dojox/layout/ScrollPane',
    'dojox/form/Uploader',
//    'dojox/form/uploader/plugins/HTML5',
    'dojox/form/uploader/plugins/IFrame',
    'dojox/image/LightboxNano',
    'dijit/_editor/plugins/TextColor',
    'dijit/_editor/plugins/LinkDialog',
    'dijit/_editor/plugins/ViewSource',
    'dijit/_editor/plugins/NewPage',
    'dijit/_editor/plugins/FullScreen',
    'dojo/domReady!',
], function(declare, query, on, parser, dom, domConstruct, domStyle, request, Memory, ObjectStore,
    Rest, RequestMemory, Grid, DijitRegistry, 
    put, 
    TitlePane, Form, Button, TextBox, ComboBox, Select, Tooltip, Dialog, Editor, 
    Save, Preview, ScrollPane, Uploader) {

    parser.parse();


    // We don't enable the input buttons until right now otherwise fast users
    // can trigger the form before the javascript is ready... not ideal
    $("#confirm_as_gw_form input[type=submit]").attr('disabled', false);
    // Confirm as GW form
    $("#confirm_as_gw_form").submit(function(e) {
        e.preventDefault();

        // Get button and disable it to prevent multiple clicks
        var submit_button = $(this).find("input[type=submit]");
        submit_button.attr("disabled", true);

        // Make ajax request
        $.ajax({
            type: $(this).attr('method'),
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

    $(".signoff_form input[type=submit]").attr('disabled', false);

    // Signoff form - determine HTTP method type and url based on
    // attributes of button which was pressed. Then submit to
    // API url and reload
    $(".signoff_form").submit(function(e) {
        e.preventDefault();

        // Get HTTP method from button used to submit form
        var submit_button = $(this).find("input[type=submit][clicked=true]");
        var button_id = submit_button.attr("id"); 
        var http_method = 'POST';
        if (button_id == 'update') {
            http_method = 'PATCH';
        } else if (button_id == 'delete') {
            http_method = 'DELETE';
        }

        // Get URL from button used to submit form; otherwise use
        // main form action
        var url = submit_button.attr('formaction');
        if (url === undefined) {
            url = $(this).attr('action');
        }

        // Get and disable all submit buttons on the form
        var all_submit_buttons = $(this).find('input[type=submit]');
        all_submit_buttons.attr("disabled", true);

        // Make ajax request
        $.ajax({
            type: http_method,
            url: url,
            data: $(this).serialize(),
            success: function(resp) {
                // Don't need to re-enable since we reload the page
                //all_submit_buttons.attr("disabled", false);
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
                // Re-enable all submit buttons
                all_submit_buttons.attr("disabled", false);
            }
        });
    });
    // Handles determination of which button was used to submit form
    $(".signoff_form input[type=submit]").click(function() {
        $("input[type=submit]", $(this).parents("form")).removeAttr("clicked");
        $(this).attr("clicked", true);
    });

    // We don't enable the input buttons until right now otherwise fast users
    // can trigger the form before the javascript is ready... not ideal
    $("#permissions_form input[type=submit]").attr('disabled', false);
    // Permissions form - submit to URL and reload
    $("#permissions_form").submit(function(e) {
        e.preventDefault();

        // Get button and disable it to prevent multiple clicks
        var submit_button = $(this).find("input[type=submit]");
        submit_button.attr("disabled", true);

        $.ajax({
            type: 'POST',
            url: $(this).attr('action'),
            data: $(this).serialize(),
            success: function(resp) {
                //this.button.set("disabled", false);
                location.reload(true);
            },
            error: function(error) {
                //this.button.set("disabled", false);
                alert(error);
                // Re-enable submit button
                submit_button.attr("disabled", false);
            }
        });
    });


});

