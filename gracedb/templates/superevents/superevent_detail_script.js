// Ugh. Why do I have to pull the stuff in here?

// Constructs text for label tooltips
function tooltiptext(name, creator, time, description) {
    //return ( creator + " " + time + "<br/>" + label_descriptions[name] );
    return ( creator + " (" + time + "): " + description );
};
var tooltip=function(){
 var id = 'tt';
 var top = 3;
 var left = 3;
 var maxw = 300;
 var speed = 10;
 var timer = 20;
 var endalpha = 95;
 var alpha = 0;
 var tt,t,c,b,h;
 var ie = document.all ? true : false;
 return{
  show:function(v,w){
   if(tt == null){
    tt = document.createElement('div');
    tt.setAttribute('id',id);
    t = document.createElement('div');
    t.setAttribute('id',id + 'top');
    c = document.createElement('div');
    c.setAttribute('id',id + 'cont');
    b = document.createElement('div');
    b.setAttribute('id',id + 'bot');
    tt.appendChild(t);
    tt.appendChild(c);
    tt.appendChild(b);
    document.body.appendChild(tt);
    tt.style.opacity = 0;
    tt.style.filter = 'alpha(opacity=0)';
    document.onmousemove = this.pos;
   }
   tt.style.display = 'block';
   c.innerHTML = v;
   tt.style.width = w ? w + 'px' : 'auto';
   if(!w && ie){
    t.style.display = 'none';
    b.style.display = 'none';
    tt.style.width = tt.offsetWidth;
    t.style.display = 'block';
    b.style.display = 'block';
   }
  if(tt.offsetWidth > maxw){tt.style.width = maxw + 'px'}
  h = parseInt(tt.offsetHeight) + top;
  clearInterval(tt.timer);
  tt.timer = setInterval(function(){tooltip.fade(1)},timer);
  },
  pos:function(e){
   var u = ie ? event.clientY + document.documentElement.scrollTop : e.pageY;
   var l = ie ? event.clientX + document.documentElement.scrollLeft : e.pageX;
   tt.style.top = (u - h) + 'px';
   tt.style.left = (l + left) + 'px';
  },
  fade:function(d){
   var a = alpha;
   if((a != endalpha && d == 1) || (a != 0 && d == -1)){
    var i = speed;
   if(endalpha - a < speed && d == 1){
    i = endalpha - a;
   }else if(alpha < speed && d == -1){
     i = a;
   }
   alpha = a + (i * d);
   tt.style.opacity = alpha * .01;
   tt.style.filter = 'alpha(opacity=' + alpha + ')';
  }else{
    clearInterval(tt.timer);
     if(d == -1){tt.style.display = 'none'}
  }
 },
 hide:function(){
  clearInterval(tt.timer);
   tt.timer = setInterval(function(){tooltip.fade(-1)},timer);
  }
 };
}();


// This should probably also go somewhere else.
// Closure
(function() {
  /**
   * Decimal adjustment of a number.
   *
   * @param {String}  type  The type of adjustment.
   * @param {Number}  value The number.
   * @param {Integer} exp   The exponent (the 10 logarithm of the adjustment base).
   * @returns {Number} The adjusted value.
   */
  function decimalAdjust(type, value, exp) {
    // If the exp is undefined or zero...
    if (typeof exp === 'undefined' || +exp === 0) {
      return Math[type](value);
    }
    value = +value;
    exp = +exp;
    // If the value is not a number or the exp is not an integer...
    if (isNaN(value) || !(typeof exp === 'number' && exp % 1 === 0)) {
      return NaN;
    }
    // Shift
    value = value.toString().split('e');
    value = Math[type](+(value[0] + 'e' + (value[1] ? (+value[1] - exp) : -exp)));
    // Shift back
    value = value.toString().split('e');
    return +(value[0] + 'e' + (value[1] ? (+value[1] + exp) : exp));
  }

  // Decimal round
  if (!Math.round10) {
    Math.round10 = function(value, exp) {
      return decimalAdjust('round', value, exp);
    };
  }
  // Decimal floor
  if (!Math.floor10) {
    Math.floor10 = function(value, exp) {
      return decimalAdjust('floor', value, exp);
    };
  }
  // Decimal ceil
  if (!Math.ceil10) {
    Math.ceil10 = function(value, exp) {
      return decimalAdjust('ceil', value, exp);
    };
  }
})();


