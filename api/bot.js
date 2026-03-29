import { createClient } from "@supabase/supabase-js";

export default async function handler(req, res) {
  const TOKEN = process.env.TELEGRAM_TOKEN;
  
  if (!TOKEN) {
    return res.status(500).json({ error: "لطفاً توکن BotFather را در ورسل ذخیره کنید." });
  }

  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SUPABASE_KEY = process.env.SUPABASE_ANON_KEY || process.env.SUPABASE_KEY;

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

  if (req.method === 'POST') {
    const update = req.body;
    if (!SUPABASE_URL || !SUPABASE_KEY) return res.status(200).send('OK');

    const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);

    const sendTg = async (chatId, text, replyMarkup = null) => {
      const payload = { chat_id: chatId, text: text, parse_mode: "Markdown" };
      if (replyMarkup) payload.reply_markup = replyMarkup;
      await fetch(`https://api.telegram.org/bot${TOKEN}/sendMessage`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
    };

    if (update.message && update.message.text) {
      const chatId = update.message.chat.id;
      const text = update.message.text;
      const firstName = update.message.from.first_name || "کاربر عزیز";
      const username = update.message.from.username || null;

      // ---- دستور /start ----
      if (text.startsWith('/start')) {
        let referrerId = null;
        const parts = text.split(' ');
        if (parts.length > 1 && !isNaN(parts[1])) {
          referrerId = parseInt(parts[1]);
          if (referrerId === chatId) referrerId = null; 
        }

        try {
          const { data: user } = await supabase.from('users').select('chat_id').eq('chat_id', chatId).maybeSingle();
          if (!user) {
            await supabase.from('users').insert({
              chat_id: chatId, username: username, referrer_id: referrerId,
              wallet_balance: 0, wallet_trx: 0, total_referrals: 0, role: 'user'
            });
            if (referrerId) {
              const { data: refUser } = await supabase.from('users').select('total_referrals').eq('chat_id', referrerId).maybeSingle();
              if (refUser) {
                await supabase.from('users').update({ total_referrals: (refUser.total_referrals || 0) + 1 }).eq('chat_id', referrerId);
                await sendTg(referrerId, `🎊 **مژده!**\nیک دوست جدید با لینک اختصاصی شما به خانواده نُوا پیوست. 🥳`);
              }
            }
          }
        } catch (dbErr) { console.error("DB Error:", dbErr); }

        const hybridKeyboard = {
          keyboard: [
            [{ text: "💎 باز کردن مینی اپ (سرعت بالا)", web_app: { url: `https://${req.headers['host']}/` } }],
            [{ text: "🛒 خرید (اینترنت ضعیف)" }, { text: "👤 داشبورد من" }],
            [{ text: "🎧 پشتیبانی" }, { text: "🔗 لینک دعوت من" }]
          ],
          resize_keyboard: true,
          is_persistent: true
        };

        const welcomeText = `✨ **سلام ${firstName}! به نُوا وی‌پی‌ان خوش آمدی.** 🚀\n\nما اینجا هستیم تا تجربه‌ای بدون مرز، امن و پرسرعت از اینترنت را برای شما فراهم کنیم. سرورهای ما مخصوص استریم، ترید و گیمینگ بهینه‌سازی شده‌اند.\n\n📱 **راحت‌ترین روش خرید:** اگر اینترنت متصل است، روی دکمه بزرگ **"باز کردن مینی اپ"** ضربه بزنید تا فروشگاه گرافیکی باز شود.\n\n⚡️ **روش جایگزین:** در صورت کندی اینترنت، از دکمه‌های متنی پایین (مانند "🛒 خرید") استفاده کنید. 👇`;
        await sendTg(chatId, welcomeText, hybridKeyboard);
      }

      // ---- دکمه: خرید ----
      else if (text === "🛒 خرید (اینترنت ضعیف)") {
        const { data: plans } = await supabase.from('plans').select('*').eq('is_active', true).order('price_toman', { ascending: true });
        if (!plans || plans.length === 0) {
          await sendTg(chatId, "⚠️ **انبار موقتاً خالی است!**\nدر حال حاضر تمامی سرورها به فروش رفته‌اند. لطفاً ساعاتی دیگر سر بزنید.");
          return res.status(200).send('OK');
        }

        let inlineKeyboard = [];
        plans.forEach(p => {
          // خواندن قیمت دلاری مستقیم از دیتابیس
          const usdText = p.price_usd ? ` | $${p.price_usd}` : '';
          inlineKeyboard.push([{ 
            text: `🚀 ${p.title_fa} - ${Number(p.price_toman).toLocaleString()} تومان${usdText}`, 
            callback_data: `buy_${p.internal_name}` 
          }]);
        });

        await sendTg(chatId, "🛍 **فروشگاه نُوا وی‌پی‌ان**\n\nبرای تهیه اشتراک، لطفاً یکی از پلن‌های قدرتمند زیر را انتخاب کنید:", { inline_keyboard: inlineKeyboard });
      }

      // ---- دکمه: داشبورد ----
      else if (text === "👤 داشبورد من") {
        const { data: user } = await supabase.from('users').select('wallet_trx').eq('chat_id', chatId).maybeSingle();
        const { data: services } = await supabase.from('configs').select('*').eq('owner_id', chatId).eq('status', 'sold');
        
        let dashMsg = `📊 **پنل کاربری اختصاصی شما**\n\n👤 شناسه کاربری: \`${chatId}\`\n💰 پورسانت دریافتی: \`${user?.wallet_trx || 0} TRX\`\n\n📦 **سرویس‌های فعال شما:**\n➖➖➖➖➖➖➖➖➖➖\n`;
        
        if (services && services.length > 0) {
          services.forEach((s, index) => {
            dashMsg += `🔹 **سرویس ${index + 1}:** ${s.plan_name}\n🔑 **کد اتصال شما (جهت کپی کلیک کنید):**\n\`${s.v2ray_uri}\`\n\n🌐 [ورود به پنل مشاهده حجم و زمان](${s.web_panel_url})\n➖➖➖➖➖➖➖➖➖➖\n`;
          });
          dashMsg += `💡 *کد بالا را کپی کرده و در برنامه‌های V2Ray یا NapsternetV جای‌گذاری کنید.*`;
        } else {
          dashMsg += "❌ شما در حال حاضر هیچ اشتراک فعالی ندارید.\nبرای تهیه اشتراک از دکمه «خرید» استفاده کنید.";
        }
        
        await sendTg(chatId, dashMsg, { disable_web_page_preview: true });
      }

      // ---- دکمه: لینک دعوت ----
      else if (text === "🔗 لینک دعوت من") {
        const botUsername = "NoovaVpn_Bot"; 
        const refLink = `https://t.me/${botUsername}?start=${chatId}`;
        const refMsg = `🤝 **کسب درآمد دلاری با نُوا** 💸\n\nشما می‌توانید با معرفی نُوا به دوستان خود، درآمد ارزی داشته باشید!\n\n🔗 **لینک دعوت اختصاصی شما:**\n\`${refLink}\`\n\n🎁 **پاداش شما:**\nبه ازای هر **۱ گیگابایت** خریدی که دوستان شما انجام دهند، مبلغ **۰.۵ ترون (TRX)** به کیف پول شما در داشبورد واریز می‌گردد!`;
        await sendTg(chatId, refMsg);
      }

      // ---- دکمه: پشتیبانی ----
      else if (text === "🎧 پشتیبانی") {
        await sendTg(chatId, "👨‍💻 **پشتیبانی ۲۴ ساعته نُوا**\n\nما همیشه در کنار شما هستیم! اگر در اتصال مشکلی دارید یا پیش از خرید نیاز به مشاوره دارید، به آیدی زیر پیام دهید:\n\n💬 **آیدی پشتیبانی:** @NovaVPN_Sup");
      }

      // ---- دریافت هش تراکنش ----
      else if (text.length >= 30 && text.match(/^[a-zA-Z0-9]+$/)) {
        const { data: pendingTx } = await supabase.from('transactions').select('id').eq('chat_id', chatId).eq('status', 'pending_verification').order('created_at', { ascending: false }).limit(1).maybeSingle();
        
        if (pendingTx) {
          await supabase.from('transactions').update({ txid_or_receipt: text }).eq('id', pendingTx.id);
          await sendTg(chatId, "⏳ **رسید شما با موفقیت ثبت شد.** ✅\n\nتراکنش در حال بررسی توسط کارشناسان (یا تایید شبکه بلاک‌چین) است. به محض تایید نهایی، کانفیگ شما **به صورت خودکار** در همین چت ارسال خواهد شد.\n\nاز شکیبایی شما صمیمانه سپاسگزاریم! 🙏");
        }
      }
    }

    // --------------------------------------------------
    // ۲. پردازش دکمه‌های شیشه‌ای (فاکتور خرید)
    // --------------------------------------------------
    else if (update.callback_query) {
      const call = update.callback_query;
      const chatId = call.message.chat.id;
      const data = call.data;

      if (data.startsWith('buy_')) {
        const planName = data.replace('buy_', '');
        const { data: plan } = await supabase.from('plans').select('*').eq('internal_name', planName).maybeSingle();
        
        if (plan) {
          await supabase.from('transactions').insert({
            chat_id: chatId, amount_toman: plan.price_toman, target_plan: planName, status: 'pending_verification', txid_or_receipt: 'AWAITING_TXID'
          });

          // دریافت قیمت لحظه‌ای ترون
          let trxPriceInUsd = 0.12; 
          try {
            const r = await fetch("https://api.coingecko.com/api/v3/simple/price?ids=tron&vs_currencies=usd");
            const d = await r.json();
            if (d.tron && d.tron.usd) trxPriceInUsd = d.tron.usd;
          } catch(e) { console.log("Fetch Crypto error:", e.message); }

          // محاسبه دقیق مبلغ دلاری از دیتابیس
          const exactUsdt = plan.price_usd || (plan.price_toman / 60000).toFixed(2);
          const exactTrx = (exactUsdt / trxPriceInUsd).toFixed(1);

          const walletAddress = "TSgfCoCsrEXJs6RKkaCJF64wXpYVTRejZ3"; 
          
          const invoiceMsg = `🧾 **فاکتور پرداخت شما صادر شد**\n\n📌 **سرویس انتخابی:** ${plan.title_fa}\n💵 **ارزش ریالی:** ${Number(plan.price_toman).toLocaleString()} تومان\n\n👇 **لطفاً یکی از مقادیر زیر را به کیف پول ما واریز کنید:**\n\n🟢 **پرداخت با تتر (USDT - TRC20):**\nمبلغ دقیق: \`${exactUsdt}\` دلار\n\n🔴 **پرداخت با ترون (TRX):**\nمبلغ دقیق: \`${exactTrx}\` ترون\n\n💳 **آدرس کیف پول ما (جهت کپی کلیک کنید):**\n\`${walletAddress}\`\n\n➖➖➖➖➖➖➖➖➖➖\n⚠️ **مرحله نهایی و مهم:**\nپس از انجام موفقیت‌آمیز واریز، **هش تراکنش (TXID)** خود را کپی کرده و مستقیماً در همین ربات ارسال کنید تا سرویس شما فعال شود.`;
          
          await sendTg(chatId, invoiceMsg);
        }
      }
      
      await fetch(`https://api.telegram.org/bot${TOKEN}/answerCallbackQuery`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ callback_query_id: call.id })
      });
    }

    return res.status(200).send('OK');
  }

  return res.status(405).send('Method Not Allowed');
}
