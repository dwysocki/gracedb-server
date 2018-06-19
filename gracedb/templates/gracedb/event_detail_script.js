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
var TIME_DISP_FMT = 'MMM D, YYYY h:mm:ss A';
//var TIME_DISP_FMT = 'LLL';

// A utility function to determine whether a log message has an image.
// This would not be necessary if we were using django template language
var hasImage = function(object) {
    if (!object.filename) return false;
    var file_extension = object.filename.slice(object.filename.length - 3);
    return image_extensions.indexOf(file_extension) >= 0; 
}

// some URLs. Usage of Django template syntax should be limited to here
var tagListUrl          = '{% url "shib:tag-list" %}';
var tagUrlPattern       = '{% url "taglogentry" object.graceid "000" "temp" %}';
var eventLogListUrl     = '{% url "shib:eventlog-list" object.graceid %}';
var eventLogSaveUrl     = '{% url "logentry" object.graceid "" %}';
var embbEventLogListUrl = '{% url "shib:embbeventlog-list" object.graceid %}';
var emObservationListUrl = '{% url "shib:emobservation-list" object.graceid %}';
var skymapJsonUrl       = '{% url "file" object.graceid "" %}';
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
    createTimeSelect(dom.byId('basic_info_event_ts'), 'gps', 'gps', true);
    createTimeSelect(dom.byId('basic_info_created_ts'), 'created', 'utc', true);
    createTimeSelect(dom.byId('neighbors_event_ts'), 'ngps', 'gps', true);
    createTimeSelect(dom.byId('neighbors_created_ts'), 'ncreated', 'utc', true);

    //----------------------------------------------------------------------------------------
    // Section for EMBB 
    //----------------------------------------------------------------------------------------
    var eventDetailContainer = dom.byId('event_detail_content');
    //var embbDiv = put(eventDetailContainer, 'div.content-area#embb_container');
    //var embbTitleDiv = put(embbDiv, 'div#embb_title_expander');
    //var embbContentDiv = put(embbDiv, 'div#embb_content'); 

    // Put the EEL form into the content div
    // FIXME This needs to be cleaned up. Empty div for now.
    //var oldEelFormDiv = dom.byId('eelFormContainer');
    //var eelFormContents = oldEelFormDiv.innerHTML;
    //var oldEmoFormDiv = dom.byId('emoFormContainer');
    //var emoFormContents = oldEmoFormDiv.innerHTML;
    // domConstruct.destroy('eelFormContainer'); 
    //domConstruct.destroy('emoFormContainer'); 
    // var embbAddDiv = put(embbContentDiv, 'div#add_eel_container');
    /* var embbAddFormDiv = put(embbAddDiv, 'div#add_eel_form_container');
    embbAddFormDiv.innerHTML = eelFormContents; */
    //var emoAddDiv = put(embbContentDiv, 'div#add_emo_container');
    //var emoAddFormDiv = put(emoAddDiv, 'div#add_emo_form_container');
    //emoAddFormDiv.innerHTML = emoFormContents; 

    //createExpandingSection(embbTitleDiv, embbContentDiv, emoAddFormDiv, 'Electromagnetic Bulletin Board');

    // Append the div that will hold our dgrid
    //put(embbContentDiv, 'div#emo-grid');

    //----------------------------------------------------------------------------------------
    // Section for log entries
    //----------------------------------------------------------------------------------------
    var annotationsDiv = put(eventDetailContainer, 'div.content-area');
    var logTitleDiv = put(annotationsDiv, 'div#log_title_expander');
    var logContentDiv = put(annotationsDiv, 'div#log_content');

    // Create the form for adding a new log entry.
    var logAddDiv = put(logContentDiv, 'div#new_log_entry_form');
    put(logAddDiv, 'div#previewer');
    put(logAddDiv, 'div#editor');
    put(logAddDiv, 'div#upload_form_container');

    // Create handlers for upload success and failture
    var uploadSuccess = function(result) {
        alert(result);
    };
    var uploadError = function(error) {
        alert(error);
    };

    createExpandingSection(logTitleDiv, logContentDiv, logAddDiv, 'Event Log Messages', true);

    //----------------------------------------------------------------------------------------
    //----------------------------------------------------------------------------------------
    // Get the tag properties. Sorta hate it that this is so complicated.
    tagStore = new declare([Rest, RequestMemory])({target: tagListUrl});
    tagStore.get('').then(function(content) { 
        var tags = content.tags;

        var tag_display_names = new Object();
        var blessed_tags = new Array();
        for (var tag_name in tags) {
            var tag = tags[tag_name];
            tag_display_names[tag_name] = tag.displayName;
            if (tag.blessed) blessed_tags.push({ name: tag_name }); 
        }
        // Reorder the blessed tags according to the priority order above.
        var new_blessed_tags = new Array();
        for (var i=0; i<blessed_tag_priority_order.length; i++) {
            var tag_name = blessed_tag_priority_order[i];
            for (var j=0; j<blessed_tags.length; j++) {
                if (blessed_tags[j].name == tag_name) {
                    new_blessed_tags.push(blessed_tags[j]);
                    break;
                }
            }
        }
        // Add the rest of them.
        for (var i=0; i<blessed_tags.length; i++) {
            if (new_blessed_tags.indexOf(blessed_tags[i]) < 0) {
                new_blessed_tags.push(blessed_tags[i]);
            }

        }
        blessed_tags = new_blessed_tags;
        var blessed_tag_names = blessed_tags.map(function (obj) { return obj.name; });
        var blessedTagStore = new Memory({ data: blessed_tags });

        // Create the tag callback generators. These don't depend on the log message contents
        // so we should be able to define them here.
        function getTagDelCallback(tag_name, N) {
            return function() {
                // Wonky replacement so we don't replace 000s in graceid or somewhere else
                // where we don't want to do that.
                tagUrl = tagUrlPattern.replace("/000/", "/"+N+"/").replace("temp",encodeURIComponent(tag_name));
                var tagResultDialog = new Dialog({ style: "width: 300px" }); 
                var actionBar = domConstruct.create("div", { "class": "dijitDialogPaneActionBar" }); 
                var tbnode = domConstruct.create("div", { 
                        style: "margin: 0px auto 0px auto; text-align: center;" 
                }, actionBar);
                var reload_page = false;
                var tagButton = new Button({ 
                    label: "Ok", 
                    onClick: function(){ 
                    tagResultDialog.hide();
                    if (reload_page) { location.reload(true); }
                }}).placeAt(tbnode); 
                request.del(tagUrl).then( 
                    function(text){ 
                        tagResultDialog.set("content", text); 
                        domConstruct.place(actionBar, tagResultDialog.containerNode); 
                        tagResultDialog.show();
                        reload_page = true;
                    }, 
                    function(error){
                        var err_msg = error;
                        if (error.response.text) { err_msg = error.response.text; }
                        tagResultDialog.set("content", "Error: " + err_msg);
                        domConstruct.place(actionBar, tagResultDialog.containerNode); 
                        tagResultDialog.show();
                        reload_page = false;
                    });
                } 
        }
        
        function getTagAddCallback(N) {
            return function() {
                // Create the tag result dialog.
                var tagResultDialog = new Dialog({ style: "width: 300px" }); 
                var actionBar = domConstruct.create("div", { "class": "dijitDialogPaneActionBar" }); 
                var tbnode = domConstruct.create("div", { 
                        style: "margin: 0px auto 0px auto; text-align: center;" 
                }, actionBar);
                var reload_page = false;
                var tagButton = new Button({ 
                    label: "Ok", 
                    onClick: function(){ 
                    tagResultDialog.hide();
                    if (reload_page) { location.reload(true); }
                    }
                }).placeAt(tbnode); 

                // Create the form
                addTagForm = new Form();
                var msg = "<p> Choose a tag \
                    name from the dropdown menu or enter a new one.  If you are \
                    creating a new tag, please also provide a display name. </p>";
                domConstruct.create("div", {innerHTML: msg} , addTagForm.containerNode);

                // Form for tagging existing log messages.
                new ComboBox({
                    name: "existingTagSelect",
                    value: "",
                    store: blessedTagStore,
                    searchAttr: "name"
                }).placeAt(addTagForm.containerNode);

                new TextBox({
                    name: "tagDispName",
                }).placeAt(addTagForm.containerNode);

                new Button({
                    type: "submit",
                    label: "OK",
                }).placeAt(addTagForm.containerNode);

                // Create the dialoge
                addTagDialog = new Dialog({
                    title: "Add Tag",
                    content: addTagForm,
                    style: "width: 300px"
                    });

                // Define the form on submit handler
                on(addTagForm, "submit", function(evt) {
                    evt.stopPropagation();
                    evt.preventDefault();
                    formData = addTagForm.getValues();
                    var tagName = formData.existingTagSelect;
                    var tagDispName = formData.tagDispName;
                    // Wonky replacement so we don't replace 000s in graceid or somewhere else
                    // where we don't want to do that.
                    var tagUrl = tagUrlPattern.replace("/000/", "/"+N+"/").replace("temp", tagName);

                    request.post(tagUrl, {
                        data: {displayName: tagDispName}
                    }).then(
                        function(text){
                            tagResultDialog.set("content", text);
                            domConstruct.place(actionBar, tagResultDialog.containerNode);
                            tagResultDialog.show();
                            reload_page = true;
                        },
                        function(error){
                            var err_msg = error;
                            if (error.response.text) { err_msg = error.response.text; }
                            tagResultDialog.set("content", "Error: " + err_msg);
                            domConstruct.place(actionBar, tagResultDialog.containerNode);
                            tagResultDialog.show();
                            reload_page = false;
                        }
                   );
                   addTagDialog.hide();
                });

                // show the dialog
                addTagDialog.show();
            }
        }

        //----------------------------------------------------------------------------------------
        //----------------------------------------------------------------------------------------
        // Now that we've got the tag info, let's get the event log objects.
        logStore = new declare([Rest, RequestMemory])({target: eventLogListUrl});
        logStore.get('').then(function(content) {

            // Pull the logs out of the JSON returned by the server.
            var logs = content.log;
            var Nlogs = logs.length;

            // Convert the 'created' times to UTC.
            logs = logs.map( function(obj) {
                var server_t = moment.tz(obj.created, 'America/Chicago');
                obj.created = server_t.clone().tz('UTC').format(TIME_DISP_FMT);
                return obj;
            });
            
            // Total up the tags present. This list will have duplicates.
            var total_tags = new Array();
            logs.forEach( function(log) { 
                log.tag_names.forEach( function (tag_name) {
                    total_tags.push(tag_name);
                });
            });
            
            // Figure out what blessed tags are present. 
            var our_blessed_tags = blessed_tag_names.filter( function(value) {
                return total_tags.indexOf(value) >= 0;
            });

            var skymap_stems = new Array();
            logs.forEach( function(log) {
                if (log.tag_names.indexOf('sky_loc') >= 0 && log.filename.indexOf('.fits') >= 0) {
                    skymap_stems.push(log.filename.slice(0,log.filename.indexOf('.fits')));
                } 
            });

            var isJsonSkymap = function(filename) {
                var is_skymap = false;
                if (filename.indexOf('.json') >= 0) {
                    skymap_stems.forEach( function(stem) {
                        if (filename.indexOf(stem) >= 0) {
                            is_skymap = true;
                        }
                    });
                }
                return is_skymap;
            };

            // If there are any blessed tags here, we'll do TitlePanes
            if (our_blessed_tags.length > 0) {
                // define our columns for the topical digest panes
                var columns = [
                    { 
                        field: 'created', 
                        renderHeaderCell: function(node) {
                            timeHeaderContainer = put(node, 'div');
                            createTimeSelect(timeHeaderContainer, 'log', 'llo');
                            put(timeHeaderContainer, 'div', 'Log Entry Created');
                            return timeHeaderContainer;
                        },
                        renderCell: function(object, value, node, options) {
                            var server_t = moment.tz(object.created, 'America/Chicago');
                            var t = put(node, 'time[name="time-log"]', server_t.format(TIME_DISP_FMT));
                            put(t, '[utc="$"]', server_t.clone().tz('UTC').format(TIME_DISP_FMT));
                            put(t, '[llo="$"]', server_t.format(TIME_DISP_FMT));
                            put(t, '[lho="$"]', server_t.clone().tz('America/Los_Angeles').format(TIME_DISP_FMT));
                            put(t, '[virgo="$"]', server_t.clone().tz('Europe/Rome').format(TIME_DISP_FMT));
                            return t;                                                       
                        }
                    }, 
                    { field: 'issuer', label: 'Submitter', get: function(obj) { return obj.issuer.display_name; } },
                    // Sometimes the comment contains HTML, so we just want to return whatever it has.
                    // This is where the link with the filename goes. Also the view in skymapViewer button
                    { 
                        field: 'comment', 
                        label: 'Comment', 
                        renderCell: function(object, value, node, options) {
                            var commentDiv = put(node, 'div');
                            // Putting this in the innerHTML allows users to create comments in HTML.
                            // Whereas, inserting the comment with the put selector escapes it.
                            commentDiv.innerHTML += value + ' ';
                            if (object.filename) put(commentDiv, 'a[href=$]', object.file, object.filename);
                            // Branson, 3/3/15
                            //if (object.filename == 'skymap.json') {
                            var isItJson = object.filename.indexOf(".json");
                            //if (isItJson  > -1) {
                            if (isJsonSkymap(object.filename)) {
                                var skymapName = object.filename.substring(0, isItJson);
                                var svButton = put(commentDiv, 
                                    'button.modButtonClass.sV_button#'+skymapName, 'View in SkymapViewer!');
                                put(svButton, '[type="button"][data-dojo-type="dijit/form/Button"]');
                                put(svButton, '[style="float: right"]');
                            }
                            return commentDiv;
                        }
                    },

                ]; 

                // Create the topical digest title panes
                for (i=0; i<our_blessed_tags.length; i++) {
                    var tag_name = our_blessed_tags[i];
                    // First filter the log messages based on whether they have this blessed tag.
                    var tagLogs = logs.filter( function(obj) { 
                        // XXX Not sure why this simpler filter didn't work.
                        // return obj.tag_names.indexOf(tag_name) > 0;
                        for (var k=0; k<obj.tag_names.length; k++) {
                            if (obj.tag_names[k]==tag_name) return true;
                        }
                        return false;  
                    });

                    // Next filter the remaining log messages based on whether or not images are present.
                    var imgLogs = tagLogs.filter( function(obj) { return hasImage(obj); });
                    var noImgLogs = tagLogs.filter ( function(obj) { return !hasImage(obj); }); 

                    // Create the title pane with a placeholder div
                    var pane_contents_id = tag_name.replace(/ /g,"_") + '_pane';
                    var tp = new TitlePane({ 
                        title: tag_display_names[tag_name],
                        content: '<div id="' + pane_contents_id + '"></div>',
                        open: true
                    });
                    logContentDiv.appendChild(tp.domNode);
                    paneContentsNode = dom.byId(pane_contents_id);

                    // Handle the log messages with images by putting them in little box.
                    if (imgLogs.length) {
                        var figContainerId = tag_name.replace(/ /g,"_")  + '_figure_container';
                        var figDiv = put(paneContentsNode, 'div#' + figContainerId);
                        // Instead of living in a table row, the figures will now just be placed
                        // directly into the div, in inline blocks.
                        //var figRow = put(figDiv, 'table.figure_container tr');
                        for (j=0; j<imgLogs.length; j++) {
                            var log = imgLogs[j];
                            //var figTabInner = put(figRow, 'td table.figures'); 
                            var figTabInner = put(figDiv, 'table.figures'); 
                            var figA = put(figTabInner, 'tr.figrow img[height="180"][src=$]', log.file); 
                            new dojox.image.LightboxNano({href: log.file}, figA); 
                            var figComment = put(figTabInner, 'tr td');
                            figComment.innerHTML = log.comment;
                            figComment.innerHTML += ' <a href="' + log.file + '">' + log.filename + '.</a> ';
                            figComment.innerHTML += 'Submitted by ' + log.issuer.display_name + ' on ' + log.created;
                        }
                        // XXX Have commented out the scroll pane at Patrick's request.
                        // var sp = new dojox.layout.ScrollPane({ orientation: "horizontal", style: "overflow: hidden;" }, figContainerId); 

                    }

                    // Handle the log messages without images by putting them in a grid.
                    if (noImgLogs.length) {
                        var gridNode = put(paneContentsNode, 'div#' + pane_contents_id + '-grid')
                        var grid = new declare([Grid, DijitRegistry])({
                            columns: columns,
                            className: 'dgrid-autoheight',
                            // Overriding renderRow here to add an extra class to the row. This is for styling.
                            renderRow: function(object,options) {
                                return put('div.supergrid-row', Grid.prototype.renderRow.call(this,object,options));
                            }
                        }, gridNode);
                        grid.renderArray(noImgLogs);
                        grid.set("sort", 'N', descending=true);
                    }

                }

                // Create the EMObservations title pane
                // XXX Branson fixme
                var pane_contents_id = 'emobservations_pane_div';
                
                // Create the title pane with a placeholder div
                var emo_tp = new TitlePane({ 
                    title: 'EM Observations',
                    content: '<div id="' + pane_contents_id + '"></div>',
                    open: true
                });
                logContentDiv.appendChild(emo_tp.domNode);
    
                var emoDiv = dom.byId(pane_contents_id);
                // Create the section for adding EMObservation records. First an outer container:
                var emoAddDiv = put(emoDiv, 'div#add_emo_container');
                // The order is important. First the toggling form display button, then the form.
                // FIXME: Such a sad way of putting in vertical space.
                put(emoDiv, 'br')
                var addEmoButtonNode = put(emoAddDiv, 'div.expandFormButton', '(add observation record)');
                var emoAddFormDiv = put(emoAddDiv, 'div#add_emo_form_container');
                domStyle.set(emoAddFormDiv, 'display', 'none');
                
                on(addEmoButtonNode, "click", function() {
                    if (domStyle.get(emoAddFormDiv, 'display') == 'none') {
                        domStyle.set(emoAddFormDiv, 'display', 'block');
                        addEmoButtonNode.innerHTML = '(cancel)';
                    } else {
                        domStyle.set(emoAddFormDiv, 'display', 'none');
                        addEmoButtonNode.innerHTML = '(add observation record)';
                    }
                });

                // Grab the form fragment and put it in the right place.
                var oldEmoFormDiv = dom.byId('emoFormContainer');
                var emoFormContents = oldEmoFormDiv.innerHTML;               
                domConstruct.destroy('emoFormContainer');
                emoAddFormDiv.innerHTML = emoFormContents;
                
                // Create the div for our grid to attach to
                put(emoDiv, 'div#emo-grid');

                // Create the full event-log title pane
                var columns = [
                    { field: 'N', label: 'No.' },
                    { 
                        field: 'created', 
                        renderHeaderCell: function(node) {
                            timeHeaderContainer = put(node, 'div');
                            var ts = createTimeSelect(timeHeaderContainer, 'audit-log', 'llo');
                            put(timeHeaderContainer, 'div', 'Log Entry Created');
                            // XXX Not sure how to get this to do the right thing.
                            return timeHeaderContainer; 
                            //return ts;
                        },
                        renderCell: function(object, value, node, options) {
                            var server_t = moment.tz(object.created, 'America/Chicago');
                            var t = put(node, 'time[name="time-audit-log"]', server_t.format(TIME_DISP_FMT));
                            put(t, '[utc="$"]', server_t.clone().tz('UTC').format(TIME_DISP_FMT));
                            put(t, '[llo="$"]', server_t.format(TIME_DISP_FMT));
                            put(t, '[lho="$"]', server_t.clone().tz('America/Los_Angeles').format(TIME_DISP_FMT));
                            put(t, '[virgo="$"]', server_t.clone().tz('Europe/Rome').format(TIME_DISP_FMT));
                            return t;                                                       
                        }
                    }, 
{ field: 'issuer', label: 'Submitter', get: function(obj) { return obj.issuer.display_name; } },
                    // Sometimes the comment contains HTML, so we just want to return whatever it has.
                    // This is where the link with the filename goes. Also the view in skymapViewer button
                    { 
                        field: 'comment', 
                        label: 'Comment', 
                        renderCell: function(object, value, node, options) {
                            commentDiv = put(node, 'div');
                            // Putting this in the innerHTML allows users to create comments in HTML.
                            // Whereas, inserting the comment with the put selector escapes it.
                            commentDiv.innerHTML += value + ' ';
                            if (object.filename) put(commentDiv, 'a[href=$]', object.file, object.filename);
                            // Create tag-related features
                            var tagButtonContainer = put(commentDiv, 'div.tagButtonContainerClass');
                            // For each existing tag on a log message, we will make a little widget
                            // to delete it.
                            object.tag_names.forEach( function(tag_name) {
                                var delDiv = put(tagButtonContainer, 'div.tagDelButtonDivClass');
                                var del_button_id = "del_button_" + object.N + '_' + tag_name.replace(/ /g, "_");
                                var delButton = put(delDiv, 'button.modButtonClass.left#' + del_button_id);
                                put(delButton, '[data-dojo-type="dijit/form/Button"]');
                                // It looks like an 'x', so people will know that this means 'delete'
                                delButton.innerHTML = '&times;';
                                var labButton = put(delDiv, 'button.modButtonClass.right', tag_name); 
                            }); 
                            // Create a button for adding a new tag.
                            var add_button_id = 'addtag_' + object.N;
                            var addButton = put(tagButtonContainer, 'button.modButtonClass#' + add_button_id);
                            put(addButton, '[data-dojo-type="dijit/form/Button"]');
                            // Put a plus sign in there.
                            addButton.innerHTML = '&#43;';

                            // The div is finally ready. Return it.
                            return commentDiv;
                        }
                    },
                    {
                        field: 'image',
                        label: ' ',
                        renderCell: function(object, value, node, options) {
                            if (value) {
                                imgNode = put(node, 'img[height="60"][src="$"]', value);
                                return new dojox.image.LightboxNano({ href: value }, imgNode); 
                            }
                        },
                        get: function(object) { 
                            if (hasImage(object)) {
                                return object.file;
                            } else {
                                return null;
                            }
                        },
                    }
                ]; 

                var pane_contents_id = 'full_log_pane_div';
                
                // Create the title pane with a placeholder div
                var tp = new TitlePane({ 
                    title: 'Full Event Log',
                    content: '<div id="' + pane_contents_id + '"></div>',
                    //open: false
                    open: true
                });
                logContentDiv.appendChild(tp.domNode);

                var grid = new declare([Grid, DijitRegistry])({
                    minRowsPerPage: Nlogs,
                    columns: columns,
                    className: 'dgrid-autoheight',
                    renderRow: function(object,options) {
                        return put('div.supergrid-row', Grid.prototype.renderRow.call(this,object,options));
                    }
                }, pane_contents_id);
                grid.renderArray(logs);
                grid.set("sort", 'N', descending=true);

                // Now that we've constructed it, let's close the title pane. 
                tp.toggle()

            } else {
                // Not doing title panes, just put up the usual log message section.
                // Will have the full eventlog section. Same as above, except that it 
                // won't be in a title pane. What is the best way to do this.

                // If we're not doing title panes, we still need to remember to destroy
                // the emoFormContainer. Otherwise it shows up!
                domConstruct.destroy('emoFormContainer');

                var columns = [
                    { field: 'N', label: 'No.' },
                    { field: 'created', label: 'Log Entry Created (UTC)' }, 
                    { field: 'issuer', label: 'Submitter', get: function(obj) { return obj.issuer.display_name; } },
                    // Sometimes the comment contains HTML, so we just want to return whatever it has.
                    // This is where the link with the filename goes. Also the view in skymapViewer button
                    { 
                        field: 'comment', 
                        label: 'Comment', 
                        renderCell: function(object, value, node, options) {
                            commentDiv = put(node, 'div');
                            // Putting this in the innerHTML allows users to create comments in HTML.
                            // Whereas, inserting the comment with the put selector escapes it.
                            commentDiv.innerHTML += value + ' ';
                            if (object.filename) put(commentDiv, 'a[href=$]', object.file, object.filename);
                            // Create tag-related features
                            var tagButtonContainer = put(commentDiv, 'div.tagButtonContainerClass');
                            // For each existing tag on a log message, we will make a little widget
                            // to delete it.
                            object.tag_names.forEach( function(tag_name) {
                                var delDiv = put(tagButtonContainer, 'div.tagDelButtonDivClass');
                                var del_button_id = "del_button_" + object.N + '_' + tag_name.replace(/ /g, "_");
                                var delButton = put(delDiv, 'button.modButtonClass.left#' + del_button_id);
                                put(delButton, '[data-dojo-type="dijit/form/Button"]');
                                // It looks like an 'x', so people will know that this means 'delete'
                                delButton.innerHTML = '&times;';
                                var labButton = put(delDiv, 'button.modButtonClass.right', tag_name); 
                            }); 
                            // Create a button for adding a new tag.
                            var add_button_id = 'addtag_' + object.N;
                            var addButton = put(tagButtonContainer, 'button.modButtonClass#' + add_button_id);
                            put(addButton, '[data-dojo-type="dijit/form/Button"]');
                            // Put a plus sign in there.
                            addButton.innerHTML = '&#43;';

                            // The div is finally ready. Return it.
                            return commentDiv;
                        }
                    },
                    {
                        field: 'image',
                        label: ' ',
                        renderCell: function(object, value, node, options) {
                            if (value) {
                                imgNode = put(node, 'img[height="60"][src="$"]', value);
                                return new dojox.image.LightboxNano({ href: value }, imgNode); 
                            }
                        },
                        get: function(object) { 
                            if (hasImage(object)) {
                                return object.file;
                            } else {
                                return null;
                            }
                        },
                    }
                ]; 

                var grid = new declare([Grid, DijitRegistry])({
                    minRowsPerPage: Nlogs,
                    columns: columns,
                    className: 'dgrid-autoheight',
                    renderRow: function(object,options) {
                        return put('div.supergrid-row', Grid.prototype.renderRow.call(this,object,options));
                    }
                }, logContentDiv);
                grid.renderArray(logs);
                grid.set("sort", 'N', descending=true);

            }

            //-------------------------------------------------------------------
            // Finally, let's see if we can get those EMOs in
            //-------------------------------------------------------------------
            emoStore = new declare([Rest, RequestMemory])({target: emObservationListUrl});
            emoStore.get('').then(function(content) {
                // Pull the EELs out of the rest content and create a new simple store from them.
                var emos = content.observations;

                if (emos.length == 0) {
                    emoDiv = dom.byId('emo-grid');

                    if (emoDiv !=== null) {
                        emoDiv.innerHTML = '<p> No EM observation entries so far. </p>';
                    }

                    // Let's try toggling the emo title pane closed.
                    //if (emo_tp.open) { emo_tp.toggle(); }
                } else {

                    // Notice that the +00:00 designating UTC will be stripped out since it 
                    // is redundant.
                    var columns  = [
                        { field: 'created', label: 'Time Created (UTC)', get: function(object) { return object.created.replace('+00:00', '');} },
                        { field: 'submitter', label: 'Submitter' },
                        { field: 'group', label: 'MOU Group' },
                        { field: 'footprint_count', label: 'N_regions' },
                        { field: 'radec',
                          label: 'Covering (ra, dec)',
                            get: function(object){
                                var raLoc = Math.round10(object.ra, -2);
                                var raHalfWidthLoc = Math.round10(object.raWidth/2.0, -2);
                                var decLoc = Math.round10(object.dec, -2);
                                var decHalfWidthLoc = Math.round10(object.decWidth/2.0, -2);
                                var rastring = raLoc + " \xB1 " + raHalfWidthLoc;
                                var decstring = decLoc + " \xB1 " + decHalfWidthLoc;
                                return "(" + rastring + ','  + decstring + ")";
                            },
                        }
                    ]; 

                    var subRowColumns  = [ 
                        { field: 'start_time', label: 'Start Time (UTC)', get: function(object) { return object.start_time.replace('+00:00', '');} },
                        { field: 'exposure_time', label: 'Exposure Time (s)' },
                        { field: 'ra', label: 'ra'},
                        { field: 'raWidth', label: 'ra width'},
                        { field: 'dec', label: 'dec'},
                        { field: 'decWidth', label: 'dec width'}
                    ]; 

                    // Add extra class names to our grid cells so we can style them separately
                    for (i = 0; i < columns.length; i++) {
                        columns[i].className = 'supergrid-cell';
                    }
                    for (i = 0; i < subRowColumns.length; i++) {
                        subRowColumns[i].className = 'subgrid-cell';
                    }

                    var grid = new Grid({ 
                        columns: columns,
                        className: 'dgrid-autoheight',

                        renderRow: function (object, options) {
                            // Add the supergrid-row class to the row so we can style it separately from the subrows.
                            var div = put('div.collapsed.supergrid-row', Grid.prototype.renderRow.call(this, object, options));

                            // Add the subdiv table which will expand and contract.
                            var t = put(div, 'div.expando table');
                            // I'm finding that the table needs to be 100% of the available width, otherwise
                            // Firefox doesn't like it. Hence the extra empty column.
                            var subGridNode = put(t, 'tr td[style="width: 5%"]+td div');
                            var sg = new Grid({
                                columns: subRowColumns,
                                className: 'dgird-subgrid',
                            }, subGridNode);
                            sg.renderArray(object.footprints);
                            // Add the text comment div as long as the comment is not an empty string.
                            if (object.comment !== "") {
                                put(t, 'tr td[style="width: 5%"]+td div.subrid-text', object.comment); 
                            }

                            return div;
                        }
                    }, 'emo-grid'); 
                    grid.renderArray(emos);
                    grid.set("sort", 'N', descending=true);

                    var expandedNode = null;

                    // listen for clicks to trigger expand/collapse in table view mode
                    var expandoListener = on(grid.domNode, '.dgrid-row:click', function (event) {
                        var node = grid.row(event).element;
                        var collapsed = node.className.indexOf('collapsed') >= 0;

                        // toggle state of node which was clicked
                        put(node, (collapsed ? '!' : '.') + 'collapsed');

                        // XXX Commenting out the following two statements has the effect of allowing
                        // more than one of the subrows to be expanded at the same time. I think this
                        // is the sort of behavior that people expect.
                        // if clicked row wasn't expanded, collapse any previously-expanded row
                        // collapsed && expandedNode && put(expandedNode, '.collapsed');

                        // if the row clicked was previously expanded, nothing is expanded now
                        // expandedNode = collapsed ? node : null;
                    });
                } // endif on whether we have any emos or not.
            });


            //-------------------------------------------------------------------
            // Now that the annotations section has been added to the dom, we
            // can work on its functionality.
            //-------------------------------------------------------------------
            var logtitle = dom.byId("logmessagetitle");
            var logtext = dom.byId("newlogtext");

            var editor_div = dom.byId("editor");
            var preview_div = dom.byId("previewer");

            // A pane holder for the form that will tag new log messages.
            // I need it up here because we're going to integrate it with the
            // editor components.
            /* 
            dojo.style(preview_div, { 'display':'none'});
            dojo.style(editor_div, { 'display':'none'});

            var button_element = dojo.create('button');
            dojo.place(button_element, logtitle, "right");
            var button = new Button({
                label: "Add Log Entry",
                state: "add",
                onClick: function(){
                    if (this.state == 'add') {
                        dojo.style(editor_div, {'display':'block'});
                        button.set('label', "Cancel Log Entry");
                        button.set('state', 'cancel');
                        editor.focus();
                    }
                    else {
                        dojo.style(editor_div, {'display':'none'});
                        dojo.style(preview_div, {'display':'none'});
                        button.set('label', "Add Log Entry");
                        button.set('state', 'add');
                        editor.set('value','');
                    }
                },
            }, button_element); */

            var savebutton = new Save({
                    url: eventLogSaveUrl,
                    onSuccess: function (resp, ioargs) {
                        //this.inherited(resp, ioargs);
                        this.button.set("disabled", false);
                        location.reload(true);
                    },
                    onError: function (error, ioargs) {
                        //this.inherited(error, ioargs);
                        this.button.set("disabled", false);
                        alert("o hai " + error);
                    },
                    save: function(postdata) {
                        var newTagName = "analyst_comments";
                        if (dom.byId('upload_input').files.length > 0) {
                            dom.byId("hidden_comment").value = postdata;
                            dom.byId("hidden_tagname").value = newTagName;
                            dom.byId("file_attach_form").submit();
                        } else { 
                            var postArgs = {
                                    url: this.url,
                                    content: { comment: postdata, tagname: newTagName },
                                    handleAs: "json"
                            };
                            this.button.set("disabled", true);
                            var deferred = dojo.xhrPost(postArgs);
                            deferred.addCallback(dojo.hitch(this, this.onSuccess));
                            deferred.addErrback(dojo.hitch(this, this.onError));
                        }

                    }
            });

            var previewbutton = new Preview({
                _preview: function(){
                        var content = this.editor.get("value");
                        preview_div.innerHTML = editor.get('value');
                        dojo.style(preview_div, {
                            'display':'block',
                            'border': ".2em solid #900",
                            'padding': '10px'
                        });
                        MathJax.Hub.Queue(["Typeset",MathJax.Hub, preview_div]);
                    }
            });

            var editor = new Editor({
                 extraPlugins : ['hiliteColor','|','createLink',
                                 'insertImage','fullscreen','viewsource','newpage', '|', previewbutton, savebutton] 
            }, editor_div);
            editor.startup();

            //-------------------------------------------------------------------------------------
            //-------------------------------------------------------------------------------------
            // The following section is for file attachments
            // The idea of this form is to allow a user to attach a file to a log entry, but
            // still submit the log entry via the usual save button. 
            var upload_div = dom.byId('upload_form_container');
            put(upload_div, 'p', 'Attach a file:')
            var f = put(upload_div, 'form[action="' + eventLogSaveUrl + '"]');
            put(f, '[method="post"]');
            put(f, '[enctype="multipart/form-data"]');
            put(f, '[id="file_attach_form"]');
            var i1 = put(f, 'input[id="upload_input"][name="uploadedFile"]');
            put(i1, '[multiple="false"]');
            put(i1, '[type="file"]');
            put(i1, '[label="Attach"]');
            put(i1, '[data-dojo-type="dojox.form.uploader"]');
            var i2 = put(f, 'input[id="hidden_comment"][name="comment"][type="hidden"]');
            var i3 = put(f, 'input[id="hidden_tagname"][name="tagname"][type="hidden"]');
            put(upload_div, 'br');
            //-------------------------------------------------------------------------------------
            //-------------------------------------------------------------------------------------

            // For each log, attach callbacks for the tag delete and add buttons.
            logs.forEach( function(log) {
                // Attach a delete callback for each tag.
                log.tag_names.forEach( function(tag_name) {
                    var del_button_id = "del_button_" + log.N + '_' + tag_name.replace(/ /g,"_");
                    on(dom.byId(del_button_id), "click", getTagDelCallback(tag_name, log.N));
                    new Tooltip({ connectId: del_button_id, label: "delete this tag" });
                });

                // Attach an add tag callback for each log.
                var add_button_id = 'addtag_' + log.N;
                on(dom.byId(add_button_id), "click", getTagAddCallback(log.N));
                new Tooltip({ connectId: add_button_id, label: "tag this log message" });

            });                 

            var nodeList = query('.sV_button');
            for(var i=0; i<nodeList.length; i++){
                node = nodeList[i];
                var skymapName = node.id;
                // Handle the post to skymapViewer button.
                // Tacking on an invisible div with a form inside.
                sVdiv = put(annotationsDiv, 'div#sV_form_div[style="display: none"]');
                sVform = put(sVdiv, 'form#sV_form[method="post"][action="$"]', 
                encodeURI(skymapViewerUrl));
                put(sVform, 'input[type="hidden"][name="skymapid"][value="{{ object.graceid }}"]'); 
                put(sVform, 'input[type="hidden"][name="json"]');
                put(sVform, 'input[type="hidden"][name="embb"]');
                put(sVform, 'input[type="submit"][value="View in skymapViewer!"]');
            
                var sV_button = node;
                if (sV_button) {
                    on(sV_button, "click", function(e) {
                        sjurl = skymapJsonUrl + '/' + e.target.id + '.json';
                        var embblog_json_url = embbEventLogListUrl;
                        var embblog_json;
                        var emobservation_json_url = emObservationListUrl;

                        dojo.xhrGet({
                            //url: embblog_json_url + "?format=json",
                            // Removing backwards compatibility hack
                            //url: emobservation_json_url + "?format=json&skymapViewer",
                            url: emobservation_json_url + "?format=json",
                            async: true,
                            load: function(embblog_json) {
    
                            // fetch JSON content.
                            dojo.xhrGet({
                                url: sjurl,
                                load: function(result) { 
                                    // Find the form and set its value to the appropriate JSON        
                                    sV_form = dom.byId("sV_form");
                                    // Shove the skymap.json contents into the value for the second form field.
                                    sV_form.elements[1].value = result; 
                                    sV_form.elements[2].value = embblog_json; 
                                    // Submit the form, which takes the user to the skymapViewer server.
                                    sV_form.submit();
                                }
                            });    // end of inside ajax
                            }
                        });        // end of outside ajax
                    });
                }
            }   // end of loop over buttons


        });
    });


});