// A utility
var getKeys = function(obj){
   var keys = [];
   for(var key in obj){
      keys.push(key);
   }
   return keys;
}

var image_extensions = ['png', 'gif', 'jpg'];
var TIME_DISP_FMT = 'MMM D, YYYY h:mm:ss A z';
var UTC_TIME_DISP_FMT = 'MMM D, YYYY HH:mm:ss z';
var UTC_TIME_INPUT_FMT = 'YYYY-MM-DD HH:mm:ss z';
//var TIME_DISP_FMT = 'LLL';

// A utility function to determine whether a log message has an image.
// This would not be necessary if we were using django template language
var hasImage = function(object) {
    if (!object.filename) return false;
    var file_extension = object.filename.slice(object.filename.length - 3);
    return image_extensions.indexOf(file_extension) >= 0; 
}

// some URLs. Usage of Django template syntax should be limited to here
var tagListUrl          = '{% url "legacy_apiweb:default:tag-list" %}';
var tagCreateUrlPattern = '{% url "legacy_apiweb:default:superevents:superevent-log-tag-list" superevent.superevent_id "000" %}';
var tagDeleteUrlPattern = '{% url "legacy_apiweb:default:superevents:superevent-log-tag-detail" superevent.superevent_id "000" "FAKE_TAG_NAME" %}';
var logListUrl     = '{% url "legacy_apiweb:default:superevents:superevent-log-list" superevent.superevent_id %}';
var logSaveUrl     = '{% url "legacy_apiweb:default:superevents:superevent-log-list" superevent.superevent_id %}';
var emObservationListUrl = '{% url "legacy_apiweb:default:superevents:superevent-emobservation-list" superevent.superevent_id %}';
var fileDownloadUrl     = '{% url "legacy_apiweb:default:superevents:superevent-file-detail" superevent.superevent_id "FAKE_FILE_NAME" %}';
var skymapViewerUrl     = '{{ SKYMAP_VIEWER_SERVICE_URL }}';

