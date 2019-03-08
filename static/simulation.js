/*jslint browser: true*/
/*global $, WebSocket, Notification*/

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
        send({"action": event.target.id });
        return false;
    });

    updater.start();
});
