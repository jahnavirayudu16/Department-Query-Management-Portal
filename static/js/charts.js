// Executive 3-Pillar Analytics & Pie Chart Insights with Chart.js

document.addEventListener('DOMContentLoaded', () => {
  const analyticsContainer = document.getElementById('analyticsDashboard');
  if (!analyticsContainer) return;

  fetch('/api/analytics-data')
    .then(res => res.json())
    .then(data => {
      // 1. Principal Desk Analysis
      if (data.principal_analysis) {
        initPrincipalPillar(data.principal_analysis);
      }
      
      // 2. AO Administrative Analysis
      if (data.ao_analysis) {
        initAoPillar(data.ao_analysis);
      }

      // 3. Department HODs Analysis
      if (data.hod_analysis) {
        initHodPillar(data.hod_analysis);
      }

      // 4. Overall Campus Overview
      initCampusOverview(data);
    })
    .catch(err => console.error('Error loading analytics data:', err));
});

/* Tab Switching Function */
function switchAnalyticsTab(tabId, btn) {
  document.querySelectorAll('.tab-pane').forEach(pane => {
    pane.classList.remove('active');
  });
  document.querySelectorAll('.analytics-tab-btn').forEach(b => {
    b.classList.remove('active');
  });

  const targetPane = document.getElementById(tabId);
  if (targetPane) {
    targetPane.classList.add('active');
  }
  if (btn) {
    btn.classList.add('active');
  }
}

