
/* This file contains the java script part of the bakeout webapp */

/* Run code style check with: standard
   http://standardjs.com/
*/

/* global input_as_json, WebSocket, MozWebSocket, XMLHttpRequest */

/* Parse input from webapp */
var INPUT = JSON.parse(input_as_json)

/* Replace console.log with a do-nothing function, if not in debug mode */
if (INPUT['debug'] !== 'debug') {
  console.log = function () {}
}
console.log('INPUT', INPUT)

// Reverse order mapping of the diodes, because internally, the pins
// are counted from the right
var DIODE_MAPPING = {
  'diode1': 'diode6',
  'diode2': 'diode5',
  'diode3': 'diode4',
  'diode4': 'diode3',
  'diode5': 'diode2',
  'diode6': 'diode1'
}
var DIODE_COLOR_MAPS = {
    // redial_gradients have center color first
  'green': {'off': '#145a32', 'on': 'radial-gradient(#d5f5e3, #2ecc71)'},
  'red': {'off': '#641e16', 'on': 'radial-gradient(#f5b7b1, #cb4335)'}

}
var DIODE_COLOR_MAP = DIODE_COLOR_MAPS[INPUT['web_diode_color_scheme']]

function onOpen () {
    /* On load of the webpage, get initial values and init the web socket connection */
  console.log('The page has been loaded. Update with current values.')
  getJSON('get/all', onReadResponse)
  initWebsocket()
}
window.onload = onOpen

var KEYBOARD_MAP = {
  'q': ['input1', 'stepUp'],
  'w': ['input2', 'stepUp'],
  'e': ['input3', 'stepUp'],
  'r': ['input4', 'stepUp'],
  't': ['input5', 'stepUp'],
  'y': ['input6', 'stepUp'],
  'a': ['input1', 'stepDown'],
  's': ['input2', 'stepDown'],
  'd': ['input3', 'stepDown'],
  'f': ['input4', 'stepDown'],
  'g': ['input5', 'stepDown'],
  'h': ['input6', 'stepDown']
}

// event.type must be keypress
function getChar (event) {
    /* Cross broser method to get a character from a key press event */
  if (event.which == null) {
    return String.fromCharCode(event.keyCode)  // IE
  } else if (event.which != 0 && event.charCode != 0) {
    return String.fromCharCode(event.which)  // the rest
  } else {
    return null  // special key
  }
}

function parseKeyPress (event) {
    /* Parse a key press event */
  var char = getChar(event)
  console.log('KEYPRESS', char)
  var action = KEYBOARD_MAP[char]
  if (typeof action !== 'undefined') {
        // Call stepUp or stepDown on the input object ..
    var element = document.getElementById(action[0])
    element[action[1]]()
        // .. and call setChannel, since calling e.g. stepUp does not fire the onchang event
    var channel = parseInt(action[0].replace('input', ''))
    setChannel(channel)
  }
}
// Listen for keypress events for the entire body (I think that is the
// way to do what we want
document.getElementById('body').onkeypress = parseKeyPress

function websocketFailed (message) {
    /* Initialize fall back when websocket fails */
  document.getElementById('websocket_status').innerHTML = message
  WEBSOCKET = null
    // Setup polling of channel status
  window.setInterval(function () {
    getJSON('get/all', onReadResponse)
  }, INPUT['web_polling_time_msec'])
}

var WEBSOCKET
function initWebsocket () {
  /* Initialize websocket */

  // Define variables, wsuri is websocket uri
  var wsuri = 'wss://cinf-wsserver.fysik.dtu.dk:9002'

  // Work around Mozilla naming the websockets differently *GRR*
  console.log('### WebSocket Setup')
  try {
    if (window.hasOwnProperty('WebSocket')) {
      WEBSOCKET = new WebSocket(wsuri)
      console.log('Connect to websocket:', wsuri, 'using WebSocket')
    } else {
      WEBSOCKET = new MozWebSocket(wsuri)
      console.log('Connect to websocket:', wsuri, 'using MozWebSocket')
    }
  } catch (err) {
    websocketFailed('No. Making connection failed.')
    return
  }

    // Check whether we succesfully initilized the web wocket connection
  if (WEBSOCKET) {
    document.getElementById('websocket_status').innerHTML = 'Yes'
  } else {
    websocketFailed('No. Did not properly initilize.')
    return
  }

  WEBSOCKET.onopen = function () {
        /* On ws open subscribe for data from machines (hostname:port) */
    var dataChannels = []
    for (var pin = 1; pin <= 6; pin++) {
      dataChannels.push(INPUT['hostname'] + ':' + pin)
      dataChannels.push(INPUT['hostname'] + ':diode' + pin)
    }

    console.log('... WebSocket Connected!')
    console.log('Subscribe to data channels: %o', dataChannels)
    WEBSOCKET.send(JSON.stringify(
      {'action': 'subscribe', 'subscriptions': dataChannels}
    ))
  }

  WEBSOCKET.onclose = function (e) {
        /* on ws close go to no websocket mode */
    console.log('WebSocket closed: %o', e)
    websocketFailed('No. WebSocket connection closed.')
  }

  WEBSOCKET.onmessage = function (e) {
        /* ws onmessage: parse the message from JSON and process it */
    var data = JSON.parse(e.data)
    processLiveEvents(data)
  }

  WEBSOCKET.onerror = function (e) {
        /* on ws error log to console */
    console.log('WebSocket error: %o', e)
  }
}

