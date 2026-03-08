import { domToPng } from 'modern-screenshot'

/**
 * Capture a card DOM element as a branded PNG data URL.
 * Captures the ORIGINAL element (preserving all computed styles),
 * then overlays a watermark via canvas.
 *
 * @param {HTMLElement} element - The card element to capture
 * @param {string} label - Label for the watermark (e.g. "Power Law")
 * @returns {Promise<string>} data URL of the PNG
 */
export async function captureCard(element, label = '') {
  if (!element) throw new Error('No element to capture')

  // Wait for animations to settle
  await new Promise((resolve) => requestAnimationFrame(resolve))

  // Capture the original element directly — keeps all computed styles
  const rawDataUrl = await domToPng(element, {
    scale: 2,
    backgroundColor: '#0f0f14',
    style: {
      // Override glassmorphism for clean render
      backdropFilter: 'none',
      webkitBackdropFilter: 'none',
    },
    filter: (node) => {
      // Hide the share button itself from the capture
      if (node?.dataset?.shareBtn === 'true') return false
      return true
    },
  })

  // Add watermark via canvas
  return addWatermark(rawDataUrl, label)
}

/**
 * Overlay a branded watermark bar at the bottom of the image.
 */
function addWatermark(dataUrl, label) {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => {
      const barHeight = 48
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

      // Left text: ₿ BTC Seer
      ctx.fillStyle = '#c8a84e'
      ctx.font = 'bold 22px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
      ctx.textBaseline = 'middle'
      ctx.fillText('\u20BF BTC Seer', 24, img.height + barHeight / 2)

      // Right text: label · date
      const dateStr = new Date().toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      })
      const rightText = label ? `${label} \u00B7 ${dateStr}` : dateStr
      ctx.fillStyle = '#9090a8'
      ctx.font = '20px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
      const rightWidth = ctx.measureText(rightText).width
      ctx.fillText(rightText, canvas.width - rightWidth - 24, img.height + barHeight / 2)

      resolve(canvas.toDataURL('image/png'))
    }
    img.onerror = reject
    img.src = dataUrl
  })
}
