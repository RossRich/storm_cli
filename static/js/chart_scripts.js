const ctx = document.getElementById('myChart');

chart_data = {
  datasets: [{
    data: [{x: 10, y: 20}, {x: 15, y: 2}, {x: 20, y: 10}],
  }]
}

chart = new Chart(ctx, {
  type: 'line',
  data: chart_data,
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