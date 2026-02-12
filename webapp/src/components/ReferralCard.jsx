import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../utils/api'
import { useTelegram } from '../hooks/useTelegram'

export default function ReferralCard() {
  const { t } = useTranslation('settings')
  const { tg } = useTelegram()
  const [info, setInfo] = useState(null)
  const [leaderboard, setLeaderboard] = useState(null)
  const [showLeaderboard, setShowLeaderboard] = useState(false)
  const [loading, setLoading] = useState(true)
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!tg?.initData) {
      setLoading(false)
      return
    }
    api.getReferralInfo(tg.initData)
      .then(setInfo)
      .catch(() => setError('Failed to load referral info'))
      .finally(() => setLoading(false))
  }, [tg])

  const handleCopy = useCallback(() => {
    if (!info?.referral_code) return
    navigator.clipboard.writeText(info.referral_code).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }, [info])

  const handleShare = useCallback(() => {
    if (!info?.share_link) return
    const text = t('referral.shareText', 'Join BTC Seer — AI-powered Bitcoin predictions! Use my link for 7 days free Premium:')
    const url = `https://t.me/share/url?url=${encodeURIComponent(info.share_link)}&text=${encodeURIComponent(text)}`
    window.open(url, '_blank')
  }, [info, t])

  const handleToggleLeaderboard = useCallback(() => {
    if (!showLeaderboard && !leaderboard) {
      api.getReferralLeaderboard()
        .then((data) => setLeaderboard(data.leaderboard))
        .catch(() => {})
    }
    setShowLeaderboard((v) => !v)
  }, [showLeaderboard, leaderboard])

  if (loading) {
    return (
      <div className="bg-bg-card rounded-2xl p-4 animate-pulse">
        <div className="h-5 w-36 bg-bg-hover rounded mb-4" />
        <div className="h-12 bg-bg-hover rounded mb-3" />
        <div className="h-10 bg-bg-hover rounded" />
      </div>
    )
  }

  return (
    <div className="bg-bg-card rounded-2xl p-4 slide-up">
      <h3 className="text-text-primary font-semibold text-sm mb-1">
        {t('referral.title', 'Invite Friends')}
      </h3>
      <p className="text-text-muted text-xs mb-4">
        {t('referral.subtitle', 'Share your code — both get +7 days Premium')}
      </p>

      {info ? (
        <>
          {/* Referral Code */}
          <div className="flex items-center gap-2 mb-3">
            <div className="flex-1 bg-bg-secondary rounded-xl px-3 py-2.5 font-mono text-text-primary text-sm tracking-widest text-center">
              {info.referral_code}
            </div>
            <button
              onClick={handleCopy}
              className="px-3 py-2.5 rounded-xl bg-accent-blue/10 text-accent-blue text-xs font-semibold active:scale-95 transition-all whitespace-nowrap"
            >
              {copied ? t('referral.copied', 'Copied!') : t('referral.copy', 'Copy')}
            </button>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-2 gap-2 mb-3">
            <div className="bg-bg-secondary rounded-xl p-2.5 text-center">
              <p className="text-text-primary font-bold text-lg">{info.referral_count}</p>
              <p className="text-text-muted text-[10px]">
                {t('referral.friendsReferred', 'Friends Referred')}
              </p>
            </div>
            <div className="bg-bg-secondary rounded-xl p-2.5 text-center">
              <p className="text-accent-green font-bold text-lg">+{info.total_bonus_days}d</p>
              <p className="text-text-muted text-[10px]">
                {t('referral.bonusEarned', 'Bonus Earned')}
              </p>
            </div>
          </div>

          {/* Share Button */}
          <button
            onClick={handleShare}
            className="w-full py-2.5 rounded-xl bg-accent-blue text-white font-semibold text-sm active:scale-[0.98] transition-all mb-3"
          >
            {t('referral.shareLink', 'Share Invite Link')}
          </button>

          {/* Referred By badge */}
          {info.referred_by && (
            <div className="bg-accent-green/10 border border-accent-green/20 rounded-xl px-3 py-2 text-center mb-3">
              <p className="text-accent-green text-xs font-medium">
                {t('referral.referredBy', 'Referred by')} @{info.referred_by}
              </p>
            </div>
          )}
        </>
      ) : (
        <div className="bg-bg-secondary rounded-xl px-3 py-4 text-center mb-3">
          <p className="text-text-muted text-xs">
            {error || 'Open in Telegram to get your referral code'}
          </p>
        </div>
      )}

      {/* Leaderboard Toggle */}
      <button
        onClick={handleToggleLeaderboard}
        className="w-full text-center text-text-muted text-xs py-1.5 hover:text-text-secondary transition-colors"
      >
        {showLeaderboard
          ? t('referral.hideLeaderboard', 'Hide Leaderboard')
          : t('referral.showLeaderboard', 'Show Leaderboard')}
      </button>

      {/* Leaderboard */}
      {showLeaderboard && (
        <div className="mt-2 space-y-1">
          {leaderboard && leaderboard.length > 0 ? (
            leaderboard.map((entry) => (
              <div
                key={entry.rank}
                className="flex items-center justify-between bg-bg-secondary rounded-lg px-3 py-2"
              >
                <div className="flex items-center gap-2">
                  <span className="text-text-muted text-xs font-mono w-5">#{entry.rank}</span>
                  <span className="text-text-primary text-xs font-medium">
                    @{entry.username}
                  </span>
                </div>
                <span className="text-accent-blue text-xs font-semibold">
                  {entry.referral_count} {t('referral.refs', 'refs')}
                </span>
              </div>
            ))
          ) : (
            <p className="text-text-muted text-xs text-center py-2">
              {t('referral.noReferrals', 'No referrals yet — be the first!')}
            </p>
          )}
        </div>
      )}
    </div>
  )
}
