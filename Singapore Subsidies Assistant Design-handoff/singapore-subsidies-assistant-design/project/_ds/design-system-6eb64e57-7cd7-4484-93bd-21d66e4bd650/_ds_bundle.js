/* @ds-bundle: {"format":4,"namespace":"DesignSystem_6eb64e","components":[{"name":"Button","sourcePath":"components/core/Button.jsx"},{"name":"Card","sourcePath":"components/core/Card.jsx"},{"name":"StatusBadge","sourcePath":"components/core/StatusBadge.jsx"},{"name":"Tag","sourcePath":"components/core/Tag.jsx"},{"name":"ChartSeries","sourcePath":"components/data/ChartSeries.jsx"},{"name":"DataTable","sourcePath":"components/data/DataTable.jsx"},{"name":"FilterBar","sourcePath":"components/data/FilterBar.jsx"},{"name":"KpiCard","sourcePath":"components/data/KpiCard.jsx"},{"name":"GlassPanel","sourcePath":"components/glass/GlassPanel.jsx"},{"name":"TabBar","sourcePath":"components/terminal/TabBar.jsx"},{"name":"WindowChrome","sourcePath":"components/terminal/WindowChrome.jsx"},{"name":"LoginScreen","sourcePath":"ui_kits/app/AppShell.jsx"},{"name":"AppShell","sourcePath":"ui_kits/app/AppShell.jsx"},{"name":"SettingsPanel","sourcePath":"ui_kits/app/AppShell.jsx"},{"name":"Dashboard","sourcePath":"ui_kits/dashboard/Dashboard.jsx"},{"name":"ExecutiveSummarySlide","sourcePath":"ui_kits/deck/Slides.jsx"},{"name":"BigStatSlide","sourcePath":"ui_kits/deck/Slides.jsx"},{"name":"InsightVsDataSlide","sourcePath":"ui_kits/deck/Slides.jsx"}],"sourceHashes":{"components/core/Button.jsx":"d064aac0f6a1","components/core/Card.jsx":"097a3150d306","components/core/StatusBadge.jsx":"8f9606f6f4a1","components/core/Tag.jsx":"77ce143e09f6","components/data/ChartSeries.jsx":"958d9328555d","components/data/DataTable.jsx":"c21a494ca127","components/data/FilterBar.jsx":"45191e81ff33","components/data/KpiCard.jsx":"c1ab6fbfe9a6","components/glass/GlassPanel.jsx":"6198c65b1bb2","components/terminal/TabBar.jsx":"ad2de05b746c","components/terminal/WindowChrome.jsx":"9a7094c6eab9","doc-page.js":"371bab66f42d","ui_kits/app/AppShell.jsx":"9116acb07d12","ui_kits/dashboard/Dashboard.jsx":"b4575f057ab4","ui_kits/deck/Slides.jsx":"0dab7c4ef8e6","ui_kits/webapp/Shell.jsx":"2ac5ec4224c6"},"inlinedExternals":[],"unexposedExports":[]} */

(() => {

const __ds_ns = (window.DesignSystem_6eb64e = window.DesignSystem_6eb64e || {});

const __ds_scope = {};

(__ds_ns.__errors = __ds_ns.__errors || []);

// components/core/Button.jsx
try { (() => {
const RADII = {
  'glow-dark': 'var(--radius-md)',
  terminal: 'var(--radius-sm)',
  pill: '999px',
  flat: '0px',
  glass: '999px',
  corporate: 'var(--radius-sm)',
  dense: 'var(--radius-sm)'
};
function Button({
  variant = 'primary',
  shape = 'pill',
  children,
  onClick,
  disabled,
  style
}) {
  const radius = RADII[shape] || '8px';
  const isMono = shape === 'terminal';
  const base = {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    fontFamily: isMono ? "var(--font-mono, 'JetBrains Mono', monospace)" : 'var(--font-heading)',
    fontWeight: 600,
    fontSize: 13,
    lineHeight: 1.2,
    padding: '8px 18px',
    borderRadius: radius,
    cursor: disabled ? 'not-allowed' : 'pointer',
    opacity: disabled ? 0.45 : 1,
    border: '1px solid transparent',
    textDecoration: 'none'
  };
  const variantStyles = {
    primary: {
      background: 'var(--color-accent)',
      color: 'var(--color-bg)'
    },
    secondary: {
      background: 'transparent',
      color: 'var(--color-text)',
      border: '1px solid var(--color-muted)'
    },
    ghost: {
      background: 'transparent',
      color: 'var(--color-accent)',
      border: 'none',
      padding: '8px 4px'
    },
    outline: {
      background: 'transparent',
      color: 'var(--color-accent)',
      border: '1px solid var(--color-accent)'
    }
  };
  return /*#__PURE__*/React.createElement("button", {
    onClick: onClick,
    disabled: disabled,
    style: {
      ...base,
      ...variantStyles[variant],
      ...style
    }
  }, children);
}
Object.assign(__ds_scope, { Button });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Button.jsx", error: String((e && e.message) || e) }); }

// components/core/Card.jsx
try { (() => {
const RADII = {
  'glow-dark': 'var(--radius-md)',
  terminal: 'var(--radius-md)',
  pill: 'var(--radius-lg)',
  flat: '0px',
  glass: 'var(--radius-lg)',
  corporate: 'var(--radius-sm)',
  dense: 'var(--radius-sm)'
};
function Card({
  kicker,
  title,
  children,
  shape = 'pill',
  accentBorder = false
}) {
  const radius = RADII[shape] || '12px';
  const isFlat = shape === 'flat';
  const isGlass = shape === 'glass';
  return /*#__PURE__*/React.createElement("div", {
    style: {
      background: isGlass ? 'color-mix(in srgb, var(--color-text) 5%, transparent)' : isFlat ? 'transparent' : 'var(--color-surface)',
      border: isFlat ? 'none' : isGlass ? '1px solid color-mix(in srgb, var(--color-text) 10%, transparent)' : accentBorder ? '1px solid var(--color-accent)' : '1px solid color-mix(in srgb, var(--color-text) 10%, transparent)',
      borderTop: isFlat ? '1px solid color-mix(in srgb, var(--color-text) 15%, transparent)' : undefined,
      borderRadius: radius,
      padding: '16px',
      display: 'flex',
      flexDirection: 'column',
      gap: 8
    }
  }, kicker && /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 9,
      fontWeight: 700,
      letterSpacing: '.08em',
      textTransform: 'uppercase',
      color: 'var(--color-accent)',
      fontFamily: 'var(--font-heading)'
    }
  }, kicker), title && /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-heading)',
      fontWeight: 600,
      fontSize: 17,
      color: 'var(--color-text)'
    }
  }, title), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-body)',
      fontSize: 13,
      color: 'var(--color-muted)',
      lineHeight: 1.5
    }
  }, children));
}
Object.assign(__ds_scope, { Card });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Card.jsx", error: String((e && e.message) || e) }); }

// components/core/StatusBadge.jsx
try { (() => {
function StatusBadge({
  status = 'info',
  label,
  shape = 'pill'
}) {
  const radius = shape === 'flat' || shape === 'dense' ? '2px' : shape === 'terminal' ? '4px' : '999px';
  const colors = {
    success: 'var(--color-success)',
    warning: 'var(--color-warning)',
    alert: 'var(--color-alert)',
    info: 'var(--color-accent)'
  };
  const c = colors[status] || colors.info;
  return /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 6,
      fontSize: 11,
      fontFamily: 'var(--font-body)',
      padding: '4px 10px',
      borderRadius: radius,
      background: `color-mix(in srgb, ${c} 14%, var(--color-surface))`,
      color: c
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      width: 6,
      height: 6,
      borderRadius: '50%',
      background: c,
      flex: 'none'
    }
  }), label);
}
Object.assign(__ds_scope, { StatusBadge });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/StatusBadge.jsx", error: String((e && e.message) || e) }); }

// components/core/Tag.jsx
try { (() => {
const RADII = {
  'glow-dark': '6px',
  terminal: '4px',
  pill: '999px',
  flat: '0px',
  glass: '999px',
  corporate: '4px',
  dense: '2px'
};
function Tag({
  tone = 'accent',
  shape = 'pill',
  children
}) {
  const radius = RADII[shape] || '6px';
  const tones = {
    accent: {
      background: 'color-mix(in srgb, var(--color-accent) 16%, var(--color-surface))',
      color: 'var(--color-accent)'
    },
    neutral: {
      background: 'var(--color-surface)',
      color: 'var(--color-muted)'
    },
    outline: {
      background: 'transparent',
      color: 'var(--color-accent)',
      border: '1px solid var(--color-accent)'
    }
  };
  return /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      fontSize: 11,
      fontFamily: 'var(--font-body)',
      letterSpacing: '.02em',
      padding: '3px 10px',
      borderRadius: radius,
      ...tones[tone]
    }
  }, children);
}
Object.assign(__ds_scope, { Tag });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Tag.jsx", error: String((e && e.message) || e) }); }

