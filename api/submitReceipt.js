import { supabase } from "../lib/supabase"

export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method Not Allowed' });

  const { chat_id, plan, txid, amount } = req.body;

  if (!chat_id || !txid || !plan) {
    return res.status(400).json({ error: "Missing required data" });
  }

  try {
    // ثبت سفارش با وضعیت pending_verification برای سیستم تایید اتوماتیک
    const { error } = await supabase.from("transactions").insert({
      chat_id: chat_id,
      txid_or_receipt: txid,
      target_plan: plan,
      amount_toman: amount,
      status: "pending_verification"
    });

    if (error) throw error;

    res.status(200).json({ ok: true, message: "Receipt submitted successfully" });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
}
