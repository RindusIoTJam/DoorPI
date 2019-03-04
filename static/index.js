var audioElement;
var audioReady = false;

$(document).ready(function() {
    $('#open').prop("disabled", true);

    if (!window.console) window.console = {};
    if (!window.console.log) window.console.log = function() {};

    $('button').click(function(event) {
        if( event.target.id == "open" ) {
            $('#open').prop("disabled", true);
            send({"action": event.target.id, "secret": updater.secret });
        }
        else {
            send({"action": event.target.id });
        }
        return false;
    });

    setInterval(function() {
        $('#time').html(new Date().toString().substring(0, 24));
    }, 1000);

    audioElement = document.createElement('audio');
    audioElement.setAttribute('src', '//' + location.host + '/static/ding-dong.mp3');
    audioElement.addEventListener("canplay",function() {
        audioReady = true;
    });

    Notification.requestPermission(function(status) {
        if (status === 'granted') {
          console.log('Notification permission status:', status);
        }
    });

    updater.start();
});

function notifyRing(date) {
    if (Notification.permission == 'granted') {
        var options = {
            body: `Somebody rang (${date})`,
            vibrate: [100, 50, 100],
        };
        new Notification("DING DONG ... RING RING ... KNOCK KNOCK", options);
    }
}

function send(message) {
    updater.socket.send( JSON.stringify(message) );
}

function prettyDate(utcSeconds) {
    var d = new Date(0);
    d.setUTCSeconds(utcSeconds);
    return d.toString().substring(0, 24);
}

var updater = {
    socket: null,

    start: function() {
        if (location.protocol != 'https:') {
            var url = "ws://" + location.host + "/door";
        } else {
            var url = "wss://" + location.host + "/door";
        }
        updater.secret = null
        updater.socket = new WebSocket(url);
        updater.socket.onmessage = function(event) {
            console.log(event.data);
            action=JSON.parse(event.data)['action'];
            if( action == "ring" ) {
                updater.secret = JSON.parse(event.data)['secret'];
                $('#open').removeAttr("disabled");
                if ( audioReady = true ) {
                    audioElement.play().catch(function(error) {
                        console.log("INFO: play() failed because the user didn't interact " +
                                    "with the document first. https://goo.gl/xX8pDD");
                    });
                }
                var pretty = prettyDate(JSON.parse(event.data)['timestamp']);
                notifyRing(pretty);
                $('#last_ring').html(pretty);
            }
            if( action == "open" ) {
                $('#open').prop("disabled", true);
                $('#last_open').html(prettyDate(JSON.parse(event.data)['timestamp']));
            }
            if( action == "update" ) {
                if ( JSON.parse(event.data)['last_open'].length > 0 ) {
                    $('#last_open').html(prettyDate(JSON.parse(event.data)['last_open']));
                }
                if ( JSON.parse(event.data)['last_ring'].length > 0 ) {
                    $('#last_ring').html(prettyDate(JSON.parse(event.data)['last_ring']));
                }
            }
            if( action == 'timeout' ) {
                $('#open').prop("disabled", true);
            }
        }
        updater.socket.onopen = function(event) {
            console.log("WS Connected");
            $("#alert").hide();
        }
        // Reconnect function
        updater.socket.onclose = function(event) {
            console.log("WS Disconnected");
            $("#alert").html("Lost connection to DoorPI, trying to reconnect.")
            $("#alert").show();
            setTimeout(function() {
                om=updater.socket.onmessage;
                oo=updater.socket.onopen;
                oc=updater.socket.onclose;
                if (location.protocol != 'https:') {
                    updater.socket = new WebSocket("ws://" + location.host + "/door");
                } else {
                    updater.socket = new WebSocket("wss://" + location.host + "/door");
                }
                updater.socket.onmessage=om;
                updater.socket.onopen=oo;
                updater.socket.onclose=oc;
            }, 1000);
        }
    },
};