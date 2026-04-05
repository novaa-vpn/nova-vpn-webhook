import { createClient } from '@supabase/supabase-js';

export default async function handler(req, res) {
  // فعال‌سازی CORS برای مینی‌اپ تلگرام
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

  if (req.method === 'OPTIONS') return res.status(200).end();

  try {
    // گرفتن متغیرهای محیطی به صورت امن داخل تابع
    const supabaseUrl = process.env.SUPABASE_URL;
    const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.SUPABASE_ANON_KEY || process.env.SUPABASE_KEY;

    if (!supabaseUrl || !supabaseKey) {
      throw new Error("تنظیمات دیتابیس در سرور یافت نشد.");
    }

    const supabase = createClient(supabaseUrl, supabaseKey);

    if (req.method === 'GET') {
      const { data, error } = await supabase.from('settings').select('*').eq('id', 1).maybeSingle();
      if (error) throw error;
      return res.status(200).json(data || { usd_rate: 60000 });
    }

    if (req.method === 'POST') {
      // بررسی احراز هویت ادمین با پشتیبانی از رمز جایگزین
      const authHeader = req.headers.authorization;
      const adminToken = process.env.ADMIN_TOKEN || process.env.ADMIN_PASSWORD || "Nova@Manager2026";
      
      if (authHeader !== `Bearer ${adminToken}`) {
        return res.status(401).json({ error: 'Unauthorized' });
      }

      const { usd_rate } = req.body;
      if (!usd_rate) return res.status(400).json({ error: 'usd_rate is required' });

      // آپسرت برای اطمینان از اینکه اگر رکورد نبود هم ساخته شود
      const { data, error } = await supabase
        .from('settings')
        .upsert({ id: 1, usd_rate: usd_rate, updated_at: new Date() })
        .select()
        .single();

      if (error) throw error;
      return res.status(200).json(data);
    }

    return res.status(405).json({ error: 'Method not allowed' });
  } catch (error) {
    console.error("Settings API Error:", error);
    return res.status(500).json({ error: error.message });
  }
}