// components/data/ChartSeries.jsx
try { (() => {
/**
 * Colorblind-safe multi-series bar/line renderer. Reads --color-series-1..5
 * from the active theme so every theme rotates its own 5-color set, but the
 * ORDER is fixed system-wide (Series 1 → 5) per the functional color rules.
 */
function ChartSeries({
  data,
  kind = 'bar',
  width = 748,
  height = 165
}) {
  const seriesVar = i => `var(--color-series-${i % 5 + 1})`;
  const max = Math.max(...data.map(d => Math.max(...d.values)));
  const chartH = height - 25,
    baseline = height - 15;
  const groupW = width / data.length;
  return /*#__PURE__*/React.createElement("svg", {
    width: width,
    height: height,
    style: {
      display: 'block'
    }
  }, /*#__PURE__*/React.createElement("line", {
    x1: "0",
    y1: baseline,
    x2: width,
    y2: baseline,
    stroke: "color-mix(in srgb, var(--color-text) 15%, transparent)",
    strokeWidth: "1"
  }), data.map((group, gi) => {
    const barW = (groupW - 16) / group.values.length;
    return group.values.map((v, si) => {
      const h = v / max * chartH;
      const x = gi * groupW + 8 + si * barW;
      return kind === 'bar' ? /*#__PURE__*/React.createElement("rect", {
        key: si,
        x: x,
        y: baseline - h,
        width: barW - 4,
        height: h,
        fill: seriesVar(si)
      }) : null;
    });
  }), data.map((group, gi) => /*#__PURE__*/React.createElement("text", {
    key: gi,
    x: gi * groupW + groupW / 2,
    y: height - 3,
    textAnchor: "middle",
    fontSize: "10",
    fill: "var(--color-muted)",
    fontFamily: "var(--font-body)"
  }, group.label)));
}
Object.assign(__ds_scope, { ChartSeries });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/data/ChartSeries.jsx", error: String((e && e.message) || e) }); }

// components/data/DataTable.jsx
try { (() => {
function DataTable({
  columns,
  rows,
  shape = 'flat',
  pageInfo
}) {
  const isFlat = shape === 'flat';
  return /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("table", {
    style: {
      width: '100%',
      borderCollapse: 'collapse',
      fontSize: 13,
      fontFamily: 'var(--font-body)'
    }
  }, /*#__PURE__*/React.createElement("thead", null, /*#__PURE__*/React.createElement("tr", null, columns.map((c, i) => /*#__PURE__*/React.createElement("th", {
    key: i,
    style: {
      textAlign: 'left',
      fontSize: 10,
      letterSpacing: '.06em',
      textTransform: 'uppercase',
      color: 'var(--color-muted)',
      padding: '8px 10px',
      borderBottom: `1px solid ${isFlat ? 'var(--color-text)' : 'color-mix(in srgb, var(--color-text) 15%, transparent)'}`,
      fontFamily: 'var(--font-heading)',
      fontWeight: 600
    }
  }, c)))), /*#__PURE__*/React.createElement("tbody", null, rows.map((row, ri) => /*#__PURE__*/React.createElement("tr", {
    key: ri
  }, row.map((cell, ci) => /*#__PURE__*/React.createElement("td", {
    key: ci,
    style: {
      padding: '8px 10px',
      borderBottom: '1px solid color-mix(in srgb, var(--color-text) 8%, transparent)',
      color: 'var(--color-text)'
    }
  }, cell)))))), pageInfo && /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      justifyContent: 'flex-end',
      alignItems: 'center',
      gap: 8,
      marginTop: 10,
      fontSize: 11,
      color: 'var(--color-muted)',
      fontFamily: 'var(--font-body)'
    }
  }, pageInfo));
}
Object.assign(__ds_scope, { DataTable });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/data/DataTable.jsx", error: String((e && e.message) || e) }); }

// components/data/FilterBar.jsx
try { (() => {
/**
 * Sits above every dashboard/table: date range, segment selector, search.
 * Consistent position and composition across all themes.
 */
function FilterBar({
  dateRange = 'Last 30 days',
  segment = 'All segments',
  onApply,
  shape = 'pill'
}) {
  const radius = shape === 'flat' || shape === 'dense' ? '4px' : shape === 'terminal' ? '4px' : '999px';
  const chip = {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 6,
    fontSize: 12,
    padding: '6px 14px',
    borderRadius: radius,
    border: '1px solid color-mix(in srgb, var(--color-text) 15%, transparent)',
    color: 'var(--color-text)',
    fontFamily: 'var(--font-body)',
    background: 'var(--color-surface)'
  };
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 10,
      flexWrap: 'wrap',
      marginBottom: 16
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: chip
  }, dateRange), /*#__PURE__*/React.createElement("span", {
    style: chip
  }, segment), /*#__PURE__*/React.createElement("input", {
    placeholder: "Search\u2026",
    style: {
      ...chip,
      background: 'var(--color-bg)',
      minWidth: 140,
      outline: 'none'
    }
  }), /*#__PURE__*/React.createElement(__ds_scope.Button, {
    variant: "secondary",
    shape: shape,
    onClick: onApply,
    style: {
      marginLeft: 'auto',
      fontSize: 12,
      padding: '6px 14px'
    }
  }, "Apply"));
}
Object.assign(__ds_scope, { FilterBar });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/data/FilterBar.jsx", error: String((e && e.message) || e) }); }

// components/data/KpiCard.jsx
try { (() => {
function Sparkline({
  points,
  color
}) {
  if (!points || points.length < 2) return null;
  const w = 80,
    h = 28;
  const max = Math.max(...points),
    min = Math.min(...points);
  const range = max - min || 1;
  const step = w / (points.length - 1);
  const d = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${i * step},${h - (p - min) / range * h}`).join(' ');
  return /*#__PURE__*/React.createElement("svg", {
    width: w,
    height: h,
    style: {
      display: 'block'
    }
  }, /*#__PURE__*/React.createElement("path", {
    d: d,
    fill: "none",
    stroke: color,
    strokeWidth: "1.75",
    strokeLinecap: "round",
    strokeLinejoin: "round"
  }));
}
const RADII = {
  'glow-dark': 'var(--radius-md)',
  terminal: 'var(--radius-md)',
  pill: 'var(--radius-lg)',
  flat: '0px',
  glass: 'var(--radius-lg)',
  corporate: 'var(--radius-sm)',
  dense: 'var(--radius-sm)'
};

/**
 * Multi-metric KPI card: label, primary metric, trend sparkline, and a delta
 * vs. a comparison baseline (prior period or target). Delta color is never
 * the only signal — always paired with an arrow glyph.
 */
function KpiCard({
  label,
  value,
  delta,
  deltaLabel = 'vs prior period',
  trend,
  shape = 'pill',
  accentColor
}) {
  const radius = RADII[shape] || '12px';
  const isFlat = shape === 'flat';
  const positive = delta != null && delta >= 0;
  const deltaColor = delta == null ? 'var(--color-muted)' : positive ? 'var(--color-success)' : 'var(--color-alert)';
  const trendColor = accentColor || 'var(--color-accent)';
  return /*#__PURE__*/React.createElement("div", {
    style: {
      background: isFlat ? 'transparent' : 'var(--color-surface)',
      borderTop: isFlat ? '1px solid color-mix(in srgb, var(--color-text) 15%, transparent)' : undefined,
      border: isFlat ? undefined : '1px solid color-mix(in srgb, var(--color-text) 10%, transparent)',
      borderRadius: radius,
      padding: 16,
      display: 'flex',
      flexDirection: 'column',
      gap: 8
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 9,
      fontWeight: 700,
      letterSpacing: '.08em',
      textTransform: 'uppercase',
      color: 'var(--color-muted)',
      fontFamily: 'var(--font-heading)'
    }
  }, label), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'flex-end',
      justifyContent: 'space-between',
      gap: 12
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-heading)',
      fontWeight: 700,
      fontSize: 26,
      color: 'var(--color-text)',
      lineHeight: 1
    }
  }, value), trend && /*#__PURE__*/React.createElement(Sparkline, {
    points: trend,
    color: trendColor
  })), delta != null && /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 11,
      color: deltaColor,
      fontFamily: 'var(--font-body)'
    }
  }, positive ? '▲' : '▼', " ", Math.abs(delta), "% ", deltaLabel));
}
Object.assign(__ds_scope, { KpiCard });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/data/KpiCard.jsx", error: String((e && e.message) || e) }); }

// components/glass/GlassPanel.jsx
try { (() => {
/** Midnight Luxury-only: translucent surface with a hairline edge. Use sparingly — one or two per screen, never stacked densely (rendering cost). */
function GlassPanel({
  children,
  style
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      background: 'color-mix(in srgb, var(--color-text) 5%, transparent)',
      border: '1px solid color-mix(in srgb, var(--color-text) 10%, transparent)',
      borderRadius: 'var(--radius-lg)',
      padding: 20,
      ...style
    }
  }, children);
}
Object.assign(__ds_scope, { GlassPanel });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/glass/GlassPanel.jsx", error: String((e && e.message) || e) }); }

// components/terminal/TabBar.jsx
try { (() => {
/** Darcula-only: file-tab strip below the window chrome. */
function TabBar({
  tabs,
  activeIndex = 0
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 2,
      padding: '0 14px',
      background: 'var(--color-bg)',
      borderBottom: '1px solid color-mix(in srgb, var(--color-text) 12%, transparent)'
    }
  }, tabs.map((t, i) => /*#__PURE__*/React.createElement("span", {
    key: i,
    style: {
      padding: '8px 16px',
      fontFamily: "var(--font-mono, 'JetBrains Mono', monospace)",
      fontSize: 11,
      background: i === activeIndex ? 'var(--color-surface)' : 'transparent',
      color: i === activeIndex ? 'var(--color-text)' : 'var(--color-muted)',
      borderTop: i === activeIndex ? '2px solid var(--color-accent)' : '2px solid transparent'
    }
  }, t)));
}
Object.assign(__ds_scope, { TabBar });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/terminal/TabBar.jsx", error: String((e && e.message) || e) }); }

// components/terminal/WindowChrome.jsx
try { (() => {
/** Darcula-only: editor-window title bar with traffic lights. */
function WindowChrome({
  title,
  badge
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 8,
      padding: '10px 14px',
      background: 'color-mix(in srgb, var(--color-bg) 85%, black)',
      borderBottom: '1px solid color-mix(in srgb, var(--color-text) 12%, transparent)'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      width: 10,
      height: 10,
      borderRadius: '50%',
      background: 'var(--color-alert)',
      display: 'inline-block'
    }
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      width: 10,
      height: 10,
      borderRadius: '50%',
      background: 'var(--color-warning)',
      display: 'inline-block'
    }
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      width: 10,
      height: 10,
      borderRadius: '50%',
      background: 'var(--color-success)',
      display: 'inline-block'
    }
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: "var(--font-mono, 'JetBrains Mono', monospace)",
      fontSize: 11,
      color: 'var(--color-muted)',
      marginLeft: 8
    }
  }, title), badge && /*#__PURE__*/React.createElement("span", {
    style: {
      marginLeft: 'auto',
      background: 'var(--color-accent)',
      color: 'var(--color-bg)',
      fontFamily: 'var(--font-heading)',
      fontWeight: 600,
      fontSize: 10,
      letterSpacing: '.08em',
      textTransform: 'uppercase',
      padding: '4px 12px',
      borderRadius: 3
    }
  }, badge));
}
Object.assign(__ds_scope, { WindowChrome });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/terminal/WindowChrome.jsx", error: String((e && e.message) || e) }); }

// doc-page.js
try { (() => {
// @ds-adherence-ignore -- omelette starter scaffold (raw elements/hex/px by design)
// Copied omelette starter. Re-running copy_starter_component with this kind overwrites this file with the latest version (page content is unaffected).
/* BEGIN USAGE */
/**
 * <doc-page> — paged-document shell for printable HTML.
 *
 * FIRST, decide how the document paginates — up front, before building:
 *
 * - FLOWING document (the default): write the whole document as one
 *   normal HTML flow inside <doc-page>; the browser's print engine
 *   splits it onto pages at export. Use for long-form documents with a
 *   single text flow: reports, memos, letters, essays.
 * - EXPLICIT pagination: a fixed set of pre-paginated pages, one
 *   <section class="page"> child per page. Use when the user asks for a
 *   specific page count, or the design implies one: a one-page resume, a
 *   two-sided flier, a poster, a certificate, a brochure — any richly
 *   laid-out document without a single text flow.
 * - If in doubt, ask the user as part of the build.
 *
 * PAGE SIZING — paper differs by country (letter vs A4), so the printed
 * sheet is not one fixed truth:
 * - FLOWING documents pin NO paper size: the print engine paginates
 *   onto the user's real paper, and the content reflows to it.
 * - EXPLICITLY PAGINATED documents print each page at a FIXED page box
 *   with overflow hidden — letter by default, size="a4" for a clearly
 *   metric user, the user's chosen paper when they export. Design each
 *   page to FILL that box, fitting letter and A4 alike without overlap.
 * - width/height pin an explicit fixed size, ONLY when the user gives
 *   one.
 * Never write your own @page rule or hard-code paper dimensions in the
 * content.
 *
 * Sizing modes (attributes):
 *   (none)                      — portrait: flowing docs use the user's
 *           paper; explicitly paginated pages use the named size box
 *           (letter unless size="a4")
 *   orientation="landscape"     — the same, landscape
 *   width / height              — explicit fixed size, ONLY when the user
 *           gives one (e.g. width="22in" height="30in" for a 22×30
 *           poster): the page IS the design's size, printed at true
 *           dimensions (or scaled onto the user's paper at print time).
 *           Any absolute CSS length: px/in/mm/cm/pt/pc.
 * The component announces the chosen mode to the host app at runtime (a
 * meta tag it injects), so the print path can inject the user's true
 * paper size.
 *
 * On screen the document renders on a desk background: a flowing
 * document as one tall scrolling sheet (Google Docs' pageless view);
 * explicitly paginated documents as one card per page.
 *
 * EXPLICIT pagination usage:
 *   <style>doc-page:not(:defined){visibility:hidden}</style>
 *   <doc-page>
 *     <section class="page" id="p1">…one page's design…</section>
 *     <section class="page" id="p2">…</section>
 *   </doc-page>
 *   <script src="doc-page.js"></script>
 * How the page box works, concretely: each .page prints as ONE full-bleed
 * sheet at a FIXED physical size — letter by default (set size="a4" for
 * a clearly metric user), the user's chosen paper when they export —
 * with overflow hidden. Nothing scrolls and nothing reflows onto a next
 * sheet: content that misses the box is CLIPPED. Design each page to
 * FILL that page box, and to fit it — letter and A4 alike — without
 * overlap. Each page is a size container; don't size anything in
 * viewport units (they track the window, not the page), and never set
 * width or height on the .page section itself (the component sizes the
 * page box; an authored height like 100% is meaningless at print and is
 * overridden). The component owns the page box, the screen card chrome,
 * and the page breaks (never add your own break-before/after). Don't mix
 * .page sections with flowing content or header/footer slots in the same
 * document.
 *
 * FLOWING usage:
 *   <style>doc-page:not(:defined){visibility:hidden}</style>
 *   <doc-page margin="0.75in">
 *     <h1>Title</h1>
 *     <p>…body…</p>
 *   </doc-page>
 *   <script src="doc-page.js"></script>
 * There is no manual page-splitting — the browser's print engine
 * paginates at export. Standard break-hygiene rules (`break-inside:
 * avoid` on figures, code blocks, images and table rows; `orphans/
 * widows: 3`) are applied so paragraphs and groups split cleanly. On
 * screen and at print, headings default to `text-wrap: balance` and
 * body text to `text-wrap: pretty`; the defaults have zero specificity,
 * so any text-wrap you declare wins.
 *
 * Other attributes:
 *   size    — letter | a4 | legal (default letter). Flowing documents:
 *           preview proportion only — it does NOT pin their printed
 *           paper (the print dialog's paper governs); leave it alone
 *           there. Explicitly paginated documents: it sets the page box
 *           the cards and the pinned @page share (the export dialog's
 *           choice overrides both at print) — set size="a4" for a
 *           clearly metric user. Scaled-fit: names the sheet the fit is
 *           computed against, same a4-for-metric-users advice.
 *   content-width / content-height — the design's own fixed dimensions
 *           (CSS lengths), for scaling a fixed-size design ONTO the
 *           named sheet: content lays out at exactly this size, and the
 *           component scales it to fit that sheet's printable area
 *           (centered horizontally, top-aligned; the export dialog
 *           re-fits to the user's actual paper choice where available).
 *           Both must be set; they do not change the page box. For pages
 *           WITHOUT running header/footer slots.
 *   margin  — printable inset on every page of a FLOWING document
 *           (default 0.75in); margin="0" makes pages full-bleed.
 *           Explicitly paginated pages are always full-bleed.
 *
 * Running header/footer (flowing documents only): give an element
 * `slot="header"` or `slot="footer"` and it repeats on every printed
 * page via `position: fixed`. To keep body text from sliding under it,
 * the component prints inside a single-cell table whose <thead>/<tfoot>
 * are spacers sized to the header/footer height — browsers repeat
 * thead/tfoot on every page, so each sheet's content starts below the
 * header and ends above the footer. On screen the header/footer render
 * once at the top/bottom of the sheet.
 *
 * At print the component injects `@page { margin: 0 }` (which leaves
 * Chrome no margin box to draw its date/URL/page-count header in) and
 * moves the visual margin onto the sheet's own padding. It also marks
 * the document as owning its print CSS (a
 * `meta[name="omelette-owns-print"]` it injects at runtime), so the
 * PDF export never injects page-geometry CSS of its own on top.
 *
 * Print best practices for the content you author:
 * - Multi-column text: use CSS columns (`column-count` +
 *   `column-gap`), never side-by-side flex/grid columns — only real
 *   CSS columns flow and break across pages. `column-span: all` lets
 *   a heading span the columns; `hyphens: auto` (needs `lang` on
 *   the html element) keeps narrow columns readable.
 * - Page breaks in flowing documents: `break-before: page` on an
 *   element that must start a new page (a chapter, an appendix). Add
 *   your own kept-together blocks (callouts, stat tiles, cards) to a
 *   `break-inside: avoid` rule, and keep each one shorter than a page.
 * - Extend `orphans: 3; widows: 3` to any custom text blocks you add
 *   (p and li are covered by default).
 * - Give long tables a <thead> — browsers repeat it on every printed
 *   page.
 * - No `position: fixed`/`sticky` and no viewport units in content:
 *   fixed elements stamp every printed page (running headers/footers go
 *   in the component's slots) and `100vh` mis-sizes at print.
 *
 * Author content as static HTML so the user can click-to-edit any text
 * directly. Do not set width/padding/background on the document body —
 * the component owns the sheet box.
 */
/* END USAGE */

(() => {
  const PAPER = {
    letter: ['8.5in', '11in'],
    a4: ['210mm', '297mm'],
    legal: ['8.5in', '14in']
  };
  const CSS_LENGTH = /^\d+(\.\d+)?(px|in|mm|cm|pt|pc)$/;
  // Unitless "0" is a valid CSS length and the natural way to write
  // margin="0"; normalise it to 0px so max()/calc() (which reject a bare
  // number) keep working.
  const safeLen = (v, fb) => {
    v = (v || '').trim();
    return v === '0' ? '0px' : CSS_LENGTH.test(v) ? v : fb;
  };
  // WebKit (Safari and every iOS browser shell) never repeats a table's
  // thead/tfoot on printed pages (WebKit bug 17205), so the spacer-borne
  // vertical margins of a FLOWING document reach only the first page
  // there. Engine check, not browser check: vendor is 'Apple Computer,
  // Inc.' exactly for WebKit and 'Google Inc.' for Blink.
  const WK_PRINT = /apple/i.test(navigator.vendor || '');
  // CSS length → px number (CSS absolute units are exact: 1in = 96px).
  // Returns NaN for anything safeLen would reject — callers gate on it.
  const PX_PER = {
    px: 1,
    in: 96,
    mm: 96 / 25.4,
    cm: 96 / 2.54,
    pt: 96 / 72,
    pc: 16
  };
  const toPx = v => {
    const m = /^(\d+(?:\.\d+)?)(px|in|mm|cm|pt|pc)$/.exec((v || '').trim());
    return m ? parseFloat(m[1]) * PX_PER[m[2]] : NaN;
  };
  const stylesheet = `
    :host {
      position: relative;
      display: block;
      /* When the viewport is narrower than the page, grow to wrap the
       * sheet (plus this padding) instead of staying viewport-width, so
       * the desk background and right margin reach the sheet's far edge
       * in the horizontal scroll. */
      min-width: max-content;
      min-height: 100vh;
      background: #f5f5f4;
      padding: 48px 24px;
      box-sizing: border-box;
      font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif;
      --doc-page-w: 8.5in;
      --doc-page-h: 11in;
      --doc-page-margin: 0.75in;
      --doc-hdr-h: 0px;
      --doc-ftr-h: 0px;
      --doc-hdr-pad: 0px;
      --doc-ftr-pad: 0px;
    }
    .sheet {
      width: var(--doc-page-w);
      margin: 0 auto;
      background: #fff;
      box-shadow: 0 2px 10px rgba(20, 20, 19, 0.12);
      border-radius: 7px;
      box-sizing: border-box;
      padding: var(--doc-page-margin);
    }
    .frame { width: 100%; border-collapse: collapse; }
    /* Scaled-fit mode (content-width/content-height): the inner .fit box
     * lays the content out at its authored fixed size and scales it onto
     * the printable area; .fit-box reserves the scaled footprint in flow
     * (transforms don't affect layout) and centers it. Without the mode,
     * both divs are unstyled block pass-throughs. */
    /* Explicit pagination: direct .page children are the pages. The sheet
     * becomes a transparent stack and each page carries the card look on
     * screen; at print each page is exactly one full-bleed sheet. The
     * ::slotted defaults are deliberately weak (document CSS wins), so
     * authored page styling can override any of this. */
    .sheet.paginated {
      background: transparent;
      box-shadow: none;
      border-radius: 0;
      padding: 0;
    }
    .paginated ::slotted(.page) {
      position: relative;
      display: block;
      width: 100%;
      aspect-ratio: var(--doc-page-ar);
      container-type: size;
      overflow: hidden;
      box-sizing: border-box;
      background: #fff;
      border-radius: 7px;
      box-shadow: 0 2px 10px rgba(0, 0, 0, 0.25);
      print-color-adjust: exact;
      -webkit-print-color-adjust: exact;
      break-inside: avoid;
    }
    .paginated ::slotted(.page:not(:first-child)) { margin-top: 1rem; }
    @media print {
      .sheet.paginated { padding: 0; }
      /* The flowing-document vertical inset lives on the repeating
       * thead/tfoot spacers, not the sheet padding — they must go too,
       * or each full-sheet .page is pushed ~margin down and spills onto
       * a second sheet. Paginated pages are full-bleed by definition
       * (content owns its insets). */
      .sheet.paginated .hdr-space,
      .sheet.paginated .ftr-space { height: 0; }
      .paginated ::slotted(.page) {
        border-radius: 0 !important;
        box-shadow: none !important;
        margin: 0 !important;
        /* Physical page-box sizing, no viewport units: Safari resolves
         * 100vh against the window, not the page box, so a vh-sized card
         * paginates wrong there. --doc-page-w/h are the named size by
         * default and are overridden to the user's chosen paper by the
         * export path, so every card is exactly one sheet either way.
         * Width + height (same source values as @page size) rather than
         * width + aspect-ratio: the ratio is a 6-decimal rounding of the
         * same division, and a few millionths of overflow would spill a
         * blank sheet after every page. The screen-only aspect-ratio
         * (preview proportions) must not leak into print. cqh typography
         * tracks the same box.
         *
         * Every declaration is !important: per CSS Scoping, unimportant
         * shadow ::slotted rules LOSE to the document context, so a page
         * section's authored inline style would silently beat this print
         * geometry. A model-authored height:100% did exactly that — the
         * percentage resolves as auto in the all-auto print ancestry, the
         * base rule's size containment turns auto into ZERO, and
         * overflow:hidden then paints nothing: a blank PDF with perfect
         * page boxes. At print the component's geometry is the design's
         * whole contract, so it must win over any authored sizing. */
        aspect-ratio: auto !important;
        width: var(--doc-page-w) !important;
        height: var(--doc-page-h) !important;
        overflow: hidden !important;
      }
      .paginated ::slotted(.page:not(:first-child)) {
        break-before: page !important;
        margin-top: 0 !important;
      }
    }
    .fit-mode .fit-box {
      width: calc(var(--doc-fit-w) * var(--doc-fit-scale));
      height: calc(var(--doc-fit-h) * var(--doc-fit-scale));
      margin: 0 auto;
      break-inside: avoid;
    }
    .fit-mode .fit {
      width: var(--doc-fit-w);
      height: var(--doc-fit-h);
      transform: scale(var(--doc-fit-scale));
      transform-origin: top left;
    }
    .frame td, .frame th { padding: 0; text-align: left; font-weight: inherit; }
    .hdr-space { height: var(--doc-hdr-h); }
    .ftr-space { height: var(--doc-ftr-h); }
    ::slotted([slot="header"]),
    ::slotted([slot="footer"]) { display: block; box-sizing: border-box; }
    @media print {
      :host { background: none; padding: 0; min-width: 0; min-height: 0; }
      .sheet {
        width: auto; margin: 0; box-shadow: none; border-radius: 0;
        padding: 0 var(--doc-page-margin);
      }
      /* The thead/tfoot spacers repeat on every page, so they carry the
       * vertical page margin (which the sheet's own padding cannot, since
       * that padding is consumed once on the first/last page). The running
       * header/footer are fixed inside that band. */
      /* The 0.35in is breathing room between a running header/footer and
       * the body; without one the spacer is exactly the page margin, so a
       * margin="0" full-bleed document gets truly full-bleed pages. */
      .hdr-space { height: max(var(--doc-page-margin), calc(var(--doc-hdr-h) + var(--doc-hdr-pad))); }
      .ftr-space { height: max(var(--doc-page-margin), calc(var(--doc-ftr-h) + var(--doc-ftr-pad))); }
      /* WebKit flowing documents: @page carries the vertical margin (see
       * _syncPrintPageRule), so the spacers keep only whatever a running
       * header/footer needs BEYOND it — page 1 would otherwise double its
       * top inset. Paginated sheets already zero their spacers above. */
      .sheet.wk-print:not(.paginated) .hdr-space { height: max(0px, calc(max(var(--doc-page-margin), calc(var(--doc-hdr-h) + var(--doc-hdr-pad))) - var(--doc-page-margin))); }
      .sheet.wk-print:not(.paginated) .ftr-space { height: max(0px, calc(max(var(--doc-page-margin), calc(var(--doc-ftr-h) + var(--doc-ftr-pad))) - var(--doc-page-margin))); }
      ::slotted([slot="header"]) {
        position: fixed; top: 0; left: 0; right: 0; margin: 0;
        padding: calc(var(--doc-page-margin) * 0.45) var(--doc-page-margin) 0;
      }
      ::slotted([slot="footer"]) {
        position: fixed; bottom: 0; left: 0; right: 0; margin: 0;
        padding: 0 var(--doc-page-margin) calc(var(--doc-page-margin) * 0.45);
      }
    }
  `;
  class DocPage extends HTMLElement {
    static get observedAttributes() {
      return ['size', 'width', 'height', 'margin', 'orientation', 'content-width', 'content-height'];
    }
    constructor() {
      super();
      this._root = this.attachShadow({
        mode: 'open'
      });
      this._mo = typeof MutationObserver === 'function' ? new MutationObserver(() => this._scheduleMeasure()) : null;
    }

    /** The named paper's [w, h], swapped when orientation="landscape".
     *  Only the named size swaps — explicit width/height are exact values
     *  the author already oriented. */
    _paperSize() {
      const named = PAPER[(this.getAttribute('size') || '').toLowerCase()] || PAPER.letter;
      const landscape = (this.getAttribute('orientation') || '').trim().toLowerCase() === 'landscape';
      return landscape ? [named[1], named[0]] : named;
    }
    get pageWidth() {
      return safeLen(this.getAttribute('width'), this._paperSize()[0]);
    }
    get pageHeight() {
      return safeLen(this.getAttribute('height'), this._paperSize()[1]);
    }
    get pageMargin() {
      return safeLen(this.getAttribute('margin'), '0.75in');
    }

    /** Scaled-fit mode's content box [w, h] as CSS lengths, or null when
     *  the mode is off (either attribute missing/invalid/zero — a partial
     *  declaration falls back to normal flow rather than guessing). */
    _contentFit() {
      const w = safeLen(this.getAttribute('content-width'), null);
      const h = safeLen(this.getAttribute('content-height'), null);
      if (!w || !h) return null;
      const wPx = toPx(w),
        hPx = toPx(h);
      return wPx > 0 && hPx > 0 ? [w, h, wPx, hPx] : null;
    }
    connectedCallback() {
      if (!this._sheet) this._render();
      this._syncSize();
      this._syncPrintPageRule();
      this._ensureTextWrapDefaults();
      this._ensureOwnsPrintMeta();
      this._syncFixedSizeMeta();
      this._syncPrintSizingMeta();
      if (this._mo) this._mo.observe(this, {
        subtree: true,
        childList: true,
        characterData: true,
        attributes: true
      });
      this._onResize = () => this._scheduleMeasure();
      window.addEventListener('resize', this._onResize);
      if (document.fonts && document.fonts.ready) {
        document.fonts.ready.then(() => this._scheduleMeasure());
      }
      this._scheduleMeasure();
    }
    disconnectedCallback() {
      window.removeEventListener('resize', this._onResize);
      if (this._mo) this._mo.disconnect();
      if (this._raf) {
        cancelAnimationFrame(this._raf);
        this._raf = null;
      }
      // Drop the head rules when the last doc-page leaves, so a deleted
      // document's @page geometry and text-wrap defaults can't apply to
      // whatever replaces it.
      const survivor = document.querySelector('doc-page');
      if (!survivor) {
        ['doc-page-print', 'doc-page-text-wrap', 'doc-page-owns-print', 'doc-page-fixed-size', 'doc-page-print-sizing'].forEach(id => {
          const tag = document.getElementById(id);
          if (tag) tag.remove();
        });
        // A live deck-stage deferred its own print-sizing meta to ours —
        // hand the page-global meta over so the deck isn't left unmarked.
        const deck = document.querySelector('deck-stage');
        if (deck && typeof deck._ensurePrintSizingMeta === 'function') {
          deck._ensurePrintSizingMeta();
        }
      } else {
        // A departed owner hands each page-global meta to whatever
        // doc-page remains (or it's removed).
        if (typeof survivor._syncFixedSizeMeta === 'function') {
          survivor._syncFixedSizeMeta();
        }
        if (typeof survivor._syncPrintSizingMeta === 'function') {
          survivor._syncPrintSizingMeta();
        }
      }
    }
    attributeChangedCallback() {
      if (!this._sheet) return;
      this._syncSize();
      this._syncPrintPageRule();
      this._syncFixedSizeMeta();
      this._syncPrintSizingMeta();
      this._scheduleMeasure();
    }
    _render() {
      this._root.innerHTML = `
        <style>${stylesheet}</style>
        <style id="vars"></style>
        <div class="sheet" data-screen-label="Document">
          <table class="frame" role="presentation">
            <thead><tr><th><div class="hdr-space"><slot name="header"></slot></div></th></tr></thead>
            <tbody><tr><td class="body"><div class="fit-box"><div class="fit"><slot></slot></div></div></td></tr></tbody>
            <tfoot><tr><td><div class="ftr-space"><slot name="footer"></slot></div></td></tr></tfoot>
          </table>
        </div>`;
      this._sheet = this._root.querySelector('.sheet');
      this._vars = this._root.getElementById('vars');
    }

    /** Runtime sizing lives in a shadow <style> :host rule, never on the
     *  light-DOM host element, so serialize-persist can't write it back. */
    _syncSize(hdrH, ftrH) {
      // Scaled-fit mode: content at its authored size, scaled onto the
      // printable area (page minus margins on both axes). The factor is a
      // plain number var so calc(length * number) stays valid; 4 decimals
      // keeps the shadow style stable across re-measures. Upscaling is
      // allowed — print transforms are vector, so text and CSS stay crisp
      // (raster images soften, which the catalog bullet warns about).
      const fit = this._contentFit();
      let fitVars = '';
      if (fit) {
        const marginPx = toPx(this.pageMargin) || 0;
        const availW = toPx(this.pageWidth) - 2 * marginPx;
        const availH = toPx(this.pageHeight) - 2 * marginPx;
        const scale = Math.min(availW / fit[2], availH / fit[3]);
        if (scale > 0 && Number.isFinite(scale)) {
          fitVars = '--doc-fit-w:' + fit[0] + ';' + '--doc-fit-h:' + fit[1] + ';' + '--doc-fit-scale:' + scale.toFixed(4) + ';';
        }
      }
      this._sheet.classList.toggle('fit-mode', !!fitVars);
      // Numeric w/h ratio for the paginated page cards' aspect-ratio —
      // aspect-ratio takes a number, not a length ratio, so compute it
      // here (CSS length division isn't portable). 6 decimals keeps the
      // shadow style stable across re-syncs.
      const arW = toPx(this.pageWidth);
      const arH = toPx(this.pageHeight);
      const ar = arW > 0 && arH > 0 ? (arW / arH).toFixed(6) : '0.772727';
      this._vars.textContent = ':host{' + fitVars + '--doc-page-ar:' + ar + ';' + '--doc-page-w:' + this.pageWidth + ';' + '--doc-page-h:' + this.pageHeight + ';' + '--doc-page-margin:' + this.pageMargin + ';' + '--doc-hdr-h:' + (hdrH || 0) + 'px;' + '--doc-ftr-h:' + (ftrH || 0) + 'px;' + '--doc-hdr-pad:' + (hdrH ? '0.35in' : '0px') + ';' + '--doc-ftr-pad:' + (ftrH ? '0.35in' : '0px') + '}';
    }

    /** @page is a no-op inside shadow DOM, so the rule lives in <head>.
     *  Re-appended on every sync so it stays last in source order — the
     *  @page cascade is source-order per descriptor, so this rule wins
     *  over any other @page rule in the document.
     *
     *  The @page SIZE is pinned where the page box IS part of the design:
     *  explicit-fixed-size mode (width + height authored), scaled-fit
     *  mode (the named sheet the fit targets), and explicit pagination
     *  (the named size the cards share — so card and sheet agree on
     *  every print path, and the export path's chosen paper overrides
     *  BOTH with one later rule). For FLOWING documents no paper size is
     *  emitted at all — the true size comes from the user's preference,
     *  injected by the export path or chosen in the print dialog — so a
     *  flowing document never fights the paper it lands on.
     *  margin: 0 is emitted in every mode: it leaves Chrome no margin box
     *  to draw its date/URL/page-count header in, and the visual margin
     *  lives on the sheet's own padding. */
    _syncPrintPageRule() {
      const id = 'doc-page-print';
      let tag = document.getElementById(id);
      if (!tag) {
        tag = document.createElement('style');
        tag.id = id;
      }
      document.head.appendChild(tag);
      // Three print-geometry regimes:
      // - true-size: the page IS the design — pin its exact size.
      // - scaled-fit (content-width/height): the fit factor is computed
      //   against the NAMED paper's printable area, so that paper must
      //   stay pinned or the scaled content overflows a smaller sheet
      //   (the export path re-fits and re-pins at print time on top).
      // - default modes: no paper size — but landscape still needs the
      //   paper-agnostic 'size: landscape' keyword, because the size
      //   descriptor is what carries orientation; without it a landscape
      //   document prints portrait whenever nothing injects a size.
      const landscape = (this.getAttribute('orientation') || '').trim().toLowerCase() === 'landscape';
      // Explicit pagination pins the page box to the SAME values that
      // size the cards (the named size by default, the export path's
      // chosen paper when its later rule overrides both) — card and
      // sheet agree on every print path, and a mismatched real paper
      // shrinks-to-fit in the dialog instead of clipping a Letter card
      // on A4. Declared before the paginated read below so both derive
      // from one check.
      const paginatedNow = this.querySelector(':scope > .page') !== null;
      const sizeDescriptor = this._trueSizePx() ? 'size: ' + this.pageWidth + ' ' + this.pageHeight + '; ' : this._contentFit() ? 'size: ' + this.pageWidth + ' ' + this.pageHeight + '; ' : paginatedNow ? 'size: ' + this.pageWidth + ' ' + this.pageHeight + '; ' : landscape ? 'size: landscape; ' : '';
      // WebKit never repeats the thead/tfoot spacers that carry a flowing
      // document's vertical page margins (see WK_PRINT above), so pages
      // after the first print edge-to-edge there. Carry the VERTICAL
      // margins on @page for WebKit instead, and the shadow print CSS
      // trims the first-page spacers by the same amount (.sheet.wk-print
      // rules). Horizontal inset stays on the sheet's own padding in
      // every engine. Blink keeps margin: 0 (a nonzero margin there
      // re-opens the box Chrome draws its header furniture in). One cost,
      // learned in testing: Safari's own date/URL headers are a USER
      // dialog setting ("Print headers and footers") that renders in the
      // margin area when room exists — margin: 0 only suppressed it by
      // leaving no room, and no CSS controls it. The export dialog's
      // Safari guide teaches turning the setting off for flowing
      // documents. Explicitly paginated and fixed-size documents keep
      // margin: 0 everywhere: their pages ARE the sheet.
      const wkFlowing = WK_PRINT && !paginatedNow && !this._trueSizePx() && !this._contentFit();
      const marginDescriptor = wkFlowing ? 'margin: ' + this.pageMargin + ' 0; ' : 'margin: 0; ';
      // Shadow-internal marker (never serialized), kept in lockstep with
      // the @page decision above: the print CSS trims the first-page
      // spacers ONLY while @page actually carries the margins — a
      // true-size or scaled-fit sheet keeps margin: 0 and must keep its
      // spacers too. Re-synced here so attribute changes and pagination
      // flips move both together.
      if (this._sheet) this._sheet.classList.toggle('wk-print', wkFlowing);
      tag.textContent = '@page { ' + sizeDescriptor + marginDescriptor + '} ' + '@media print { html, body { margin: 0 !important; padding: 0 !important; background: none !important; height: auto !important; overflow: visible !important; } ' + 'h1,h2,h3,h4,h5,h6 { break-after: avoid; } ' + 'figure,pre,blockquote,img,svg,tr { break-inside: avoid; } ' + 'p,li { orphans: 3; widows: 3; } ' + '* { -webkit-print-color-adjust: exact; print-color-adjust: exact; ' + 'backdrop-filter: none !important; -webkit-backdrop-filter: none !important; } ' + '*, *::before, *::after { animation-delay: -99s !important; animation-duration: .001s !important; ' + 'animation-iteration-count: 1 !important; animation-fill-mode: both !important; ' + 'animation-play-state: running !important; transition-duration: 0s !important; } }';
    }

    /** Typographic defaults for document text: balance headings, avoid
     *  widowed/orphaned words in body copy (browsers without text-wrap
     *  support drop the declarations). Zero-specificity via :where() so
     *  any text-wrap authored on those elements wins; document-level so the
     *  rules reach the slotted (light DOM) content — shadow styles can't.
     *  data-omelette-injected marks the tag for the host editor to strip
     *  at serialize, so it is never written back as authored source. */
    _ensureTextWrapDefaults() {
      if (document.getElementById('doc-page-text-wrap')) return;
      const tag = document.createElement('style');
      tag.id = 'doc-page-text-wrap';
      tag.setAttribute('data-omelette-injected', '');
      tag.textContent = ':where(h1,h2,h3,h4,h5,h6){text-wrap:balance}' + ':where(p,li,blockquote,figcaption){text-wrap:pretty}';
      document.head.appendChild(tag);
    }

    /** Declares that this document owns its print CSS. The instant-PDF
     *  export checks for the meta by NAME PRESENCE alone (content is
     *  ignored) and skips its automatic print-CSS injections, so the
     *  component's @page geometry is never overridden by a heuristic.
     *  data-omelette-injected keeps it out of serialized source. */
    _ensureOwnsPrintMeta() {
      if (document.getElementById('doc-page-owns-print')) return;
      const tag = document.createElement('meta');
      tag.id = 'doc-page-owns-print';
      tag.name = 'omelette-owns-print';
      tag.content = 'true';
      tag.setAttribute('data-omelette-injected', '');
      document.head.appendChild(tag);
    }

    /** This page's valid true-size page box (explicit width AND height)
     *  as [w, h] px ints, or null when the mode is off. */
    _trueSizePx() {
      if (!safeLen(this.getAttribute('width'), null) || !safeLen(this.getAttribute('height'), null)) return null;
      const w = Math.round(toPx(this.pageWidth));
      const h = Math.round(toPx(this.pageHeight));
      return w > 0 && h > 0 ? [w, h] : null;
    }

    /** True-size pages (explicit width AND height) also declare the page
     *  box as the preview size: the in-app preview reads
     *  meta[name="omelette-fixed-size"] (content "W,H" in px ints) and
     *  scales the sheet into view — without it an 18in poster previews at
     *  true size with scrollbars. Never overrides an author-set meta
     *  (only the component's own id is managed). The meta is page-global
     *  while doc-page instances are not, so every sync recomputes the
     *  page-wide owner — the first connected true-size doc-page — and a
     *  non-true-size sibling's sync can never delete the owner's meta.
     *  Removed when no true-size page remains (the owner's disconnect
     *  re-syncs via any survivor) or when an author-set meta exists. */
    _syncFixedSizeMeta() {
      const id = 'doc-page-fixed-size';
      const own = document.getElementById(id);
      const authored = document.querySelector('meta[name="omelette-fixed-size"]:not([data-omelette-injected])');
      // The page-wide owner, not this instance: an upgraded true-size page
      // anywhere in the document keeps the meta alive and sized.
      let box = null;
      for (const el of document.querySelectorAll('doc-page')) {
        box = typeof el._trueSizePx === 'function' ? el._trueSizePx() : null;
        if (box) break;
      }
      if (!box || authored) {
        if (own) own.remove();
        return;
      }
      const tag = own || document.createElement('meta');
      tag.id = id;
      tag.name = 'omelette-fixed-size';
      tag.content = box[0] + ',' + box[1];
      tag.setAttribute('data-omelette-injected', '');
      if (!own) document.head.appendChild(tag);
    }

    /** This page's print-sizing mode: 'fixed' when an explicit width AND
     *  height are authored (the page is the design's own size), else the
     *  default paper in the authored orientation. */
    _printSizingMode() {
      if (this._trueSizePx()) return 'fixed';
      const landscape = (this.getAttribute('orientation') || '').trim().toLowerCase() === 'landscape';
      return landscape ? 'default-landscape' : 'default-portrait';
    }

    /** Announces the print-sizing mode to the host app:
     *  meta[name="omelette-print-sizing"] with content 'default-portrait',
     *  'default-landscape', or 'fixed' (fixed pages also carry the
     *  omelette-fixed-size meta with the page box in px). The export path
     *  probes it to decide what true paper size to inject at print time —
     *  in the default modes the component emits no paper size of its own.
     *  Same page-global ownership rules as the fixed-size meta above:
     *  first connected doc-page owns it, an authored meta is never
     *  overridden, removed when no doc-page remains. */
    _syncPrintSizingMeta() {
      const id = 'doc-page-print-sizing';
      const own = document.getElementById(id);
      const authored = document.querySelector('meta[name="omelette-print-sizing"]:not([data-omelette-injected])');
      // A fixed page wins outright (mirroring the fixed-size loop above,
      // so the two metas can never contradict each other in a mixed
      // multi-page document); otherwise the first page's mode holds.
      let mode = null;
      for (const el of document.querySelectorAll('doc-page')) {
        if (typeof el._printSizingMode !== 'function') continue;
        const m = el._printSizingMode();
        if (m === 'fixed') {
          mode = m;
          break;
        }
        if (mode === null) mode = m;
      }
      if (!mode || authored) {
        if (own) own.remove();
        return;
      }
      // A deck-stage that connected first injected its own meta and
      // defers to any existing one — take it over, or the document ends
      // up with two conflicting injected metas (a doc-page page is the
      // document; the deck re-ensures its meta if every doc-page leaves).
      const deckMeta = document.getElementById('deck-stage-print-sizing');
      if (deckMeta) deckMeta.remove();
      const tag = own || document.createElement('meta');
      tag.id = id;
      tag.name = 'omelette-print-sizing';
      tag.content = mode;
      tag.setAttribute('data-omelette-injected', '');
      if (!own) document.head.appendChild(tag);
    }
    _scheduleMeasure() {
      if (this._raf) return;
      this._raf = requestAnimationFrame(() => {
        this._raf = null;
        this._measure();
      });
    }

    /** Slot heights feed the print spacers (--doc-hdr-h / --doc-ftr-h), so
     *  they re-measure on content mutation, resize, and font load. The
     *  same pass detects explicit pagination (direct .page children) and
     *  toggles the sheet between the flowing-document card and the
     *  page-per-card stack — content edits can add or remove pages at any
     *  time, so this tracks the same mutations the measurement does. */
    _measure() {
      const hdr = this.querySelector(':scope > [slot="header"]');
      const ftr = this.querySelector(':scope > [slot="footer"]');
      const wasPaginated = this._sheet.classList.contains('paginated');
      this._sheet.classList.toggle('paginated', this.querySelector(':scope > .page') !== null);
      // The WebKit @page margin is flowing-only, so a pagination flip
      // must re-emit the rule (content edits can add or remove .page
      // sections at any time).
      if (this._sheet.classList.contains('paginated') !== wasPaginated) {
        this._syncPrintPageRule();
      }
      this._syncSize(hdr ? hdr.offsetHeight : 0, ftr ? ftr.offsetHeight : 0);
    }
  }
  if (!customElements.get('doc-page')) {
    customElements.define('doc-page', DocPage);
  }
})();
})(); } catch (e) { __ds_ns.__errors.push({ path: "doc-page.js", error: String((e && e.message) || e) }); }

// ui_kits/app/AppShell.jsx
try { (() => {
const {
  useState
} = React;
const hair = pct => `1px solid color-mix(in srgb, var(--color-text) ${pct}%, transparent)`;

/** Login screen. Centered card on the theme background; no imagery. */
function LoginScreen({
  shape = 'corporate',
  onSubmit
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      background: 'var(--color-bg)',
      color: 'var(--color-text)',
      fontFamily: 'var(--font-body)',
      minHeight: '100%',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: 'var(--space-4)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: 340,
      display: 'flex',
      flexDirection: 'column',
      gap: 'var(--space-2)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-heading)',
      fontWeight: 'var(--fw-heading)',
      fontSize: 'var(--fs-h3)',
      lineHeight: 'var(--lh-heading)'
    }
  }, "Sign in"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 'var(--fs-caption)',
      color: 'var(--color-muted)'
    }
  }, "Use your workspace account."), /*#__PURE__*/React.createElement(Field, {
    shape: shape,
    label: "Email",
    value: "ops@ledgerline.io"
  }), /*#__PURE__*/React.createElement(Field, {
    shape: shape,
    label: "Password",
    value: "\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022"
  }), /*#__PURE__*/React.createElement(__ds_scope.Button, {
    shape: shape,
    variant: "primary",
    onClick: onSubmit
  }, "Continue"), /*#__PURE__*/React.createElement(__ds_scope.Button, {
    shape: shape,
    variant: "ghost"
  }, "Use single sign-on")));
}
function Field({
  label,
  value,
  shape,
  error
}) {
  return /*#__PURE__*/React.createElement("label", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 5
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 'var(--fs-caption)',
      color: 'var(--color-muted)'
    }
  }, label), /*#__PURE__*/React.createElement("input", {
    defaultValue: value,
    style: {
      fontFamily: 'var(--font-body)',
      fontSize: 'var(--fs-body)',
      padding: '9px 11px',
      color: 'var(--color-text)',
      background: 'var(--input-bg)',
      border: `1px solid var(${error ? '--input-border-error' : '--input-border'})`,
      borderRadius: shape === 'flat' ? 0 : 'var(--radius-sm)',
      outline: 'none'
    }
  }));
}
const NAV = ['Overview', 'Members', 'Billing', 'Settings'];

/** App shell: sidebar nav + top bar + routed body. The Web/App UI surface. */
function AppShell({
  shape = 'corporate'
}) {
  const [route, setRoute] = useState('Members');
  const flat = shape === 'flat';
  const pill = shape === 'pill' || shape === 'glass';
  return /*#__PURE__*/React.createElement("div", {
    style: {
      background: 'var(--color-bg)',
      color: 'var(--color-text)',
      fontFamily: 'var(--font-body)',
      minHeight: '100%',
      display: 'flex'
    }
  }, /*#__PURE__*/React.createElement("nav", {
    style: {
      flex: '0 0 208px',
      borderRight: hair(10),
      padding: 'var(--space-3)',
      display: 'flex',
      flexDirection: 'column',
      gap: 'var(--space-3)',
      background: flat ? 'transparent' : 'var(--color-surface)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 8
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: 18,
      height: 18,
      background: 'var(--color-accent)',
      borderRadius: pill ? 999 : 'var(--radius-sm)'
    }
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-heading)',
      fontWeight: 'var(--fw-heading)',
      fontSize: 13
    }
  }, "Ledgerline")), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 2
    }
  }, NAV.map(n => /*#__PURE__*/React.createElement("button", {
    key: n,
    onClick: () => setRoute(n),
    style: {
      textAlign: 'left',
      fontFamily: 'var(--font-body)',
      fontSize: 13,
      fontWeight: route === n ? 600 : 400,
      padding: '9px 10px',
      border: 'none',
      cursor: 'pointer',
      borderRadius: flat ? 0 : 'var(--radius-sm)',
      background: route === n ? 'var(--color-primary-soft)' : 'transparent',
      color: route === n ? 'var(--color-accent)' : 'var(--color-muted)'
    }
  }, n))), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 'auto'
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.StatusBadge, {
    shape: shape,
    status: "success",
    label: "Synced"
  }))), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      minWidth: 0
    }
  }, /*#__PURE__*/React.createElement("header", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 'var(--space-2)',
      padding: 'var(--space-3)',
      borderBottom: hair(10)
    }
  }, /*#__PURE__*/React.createElement("h1", {
    style: {
      margin: 0,
      marginRight: 'auto',
      fontFamily: 'var(--font-heading)',
      fontWeight: 'var(--fw-heading)',
      fontSize: 'var(--fs-h3)',
      lineHeight: 'var(--lh-heading)'
    }
  }, route), /*#__PURE__*/React.createElement(__ds_scope.Tag, {
    shape: shape,
    tone: "neutral"
  }, "Workspace: Finance"), /*#__PURE__*/React.createElement(__ds_scope.Button, {
    shape: shape,
    variant: "secondary"
  }, "Invite")), /*#__PURE__*/React.createElement("div", {
    style: {
      padding: 'var(--space-3)',
      display: 'flex',
      flexDirection: 'column',
      gap: 'var(--gap-grid)'
    }
  }, route === 'Settings' ? /*#__PURE__*/React.createElement(SettingsPanel, {
    shape: shape
  }) : /*#__PURE__*/React.createElement(MembersPanel, {
    shape: shape
  }))));
}
function MembersPanel({
  shape
}) {
  return /*#__PURE__*/React.createElement(__ds_scope.DataTable, {
    shape: shape,
    pageInfo: "1\u20135 of 42",
    columns: ['Member', 'Role', 'Last active', 'State'],
    rows: [['Ana Petrov', 'Admin', '2 min ago', 'Active'], ['Devon Hale', 'Analyst', '1 h ago', 'Active'], ['Mira Osei', 'Analyst', 'Yesterday', 'Active'], ['Sam Trent', 'Viewer', '6 d ago', 'Idle'], ['Jo Whitfield', 'Viewer', '—', 'Invited']]
  });
}

/** Settings screen with toggle rows — the third Web/App surface. */
function SettingsPanel({
  shape = 'corporate'
}) {
  const [on, setOn] = useState({
    digest: true,
    alerts: true,
    beta: false
  });
  const Row = ({
    k,
    label,
    help
  }) => /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 16,
      padding: '12px 0',
      borderBottom: hair(8)
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 13,
      fontWeight: 500
    }
  }, label), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 'var(--fs-caption)',
      color: 'var(--color-muted)'
    }
  }, help)), /*#__PURE__*/React.createElement("button", {
    onClick: () => setOn(s => ({
      ...s,
      [k]: !s[k]
    })),
    "aria-pressed": on[k],
    style: {
      width: 38,
      height: 21,
      padding: 2,
      border: 'none',
      cursor: 'pointer',
      borderRadius: 999,
      background: on[k] ? 'var(--color-accent)' : 'var(--color-disabled-bg)',
      display: 'flex',
      justifyContent: on[k] ? 'flex-end' : 'flex-start'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      width: 17,
      height: 17,
      borderRadius: 999,
      background: 'var(--color-bg)'
    }
  })));
  return /*#__PURE__*/React.createElement(__ds_scope.Card, {
    shape: shape,
    kicker: "Notifications",
    title: "Delivery preferences"
  }, /*#__PURE__*/React.createElement(Row, {
    k: "digest",
    label: "Weekly digest",
    help: "Sent Mondays, 07:00 UTC."
  }), /*#__PURE__*/React.createElement(Row, {
    k: "alerts",
    label: "Threshold alerts",
    help: "Fires when an account crosses its credit cap."
  }), /*#__PURE__*/React.createElement(Row, {
    k: "beta",
    label: "Preview features",
    help: "Unreleased report layouts."
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 8,
      marginTop: 'var(--space-2)'
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Button, {
    shape: shape,
    variant: "primary"
  }, "Save changes"), /*#__PURE__*/React.createElement(__ds_scope.Button, {
    shape: shape,
    variant: "ghost"
  }, "Reset")));
}
Object.assign(__ds_scope, { LoginScreen, AppShell, SettingsPanel });
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/app/AppShell.jsx", error: String((e && e.message) || e) }); }

// ui_kits/dashboard/Dashboard.jsx
try { (() => {
/**
 * Full dashboard screen recreation, composed entirely from the shared
 * component set. Pass `shape` matching the active theme's --shape token
 * (see readme.md's theme table) and wrap this in an element carrying
 * data-theme="<theme-name>".
 */
function Dashboard({
  shape = 'pill'
}) {
  const chartData = [{
    label: 'Jan',
    values: [68, 52, 40]
  }, {
    label: 'Feb',
    values: [84, 61, 45]
  }, {
    label: 'Mar',
    values: [55, 48, 38]
  }, {
    label: 'Apr',
    values: [91, 70, 52]
  }, {
    label: 'May',
    values: [73, 58, 44]
  }];
  return /*#__PURE__*/React.createElement("div", {
    style: {
      background: 'var(--color-bg)',
      color: 'var(--color-text)',
      fontFamily: 'var(--font-body)',
      padding: 32,
      minHeight: '100%'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 16,
      marginBottom: 24
    }
  }, /*#__PURE__*/React.createElement("h1", {
    style: {
      fontFamily: 'var(--font-heading)',
      fontWeight: 700,
      fontSize: 24,
      margin: 0,
      marginRight: 'auto'
    }
  }, "Analytics Dashboard"), /*#__PURE__*/React.createElement(__ds_scope.Tag, {
    shape: shape
  }, "Q2 2026"), /*#__PURE__*/React.createElement(__ds_scope.Button, {
    shape: shape,
    variant: "primary"
  }, "Export Report")), /*#__PURE__*/React.createElement(__ds_scope.FilterBar, {
    shape: shape
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'grid',
      gridTemplateColumns: 'repeat(4, 1fr)',
      gap: 16,
      marginBottom: 24
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.KpiCard, {
    label: "Revenue",
    value: "$2.4M",
    delta: 12.4,
    trend: [40, 52, 48, 61, 58, 70, 68, 75],
    shape: shape,
    accentColor: "var(--color-series-1)"
  }), /*#__PURE__*/React.createElement(__ds_scope.KpiCard, {
    label: "Active Users",
    value: "18.2K",
    delta: 8.1,
    trend: [30, 34, 33, 40, 44, 46, 50, 55],
    shape: shape,
    accentColor: "var(--color-series-2)"
  }), /*#__PURE__*/React.createElement(__ds_scope.KpiCard, {
    label: "Completion",
    value: "94.3%",
    delta: 2.0,
    trend: [80, 82, 85, 88, 90, 91, 93, 94],
    shape: shape,
    accentColor: "var(--color-series-3)"
  }), /*#__PURE__*/React.createElement(__ds_scope.KpiCard, {
    label: "Churn Risk",
    value: "3.1%",
    delta: -0.4,
    deltaLabel: "vs target",
    trend: [6, 5.5, 5, 4.6, 4, 3.6, 3.3, 3.1],
    shape: shape,
    accentColor: "var(--color-alert)"
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      background: shape === 'flat' ? 'transparent' : 'var(--color-surface)',
      border: shape === 'flat' ? 'none' : '1px solid color-mix(in srgb, var(--color-text) 10%, transparent)',
      borderTop: shape === 'flat' ? '1px solid color-mix(in srgb, var(--color-text) 15%, transparent)' : undefined,
      borderRadius: shape === 'flat' ? 0 : 'var(--radius-md)',
      padding: 16,
      marginBottom: 24
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 11,
      color: 'var(--color-muted)',
      marginBottom: 10,
      fontFamily: 'var(--font-heading)',
      fontWeight: 600
    }
  }, "Monthly Performance \u2014 Series 1 \xB7 2 \xB7 3"), /*#__PURE__*/React.createElement(__ds_scope.ChartSeries, {
    data: chartData
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 8,
      marginBottom: 20,
      flexWrap: 'wrap'
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.StatusBadge, {
    status: "success",
    label: "Systems Nominal",
    shape: shape
  }), /*#__PURE__*/React.createElement(__ds_scope.StatusBadge, {
    status: "warning",
    label: "2 Metrics Near Threshold",
    shape: shape
  }), /*#__PURE__*/React.createElement(__ds_scope.StatusBadge, {
    status: "alert",
    label: "1 Critical Alert",
    shape: shape
  })), /*#__PURE__*/React.createElement(__ds_scope.DataTable, {
    shape: shape,
    columns: ['Segment', 'Revenue', 'Users', 'Trend'],
    rows: [['Enterprise', '$1.2M', '4,204', '▲ 12%'], ['Mid-Market', '$820K', '8,910', '▲ 6%'], ['SMB', '$380K', '5,086', '▼ 2%']],
    pageInfo: "Page 1 of 4"
  }));
}
Object.assign(__ds_scope, { Dashboard });
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/dashboard/Dashboard.jsx", error: String((e && e.message) || e) }); }

// ui_kits/deck/Slides.jsx
try { (() => {
const slideBase = {
  width: 960,
  height: 540,
  padding: 56,
  display: 'flex',
  flexDirection: 'column',
  boxSizing: 'border-box',
  fontFamily: 'var(--font-body)',
  background: 'var(--color-bg)',
  color: 'var(--color-text)'
};
function ExecutiveSummarySlide({
  shape = 'pill'
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: slideBase
  }, /*#__PURE__*/React.createElement(__ds_scope.Tag, {
    shape: shape,
    tone: "outline"
  }, "Executive Summary"), /*#__PURE__*/React.createElement("h1", {
    style: {
      fontFamily: 'var(--font-heading)',
      fontWeight: 700,
      fontSize: 32,
      margin: '12px 0 24px'
    }
  }, "Q2 Performance Overview"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'grid',
      gridTemplateColumns: 'repeat(3, 1fr)',
      gap: 20,
      marginBottom: 24
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.KpiCard, {
    label: "Revenue",
    value: "$2.4M",
    delta: 12.4,
    shape: shape,
    accentColor: "var(--color-series-1)"
  }), /*#__PURE__*/React.createElement(__ds_scope.KpiCard, {
    label: "Active Users",
    value: "18.2K",
    delta: 8.1,
    shape: shape,
    accentColor: "var(--color-series-2)"
  }), /*#__PURE__*/React.createElement(__ds_scope.KpiCard, {
    label: "Completion",
    value: "94.3%",
    delta: 2.0,
    shape: shape,
    accentColor: "var(--color-series-3)"
  })), /*#__PURE__*/React.createElement("p", {
    style: {
      fontSize: 15,
      lineHeight: 1.6,
      color: 'var(--color-muted)',
      maxWidth: 640
    }
  }, "Revenue and completion both beat target this quarter; churn risk remains the one metric to watch."));
}
function BigStatSlide({
  shape = 'pill'
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      ...slideBase,
      justifyContent: 'center',
      alignItems: 'center',
      textAlign: 'center'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-heading)',
      fontSize: 13,
      letterSpacing: '.12em',
      textTransform: 'uppercase',
      color: 'var(--color-accent)',
      marginBottom: 16
    }
  }, "Retention Rate"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-heading)',
      fontWeight: 700,
      fontSize: 120,
      lineHeight: 1,
      color: 'var(--color-text)'
    }
  }, "222.5%"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 16,
      color: 'var(--color-success)',
      marginTop: 16
    }
  }, "\u25B2 Target exceeded \u2014 highest in company history"));
}
function InsightVsDataSlide({
  shape = 'pill'
}) {
  const chartData = [{
    label: 'Jan',
    values: [68, 52]
  }, {
    label: 'Feb',
    values: [84, 61]
  }, {
    label: 'Mar',
    values: [55, 48]
  }, {
    label: 'Apr',
    values: [91, 70]
  }, {
    label: 'May',
    values: [73, 58]
  }];
  return /*#__PURE__*/React.createElement("div", {
    style: {
      ...slideBase,
      flexDirection: 'row',
      gap: 40
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1.4
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-heading)',
      fontSize: 13,
      letterSpacing: '.1em',
      textTransform: 'uppercase',
      color: 'var(--color-accent)',
      marginBottom: 12
    }
  }, "Data"), /*#__PURE__*/React.createElement(__ds_scope.ChartSeries, {
    data: chartData,
    width: 480,
    height: 220
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      display: 'flex',
      flexDirection: 'column',
      gap: 14,
      justifyContent: 'center'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-heading)',
      fontSize: 13,
      letterSpacing: '.1em',
      textTransform: 'uppercase',
      color: 'var(--color-accent)',
      marginBottom: 4
    }
  }, "Insight"), ['Growth accelerated in April, +91% peak', 'Series 2 lags but is closing the gap', 'Recommend reallocating budget to April’s driver channel'].map((t, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    style: {
      display: 'flex',
      gap: 10,
      alignItems: 'flex-start'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      color: 'var(--color-accent)',
      fontFamily: 'var(--font-heading)',
      fontWeight: 700
    }
  }, "0", i + 1), /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 15,
      lineHeight: 1.5
    }
  }, t)))));
}
Object.assign(__ds_scope, { ExecutiveSummarySlide, BigStatSlide, InsightVsDataSlide });
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/deck/Slides.jsx", error: String((e && e.message) || e) }); }

// ui_kits/webapp/Shell.jsx
try { (() => {
const NAV = [['Overview', 'M3 3h6v6H3zM11 3h6v6h-6zM3 11h6v6H3zM11 11h6v6h-6z'], ['Reports', 'M4 3h9l3 3v11H4zM12 3v4h4'], ['Segments', 'M10 2a8 8 0 108 8h-8z'], ['Alerts', 'M10 3a5 5 0 00-5 5v3l-2 3h14l-2-3V8a5 5 0 00-5-5zM8 16a2 2 0 004 0'], ['Settings', 'M10 7a3 3 0 100 6 3 3 0 000-6zM10 2v2M10 16v2M2 10h2M16 10h2M4.5 4.5l1.5 1.5M14 14l1.5 1.5M15.5 4.5L14 6M6 14l-1.5 1.5']];
function Icon({
  d,
  size = 16,
  color = 'currentColor'
}) {
  return /*#__PURE__*/React.createElement("svg", {
    width: size,
    height: size,
    viewBox: "0 0 20 20",
    fill: "none",
    stroke: color,
    strokeWidth: "1.5",
    strokeLinecap: "round",
    strokeLinejoin: "round",
    style: {
      display: 'block',
      flex: 'none'
    }
  }, /*#__PURE__*/React.createElement("path", {
    d: d
  }));
}
function Sidebar({
  active,
  onNavigate,
  radius
}) {
  return /*#__PURE__*/React.createElement("aside", {
    style: {
      width: 216,
      flex: 'none',
      background: 'var(--color-surface)',
      borderRight: '1px solid color-mix(in srgb, var(--color-text) 10%, transparent)',
      padding: 'var(--space-2)',
      display: 'flex',
      flexDirection: 'column',
      gap: 'var(--space-2)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 10,
      padding: '6px 8px'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: 22,
      height: 22,
      borderRadius: radius,
      background: 'var(--color-accent)',
      flex: 'none'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-heading)',
      fontWeight: 700,
      fontSize: 14,
      letterSpacing: '-.01em'
    }
  }, "Multi\u2011Theme")), /*#__PURE__*/React.createElement("nav", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 2
    }
  }, NAV.map(([label, d]) => {
    const on = label === active;
    return /*#__PURE__*/React.createElement("button", {
      key: label,
      onClick: () => onNavigate(label),
      style: {
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        padding: '8px 10px',
        borderRadius: radius,
        border: '1px solid transparent',
        cursor: 'pointer',
        textAlign: 'left',
        background: on ? 'var(--color-primary-soft)' : 'transparent',
        color: on ? 'var(--color-accent)' : 'var(--color-muted)',
        fontFamily: 'var(--font-body)',
        fontSize: 13,
        fontWeight: on ? 600 : 400
      }
    }, /*#__PURE__*/React.createElement(Icon, {
      d: d
    }), label);
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 'auto',
      padding: '10px',
      borderTop: '1px solid color-mix(in srgb, var(--color-text) 10%, transparent)',
      display: 'flex',
      alignItems: 'center',
      gap: 10
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: 26,
      height: 26,
      borderRadius: '50%',
      background: 'var(--color-series-3)',
      flex: 'none'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      minWidth: 0
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 12,
      fontWeight: 600
    }
  }, "Rae Okonjo"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 10,
      color: 'var(--color-muted)'
    }
  }, "Analytics Lead"))));
}
function TopBar({
  title,
  themeSlug,
  onTheme,
  radius
}) {
  return /*#__PURE__*/React.createElement("header", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 'var(--space-2)',
      padding: 'var(--space-2) var(--space-3)',
      borderBottom: '1px solid color-mix(in srgb, var(--color-text) 10%, transparent)'
    }
  }, /*#__PURE__*/React.createElement("h1", {
    style: {
      margin: 0,
      marginRight: 'auto',
      fontFamily: 'var(--font-heading)',
      fontWeight: 'var(--fw-heading)',
      fontSize: 'var(--fs-h3)',
      lineHeight: 'var(--lh-heading)'
    }
  }, title), /*#__PURE__*/React.createElement("select", {
    value: themeSlug,
    onChange: e => onTheme(e.target.value),
    style: {
      fontFamily: 'var(--font-body)',
      fontSize: 12,
      padding: '6px 10px',
      borderRadius: radius,
      background: 'var(--input-bg)',
      color: 'var(--color-text)',
      border: '1px solid var(--input-border)',
      cursor: 'pointer'
    }
  }, THEMES.map(t => /*#__PURE__*/React.createElement("option", {
    key: t.slug,
    value: t.slug
  }, t.name))), /*#__PURE__*/React.createElement(Button, {
    shape: SHAPE_OF[themeSlug],
    variant: "primary"
  }, "Export"));
}
Object.assign(window, {
  Icon,
  Sidebar,
  TopBar,
  NAV
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/webapp/Shell.jsx", error: String((e && e.message) || e) }); }

__ds_ns.Button = __ds_scope.Button;

__ds_ns.Card = __ds_scope.Card;

__ds_ns.StatusBadge = __ds_scope.StatusBadge;

__ds_ns.Tag = __ds_scope.Tag;

__ds_ns.ChartSeries = __ds_scope.ChartSeries;

__ds_ns.DataTable = __ds_scope.DataTable;

__ds_ns.FilterBar = __ds_scope.FilterBar;

__ds_ns.KpiCard = __ds_scope.KpiCard;

__ds_ns.GlassPanel = __ds_scope.GlassPanel;

__ds_ns.TabBar = __ds_scope.TabBar;

__ds_ns.WindowChrome = __ds_scope.WindowChrome;

__ds_ns.LoginScreen = __ds_scope.LoginScreen;

__ds_ns.AppShell = __ds_scope.AppShell;

__ds_ns.SettingsPanel = __ds_scope.SettingsPanel;

__ds_ns.Dashboard = __ds_scope.Dashboard;

__ds_ns.ExecutiveSummarySlide = __ds_scope.ExecutiveSummarySlide;

__ds_ns.BigStatSlide = __ds_scope.BigStatSlide;

__ds_ns.InsightVsDataSlide = __ds_scope.InsightVsDataSlide;

})();
