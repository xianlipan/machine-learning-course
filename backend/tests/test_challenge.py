import math
import sqlite3
import pytest
from fastapi.testclient import TestClient
from backend.app import create_app
from backend.evaluator import evaluate, MAX_BYTES


LABELS = {'TEST_1': 100., 'TEST_2': 200., 'TEST_3': 300.}


def test_alignment_rmse_and_bom():
    content = b'\xef\xbb\xbfsample_id,prediction\r\nTEST_3,303\r\nTEST_1,104\r\nTEST_2,200\r\n'
    assert evaluate(content, LABELS) == pytest.approx(math.sqrt(25 / 3))
    assert evaluate(b'prediction,sample_id\n300,TEST_3\n100,TEST_1\n200,TEST_2\n', LABELS) == 0


@pytest.mark.parametrize('content,message', [
    (b'sample_id\nTEST_1\n', 'prediction'),
    (b'sample_id,prediction,extra\nTEST_1,100,1\n', '只能包含'),
    (b'sample_id,prediction\nTEST_1,100\nTEST_1,100\n', '重复'),
    (b'sample_id,prediction\nTEST_1,\n', '缺失'),
    (b'sample_id,prediction\nTEST_1,NaN\n', '有限数'),
    (b'sample_id,prediction\nTEST_1,inf\n', '有限数'),
    (b'sample_id,prediction\nTEST_1,-inf\n', '有限数'),
    (b'sample_id,prediction\nTEST_1,abc\n', '数字'),
    (b'sample_id,prediction\nTEST_1,100\n', '不完整'),
    (b'sample_id,prediction\nUNKNOWN,100\n', '额外'),
    (b'sample_id,prediction\nTEST_1,100,3\n', '两列'),
    (b'sample_id,prediction\n"TEST_1,100\n', '格式错误'),
])
def test_invalid(content, message):
    with pytest.raises(ValueError, match=message):
        evaluate(content, LABELS)


def test_file_size():
    with pytest.raises(ValueError, match='10 MB'):
        evaluate(b'x' * (MAX_BYTES + 1), LABELS)


@pytest.fixture
def service(tmp_path):
    labels = tmp_path / 'labels.csv'
    labels.write_text('sample_id,totalPrice\nTEST_1,100\nTEST_2,200\nTEST_3,300\n')
    db = tmp_path / 'scores.db'
    with TestClient(create_app(labels, db)) as client:
        yield client, db


def submit(client, student='001', offset=0, name='学生'):
    content = 'sample_id,prediction\n' + ''.join(f'{key},{value + offset}\n' for key, value in reversed(list(LABELS.items())))
    return client.post('/api/evaluate', data={'name': name, 'student_id': student},
                       files={'file': ('submission.csv', content, 'text/csv')})


def test_api_best_score_ranking_and_privacy(service):
    client, db = service
    assert client.get('/api/health').status_code == 200
    first = submit(client, offset=10).json()
    assert first['success'] and first['rmse'] == pytest.approx(10) and first['submission_count'] == 1
    worse = submit(client, offset=20).json()
    assert worse['rmse'] == pytest.approx(20) and worse['best_rmse'] == pytest.approx(10) and worse['submission_count'] == 2
    assert submit(client, offset=5).json()['best_rmse'] == pytest.approx(5)
    for i in range(2, 24):
        assert submit(client, student=f'{i:03}', offset=1).status_code == 200
    result = submit(client, offset=6).json()
    assert result['rank'] == 23 and result['total_students'] == 23
    board = client.get('/api/leaderboard').json()['leaderboard']
    assert len(board) == 20 and board[0]['rank'] == board[1]['rank'] == 1
    assert all(set(row) == {'rank', 'name', 'rmse'} for row in board)
    assert [x['rmse'] for x in board] == sorted(x['rmse'] for x in board)
    with sqlite3.connect(db) as connection:
        assert connection.execute('SELECT submission_count FROM leaderboard WHERE student_id="001"').fetchone()[0] == 4
    for path in ('/data/labels.csv', '/api/labels', '/backend/data/labels.csv'):
        assert client.get(path).status_code == 404


def test_upload_errors_and_cors(service):
    client, _ = service
    for name, student, filename, content in [
        (' ', '001', 'submission.csv', 'sample_id,prediction\n'),
        ('学生', 'bad id', 'submission.csv', ''),
        ('学生', '001', 'model.py', 'print(1)'),
        ('学生', '001', 'submission.csv', 'sample_id,prediction\nTEST_1,NaN\n'),
    ]:
        response = client.post('/api/evaluate', data={'name': name, 'student_id': student}, files={'file': (filename, content)})
        assert response.status_code == 400 and isinstance(response.json()['detail'], str)
    assert client.get('/api/leaderboard').json() == {'leaderboard': []}
    assert client.post('/api/evaluate', content=b'x' * (MAX_BYTES + 65537)).status_code == 413
    assert client.post('/api/evaluate', json={}).status_code == 415
    malformed = client.post('/api/evaluate', content=b'invalid', headers={'Content-Type': 'multipart/form-data'})
    assert malformed.status_code == 400 and '格式错误' in malformed.json()['detail']
    response = client.options('/api/evaluate', headers={'Origin': 'https://xianlipan.github.io', 'Access-Control-Request-Method': 'POST'})
    assert response.headers['access-control-allow-origin'] == 'https://xianlipan.github.io'


def test_missing_labels_prevents_startup(tmp_path):
    with pytest.raises(RuntimeError, match='隐藏标签'):
        with TestClient(create_app(tmp_path / 'missing.csv', tmp_path / 'db.db')):
            pass
