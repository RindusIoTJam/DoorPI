/*jslint browser: true*/
/*global $, WebSocket, Notification*/

var audioElement;
var audioReady = false;

function prettyDate(utcSeconds) {
    "use strict";
    var d = new Date(0);
    d.setUTCSeconds(utcSeconds);
    return d.toString().substring(0, 24);
}

function notifyRing(date) {
    "use strict";
    if (Notification.permission === 'granted') {
        var options = {
            body: 'Somebody rang ' + date + '!',
            vibrate: [100, 50, 100],
        },
            notification = new Notification("DING DONG ... RING RING ... KNOCK KNOCK", options);
        console.log("Created notification: " + notification.body);
    }
}

var updater = {
    socket: null,

    start: function () {
        "use strict";
        var url = "wss://" + location.host + "/door";
        if (location.protocol !== 'https:') {
            url = "ws://" + location.host + "/door";
        }
        updater.secret = null;
        updater.socket = new WebSocket(url);
        updater.socket.onmessage = function (event) {
            console.log(event.data);
            var action = JSON.parse(event.data).action,
                pretty = prettyDate(JSON.parse(event.data).timestamp);
            if (action === "ring") {
                updater.secret = JSON.parse(event.data).secret;
                $('#open').removeAttr("disabled");
                if (audioReady === true) {
                    audioElement.play().catch(function (error) {
                        console.log("INFO: play() failed because the user didn't interact " +
                                    "with the document first. https://goo.gl/xX8pDD");
                        console.log(error);
                    });
                }
                notifyRing(pretty);
                $('#last_ring').html(pretty);
            }
            if (action === "open") {
                $('#open').prop("disabled", true);
                $('#last_open').html(pretty);
            }
            if (action === "update") {
                if (JSON.parse(event.data).last_open.length > 0) {
                    $('#last_open').html(prettyDate(JSON.parse(event.data).last_open));
                }
                if (JSON.parse(event.data).last_ring.length > 0) {
                    $('#last_ring').html(prettyDate(JSON.parse(event.data).last_ring));
                }
            }
            if (action === 'timeout') {
                $('#open').prop("disabled", true);
            }
        };
        updater.socket.onopen = function () {
            console.log("WS Connected");
            $("#alert").hide();
        };
        // Reconnect function
        updater.socket.onclose = function () {
            console.log("WS Disconnected");
            $("#alert").html("Lost connection to DoorPI, trying to reconnect.");
            $("#alert").show();
            setTimeout(function () {
                var om = updater.socket.onmessage,
                    oo = updater.socket.onopen,
                    oc = updater.socket.onclose,
                    wu = "wss://" + location.host + "/door";
                if (location.protocol !== 'https:') {
                    wu = "ws://" + location.host + "/door";
                }
                updater.socket = new WebSocket(wu);
                updater.socket.onmessage = om;
                updater.socket.onopen = oo;
                updater.socket.onclose = oc;
            }, 1000);
        };
    },
};

function send(message) {
    "use strict";
    console.log('sending', JSON.stringify(message));
    updater.socket.send(JSON.stringify(message));
}

$(document).ready(function () {
    "use strict";
    $('#open').prop("disabled", true);

    if (!window.console) { window.console = { /* NOP*/ }; }
    if (!window.console.log) { window.console.log = { /* NOP*/ }; }

    $('button').click(function (event) {
        if (event.target.id === "open") {
            $('#open').prop("disabled", true);
            send({"action": event.target.id, "secret": updater.secret });
        } else {
            send({"action": event.target.id });
        }
        return false;
    });

    setInterval(function () {
        $('#time').html(new Date().toString().substring(0, 24));
    }, 1000);

    audioElement = document.createElement('audio');
    audioElement.setAttribute('src', '//' + location.host + '/static/ding-dong.mp3');
    audioElement.addEventListener("canplay", function () {
        audioReady = true;
    });

    Notification.requestPermission(function (status) {
        if (status === 'granted') {
            console.log('Notification permission status:', status);
        }
    });

    updater.start();
});
