"""CSV-only evaluation; never execute submissions or expose private labels."""
import csv
import io
import math
from pathlib import Path

MAX_BYTES = 10 * 1024 * 1024


def read_values(content: bytes, value_column: str) -> dict[str, float]:
    if not content:
        raise ValueError('文件为空。')
    if len(content) > MAX_BYTES:
        raise ValueError('文件不能超过 10 MB。')
    try:
        text = content.decode('utf-8-sig')
    except UnicodeDecodeError:
        raise ValueError('请使用 UTF-8 编码保存 CSV 文件。') from None
    try:
        reader = csv.reader(io.StringIO(text, newline=''), strict=True)
        header = next(reader, [])
        for column in ('sample_id', value_column):
            if column not in header:
                raise ValueError(f'提交文件缺少 {column} 列。')
        if len(header) != 2 or set(header) != {'sample_id', value_column}:
            raise ValueError(f'文件只能包含 sample_id 和 {value_column} 两列。')
        id_index, value_index = header.index('sample_id'), header.index(value_column)
        values = {}
        for row in reader:
            if len(row) != 2:
                raise ValueError('CSV 每行必须恰好包含两列，不能有空行。')
            sample_id, raw_value = row[id_index], row[value_index].strip()
            if not sample_id or sample_id != sample_id.strip():
                raise ValueError('sample_id 不能为空或包含首尾空格。')
            if sample_id in values:
                raise ValueError('发现重复的 sample_id。')
            if not raw_value:
                raise ValueError('预测结果中存在缺失值。')
            try:
                value = float(raw_value)
            except ValueError:
                raise ValueError('prediction 必须是数字。') from None
            if not math.isfinite(value):
                raise ValueError('预测结果必须为有限数，不能包含 NaN、inf 或 -inf。')
            values[sample_id] = value
        if not values:
            raise ValueError('测试样本数量不完整。')
        return values
    except csv.Error:
        raise ValueError('CSV 格式错误，请检查分隔符和引号。') from None


def load_labels(path: Path) -> dict[str, float]:
    return read_values(path.read_bytes(), 'totalPrice')


def evaluate(content: bytes, labels: dict[str, float]) -> float:
    predictions = read_values(content, 'prediction')
    if predictions.keys() != labels.keys():
        if predictions.keys() - labels.keys():
            raise ValueError('提交文件包含额外的 sample_id。')
        raise ValueError('测试样本数量不完整，缺少测试 sample_id。')
    # hypot avoids overflow when squaring large, but finite, predictions.
    errors = [predictions[key] - target for key, target in labels.items()]
    rmse = math.hypot(*errors) / math.sqrt(len(labels))
    if not math.isfinite(rmse):
        raise ValueError('预测数值过大，无法计算有限的 RMSE。')
    return rmse
