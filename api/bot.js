import { supabase } from "../lib/supabase";

export default async function handler(req, res) {
  const TOKEN = process.env.TELEGRAM_TOKEN;
  
  // متد GET برای تنظیم Webhook (همان /setup)
  if (req.method === 'GET') {
    const protocol = req.headers['x-forwarded-proto'] || 'https';
    const host = req.headers['host'];
    const webhookUrl = `${protocol}://${host}/${TOKEN}`;
    
    try {
      const response = await fetch(`https://api.telegram.org/bot${TOKEN}/setWebhook?url=${webhookUrl}`);
      const data = await response.json();
      return res.status(200).json({ ok: true, webhook: data, url: webhookUrl });
    } catch (e) {
      return res.status(500).json({ error: e.message });
    }
  }

  // متد POST برای دریافت پیام‌های تلگرام
  if (req.method === 'POST') {
    const update = req.body;

    if (update.message && update.message.text) {
      const chatId = update.message.chat.id;
      const text = update.message.text;
      const firstName = update.message.from.first_name;
      const username = update.message.from.username || null;

      // --- مدیریت دستور /start و سیستم رفرال ---
      if (text.startsWith('/start')) {
        let referrerId = null;
        const parts = text.split(' ');
        if (parts.length > 1 && !isNaN(parts[1])) {
          referrerId = parseInt(parts[1]);
          if (referrerId === chatId) referrerId = null; // جلوگیری از دعوت خود شخص
        }

        try {
          // ۱. بررسی وجود کاربر در دیتابیس
          const { data: user } = await supabase
            .from('users')
            .select('*')
            .eq('chat_id', chatId)
            .maybeSingle();

          if (!user) {
            // ۲. ثبت کاربر جدید و اتصال به معرف
            await supabase.from('users').insert({
              chat_id: chatId,
              username: username,
              referrer_id: referrerId,
              wallet_balance: 0,
              wallet_trx: 0,
              total_referrals: 0,
              role: 'user'
            });

            // ۳. افزایش تعداد دعوت‌های موفق معرف
            if (referrerId) {
              const { data: refUser } = await supabase.from('users').select('total_referrals').eq('chat_id', referrerId).maybeSingle();
              if (refUser) {
                await supabase.from('users').update({ total_referrals: (refUser.total_referrals || 0) + 1 }).eq('chat_id', referrerId);
                
                // اطلاع‌رسانی به معرف (اختیاری)
                await fetch(`https://api.telegram.org/bot${TOKEN}/sendMessage`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({
                    chat_id: referrerId,
                    text: `🎊 **تبریک!** یک کاربر جدید با لینک دعوت شما عضو شد.`
                  })
                });
              }
            }
          } else {
            // آپدیت یوزرنیم در صورت تغییر
            if (user.username !== username) {
              await supabase.from('users').update({ username: username }).eq('chat_id', chatId);
            }
          }
        } catch (dbErr) {
          console.error("Database Error:", dbErr);
        }

        // متن خوش‌آمدمگویی حرفه‌ای
        const welcomeText = `سلام ${firstName} عزیز! به نُوا وی‌پی‌ان خوش آمدید. 🚀\n\n💎 **نُوا، سریع‌ترین و پایدارترین اینترنت آزاد استارلینک**\n\nبرای خرید سرویس، مدیریت اکانت و مشاهده درآمد خود، روی دکمه زیر کلیک کنید:`;
        
        const keyboard = {
          inline_keyboard: [
            [{ text: "⚡️ ورود به پنل هوشمند نُوا", web_app: { url: `https://${req.headers['host']}/` } }],
            [
              { text: "🎧 پشتیبانی", url: "https://t.me/NovaVPN_Sup" },
              { text: "📢 کانال اطلاع‌رسانی", url: "https://t.me/NovaVPN_Net" }
            ]
          ]
        };

        await fetch(`https://api.telegram.org/bot${TOKEN}/sendMessage`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            chat_id: chatId,
            text: welcomeText,
            reply_markup: keyboard,
            parse_mode: "Markdown"
          })
        });
      }
    }

    return res.status(200).send('OK');
  }

  return res.status(405).send('Method Not Allowed');
}
