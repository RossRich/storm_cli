const ctx = document.getElementById('myChart');

    // labels = Utils.labels({ min: 0, max: 10 })

    chart_data = {
      labels: [0],
      datasets: [{
        label: '# of Votes',
        data: [],
        borderWidth: 1
      }]
    }
    chart = new Chart(ctx, {
      type: 'line',
      data: chart_data,
      options: {
        scales: {
          y: {
            beginAtZero: true
          }
        }
      }
    });

    chart.data.datasets[0].data.push(30)
    chart.update()