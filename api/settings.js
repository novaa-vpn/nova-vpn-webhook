import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY // استفاده از Service Role برای دسترسی کامل در بک‌اند
);

export default async function handler(req, res) {
  // فعال‌سازی CORS برای مینی‌اپ تلگرام
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

  if (req.method === 'OPTIONS') return res.status(200).end();

  try {
    if (req.method === 'GET') {
      const { data, error } = await supabase.from('settings').select('*').eq('id', 1).single();
      if (error) throw error;
      return res.status(200).json(data);
    }

    if (req.method === 'POST') {
      // بررسی احراز هویت ادمین
      const authHeader = req.headers.authorization;
      if (authHeader !== `Bearer ${process.env.ADMIN_TOKEN}`) {
        return res.status(401).json({ error: 'Unauthorized' });
      }

      const { usd_rate } = req.body;
      if (!usd_rate) return res.status(400).json({ error: 'usd_rate is required' });

      const { data, error } = await supabase
        .from('settings')
        .update({ usd_rate, updated_at: new Date() })
        .eq('id', 1)
        .select()
        .single();

      if (error) throw error;
      return res.status(200).json(data);
    }

    return res.status(405).json({ error: 'Method not allowed' });
  } catch (error) {
    return res.status(500).json({ error: error.message });
  }
}
