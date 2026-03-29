import { createClient } from "@supabase/supabase-js";

export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method Not Allowed' });

  const { chat_id, plan, txid, amount_toman, crypto_currency, crypto_amount, notes } = req.body;

  if (!chat_id || !txid || !plan) {
    return res.status(400).json({ error: "Missing required data" });
  }

  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SUPABASE_KEY = process.env.SUPABASE_ANON_KEY || process.env.SUPABASE_KEY;
  const TOKEN = process.env.TELEGRAM_TOKEN;
  const ADMIN_ID = process.env.ADMIN_CHAT_ID; // آیدی عددی شما برای دریافت هشدارها

  if (!SUPABASE_URL || !SUPABASE_KEY) {
    return res.status(500).json({ error: "Supabase credentials missing." });
  }

  const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);

  try {
    const { error } = await supabase.from("transactions").insert({
      chat_id: chat_id,
      txid_or_receipt: txid,
      target_plan: plan,
      amount_toman: amount_toman,
      crypto_currency: crypto_currency,
      crypto_amount: crypto_amount,
      notes: notes || null,
      status: "pending_verification" 
    });

    if (error) throw error;

    // ارسال پیام هشدار به تلگرام ادمین
    if (TOKEN && ADMIN_ID) {
      const msg = `💰 **رسید پرداخت جدید!**\n\n👤 کاربر: \`${chat_id}\`\n🛍 پلن: ${plan}\n💵 مبلغ: ${Number(amount_toman).toLocaleString()} تومان (${crypto_amount} ${crypto_currency})\n📝 توضیحات: ${notes || 'ندارد'}\n🔍 هش تراکنش:\n\`${txid}\`\n\nلطفاً جهت تایید به پنل مدیریت مراجعه کنید.`;
      
      await fetch(`https://api.telegram.org/bot${TOKEN}/sendMessage`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chat_id: ADMIN_ID, text: msg, parse_mode: 'Markdown' })
      });
    }

    res.status(200).json({ ok: true, message: "Receipt submitted successfully" });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
}
