import { createClient } from "@supabase/supabase-js";

export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method Not Allowed' });

  const { chat_id, plan_id } = req.body;

  if (!chat_id || !plan_id) {
    return res.status(400).json({ error: "اطلاعات ناقص است." });
  }

  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SUPABASE_KEY = process.env.SUPABASE_ANON_KEY || process.env.SUPABASE_KEY;
  const TOKEN = process.env.TELEGRAM_TOKEN;
  const ADMIN_ID = process.env.ADMIN_CHAT_ID;

  const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);

  try {
    // ۱. استخراج قیمت محصول
    const { data: planData } = await supabase.from("plans").select("*").eq("internal_name", plan_id).maybeSingle();
    if (!planData || !planData.is_active) {
      return res.status(400).json({ error: "محصول مورد نظر یافت نشد یا غیرفعال است." });
    }
    const price = Number(planData.price_toman);

    // ۲. بررسی موجودی کیف پول خریدار
    const { data: user } = await supabase.from("users").select("wallet_balance, referrer_id").eq("chat_id", chat_id).maybeSingle();
    if (!user) return res.status(400).json({ error: "کاربر یافت نشد." });

    const currentBalance = Number(user.wallet_balance || 0);
    if (currentBalance < price) {
      return res.status(400).json({ error: "موجودی کیف پول شما کافی نیست! ابتدا حساب خود را شارژ کنید." });
    }

    // ۳. برداشت کانفیگ آزاد از انبار
    const { data: conf } = await supabase.from('configs').select('*').eq('plan_name', plan_id).eq('status', 'available').limit(1).maybeSingle();
    if (!conf) {
      // هشدار به ادمین که انبار خالی شده
      if (TOKEN && ADMIN_ID) {
        await fetch(`https://api.telegram.org/bot${TOKEN}/sendMessage`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ chat_id: ADMIN_ID, text: `⚠️ **اخطار فوری انبار!**\nکاربر قصد خرید آنی با کیف پول برای محصول **${planData.title_fa}** را داشت اما انبار خالی است!`, parse_mode: 'Markdown' })
        });
      }
      return res.status(400).json({ error: "موجودی این سرویس موقتاً به اتمام رسیده و به زودی شارژ خواهد شد." });
    }

    // ۴. کسر مبلغ از کیف پول
    const newBalance = currentBalance - price;
    await supabase.from("users").update({ wallet_balance: newBalance }).eq("chat_id", chat_id);

    // ۵. قفل کردن کانفیگ به نام کاربر
    await supabase.from('configs').update({ status: 'sold', owner_id: chat_id, sold_at: new Date() }).eq('id', conf.id);

    // ۶. پاداش معرف (در صورت وجود)
    if (user.referrer_id) {
      const reward = (planData.gb_amount || 0) * 0.5;
      if (reward > 0) {
        const { data: refUser } = await supabase.from('users').select('wallet_trx').eq('chat_id', user.referrer_id).maybeSingle();
        await supabase.from('users').update({ wallet_trx: (refUser?.wallet_trx || 0) + reward }).eq('chat_id', user.referrer_id);
        await fetch(`https://api.telegram.org/bot${TOKEN}/sendMessage`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ chat_id: user.referrer_id, text: `🎊 **مژده!**\nزیرمجموعه شما با کیف پول خود خرید کرد و \`${reward} TRX\` پاداش گرفتید!` })
        });
      }
    }

    // ۷. ارسال کانفیگ به خریدار در تلگرام
    const panelMsg = conf.web_panel_url ? `\n\n📊 **پنل مصرف:**\n${conf.web_panel_url}` : '';
    const successMsg = `🎉 **خرید آنی با کیف پول موفق بود!** ✅\n\n🚀 **سرویس اختصاصی شما:**\n\`${conf.v2ray_uri}\`${panelMsg}\n\n💳 موجودی باقی‌مانده: ${newBalance.toLocaleString()} تومان`;
    
    await fetch(`https://api.telegram.org/bot${TOKEN}/sendMessage`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_id: chat_id, text: successMsg, parse_mode: 'Markdown' })
    });

    // ۸. اطلاع‌رسانی به ادمین از فروش موفق
    if (TOKEN && ADMIN_ID) {
      const adminReportMsg = `💵 **خرید آنی (کسر از کیف پول)** ✅\n\n👤 خریدار: \`${chat_id}\`\n🛍 محصول: ${planData.title_fa}\n💰 مبلغ: ${price.toLocaleString()} تومان\n\n*(سرویس در لحظه تحویل داده شد)*`;
      await fetch(`https://api.telegram.org/bot${TOKEN}/sendMessage`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chat_id: ADMIN_ID, text: adminReportMsg, parse_mode: 'Markdown' })
      });
    }

    return res.status(200).json({ ok: true, message: "خرید موفق بود! کانفیگ به تلگرام شما ارسال شد." });

  } catch (e) {
    return res.status(500).json({ error: e.message });
  }
}
