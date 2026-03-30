import { createClient } from "@supabase/supabase-js";

export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method Not Allowed' });

  // دریافت اطلاعات از فرانت‌اند
  const { chat_id, plan, txid, crypto_currency, notes } = req.body;

  if (!chat_id || !txid || !plan) {
    return res.status(400).json({ error: "اطلاعات ناقص است." });
  }

  const cleanTxid = txid.trim();

  // ==========================================
  // 🛡️ لایه امنیتی ۰: فیلتر هوشمند در درگاه ورودی
  // ==========================================
  // این الگو چک می‌کند که متن وارد شده حتماً بین 40 تا 90 کاراکتر و فقط شامل حروف مجاز بلاک‌چین باشد
  const txidRegex = /^[a-zA-Z0-9\+\/\-\_=]{40,90}$/;
  if (!txidRegex.test(cleanTxid)) {
    return res.status(400).json({ error: "❌ هش تراکنش نامعتبر است! هش (TXID) یک کد طولانی (حداقل ۴۴ کاراکتر) شامل اعداد و حروف انگلیسی است." });
  }

  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SUPABASE_KEY = process.env.SUPABASE_ANON_KEY || process.env.SUPABASE_KEY;
  const TOKEN = process.env.TELEGRAM_TOKEN;
  const ADMIN_ID = process.env.ADMIN_CHAT_ID;

  const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);

  try {
    // 🛡️ لایه امنیتی ۱: جلوگیری از ثبت هش تکراری در لحظه
    const { data: existingTx } = await supabase.from("transactions").select("id").eq("txid_or_receipt", cleanTxid).maybeSingle();
    if (existingTx) {
      return res.status(400).json({ error: "❌ این رسید قبلاً در سیستم ثبت شده است!" });
    }

    // 🛡️ لایه امنیتی ۲: استخراج قیمت واقعی از دیتابیس (جلوگیری از دستکاری فرانت‌اند)
    const { data: planData } = await supabase.from("plans").select("*").eq("internal_name", plan).maybeSingle();
    if (!planData) throw new Error("پلن انتخابی در سیستم وجود ندارد.");

    // محاسبه قیمت زنده ارزها در سمت سرور
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

    const secureCryptoAmount = parseFloat((planData.price_usd / cryptoPrice).toFixed(2));

    // ثبت نهایی در دیتابیس (صف انتظار)
    const { error } = await supabase.from("transactions").insert({
      chat_id: chat_id,
      txid_or_receipt: cleanTxid,
      target_plan: plan,
      amount_toman: planData.price_toman,
      crypto_currency: crypto_currency,
      crypto_amount: secureCryptoAmount, 
      notes: notes || null,
      status: "pending_verification" 
    });

    if (error) throw error;

    // ارسال پیام هشدار به تلگرام ادمین
    if (TOKEN && ADMIN_ID) {
      const msg = `💰 **درخواست بررسی خودکار فعال شد!**\n\n👤 کاربر: \`${chat_id}\`\n🛍 پلن: ${plan}\n💵 مبلغ مورد انتظار: ${secureCryptoAmount} ${crypto_currency}\n🔍 هش تراکنش:\n\`${cleanTxid}\`\n\n(سیستم تا ۵ دقیقه آینده این تراکنش را از بلاک‌چین استعلام خواهد کرد)`;
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
