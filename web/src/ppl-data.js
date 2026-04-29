// ppl-data.js — Asset universe, mock calculations, and FIRE engine
// Asset pool aligned with src/processing/screening.py (35 assets)

const PPL_BLUE6 = ['#d2e4f5','#a8cae8','#72a8d4','#4182b9','#1e5a96','#0a326e'];

// ── Asset Universe (35 assets — matches screening.py ASSET_POOL) ──────────────
const PPL_ASSETS = [
  // Taiwan ETFs
  { ticker:'0050.TW',    name:'Yuanta Taiwan 50 ETF',                    category:'TW_ETF', subcategory:'Market-Cap',            currency:'TWD', aumNote:'approx. TWD 1,661.5B', cagr:10.2, vol:19.8, maxDD:-46.3, sharpe:0.71, worstYear:-43.0, worstYearLabel:2008 },
  { ticker:'0056.TW',    name:'Yuanta High Dividend ETF',                 category:'TW_ETF', subcategory:'High Dividend',          currency:'TWD', aumNote:'approx. TWD 584.1B',   cagr:7.1,  vol:15.3, maxDD:-40.1, sharpe:0.62, worstYear:-38.2, worstYearLabel:2008 },
  { ticker:'00878.TW',   name:'Cathay Sustainable High Dividend ETF',     category:'TW_ETF', subcategory:'High Dividend / ESG',    currency:'TWD', aumNote:'approx. TWD 485.4B',   cagr:8.4,  vol:14.1, maxDD:-32.5, sharpe:0.74, worstYear:-30.1, worstYearLabel:2022 },
  { ticker:'00919.TW',   name:'Group Benefits Taiwan Select HY ETF',      category:'TW_ETF', subcategory:'High Dividend',          currency:'TWD', aumNote:'approx. TWD 451.8B',   cagr:9.1,  vol:16.2, maxDD:-35.4, sharpe:0.76, worstYear:-33.2, worstYearLabel:2022 },
  { ticker:'006208.TW',  name:'Fubon Taiwan 50 ETF',                      category:'TW_ETF', subcategory:'Market-Cap',            currency:'TWD', aumNote:'approx. TWD 389.4B',   cagr:10.1, vol:19.5, maxDD:-45.8, sharpe:0.70, worstYear:-42.5, worstYearLabel:2008 },
  { ticker:'00937B.TWO', name:'Group Benefits ESG IG Bond 20+ ETF',       category:'TW_ETF', subcategory:'Bond',                  currency:'TWD', aumNote:'approx. TWD 267.9B',   cagr:3.8,  vol:9.2,  maxDD:-22.1, sharpe:0.48, worstYear:-18.4, worstYearLabel:2022 },
  { ticker:'00679B.TWO', name:'Yuanta US Treasury 20+ Year ETF',          category:'TW_ETF', subcategory:'Bond',                  currency:'TWD', aumNote:'approx. TWD 203.7B',   cagr:2.9,  vol:11.4, maxDD:-35.2, sharpe:0.34, worstYear:-24.8, worstYearLabel:2022 },
  { ticker:'00751B.TWO', name:'Yuanta AAA-A Corporate Bond ETF',          category:'TW_ETF', subcategory:'Bond',                  currency:'TWD', aumNote:'approx. TWD 180.0B',   cagr:3.2,  vol:7.8,  maxDD:-18.6, sharpe:0.45, worstYear:-14.2, worstYearLabel:2022 },
  { ticker:'0052.TW',    name:'Fubon Technology ETF',                     category:'TW_ETF', subcategory:'Technology Theme',      currency:'TWD', aumNote:'approx. TWD 132.0B',   cagr:13.4, vol:22.1, maxDD:-48.2, sharpe:0.74, worstYear:-45.1, worstYearLabel:2008 },
  { ticker:'00929.TW',   name:'Fuh Hwa Taiwan Tech High Yield ETF',       category:'TW_ETF', subcategory:'Tech High Dividend',    currency:'TWD', aumNote:'approx. TWD 115.2B',   cagr:10.8, vol:18.4, maxDD:-36.2, sharpe:0.72, worstYear:-33.4, worstYearLabel:2022 },
  { ticker:'00713.TW',   name:'Yuanta Taiwan High Dividend Low Vol ETF',  category:'TW_ETF', subcategory:'High Dividend Low Vol', currency:'TWD', aumNote:'approx. TWD 113.0B',   cagr:6.8,  vol:12.4, maxDD:-28.3, sharpe:0.68, worstYear:-26.0, worstYearLabel:2022 },
  { ticker:'00952.TW',   name:'KGI Taiwan AI 50 ETF',                     category:'TW_ETF', subcategory:'AI Theme',             currency:'TWD', aumNote:'approx. TWD 60.0B',    cagr:14.2, vol:23.8, maxDD:-38.5, sharpe:0.75, worstYear:-35.2, worstYearLabel:2022 },
  // US ETFs
  { ticker:'VOO',   name:'Vanguard S&P 500 ETF',                   category:'US_ETF', subcategory:'US Large-Cap Blend',      currency:'USD', aumNote:'approx. USD 827.0B',  cagr:13.8, vol:17.2, maxDD:-33.7, sharpe:0.95, worstYear:-18.2, worstYearLabel:2022 },
  { ticker:'IVV',   name:'iShares Core S&P 500 ETF',               category:'US_ETF', subcategory:'US Large-Cap Blend',      currency:'USD', aumNote:'approx. USD 766.0B',  cagr:13.7, vol:17.1, maxDD:-33.5, sharpe:0.94, worstYear:-18.1, worstYearLabel:2022 },
  { ticker:'SPY',   name:'SPDR S&P 500 ETF Trust',                 category:'US_ETF', subcategory:'US Large-Cap Blend',      currency:'USD', aumNote:'approx. USD 672.0B',  cagr:13.6, vol:17.3, maxDD:-33.8, sharpe:0.93, worstYear:-18.2, worstYearLabel:2022 },
  { ticker:'VTI',   name:'Vanguard Total Stock Market ETF',        category:'US_ETF', subcategory:'US Total Market',         currency:'USD', aumNote:'approx. USD 586.0B',  cagr:13.2, vol:17.5, maxDD:-34.9, sharpe:0.91, worstYear:-19.5, worstYearLabel:2022 },
  { ticker:'QQQ',   name:'Invesco QQQ Trust',                      category:'US_ETF', subcategory:'US Technology Growth',    currency:'USD', aumNote:'approx. USD 400.0B',  cagr:18.6, vol:23.1, maxDD:-49.7, sharpe:0.97, worstYear:-32.6, worstYearLabel:2022 },
  { ticker:'VUG',   name:'Vanguard Growth ETF',                    category:'US_ETF', subcategory:'US Growth',               currency:'USD', aumNote:'approx. USD 207.4B',  cagr:15.1, vol:20.8, maxDD:-38.4, sharpe:0.88, worstYear:-33.2, worstYearLabel:2022 },
  { ticker:'VEA',   name:'Vanguard FTSE Developed Markets ETF',    category:'US_ETF', subcategory:'Developed International', currency:'USD', aumNote:'approx. USD 219.9B',  cagr:6.2,  vol:16.8, maxDD:-44.2, sharpe:0.52, worstYear:-23.8, worstYearLabel:2022 },
  { ticker:'IEFA',  name:'iShares Core MSCI EAFE ETF',             category:'US_ETF', subcategory:'Developed International', currency:'USD', aumNote:'approx. USD 180.9B',  cagr:5.9,  vol:16.5, maxDD:-43.8, sharpe:0.50, worstYear:-23.2, worstYearLabel:2022 },
  { ticker:'VTV',   name:'Vanguard Value ETF',                     category:'US_ETF', subcategory:'US Value',                currency:'USD', aumNote:'approx. USD 169.3B',  cagr:11.4, vol:15.8, maxDD:-34.2, sharpe:0.82, worstYear:-22.4, worstYearLabel:2022 },
  { ticker:'GLD',   name:'SPDR Gold Shares',                       category:'US_ETF', subcategory:'Gold / Commodities',      currency:'USD', aumNote:'approx. USD 163.4B',  cagr:8.4,  vol:14.9, maxDD:-45.0, sharpe:0.61, worstYear:-28.3, worstYearLabel:2013 },
  { ticker:'BND',   name:'Vanguard Total Bond Market ETF',         category:'US_ETF', subcategory:'US Total Bond',           currency:'USD', aumNote:'approx. USD 152.6B',  cagr:2.3,  vol:6.1,  maxDD:-17.2, sharpe:0.42, worstYear:-13.1, worstYearLabel:2022 },
  { ticker:'IEMG',  name:'iShares Core MSCI Emerging Markets ETF', category:'US_ETF', subcategory:'Emerging Markets',        currency:'USD', aumNote:'approx. USD 148.9B',  cagr:5.4,  vol:20.1, maxDD:-47.8, sharpe:0.41, worstYear:-24.1, worstYearLabel:2022 },
  { ticker:'VXUS',  name:'Vanguard Total International Stock ETF', category:'US_ETF', subcategory:'Global ex-US',            currency:'USD', aumNote:'approx. USD 144.0B',  cagr:5.7,  vol:16.9, maxDD:-43.5, sharpe:0.48, worstYear:-23.0, worstYearLabel:2022 },
  { ticker:'AGG',   name:'iShares Core U.S. Aggregate Bond ETF',   category:'US_ETF', subcategory:'US Total Bond',           currency:'USD', aumNote:'approx. USD 135.9B',  cagr:2.1,  vol:6.0,  maxDD:-17.0, sharpe:0.40, worstYear:-13.0, worstYearLabel:2022 },
  { ticker:'IEF',   name:'iShares 7-10 Year Treasury Bond ETF',    category:'US_ETF', subcategory:'Intermediate US Treasury',currency:'USD', aumNote:'approx. USD 45.0B',   cagr:1.8,  vol:7.2,  maxDD:-18.4, sharpe:0.32, worstYear:-15.1, worstYearLabel:2022 },
  // Crypto
  { ticker:'BTC-USD',  name:'Bitcoin',   category:'CRYPTO', subcategory:'Store of Value',          currency:'USD', aumNote:'approx. USD 1,300.0B', cagr:42.1, vol:68.4, maxDD:-83.4, sharpe:0.84, worstYear:-65.0, worstYearLabel:2022 },
  { ticker:'ETH-USD',  name:'Ethereum',  category:'CRYPTO', subcategory:'Smart Contract Platform', currency:'USD', aumNote:'approx. USD 280.0B',   cagr:38.5, vol:82.3, maxDD:-94.4, sharpe:0.71, worstYear:-67.4, worstYearLabel:2022 },
  { ticker:'BNB-USD',  name:'BNB',       category:'CRYPTO', subcategory:'Exchange Platform Token', currency:'USD', aumNote:'approx. USD 85.0B',    cagr:35.1, vol:75.2, maxDD:-90.1, sharpe:0.69, worstYear:-72.4, worstYearLabel:2022 },
  { ticker:'XRP-USD',  name:'XRP',       category:'CRYPTO', subcategory:'Cross-Border Payments',   currency:'USD', aumNote:'approx. USD 65.0B',    cagr:28.4, vol:88.3, maxDD:-95.1, sharpe:0.58, worstYear:-91.1, worstYearLabel:2018 },
  { ticker:'SOL-USD',  name:'Solana',    category:'CRYPTO', subcategory:'High-Performance L1',     currency:'USD', aumNote:'approx. USD 65.0B',    cagr:55.2, vol:95.1, maxDD:-97.4, sharpe:0.78, worstYear:-97.0, worstYearLabel:2022 },
  { ticker:'TRX-USD',  name:'TRON',      category:'CRYPTO', subcategory:'Stablecoin Settlement',   currency:'USD', aumNote:'approx. USD 25.0B',    cagr:22.3, vol:79.4, maxDD:-91.2, sharpe:0.45, worstYear:-74.5, worstYearLabel:2022 },
  { ticker:'DOGE-USD', name:'Dogecoin',  category:'CRYPTO', subcategory:'Meme Coin',               currency:'USD', aumNote:'approx. USD 25.0B',    cagr:31.8, vol:102.4,maxDD:-92.1, sharpe:0.42, worstYear:-88.4, worstYearLabel:2022 },
  { ticker:'ADA-USD',  name:'Cardano',   category:'CRYPTO', subcategory:'Academic L1',             currency:'USD', aumNote:'approx. USD 20.0B',    cagr:24.6, vol:91.2, maxDD:-93.8, sharpe:0.39, worstYear:-77.9, worstYearLabel:2022 },
];

