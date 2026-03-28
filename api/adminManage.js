import { supabase } from "../lib/supabase";

export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method Not Allowed' });

  const { action, admin_pass, tx_id, plan, v2ray, panel, message_text, target_chat_id } = req.body;

  if (admin_pass !== 'admin123') {
    return res.status(401).json({ error: "Unauthorized" });
  }

  const TOKEN = process.env.TELEGRAM_TOKEN;

  const sendTg = async (id, text) => {
    try {
      await fetch(`https://api.telegram.org/bot${TOKEN}/sendMessage`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chat_id: id, text, parse_mode: "Markdown" })
      });
    } catch (e) { console.error(e); }
  };

  try {
    if (action === 'get_pending') {
      const { data } = await supabase.from('transactions').select('*').in('status', ['pending', 'pending_verification']).order('created_at', { ascending: false });
      return res.status(200).json({ receipts: data || [] });
    }

    if (action === 'get_inventory') {
      const { data } = await supabase.from('configs').select('plan_name').eq('status', 'available');
      const stats = data.reduce((acc, curr) => {
        acc[curr.plan_name] = (acc[curr.plan_name] || 0) + 1;
        return acc;
      }, {});
      return res.status(200).json({ stats });
    }

    if (action === 'add_config') {
      const { error } = await supabase.from('configs').insert({ plan_name: plan, v2ray_uri: v2ray, web_panel_url: panel });
      if (error) throw error;
      return res.status(200).json({ ok: true });
    }

    if (action === 'get_users') {
      const { data } = await supabase.from('users').select('*').order('created_at', { ascending: false }).limit(50);
      return res.status(200).json({ users: data || [] });
    }

    if (action === 'approve') {
      const { data: tx } = await supabase.from('transactions').select('*').eq('id', tx_id).single();
      const { data: conf } = await supabase.from('configs').select('*').eq('plan_name', tx.target_plan).eq('status', 'available').limit(1).single();
      
      if (!conf) throw new Error("انبار خالی است!");

      await supabase.from('configs').update({ status: 'sold', owner_id: tx.chat_id, sold_at: new Date() }).eq('id', conf.id);
      await supabase.from('transactions').update({ status: 'approved', handled_at: new Date() }).eq('id', tx_id);

      // پورسانت معرف
      const { data: user } = await supabase.from('users').select('referrer_id').eq('chat_id', tx.chat_id).single();
      if (user?.referrer_id) {
        const { data: planData } = await supabase.from('plans').select('gb_amount').eq('internal_name', tx.target_plan).single();
        const reward = (planData?.gb_amount || 0) * 0.5;
        if (reward > 0) {
          const { data: ref } = await supabase.from('users').select('wallet_trx').eq('chat_id', user.referrer_id).single();
          await supabase.from('users').update({ wallet_trx: (ref.wallet_trx || 0) + reward }).eq('chat_id', user.referrer_id);
          await sendTg(user.referrer_id, `🎊 **پاداش دعوت!**\nمبلغ \`${reward} TRX\` بابت خرید زیرمجموعه به حساب شما واریز شد.`);
        }
      }

      await sendTg(tx.chat_id, `🎉 **سفارش تایید شد!**\n\n🚀 کانفیگ:\n\`${conf.v2ray_uri}\`\n\n📊 پنل مصرف:\n${conf.web_panel_url}`);
      return res.status(200).json({ ok: true });
    }

    if (action === 'reject') {
      const { data: tx } = await supabase.from('transactions').select('chat_id').eq('id', tx_id).single();
      await supabase.from('transactions').update({ status: 'rejected' }).eq('id', tx_id);
      await sendTg(tx.chat_id, "❌ **پرداخت شما تایید نشد.**\nدر صورت اشتباه، با پشتیبانی در تماس باشید.");
      return res.status(200).json({ ok: true });
    }

    if (action === 'broadcast') {
      const { data: users } = await supabase.from('users').select('chat_id');
      for (const u of users) {
        await sendTg(u.chat_id, message_text);
      }
      return res.status(200).json({ ok: true });
    }

    return res.status(400).json({ error: "Invalid action" });
  } catch (err) {
    return res.status(500).json({ error: err.message });
  }
}
