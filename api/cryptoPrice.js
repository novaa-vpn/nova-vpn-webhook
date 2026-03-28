export default async function handler(req, res) {
  // کش کردن درخواست در سرور برای جلوگیری از کندی و بن شدن IP
  res.setHeader('Cache-Control', 's-maxage=600, stale-while-revalidate');
  
  try {
    const r = await fetch("https://api.coingecko.com/api/v3/simple/price?ids=tether,tron,the-open-network,ripple&vs_currencies=usd");
    const data = await r.json();
    
    res.status(200).json({
      USDT: data.tether?.usd || 1,
      TRX: data.tron?.usd || 0.12,
      TON: data["the-open-network"]?.usd || 5.0,
      XRP: data.ripple?.usd || 0.6
    });
  } catch (e) {
    // مقادیر پیش‌فرض در صورت قطعی اینترنت سرور
    res.status(200).json({ USDT: 1, TRX: 0.12, TON: 5.0, XRP: 0.6 });
  }
}
