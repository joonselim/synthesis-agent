// content.js

// 텍스트 추출 및 HUD 출력 요청 수신
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "extract_text") {
        sendResponse({ text: document.body.innerText });
    } else if (request.action === "show_hud") {
        renderGlassHUD(request.data);
    }
});

function renderGlassHUD(auditData) {
    // 이미 HUD가 떠있다면 제거 (중복 방지)
    const existingHud = document.getElementById('synthesis-agent-hud');
    if (existingHud) existingHud.remove();

    // Glass UI 컨테이너 생성
    const hud = document.createElement('div');
    hud.id = 'synthesis-agent-hud';

    // 기획안 기반의 투명 Glass UI 스타일링
    Object.assign(hud.style, {
        position: 'fixed',
        top: '20px',
        right: '20px',
        width: '340px',
        padding: '20px',
        background: 'rgba(255, 255, 255, 0.2)', // 반투명 배경
        backdropFilter: 'blur(12px)',           // 블러 효과 (Glass 핵심)
        WebkitBackdropFilter: 'blur(12px)',
        border: '1px solid rgba(255, 60, 60, 0.4)', // 상반되는 정보 경고용 붉은 테두리
        borderLeft: '4px solid #e74c3c',            // 시각적 강조선
        borderRadius: '16px',
        boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.2)',
        zIndex: '2147483647', // 무조건 최상단
        color: '#1d1d1f',
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        transition: 'all 0.3s ease-in-out',
        opacity: '0',
        transform: 'translateX(20px)'
    });

    // HUD 내부 콘텐츠 (Auditor 결과)
    hud.innerHTML = `
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
      <h3 style="margin: 0; color: #e74c3c; font-size: 15px; font-weight: 700;">🚨 Conflict Auditor</h3>
      <span id="close-hud-btn" style="cursor: pointer; font-size: 18px; color: #666;">&times;</span>
    </div>
    <div style="font-size: 14px; font-weight: 600; line-height: 1.5; margin-bottom: 15px;">
      ${auditData.message}
    </div>
    <div style="background: rgba(255, 255, 255, 0.6); padding: 12px; border-radius: 10px; font-size: 13px; line-height: 1.6; border: 1px solid rgba(255,255,255,0.8);">
      <strong style="color: #0071e3;">💡 에이전트 판단 (Decision):</strong><br/>
      ${auditData.decision}
    </div>
  `;

    document.body.appendChild(hud);

    // 부드럽게 나타나는 애니메이션 효과
    setTimeout(() => {
        hud.style.opacity = '1';
        hud.style.transform = 'translateX(0)';
    }, 10);

    // 닫기 버튼 이벤트
    document.getElementById('close-hud-btn').addEventListener('click', () => {
        hud.style.opacity = '0';
        hud.style.transform = 'translateX(20px)';
        setTimeout(() => hud.remove(), 300);
    });
}