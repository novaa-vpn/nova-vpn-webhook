// ---------------------------------------------------
// AUTHENTICATION & INITIALIZATION
// ---------------------------------------------------
let adminPass = localStorage.getItem('nova_admin_pass') || '';
let activeView = 'dashboard'; 
let allTickets = [];
let currentChatId = null;

window.onload = () => {
  if (adminPass) {
    document.getElementById('admin-pass-input').value = adminPass;
    login(true); // ورود خودکار اگر رمز موجود بود
  } else {
    document.getElementById('auth-modal').classList.remove('hidden');
    document.getElementById('app-container').classList.add('hidden');
  }
};

async function login(isAuto = false) {
  const passInput = document.getElementById('admin-pass-input').value.trim();
  if (!passInput) return alert('لطفاً کلید امنیتی را وارد کنید.');
  
  const btn = document.getElementById('login-btn');
  const originalText = btn.innerHTML;
  btn.innerHTML = 'در حال بررسی... <i class="ph-bold ph-spinner animate-spin"></i>';
  btn.disabled = true;
  
  try {
    // تست صحت رمز با گرفتن آمار داشبورد
    const res = await fetch('/api/adminManage', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'get_dashboard_stats', admin_pass: passInput })
    });
    
    if (res.ok) {
      adminPass = passInput;
      localStorage.setItem('nova_admin_pass', adminPass);
      
      document.getElementById('auth-modal').classList.add('hidden');
      const appContainer = document.getElementById('app-container');
      appContainer.classList.remove('hidden');
      appContainer.classList.add('flex'); // اضافه کردن فلکس برای تیل‌ویند
      
      // همگام سازی انتخاب موبایل با تب فعال
      document.getElementById('mobile-nav').value = activeView;
      
      refreshAll();
    } else {
      if(!isAuto) alert('کلید امنیتی (Admin Key) اشتباه است!');
      logoutSilent();
    }
  } catch(e) {
    if(!isAuto) alert('خطای ارتباط با سرور. اتصال اینترنت خود را بررسی کنید.');
  } finally {
    btn.innerHTML = originalText;
    btn.disabled = false;
  }
}

function logoutSilent() {
  adminPass = '';
  localStorage.removeItem('nova_admin_pass');
  document.getElementById('auth-modal').classList.remove('hidden');
  document.getElementById('app-container').classList.add('hidden');
  document.getElementById('app-container').classList.remove('flex');
}

function logout() {
  if(confirm('آیا می‌خواهید از حساب مدیریت خارج شوید؟')) {
    logoutSilent();
    document.getElementById('admin-pass-input').value = '';
  }
}

// ---------------------------------------------------
// API CALL WRAPPERS (استفاده از رمز گلوبال)
// ---------------------------------------------------
async function apiCall(action, params = {}) {
  try {
    const res = await fetch('/api/adminManage', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, admin_pass: adminPass, ...params })
    });
    const data = await res.json();
    if (res.status === 401) { logoutSilent(); return null; }
    if (!res.ok) throw new Error(data.error || 'خطای سرور');
    return data;
  } catch (err) { alert(err.message); return null; }
}

async function apiCallNew(endpoint, method = 'GET', body = null) {
  // API های ولت و تنظیمات از Bearer Token استفاده می‌کنند
  const headers = { 'Authorization': `Bearer ${adminPass}` };
  if (body) headers['Content-Type'] = 'application/json';
  
  try {
    const res = await fetch(endpoint, { method, headers, body: body ? JSON.stringify(body) : null });
    const data = await res.json();
    if (res.status === 401) { logoutSilent(); return null; }
    if (!res.ok) throw new Error(data.error || 'خطا در ارتباط با سرور');
    return data;
  } catch (err) { alert(err.message); return null; }
}

// ---------------------------------------------------
// VIEW ROUTING
// ---------------------------------------------------
function switchView(viewId, btnEl) {
  document.querySelectorAll('.view-section').forEach(el => el.classList.remove('active'));
  document.getElementById(`view-${viewId}`).classList.add('active');
  
  // Update Desktop Sidebar active state
  if (btnEl) {
    document.querySelectorAll('.sidebar-item').forEach(el => el.classList.remove('active'));
    btnEl.classList.add('active');
  } else {
     // اگر از منوی موبایل انتخاب شد، سایدبار دسکتاپ رو هم آپدیت کن
     document.querySelectorAll('.sidebar-item').forEach(el => {
       if(el.getAttribute('onclick').includes(`'${viewId}'`)) el.classList.add('active');
       else el.classList.remove('active');
     });
  }
  
  // Update Mobile Nav Select value
  document.getElementById('mobile-nav').value = viewId;
  
  activeView = viewId;
  refreshAll();
}

