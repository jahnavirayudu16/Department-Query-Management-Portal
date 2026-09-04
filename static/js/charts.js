// Central Admin Analytics Dashboard Visualizations with Chart.js

document.addEventListener('DOMContentLoaded', () => {
  const analyticsContainer = document.getElementById('analyticsDashboard');
  if (!analyticsContainer) return;

  fetch('/api/analytics-data')
    .then(res => res.json())
    .then(data => {
      initDepartmentPieChart(data.departments);
      initYearPieChart(data.years);
      populateMatrixTable(data.matrix);
      initCategoryChart(data.categories);
      initStatusChart(data.statuses);
      initPriorityChart(data.priorities);
      updateSummaryBadges(data);
    })
    .catch(err => console.error('Error loading analytics:', err));
});

/* 1. Department Problem Distribution Pie Chart */
function initDepartmentPieChart(data) {
  const ctx = document.getElementById('deptPieChart');
  if (!ctx || !data || !data.labels || !data.data) return;

  // Rich distinct palette for departments
  const colors = [
    '#4f46e5', '#0284c7', '#06b6d4', '#10b981', '#f59e0b',
    '#ec4899', '#8b5cf6', '#64748b', '#ef4444'
  ];

  new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: data.labels,
      datasets: [{
        data: data.data,
        backgroundColor: colors.slice(0, data.labels.length),
        borderWidth: 2,
        borderColor: '#ffffff',
        hoverOffset: 10
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            font: { family: 'Inter', size: 11, weight: 'bold' },
            padding: 12,
            boxWidth: 14
          }
        },
        tooltip: {
          callbacks: {
            label: function(context) {
              const label = context.label || '';
              const value = context.raw || 0;
              const total = context.dataset.data.reduce((a, b) => a + b, 0);
              const percentage = total > 0 ? Math.round((value / total) * 100) : 0;
              return ` ${label}: ${value} issues (${percentage}%)`;
            }
          }
        }
      }
    }
  });
}

/* 2. Student Year of Study Pie Chart */
function initYearPieChart(data) {
  const ctx = document.getElementById('yearPieChart');
  if (!ctx || !data || !data.labels || !data.data) return;

  const colors = ['#0284c7', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6'];

  new Chart(ctx, {
    type: 'pie',
    data: {
      labels: data.labels,
      datasets: [{
        data: data.data,
        backgroundColor: colors.slice(0, data.labels.length),
        borderWidth: 2,
        borderColor: '#ffffff',
        hoverOffset: 10
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            font: { family: 'Inter', size: 11, weight: 'bold' },
            padding: 12,
            boxWidth: 14
          }
        },
        tooltip: {
          callbacks: {
            label: function(context) {
              const label = context.label || '';
              const value = context.raw || 0;
              const total = context.dataset.data.reduce((a, b) => a + b, 0);
              const percentage = total > 0 ? Math.round((value / total) * 100) : 0;
              return ` ${label}: ${value} issues (${percentage}%)`;
            }
          }
        }
      }
    }
  });
}

/* 3. Department × Year Cross-Matrix Breakdown Table */
function populateMatrixTable(matrixData) {
  const tbody = document.getElementById('matrixTableBody');
  if (!tbody || !matrixData || !matrixData.length) return;

  tbody.innerHTML = '';

  matrixData.forEach(row => {
    const tr = document.createElement('tr');
    tr.style.borderBottom = '1px solid #f1f5f9';
    tr.innerHTML = `
      <td style="padding: 0.75rem 1rem; font-weight: 700; color: #0f172a;">
        🏢 ${row.dept_name}
      </td>
      <td style="padding: 0.75rem 1rem; text-align: center; color: #475569;">
        ${row.yr1 > 0 ? `<strong>${row.yr1}</strong>` : '<span style="color: #cbd5e1;">-</span>'}
      </td>
      <td style="padding: 0.75rem 1rem; text-align: center; color: #475569;">
        ${row.yr2 > 0 ? `<strong>${row.yr2}</strong>` : '<span style="color: #cbd5e1;">-</span>'}
      </td>
      <td style="padding: 0.75rem 1rem; text-align: center; color: #475569;">
        ${row.yr3 > 0 ? `<strong>${row.yr3}</strong>` : '<span style="color: #cbd5e1;">-</span>'}
      </td>
      <td style="padding: 0.75rem 1rem; text-align: center; color: #475569;">
        ${row.yr4 > 0 ? `<strong>${row.yr4}</strong>` : '<span style="color: #cbd5e1;">-</span>'}
      </td>
      <td style="padding: 0.75rem 1rem; text-align: center; color: #475569;">
        ${row.faculty_count > 0 ? `<strong>${row.faculty_count}</strong>` : '<span style="color: #cbd5e1;">-</span>'}
      </td>
      <td style="padding: 0.75rem 1rem; text-align: center; font-weight: 800; color: #4f46e5;">
        <span class="badge badge-primary" style="font-size: 0.82rem; padding: 3px 8px;">${row.total_count}</span>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

/* 4. Category Doughnut Chart */
function initCategoryChart(data) {
  const ctx = document.getElementById('catChart');
  if (!ctx || !data || !data.labels) return;

  new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: data.labels,
      datasets: [{
        data: data.data,
        backgroundColor: ['#4f46e5', '#0284c7', '#f59e0b'],
        borderWidth: 2,
        borderColor: '#ffffff'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'bottom', labels: { font: { family: 'Inter', size: 10 } } }
      }
    }
  });
}

/* 5. Status Chart */
function initStatusChart(data) {
  const ctx = document.getElementById('statusChart');
  if (!ctx || !data || !data.labels) return;

  new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: data.labels,
      datasets: [{
        data: data.data,
        backgroundColor: ['#3b82f6', '#8b5cf6', '#f59e0b', '#06b6d4', '#10b981'],
        borderWidth: 2,
        borderColor: '#ffffff'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'bottom', labels: { font: { family: 'Inter', size: 10 } } }
      }
    }
  });
}

/* 6. Priority Chart */
function initPriorityChart(data) {
  const ctx = document.getElementById('priorityChart');
  if (!ctx || !data || !data.labels) return;

  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: data.labels,
      datasets: [{
        label: 'Issues',
        data: data.data,
        backgroundColor: ['#94a3b8', '#f59e0b', '#ea580c', '#dc2626'],
        borderRadius: 6
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

/* Top Highlights & Badges Calculation */
function updateSummaryBadges(data) {
  const topDeptBadge = document.getElementById('topDeptBadge');
  const topYearBadge = document.getElementById('topYearBadge');
  const totalBadge = document.getElementById('totalQueriesBadge');

  if (topDeptBadge && data.departments && data.departments.labels.length) {
    topDeptBadge.textContent = `🔥 ${data.departments.labels[0]} (${data.departments.data[0]} issues)`;
  }

  if (topYearBadge && data.years && data.years.labels.length) {
    topYearBadge.textContent = `⚠️ ${data.years.labels[0]} (${data.years.data[0]} issues)`;
  }

  if (totalBadge && data.statuses && data.statuses.data.length) {
    const total = data.statuses.data.reduce((a, b) => a + b, 0);
    totalBadge.textContent = `${total} Active & Resolved Queries`;
  }
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
