import { createClient } from '@supabase/supabase-js';

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
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

    const authHeader = req.headers.authorization;
    const adminToken = process.env.ADMIN_TOKEN || process.env.ADMIN_PASSWORD || "Nova@Manager2026";
    const isAdmin = authHeader === `Bearer ${adminToken}`;

    // گرفتن اطلاعات کیف پول‌ها
    if (req.method === 'GET') {
      const { network, select_best } = req.query;

      // منطق انتخاب هوشمند کیف پول برای کاربر (بر اساس اولویت و کمترین استفاده)
      if (select_best === 'true' && network) {
        const { data, error } = await supabase
          .from('wallets')
          .select('*')
          .eq('network', network)
          .eq('is_active', true)
          .order('priority', { ascending: false }) // اولویت بالاتر
          .order('usage_count', { ascending: true }) // کمترین استفاده
          .limit(1)
          .maybeSingle();

        if (error) throw error;
        if (!data) return res.status(404).json({ error: 'No active wallet found for this network' });
        return res.status(200).json(data);
      } 
      
      // گرفتن همه کیف پول‌ها برای پنل ادمین
      if (isAdmin) {
        const { data, error } = await supabase.from('wallets').select('*').order('created_at', { ascending: false });
        if (error) throw error;
        return res.status(200).json(data || []);
      }

      return res.status(401).json({ error: 'Unauthorized' });
    }

    // عملیات‌های مدیریت (فقط ادمین)
    if (!isAdmin) return res.status(401).json({ error: 'Unauthorized' });

    if (req.method === 'POST') {
      const { network, address, label, priority } = req.body;
      const { data, error } = await supabase.from('wallets').insert([{ network, address, label, priority: priority || 0 }]).select().single();
      if (error) throw error;
      return res.status(201).json(data);
    }

    if (req.method === 'PUT') {
      const { id, is_active, priority, label } = req.body;
      const { data, error } = await supabase.from('wallets').update({ is_active, priority, label }).eq('id', id).select().single();
      if (error) throw error;
      return res.status(200).json(data);
    }

    if (req.method === 'DELETE') {
      const { id } = req.query;
      const { error } = await supabase.from('wallets').delete().eq('id', id);
      if (error) throw error;
      return res.status(200).json({ success: true });
    }

    return res.status(405).json({ error: 'Method not allowed' });
  } catch (error) {
    console.error("Wallets API Error:", error);
    return res.status(500).json({ error: error.message });
  }
}