async function refreshAll() {
  if (activeView === 'dashboard') loadDashboard();
  if (activeView === 'sold') loadSoldConfigs();
  if (activeView === 'history') loadTransactionHistory();
  if (activeView === 'receipts') loadReceipts();
  if (activeView === 'tickets') loadTickets();
  if (activeView === 'users') loadUsers();
  if (activeView === 'inventory') { loadInventory(); loadPlans(); }
  if (activeView === 'wallets') loadWallets();
  if (activeView === 'settings') loadSettings();
}

// ---------------------------------------------------
// MODULE: DASHBOARD
// ---------------------------------------------------
async function loadDashboard() {
  const data = await apiCall('get_dashboard_stats');
  if (data) {
    document.getElementById('stat-revenue').innerHTML = `${Number(data.total_revenue).toLocaleString()} <span class="text-xs text-slate-500">T</span>`;
    document.getElementById('stat-users').innerText = data.users_count;
    document.getElementById('stat-pending').innerText = data.pending_receipts;
    document.getElementById('stat-avail').innerText = data.available_configs;
    document.getElementById('stat-sold').innerText = data.sold_configs;
  }
}

// ---------------------------------------------------
// MODULE: SOLD CONFIGS
// ---------------------------------------------------
async function loadSoldConfigs() {
  const data = await apiCall('get_sold_configs');
  const tbody = document.getElementById('sold-configs-body');
  if (!data || data.configs.length === 0) {
    tbody.innerHTML = '<tr><td colspan="5" class="text-center p-6 text-slate-500">هیچ سرویس فروخته شده‌ای یافت نشد.</td></tr>';
    return;
  }
  
  tbody.innerHTML = data.configs.map(c => `
    <tr class="border-b border-white/5 hover:bg-white/5 transition">
      <td class="p-4 font-mono text-xs text-blue-400">${c.owner_id || 'نامشخص'}</td>
      <td class="p-4 font-bold text-xs">${c.plan_name}</td>
      <td class="p-4 text-[10px] text-slate-400 font-mono min-w-[120px]">${new Date(c.sold_at).toLocaleString('fa-IR')}</td>
      <td class="p-4">
        <div class="text-[10px] text-slate-400 font-mono truncate max-w-[100px] md:max-w-[150px] bg-black/30 p-1 rounded" title="${c.v2ray_uri}">
          ${c.v2ray_uri || c.web_panel_url || '-'}
        </div>
      </td>
      <td class="p-4 text-center">
        <button onclick="deleteConfig('${c.id}')" class="bg-slate-800 p-2 rounded-lg text-red-400 hover:bg-red-900/30 transition" title="حذف این کانفیگ از سیستم"><i class="ph ph-trash"></i></button>
      </td>
    </tr>
  `).join('');
}

async function deleteConfig(id) {
  if(!confirm('آیا از حذف دائم این کانفیگ از دیتابیس مطمئن هستید؟ (اگر کاربر این کانفیگ را خریده باشد، از پنل او نیز پاک می‌شود!)')) return;
  const res = await apiCall('delete_config', { config_id: id });
  if (res) {
    alert('کانفیگ با موفقیت حذف شد.');
    if (activeView === 'sold') loadSoldConfigs();
    if (activeView === 'inventory') loadInventory();
  }
}

