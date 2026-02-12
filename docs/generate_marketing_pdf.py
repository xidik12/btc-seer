"""Generate a well-designed Marketing Guide PDF using reportlab."""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, ListFlowable, ListItem,
)
from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate, Frame
from reportlab.lib.fonts import addMapping
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

# ── Colors ──
DARK_BG = HexColor("#0D1117")
CARD_BG = HexColor("#161B22")
ACCENT_BLUE = HexColor("#4A9EFF")
ACCENT_GREEN = HexColor("#2EA043")
ACCENT_ORANGE = HexColor("#F0883E")
ACCENT_YELLOW = HexColor("#E3B341")
TEXT_PRIMARY = HexColor("#E6EDF3")
TEXT_SECONDARY = HexColor("#8B949E")
TEXT_MUTED = HexColor("#484F58")
WHITE = HexColor("#FFFFFF")
DARK_BORDER = HexColor("#30363D")
SECTION_BG = HexColor("#1C2128")
HIGHLIGHT_BG = HexColor("#1F2937")

# For PDF we use white background with dark text for readability
PAGE_BG = HexColor("#FFFFFF")
BRAND_DARK = HexColor("#0D1117")
BRAND_BLUE = HexColor("#2563EB")
BRAND_GREEN = HexColor("#059669")
BRAND_ORANGE = HexColor("#EA580C")
BRAND_PURPLE = HexColor("#7C3AED")
BRAND_RED = HexColor("#DC2626")
TEXT_DARK = HexColor("#111827")
TEXT_BODY = HexColor("#374151")
TEXT_LIGHT = HexColor("#6B7280")
LIGHT_BLUE_BG = HexColor("#EFF6FF")
LIGHT_GREEN_BG = HexColor("#ECFDF5")
LIGHT_ORANGE_BG = HexColor("#FFF7ED")
LIGHT_PURPLE_BG = HexColor("#F5F3FF")
BORDER_LIGHT = HexColor("#E5E7EB")
BORDER_BLUE = HexColor("#BFDBFE")

OUTPUT = os.path.join(os.path.dirname(__file__), "marketing-guide.pdf")

# ── Styles ──
styles = {
    "cover_title": ParagraphStyle(
        "cover_title", fontName="Helvetica-Bold", fontSize=36,
        textColor=WHITE, alignment=TA_CENTER, leading=44,
    ),
    "cover_subtitle": ParagraphStyle(
        "cover_subtitle", fontName="Helvetica", fontSize=16,
        textColor=HexColor("#93C5FD"), alignment=TA_CENTER, leading=22,
    ),
    "cover_detail": ParagraphStyle(
        "cover_detail", fontName="Helvetica", fontSize=11,
        textColor=HexColor("#9CA3AF"), alignment=TA_CENTER, leading=16,
    ),
    "h1": ParagraphStyle(
        "h1", fontName="Helvetica-Bold", fontSize=24,
        textColor=BRAND_DARK, spaceAfter=6, spaceBefore=20, leading=30,
    ),
    "h2": ParagraphStyle(
        "h2", fontName="Helvetica-Bold", fontSize=16,
        textColor=BRAND_BLUE, spaceAfter=4, spaceBefore=14, leading=22,
    ),
    "h3": ParagraphStyle(
        "h3", fontName="Helvetica-Bold", fontSize=13,
        textColor=TEXT_DARK, spaceAfter=3, spaceBefore=10, leading=18,
    ),
    "body": ParagraphStyle(
        "body", fontName="Helvetica", fontSize=10.5,
        textColor=TEXT_BODY, leading=16, spaceAfter=4,
    ),
    "body_bold": ParagraphStyle(
        "body_bold", fontName="Helvetica-Bold", fontSize=10.5,
        textColor=TEXT_DARK, leading=16, spaceAfter=4,
    ),
    "bullet": ParagraphStyle(
        "bullet", fontName="Helvetica", fontSize=10.5,
        textColor=TEXT_BODY, leading=16, leftIndent=16, bulletIndent=4,
        spaceAfter=2,
    ),
    "code": ParagraphStyle(
        "code", fontName="Courier", fontSize=9,
        textColor=TEXT_DARK, backColor=HexColor("#F3F4F6"),
        leading=13, spaceAfter=4, leftIndent=8, rightIndent=8,
        borderPadding=(4, 6, 4, 6),
    ),
    "tip": ParagraphStyle(
        "tip", fontName="Helvetica-Oblique", fontSize=10,
        textColor=BRAND_GREEN, leading=14, leftIndent=12,
        spaceAfter=4, spaceBefore=4,
    ),
    "section_num": ParagraphStyle(
        "section_num", fontName="Helvetica-Bold", fontSize=11,
        textColor=WHITE, alignment=TA_CENTER, leading=14,
    ),
    "toc_item": ParagraphStyle(
        "toc_item", fontName="Helvetica", fontSize=12,
        textColor=BRAND_BLUE, leading=22, leftIndent=20, spaceAfter=2,
    ),
    "footer": ParagraphStyle(
        "footer", fontName="Helvetica", fontSize=8,
        textColor=TEXT_LIGHT, alignment=TA_CENTER,
    ),
}


