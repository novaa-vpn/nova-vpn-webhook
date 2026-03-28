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

    if (update.message && update.message.text === '/start') {
      const chatId = update.message.chat.id;
      const firstName = update.message.from.first_name;
      
      // متن خوش‌آمدگویی و دکمه باز کردن مینی‌اپ
      const welcomeText = `سلام ${firstName} عزیز! 🚀\nبه Nova VPN خوش آمدید.\n\nبرای خرید سرویس، مدیریت اکانت و مشاهده موجودی، از دکمه زیر استفاده کنید:`;
      
      const keyboard = {
        inline_keyboard: [
          [
            {
              text: "💎 باز کردن پنل هوشمند نُوا",
              web_app: { url: `https://${req.headers['host']}/` }
            }
          ],
          [
            { text: "🎧 پشتیبانی", url: "https://t.me/NovaVPN_Sup" },
            { text: "📢 کانال ما", url: "https://t.me/NovaVPN_Net" }
          ]
        ]
      };

      try {
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
      } catch (e) {
        console.error("Error sending message:", e);
      }
    }

    return res.status(200).send('OK');
  }

  return res.status(405).send('Method Not Allowed');
}
