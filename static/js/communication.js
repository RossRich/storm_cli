(function (socket_io) {
  M.AutoInit();
  C = {};
  C.jQueryLoaded = !!window.jQuery;
  C.socket_io = socket_io
})(io());

let VIEW_DATA_SRC = {
  UPDATE_CONF: 0,
  SELECT_DEVICE: 1
};

let SYSTEM_CMD = {
  START_TEST: 10,
  STOP_TEST: 11,
  SETUP_ESC: 12,
  GET_CONFIG: 14
};

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
};

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

function get_mian_chart() {
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
};


let OnConnectToast = function () {
  M.toast({ html: '<i class=\'material-icons\'>desktop_windows</i> Сервер активен' });
};

let OnDisconnectToast = function () {
  M.toast({ html: '<i class=\'material-icons\'>close</i> Связь с сервером потеряна' });
};

let OnNewPortToast = function () {
  M.toast({ html: '<i class=\'material-icons\'>usb</i> Найдено новое устройство' });
};

let OnNewCfgToast = function () {
  M.toast({ html: '<i class=\'material-icons\'>settings</i> Новые параметры приняты' });
};

let kp_val = 0.0;
const filter_gain = 0.35;
const HW_INIT = 0;
const HW_IDLE = 1;
const HW_RUN_TEST = 4;
const HW_CALIB = 6;
const HW_STOPING_WORK = 7;

let OnNewMeasurements = function (context, measurements) {
  // let serial_data = serial_data_t.data;
  // if (C.data_list.length > 100) {
  // C.data_list.shift();
  // }
  // C.data_list.push(serial_data);

  C.hw_status = parseInt(measurements["state"]);
  let voltage_val = measurements["voltage"];
  let current_val = measurements["current"];
  let weight_val = measurements["weight"];
  let throttle_val = measurements["pwm"];
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

  if (Object.keys(C.value_fields).length > 0) {
    Object.keys(C.value_fields).forEach((key) => {
      if (key == "voltage") {
        C.value_fields[key].text(voltage_val.toString());
      } else if (key == "current") {
        C.value_fields[key].text(current_val.toString());
      } else if (key == "weight") {
        C.value_fields[key].text(weight_val.toString());
      } else if (key == "throttle") {
        C.value_fields[key].text(throttle_val.toString());
      } else if (key == "performance") {
        C.value_fields[key].text(kp_val.toString());
      }
    });
  }

  // console.log(serial_data);
};

let OnNewPort = function (context, ports_obj) {
  if (ports_obj.length == 0)
    return;

  disabled_model_btn = $("header").find("a.modal-trigger.disabled")
  if (disabled_model_btn.length > 0) {
    disabled_model_btn.removeClass("disabled")
  }

  selector_id = $(context.port_selector.el);
  selector_id.find("option").not(":disabled").remove();
  ports_obj.forEach((port, index) => {
    $("<option \>", { value: port.name, text: port.name }).appendTo(selector_id);
  });
  context.port_selector.destroy();
  M.FormSelect.init(selector_id, { classes: "port_selector_wrapper" });
  context.port_selector = M.FormSelect.getInstance(selector_id);
  context.ports_list = ports_obj

  OnNewPortToast();
};

let get_value_fields = function () {
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
    context.socket_io.emit("new_cmd", { cmd: SYSTEM_CMD.START_TEST });
    if (context.main_chart.data.labels.length > 10) {
      context.session.push(structuredClone(context.main_chart.data));
    }
    context.main_chart.data = structuredClone(chart_default_data);
    context.main_chart.update();
  }
};

let OnStopTest = function (event) {
  let context = event.data.context;
  if (context.socket_io.active) {
    console.log("stop test");
    event.data.context.socket_io.emit("new_cmd", { cmd: SYSTEM_CMD.STOP_TEST });
  }
};

let OnSetupEsc = function (event) {
  let context = event.data.context;
  if (context.socket_io.active && context.hw_status == HW_IDLE) {
    console.log("start calib");
    event.data.context.socket_io.emit("new_cmd", { cmd: SYSTEM_CMD.SETUP_ESC });
  }
};