def build_pdf():
    doc = SimpleDocTemplate(
        OUTPUT,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    story = []
    W = doc.width

    # ═══════════════════════════════════════════════
    #  COVER PAGE
    # ═══════════════════════════════════════════════
    cover_table = Table(
        [[""]], colWidths=[W], rowHeights=[doc.height],
    )
    cover_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BRAND_DARK),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))

    # Build cover content separately
    story.append(Spacer(1, 60 * mm))

    # Logo / icon area
    icon_table = Table(
        [[Paragraph("&#x1f52e;", ParagraphStyle("emoji", fontSize=48, alignment=TA_CENTER))]],
        colWidths=[W],
    )
    story.append(icon_table)
    story.append(Spacer(1, 10 * mm))

    story.append(Paragraph("BTC SEER", ParagraphStyle(
        "cover_t", fontName="Helvetica-Bold", fontSize=42,
        textColor=BRAND_BLUE, alignment=TA_CENTER, leading=50,
    )))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("Marketing Guide", ParagraphStyle(
        "cover_s", fontName="Helvetica-Bold", fontSize=24,
        textColor=TEXT_DARK, alignment=TA_CENTER, leading=30,
    )))
    story.append(Spacer(1, 8 * mm))
    story.append(HRFlowable(width="40%", thickness=2, color=BRAND_BLUE, spaceAfter=8 * mm))
    story.append(Paragraph(
        "Step-by-step playbook for growing BTC Seer's user base.<br/>"
        "Written for non-technical people — follow each section exactly.",
        ParagraphStyle("cover_d", fontName="Helvetica", fontSize=12,
                       textColor=TEXT_LIGHT, alignment=TA_CENTER, leading=18),
    ))
    story.append(Spacer(1, 15 * mm))

    # Cover info boxes
    info_data = [
        ["Platform", "Telegram Bot + Web App"],
        ["Bot", "@BTCSeerBot"],
        ["Dashboard", "btc-oracle-production.up.railway.app"],
        ["Date", "February 2026"],
    ]
    info_table = Table(info_data, colWidths=[W * 0.3, W * 0.5])
    info_table.setStyle(TableStyle([
        ("TEXTCOLOR", (0, 0), (0, -1), TEXT_LIGHT),
        ("TEXTCOLOR", (1, 0), (1, -1), TEXT_DARK),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (0, 0), (0, -1), "RIGHT"),
        ("ALIGN", (1, 0), (1, -1), "LEFT"),
        ("LEFTPADDING", (1, 0), (1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(info_table)

    story.append(PageBreak())

    # ═══════════════════════════════════════════════
    #  TABLE OF CONTENTS
    # ═══════════════════════════════════════════════
    story.append(Paragraph("Table of Contents", styles["h1"]))
    story.append(Spacer(1, 4 * mm))

    toc_items = [
        ("1", "Daily Twitter/X Posting", BRAND_BLUE),
        ("2", "Reddit Strategy", BRAND_ORANGE),
        ("3", "Telegram Channel Setup", BRAND_BLUE),
        ("4", "YouTube Shorts", BRAND_RED),
        ("5", "Influencer Outreach", BRAND_PURPLE),
        ("6", "Product Hunt / Hacker News Launch", BRAND_GREEN),
        ("7", "Referral System Promotion", BRAND_ORANGE),
    ]

    for num, title, color in toc_items:
        # Number badge + title
        badge = Table(
            [[Paragraph(num, styles["section_num"])]],
            colWidths=[24], rowHeights=[24],
        )
        badge.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), color),
            ("VALIGN", (0, 0), (0, 0), "MIDDLE"),
            ("ALIGN", (0, 0), (0, 0), "CENTER"),
            ("ROUNDEDCORNERS", [6, 6, 6, 6]),
        ]))

        row = Table(
            [[badge, Paragraph(title, ParagraphStyle(
                "toc_t", fontName="Helvetica", fontSize=13,
                textColor=TEXT_DARK, leading=20,
            ))]],
            colWidths=[32, W - 40],
        )
        row.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (1, 0), (1, 0), 8),
        ]))
        story.append(row)
        story.append(Spacer(1, 3 * mm))

    story.append(PageBreak())

    # ═══════════════════════════════════════════════
    #  HELPER FUNCTIONS
    # ═══════════════════════════════════════════════

    def section_header(num, title, color=BRAND_BLUE):
        """Create a styled section header with number badge."""
        story.append(Spacer(1, 6 * mm))
        badge = Table(
            [[Paragraph(str(num), styles["section_num"])]],
            colWidths=[28], rowHeights=[28],
        )
        badge.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), color),
            ("VALIGN", (0, 0), (0, 0), "MIDDLE"),
            ("ALIGN", (0, 0), (0, 0), "CENTER"),
        ]))
        header_row = Table(
            [[badge, Paragraph(title, styles["h1"])]],
            colWidths=[36, W - 44],
        )
        header_row.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (1, 0), (1, 0), 8),
        ]))
        story.append(header_row)
        story.append(HRFlowable(width="100%", thickness=1.5, color=color, spaceAfter=4 * mm))

    def sub(title):
        story.append(Paragraph(title, styles["h2"]))

    def sub2(title):
        story.append(Paragraph(title, styles["h3"]))

    def p(text):
        story.append(Paragraph(text, styles["body"]))

    def pb(text):
        story.append(Paragraph(text, styles["body_bold"]))

    def bullet(text):
        story.append(Paragraph(f"&bull;  {text}", styles["bullet"]))

    def code_block(text):
        """Render a code/template block."""
        lines = text.strip().split("\n")
        for line in lines:
            line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            story.append(Paragraph(line if line.strip() else "&nbsp;", styles["code"]))
        story.append(Spacer(1, 2 * mm))

    def tip(text):
        tip_table = Table(
            [[Paragraph(f"&#x1f4a1;  {text}", styles["tip"])]],
            colWidths=[W],
        )
        tip_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), LIGHT_GREEN_BG),
            ("LEFTPADDING", (0, 0), (0, 0), 10),
            ("RIGHTPADDING", (0, 0), (0, 0), 10),
            ("TOPPADDING", (0, 0), (0, 0), 6),
            ("BOTTOMPADDING", (0, 0), (0, 0), 6),
        ]))
        story.append(tip_table)
        story.append(Spacer(1, 2 * mm))

    def info_box(title, text, bg=LIGHT_BLUE_BG, border=BORDER_BLUE):
        box_content = Table(
            [[Paragraph(f"<b>{title}</b><br/>{text}", ParagraphStyle(
                "box", fontName="Helvetica", fontSize=10,
                textColor=TEXT_DARK, leading=15,
            ))]],
            colWidths=[W - 4],
        )
        box_content.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), bg),
            ("LEFTPADDING", (0, 0), (0, 0), 12),
            ("RIGHTPADDING", (0, 0), (0, 0), 12),
            ("TOPPADDING", (0, 0), (0, 0), 8),
            ("BOTTOMPADDING", (0, 0), (0, 0), 8),
            ("LINEBELOW", (0, 0), (0, 0), 0.5, border),
            ("LINEABOVE", (0, 0), (0, 0), 0.5, border),
            ("LINEBEFORE", (0, 0), (0, 0), 0.5, border),
            ("LINEAFTER", (0, 0), (0, 0), 0.5, border),
        ]))
        story.append(box_content)
        story.append(Spacer(1, 3 * mm))

    def make_table(headers, rows, col_widths=None):
        """Create a styled table."""
        data = [headers] + rows
        if not col_widths:
            n = len(headers)
            col_widths = [W / n] * n
        t = Table(data, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BRAND_DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("TEXTCOLOR", (0, 1), (-1, -1), TEXT_BODY),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [PAGE_BG, HexColor("#F9FAFB")]),
            ("LINEBELOW", (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
        ]))
        story.append(t)
        story.append(Spacer(1, 3 * mm))

    def sp(h=4):
        story.append(Spacer(1, h * mm))

    # ═══════════════════════════════════════════════
    #  SECTION 1: TWITTER/X
    # ═══════════════════════════════════════════════
    section_header(1, "Daily Twitter/X Posting", BRAND_BLUE)

    info_box("Goal", "Build a following of crypto traders who see BTC Seer predictions daily.")

    sub("Account Setup")
    bullet("Create Twitter/X account: <b>@BTCSeer</b>")
    bullet("Profile pic: BTC Seer logo (crystal ball with Bitcoin)")
    bullet('Bio: <i>AI-powered Bitcoin predictions | 60+ features analyzed | Live signals &amp; accuracy tracking | Try free: t.me/BTCSeerBot</i>')
    bullet("Pin a tweet with your best accuracy screenshot")
    sp()

    sub("Daily Posting Schedule")

    sub2("Morning Post (9:00 AM UTC) — Prediction")
    code_block("""BTC Seer AI Prediction for [DATE]:

Direction: [BULLISH/BEARISH]
Confidence: [XX]%
Current Price: $[PRICE]
1h Target: $[PRICE] ([+/-X.X]%)
24h Target: $[PRICE] ([+/-X.X]%)

Track record: [X]% accuracy over [N] predictions

Try it free: t.me/BTCSeerBot

#Bitcoin #BTC #CryptoTrading #AI""")

    sub2("Evening Post (9:00 PM UTC) — Results")
    code_block("""BTC Seer prediction results for today:

1h prediction: [Correct/Wrong]
4h prediction: [Correct/Wrong]

Running accuracy: [X]% ([N] predictions)

Full dashboard: t.me/BTCSeerBot

#Bitcoin #CryptoSignals #AI""")

    sub2("Weekly Post (Sunday) — Stats Thread")
    code_block("""BTC Seer Weekly Report:

Predictions made: [N]
Correct: [N] ([X]%)
Best call: [describe]
Worst miss: [describe]

All data transparent, all accuracy auditable.

Try it: t.me/BTCSeerBot

#Bitcoin #AI #MachineLearning""")

    sub("Hashtags")
    pb("Primary:")
    p("#Bitcoin #BTC #Crypto #CryptoTrading #AI")
    pb("Secondary:")
    p("#MachineLearning #TradingSignals #CryptoSignals #BullRun #Altcoins")
    tip("Check trending crypto hashtags daily and include 1-2 relevant ones.")

    sub("Screenshot Tips")
    bullet("Open BTC Seer web app on your phone")
    bullet("Dashboard tab — screenshot the prediction card")
    bullet("Accuracy tab — screenshot the accuracy chart")
    bullet("Post screenshots as images with your tweet")

    sub("Engagement Rules")
    bullet("Reply to <b>every</b> comment on your posts")
    bullet("Quote-retweet popular BTC analysis tweets with your prediction")
    bullet("Follow and engage with crypto traders (50-100/day)")
    bullet("Never shill aggressively — let accuracy speak for itself")

    story.append(PageBreak())

    # ═══════════════════════════════════════════════
    #  SECTION 2: REDDIT
    # ═══════════════════════════════════════════════
    section_header(2, "Reddit Strategy", BRAND_ORANGE)

    info_box("Goal", "Reach crypto communities with valuable content that naturally leads to BTC Seer.", bg=LIGHT_ORANGE_BG, border=HexColor("#FED7AA"))

    sub("Target Subreddits")
    make_table(
        ["Subreddit", "Rules", "Post Type"],
        [
            ["r/CryptoCurrency", "No self-promo in titles", "Weekly prediction analysis"],
            ["r/Bitcoin", "Strict — educational only", "Technical analysis only"],
            ["r/CryptoMarkets", "More relaxed", "Trading signal posts"],
            ["r/algotrading", "Must be technical", "ML model discussion"],
            ["r/MachineLearning", "Technical depth required", "Architecture & results"],
            ["r/SideProject", "Show projects", "Launch post"],
        ],
        col_widths=[W * 0.25, W * 0.35, W * 0.4],
    )

    sub("Step 1: Build Karma (1-2 weeks)")
    bullet("Comment helpfully on 5-10 posts/day in crypto subreddits")
    bullet("Share genuine market analysis")
    bullet("Answer questions about ML or crypto trading")
    bullet("Get to <b>500+ karma</b> before posting your own content")
    sp()

    sub("Step 2: First Post (r/CryptoCurrency)")
    code_block("""Title: I built an AI system that predicts Bitcoin price
direction — here's what I learned after [N] predictions

Body:
Hey everyone,

I've been working on a Bitcoin prediction system that uses:
- Machine learning (TFT, LSTM, XGBoost ensemble)
- 60+ features (price, news sentiment, on-chain, macro)
- Transparent accuracy tracking

After [N] predictions, here are the results:
- 1h accuracy: [X]%
- 4h accuracy: [X]%
- 24h accuracy: [X]%

Key insights:
1. [What features matter most]
2. [When the model fails]
3. [Market conditions that affect accuracy]

Happy to answer questions about the methodology.

[Link to bot only if asked in comments]""")

    sub("Step 3: Technical Post (r/algotrading)")
    code_block("""Title: Bitcoin direction prediction using TFT + LSTM
+ XGBoost ensemble — architecture and results

Body:
[Technical breakdown of model architecture]
[Feature engineering approach]
[Training methodology]
[Backtesting results vs live results]
[Lessons learned]""")

    tip("NEVER directly link to the bot in post titles. Wait for people to ask, then share the link.")

    sub("Reddit Rules")
    bullet("Always provide value first, product second")
    bullet("Don't post more than once per week per subreddit")
    bullet("Follow each subreddit's specific rules carefully")
    bullet("Engage authentically in comments")

    story.append(PageBreak())

    # ═══════════════════════════════════════════════
    #  SECTION 3: TELEGRAM CHANNEL
    # ═══════════════════════════════════════════════
    section_header(3, "Telegram Channel Setup", BRAND_BLUE)

    info_box("Channel", "Create <b>@BTCSeerSignals</b> — auto-posted AI predictions &amp; signals")

    sub("Step 1: Create the Channel")
    bullet("Open Telegram → hamburger menu → <b>New Channel</b>")
    bullet('Name: <b>BTC Seer Signals</b>')
    bullet("Handle: <b>@BTCSeerSignals</b>")
    bullet("Set profile photo (BTC Seer logo)")
    sp()

    pb("Channel Description:")
    code_block("""AI-powered Bitcoin predictions & trading signals
Updated every 30 minutes
Transparent accuracy tracking

Bot: @BTCSeerBot
Web: btc-oracle-production.up.railway.app""")

    sub("Step 2: Enable Auto-Posting")
    bullet("Add @BTCSeerBot as admin to the channel")
    bullet("Grant <b>Post Messages</b> permission")
    bullet("The bot will auto-post predictions every 30 minutes")
    sp()

    sub("Step 3: Content Schedule")
    bullet("<b>Every prediction</b>: Auto-posted by bot (every 30 min)")
    bullet("<b>Daily summary</b>: Manual post with accuracy stats")
    bullet("<b>Weekly report</b>: Detailed performance analysis")
    sp()

    sub("Step 4: Cross-Promote")
    bullet("Share channel link in the bot's /start message")
    bullet("Add channel link to Twitter bio")
    bullet("Pin channel link in relevant Telegram groups")
    sp()

    sub("Telegram Groups to Join")
    bullet("Crypto trading groups (share predictions, don't spam)")
    bullet("Bitcoin discussion groups")
    bullet("AI/ML groups (share technical details)")
    tip("Provide value first. Share a prediction, wait for people to ask about the source.")

    story.append(PageBreak())

    # ═══════════════════════════════════════════════
    #  SECTION 4: YOUTUBE SHORTS
    # ═══════════════════════════════════════════════
    section_header(4, "YouTube Shorts", BRAND_RED)

    info_box("Equipment", "Smartphone with screen recording + free video editor (CapCut or InShot)", bg=HexColor("#FEF2F2"), border=HexColor("#FECACA"))

    sub('Short #1: "AI Predicts Bitcoin\'s Next Move" (30-60 sec)')
    bullet("Open phone, start screen recording")
    bullet('Open BTC Seer web app → Dashboard')
    bullet('Narrate: "This AI analyzes 60 features to predict Bitcoin\'s price direction every 30 minutes."')
    bullet("Scroll to show prediction card, confidence score")
    bullet("Switch to Accuracy page")
    bullet('Narrate: "And here\'s the real accuracy — [X]% over [N] predictions. Not cherry-picked."')
    bullet('End: "Link in bio to try it free."')
    sp()

    sub('Short #2: "Did the AI Get It Right?" (30 sec)')
    bullet("Screenshot yesterday's prediction")
    bullet("Show current price")
    bullet('Compare: "Yesterday the AI said [direction] with [X]% confidence. Today\'s price: $[X]. It was [RIGHT/WRONG]."')
    bullet('End: "Follow for daily AI Bitcoin predictions."')
    sp()

    sub('Short #3: "How This Bitcoin AI Works" (60 sec)')
    bullet("Screen record the web app")
    bullet("Show each data source tab (Technical, News, On-chain, Macro)")
    bullet('Narrate: "This AI looks at [list features]. It uses 3 ML models voting together."')
    bullet("Show the prediction result")
    bullet('End: "Try it free — link in bio."')
    sp()

    sub("Best Practices")
    bullet("Upload <b>1-2 Shorts per day</b>")
    bullet('First 3 seconds must hook: "This AI just predicted Bitcoin will..."')
    bullet("Add text overlays with CapCut")
    bullet("Hashtags: #Bitcoin #BTC #CryptoTrading #AI #TradingSignals #Shorts")
    bullet("Description: Include bot link t.me/BTCSeerBot")
    tip("Same content can be cross-posted to TikTok with the same format and hashtags.")

    story.append(PageBreak())

    # ═══════════════════════════════════════════════
    #  SECTION 5: INFLUENCER OUTREACH
    # ═══════════════════════════════════════════════
    section_header(5, "Influencer Outreach", BRAND_PURPLE)

    sub("Target Influencers")
    make_table(
        ["Type", "Followers", "Approach"],
        [
            ["Crypto YouTubers", "10K-100K", "Free premium for review"],
            ["Crypto Twitter", "5K-50K", "DM with prediction screenshot"],
            ["Trading educators", "10K+", "Affiliate/referral partnership"],
            ["AI/ML creators", "5K+", "Technical collaboration"],
        ],
        col_widths=[W * 0.3, W * 0.2, W * 0.5],
    )

    sub("Template: Crypto YouTuber Email")
    code_block("""Subject: Free AI Bitcoin prediction tool for your audience

Hi [Name],

I'm building BTC Seer — an AI that predicts Bitcoin price
direction using ML models trained on 60+ features (news
sentiment, on-chain data, macro, funding rates).

It's been running live with [X]% accuracy over [N]
predictions — all publicly auditable.

I'd love to give you free lifetime Premium access to try
it out. If you find it useful, maybe you'd share it with
your audience.

No strings attached — just want honest feedback.

Try it: t.me/BTCSeerBot

Best,
[Your name]""")

    sub("Template: Twitter DM")
    code_block("""Hey [Name], love your BTC analysis!

I built an AI prediction system hitting [X]% accuracy
over [N] live predictions. Uses ML ensemble (TFT + LSTM
+ XGBoost) on 60+ features.

Would love your take: t.me/BTCSeerBot

Happy to give you premium access to test it.""")

    sub("Outreach Process")
    bullet("Make a list of <b>50 target influencers</b> in a spreadsheet")
    bullet("Send <b>5-10 outreach messages per day</b>")
    bullet("Follow up after <b>3 days</b> if no response")
    bullet("Track responses and conversions")
    bullet("For those who agree: send premium code, ask for honest review")

    story.append(PageBreak())

    # ═══════════════════════════════════════════════
    #  SECTION 6: PRODUCT HUNT / HN
    # ═══════════════════════════════════════════════
    section_header(6, "Product Hunt / Hacker News", BRAND_GREEN)

    sub("Product Hunt Launch")

    sub2("Preparation (1 week before)")
    bullet("Create account at <b>producthunt.com</b>")
    bullet('Upload product: name "BTC Seer"')
    bullet('Tagline: "AI-powered Bitcoin predictions with transparent accuracy"')
    bullet("Prepare 4-5 screenshots (Dashboard, Predictions, Accuracy, Signals)")
    sp()

    pb("Product Description:")
    code_block("""BTC Seer is an AI system that predicts Bitcoin's price
direction using:

- 3 ML models (TFT, LSTM, XGBoost) voting in ensemble
- 60+ features: price, news, on-chain, macro, funding
- Predictions every 30 minutes with confidence scores
- Full transparent accuracy tracking

Available as Telegram Bot, Web Dashboard, and REST API.
Currently [X]% live accuracy over [N] predictions.""")

    sub2("Launch Day")
    bullet("Post at <b>12:01 AM PST</b> (PH resets daily)")
    bullet('Share on all channels: "We just launched on Product Hunt!"')
    bullet("Respond to every comment within <b>30 minutes</b>")
    bullet("Post updates throughout the day")
    sp()

    sub("Hacker News (Show HN)")
    code_block("""Title: Show HN: BTC Seer — AI Bitcoin predictions with
ML ensemble and transparent accuracy

Tech stack: Python, FastAPI, PyTorch, React, Railway
Features: OHLCV, RSI, MACD, Bollinger Bands, NLP
sentiment, funding rates, on-chain metrics, macro
indicators, fear & greed, BTC dominance, M2 supply

Live accuracy: [X]% over [N] predictions

Key insight: No single model beats a diverse ensemble.""")

    tip("Post on HN between 8-10 AM EST on weekdays. Be genuinely technical — HN readers appreciate depth.")

    story.append(PageBreak())

    # ═══════════════════════════════════════════════
    #  SECTION 7: REFERRAL SYSTEM
    # ═══════════════════════════════════════════════
    section_header(7, "Referral System Promotion", BRAND_ORANGE)

    sub("How It Works")
    bullet("Each user gets a <b>unique referral code</b> in Settings")
    bullet("Share via deep link: <b>t.me/BTCSeerBot?start=ref_CODE</b>")
    bullet("New user who joins gets <b>+7 days Premium</b>")
    bullet("Referrer also gets <b>+7 days Premium</b>")
    bullet("Leaderboard tracks top referrers")
    sp()

    sub("Social Media Post")
    code_block("""BTC Seer now has referral rewards!

Share your invite link:
-> Your friend gets 7 days Premium FREE
-> You also get +7 days Premium

Open @BTCSeerBot -> Settings -> Invite Friends

#Bitcoin #CryptoTrading #AI""")

    sub("Telegram Channel Post")
    code_block("""NEW: Invite friends, get free Premium!

Every friend you invite = +7 days Premium for BOTH.

1. Open @BTCSeerBot
2. Go to Settings -> Invite Friends
3. Share your unique link
4. Both get 7 days of AI predictions & signals

Top referrers shown on the leaderboard!""")

    story.append(PageBreak())

    # ═══════════════════════════════════════════════
    #  WEEKLY CONTENT CALENDAR
    # ═══════════════════════════════════════════════
    story.append(Paragraph("Weekly Content Calendar", styles["h1"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=BRAND_BLUE, spaceAfter=4 * mm))

    cal_data = [
        ["Day", "Twitter", "Reddit", "YouTube", "Telegram"],
        ["Mon", "Prediction + Results", "—", 'Short: "AI predicts..."', "Auto predictions"],
        ["Tue", "Prediction + Results", "—", '"Did AI get it right?"', "Auto predictions"],
        ["Wed", "Prediction + Results", "r/CryptoMarkets post", "—", "Auto predictions"],
        ["Thu", "Prediction + Results", "—", '"How the AI works"', "Auto predictions"],
        ["Fri", "Prediction + Weekly stats", "—", "—", "Auto + weekly summary"],
        ["Sat", "Engagement day", "r/CryptoCurrency post", "Weekly recap Short", "Auto predictions"],
        ["Sun", "Weekly report thread", "—", "—", "Weekly report"],
    ]
    cal = Table(cal_data, colWidths=[W * 0.1, W * 0.22, W * 0.22, W * 0.23, W * 0.23], repeatRows=1)
    cal.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("TEXTCOLOR", (0, 1), (-1, -1), TEXT_BODY),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [PAGE_BG, HexColor("#F9FAFB")]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
        ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
    ]))
    story.append(cal)
    sp(8)

    # ═══════════════════════════════════════════════
    #  METRICS
    # ═══════════════════════════════════════════════
    story.append(Paragraph("Metrics to Track", styles["h1"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=BRAND_GREEN, spaceAfter=4 * mm))

    metrics_data = [
        ["Metric", "Tool", "Month 1 Target"],
        ["Twitter followers", "Twitter Analytics", "500"],
        ["Twitter impressions/day", "Twitter Analytics", "5,000"],
        ["Reddit post upvotes", "Reddit", "50+ per post"],
        ["YouTube Shorts views", "YouTube Studio", "1,000+ per Short"],
        ["Telegram bot users", "Bot admin stats", "500"],
        ["Telegram channel subs", "Channel stats", "200"],
        ["Referral signups", "Bot admin stats", "50"],
        ["Product Hunt upvotes", "Product Hunt", "100+"],
    ]
    metrics = Table(metrics_data, colWidths=[W * 0.4, W * 0.3, W * 0.3], repeatRows=1)
    metrics.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("TEXTCOLOR", (0, 1), (-1, -1), TEXT_BODY),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [PAGE_BG, HexColor("#F9FAFB")]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
    ]))
    story.append(metrics)
    sp(8)

    # ═══════════════════════════════════════════════
    #  QUICK START CHECKLIST
    # ═══════════════════════════════════════════════
    story.append(Paragraph("Quick Start Checklist", styles["h1"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=BRAND_ORANGE, spaceAfter=4 * mm))

    checklist = [
        "Set up Twitter/X @BTCSeer account with logo + bio",
        "Post first prediction tweet with screenshot",
        "Create r/CryptoCurrency account, start building karma",
        "Create @BTCSeerSignals Telegram channel",
        "Record first YouTube Short",
        "Send first 10 influencer outreach DMs",
        "Prepare Product Hunt listing (screenshots, description)",
        "Share referral link on all channels",
        "Set up daily posting routine (morning prediction, evening results)",
    ]
    for item in checklist:
        row = Table(
            [[Paragraph("&#x2610;", ParagraphStyle("cb", fontSize=14, textColor=BRAND_BLUE)),
              Paragraph(item, styles["body"])]],
            colWidths=[20, W - 28],
        )
        row.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (0, 0), 0),
        ]))
        story.append(row)
        story.append(Spacer(1, 1.5 * mm))

    # ═══════════════════════════════════════════════
    #  BUILD
    # ═══════════════════════════════════════════════
    doc.build(story)
    print(f"PDF generated: {OUTPUT}")


if __name__ == "__main__":
    build_pdf()
