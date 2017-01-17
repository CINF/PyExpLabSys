
/* This file contains the java script part of the bakeout webapp */

function update_with_initial_values(){
    /* Ask for initial values when the page has loaded */
    console.log("The page has been loaded. Update with current values.");
    getJSON("get/all", on_initial_value_response);
}
window.onload = update_with_initial_values;

function on_initial_value_response(error, data){
    /* Call back for when the page has loaded */
    console.log("Reply to initial values were", data);
    for (var property in data) {
        if (data.hasOwnProperty(property)) {
            // For each channel, update both the current setpoint and the set point control
            document.getElementById("current_value" + property).innerHTML = data[property][1].toFixed(2);
            document.getElementById("input" + property).value = data[property][1];
        }
    }
}

function set_channel(channel_number){
    /* Set a channel to the value of its input field */
    var input_value, data = {};
    input_value = parseFloat(document.getElementById("input" + channel_number).value);
    console.log("Settings channel " + channel_number + " to " + input_value);
    data[[channel_number]] = input_value;
    getJSON("set/" + encodeURIComponent(JSON.stringify(data)), on_set_response);
    
}

function on_set_response(error, data){
    /* Call back after channel has been set */
    console.log("Set reply, error: " + error + "   data: " + data);
    /* The read of the current value is delayed slightly to allow the
     * application to act on the request for change */
    window.setTimeout(function(){
        read_channel(data);
    }, 100);
}


function read_channel(channel_number){
    /* Get the setpoint of channel and set on webpage */
    console.log("Get channel status: " + channel_number);
    data = getJSON("get/" + channel_number, on_read_response);
    
}

function on_read_response(error, data){
    /* Call back after reading channel status */
    var time, value, name;
    console.log("Read reply, error " + error + "   data: " + data);

    // Think about doing some clever checks with the time
    time = data[0];
    value = data[1];
    name = data[2];
    document.getElementById("current_value" + name).innerHTML = value;
}


/* ### Utility Functions ### */

function getJSON(url, callback) {
    /* Get the object served on a url as JSON */
    console.log("Getting JSON content of: " + url);
    var xhr = new XMLHttpRequest();
    xhr.open("get", url, true);
    xhr.responseType = "json";
    xhr.onload = function() {
      var status = xhr.status;
      if (status == 200) {
        callback(null, xhr.response);
      } else {
        callback(status);
      }
    };
    xhr.send();
};
