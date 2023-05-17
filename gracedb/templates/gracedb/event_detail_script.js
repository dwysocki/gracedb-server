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

