import { createClient } from '@supabase/supabase-js';

const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY);

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') return res.status(200).end();

  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  try {
    // مقادیر دریافتی از فرانت‌اند ارتقا یافته
    const { 
      chat_id, 
      plan_gb, 
      price_irr, 
      tx_hash, 
      crypto_amount, 
      crypto_network, 
      wallet_id 
    } = req.body;

    if (!chat_id || !tx_hash || !wallet_id) {
      return res.status(400).json({ error: 'Missing required fields' });
    }

    // 1. ثبت رسید در دیتابیس
    const { data: receiptData, error: receiptError } = await supabase
      .from('receipts')
      .insert([{
        chat_id,
        plan_gb,
        price_irr,
        tx_hash,
        crypto_amount,
        crypto_network,
        wallet_id,
        status: 'pending' // نیازمند تایید ادمین
      }])
      .select()
      .single();

    if (receiptError) throw receiptError;

    // 2. افزایش تعداد دفعات استفاده از کیف پول (برای سیستم تقسیم بار)
    const { error: walletError } = await supabase.rpc('increment_wallet_usage', { row_id: wallet_id });
    // اگر RPC تعریف نشده است، به صورت دستی آپدیت می‌کنیم:
    if (walletError) {
      const { data: wallet } = await supabase.from('wallets').select('usage_count').eq('id', wallet_id).single();
      if (wallet) {
        await supabase.from('wallets').update({ usage_count: wallet.usage_count + 1 }).eq('id', wallet_id);
      }
    }

    // (اختیاری) در اینجا می‌توانید به ربات تلگرام پیام ادمین ارسال کنید که رسید جدید ثبت شده است
    
    return res.status(200).json({ success: true, data: receiptData });

  } catch (error) {
    return res.status(500).json({ error: error.message });
  }
}
