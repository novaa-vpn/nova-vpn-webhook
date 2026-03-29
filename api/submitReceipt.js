import { createClient } from "@supabase/supabase-js";

export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method Not Allowed' });

  // دریافت مقادیر ارسال شده از فرم خرید در فرانت‌اند
  const { chat_id, plan, txid, amount_toman, crypto_currency, crypto_amount, notes } = req.body;

  if (!chat_id || !txid || !plan) {
    return res.status(400).json({ error: "Missing required data" });
  }

  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SUPABASE_KEY = process.env.SUPABASE_ANON_KEY || process.env.SUPABASE_KEY;

  if (!SUPABASE_URL || !SUPABASE_KEY) {
    return res.status(500).json({ error: "Supabase credentials missing." });
  }

  const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);

  try {
    // درج تراکنش جدید با تمامی فیلدهای مورد نیاز و وضعیت اولیه اعتبارسنجی
    const { error } = await supabase.from("transactions").insert({
      chat_id: chat_id,
      txid_or_receipt: txid,
      target_plan: plan,
      amount_toman: amount_toman,
      crypto_currency: crypto_currency,
      crypto_amount: crypto_amount,
      notes: notes || null,
      status: "pending_verification" // وضعیت اولیه
    });

    if (error) throw error;

    res.status(200).json({ ok: true, message: "Receipt submitted successfully" });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
}