let OnUpdateConfig = function (event) {
  let context = event.data.context;
  console.log(context.configuration);
  if (context.socket_io.active) {
    let data = { src: VIEW_DATA_SRC.UPDATE_CONF, data: context.configuration };
    context.socket_io.emit("submit", data);
  }
};

let OnSetMaxThrottle = function (event) {
  let context = event.data.context;
  let cfg = context.configuration;
  cfg.max_throttle = $(this).val();
  const ti = Math.trunc(100.0 / (cfg.max_pwm - cfg.min_pwm) * cfg.max_throttle);
  context.conf_fields.throttle_info.text(ti.toString());
  $(context).trigger("update_configuration");
};

let OnNewConf = function (context, conf) {
  let cfg = context.configuration;
  cfg.max_throttle = conf.max_throttle;
  cfg.max_pwm = conf.max_pwm;
  cfg.min_pwm = conf.min_pwm;

  context.conf_fields.max_throttle.val(cfg.max_throttle);
  const ti = Math.trunc(100.0 / (cfg.max_pwm - cfg.min_pwm) * cfg.max_throttle);
  context.conf_fields.throttle_info.text(ti.toString());
  OnNewCfgToast();
};

let create_session_obj = function () {
  return { time: Date(), is_notified: false };
};

let get_conf_fields = function () {
  let panel = $("div.action_panel").find("div#conf-panel");
  if (panel.length == 0) {
    return {};
  }

  let max_pwm = $(panel).find("#conf_max_pwm");
  let min_pwm = $(panel).find("#conf_min_pwm");
  let max_throttle = $(panel).find("#conf_max_throttle");
  let throttle_info = $(panel).find("#max_throttle_info")

  return { max_pwm: max_pwm, min_pwm: min_pwm, max_throttle: max_throttle, throttle_info: throttle_info };
};

C.AutoInit = function () {
  this.ports_list = []
  this.data_list = []
  this.session = []
  this.configuration = { max_throttle: 950, max_pwm: 2000, min_pwm: 1000 }
  this.port_selector = M.FormSelect.getInstance($("select#port_selector"));
  this.port_modal = M.Modal.getInstance($(".modal#select_port_modal"));
  this.main_chart = get_mian_chart();
  this.value_fields = get_value_fields();
  this.conf_fields = get_conf_fields();
  this.start_test_btn = $(".action_panel").find("a#start_test");
  this.stop_test_btn = $(".action_panel").find("a#stop_test");
  this.start_calibration_btn = $("a#start_calibration");
  this.hw_status = HW_INIT;
  this.session_obj = create_session_obj();

  if (this.port_modal.$el.has("a#action_end").length > 0) {
    this.port_modal.$el.find("a#action_end").on("click", function () {
      if (C.socket_io.connected) {
        selector_options = $(C.port_modal.el).find(".port_selector_wrapper > * > .selected").not(".disabled");
        if (selector_options.length > 0) {
          let data = {
            src: VIEW_DATA_SRC.SELECT_DEVICE,
            data: {
              name: $(selector_options).first().text().toString(),
            }
          };
          C.socket_io.emit("submit", data, (response) => {
            console.log(response)
            console.log("select dev response");
          });
        }
      } else {
        console.log("Not connected");
      }
    })
  }

  this.socket_io.on("connect", OnConnectToast);
  this.socket_io.on("disconnect", OnDisconnectToast);
  this.socket_io.on("new_devices", (ports_list) => {
    OnNewPort(this, ports_list);
  });

  this.socket_io.on("new_configuration", (conf) => {
    OnNewConf(this, conf);
  });

  this.socket_io.on("new_measurements", (measurements) => {
    OnNewMeasurements(this, measurements);
  });

  $(this).on("update_configuration", { context: this }, OnUpdateConfig);

  if (this.start_test_btn != undefined) {
    this.start_test_btn.click({ context: this }, OnStartTest);
  }

  if (this.stop_test_btn != undefined) {
    this.stop_test_btn.click({ context: this }, OnStopTest);
  }

  if (this.start_calibration_btn != undefined) {
    this.start_calibration_btn.click({ context: this }, OnSetupEsc);
  }

  if (this.conf_fields.max_throttle != undefined) {
    this.conf_fields.max_throttle.mouseup({ context: this }, OnSetMaxThrottle);
  }

};

C.AutoInit();