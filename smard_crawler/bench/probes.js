async () => {
  const r = {};
  const safe = (k, f) => { try { r[k] = f(); } catch (e) { r[k] = 'ERR:' + e.message; } };
  const withTimeout = (p, ms) => Promise.race([p, new Promise(res => setTimeout(() => res('TIMEOUT'), ms))]);
  const isNative = (fn) => typeof fn === 'function' && /\{\s*\[native code\]\s*\}$/.test(Function.prototype.toString.call(fn));

  const proto = Object.getPrototypeOf(navigator);
  safe('webdriver', () => navigator.webdriver);
  safe('webdriver_own', () => Object.prototype.hasOwnProperty.call(navigator, 'webdriver'));
  safe('ua', () => navigator.userAgent);
  safe('platform', () => navigator.platform);
  safe('languages', () => (navigator.languages || []).join(','));
  safe('plugins', () => navigator.plugins.length);
  safe('plugins_is_pluginarray', () => navigator.plugins instanceof PluginArray);
  safe('mime_types', () => navigator.mimeTypes.length);
  safe('hw_concurrency', () => navigator.hardwareConcurrency);
  safe('device_memory', () => navigator.deviceMemory);
  safe('window_chrome', () => typeof window.chrome === 'object' && window.chrome !== null);
  safe('uad_brands', () => navigator.userAgentData
    ? navigator.userAgentData.brands.map(b => b.brand + '/' + b.version).join('|') : null);
  safe('uad_platform', () => navigator.userAgentData ? navigator.userAgentData.platform : null);
  safe('getters_native', () => {
    const props = ['webdriver', 'hardwareConcurrency', 'languages', 'plugins', 'platform', 'userAgent'];
    const bad = props.filter(p => {
      const d = Object.getOwnPropertyDescriptor(proto, p);
      return d && d.get && !isNative(d.get);
    });
    return bad.length ? bad.join(',') : true;
  });
  safe('tostring_native', () => isNative(Function.prototype.toString));
  safe('screen', () => [screen.width, screen.height, screen.colorDepth].join('x'));
  safe('outer_zero', () => window.outerWidth === 0 || window.outerHeight === 0);
  safe('timezone', () => Intl.DateTimeFormat().resolvedOptions().timeZone);
  safe('webgl', () => {
    const gl = document.createElement('canvas').getContext('webgl');
    if (!gl) return null;
    const ext = gl.getExtension('WEBGL_debug_renderer_info');
    return ext ? gl.getParameter(ext.UNMASKED_VENDOR_WEBGL) + ' | ' + gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : 'no-debug-ext';
  });
  const canvasHash = () => {
    const c = document.createElement('canvas'); c.width = 220; c.height = 40;
    const x = c.getContext('2d');
    x.textBaseline = 'top'; x.font = '16px Arial'; x.fillStyle = '#f60'; x.fillRect(10, 5, 100, 25);
    x.fillStyle = '#069'; x.fillText('SMard canvas \u{1F50E}', 4, 12);
    const s = c.toDataURL(); let h = 0;
    for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
    return h;
  };
  safe('canvas_hash', () => { const a = canvasHash(), b = canvasHash(); return a === b ? a : 'UNSTABLE'; });

  let cdpTouched = false;
  try {
    const e = new Error();
    Object.defineProperty(e, 'stack', { get() { cdpTouched = true; return ''; } });
    console.debug(e);
  } catch (_) {}
  r.cdp_runtime_detected = cdpTouched;

  try {
    const q = await withTimeout(navigator.permissions.query({ name: 'notifications' }), 2000);
    r.notification_permission = typeof Notification !== 'undefined' ? Notification.permission : null;
    r.notification_query = q && q.state ? q.state : String(q);
  } catch (e) { r.notification_query = 'ERR:' + e.message; }

  try {
    const f = document.createElement('iframe'); f.srcdoc = '<p>x</p>';
    document.body.appendChild(f);
    await withTimeout(new Promise(res => f.onload = res), 2000);
    r.iframe_ua = f.contentWindow.navigator.userAgent;
    r.iframe_webdriver = f.contentWindow.navigator.webdriver;
    f.remove();
  } catch (e) { r.iframe_ua = 'ERR:' + e.message; }

  try {
    const src = 'postMessage({ua: navigator.userAgent, platform: navigator.platform, hw: navigator.hardwareConcurrency})';
    const w = new Worker(URL.createObjectURL(new Blob([src], { type: 'text/javascript' })));
    const msg = await withTimeout(new Promise(res => w.onmessage = ev => res(ev.data)), 3000);
    w.terminate();
    if (msg === 'TIMEOUT') { r.worker_ua = 'TIMEOUT'; }
    else { r.worker_ua = msg.ua; r.worker_platform = msg.platform; r.worker_hw = msg.hw; }
  } catch (e) { r.worker_ua = 'ERR:' + e.message; }

  return r;
}
