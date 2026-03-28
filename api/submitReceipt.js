import { supabase } from "../lib/supabase"

export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method Not Allowed' });

  // دریافت مقادیر ارسال شده از فرم خرید در فرانت‌اند
  const { chat_id, plan, txid, amount_toman, crypto_currency, crypto_amount, notes } = req.body;

  if (!chat_id || !txid || !plan) {
    return res.status(400).json({ error: "Missing required data" });
  }

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
