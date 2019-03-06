self.addEventListener('notificationclick', function(event) {
  var messageId = event.notification.data;

  event.notification.close();

  if (event.action === 'open') {
    // clients.openWindow("/?open");
    updater.socket.send( JSON.stringify(
      {
        "action": "open",
        secret: updater.secret
      }
    ));
  }
}, false);


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
            action=JSON.parse(event.data)['action'];
            if( action == "ring" ) {
              
                updater.secret = JSON.parse(event.data)['secret'];
            }
        }
        // Reconnect function
        updater.socket.onclose = function(event) {
            setTimeout(function() {
                om=updater.socket.onmessage;
                oc=updater.socket.onclose;
                if (location.protocol != 'https:') {
                    updater.socket = new WebSocket("ws://" + location.host + "/door");
                } else {
                    updater.socket = new WebSocket("wss://" + location.host + "/door");
                }
                updater.socket.onmessage=om;
                updater.socket.onclose=oc;
            }, 1000);
        }
    },
};

updater.start();