// ── Persona Presets ────────────────────────────────────────────────────────────
const PPL_PERSONAS = {
  '🐣 Young Professional': {
    watchlist: ['0050.TW','VTI','VEA','BND','GLD','BTC-USD'],
    weights:   { '0050.TW':0.25, 'VTI':0.25, 'VEA':0.15, 'BND':0.20, 'GLD':0.10, 'BTC-USD':0.05 },
    risk: 'Medium', initial: 100000, monthly: 10000, annual_expenses: 600000,
    description: { en: 'Medium-risk accumulation with Taiwan, US, developed-market, bond, gold, and Bitcoin exposure.',
                   zh: '中風險累積型：台股、美股、已開發市場、債券、黃金、比特幣全面配置。' },
  },
  '🕊️ Pre-Retirement': {
    watchlist: ['0050.TW','00878.TW','VEA','BND','GLD','VTI'],
    weights:   { '0050.TW':0.20, '00878.TW':0.20, 'VEA':0.15, 'BND':0.25, 'GLD':0.15, 'VTI':0.05 },
    risk: 'Low', initial: 5000000, monthly: 50000, annual_expenses: 1200000,
    description: { en: 'Low-risk retirement sprint with diversified equity, bond, and gold exposure.',
                   zh: '低風險退休衝刺型：多元股票、債券與黃金，降低波動保護本金。' },
  },
  '🚀 Aggressive Growth': {
    watchlist: ['VTI','QQQ','0050.TW','VEA','BTC-USD','GLD'],
    weights:   { 'VTI':0.35, 'QQQ':0.20, '0050.TW':0.15, 'VEA':0.10, 'BTC-USD':0.15, 'GLD':0.05 },
    risk: 'High', initial: 800000, monthly: 30000, annual_expenses: 800000,
    description: { en: 'High-risk growth portfolio with VTI, QQQ, Taiwan equity, developed markets, Bitcoin, and gold.',
                   zh: '高風險積極成長型：VTI、QQQ、台股、已開發市場、比特幣與黃金組合。' },
  },
};

