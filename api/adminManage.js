import { createClient } from "@supabase/supabase-js";

export default async function handler(req, res) {
  try {
    if (req.method !== 'POST') return res.status(405).json({ error: 'Method Not Allowed' });

    const body = typeof req.body === 'string' ? JSON.parse(req.body) : (req.body || {});
    const { action, admin_pass, tx_id, plan, v2ray, panel, target_chat_id, plan_id, title_fa, price_toman, price_usd, status, role, amount, message_text } = body;
    
    const SECRET_PASS = process.env.ADMIN_PASSWORD || "Nova@Manager2026";
    if (admin_pass !== SECRET_PASS) return res.status(401).json({ error: "رمز عبور مدیریت اشتباه است." });

    const SUPABASE_URL = process.env.SUPABASE_URL;
    const SUPABASE_KEY = process.env.SUPABASE_ANON_KEY || process.env.SUPABASE_KEY;
    const TOKEN = process.env.TELEGRAM_TOKEN;

    const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);

    // ==========================================
    // 💬 بخش جدید: CRM و پشتیبانی (تیکتینگ)
    // ==========================================
    
    if (action === 'get_tickets') {
      const { data, error } = await supabase
        .from('support_tickets')
        .select(`*, users(username)`)
        .order('created_at', { ascending: true });
        
      if (error) {
        console.error("Get Tickets Error:", error.message);
        return res.status(200).json({ tickets: [] });
      }
      return res.status(200).json({ tickets: data || [] });
    }

    if (action === 'reply_ticket') {
      if (!target_chat_id || !message_text) throw new Error("اطلاعات ناقص است");
      
      await supabase.from('support_tickets').insert({
        chat_id: target_chat_id, sender: 'admin', message_text: message_text, is_read: true
      });

      const replyMsg = `👨‍💻 **پاسخ پشتیبانی:**\n\n${message_text}\n\n*(برای ارسال پیام جدید مجدداً از دکمه پشتیبانی استفاده کنید)*`;
      await fetch(`https://api.telegram.org/bot${TOKEN}/sendMessage`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chat_id: target_chat_id, text: replyMsg, parse_mode: 'Markdown' })
      });

      return res.status(200).json({ ok: true });
    }

    if (action === 'broadcast') {
      if (!message_text) throw new Error("متن پیام خالی است");
      
      const { data: users } = await supabase.from('users').select('chat_id');
      if (users && users.length > 0) {
        const broadcastMsg = `📢 **اطلاعیه نُوا وی‌پی‌ان:**\n\n${message_text}`;
        users.forEach(u => {
          fetch(`https://api.telegram.org/bot${TOKEN}/sendMessage`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ chat_id: u.chat_id, text: broadcastMsg, parse_mode: 'Markdown' })
          }).catch(() => {});
        });
      }
      return res.status(200).json({ ok: true, count: users ? users.length : 0 });
    }

    // ==========================================
    // 🛒 بخش مالی و فروشگاهی 
    // ==========================================

    if (action === 'get_pending') {
      const { data } = await supabase.from('transactions').select('*').eq('status', 'pending_verification').order('created_at', { ascending: false });
      return res.status(200).json({ receipts: data || [] });
    }

    if (action === 'approve') {
      const { data: tx } = await supabase.from('transactions').select('*').eq('id', tx_id).single();

      // --- 🆕 اضافه شدن منطق شارژ کیف پول ---
      if (tx.target_plan === 'wallet_topup') {
        const { data: user } = await supabase.from('users').select('wallet_balance').eq('chat_id', tx.chat_id).single();
        const newBalance = (Number(user?.wallet_balance) || 0) + Number(tx.amount_toman);

        await supabase.from('users').update({ wallet_balance: newBalance }).eq('chat_id', tx.chat_id);
        await supabase.from('transactions').update({ status: 'approved', handled_at: new Date() }).eq('id', tx_id);

        const msg = `💳 **کیف پول شما با موفقیت شارژ شد!**\n\n💰 مبلغ شارژ: ${Number(tx.amount_toman).toLocaleString()} تومان\n💵 موجودی فعلی: ${newBalance.toLocaleString()} تومان\n\nاکنون می‌توانید از موجودی خود برای خرید سریع استفاده کنید.`;
        await fetch(`https://api.telegram.org/bot${TOKEN}/sendMessage`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ chat_id: tx.chat_id, text: msg, parse_mode: 'Markdown' })
        });
        return res.status(200).json({ ok: true });
      }
      // --------------------------------------

      // منطق قبلی برای تحویل کانفیگ
      const { data: conf } = await supabase.from('configs').select('*').eq('plan_name', tx.target_plan).eq('status', 'available').limit(1).maybeSingle();
      if (!conf) throw new Error("انبار برای این پلن خالی است!");

      await supabase.from('configs').update({ status: 'sold', owner_id: tx.chat_id, sold_at: new Date() }).eq('id', conf.id);
      await supabase.from('transactions').update({ status: 'approved', handled_at: new Date() }).eq('id', tx_id);

      const panelMsg = conf.web_panel_url ? `\n\n📊 [پنل مصرف](${conf.web_panel_url})` : '';
      const msg = `🎉 **سرویس شما فعال شد!**\n\n🚀 **کد اتصال:**\n\`${conf.v2ray_uri}\`${panelMsg}`;
      await fetch(`https://api.telegram.org/bot${TOKEN}/sendMessage`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chat_id: tx.chat_id, text: msg, parse_mode: 'Markdown' })
      });
      return res.status(200).json({ ok: true });
    }

    if (action === 'reject') {
      await supabase.from('transactions').update({ status: 'rejected' }).eq('id', tx_id);
      return res.status(200).json({ ok: true });
    }

    if (action === 'get_plans_list') {
      const { data } = await supabase.from('plans').select('*').order('price_toman', { ascending: true });
      return res.status(200).json({ plans: data || [] });
    }

    if (action === 'add_plan') {
      await supabase.from('plans').insert({ internal_name: plan_id, title_fa, title_en: title_fa, price_toman, price_usd, is_active: true });
      return res.status(200).json({ ok: true });
    }

    if (action === 'toggle_plan') {
      await supabase.from('plans').update({ is_active: status }).eq('internal_name', plan_id);
      return res.status(200).json({ ok: true });
    }

    if (action === 'delete_plan') {
      await supabase.from('plans').delete().eq('internal_name', plan_id);
      return res.status(200).json({ ok: true });
    }

    if (action === 'get_users') {
      const { data } = await supabase.from('users').select('*').order('joined_at', { ascending: false }).limit(200);
      return res.status(200).json({ users: data || [] });
    }

    if (action === 'update_user_balance') {
      await supabase.from('users').update({ wallet_balance: amount }).eq('chat_id', target_chat_id);
      return res.status(200).json({ ok: true });
    }

    if (action === 'update_user_role') {
      await supabase.from('users').update({ role: role }).eq('chat_id', target_chat_id);
      return res.status(200).json({ ok: true });
    }

    if (action === 'get_inventory') {
      const { data } = await supabase.from('configs').select('plan_name').eq('status', 'available');
      const stats = data.reduce((acc, curr) => { acc[curr.plan_name] = (acc[curr.plan_name] || 0) + 1; return acc; }, {});
      return res.status(200).json({ stats });
    }

    if (action === 'add_config') {
      await supabase.from('configs').insert({ plan_name: plan, v2ray_uri: v2ray, web_panel_url: panel || '' });
      return res.status(200).json({ ok: true });
    }

    return res.status(400).json({ error: "Action not found" });
  } catch (err) { return res.status(500).json({ error: err.message }); }
}
