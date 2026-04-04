// api/usage.js
export default async function handler(req, res) {
  // تنظیمات CORS برای مینی‌اپ
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  
  if (req.method === 'OPTIONS') return res.status(200).end();

  const { sub_link } = req.query;

  if (!sub_link || !sub_link.startsWith('http')) {
    return res.status(400).json({ error: "لینک ساب معتبر نیست." });
  }

  try {
    // درخواست به لینک ساب پنل شما
    const response = await fetch(sub_link, {
      method: 'GET',
      headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)' }
    });

    // خواندن هدر حاوی اطلاعات مصرف
    const userInfo = response.headers.get('subscription-userinfo');

    if (!userInfo) {
      return res.status(404).json({ error: "اطلاعات مصرف در این لینک یافت نشد (احتمالاً پنل پشتیبانی نمی‌کند)." });
    }

    // تجزیه کردن هدر (مثال: upload=100; download=200; total=1000; expire=1234567)
    const stats = {};
    userInfo.split(';').forEach(part => {
      const [key, value] = part.trim().split('=');
      if (key && value) stats[key] = Number(value);
    });

    // تبدیل بایت به گیگابایت
    const bytesToGB = (bytes) => (bytes / (1024 ** 3)).toFixed(2);

    const totalGB = bytesToGB(stats.total || 0);
    const usedGB = bytesToGB((stats.upload || 0) + (stats.download || 0));
    const remainGB = (totalGB - usedGB).toFixed(2);
    
    // محاسبه روزهای باقی‌مانده
    let remainDays = "نامحدود";
    if (stats.expire) {
      const now = Math.floor(Date.now() / 1000);
      const diffSeconds = stats.expire - now;
      remainDays = diffSeconds > 0 ? Math.floor(diffSeconds / 86400) : "منقضی شده";
    }

    return res.status(200).json({
      total_gb: totalGB,
      used_gb: usedGB,
      remain_gb: remainGB > 0 ? remainGB : 0,
      remain_days: remainDays,
      raw_expire: stats.expire
    });

  } catch (error) {
    return res.status(500).json({ error: "خطا در ارتباط با سرور VPN." });
  }
}