// This little list determines the priority ordering of the digest sections.
var blessed_tag_priority_order = [
    'analyst_comments',
    'psd',
    'data_quality',
    'sky_loc',
    'background',
    'ext_coinc',
    'strain',
    'tfplots',
    'sig_info',
    'audio',    
];

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

    //----------------------------------------------------------------------------------------
    // Some utility functions
    //----------------------------------------------------------------------------------------
    var createExpandingSection = function (titleNode, contentNode, formNode, titleText, initiallyOpen) {

        // Instead let's make a table. 
        var titleTableRow = put(titleNode, "table tr");
        var expandGlyphNode = put(titleTableRow, "td.title div.expandGlyph"); 
        var titleTextNode = put(titleTableRow, "td.title h2", titleText);
        var addButtonNode = put(titleTableRow, "td.title div.expandFormButton", '(add)');

        if (!(initiallyOpen && initiallyOpen==true)) { 
            put(expandGlyphNode, '.closed');
            domStyle.set(contentNode, 'display', 'none');
            domStyle.set(addButtonNode, 'display', 'none'); 
        }
        // This one is always closed initially
        domStyle.set(formNode, 'display', 'none');
       
        on(expandGlyphNode, "click", function() {
            if (domStyle.get(contentNode, 'display') == 'none') {
                domStyle.set(contentNode, 'display', 'block');
                domStyle.set(addButtonNode, 'display', 'block'); 
                put(expandGlyphNode, '!closed');
            } else {
                domStyle.set(contentNode, 'display', 'none');
                domStyle.set(addButtonNode, 'display', 'none');
                put(expandGlyphNode, '.closed');
            }
        });
        
        on(titleTextNode, "click", function() {
            if (domStyle.get(contentNode, 'display') == 'none') {
                domStyle.set(contentNode, 'display', 'block');
                domStyle.set(addButtonNode, 'display', 'block'); 
                put(expandGlyphNode, '!closed');
            } else {
                domStyle.set(contentNode, 'display', 'none');
                domStyle.set(addButtonNode, 'display', 'none');
                put(expandGlyphNode, '.closed');
            }
        });

        on(addButtonNode, "click", function() {
            if (domStyle.get(formNode, 'display') == 'none') {
                domStyle.set(formNode, 'display', 'block');
                addButtonNode.innerHTML = '(cancel)';
            } else {
                domStyle.set(formNode, 'display', 'none');
                addButtonNode.innerHTML = '(add)';
            }
        });
    }

    var createExpandingSectionNoForm = function (titleNode, contentNode, titleText, initiallyOpen) {
        // Instead let's make a table. 
        var titleTableRow = put(titleNode, "table tr");
        var expandGlyphNode = put(titleTableRow, "td.title div.expandGlyph"); 
        var titleTextNode = put(titleTableRow, "td.title h2", titleText);

        if (!(initiallyOpen && initiallyOpen==true)) { 
            put(expandGlyphNode, '.closed');
            domStyle.set(contentNode, 'display', 'none');
        }
       
        on(expandGlyphNode, "click", function() {
            if (domStyle.get(contentNode, 'display') == 'none') {
                domStyle.set(contentNode, 'display', 'block');
                put(expandGlyphNode, '!closed');
            } else {
                domStyle.set(contentNode, 'display', 'none');
                put(expandGlyphNode, '.closed');
            }
        });
        
        on(titleTextNode, "click", function() {
            if (domStyle.get(contentNode, 'display') == 'none') {
                domStyle.set(contentNode, 'display', 'block');
                put(expandGlyphNode, '!closed');
            } else {
                domStyle.set(contentNode, 'display', 'none');
                put(expandGlyphNode, '.closed');
            }
        });
    }

    var timeChoicesData = [ 
        {"id": "llo",   "label": "LLO Local"},
        {"id": "lho",   "label": "LHO Local"},
        {"id": "virgo", "label": "Virgo Local"},
        {"id": "utc",   "label": "UTC"},
    ];
    // XXX Fixme. So. Bad.
    var timeChoicesDataWithGps = [ 
        {"id": "gps",   "label": "GPS Time"},
        {"id": "llo",   "label": "LLO Local"},
        {"id": "lho",   "label": "LHO Local"},
        {"id": "virgo", "label": "Virgo Local"},
        {"id": "utc",   "label": "UTC"},
    ];

    var timeChoices = new Memory ({ data: timeChoicesData });
    var timeChoicesStore = new ObjectStore({ objectStore: timeChoices});
    var timeChoicesWithGps = new Memory ({ data: timeChoicesDataWithGps });
    var timeChoicesWithGpsStore = new ObjectStore({ objectStore: timeChoicesWithGps});

    var createTimeSelect = function(node, label, defaultName, useGps) {
        var myStore = (useGps) ? timeChoicesWithGpsStore : timeChoicesStore;
        var s = new Select({ store: myStore }, node);
        s.attr("value", defaultName);
        s.on("change", function () { changeTime(this, label); });
        return s;
    }

    //----------------------------------------------------------------------------------------
    // Take care of stray time selects
    //----------------------------------------------------------------------------------------
    createTimeSelect(dom.byId('preferred_event_gps_ts'), 'pref_event_gps', 'gps', true);
    createTimeSelect(dom.byId('preferred_event_created_ts'), 'pref_event_created', 'utc', true);
    createTimeSelect(dom.byId('superevent_created_ts'), 'superevent_created', 'utc', true);


});

