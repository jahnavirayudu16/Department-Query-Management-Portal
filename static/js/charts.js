// Analytics Dashboard Visualizations with Chart.js

document.addEventListener('DOMContentLoaded', () => {
  const analyticsContainer = document.getElementById('analyticsDashboard');
  if (!analyticsContainer) return;

  fetch('/api/analytics-data')
    .then(res => res.json())
    .then(data => {
      initCategoryPieChart(data.categories);
      initDepartmentChart(data.departments);
      initStatusChart(data.statuses);
      initPriorityChart(data.priorities);
    })
    .catch(err => console.error('Error loading analytics:', err));
});

// Category Distribution Pie Chart - "Ye category lo ekkuva problems unnayi"
function initCategoryPieChart(data) {
  const ctx = document.getElementById('catChart');
  if (!ctx) return;

  // Determine top problematic category
  let maxCount = -1;
  let topCategory = 'None';
  if (data && data.labels && data.data) {
    data.data.forEach((val, idx) => {
      if (val > maxCount) {
        maxCount = val;
        topCategory = data.labels[idx];
      }
    });
    
    const topBadge = document.getElementById('topProblemCategoryBadge');
    if (topBadge) {
      topBadge.textContent = `🔥 Most Reported: ${topCategory} (${maxCount} issues)`;
    }
  }

  new Chart(ctx, {
    type: 'pie',
    data: {
      labels: data.labels,
      datasets: [{
        data: data.data,
        backgroundColor: ['#4f46e5', '#0284c7', '#f59e0b', '#10b981', '#ec4899'],
        borderWidth: 2,
        borderColor: '#ffffff',
        hoverOffset: 8
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            font: { family: 'Inter', size: 12, weight: 'bold' },
            padding: 16
          }
        },
        tooltip: {
          callbacks: {
            label: function(context) {
              const label = context.label || '';
              const value = context.raw || 0;
              const total = context.dataset.data.reduce((a, b) => a + b, 0);
              const percentage = total > 0 ? Math.round((value / total) * 100) : 0;
              return ` ${label}: ${value} problems (${percentage}%)`;
            }
          }
        }
      }
    }
  });
}

function initDepartmentChart(data) {
  const ctx = document.getElementById('deptChart');
  if (!ctx) return;
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: data.labels,
      datasets: [{
        label: 'Total Queries',
        data: data.data,
        backgroundColor: '#4f46e5',
        borderRadius: 8
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, ticks: { precision: 0, font: { family: 'Inter' } }, grid: { color: '#f1f5f9' } },
        x: { grid: { display: false }, ticks: { font: { family: 'Inter', weight: 'bold' } } }
      }
    }
  });
}

function initStatusChart(data) {
  const ctx = document.getElementById('statusChart');
  if (!ctx) return;
  new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: data.labels,
      datasets: [{
        data: data.data,
        backgroundColor: ['#3b82f6', '#8b5cf6', '#f59e0b', '#06b6d4', '#10b981', '#ef4444'],
        borderWidth: 2,
        borderColor: '#ffffff'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'bottom', labels: { font: { family: 'Inter', size: 11 } } }
      }
    }
  });
}

function initPriorityChart(data) {
  const ctx = document.getElementById('priorityChart');
  if (!ctx) return;
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: data.labels,
      datasets: [{
        label: 'Queries by Priority',
        data: data.data,
        backgroundColor: ['#94a3b8', '#f59e0b', '#ea580c', '#dc2626'],
        borderRadius: 8
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, ticks: { precision: 0 } },
        x: { grid: { display: false } }
      }
    }
  });
}

function initResponseTimesChart(data) {
  const ctx = document.getElementById('respTimeChart');
  if (!ctx) return;
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: data.labels,
      datasets: [{
        label: 'Target SLA (Mins)',
        data: data.data,
        backgroundColor: '#0ea5e9',
        borderRadius: 8
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      indexAxis: 'y',
      plugins: { legend: { display: false } },
      scales: { x: { beginAtZero: true } }
    }
  });
}

function initRatingsChart(data) {
  const ctx = document.getElementById('ratingsChart');
  if (!ctx) return;
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: data.labels,
      datasets: [{
        label: 'User Ratings',
        data: data.data,
        backgroundColor: '#fbbf24',
        borderRadius: 8
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true, ticks: { precision: 0 } } }
    }
  });
}
