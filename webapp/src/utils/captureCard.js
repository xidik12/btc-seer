import { domToPng } from 'modern-screenshot'
import { getBotUsernameSync } from './botConfig'

const isAndroid = /android/i.test(navigator.userAgent)

/** Lazy-load html2canvas only when needed (Android) */
let _html2canvas = null
async function getHtml2Canvas() {
  if (!_html2canvas) {
    _html2canvas = (await import('html2canvas')).default
  }
  return _html2canvas
}

/**
 * Capture a card DOM element as a branded PNG data URL.
 * Uses html2canvas on Android (SVG foreignObject is broken in Android WebView),
 * and modern-screenshot on iOS/desktop where it works perfectly.
 *
 * @param {HTMLElement} element - The card element to capture
 * @param {string} label - Label for the watermark (e.g. "Power Law")
 * @returns {Promise<string>} data URL of the PNG
 */
export async function captureCard(element, label = '') {
  if (!element) throw new Error('No element to capture')

  // Wait for animations to settle
  await new Promise((resolve) => requestAnimationFrame(resolve))

  let rawDataUrl

  if (isAndroid) {
    // html2canvas re-parses CSS and paints to canvas directly —
    // works reliably on Android WebView where foreignObject fails
    const html2canvas = await getHtml2Canvas()
    const canvas = await html2canvas(element, {
      scale: 2,
      backgroundColor: '#0f0f14',
      useCORS: true,
      logging: false,
      ignoreElements: (el) => el?.dataset?.shareBtn === 'true',
    })
    rawDataUrl = canvas.toDataURL('image/png')
  } else {
    // modern-screenshot works great on iOS / desktop
    rawDataUrl = await domToPng(element, {
      scale: 2,
      backgroundColor: '#0f0f14',
      style: {
        backdropFilter: 'none',
        webkitBackdropFilter: 'none',
      },
      filter: (node) => {
        if (node?.dataset?.shareBtn === 'true') return false
        return true
      },
    })
  }

  return addWatermark(rawDataUrl, label)
}

/**
 * Overlay a branded watermark bar at the bottom of the image.
 * Line 1: "₿ BTC Seer" (left) + "Label · Date" (right)
 * Line 2: "t.me/BTC_Seer_Bot" (left)
 */
function addWatermark(dataUrl, label) {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => {
      const barHeight = 72
      const canvas = document.createElement('canvas')
      canvas.width = img.width
      canvas.height = img.height + barHeight

      const ctx = canvas.getContext('2d')

      // Background
      ctx.fillStyle = '#0f0f14'
      ctx.fillRect(0, 0, canvas.width, canvas.height)

      // Original image
      ctx.drawImage(img, 0, 0)

      // Watermark bar
      ctx.fillStyle = '#16161e'
      ctx.fillRect(0, img.height, canvas.width, barHeight)

      // Separator line
      ctx.strokeStyle = 'rgba(255,255,255,0.06)'
      ctx.lineWidth = 1
      ctx.beginPath()
      ctx.moveTo(0, img.height)
      ctx.lineTo(canvas.width, img.height)
      ctx.stroke()

      const botUsername = getBotUsernameSync() || 'BTC_Seer_Bot'

      // Line 1 left: ₿ BTC Seer
      ctx.fillStyle = '#c8a84e'
      ctx.font = 'bold 22px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
      ctx.textBaseline = 'middle'
      ctx.fillText('\u20BF BTC Seer', 24, img.height + barHeight * 0.33)

      // Line 1 right: Label · Date
      const dateStr = new Date().toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      })
      const rightText = label ? `${label} \u00B7 ${dateStr}` : dateStr
      ctx.fillStyle = '#9090a8'
      ctx.font = '20px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
      const rightWidth = ctx.measureText(rightText).width
      ctx.fillText(rightText, canvas.width - rightWidth - 24, img.height + barHeight * 0.33)

      // Line 2: bot link
      ctx.fillStyle = '#6e6e88'
      ctx.font = '16px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
      ctx.fillText(`t.me/${botUsername}`, 24, img.height + barHeight * 0.72)

      resolve(canvas.toDataURL('image/png'))
    }
    img.onerror = reject
    img.src = dataUrl
  })
}
