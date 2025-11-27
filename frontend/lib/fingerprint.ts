/**
 * Генерация уникального отпечатка устройства для детекции множественных устройств
 */

export async function generateDeviceFingerprint(): Promise<string> {
  const components: Record<string, any> = {}
  
  // Разрешение экрана
  components.screen = `${screen.width}x${screen.height}x${screen.colorDepth}`
  
  // Часовой пояс
  components.timezone = Intl.DateTimeFormat().resolvedOptions().timeZone
  
  // Язык
  components.language = navigator.language
  
  // Платформа
  components.platform = navigator.platform
  
  // Аппаратная конкуренция (количество ядер)
  components.hardwareConcurrency = navigator.hardwareConcurrency || 0
  
  // Память устройства (если доступна)
  if ('deviceMemory' in navigator) {
    components.deviceMemory = (navigator as any).deviceMemory
  }
  
  // Canvas fingerprint
  try {
    const canvas = document.createElement('canvas')
    const ctx = canvas.getContext('2d')
    if (ctx) {
      ctx.textBaseline = 'top'
      ctx.font = '14px Arial'
      ctx.fillText('NeuroView Fingerprint', 2, 2)
      components.canvas = canvas.toDataURL()
    }
  } catch (e) {
    // Игнорируем ошибки canvas
  }
  
  // WebGL fingerprint
  try {
    const canvas = document.createElement('canvas')
    const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl') as WebGLRenderingContext | null
    if (gl && 'getExtension' in gl) {
      const debugInfo = gl.getExtension('WEBGL_debug_renderer_info')
      if (debugInfo) {
        components.webglVendor = gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL)
        components.webglRenderer = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL)
      }
    }
  } catch (e) {
    // Игнорируем ошибки WebGL
  }
  
  // User Agent
  components.userAgent = navigator.userAgent
  
  // Создаем строку для хеширования
  const fingerprintString = JSON.stringify(components)
  
  // Хешируем с помощью Web Crypto API
  try {
    const encoder = new TextEncoder()
    const data = encoder.encode(fingerprintString)
    const hashBuffer = await crypto.subtle.digest('SHA-256', data)
    const hashArray = Array.from(new Uint8Array(hashBuffer))
    const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('')
    return hashHex
  } catch (e) {
    // Fallback на простой хеш если crypto API недоступен
    let hash = 0
    for (let i = 0; i < fingerprintString.length; i++) {
      const char = fingerprintString.charCodeAt(i)
      hash = ((hash << 5) - hash) + char
      hash = hash & hash // Convert to 32bit integer
    }
    return Math.abs(hash).toString(16)
  }
}




