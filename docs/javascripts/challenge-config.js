// 正式部署后，将下方占位域名替换为后端 HTTPS 地址；本地预览自动连接本机后端。
window.CHALLENGE_API_BASE = ["localhost", "127.0.0.1"].includes(window.location.hostname)
  ? "http://127.0.0.1:8001"
  : "https://YOUR-BACKEND-DOMAIN";
