import { supabase } from "../lib/supabase"

export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method Not Allowed' });

  const { action, admin_pass, tx_id, target_chat_id, message_text } = req.body;

  // یک رمز ساده برای جلوگیری از دسترسی افراد متفرقه به پنل (می‌توانید تغییر دهید)
  if (admin_pass !== 'admin123') {
    return res.status(401).json({ error: "رمز عبور ادمین اشتباه است." });
  }

  const TELEGRAM_TOKEN = process.env.TELEGRAM_TOKEN;

  // --- تابع کمکی برای ارسال پیام به تلگرام ---
  const sendTelegramMessage = async (chatId, text) => {
    try {
      await fetch(`https://api.telegram.org/bot${TELEGRAM_TOKEN}/sendMessage`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chat_id: chatId, text: text, parse_mode: "Markdown" })
      });
    } catch (err) {
      console.error("Telegram sending error:", err);
    }
  };

  try {
    // ۱. دریافت لیست تراکنش‌های معلق
    if (action === 'get_pending') {
      const { data, error } = await supabase
        .from('transactions')
        .select('*')
        .in('status', ['pending', 'pending_verification'])
        .order('created_at', { ascending: false });
        
      if (error) throw error;
      return res.status(200).json({ receipts: data });
    }

    // ۲. تایید فاکتور و تحویل کانفیگ
    else if (action === 'approve') {
      if (!tx_id) return res.status(400).json({ error: "آیدی تراکنش نامعتبر است." });

      // گرفتن اطلاعات تراکنش
      const { data: txData } = await supabase.from('transactions').select('*').eq('id', tx_id).single();
      if (!txData) return res.status(404).json({ error: "تراکنش یافت نشد." });

      // پیدا کردن یک کانفیگ آزاد در انبار برای این پلن
      const { data: configData } = await supabase
        .from('configs')
        .select('*')
        .eq('plan_name', txData.target_plan)
        .eq('status', 'available')
        .limit(1)
        .single();

      if (!configData) {
        return res.status(400).json({ error: "انبار خالی است! هیچ کانفیگ آزادی برای این پلن وجود ندارد." });
      }

      // فروش کانفیگ و تایید تراکنش
      await supabase.from('configs').update({ status: 'sold', owner_id: txData.chat_id, sold_at: new Date() }).eq('id', configData.id);
      await supabase.from('transactions').update({ status: 'approved', handled_at: new Date() }).eq('id', tx_id);

      // --- محاسبه پورسانت معرف (0.5 ترون به ازای هر 1 گیگ) ---
      const { data: buyer } = await supabase.from('users').select('*').eq('chat_id', txData.chat_id).single();
      if (buyer && buyer.referrer_id) {
        // بدست آوردن حجم پلن
        const { data: planData } = await supabase.from('plans').select('gb_amount').eq('internal_name', txData.target_plan).single();
        const gb = planData?.gb_amount || 0;
        
        if (gb > 0) {
          const rewardTrx = gb * 0.5; // قانون شما: 0.5 TRX به ازای هر 1 گیگ
          const { data: referrer } = await supabase.from('users').select('wallet_trx').eq('chat_id', buyer.referrer_id).single();
          
          if (referrer) {
            await supabase.from('users').update({ wallet_trx: Number(referrer.wallet_trx || 0) + rewardTrx }).eq('chat_id', buyer.referrer_id);
            // ارسال پیام تشویقی به معرف
            await sendTelegramMessage(buyer.referrer_id, `🎊 **مژده! پورسانت جدید واریز شد!**\n\nزیرمجموعه شما یک خرید انجام داد.\nمبلغ \`${rewardTrx} TRX\` به عنوان پاداش به کیف پول شما در ربات اضافه شد.`);
          }
        }
      }

      // ارسال پیام موفقیت و کانفیگ به مشتری
      const successMsg = `🎉 **سفارش شما تایید شد!**\n\nسپاس از خرید شما. سرویس شما هم‌اکنون فعال است.\n\n🚀 **کانفیگ اختصاصی شما:**\n\`${configData.v2ray_uri}\`\n\n📊 **لینک مشاهده مصرف (پنل وب):**\n${configData.web_panel_url}\n\nتیم پشتیبانی نُوا همواره در کنار شماست.`;
      await sendTelegramMessage(txData.chat_id, successMsg);

      return res.status(200).json({ success: true });
    }

    // ۳. رد کردن فاکتور
    else if (action === 'reject') {
      if (!tx_id) return res.status(400).json({ error: "آیدی تراکنش نامعتبر است." });
      
      const { data: txData } = await supabase.from('transactions').select('chat_id').eq('id', tx_id).single();
      await supabase.from('transactions').update({ status: 'rejected', handled_at: new Date() }).eq('id', tx_id);
      
      if (txData) {
        await sendTelegramMessage(txData.chat_id, "❌ **سفارش شما رد شد.**\n\nمتأسفانه پرداخت شما توسط کارشناسان ما تایید نشد. این مشکل ممکن است به دلیل مغایرت مبلغ واریزی یا اشتباه بودن هش تراکنش (TXID) باشد.\n\nلطفاً در صورت بروز مشکل با پشتیبانی در تماس باشید.");
      }
      return res.status(200).json({ success: true });
    }

    // ۴. ارسال پیام دستی (پشتیبانی) به کاربر خاص
    else if (action === 'send_message') {
      if (!target_chat_id || !message_text) return res.status(400).json({ error: "اطلاعات پیام ناقص است." });
      
      const formattedMsg = `💬 **پیام از طرف مدیریت نُوا:**\n\n${message_text}`;
      await sendTelegramMessage(target_chat_id, formattedMsg);
      return res.status(200).json({ success: true });
    }

    return res.status(400).json({ error: "عملیات نامشخص" });

  } catch (error) {
    console.error("Admin Action Error:", error);
    return res.status(500).json({ error: error.message });
  }
}
