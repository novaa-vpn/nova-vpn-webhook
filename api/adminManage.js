import { supabase } from "../lib/supabase";

export default async function handler(req, res) {
  // ۱. فقط متد POST مجاز است
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method Not Allowed' });
  }

  const { action, admin_pass, tx_id, plan, v2ray, panel, message_text, target_chat_id } = req.body;
  
  // ۲. بررسی امنیت (رمز عبور)
  // حتماً این رمز را با رمزی که در فایل index.html ادمین وارد می‌کنید ست کنید
  const SECRET_PASS = process.env.ADMIN_PASSWORD || "Nova@Manager2026";

  if (admin_pass !== SECRET_PASS) {
    return res.status(401).json({ error: "خطای امنیتی: رمز عبور اشتباه است." });
  }

  const TOKEN = process.env.TELEGRAM_TOKEN;

  // تابع کمکی ارسال پیام تلگرام
  const sendTg = async (id, text) => {
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

      // دریافت اطلاعات تراکنش
      const { data: tx, error: txErr } = await supabase.from('transactions').select('*').eq('id', tx_id).maybeSingle();
      if (txErr || !tx) throw new Error("تراکنش در دیتابیس یافت نشد.");

      // پیدا کردن کانفیگ خالی در انبار
      const { data: conf, error: confErr } = await supabase
        .from('configs')
        .select('*')
        .eq('plan_name', tx.target_plan)
        .eq('status', 'available')
        .limit(1)
        .maybeSingle();
      
      if (confErr || !conf) throw new Error("انبار خالی است! ابتدا از تب انبار، کانفیگ اضافه کنید.");

      // ۱. رزرو کانفیگ برای کاربر
      const { error: updConfErr } = await supabase.from('configs').update({ 
        status: 'sold', 
        owner_id: tx.chat_id, 
        sold_at: new Date() 
      }).eq('id', conf.id);
      if (updConfErr) throw updConfErr;

      // ۲. تایید نهایی تراکنش
      const { error: updTxErr } = await supabase.from('transactions').update({ 
        status: 'approved', 
        handled_at: new Date() 
      }).eq('id', tx_id);
      if (updTxErr) throw updTxErr;

      // ۳. محاسبه و واریز پورسانت ترون (0.5 TRX به ازای هر 1 گیگ)
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

      // ۴. ارسال پیام موفقیت و کانفیگ به مشتری
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
      const { error } = await supabase.from('configs').insert({ 
        plan_name: plan, 
        v2ray_uri: v2ray, 
        web_panel_url: panel 
      });
      if (error) throw error;
      return res.status(200).json({ ok: true });
    }

    return res.status(400).json({ error: "عملیات نامعتبر است." });

  } catch (err) {
    // چاپ خطای دقیق در لاگ ورسل برای عیب‌یابی راحت‌تر
    console.error("🚨 CRITICAL ADMIN ERROR:", err.message);
    return res.status(500).json({ error: err.message });
  }
}