const RISK_VOL_TARGET = { 'Low':0.12, 'Medium':0.20, 'High':0.35, 'Extreme High':0.65 };

// ── Auto-allocation (inverse-vol weight targeting) ────────────────────────────
function computeAllocation(tickers, riskLevel) {
  const assets = tickers.map(t => PPL_ASSETS.find(a => a.ticker === t)).filter(Boolean);
  if (!assets.length) return {};
  const targetVol = RISK_VOL_TARGET[riskLevel] || 0.20;
  const vols = assets.map(a => a.vol / 100);
  let weights = vols.map(v => 1 / Math.max(v, 0.001));
  const sum = weights.reduce((s, w) => s + w, 0);
  weights = weights.map(w => w / sum);
  for (let i = 0; i < 200; i++) {
    const portVol = weights.reduce((s, w, j) => s + w * vols[j], 0);
    if (Math.abs(portVol - targetVol) < 0.001) break;
    weights = weights.map((w, j) => portVol > targetVol
      ? w * (1 - 0.05 * (vols[j] / Math.max(...vols)))
      : w * (1 + 0.05 * (vols[j] / Math.max(...vols))));
    const s2 = weights.reduce((s, w) => s + w, 0);
    weights = weights.map(w => Math.max(w / s2, 0.01));
    const s3 = weights.reduce((s, w) => s + w, 0);
    weights = weights.map(w => w / s3);
  }
  const result = {};
  assets.forEach((a, i) => { result[a.ticker] = weights[i]; });
  return result;
}

