import { createClient } from "@supabase/supabase-js";

export default async function handler(req, res) {
  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SUPABASE_KEY = process.env.SUPABASE_ANON_KEY || process.env.SUPABASE_KEY;
  const TOKEN = process.env.TELEGRAM_TOKEN;
  
  // آدرس ولت‌های شما برای هر ارز (بر اساس کدهای فرانت‌اند)
  const WALLETS = {
    USDT: "TSgfCoCsrEXJs6RKkaCJF64wXpYVTRejZ3",
    TRX:  "TSgfCoCsrEXJs6RKkaCJF64wXpYVTRejZ3",
    TON:  "UQCpWdG73bwuwFAp2EDQLLkl6VhTGpVVJDre8X02qvJ5OJem",
    XRP:  "rJ8A6gUZzwXm9XJv2fLaTGd6GkpBMdmm8F"
  };

  if (!SUPABASE_URL || !SUPABASE_KEY) {
    return res.status(500).json({ error: "Supabase credentials missing." });
  }

  const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);

  try {
    // ۱. پیدا کردن تمام تراکنش‌های معلق
    const { data: pendingTxs, error: txError } = await supabase
      .from('transactions')
      .select('*')
      .eq('status', 'pending_verification');

    if (txError) throw txError;
    if (!pendingTxs || pendingTxs.length === 0) {
      return res.status(200).json({ message: "هیچ تراکنش معلقی برای بررسی وجود ندارد." });
    }

    let results = [];

    // ۲. بررسی تک تک تراکنش‌ها در شبکه‌های مختلف
    for (const tx of pendingTxs) {
      const txid = tx.txid_or_receipt;
      const currency = tx.crypto_currency;
      let isPaymentValid = false;
      
      if (!txid || txid.length < 10) continue;

      try {
        // ==========================================
        // 🟢 بررسی شبکه TRON (برای USDT و TRX)
        // ==========================================
        if (currency === 'USDT' || currency === 'TRX') {
          const response = await fetch(`https://apilist.tronscanapi.com/api/transaction-info?hash=${txid}`);
          const scanData = await response.json();

          if (scanData && scanData.contractRet === "SUCCESS") {
            if (currency === 'USDT' && scanData.trc20TransferInfo) {
              for (const t of scanData.trc20TransferInfo) {
                if (t.symbol === "USDT" && t.to_address === WALLETS.USDT) {
                  const amountPaid = parseFloat(t.amount_str) / 1e6; 
                  if (amountPaid >= (tx.crypto_amount - 0.1)) isPaymentValid = true;
                }
              }
            } else if (currency === 'TRX' && scanData.contractData) {
              const contract = scanData.contractData;
              if (contract.to_address === WALLETS.TRX) {
                const amountPaid = parseFloat(contract.amount) / 1e6; 
                if (amountPaid >= (tx.crypto_amount - 1)) isPaymentValid = true;
              }
            }
          }
        } 
        // ==========================================
        // 🔵 بررسی شبکه TON (Toncoin)
        // ==========================================
        else if (currency === 'TON') {
          const response = await fetch(`https://tonapi.io/v2/events/${txid}`);
          const data = await response.json();
          
          if (data && data.actions && data.actions.length > 0) {
            for (const action of data.actions) {
              // بررسی موفق بودن تراکنش و نوع آن
              if (action.type === 'TonTransfer' && action.status === 'ok') {
                const transfer = action.TonTransfer;
                const amountPaid = transfer.amount / 1e9; // تون ۹ صفر اعشار دارد
                
                // در شبکه تون با یک ارفاق جزئی 0.05 چک میکنیم
                if (amountPaid >= (tx.crypto_amount - 0.05)) {
                  isPaymentValid = true;
                  break;
                }
              }
            }
          }
        }
        // ==========================================
        // ⚫ بررسی شبکه RIPPLE (XRP)
        // ==========================================
        else if (currency === 'XRP') {
          const response = await fetch(`https://api.xrpscan.com/api/v1/tx/${txid}`);
          const data = await response.json();
          
          if (data && data.meta && data.meta.TransactionResult === "tesSUCCESS") {
            if (data.Destination === WALLETS.XRP) {
              const amountPaid = parseFloat(data.Amount) / 1e6; // ریپل ۶ صفر اعشار دارد
              if (amountPaid >= (tx.crypto_amount - 0.5)) isPaymentValid = true;
            }
          }
        }

        // ==========================================
        // 🚀 عملیات تحویل خودکار (در صورت معتبر بودن)
        // ==========================================
        if (isPaymentValid) {
          const { data: conf } = await supabase.from('configs').select('*').eq('plan_name', tx.target_plan).eq('status', 'available').limit(1).maybeSingle();
          
          if (conf) {
            await supabase.from('configs').update({ status: 'sold', owner_id: tx.chat_id, sold_at: new Date() }).eq('id', conf.id);
            await supabase.from('transactions').update({ status: 'approved', handled_at: new Date() }).eq('id', tx.id);

            // واریز پاداش معرف
            const { data: buyer } = await supabase.from('users').select('referrer_id').eq('chat_id', tx.chat_id).maybeSingle();
            if (buyer?.referrer_id) {
              const { data: planData } = await supabase.from('plans').select('gb_amount').eq('internal_name', tx.target_plan).maybeSingle();
              const reward = (planData?.gb_amount || 0) * 0.5;
              if (reward > 0) {
                const { data: refUser } = await supabase.from('users').select('wallet_trx').eq('chat_id', buyer.referrer_id).maybeSingle();
                await supabase.from('users').update({ wallet_trx: (refUser?.wallet_trx || 0) + reward }).eq('chat_id', buyer.referrer_id);
                await fetch(`https://api.telegram.org/bot${TOKEN}/sendMessage`, {
                  method: 'POST', headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ chat_id: buyer.referrer_id, text: `🎊 **مژده!**\nزیرمجموعه شما خریدی انجام داد و \`${reward} TRX\` پاداش گرفتید!` })
                });
              }
            }

            // ارسال کانفیگ
            const successMsg = `🎉 **تراکنش شما (${currency}) به صورت خودکار تایید شد!**\n\n🚀 **سرویس اختصاصی شما:**\n\`${conf.v2ray_uri}\`\n\n📊 **پنل مصرف:**\n${conf.web_panel_url}`;
            await fetch(`https://api.telegram.org/bot${TOKEN}/sendMessage`, {
              method: 'POST', headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ chat_id: tx.chat_id, text: successMsg, parse_mode: 'Markdown' })
            });

            results.push({ txid, status: `Approved & Delivered (${currency})` });
          } else {
            results.push({ txid, status: "Inventory Empty!" });
            const adminMsg = `⚠️ **هشدار مهم انبار!**\nپرداخت کاربر در شبکه ${currency} تایید شد اما انبار خالی است!`;
            await fetch(`https://api.telegram.org/bot${TOKEN}/sendMessage`, {
              method: 'POST', headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ chat_id: process.env.ADMIN_CHAT_ID || WALLETS.TRX, text: adminMsg }) 
            });
          }
        } else {
          results.push({ txid, status: "Invalid or Not Confirmed" });
        }

      } catch (err) {
        results.push({ txid, error: err.message });
      }
    }

    return res.status(200).json({ checked: pendingTxs.length, results });

  } catch (e) {
    return res.status(500).json({ error: e.message });
  }
}
