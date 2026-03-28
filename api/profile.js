// api/profile.js اصلاح شده
import { supabase } from "../lib/supabase"

export default async function handler(req, res) {
  const { chat_id } = req.query
  if (!chat_id) return res.status(400).json({ error: "chat_id required" })

  // دریافت اطلاعات کاربر و اشتراک‌های او به صورت همزمان
  const { data: user, error } = await supabase
    .from("users")
    .select("*, subscriptions(*)") // فرض بر وجود جدول اشتراک‌ها
    .eq("chat_id", chat_id)
    .maybeSingle()

  if (error) return res.status(500).json({ error: error.message })

  if (!user) {
    // ایجاد کاربر جدید در صورت عدم وجود
    const { data: newUser } = await supabase
      .from("users")
      .insert({ chat_id, balance: 0, role: "user" })
      .select().single()
    return res.json(newUser)
  }

  return res.json(user)
}