// ---------------------------------------------------
// MODULE: HISTORY
// ---------------------------------------------------
async function loadTransactionHistory() {
  const data = await apiCall('get_all_transactions');
  const tbody = document.getElementById('history-body');
  if (!data || data.transactions.length === 0) {
    tbody.innerHTML = '<tr><td colspan="5" class="text-center p-6 text-slate-500">هیچ تاریخچه‌ای وجود ندارد.</td></tr>';
    return;
  }
  
  tbody.innerHTML = data.transactions.map(t => {
    const isApproved = t.status === 'approved';
    const isTopup = t.target_plan === 'wallet_topup';
    return `
    <tr class="border-b border-white/5 hover:bg-white/5 transition opacity-${isApproved ? '100' : '50'}">
      <td class="p-4 text-[10px] text-slate-400 font-mono min-w-[120px]">${new Date(t.handled_at || t.created_at).toLocaleString('fa-IR')}</td>
      <td class="p-4 font-mono text-xs text-blue-400">${t.chat_id}</td>
      <td class="p-4 text-xs font-bold">${isTopup ? 'شارژ کیف‌پول' : t.target_plan}</td>
      <td class="p-4 font-mono text-xs min-w-[100px]">${Number(t.amount_toman).toLocaleString()} <span class="text-[9px] text-slate-500">(${t.crypto_amount} ${t.crypto_currency})</span></td>
      <td class="p-4">
        <span class="px-2 py-1 rounded text-[10px] font-bold ${isApproved ? 'bg-green-900/30 text-green-400' : 'bg-red-900/30 text-red-400'}">
          ${isApproved ? 'موفق' : 'رد شده'}
        </span>
      </td>
    </tr>
  `}).join('');
}

// ---------------------------------------------------
// MODULE: RECEIPTS
// ---------------------------------------------------
async function loadReceipts() {
  const data = await apiCall('get_pending');
  const container = document.getElementById('receipts-list');
  if (!data) return;
  if (data.receipts.length === 0) {
    container.innerHTML = '<div class="glass p-10 text-center text-slate-500 rounded-3xl">هیچ تراکنش معلقی وجود ندارد.</div>';
    return;
  }
  
  container.innerHTML = data.receipts.map(r => {
    const isTopup = r.target_plan === 'wallet_topup';
    const badgeHtml = isTopup 
      ? `<span class="bg-purple-900/30 text-purple-400 px-2 py-1 rounded text-xs font-bold flex items-center gap-1"><i class="ph-bold ph-wallet"></i> درخواست شارژ حساب</span>`
      : `<span class="bg-blue-900/30 text-blue-400 px-2 py-1 rounded text-xs font-bold">${r.target_plan}</span>`;

    return `
    <div class="glass p-5 rounded-2xl border-r-4 ${isTopup ? 'border-purple-500' : 'border-blue-500'} flex flex-col md:flex-row justify-between items-center gap-4">
      <div class="flex-1 w-full">
        <div class="flex items-center gap-2 mb-2">
          <span class="bg-slate-800 px-2 py-1 rounded text-xs font-mono text-slate-300">ID: ${r.chat_id}</span>
          ${badgeHtml}
        </div>
        <div class="text-sm font-mono text-white break-all bg-black/30 p-2 rounded border border-white/5">${r.txid_or_receipt}</div>
        <div class="mt-2 text-xs text-slate-400">مبلغ: <span class="text-white">${Number(r.amount_toman).toLocaleString()} T</span> | ارز: <span class="text-white">${r.crypto_amount} ${r.crypto_currency}</span></div>
        ${r.notes ? `<div class="mt-2 text-xs bg-yellow-500/10 text-yellow-200 p-2 rounded border border-yellow-500/20">📝 ${r.notes}</div>` : ''}
      </div>
      <div class="flex gap-2 w-full md:w-auto">
        <button onclick="txAction('${r.id}', 'approve')" class="flex-1 md:flex-none bg-green-600 px-6 py-3 rounded-xl font-bold text-xs">تایید و اعمال</button>
        <button onclick="txAction('${r.id}', 'reject')" class="flex-1 md:flex-none bg-red-600/50 px-6 py-3 rounded-xl font-bold text-xs">رد کردن</button>
      </div>
    </div>
  `}).join('');
}

async function txAction(id, type) {
  if (!confirm('آیا مطمئن هستید؟')) return;
  const res = await apiCall(type, { tx_id: id });
  if (res) {
    if(activeView === 'receipts') loadReceipts();
  }
}

