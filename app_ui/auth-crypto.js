/**
 * DuoDish 登录/注册 前端加密工具
 * 使用 RSA-OAEP SHA-256 加密用户名和密码，保护传输安全
 *
 * 使用前需确保运行在安全上下文（HTTPS 或 localhost）
 *
 * @example
 * // 登录
 * const encrypted = await encryptAuthData(publicKey, { username: 'alice', password: '123456' });
 * fetch('/api/auth/login', { method: 'POST', body: JSON.stringify({ encryptedData: encrypted }) });
 *
 * @example
 * // 注册
 * const encrypted = await encryptAuthData(publicKey, { username: 'bob', password: '123456', nickname: '阿宝' });
 * fetch('/api/auth/register', { method: 'POST', body: JSON.stringify({ encryptedData: encrypted }) });
 */

/**
 * 从 API 获取 RSA 公钥
 * @param {string} [baseUrl=''] - API 基础 URL
 * @returns {Promise<string>} PEM 格式公钥
 */
export async function fetchPublicKey(baseUrl = '') {
  const res = await fetch(`${baseUrl}/api/auth/public-key`);
  if (!res.ok) throw new Error('获取公钥失败');
  const json = await res.json();
  if (!json.publicKey) throw new Error('公钥格式错误');
  return json.publicKey;
}

/**
 * 将 PEM 公钥转换为 CryptoKey
 * @param {string} pem - PEM 格式公钥
 * @returns {Promise<CryptoKey>}
 */
export async function importPublicKey(pem) {
  const pemContents = pem
    .replace(/-----BEGIN PUBLIC KEY-----/, '')
    .replace(/-----END PUBLIC KEY-----/, '')
    .replace(/\s/g, '');
  const binaryDer = Uint8Array.from(atob(pemContents), (c) => c.charCodeAt(0));
  return crypto.subtle.importKey(
    'spki',
    binaryDer,
    { name: 'RSA-OAEP', hash: 'SHA-256' },
    false,
    ['encrypt']
  );
}

/**
 * 生成随机十六进制串（用于防重放、确保密文唯一性）
 */
function randomHex(len) {
  const arr = new Uint8Array(len);
  crypto.getRandomValues(arr);
  return Array.from(arr, (b) => b.toString(16).padStart(2, '0')).join('');
}

/**
 * 使用 RSA 公钥加密认证数据
 * 自动注入时间戳 _t 和随机数 _n，防止重放攻击并确保每次密文不同
 * @param {string|CryptoKey} publicKeyOrPem - PEM 字符串或已导入的 CryptoKey
 * @param {{ username: string, password: string, nickname?: string }} data - 待加密对象
 * @returns {Promise<string>} Base64 编码的密文，可直接作为 encryptedData 传给登录/注册接口
 */
export async function encryptAuthData(publicKeyOrPem, data) {
  const publicKey =
    typeof publicKeyOrPem === 'string'
      ? await importPublicKey(publicKeyOrPem)
      : publicKeyOrPem;

  const payload = JSON.stringify({
    username: data.username,
    password: data.password,
    ...(data.nickname != null && { nickname: data.nickname }),
    _t: Math.floor(Date.now() / 1000),
    _n: randomHex(16),
  });

  const encoder = new TextEncoder();
  const plainBytes = encoder.encode(payload);

  const cipherBytes = await crypto.subtle.encrypt(
    { name: 'RSA-OAEP' },
    publicKey,
    plainBytes
  );

  const bytes = new Uint8Array(cipherBytes);
  let binary = '';
  for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
  return btoa(binary);
}

/**
 * 便捷方法：获取公钥并加密，用于登录
 * @param {{ username: string, password: string }} data
 * @param {string} [baseUrl='']
 * @returns {Promise<string>} encryptedData
 */
export async function encryptLoginData(data, baseUrl = '') {
  const pem = await fetchPublicKey(baseUrl);
  return encryptAuthData(pem, data);
}

/**
 * 便捷方法：获取公钥并加密，用于注册
 * @param {{ username: string, password: string, nickname?: string }} data
 * @param {string} [baseUrl='']
 * @returns {Promise<string>} encryptedData
 */
export async function encryptRegisterData(data, baseUrl = '') {
  const pem = await fetchPublicKey(baseUrl);
  return encryptAuthData(pem, data);
}
