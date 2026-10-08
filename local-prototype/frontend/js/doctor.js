/* Local fictional-report viewer. All dynamic content is rendered as text. */
const reportList = document.getElementById('reportList');
const emptyState = document.getElementById('emptyState');
const reportContent = document.getElementById('reportContent');
const refreshBtn = document.getElementById('refreshBtn');
function textNode(tag, text, className = '') {
    const node = document.createElement(tag);
    node.textContent = String(text ?? '');
    node.className = className;
    return node;
}
function setText(id, text) { document.getElementById(id).textContent = String(text ?? 'No disponible'); }
async function fetchReports() {
    try {
        const response = await fetch('/api/reports');
        if (!response.ok) throw new Error();
        const data = await response.json();
        reportList.replaceChildren();
        for (const report of data.reports) {
            const card = textNode('button', `${report.main_symptom} — ${formatDate(report.generated_at)}`, 'report-card');
            card.type = 'button';
            card.addEventListener('click', () => loadReportDetails(report.report_id));
            reportList.appendChild(card);
        }
        if (!data.reports.length) reportList.appendChild(textNode('p', 'No hay casos guardados. Genera un caso ficticio en la demo.'));
    } catch (_) { reportList.replaceChildren(textNode('p', 'No se pudieron cargar los informes.')); }
}
async function loadReportDetails(id) {
    try {
        const response = await fetch(`/api/reports/${encodeURIComponent(id)}`);
        if (!response.ok) throw new Error();
        renderReportDetails(await response.json());
    } catch (_) { reportList.appendChild(textNode('p', 'El caso no existe o ha caducado.')); }
}
function renderReportDetails(report) {
    emptyState.style.display = 'none';
    reportContent.classList.add('active');
    setText('reportIdDisplay', report.report_id);
    setText('reportDateDisplay', formatDate(report.generated_at));
    setText('patAge', report.patient_intake?.age || 'No especificada');
    setText('patSex', report.patient_intake?.sex || 'No especificado');
    setText('patSymptom', report.patient_intake?.main_symptom);
    setText('specName', report.assigned_specialty || 'Sin clasificar');
    setText('specConf', report.demo ? 'Demo sin ML' : (report.analysis_degraded ? 'Modelo no disponible / degradado' : 'Modelo experimental; sin validación clínica'));
    setText('narrativeReport', report.clinical_summary);
    document.getElementById('narrativeReport').style.whiteSpace = 'pre-wrap';
    // Retain existing score elements when present; score is an experimental rule output.
    const score = document.getElementById('urgencyScore');
    if (score) score.textContent = String(report.urgency_score ?? 0);
    const level = document.getElementById('urgencyLabel');
    if (level) level.textContent = `Puntuación experimental: ${report.urgency_score ?? 0}/100 · ${report.urgency_level || report.urgency_label || 'No disponible'}`;
    const bar = document.getElementById('urgencyBar');
    if (bar) bar.style.width = `${Math.min(100, Math.max(0, Number(report.urgency_score) || 0))}%`;
    const alarms = report.alarm_signals || [];
    const alarmList = document.getElementById('alarmList');
    alarmList.replaceChildren(...alarms.map(a => textNode('li', a.signal)));
    document.getElementById('alarmSignalsContainer').style.display = alarms.length ? 'block' : 'none';
    const grid = document.getElementById('hypothesesGrid');
    grid.replaceChildren(textNode('p', 'Resultados experimentales. Las reglas no están clínicamente validadas.'));
    if (report.insufficient_data) grid.appendChild(textNode('p', 'Información insuficiente para clasificar.'));
    if (report.ml_suppressed_reason) grid.appendChild(textNode('p', report.ml_suppressed_reason));
    for (const alert of report.clinical_alerts || []) {
        const card = textNode('div', '', 'report-card');
        card.append(textNode('strong', alert.disease_name), textNode('p', 'Regla experimental: ' + alert.severity));
        for (const evidence of alert.rule_evidence || []) card.appendChild(textNode('p', typeof evidence === 'string' ? evidence : evidence.label || evidence.key));
        grid.appendChild(card);
    }
    for (const hypothesis of report.ml_hypotheses || []) {
        const card = textNode('div', '', 'report-card');
        card.append(textNode('strong', hypothesis.disease_name), textNode('p', `Salida del modelo: ${(Number(hypothesis.probability) * 100).toFixed(1)}%. No es una probabilidad clínica validada.`));
        card.appendChild(textNode('p', 'SHAP explica un estimador base, no la probabilidad calibrada final.'));
        for (const [feature, value] of Object.entries(hypothesis.shap_explanation || {})) card.appendChild(textNode('p', `${feature}: ${Number(value).toFixed(4)}`));
        grid.appendChild(card);
    }
    const features = document.getElementById('featureGrid');
    features.replaceChildren();
    for (const [key, state] of Object.entries(report.bayes_features || {})) {
        if (state !== 'unknown') features.appendChild(textNode('span', `${key}: ${state === 'present' ? 'confirmado' : 'negado'}`, 'feature-tag'));
    }
    if (!features.children.length) features.appendChild(textNode('p', 'Síntomas no preguntados / desconocidos.'));
}
refreshBtn.addEventListener('click', fetchReports);
window.addEventListener('DOMContentLoaded', async () => {
    await fetchReports();
    if (window.location.hash) await loadReportDetails(window.location.hash.slice(1));
});
