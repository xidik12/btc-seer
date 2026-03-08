import { domToPng } from 'modern-screenshot'

/**
 * Capture a card DOM element as a branded PNG data URL.
 * @param {HTMLElement} element - The card element to capture
 * @param {string} label - Label for the watermark (e.g. "Power Law")
 * @returns {Promise<string>} data URL of the PNG
 */
export async function captureCard(element, label = '') {
  if (!element) throw new Error('No element to capture')

  // Wait for animations to settle
  await new Promise((resolve) => requestAnimationFrame(resolve))

  const width = element.offsetWidth
  const clone = element.cloneNode(true)

  // Fix glassmorphism: replace backdrop-filter with solid bg
  clone.querySelectorAll('*').forEach((el) => {
    const style = el.style
    if (style.backdropFilter) style.backdropFilter = 'none'
    if (style.webkitBackdropFilter) style.webkitBackdropFilter = 'none'
  })

  // Walk all elements with bg-bg-card class and solidify
  const walker = (node) => {
    if (node.nodeType !== 1) return
    if (node.className && typeof node.className === 'string' && node.className.includes('bg-bg-card')) {
      node.style.backdropFilter = 'none'
      node.style.webkitBackdropFilter = 'none'
      node.style.backgroundColor = '#22222e'
    }
    for (const child of node.children) walker(child)
  }
  walker(clone)

  // Solidify the root element too
  clone.style.backdropFilter = 'none'
  clone.style.webkitBackdropFilter = 'none'
  if (clone.className && typeof clone.className === 'string' && clone.className.includes('bg-bg-card')) {
    clone.style.backgroundColor = '#22222e'
  }

  // Inject watermark bar at bottom
  const watermark = document.createElement('div')
  watermark.style.cssText = `
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 12px;
    margin-top: 8px;
    border-top: 1px solid rgba(255,255,255,0.06);
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  `
  const left = document.createElement('span')
  left.textContent = '\u20BF BTC Seer'
  left.style.cssText = 'color: #c8a84e; font-size: 11px; font-weight: 700; letter-spacing: 0.02em;'

  const right = document.createElement('span')
  const dateStr = new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  right.textContent = label ? `${label} \u00B7 ${dateStr}` : dateStr
  right.style.cssText = 'color: #9090a8; font-size: 10px;'

  watermark.appendChild(left)
  watermark.appendChild(right)
  clone.appendChild(watermark)

  // Position clone off-screen for rendering
  clone.style.position = 'fixed'
  clone.style.left = '-9999px'
  clone.style.top = '0'
  clone.style.width = `${width}px`
  clone.style.zIndex = '-1'
  document.body.appendChild(clone)

  try {
    const dataUrl = await domToPng(clone, {
      scale: 2,
      backgroundColor: '#0f0f14',
      width,
      style: {
        // Ensure no backdrop-filter on root
        backdropFilter: 'none',
        webkitBackdropFilter: 'none',
      },
    })
    return dataUrl
  } finally {
    document.body.removeChild(clone)
  }
}
