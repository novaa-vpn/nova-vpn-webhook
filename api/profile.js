import { supabase } from "../lib/supabase"

export default async function handler(req, res) {
  const { chat_id } = req.query;

  if (!chat_id) {
    return res.status(400).json({ error: "chat_id required" });
  }

  try {
    // دریافت اطلاعات شخصی کاربر
    const { data: user, error: userError } = await supabase
      .from("users")
      .select("*")
      .eq("chat_id", chat_id)
      .maybeSingle();

    if (userError) throw userError;

    // اگر کاربر جدید است، آن را در دیتابیس می‌سازیم
    let userData = user;
    if (!userData) {
      const { data: newUser, error: insertError } = await supabase
        .from("users")
        .insert({ chat_id: chat_id, wallet_balance: 0, role: "user" })
        .select()
        .single();
      
      if (insertError) throw insertError;
      userData = newUser;
    }

    // دریافت لیست کانفیگ‌ها (سرویس‌های) فعال همین کاربر
    const { data: services } = await supabase
      .from("configs")
      .select("*")
      .eq("owner_id", chat_id)
      .eq("status", "sold");

    return res.status(200).json({
      chat_id: userData.chat_id,
      balance: userData.wallet_balance || 0,
      role: userData.role,
      services: services || []
    });

  } catch (e) {
    return res.status(500).json({ error: e.message });
  }
}
