"""Regression checks for unavailable models, offline demo and data isolation."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import time
import pytest
import pandas as pd
from fastapi.testclient import TestClient
import main
from ml.features import encode_features, FEATURE_COLUMNS, FEATURE_SCHEMA, training_frame
from ml.naive_bayes import SpecialtyClassifier
from ml.pipeline import MedicalPipeline
from ml.train import prepare_dataset, split_dataset
from schemas.medical import BAYES_FEATURE_KEYS

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(main.config, 'DEMO_MODE', True)
    main.sessions.clear()
    main.reports.clear()
    main._ml_pipeline = None
    # Current Starlette TestClient uses a named client address; provide an explicit loopback scope.
    async def loopback_app(scope, receive, send):
        scope['client'] = ('127.0.0.1', 12345)
        await main.app(scope, receive, send)
    with TestClient(loopback_app, base_url='http://127.0.0.1:8000') as c:
        yield c
    main.sessions.clear()
    main.reports.clear()


def test_unknown_is_not_confirmed_absence():
    unknown = encode_features({'cough': 'unknown'})
    absent = encode_features({'cough': 'absent'})
    assert unknown['cough'] == absent['cough'] == 0
    assert unknown['cough__observed'] == 0
    assert absent['cough__observed'] == 1
    assert encode_features({'cough': 'present'})['cough'] == 1
    with pytest.raises(ValueError): encode_features({'cough': 'maybe'})


def test_untrained_router_refuses_prediction():
    with pytest.raises(RuntimeError): SpecialtyClassifier().predict_specialty({'cough': 'present'})


def test_missing_artifacts_are_explicit(monkeypatch, tmp_path):
    import ml.pipeline as module
    monkeypatch.setattr(module, 'MODELS_DIR', tmp_path)
    pipeline = MedicalPipeline()
    result = pipeline.analyze({'itching': 'present', 'skin_rash': 'present'})
    assert not pipeline.availability()['ready']
    assert result['analysis_degraded']
    assert result['ml_hypotheses'] == []
    assert result['ml_suppressed_reason']
    assert result['assigned_specialty'] == 'sin_clasificar'


def test_legacy_artifact_rejected(tmp_path):
    import joblib
    artifact = tmp_path / 'old.joblib'
    joblib.dump({'model': None, 'classes': []}, artifact)
    with pytest.raises(ValueError, match='Incompatible'): SpecialtyClassifier().load(artifact)


def test_demo_never_calls_external_llm(client, monkeypatch):
    async def forbidden(*args, **kwargs): raise AssertionError('External LLM was called')
    monkeypatch.setattr(main.extract_agent, 'extract', forbidden)
    monkeypatch.setattr(main.report_agent, 'generate_report', forbidden)
    health = client.get('/api/health').json()
    assert health['demo_mode'] and not health['ml_pipeline_loaded']
    cases = client.get('/api/demo/cases').json()['cases']
    assert len(cases) == 3
    for case in cases:
        response = client.post('/api/demo/' + case['id'])
        assert response.status_code == 200
        report = response.json()
        assert report['demo'] and report['experimental']
        assert report['ml_hypotheses'] == []
        assert client.get('/api/reports/' + report['report_id']).status_code == 200
    assert client.post('/api/demo/not-a-case').status_code == 404


def test_expired_reports_removed(client, monkeypatch):
    report = client.post('/api/demo/insufficient').json()
    main.sessions[report['report_id']]['started_monotonic'] = time.monotonic() - 3601
    assert client.get('/api/reports/' + report['report_id']).status_code == 404
    assert client.get('/api/reports').json()['reports'] == []


def test_remote_and_untrusted_origins_refused(client):
    assert client.get('/api/reports', headers={'Origin': 'https://evil.example'}).status_code == 403
    assert client.get('/api/reports', headers={'Host': 'evil.example'}).status_code == 403
    assert client.get('/api/reports', headers={'Origin': 'http://127.0.0.1:8000'}).status_code == 200
    with TestClient(main.app) as remote:
        assert remote.get('/api/reports').status_code == 403


def test_training_splits_have_no_exact_pattern_overlap(tmp_path):
    rows = []
    for label in ['Allergy', 'Acne']:
        for i in range(10):
            row = {k: 0 for k in BAYES_FEATURE_KEYS}
            row[BAYES_FEATURE_KEYS[i]] = 1
            row[BAYES_FEATURE_KEYS[20 if label == 'Allergy' else 21]] = 1
            rows.append({**row, 'prognosis': label})
    path = tmp_path / 'fictional.csv'
    pd.DataFrame(rows + [rows[0]]).to_csv(path, index=False)
    df = prepare_dataset(path)
    assert len(df) == 20
    tr, te = split_dataset(df, 42)
    assert set(tr).isdisjoint(te)
    assert split_dataset(df, 42)[0].tolist() == tr.tolist()
    assert list(training_frame(df[BAYES_FEATURE_KEYS]).columns) == FEATURE_COLUMNS
    rows.append({**rows[0], 'prognosis': 'Acne'})
    pd.DataFrame(rows).to_csv(path, index=False)
    with pytest.raises(ValueError, match='conflicting'): prepare_dataset(path)