// ---------------------------------------------------
// MODULE: TICKETS
// ---------------------------------------------------
async function loadTickets() {
  const data = await apiCall('get_tickets');
  if (!data) return;
  allTickets = data.tickets;
  
  const chatGroups = {};
  allTickets.forEach(t => {
    if(!chatGroups[t.chat_id]) chatGroups[t.chat_id] = { messages: [], username: t.users?.username || 'Unknown' };
    chatGroups[t.chat_id].messages.push(t);
  });

  const listContainer = document.getElementById('ticket-users-list');
  if (Object.keys(chatGroups).length === 0) {
    listContainer.innerHTML = '<div class="p-5 text-center text-xs text-slate-500">هیچ پیامی وجود ندارد</div>';
    return;
  }

  listContainer.innerHTML = Object.keys(chatGroups).map(chatId => {
    const msgs = chatGroups[chatId].messages;
    const lastMsg = msgs[msgs.length - 1];
    return `
      <div onclick="openChat('${chatId}')" class="p-3 md:p-4 border-b border-white/5 hover:bg-white/5 cursor-pointer transition flex items-center gap-3 ${currentChatId == chatId ? 'bg-blue-900/20 border-r-2 border-r-blue-500' : ''}">
        <div class="w-8 h-8 md:w-10 md:h-10 bg-slate-800 rounded-full flex justify-center items-center shrink-0">
          <i class="ph-fill ph-user text-slate-400"></i>
        </div>
        <div class="flex-1 overflow-hidden">
          <div class="font-bold text-xs md:text-sm text-slate-200 truncate">@${chatGroups[chatId].username}</div>
          <div class="text-[9px] md:text-[10px] text-slate-400 truncate mt-1">${lastMsg.message_text}</div>
        </div>
      </div>
    `;
  }).join('');

  if(currentChatId) openChat(currentChatId);
}

function openChat(chatId) {
  currentChatId = chatId;
  const chatHistory = document.getElementById('chat-history');
  
  document.getElementById('reply-input').disabled = false;
  document.getElementById('reply-btn').disabled = false;
  
  const userMsgs = allTickets.filter(t => t.chat_id == chatId);
  if(userMsgs.length > 0) {
     document.getElementById('chat-header-name').innerText = `@${userMsgs[0].users?.username || 'کاربر'}`;
     document.getElementById('chat-header-id').innerText = chatId;
  }

  chatHistory.innerHTML = userMsgs.map(t => {
    const isUser = t.sender === 'user';
    const date = new Date(t.created_at).toLocaleTimeString('fa-IR', {hour: '2-digit', minute:'2-digit'});
    return `
      <div class="flex ${isUser ? 'justify-end' : 'justify-start'} mb-2">
        <div class="${isUser ? 'chat-bubble-user text-right text-slate-200' : 'chat-bubble-admin text-left text-blue-100'} p-3 max-w-[85%] md:max-w-[80%]">
          <div class="text-xs md:text-sm break-words">${t.message_text.replace(/\n/g, '<br>')}</div>
          <div class="text-[9px] opacity-50 mt-1">${date}</div>
        </div>
      </div>
    `;
  }).join('');

  chatHistory.scrollTop = chatHistory.scrollHeight;
}

async function sendReply() {
  const input = document.getElementById('reply-input');
  const text = input.value.trim();
  if (!text || !currentChatId) return;

  const btn = document.getElementById('reply-btn');
  btn.disabled = true;
  
  const res = await apiCall('reply_ticket', { target_chat_id: currentChatId, message_text: text });
  if (res) {
    input.value = '';
    loadTickets(); 
  }
  btn.disabled = false;
}

// ---------------------------------------------------
// MODULE: USERS
// ---------------------------------------------------
async function loadUsers() {
  const data = await apiCall('get_users');
  if (!data) return;
  document.getElementById('users-table-body').innerHTML = data.users.map(u => `
    <tr class="border-b border-white/5 hover:bg-white/5 transition">
      <td class="p-4 font-mono text-xs">${u.chat_id}<br><span class="text-[10px] text-slate-500">@${u.username || 'n/a'}</span></td>
      <td class="p-4 font-mono text-blue-400">${Number(u.wallet_balance || 0).toLocaleString()}</td>
      <td class="p-4 font-mono text-red-400">${u.wallet_trx || 0}</td>
      <td class="p-4 text-center">${u.total_referrals || 0}</td>
      <td class="p-4 flex gap-2 justify-center">
        <button onclick="editBalance('${u.chat_id}')" class="bg-blue-600/20 text-blue-400 p-2 rounded-lg" title="شارژ"><i class="ph ph-coins"></i></button>
        <button onclick="banUser('${u.chat_id}', '${u.role}')" class="bg-slate-800 p-2 rounded-lg text-red-400" title="مسدود"><i class="ph ph-prohibit"></i></button>
      </td>
    </tr>
  `).join('');
}

