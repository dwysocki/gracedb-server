var tl;

var eventSource = new Timeline.DefaultEventSource();

function onLoad() {
  var bandInfos = [
    Timeline.createBandInfo({
        eventSource:    eventSource,
        //date:           "Sat May 20 1961 00:00:00 GMT-0600",
        width:          "70%", 
        intervalUnit:   Timeline.DateTime.HOUR, 
        intervalPixels: 100
    }),
    Timeline.createBandInfo({
        eventSource:    eventSource,
        //date:           "Sat May 20 1961 00:00:00 GMT-0600",
        width:          "15%", 
        intervalUnit:   Timeline.DateTime.DAY, 
        intervalPixels: 100,
        overview:       true
    }),
    Timeline.createBandInfo({
        eventSource:    eventSource,
        //date:           "Sat May 20 1961 00:00:00 GMT-0600",
        width:          "15%", 
        intervalUnit:   Timeline.DateTime.MONTH, 
        intervalPixels: 200,
        overview:       true
    })
  ];
  bandInfos[1].syncWith = 0;
  bandInfos[1].highlight = true;
  bandInfos[2].syncWith = 1;
  bandInfos[2].highlight = true;
  tl = Timeline.create(document.getElementById("tl"), bandInfos);
  Timeline.loadJSON("/gracedb/events/timeline",
                    function(json, url) { eventSource.loadJSON(json, url); });
}
var resizeTimerID = null;
function onResize() {
    if (resizeTimerID == null) {
        resizeTimerID = window.setTimeout(function() {
            resizeTimerID = null;
            tl.layout();
        }, 500);
    }
}
