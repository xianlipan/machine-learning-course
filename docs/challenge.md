---
hide:
  - navigation
  - toc
---
# 北京房价预测挑战

本实验使用北京市二手房成交数据，你的任务是利用训练数据建立回归预测模型，并对给定测试集进行预测。提交预测结果后，平台将自行计算 **RMSE**，并更新排行榜。

<div class="challenge-layout" id="housing-challenge">
  <div class="challenge-main">
    <section class="challenge-panel" aria-labelledby="download-title">
      <h2 id="download-title" class="challenge-section-title">下载实验数据 <span class="challenge-title-note">使用 sample_id 对齐训练 X 与 y，sample_id 仅用作标识。</span></h2>
      <div class="challenge-downloads">
        <a href="../assets/challenge/01_北京房价_训练集_X.csv" download>01 · 训练集 X <small>CSV · 输入特征</small></a>
        <a href="../assets/challenge/02_北京房价_训练集_y.csv" download>02 · 训练集 y <small>CSV · 真实总价</small></a>
        <a href="../assets/challenge/03_北京房价_测试集_X.csv" download>03 · 测试集 X <small>CSV · 待预测样本</small></a>
        <a href="../assets/challenge/05_submission示例.csv" download>05 · 提交模板 <small>CSV · 填写 prediction</small></a>
      </div>
    </section>
    <section class="challenge-panel" aria-labelledby="submit-title">
      <h2 id="submit-title" class="challenge-section-title">提交预测结果 <span class="challenge-title-note challenge-limit-notice">每人最多可提交三次</span></h2>
      <details><summary>submission.csv 格式示例</summary>
        <pre><code>sample_id,prediction
TEST_000001,356.72
TEST_000002,421.31
TEST_000003,198.46</code></pre>
        <p>不要修改 sample_id。prediction 为预测的 totalPrice，单位为万元。正式提交必须包含全部测试样本，每个 sample_id 恰好出现一次；行顺序不限，仅允许这两列。请保存为 UTF-8 CSV，文件不超过 10 MB。</p>
      </details>
      <form id="challenge-form">
        <div class="challenge-fields">
          <label>姓名<input name="name" required maxlength="60" autocomplete="name" placeholder="请输入姓名"></label>
          <label>学号<input name="student_id" required maxlength="64" pattern="[A-Za-z0-9_-]+" placeholder="请输入学号"></label>
        </div>
        <label class="challenge-upload">上传 submission.csv<input id="challenge-file" name="file" type="file" accept=".csv,text/csv" required></label>
        <p id="challenge-filename" class="challenge-muted" aria-live="polite">尚未选择文件</p>
        <button class="md-button md-button--primary" id="challenge-submit" type="submit">开始评测</button>
        <p class="challenge-muted">姓名及最好成绩会显示在公开排行榜中，学号不公开。平台只接收预测 CSV。</p>
      </form>
    </section>
  </div>
  <aside class="challenge-panel challenge-ranking" aria-labelledby="ranking-title">
    <p class="challenge-kicker">LEADERBOARD</p>
    <h2 id="ranking-title">挑战排行榜</h2>
    <p class="challenge-muted">个人历史最好成绩 · 前 10 名</p>
    <button type="button" id="challenge-refresh" class="md-button">刷新排行榜</button>
    <p id="challenge-ranking-status" role="status">正在加载排行榜……</p>
    <div class="challenge-table-wrap">
      <table class="challenge-table"><thead><tr><th scope="col">排名</th><th scope="col">姓名</th><th scope="col">RMSE（万元）</th></tr></thead><tbody id="challenge-ranking-body"></tbody></table>
    </div>
    <p class="challenge-muted">同分并列排名。评测后，即使不在前 10 名，也能查看自己的实际排名。</p>
    <div id="challenge-result" role="status" aria-live="polite" hidden></div>
  </aside>
</div>

<noscript>请启用 JavaScript 以提交预测文件并查看排行榜。数据仍可通过上方链接下载。</noscript>
