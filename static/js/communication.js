(function (socket_io) {
  M.AutoInit();
  C = {};
  C.jQueryLoaded = !!window.jQuery;
  C.socket_io = socket_io
})(io());

chart_data = {
  datasets: [{
    data: [{ x: 10, y: 20 }, { x: 15, y: 2 }, { x: 20, y: 10 }],
  }]
}

function build_chart() {
  return new Chart(document.getElementById('myChart'), {
    type: 'line',
    data: {
      labels: [0],
      datasets: [
        {
          label: "Ток",
          data: [0]
        },
        {
          label: "Напряжение",
          data: [0]
        },
        {
          label: "Газ",
          data: [0]
        },
        {
          label: "Тяга",
          data: [0]
        }
      ],
    },
    options: {
      plugins: {
        legend: {
          display: true,
          position: "bottom",
          align: "start"
        }
      }
    }
  });
}


var OnConnect = function () {
  M.toast({ html: '<i class=\'material-icons\'>check</i> Сервер доступен' })
};

var OnDisconnect = function () {
  M.toast({ html: '<i class=\'material-icons\'>close</i> Связь с сервер потерена' })
};

var OnDataReceived = function (serial_data) {

  C.chart.data.labels.push(Math.floor(Date.now() / 1000));

  var current = C.chart.data.datasets[0];
  var voltage = C.chart.data.datasets[1];
  var throttle = C.chart.data.datasets[2];
  var weight = C.chart.data.datasets[3];

  Object.keys(serial_data).forEach((key) => {
    var sensor_data = serial_data[key];
    if (key == "voltage") {
      voltage.data.push(sensor_data);
    } else if (key == "current") {
      current.data.push(sensor_data);
    } else if (key == "weight") {
      weight.data.push(sensor_data);
    } else if (key == "pwm") {
      throttle.data.push(sensor_data);
    }
  });
  C.chart.update();
  console.log(serial_data);
};

var OnNewPort = function (context, ports_obj) {
  if (ports_obj.length == 0)
    return;

  disabled_model_btn = $("header").find("a.modal-trigger.disabled")
  if (disabled_model_btn.length > 0) {
    disabled_model_btn.removeClass("disabled")
  }

  selector_id = $(context.port_selector.el);
  selector_id.find("option").not(":disabled").empty();
  ports_obj.forEach((port, index) => {
    $("<option \>", { value: index, text: port.value, arr_index: port.index }).appendTo(selector_id);
  });
  context.port_selector.destroy();
  M.FormSelect.init(selector_id, { classes: "port_selector_wrapper" });
  context.port_selector = M.FormSelect.getInstance(selector_id);
  context.ports_list = ports_obj
};

C.AutoInit = function () {
  this.ports_list = []
  this.port_selector = M.FormSelect.getInstance($("select#port_selector"));
  this.port_modal = M.Modal.getInstance($(".modal#select_port_modal"));
  this.chart = build_chart();
  if (this.port_modal.$el.has("a#action_end").length > 0) {
    this.port_modal.$el.find("a#action_end").first().on("click", function () {
      if (C.socket_io.connected) {
        selector_options = $(C.port_modal.el).find(".port_selector_wrapper > * > .selected").not(".disabled");
        // slected_idx = C.port_selector.getSelectedValues()[0];
        // console.log(slected_idx);
        console.log(selector_options);
        if (selector_options.length > 0) {
          C.socket_io.emit("select_port", { name: $(selector_options).first().text().toString() });
        }
      } else {
        console.log("Not connected");
      }
    })
  }

  this.socket_io.on("connect", OnConnect);
  this.socket_io.on("disconnect", OnDisconnect);
  this.socket_io.on("new_port", (ports_list) => {
    OnNewPort(C, ports_list);
  });
  this.socket_io.on("update_serial_data", OnDataReceived);
};

C.AutoInit();
// C.port_modal.open();
// OnNewPort(C, ["test1", "test2"])



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