import { createClient } from "@supabase/supabase-js";

export default async function handler(req, res) {
  // کش کردن پاسخ به مدت ۱۰ دقیقه (۶۰۰ ثانیه)
  res.setHeader('Cache-Control', 's-maxage=600, stale-while-revalidate');
  
  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SUPABASE_KEY = process.env.SUPABASE_ANON_KEY || process.env.SUPABASE_KEY;
  const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);

  try {
    // ۱. دریافت اطلاعات قیمتی از CoinGecko API
    const r = await fetch("https://api.coingecko.com/api/v3/simple/price?ids=tether,tron,the-open-network,ripple&vs_currencies=usd");
    
    if (!r.ok) throw new Error("API Limit or Server Error");
    
    const data = await r.json();
    
    if (!data.tron?.usd || !data["the-open-network"]?.usd) {
        throw new Error("Invalid Price Data");
    }
    
    const prices = {
      USDT: data.tether?.usd || 1.00,
      TRX: data.tron.usd,
      TON: data["the-open-network"].usd,
      XRP: data.ripple?.usd || 0.60
    };

    // ۲. ذخیره قیمت‌های زنده در دیتابیس خودمان
    for (const [symbol, price] of Object.entries(prices)) {
      await supabase.from('crypto_prices').upsert({ symbol, price, updated_at: new Date() });
    }

    res.status(200).json(prices);
  } catch (e) {
    console.log("API Error, reading from DB:", e.message);
    
    // ۳. اگر API قطع بود، قیمت‌ها را از دیتابیس می‌خوانیم (فروش متوقف نمی‌شود)
    const { data: savedPrices, error } = await supabase.from('crypto_prices').select('*');
    
    if (error || !savedPrices || savedPrices.length === 0) {
       return res.status(500).json({ error: "ارتباط با سرور قیمت‌گذاری قطع است. دقایقی دیگر تلاش کنید." });
    }

    const fallbackPrices = {};
    savedPrices.forEach(p => fallbackPrices[p.symbol] = p.price);
    
    res.status(200).json(fallbackPrices);
  }
}
