import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {JSDOM} from 'jsdom';
const fixture = '<img src=x onerror="window.compromised=true"><script>window.compromised=true</script>';
test('report fields and generated text cannot inject executable HTML', () => {
    const html = fs.readFileSync('local-prototype/frontend/doctor.html', 'utf8');
    const dom = new JSDOM(html, {runScripts: 'outside-only', url: 'http://127.0.0.1:8000/doctor'});
    dom.window.fetch = async () => ({ok:true, json:async()=>({reports:[]})});
    dom.window.eval(fs.readFileSync('local-prototype/frontend/js/utils.js', 'utf8'));
    dom.window.eval(fs.readFileSync('local-prototype/frontend/js/doctor.js', 'utf8'));
    dom.window.renderReportDetails({report_id:fixture, clinical_summary:fixture, patient_intake:{main_symptom:fixture},
        clinical_alerts:[{disease_name:fixture, severity:fixture, rule_evidence:[{label:fixture}]}],
        ml_hypotheses:[{disease_name:fixture, probability:0.7, shap_explanation:{[fixture]:1}}],
        alarm_signals:[{signal:fixture}], bayes_features:{[fixture]:'present'}});
    assert.equal(dom.window.document.querySelector('#narrativeReport').textContent, fixture);
    assert.equal(dom.window.document.querySelectorAll('#reportContent img, #reportContent script').length, 0);
    assert.equal(dom.window.compromised, undefined);
});
test('chat renders hostile input and streamed model output as text', () => {
    const dom = new JSDOM(fs.readFileSync('local-prototype/frontend/index.html','utf8'), {runScripts:'outside-only',url:'http://127.0.0.1:8000'});
    dom.window.fetch = async () => ({json:async()=>({demo_mode:true,cases:[]})});
    dom.window.eval(fs.readFileSync('local-prototype/frontend/js/utils.js','utf8'));
    dom.window.eval(fs.readFileSync('local-prototype/frontend/js/chat.js','utf8'));
    dom.window.addMessage(fixture,'user');
    dom.window.handleServerMessage({type:'token',content:fixture});
    dom.window.handleServerMessage({type:'stream_end'});
    assert.equal(dom.window.document.querySelectorAll('#messagesArea img, #messagesArea script').length,0);
    assert.ok(dom.window.document.querySelector('#messagesArea').textContent.includes(fixture));
});
