// background.js

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === 'complete' && tab.url && !tab.url.startsWith('chrome://')) {
    chrome.tabs.sendMessage(tabId, { action: "extract_text" }, (response) => {
      if (chrome.runtime.lastError) return;

      if (response && response.text) {
        const payload = {
          tabId: tab.id,
          url: tab.url,
          title: tab.title,
          content: response.text,
          timestamp: new Date().toISOString()
        };
        sendToLocalAgent(payload, tabId); // tabId를 함께 넘겨줍니다.
      }
    });
  }
});

function sendToLocalAgent(data, tabId) {
  fetch('http://127.0.0.1:8000/api/ingest', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
    .then(res => res.json())
    .then(response => {
      console.log("로컬 서버 응답:", response);
      // 서버가 Consistency Audit 결과를 보내줬고, 충돌이 감지되었다면 화면(content.js)으로 전송
      if (response.audit_result && response.audit_result.conflict_detected) {
        chrome.tabs.sendMessage(tabId, {
          action: "show_hud",
          data: response.audit_result
        });
      }
    })
    .catch(err => console.error("서버 연결 실패:", err));
}