/* -------------------------------------------------------------
   1. PRINCIPAL DESK PILLAR
------------------------------------------------------------- */
function initPrincipalPillar(pData) {
  const sum = pData.summary || {};
  
  // Executive Header Cards
  setText('cardPrincipalTotal', sum.total ?? 0);
  setText('cardPrincipalSolved', `${sum.solved_percent ?? 0}%`);
  setText('cardPrincipalPending', sum.pending ?? 0);

  // Tab KPI Tiles
  setText('pSummaryTotal', sum.total ?? 0);
  setText('pSummarySolved', sum.solved ?? 0);
  setText('pSummarySolvedRate', `${sum.solved_percent ?? 0}% Resolution Rate`);
  setText('pSummaryPending', sum.pending ?? 0);
  setText('pSummaryUrgent', sum.urgent ?? 0);

  // Topics Chart (Wi-Fi, Food, Cleanliness, Maintenance)
  const topicCtx = document.getElementById('pTopicChart');
  if (topicCtx && pData.topics && pData.topics.labels.length) {
    const topicColors = ['#4f46e5', '#0284c7', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6', '#64748b'];
    new Chart(topicCtx, {
      type: 'doughnut',
      data: {
        labels: pData.topics.labels,
        datasets: [{
          data: pData.topics.data,
          backgroundColor: topicColors.slice(0, pData.topics.labels.length),
          borderWidth: 2,
          borderColor: '#ffffff',
          hoverOffset: 8
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'bottom', labels: { font: { family: 'Inter', size: 11, weight: 'bold' }, padding: 10 } }
        }
      }
    });
  }

  // Status Chart
  const stCtx = document.getElementById('pStatusChart');
  if (stCtx && pData.statuses && pData.statuses.labels.length) {
    new Chart(stCtx, {
      type: 'doughnut',
      data: {
        labels: pData.statuses.labels,
        datasets: [{
          data: pData.statuses.data,
          backgroundColor: ['#10b981', '#3b82f6', '#f59e0b', '#ec4899'],
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

  // Priority Chart
  const prCtx = document.getElementById('pPriorityChart');
  if (prCtx && pData.priorities && pData.priorities.labels.length) {
    const colorMap = { 'Critical': '#dc2626', 'High': '#ea580c', 'Medium': '#f59e0b', 'Low': '#64748b' };
    new Chart(prCtx, {
      type: 'bar',
      data: {
        labels: pData.priorities.labels,
        datasets: [{
          data: pData.priorities.data,
          backgroundColor: pData.priorities.labels.map(l => colorMap[l] || '#4f46e5'),
          borderRadius: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true, ticks: { precision: 0 } }, x: { grid: { display: false } } }
      }
    });
  }
}

/* -------------------------------------------------------------
   2. AO ADMINISTRATIVE PILLAR
------------------------------------------------------------- */
function initAoPillar(aoData) {
  const sum = aoData.summary || {};

  // Executive Header Cards
  setText('cardAoTotal', sum.total ?? 0);
  setText('cardAoSolved', `${sum.solved_percent ?? 0}%`);
  setText('cardAoPending', sum.pending ?? 0);

  // Tab KPI Tiles
  setText('aoSummaryTotal', sum.total ?? 0);
  setText('aoSummarySolved', sum.solved ?? 0);
  setText('aoSummarySolvedRate', `${sum.solved_percent ?? 0}% Resolution Rate`);
  setText('aoSummaryPending', sum.pending ?? 0);
  setText('aoSummaryUrgent', sum.urgent ?? 0);

  // Administrative Topics Chart
  const topicCtx = document.getElementById('aoTopicChart');
  if (topicCtx && aoData.topics && aoData.topics.labels.length) {
    const aoColors = ['#0284c7', '#06b6d4', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6'];
    new Chart(topicCtx, {
      type: 'doughnut',
      data: {
        labels: aoData.topics.labels,
        datasets: [{
          data: aoData.topics.data,
          backgroundColor: aoColors.slice(0, aoData.topics.labels.length),
          borderWidth: 2,
          borderColor: '#ffffff',
          hoverOffset: 8
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'bottom', labels: { font: { family: 'Inter', size: 11, weight: 'bold' }, padding: 10 } }
        }
      }
    });
  }

  // AO Status Chart
  const stCtx = document.getElementById('aoStatusChart');
  if (stCtx && aoData.statuses && aoData.statuses.labels.length) {
    new Chart(stCtx, {
      type: 'doughnut',
      data: {
        labels: aoData.statuses.labels,
        datasets: [{
          data: aoData.statuses.data,
          backgroundColor: ['#10b981', '#0284c7', '#f59e0b', '#ec4899'],
          borderWidth: 2,
          borderColor: '#ffffff'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: 'bottom', labels: { font: { family: 'Inter', size: 10 } } } }
      }
    });
  }

  // AO Student Year Chart
  const yrCtx = document.getElementById('aoYearChart');
  if (yrCtx && aoData.years && aoData.years.labels.length) {
    new Chart(yrCtx, {
      type: 'pie',
      data: {
        labels: aoData.years.labels,
        datasets: [{
          data: aoData.years.data,
          backgroundColor: ['#0284c7', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6'],
          borderWidth: 2,
          borderColor: '#ffffff'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: 'bottom', labels: { font: { family: 'Inter', size: 10 } } } }
      }
    });
  }
}

/* -------------------------------------------------------------
   3. HODs ACADEMIC PILLAR
------------------------------------------------------------- */
function initHodPillar(hodData) {
  const sum = hodData.summary || {};

  // Executive Header Cards
  setText('cardHodTotal', sum.total ?? 0);
  setText('cardHodSolved', `${sum.solved_percent ?? 0}%`);
  setText('cardHodUnassigned', sum.unassigned ?? 0);

  // Tab KPI Tiles
  setText('hodSummaryTotal', sum.total ?? 0);
  setText('hodSummarySolved', sum.solved ?? 0);
  setText('hodSummarySolvedRate', `${sum.solved_percent ?? 0}% Resolution Rate`);
  setText('hodSummaryPending', sum.pending ?? 0);
  setText('hodSummaryUnassigned', sum.unassigned ?? 0);

  // Academic Degree Distribution Chart (B.Tech vs M.Tech vs MCA vs MBA)
  const degCtx = document.getElementById('hodDegreeChart');
  if (degCtx && hodData.degrees && hodData.degrees.labels.length) {
    const degColors = ['#10b981', '#059669', '#047857', '#065f46', '#34d399'];
    new Chart(degCtx, {
      type: 'doughnut',
      data: {
        labels: hodData.degrees.labels,
        datasets: [{
          data: hodData.degrees.data,
          backgroundColor: degColors.slice(0, hodData.degrees.labels.length),
          borderWidth: 2,
          borderColor: '#ffffff',
          hoverOffset: 8
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'bottom', labels: { font: { family: 'Inter', size: 11, weight: 'bold' }, padding: 10 } }
        }
      }
    });
  }

  // Academic Topics Chart (Exams, Marks, Attendance, Labs, Projects)
  const topicCtx = document.getElementById('hodTopicChart');
  if (topicCtx && hodData.topics && hodData.topics.labels.length) {
    new Chart(topicCtx, {
      type: 'bar',
      data: {
        labels: hodData.topics.labels,
        datasets: [{
          data: hodData.topics.data,
          backgroundColor: '#8b5cf6',
          borderRadius: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true, ticks: { precision: 0 } }, x: { grid: { display: false } } }
      }
    });
  }

  // HOD Performance Scorecard Table
  populateHodPerformanceTable(hodData.hod_table);
}

function populateHodPerformanceTable(hodList) {
  const tbody = document.getElementById('hodPerformanceTableBody');
  if (!tbody) return;
  if (!hodList || !hodList.length) {
    tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 1.5rem; color: #64748b;">No active HOD accounts found.</td></tr>';
    return;
  }

  tbody.innerHTML = '';
  hodList.forEach(h => {
    const tr = document.createElement('tr');
    tr.style.borderBottom = '1px solid #f1f5f9';
    tr.innerHTML = `
      <td style="padding: 0.85rem 1rem; font-weight: 700; color: #0f172a;">
        🎓 ${h.course} &bull; ${h.department}
        <div style="font-size: 0.72rem; color: #64748b; font-weight: 500;">Level: ${h.level}</div>
      </td>
      <td style="padding: 0.85rem 1rem;">
        <strong>${h.name}</strong>
        <div style="font-size: 0.72rem; color: #64748b;">${h.email}</div>
      </td>
      <td style="padding: 0.85rem 1rem; text-align: center; font-weight: 700; color: #1e1b4b;">
        ${h.total}
      </td>
      <td style="padding: 0.85rem 1rem; text-align: center; font-weight: 700; color: #059669;">
        ${h.solved}
      </td>
      <td style="padding: 0.85rem 1rem; text-align: center;">
        <span class="badge" style="background: ${h.solved_percent >= 75 ? '#dcfce7; color: #15803d;' : (h.solved_percent >= 40 ? '#fef3c7; color: #b45309;' : '#fee2e2; color: #b91c1c;')} font-weight: 800; font-size: 0.78rem;">
          ${h.solved_percent}%
        </span>
      </td>
      <td style="padding: 0.85rem 1rem; text-align: center; color: #b45309; font-weight: 600;">
        ${h.pending}
      </td>
      <td style="padding: 0.85rem 1rem; text-align: center;">
        ${h.unassigned > 0 ? `<span class="badge" style="background: #fce7f3; color: #be185d; font-weight: 800;">${h.unassigned}</span>` : '<span style="color: #94a3b8;">0</span>'}
      </td>
    `;
    tbody.appendChild(tr);
  });
}

/* -------------------------------------------------------------
   4. TOTAL CAMPUS OVERVIEW
------------------------------------------------------------- */
function initCampusOverview(data) {
  // KPI Summary Cards
  setText('summaryTotal', data.summary?.total ?? 0);
  setText('summarySolved', data.summary?.solved ?? 0);
  setText('summarySolvedPercent', `${data.summary?.solved_percent ?? 0}% Resolution Rate`);
  setText('summaryPending', data.summary?.pending ?? 0);
  setText('summaryUnassigned', data.summary?.unassigned ?? 0);

  // Department Problem Distribution Pie Chart
  const deptCtx = document.getElementById('deptPieChart');
  if (deptCtx && data.departments && data.departments.labels.length) {
    const colors = ['#4f46e5', '#0284c7', '#06b6d4', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6', '#64748b', '#ef4444'];
    new Chart(deptCtx, {
      type: 'doughnut',
      data: {
        labels: data.departments.labels,
        datasets: [{
          data: data.departments.data,
          backgroundColor: colors.slice(0, data.departments.labels.length),
          borderWidth: 2,
          borderColor: '#ffffff',
          hoverOffset: 10
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'bottom', labels: { font: { family: 'Inter', size: 11, weight: 'bold' }, padding: 12 } }
        }
      }
    });
  }

  // Student Year of Study Pie Chart
  const yrCtx = document.getElementById('yearPieChart');
  if (yrCtx && data.years && data.years.labels.length) {
    new Chart(yrCtx, {
      type: 'pie',
      data: {
        labels: data.years.labels,
        datasets: [{
          data: data.years.data,
          backgroundColor: ['#0284c7', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6'],
          borderWidth: 2,
          borderColor: '#ffffff',
          hoverOffset: 10
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'bottom', labels: { font: { family: 'Inter', size: 11, weight: 'bold' }, padding: 12 } }
        }
      }
    });
  }

  // Department × Year Cross-Matrix Breakdown Table
  populateMatrixTable(data.matrix);
}

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

function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}
