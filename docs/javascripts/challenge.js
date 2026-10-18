(() => {
  function init() {
    const root = document.getElementById('housing-challenge');
    if (!root || root.dataset.initialized) return;
    root.dataset.initialized = 'true';
    const get = (id) => document.getElementById(id);
    const form = get('challenge-form');
    const fileInput = get('challenge-file');
    const result = get('challenge-result');
    const button = get('challenge-submit');
    const rankingStatus = get('challenge-ranking-status');
    const base = (window.CHALLENGE_API_BASE || '').replace(/\/+$/, '');
    const configured = /^https?:\/\//.test(base) && !base.includes('YOUR-BACKEND-DOMAIN');

    async function api(path, options = {}) {
      if (!configured) throw new Error('评测服务尚未配置，请等待教师开放挑战。');
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 60000);
      try {
        const response = await fetch(base + path, { ...options, signal: controller.signal });
        const data = await response.json();
        if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : '请求失败，请检查文件后重试。');
        return data;
      } catch (error) {
        if (error.name === 'AbortError') throw new Error('请求超时，请刷新排行榜确认结果后重试。');
        if (error instanceof TypeError || error instanceof SyntaxError) throw new Error('无法连接评测服务，请检查网络或联系教师。');
        throw error;
      } finally { clearTimeout(timeout); }
    }

    async function refresh() {
      rankingStatus.textContent = '正在加载排行榜……';
      try {
        const data = await api('/api/leaderboard');
        const body = get('challenge-ranking-body');
        body.replaceChildren();
        data.leaderboard.forEach((entry) => {
          const row = document.createElement('tr');
          if (entry.rank <= 3) row.className = 'challenge-top';
          [entry.rank, entry.name, Number(entry.rmse).toFixed(2)].forEach((value) => {
            const cell = document.createElement('td');
            cell.textContent = value;
            row.append(cell);
          });
          body.append(row);
        });
        rankingStatus.textContent = data.leaderboard.length ? '已更新 · 按完整精度排名' : '暂无成绩，欢迎提交第一份预测。';
      } catch (error) { rankingStatus.textContent = error.message; }
    }

    fileInput.addEventListener('change', () => {
      get('challenge-filename').textContent = fileInput.files[0]?.name || '尚未选择文件';
    });
    get('challenge-refresh').addEventListener('click', refresh);
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      result.hidden = false;
      result.className = '';
      const file = fileInput.files[0];
      if (!file || !/\.csv$/i.test(file.name) || file.size > 10 * 1024 * 1024) {
        result.textContent = '请选择不超过 10 MB 的 CSV 文件。';
        return;
      }
      // Capture all fields before disabling the button.
      const payload = new FormData(form);
      button.disabled = true;
      result.textContent = '正在评测，请稍候……';
      try {
        const data = await api('/api/evaluate', { method: 'POST', body: payload });
        result.replaceChildren();
        const title = document.createElement('h3');
        title.textContent = '评测完成 · 提交成功';
        result.append(title);
        const score = document.createElement('p');
        score.className = 'challenge-score';
        score.textContent = `RMSE：${Number(data.rmse).toFixed(2)} 万元`;
        result.append(score);
        const details = document.createElement('p');
        details.textContent = `当前排名：${data.rank} / ${data.total_students}（按历史最好成绩） · 最好 RMSE：${Number(data.best_rmse).toFixed(2)} 万元 · 你已提交：${data.submission_count} 次`;
        if (Number.isInteger(data.remaining_submissions)) details.textContent += ` · 剩余可提交：${data.remaining_submissions} 次`;
        result.append(details);
        const time = document.createElement('p');
        time.textContent = `提交时间：${new Date(data.submitted_at).toLocaleString('zh-CN')}`;
        result.append(time);
        await refresh();
      } catch (error) {
        result.className = 'challenge-error';
        result.textContent = `提交失败：${error.message}`;
      } finally { button.disabled = false; }
    });
    refresh();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
  if (typeof document$ !== 'undefined') document$.subscribe(init);
})();
