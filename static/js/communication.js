(function (socket_io) {
  M.AutoInit();
  C = {};
  C.jQueryLoaded = !!window.jQuery;
  C.socket_io = socket_io
})(io());

function build_param_chart(element_id) {
  return new Chart($("#" + element_id), {
    type: "doughnut",
    data: {
      datasets: [
        {
          data: [100, 0]
        }
      ]
    },
    options: {
      plugins: {
        legend: {
          display: false
        },
        title: {
          display: false
        }
      }
    }
  })
}

const chart_default_data = {
  labels: [0],
  datasets: [
    {
      label: "Ток",
      data: [0],
    },
    {
      label: "Напряжение",
      data: [0],
      hidden: true
    },
    {
      label: "Газ",
      data: [0],
      hidden: true
    },
    {
      label: "Тяга",
      data: [0]
    },
    {
      label: "КЭ",
      data: [0]
    }
  ],
};

function build_mian_chart() {
  return new Chart($("#main_chart"), {
    type: 'line',
    data: structuredClone(chart_default_data),
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


let OnConnect = function () {
  M.toast({ html: '<i class=\'material-icons\'>check</i> Сервер доступен' })
};

let OnDisconnect = function () {
  M.toast({ html: '<i class=\'material-icons\'>close</i> Связь с сервер потерена' })
};

let kp_val = 0.0;
const filter_gain = 0.35;
const HW_INIT = 0;
const HW_IDLE = 1;
const HW_RUN_TEST = 4;
const HW_CALIB = 6;
const HW_STOPING_WORK = 7;

let OnDataReceived = function (serial_data) {
  if (C.data_list.length > 100) {
    C.data_list.shift();
  }
  C.data_list.push(serial_data);

  C.hw_status = parseInt(serial_data["state"]);
  let voltage_val = serial_data["voltage"];
  let current_val = serial_data["current"];
  let weight_val = serial_data["weight"];
  let throttle_val = serial_data["pwm"];
  // let kp_val = 0.0;
  if (parseFloat(weight_val) > 0.1) {
    kp_val = (kp_val * filter_gain) + ((1 - filter_gain) * (parseFloat(weight_val) / (parseFloat(current_val) * parseFloat(voltage_val))));
    kp_val = Math.round(kp_val * 100) / 100;
  }

  if (C.hw_status == HW_RUN_TEST) {
    C.main_chart.data.labels.push(C.main_chart.data.labels.length + 1);
    let current_arr = C.main_chart.data.datasets[0];
    let voltage_arr = C.main_chart.data.datasets[1];
    let throttle_arr = C.main_chart.data.datasets[2];
    let weight_arr = C.main_chart.data.datasets[3];
    let performance_arr = C.main_chart.data.datasets[4];

    voltage_arr.data.push(voltage_val);
    current_arr.data.push(current_val);
    weight_arr.data.push(weight_val);
    let _range = parseFloat(throttle_val) - 1000.0;
    throttle_arr.data.push(_range * 0.1);
    performance_arr.data.push(kp_val);

    C.main_chart.update();
  }

  if (Object.keys(C.digits).length > 0) {
    Object.keys(C.digits).forEach((key) => {
      if (key == "voltage") {
        C.digits[key].text(voltage_val.toString());
      } else if (key == "current") {
        C.digits[key].text(current_val.toString());
      } else if (key == "weight") {
        C.digits[key].text(weight_val.toString());
      } else if (key == "throttle") {
        C.digits[key].text(throttle_val.toString());
      } else if (key == "performance") {
        C.digits[key].text(kp_val.toString());
      }
    });
  }

  console.log(serial_data);
};

let OnNewPort = function (context, ports_obj) {
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

let FindDigits = function () {
  let panels = $(".digits-panel");

  if (panels == undefined || panels.length == 0) {
    console.log("Digits panel not found");
    return [];
  }

  const current_item = panels.find("#current_val").first();
  const voltage_item = panels.find("#voltage_val").first();
  const weight_item = panels.find("#weight_val").first();
  const throttle_item = panels.find("#throttle_val").first();
  const performance_item = panels.find("#performance_val").first();

  return { current: current_item, voltage: voltage_item, weight: weight_item, throttle: throttle_item, performance: performance_item };
};

let OnStartTest = function (event) {
  let context = event.data.context;
  if (context.socket_io.active && context.hw_status == HW_IDLE) {
    console.log("start test");
    event.data.context.socket_io.emit("new_cmd", { cmd: "101" });
    if (event.data.context.main_chart.data.labels.length > 10) {
      event.data.context.session.push(structuredClone(event.data.context.main_chart.data));
    }
    event.data.context.main_chart.data = structuredClone(chart_default_data);
    event.data.context.main_chart.update();
  }
};

let OnStopTest = function (event) {
  let context = event.data.context;
  if (context.socket_io.active) {
    console.log("stop test");
    event.data.context.socket_io.emit("new_cmd", { cmd: "254" });
  }
};

let OnStartCalibration = function (event) {
  let context = event.data.context;
  if (context.socket_io.active && context.hw_status == HW_IDLE) {
    console.log("start calib");
    event.data.context.socket_io.emit("new_cmd", { cmd: "212" });
  }
};

let create_session_obj = function() {
  return { time: Date(), is_notified: false };
}

C.AutoInit = function () {
  this.ports_list = []
  this.data_list = []
  this.session = []
  this.port_selector = M.FormSelect.getInstance($("select#port_selector"));
  this.port_modal = M.Modal.getInstance($(".modal#select_port_modal"));
  this.main_chart = build_mian_chart();
  this.digits = FindDigits();
  this.start_test_btn = $(".action_panel").find("a#start_test").first();
  this.stop_test_btn = $(".action_panel").find("a#stop_test").first();
  this.start_calibration_btn = $("a#start_calibration").first();
  this.hw_status = HW_INIT;
  this.session_obj = create_session_obj();
  if (this.port_modal.$el.has("a#action_end").length > 0) {
    this.port_modal.$el.find("a#action_end").first().on("click", function () {
      if (C.socket_io.connected) {
        selector_options = $(C.port_modal.el).find(".port_selector_wrapper > * > .selected").not(".disabled");
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

  if (this.start_test_btn != undefined) {
    this.start_test_btn.click({ context: this }, OnStartTest);
  }

  if (this.stop_test_btn != undefined) {
    this.stop_test_btn.click({ context: this }, OnStopTest);
  }

  if (this.start_calibration_btn != undefined) {
    this.start_calibration_btn.click({ context: this }, OnStartCalibration);
  }
};

C.AutoInit();