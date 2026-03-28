export default async function handler(req, res) {
  // کش کردن پاسخ به مدت ۱۰ دقیقه (۶۰۰ ثانیه) در سرور Vercel
  res.setHeader('Cache-Control', 's-maxage=600, stale-while-revalidate');
  
  try {
    // دریافت اطلاعات قیمتی از CoinGecko API
    const r = await fetch("https://api.coingecko.com/api/v3/simple/price?ids=tether,tron,the-open-network,ripple&vs_currencies=usd");
    const data = await r.json();
    
    res.status(200).json({
      USDT: data.tether?.usd || 1,
      TRX: data.tron?.usd || 0.12,
      TON: data["the-open-network"]?.usd || 5.0,
      XRP: data.ripple?.usd || 0.6
    });
  } catch (e) {
    // در صورت قطعی ارتباط با CoinGecko، قیمت‌های پیش‌فرض ارسال می‌شود
    res.status(200).json({ USDT: 1, TRX: 0.12, TON: 5.0, XRP: 0.6 });
  }
}
