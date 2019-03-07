/*jslint browser: true*/
/*global self, WebSocket*/

var updater = {
    socket: null,

    start: function () {
        "use strict";
        var action,
            url = "wss://" + location.host + "/door";
        if (location.protocol !== 'https:') {
            url = "ws://" + location.host + "/door";
        }
        updater.secret = null;
        updater.socket = new WebSocket(url);
        updater.socket.onmessage = function (event) {
            action = JSON.parse(event.data).action;
            if (action === "ring") {
                updater.secret = JSON.parse(event.data).secret;
            }
        };
        // Reconnect function
        updater.socket.onclose = function () {
            setTimeout(function () {
                var om = updater.socket.onmessage,
                    oc = updater.socket.onclose;
                if (location.protocol !== 'https:') {
                    updater.socket = new WebSocket("ws://" + location.host + "/door");
                } else {
                    updater.socket = new WebSocket("wss://" + location.host + "/door");
                }
                updater.socket.onmessage = om;
                updater.socket.onclose = oc;
            }, 1000);
        };
    },
};

self.addEventListener('notificationclick', function (event) {
    "use strict";
    //var messageId = event.notification.data;
    event.notification.close();

    if (event.action === 'open') {
        // clients.openWindow("/?open");
        updater.socket.send(JSON.stringify(
            {
                "action": "open",
                secret: updater.secret
            }
        ));
    }
}, false);

updater.start();