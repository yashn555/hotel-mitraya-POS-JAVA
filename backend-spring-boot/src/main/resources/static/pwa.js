/**
 * Hotel Mitraya PWA App Installer & Service Worker Registration
 * Enables 1-Click Native Android App Installation for Waiters & Cashiers
 */

(function () {
    // 1. Register Service Worker
    if ('serviceWorker' in navigator) {
        window.addEventListener('load', () => {
            navigator.serviceWorker.register('/static/sw.js')
                .then(reg => {
                    console.log('[PWA] Service Worker registered:', reg.scope);
                })
                .catch(err => {
                    console.warn('[PWA] Service Worker registration failed:', err);
                });
        });
    }

    // 2. Android PWA Install Prompt Handler
    let deferredPrompt = null;

    window.addEventListener('beforeinstallprompt', (e) => {
        // Prevent default browser mini-infobar
        e.preventDefault();
        deferredPrompt = e;

        // Show install button / banner if not running in standalone mode
        if (!window.matchMedia('(display-mode: standalone)').matches) {
            renderPWAInstallBanner();
        }
    });

    function renderPWAInstallBanner() {
        if (document.getElementById('pwa-install-banner')) return;

        const banner = document.createElement('div');
        banner.id = 'pwa-install-banner';
        banner.style.cssText = `
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            z-index: 99999;
            background: linear-gradient(135deg, #1e3a8a, #1d4ed8);
            border: 2px solid #3b82f6;
            color: #ffffff;
            padding: 12px 20px;
            border-radius: 14px;
            display: flex;
            align-items: center;
            gap: 14px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5), 0 0 20px rgba(37,99,235,0.4);
            font-family: 'Plus Jakarta Sans', system-ui, sans-serif;
            max-width: 90vw;
            animation: slideUp 0.3s ease;
        `;

        banner.innerHTML = `
            <img src="/static/logo.png" style="width: 38px; height: 38px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.3);">
            <div>
                <div style="font-weight: 800; font-size: 14px; letter-spacing: 0.3px;">Install Mitraya App</div>
                <div style="font-size: 11.5px; color: #bfdbfe;">Direct full-screen waiter POS app</div>
            </div>
            <button id="btn-pwa-install-now" style="
                background: #f59e0b;
                color: #0f172a;
                border: none;
                padding: 8px 14px;
                border-radius: 8px;
                font-weight: 800;
                font-size: 13px;
                cursor: pointer;
                display: flex;
                align-items: center;
                gap: 6px;
                margin-left: 4px;
            ">
                <i class="fa-solid fa-download"></i> Install
            </button>
            <button id="btn-pwa-install-close" style="
                background: transparent;
                border: none;
                color: #93c5fd;
                font-size: 16px;
                cursor: pointer;
                padding: 4px;
            ">&times;</button>
        `;

        document.body.appendChild(banner);

        document.getElementById('btn-pwa-install-now').addEventListener('click', async () => {
            if (deferredPrompt) {
                deferredPrompt.prompt();
                const { outcome } = await deferredPrompt.userChoice;
                console.log('[PWA] User choice:', outcome);
                deferredPrompt = null;
                banner.remove();
            }
        });

        document.getElementById('btn-pwa-install-close').addEventListener('click', () => {
            banner.remove();
        });
    }

    window.addEventListener('appinstalled', () => {
        console.log('[PWA] Hotel Mitraya App installed successfully!');
        const banner = document.getElementById('pwa-install-banner');
        if (banner) banner.remove();
        deferredPrompt = null;
    });
})();
