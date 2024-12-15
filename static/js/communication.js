(function (socket_io) {
  C = {};
  C.jQueryLoaded = !!window.jQuery;
  C.socket_io = socket_io
})(io());

var OnConnect = function () {
  M.toast({ html: '<i class=\'material-icons\'>check</i> Сервер доступен' })
};

var OnDisconnect = function () {
  M.toast({ html: '<i class=\'material-icons\'>close</i> Связь с сервер потерена' })
};

var OnDataReceive = function () {
};

var OnNewPort = function (context, ports_list) {
  if (ports_list.length == 0)
    return;

  disabled_model_btn = $("header").find("a.modal-trigger.disabled")
  if (disabled_model_btn.length > 0) {
    disabled_model_btn.removeClass("disabled")
  }
  
  C.ports_list = ports_list

  selector_id = $(context.port_selector.el);
  selector_id.find("option").not(":disabled").empty();
  ports_list.forEach((port, index) => {
    $("<option \>", { value: index + 1, text: port }).appendTo(selector_id);
  });
  context.port_selector.destroy();
  M.FormSelect.init(selector_id);
  context.port_selector = M.FormSelect.getInstance(selector_id);
};

C.AutoInit = function () {
  this.ports_list = []
  this.port_selector = M.FormSelect.getInstance($("select#port_selector"));
  this.port_modal = M.Modal.getInstance($(".modal#select_port_modal"));
  if (this.port_modal.$el.has("a#action_end").length > 0) {
    this.port_modal.$el.find("a#action_end").first().on("click", function () {
      console.log(C.port_selector.getSelectedValues());
    })
  }

  this.socket_io.on("connect", OnConnect);
  this.socket_io.on("disconnect", OnDisconnect);
  this.socket_io.on("new_port", (ports_list) => {
    OnNewPort(this, ports_list);
  });

};

C.AutoInit();
// C.port_modal.open();
OnNewPort(C, ["test1", "test2"])



/* socket.on('connect', function () {
  M.toast({ html: 'Connected' })
});

socket.on("serial_data", (msg) => {

});

socket.on("request", (msg) => {
  M.toast({ html: msg.data })
  if (msg.event == "new_port") {
    console.log(msg.data)
    for (let i = 0; i < msg.data.length; i++) {
      $("ul#cmn_ports").append($("<li/>", {
        html: "<a href='#!'>" + msg.data[i] + "</a>"
      }));
    }

  }
}) */