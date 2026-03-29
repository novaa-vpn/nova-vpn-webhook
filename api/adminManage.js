import { createClient } from "@supabase/supabase-js";

export default async function handler(req, res) {
  // ۱. فقط متد POST مجاز است
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method Not Allowed' });
  }

  const { action, admin_pass, tx_id, plan, v2ray, panel, message_text, target_chat_id, plan_id, title_fa, price_toman, gb_amount } = req.body;
  
  // ۲. بررسی امنیت (رمز عبور)
  const SECRET_PASS = process.env.ADMIN_PASSWORD || "Nova@Manager2026";

  if (admin_pass !== SECRET_PASS) {
    return res.status(401).json({ error: "خطای امنیتی: رمز عبور اشتباه است." });
  }

  // ۳. بررسی متغیرهای محیطی درون تابع (برای جلوگیری از کرش کردن سرور در صورت نبود متغیرها)
  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SUPABASE_KEY = process.env.SUPABASE_ANON_KEY || process.env.SUPABASE_KEY;
  const TOKEN = process.env.TELEGRAM_TOKEN;

  if (!SUPABASE_URL || !SUPABASE_KEY) {
    return res.status(500).json({ error: "متغیرهای دیتابیس (SUPABASE_URL و SUPABASE_ANON_KEY) در تنظیمات Vercel یافت نشدند!" });
  }

  // اتصال ایمن به دیتابیس
  const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);

  // تابع کمکی ارسال پیام تلگرام
  const sendTg = async (id, text) => {
    if (!TOKEN) return;
    try {
      await fetch(`https://api.telegram.org/bot${TOKEN}/sendMessage`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chat_id: id, text, parse_mode: "Markdown" })
      });
    } catch (e) {
      console.error("Telegram Send Error:", e.message);
    }
  };

  try {
    // --- عملیات دریافت تراکنش‌های معلق ---
    if (action === 'get_pending') {
      const { data, error } = await supabase
        .from('transactions')
        .select('*')
        .in('status', ['pending', 'pending_verification'])
        .order('created_at', { ascending: false });
      
      if (error) throw error;
      return res.status(200).json({ receipts: data || [] });
    }

    // --- عملیات تایید تراکنش و تحویل خودکار ---
    if (action === 'approve') {
      if (!tx_id) throw new Error("آیدی تراکنش ارسال نشده است.");

      const { data: tx, error: txErr } = await supabase.from('transactions').select('*').eq('id', tx_id).maybeSingle();
      if (txErr || !tx) throw new Error("تراکنش در دیتابیس یافت نشد.");

      const { data: conf, error: confErr } = await supabase
        .from('configs')
        .select('*')
        .eq('plan_name', tx.target_plan)
        .eq('status', 'available')
        .limit(1)
        .maybeSingle();
      
      if (confErr || !conf) throw new Error("انبار خالی است! ابتدا از تب انبار، کانفیگ اضافه کنید.");

      const { error: updConfErr } = await supabase.from('configs').update({ status: 'sold', owner_id: tx.chat_id, sold_at: new Date() }).eq('id', conf.id);
      if (updConfErr) throw updConfErr;

      const { error: updTxErr } = await supabase.from('transactions').update({ status: 'approved', handled_at: new Date() }).eq('id', tx_id);
      if (updTxErr) throw updTxErr;

      const { data: buyer } = await supabase.from('users').select('referrer_id').eq('chat_id', tx.chat_id).maybeSingle();
      if (buyer?.referrer_id) {
        const { data: planData } = await supabase.from('plans').select('gb_amount').eq('internal_name', tx.target_plan).maybeSingle();
        const gb = planData?.gb_amount || 0;
        const reward = gb * 0.5;

        if (reward > 0) {
          const { data: refUser } = await supabase.from('users').select('wallet_trx').eq('chat_id', buyer.referrer_id).maybeSingle();
          const currentTrx = refUser?.wallet_trx || 0;
          await supabase.from('users').update({ wallet_trx: currentTrx + reward }).eq('chat_id', buyer.referrer_id);
          
          await sendTg(buyer.referrer_id, `🎊 **مژده! پاداش جدید واریز شد**\n\nزیرمجموعه شما یک خرید انجام داد و مبلغ \`${reward} TRX\` به کیف پول شما اضافه شد.`);
        }
      }

      const successMsg = `🎉 **سفارش شما تایید شد!**\n\n🚀 **کانفیگ اختصاصی شما:**\n\`${conf.v2ray_uri}\`\n\n📊 **پنل مشاهده مصرف:**\n${conf.web_panel_url}`;
      await sendTg(tx.chat_id, successMsg);

      return res.status(200).json({ ok: true });
    }

    // --- عملیات رد تراکنش ---
    if (action === 'reject') {
      const { error: rejErr } = await supabase.from('transactions').update({ status: 'rejected' }).eq('id', tx_id);
      if (rejErr) throw rejErr;

      const { data: txInfo } = await supabase.from('transactions').select('chat_id').eq('id', tx_id).maybeSingle();
      if (txInfo) {
        await sendTg(txInfo.chat_id, "❌ **متاسفانه تراکنش شما رد شد.**\n\nدلیل احتمالی: مغایرت مبلغ یا اشتباه بودن هش تراکنش. لطفا با پشتیبانی در ارتباط باشید.");
      }
      return res.status(200).json({ ok: true });
    }

    // --- عملیات مشاهده موجودی انبار ---
    if (action === 'get_inventory') {
      const { data, error } = await supabase.from('configs').select('plan_name').eq('status', 'available');
      if (error) throw error;
      const stats = data.reduce((acc, curr) => {
        acc[curr.plan_name] = (acc[curr.plan_name] || 0) + 1;
        return acc;
      }, {});
      return res.status(200).json({ stats });
    }

    // --- عملیات افزودن کانفیگ جدید ---
    if (action === 'add_config') {
      const { error } = await supabase.from('configs').insert({ plan_name: plan, v2ray_uri: v2ray, web_panel_url: panel });
      if (error) throw error;
      return res.status(200).json({ ok: true });
    }
    
    // --- عملیات دریافت لیست کاربران ---
    if (action === 'get_users') {
      const { data, error } = await supabase.from('users').select('*').order('created_at', { ascending: false }).limit(50);
      if (error) throw error;
      return res.status(200).json({ users: data || [] });
    }
    
    // --- عملیات ارسال پیام همگانی ---
    if (action === 'broadcast') {
      if (!message_text) throw new Error("متن پیام خالی است.");
      const { data: users } = await supabase.from('users').select('chat_id');
      if (users) {
        for (const u of users) {
          await sendTg(u.chat_id, message_text);
        }
      }
      return res.status(200).json({ ok: true });
    }

    // --- عملیات ارسال پیام به یک کاربر خاص ---
    if (action === 'send_message') {
      if (!target_chat_id || !message_text) throw new Error("آیدی کاربر یا متن پیام وارد نشده است.");
      await sendTg(target_chat_id, `💬 **پیام از پشتیبانی نُوا:**\n\n${message_text}`);
      return res.status(200).json({ ok: true });
    }

    // --- عملیات حذف کاربر ---
    if (action === 'delete_user') {
      if (!target_chat_id) throw new Error("آیدی کاربر نامعتبر است.");
      // به دلیل وابستگی‌های دیتابیس (سفارشات/تراکنش‌ها)، امن‌ترین کار پاک کردن رکورد از جدول است
      const { error } = await supabase.from('users').delete().eq('chat_id', target_chat_id);
      if (error) throw new Error("امکان حذف کاربر نیست! (ممکن است کاربر سفارش فعالی داشته باشد)");
      return res.status(200).json({ ok: true });
    }

    // --- عملیات ایجاد پلن (سرویس) جدید ---
    if (action === 'add_plan') {
      if (!plan_id || !title_fa || !price_toman) throw new Error("اطلاعات محصول جدید ناقص است.");
      
      const { error } = await supabase.from('plans').insert({
        internal_name: plan_id,
        title_fa: title_fa,
        title_en: title_fa,
        price_toman: price_toman,
        gb_amount: gb_amount || 0,
        is_active: true
      });
      if (error) throw new Error("خطا در ثبت محصول. ممکن است نام سیستمی (ID) تکراری باشد.");
      return res.status(200).json({ ok: true });
    }

    return res.status(400).json({ error: "عملیات نامعتبر است." });

  } catch (err) {
    return res.status(500).json({ error: err.message });
  }
}
