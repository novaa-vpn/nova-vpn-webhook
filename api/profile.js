import { createClient } from "@supabase/supabase-js";

export default async function handler(req, res) {
  const { chat_id } = req.query;

  // بررسی وجود آیدی کاربر
  if (!chat_id) {
    return res.status(400).json({ error: "chat_id required" });
  }

  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SUPABASE_KEY = process.env.SUPABASE_ANON_KEY || process.env.SUPABASE_KEY;

  // بررسی تنظیمات دیتابیس در ورسل
  if (!SUPABASE_URL || !SUPABASE_KEY) {
    return res.status(500).json({ error: "Supabase credentials missing." });
  }

  const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);

  try {
    // ۱. دریافت یا ثبت‌نام خودکار اطلاعات اصلی کاربر
    let { data: user, error: userError } = await supabase
      .from("users")
      .select("*")
      .eq("chat_id", chat_id)
      .maybeSingle();

    if (userError) throw userError;

    // اگر کاربر به هر دلیلی در دیتابیس نبود (مثلاً مستقیم لینک مینی‌اپ را باز کرده)
    if (!user) {
      const { data: newUser, error: insertError } = await supabase
        .from("users")
        .insert({ 
          chat_id: chat_id, 
          wallet_balance: 0, 
          wallet_trx: 0, 
          role: "user", 
          total_referrals: 0 
        })
        .select()
        .single();
      
      if (insertError) throw insertError;
      user = newUser;
    }

    // ۲. دریافت سرویس‌های خریداری شده (فروخته شده) به این کاربر
    const { data: services } = await supabase
      .from("configs")
      .select("*")
      .eq("owner_id", chat_id)
      .eq("status", "sold");

    // ۳. دریافت تاریخچه کامل تراکنش‌ها (از جدید به قدیم)
    const { data: transactions } = await supabase
      .from("transactions")
      .select("*")
      .eq("chat_id", chat_id)
      .order('created_at', { ascending: false });

    // ۴. دریافت لیست محصولات (پلن‌ها) برای نمایش در فروشگاه مینی‌اپ
    const { data: plans } = await supabase
      .from("plans")
      .select("*")
      .order('price_toman', { ascending: true });

    // ارسال پاسخ نهایی به فرانت‌اِند مینی‌اپ
    return res.status(200).json({
      user: user,
      services: services || [],
      transactions: transactions || [],
      plans: plans || []
    });

  } catch (e) {
    // جلوگیری از کرش کردن و ارسال خطای دقیق
    console.error("Profile API Error:", e.message);
    return res.status(500).json({ error: e.message });
  }
}