async function editBalance(chatId) {
  const amount = prompt("مبلغ جدید کیف پول (تومان):");
  if (amount === null) return;
  const res = await apiCall('update_user_balance', { target_chat_id: chatId, amount: Number(amount) });
  if (res) loadUsers();
}

async function banUser(id, currentRole) {
  const newRole = currentRole === 'banned' ? 'user' : 'banned';
  if (!confirm(`آیا می‌خواهید این کاربر را ${newRole === 'banned' ? 'مسدود' : 'آزاد'} کنید؟`)) return;
  const res = await apiCall('update_user_role', { target_chat_id: id, role: newRole });
  if (res) loadUsers();
}

// ---------------------------------------------------
// MODULE: INVENTORY & PLANS
// ---------------------------------------------------
async function loadInventory() {
  const data = await apiCall('get_inventory');
  if (!data) return;
  document.getElementById('inventory-status').innerHTML = Object.entries(data.stats).map(([name, count]) => `
    <div class="flex justify-between p-3 bg-slate-900/50 rounded-xl border border-white/5">
      <span class="text-sm font-bold">${name}</span>
      <span class="bg-blue-600/20 text-blue-400 px-3 py-1 rounded-full text-xs font-mono font-bold">${count} موجود</span>
    </div>
  `).join('') || '<div class="text-center text-xs text-slate-500">انبار خالی است.</div>';
}

async function loadPlans() {
  const data = await apiCall('get_plans_list');
  if (!data) return;
  
  document.getElementById('inv-plan').innerHTML = data.plans.map(p => `<option value="${p.internal_name}">${p.title_fa}</option>`).join('');
  
  document.getElementById('plans-list').innerHTML = data.plans.map(p => `
    <div class="glass p-4 rounded-2xl flex justify-between items-center border border-white/5">
      <div>
        <div class="font-bold text-sm">${p.title_fa} <span class="text-[10px] text-slate-500 hidden md:inline">(${p.internal_name})</span></div>
        <div class="text-xs text-slate-400 mt-1">${Number(p.price_toman).toLocaleString()} تومان | $${p.price_usd}</div>
      </div>
      <div class="flex gap-2 shrink-0">
        <button onclick="togglePlan('${p.internal_name}', ${p.is_active})" class="px-3 py-1.5 rounded-lg text-[10px] font-bold ${p.is_active ? 'bg-green-600' : 'bg-red-600'}">${p.is_active ? 'فعال' : 'غیرفعال'}</button>
        <button onclick="deletePlan('${p.internal_name}')" class="bg-slate-800 p-2 rounded-lg text-red-400"><i class="ph ph-trash"></i></button>
      </div>
    </div>
  `).join('');
}

async function addConfig() {
  const plan = document.getElementById('inv-plan').value;
  const v2ray = document.getElementById('inv-v2ray').value;
  const panel = document.getElementById('inv-panel').value;
  const note = document.getElementById('inv-note').value;

  if (!v2ray) return alert('کد کانفیگ الزامی است');
  const data = await apiCall('add_config', { plan, v2ray, panel: panel || '', note });
  
  if (data) { 
    alert('کانفیگ با موفقیت به انبار اضافه شد.'); 
    document.getElementById('inv-v2ray').value = ''; 
    document.getElementById('inv-panel').value = ''; 
    loadInventory(); 
  }
}

async function addNewPlan() {
  const params = {
    plan_id: document.getElementById('p-id').value,
    title_fa: document.getElementById('p-title').value,
    price_toman: Number(document.getElementById('p-toman').value),
    price_usd: Number(document.getElementById('p-usd').value)
  };
  if (!params.plan_id || !params.title_fa) return alert("فیلدها را پر کنید.");
  const res = await apiCall('add_plan', params);
  if (res) { alert("محصول ثبت شد."); loadPlans(); }
}

async function togglePlan(id, current) {
  const res = await apiCall('toggle_plan', { plan_id: id, status: !current });
  if (res) loadPlans();
}

async function deletePlan(id) {
  if (!confirm('مطمئن هستید؟')) return;
  const res = await apiCall('delete_plan', { plan_id: id });
  if (res) loadPlans();
}

