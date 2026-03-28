import { supabase } from "../lib/supabase"

export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method Not Allowed' });

  const { txid, expectedAmount } = req.body;
  
  if (!txid) return res.status(400).json({ error: "TXID required" });

  // این همان ولتی است که در داشبورد به کاربر نمایش می‌دهید
  const MY_WALLET = "TSgfCoCsrEXJs6RKkaCJF64wXpYVTRejZ3"; 

  try {
    // دریافت اطلاعات تراکنش از بلاک‌چین ترون
    const tronGridUrl = `https://api.trongrid.io/v1/accounts/${MY_WALLET}/transactions/trc20`;
    const response = await fetch(tronGridUrl);
    const data = await response.json();

    if (!data.success || !data.data) {
      return res.status(400).json({ verified: false, reason: "TronGrid API is down or invalid response" });
    }

    // جستجوی هش تراکنش در بین آخرین واریزی‌های ولت شما
    const tx = data.data.find(t => t.transaction_id === txid);

    if (!tx) {
      return res.status(200).json({ verified: false, reason: "Transaction not found on the blockchain" });
    }

    // بررسی نوع ارز (USDT)، گیرنده و مقدار
    const isUSDT = tx.token_info.symbol === "USDT";
    const actualAmount = parseInt(tx.value) / Math.pow(10, tx.token_info.decimals);
    const isToMyWallet = tx.to === MY_WALLET;

    if (isUSDT && isToMyWallet && actualAmount >= expectedAmount) {
      // ✅ تراکنش صحیح است!
      return res.status(200).json({ verified: true, amount: actualAmount, message: "Payment verified successfully!" });
    } else {
      return res.status(200).json({ verified: false, reason: "Invalid amount or token type" });
    }

  } catch (e) {
    return res.status(500).json({ error: e.message });
  }
}