// ── Seeded RNG (Mulberry32) ───────────────────────────────────────────────────
function mulberry32(a) {
  return function() {
    a |= 0; a = a + 0x6D2B79F5 | 0;
    let t = Math.imul(a ^ a >>> 15, 1 | a);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}

// ── Mock backtest (monthly, 2010-01 → 2025-04) ────────────────────────────────
// Deterministic: seeded from weighted CAGR + vol.
// Shocks are calibrated to major market events; matches real run_backtest() output shape:
//   { labels, portVals, invested, drawdowns, annualReturns, finalVal, totalInv, cagr, maxDD }
function generateBacktest(allocation, initial = 300000, monthly = 15000) {
  const tickers = Object.keys(allocation);
  let wCagr = 0, wVol = 0;
  tickers.forEach(t => {
    const a = PPL_ASSETS.find(x => x.ticker === t);
    if (a) { wCagr += allocation[t] * a.cagr / 100; wVol += allocation[t] * a.vol / 100; }
  });
  const seed = Math.round(wCagr * 1000 + wVol * 100);
  const rand = mulberry32(seed);
  const monthlyMu = wCagr / 12;
  const monthlySig = wVol / Math.sqrt(12);

  const shocks = {
    '2011-08':-3,'2011-09':-2,
    '2015-08':-3,'2015-09':-2,'2015-12':-1.5,
    '2018-10':-2.5,'2018-11':-1.5,'2018-12':-3,
    '2020-02':-2,'2020-03':-6,'2020-04':4,'2020-11':3,
    '2022-01':-2.5,'2022-04':-2,'2022-06':-2.5,'2022-09':-2,
    '2023-03':2,'2023-11':2.5,'2024-03':1.5,'2024-11':2,
  };

  const labels = [], portVals = [], invested = [], drawdowns = [];
  let pv = initial, inv = initial, peak = initial;

  for (let yr = 2010; yr <= 2025; yr++) {
    for (let mo = 1; mo <= 12; mo++) {
      if (yr === 2025 && mo > 4) break;
      const key = `${yr}-${String(mo).padStart(2,'0')}`;
      if (yr > 2010 || mo > 1) { pv += monthly; inv += monthly; }
      const shock = shocks[key] || 0;
      const z = (rand() - 0.5) * 2;
      const ret = monthlyMu + monthlySig * (z + shock);
      pv = Math.max(pv * (1 + ret), inv * 0.1);
      peak = Math.max(peak, pv);
      const dd = peak > 0 ? ((pv - peak) / peak) * 100 : 0;
      labels.push(key);
      portVals.push(Math.round(pv));
      invested.push(Math.round(inv));
      drawdowns.push(parseFloat(dd.toFixed(2)));
    }
  }

  const annualReturns = [];
  for (let yr = 2010; yr <= 2024; yr++) {
    const idxStart = labels.indexOf(`${yr}-01`);
    const idxEnd   = labels.indexOf(`${yr}-12`);
    if (idxStart < 0 || idxEnd < 0) continue;
    const ret = (portVals[idxEnd] / portVals[idxStart] - 1) * 100;
    annualReturns.push({ year: yr, ret: parseFloat(ret.toFixed(1)) });
  }

  const finalVal  = portVals[portVals.length - 1];
  const totalInv  = invested[invested.length - 1];
  const years     = labels.length / 12;
  const cagr      = years > 0 && totalInv > 0 ? (Math.pow(finalVal / totalInv, 1 / years) - 1) : 0;
  const maxDD     = Math.min(...drawdowns);

  return { labels, portVals, invested, drawdowns, annualReturns, finalVal, totalInv, cagr, maxDD };
}

// ── Drawdown episode events ───────────────────────────────────────────────────
const DRAWDOWN_EVENTS = [
  { xMin:'2011-07', xMax:'2011-11', label:'EU Debt Crisis',      labelZh:'歐債危機',     color:'orange' },
  { xMin:'2015-07', xMax:'2016-01', label:'China Slowdown',      labelZh:'中國放緩',     color:'orange' },
  { xMin:'2018-09', xMax:'2019-01', label:'Rate Hike Sell-off',  labelZh:'升息賣壓',     color:'red'    },
  { xMin:'2020-02', xMax:'2020-05', label:'COVID Crash',         labelZh:'COVID 崩盤',   color:'purple' },
  { xMin:'2022-01', xMax:'2022-10', label:'2022 Bear Market',    labelZh:'2022 熊市',    color:'red'    },
];

// ── FIRE calculator ───────────────────────────────────────────────────────────
function calculateFIRE({ cagr, currentSavings, monthlyContrib, annualExpenses, withdrawalRate, inflation }) {
  const target = annualExpenses / withdrawalRate;
  const realRate = (1 + cagr) / (1 + inflation) - 1;
  const labels = [], nomVals = [], realVals = [];
  let savings = currentSavings;
  let realSavings = currentSavings;
  let yearsNominal = null, yearsReal = null;
  for (let y = 0; y <= 50; y++) {
    labels.push(y);
    nomVals.push(Math.round(savings));
    realVals.push(Math.round(realSavings));
    if (yearsNominal === null && savings >= target) yearsNominal = y;
    if (yearsReal === null && realSavings >= target) yearsReal = y;
    savings = (savings + monthlyContrib * 12) * (1 + cagr);
    realSavings = (realSavings + monthlyContrib * 12) * (1 + realRate);
  }
  return { labels, nomVals, realVals, target, yearsNominal, yearsReal };
}
