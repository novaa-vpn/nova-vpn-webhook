import { createClient } from "@supabase/supabase-js";

export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method Not Allowed' });

  // اضافه شدن amount_toman برای دریافت مبلغ دلخواه شارژ
  const { chat_id, plan, txid, crypto_currency, notes, amount_toman } = req.body;

  if (!chat_id || !txid || !plan) {
    return res.status(400).json({ error: "اطلاعات ناقص است." });
  }

  const cleanTxid = txid.trim();

  // فیلتر هوشمند درگاه ورودی
  const txidRegex = /^[a-zA-Z0-9\+\/\-\_=]{40,90}$/;
  if (!txidRegex.test(cleanTxid)) {
    return res.status(400).json({ error: "❌ هش تراکنش نامعتبر است! هش (TXID) یک کد طولانی شامل اعداد و حروف انگلیسی است." });
  }

  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SUPABASE_KEY = process.env.SUPABASE_ANON_KEY || process.env.SUPABASE_KEY;
  const TOKEN = process.env.TELEGRAM_TOKEN;
  const ADMIN_ID = process.env.ADMIN_CHAT_ID;

  const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);

  try {
    const { data: existingTx } = await supabase.from("transactions").select("id").eq("txid_or_receipt", cleanTxid).maybeSingle();
    if (existingTx) {
      return res.status(400).json({ error: "❌ این رسید قبلاً در سیستم ثبت شده است!" });
    }

    let finalTomanPrice = 0;
    let finalUsdPrice = 0;

    // --- 🆕 اضافه شدن منطق قیمت‌گذاری داینامیک برای شارژ کیف پول ---
    if (plan === 'wallet_topup') {
      if (!amount_toman || amount_toman < 10000) return res.status(400).json({ error: "مبلغ شارژ باید حداقل ۱۰,۰۰۰ تومان باشد." });
      finalTomanPrice = amount_toman;
      finalUsdPrice = amount_toman / 60000; // نرخ تقریبی محاسبه ارز پایه برای شارژ
    } else {
      // استخراج قیمت واقعی از دیتابیس برای خرید پلن
      const { data: planData } = await supabase.from("plans").select("*").eq("internal_name", plan).maybeSingle();
      if (!planData) throw new Error("پلن انتخابی در سیستم وجود ندارد.");
      finalTomanPrice = planData.price_toman;
      finalUsdPrice = planData.price_usd;
    }

    // محاسبه قیمت زنده ارزها
    let cryptoPrice = 1; 
    try {
      if (crypto_currency === 'TRX') {
        const r = await fetch("https://api.coingecko.com/api/v3/simple/price?ids=tron&vs_currencies=usd");
        const d = await r.json();
        if (d.tron && d.tron.usd) cryptoPrice = d.tron.usd;
      } else if (crypto_currency === 'TON') {
        cryptoPrice = 5.00; 
      } else if (crypto_currency === 'XRP') {
        cryptoPrice = 0.60; 
      }
    } catch(e) { console.log("خطا در دریافت قیمت لحظه‌ای سرور"); }

    const secureCryptoAmount = parseFloat((finalUsdPrice / cryptoPrice).toFixed(2));

    // ثبت در دیتابیس
    const { error } = await supabase.from("transactions").insert({
      chat_id: chat_id,
      txid_or_receipt: cleanTxid,
      target_plan: plan,
      amount_toman: finalTomanPrice, // مبلغ ثبت شده ایمن
      crypto_currency: crypto_currency,
      crypto_amount: secureCryptoAmount, 
      notes: notes || null,
      status: "pending_verification" 
    });

    if (error) throw error;

    if (TOKEN && ADMIN_ID) {
      const planNameStr = plan === 'wallet_topup' ? 'شارژ کیف پول' : plan;
      const msg = `💰 **درخواست بررسی خودکار فعال شد!**\n\n👤 کاربر: \`${chat_id}\`\n🛍 نوع عملیات: ${planNameStr}\n💵 مبلغ مورد انتظار: ${secureCryptoAmount} ${crypto_currency}\n🔍 هش تراکنش:\n\`${cleanTxid}\``;
      await fetch(`https://api.telegram.org/bot${TOKEN}/sendMessage`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chat_id: ADMIN_ID, text: msg, parse_mode: 'Markdown' })
      });
    }

    res.status(200).json({ ok: true, message: "رسید با موفقیت ثبت شد" });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
}