var FIRST_LIVE_EVENT = true
function processLiveEvents (input) {
    /* Process events comming in on the live socket */
  console.log('LIVE EVENT', input)

    /* The first event comming in on the Live Socket is the reply to
     * the subscription. This may be out of sync and therefore we do
     * not use it.
     */
  if (FIRST_LIVE_EVENT) {
    FIRST_LIVE_EVENT = false
    console.log('Skipping first live event')
    return
  }
  var data = input['data']
  for (var property in data) {
    if (data.hasOwnProperty(property)) {
      if (property.startsWith('diode')) {
        processDiodeEvent(data, property)
      } else {
        processChannelEvent(data, property)
      }
    }
  }
}

function processDiodeEvent (data, property) {
  /* Process a diode event */
  var color
  var realDiodeName = DIODE_MAPPING[property]
  if (data[property][1]) {
    color = DIODE_COLOR_MAP['on']
  } else {
    color = DIODE_COLOR_MAP['off']
  }
  document.getElementById(realDiodeName).style.background = color
}

function processChannelEvent (data, property) {
  console.log('CHANNEL EVENT:', data[property], '#', property)
  document.getElementById('current_value' + property).innerHTML = data[property][1].toFixed(3)
  document.getElementById('input' + property).value = data[property][1]
}

function setChannel (channelNumber) {
  /* Set a channel to the value of its input field */
  var inputValue
  var data = {}
  inputValue = parseFloat(document.getElementById('input' + channelNumber).value)
  console.log('Settings channel ' + channelNumber + ' to ' + inputValue)
  data[[channelNumber]] = inputValue
  getJSON('set/' + encodeURIComponent(JSON.stringify(data)), onSetResponse)
}

function onSetResponse (error, data) {
  /* Call back after channel has been set */
  console.log('Set reply, error: ' + error + '   data: ' + data)
  /* The read of the current value is delayed slightly to allow the
   * application to act on the request for change */
  window.setTimeout(function () {
    getJSON('get/' + data, onReadResponse)
  }, 100)
}

function onReadResponse (error, data) {
    /* Call back after reading channel status */
  var time, value, name
  console.log('Read reply, error ' + error + '   data: ' + data)

    // The data is an array if a single channel was queried
  if (Array.isArray(data)) {
        // Think about doing some clever checks with the time
    time = data[0]
    value = data[1]
    name = data[2]
    document.getElementById('current_value' + name).innerHTML = value
  } else {
    for (var property in data) {
      if (data.hasOwnProperty(property)) {
                // For each channel, update both the current setpoint and the set point control
        document.getElementById('current_value' + property).innerHTML = data[property][1].toFixed(3)
        document.getElementById('input' + property).value = data[property][1]
      }
    }
  }
}

function toggle(list){
  /* Toggle html element visibility */
  var elementStyle=document.getElementById(list).style
  if (elementStyle.display=="none"){
    elementStyle.display = "block"
  } else {
    elementStyle.display = "none"
  }
}



/* ### Utility Functions ### */

function getJSON (url, callback) {
    /* Get the object served on a url as JSON */
  console.log('Getting JSON content of: ' + url)
  var xhr = new XMLHttpRequest()
  xhr.open('get', url, true)
  xhr.responseType = 'json'
  xhr.onload = function () {
    var status = xhr.status
    if (status === 200) {
      callback(null, xhr.response)
    } else {
      callback(status)
    }
  }
  xhr.send()
};