// ---------------------------------------------------
// MODULE: BROADCAST
// ---------------------------------------------------
async function sendBroadcast() {
  const text = document.getElementById('bc-text').value;
  if (!text || !confirm('این پیام برای تمام کاربران ارسال خواهد شد. آیا مطمئن هستید؟')) return;
  const data = await apiCall('broadcast', { message_text: text });
  if (data) {
    alert(`عملیات موفق. پیام در حال ارسال به ${data.count} کاربر است.`);
    document.getElementById('bc-text').value = '';
  }
}

// ---------------------------------------------------
// MODULE: WALLETS
// ---------------------------------------------------
async function loadWallets() {
  const container = document.getElementById('wallets-list');
  container.innerHTML = '<div class="text-center text-xs text-slate-500 py-10">در حال لود...</div>';
  
  const data = await apiCallNew('/api/wallets');
  if (!data) return;

  if (data.length === 0) {
    container.innerHTML = '<div class="text-center text-xs text-slate-500 py-10">هیچ کیف پولی ثبت نشده است.</div>';
    return;
  }

  container.innerHTML = data.map(w => `
    <div class="glass p-4 rounded-2xl border border-white/5 relative overflow-hidden">
      <div class="flex justify-between items-start mb-2">
        <div class="flex items-center gap-2">
          <span class="bg-slate-800 text-white font-bold px-2 py-1 rounded text-xs">${w.network}</span>
          <span class="text-[10px] text-slate-400">${w.label || 'بدون نام'}</span>
        </div>
        <div class="flex gap-2">
          <button onclick="toggleWallet('${w.id}', ${!w.is_active})" class="px-2 py-1 md:px-3 md:py-1 rounded-lg text-[10px] font-bold ${w.is_active ? 'bg-emerald-900/50 text-emerald-400' : 'bg-red-900/50 text-red-400'} border ${w.is_active ? 'border-emerald-500/20' : 'border-red-500/20'}">
            ${w.is_active ? 'فعال' : 'غیرفعال'}
          </button>
          <button onclick="deleteWallet('${w.id}')" class="bg-slate-800 p-1.5 rounded-lg text-red-400 border border-white/5"><i class="ph ph-trash"></i></button>
        </div>
      </div>
      <div class="text-[10px] md:text-xs font-mono text-slate-300 break-all bg-black/30 p-2 rounded border border-white/5 mt-2">${w.address}</div>
      <div class="flex justify-between mt-3 text-[10px] text-slate-500 border-t border-white/5 pt-2">
        <span>استفاده: <strong class="text-white">${w.usage_count}</strong></span>
        <span>اولویت: <strong class="text-white">${w.priority}</strong></span>
      </div>
    </div>
  `).join('');
}

async function saveWallet() {
  const payload = {
    network: document.getElementById('w-network').value,
    address: document.getElementById('w-address').value.trim(),
    label: document.getElementById('w-label').value,
    priority: parseInt(document.getElementById('w-priority').value) || 0
  };
  if(!payload.address) return alert('وارد کردن آدرس کیف پول الزامی است');
  
  const res = await apiCallNew('/api/wallets', 'POST', payload);
  if(res) {
    alert('کیف پول با موفقیت ثبت شد.');
    document.getElementById('w-address').value = '';
    document.getElementById('w-label').value = '';
    loadWallets();
  }
}

async function toggleWallet(id, is_active) {
  const res = await apiCallNew('/api/wallets', 'PUT', { id, is_active });
  if (res) loadWallets();
}

async function deleteWallet(id) {
  if(!confirm('آیا از حذف این کیف پول اطمینان دارید؟')) return;
  const res = await apiCallNew(`/api/wallets?id=${id}`, 'DELETE');
  if (res) loadWallets();
}

// ---------------------------------------------------
// MODULE: SETTINGS
// ---------------------------------------------------
async function loadSettings() {
  const data = await apiCallNew('/api/settings');
  if (data) {
    document.getElementById('sys-usd-rate').value = data.usd_rate;
  }
}

async function saveSettings() {
  const btn = document.getElementById('btn-save-settings');
  const rate = document.getElementById('sys-usd-rate').value;
  if(!rate) return alert("مبلغ را وارد کنید");
  
  btn.innerText = 'در حال ذخیره...';
  const res = await apiCallNew('/api/settings', 'POST', { usd_rate: rate });
  if (res) alert('✅ قیمت جدید دلار در سیستم اعمال شد.');
  btn.innerText = 'ذخیره تغییرات';
}
