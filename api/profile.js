import { createClient } from "@supabase/supabase-js";

export default async function handler(req, res) {
  const { chat_id } = req.query;

  if (!chat_id) {
    return res.status(400).json({ error: "chat_id required" });
  }

  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SUPABASE_KEY = process.env.SUPABASE_ANON_KEY || process.env.SUPABASE_KEY;

  if (!SUPABASE_URL || !SUPABASE_KEY) {
    return res.status(500).json({ error: "Supabase credentials missing." });
  }

  const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);

  try {
    // ۱. دریافت اطلاعات اصلی کاربر
    let { data: user, error: userError } = await supabase
      .from("users")
      .select("*")
      .eq("chat_id", chat_id)
      .maybeSingle();

    if (userError) throw userError;

    // ثبت‌نام سریع در صورتی که کاربر قبلاً با دکمه ربات استارت نکرده باشد
    if (!user) {
      const { data: newUser, error: insertError } = await supabase
        .from("users")
        .insert({ chat_id: chat_id, wallet_balance: 0, wallet_trx: 0, role: "user", total_referrals: 0 })
        .select()
        .single();
      
      if (insertError) throw insertError;
      user = newUser;
    }

    // ۲. دریافت سرویس‌های خریداری شده (فعال) کاربر
    const { data: services } = await supabase
      .from("configs")
      .select("*")
      .eq("owner_id", chat_id)
      .eq("status", "sold");

    // ۳. دریافت تاریخچه کامل تراکنش‌ها و مرتب‌سازی جدیدترین به قدیمی‌ترین
    const { data: transactions } = await supabase
      .from("transactions")
      .select("*")
      .eq("chat_id", chat_id)
      .order('created_at', { ascending: false });

    // بازگرداندن تمام اطلاعات برای نمایش در داشبورد
    return res.status(200).json({
      user: user,
      services: services || [],
      transactions: transactions || []
    });

  } catch (e) {
    return res.status(500).json({ error: e.message });
  }
}
