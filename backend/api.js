/**
 * Film Archive API Service Layer
 * 提供与后端 API 的通信功能
 */

// Supabase Edge Function 配置
const SUPABASE_ANON_KEY = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJvbGUiOiJhbm9uIiwiaWF0IjoxNzc2NTY2Mjg2LCJleHAiOjEzMjg3MjA2Mjg2fQ.w9zHwgYJHx0lFBVYgcwNRhiGzSTe_r9A65U_x6WMyEM';

const BACKEND_URL = 'https://3015-01KPJ57BHH2M05B2MPX41XS182.sandbox.meoo.host/sb-api/functions/v1/film-archive';

// 检测当前页面 URL，自动推断后端地址
function detectApiBaseUrl() {
    // 1. 优先使用 localStorage 中存储的配置
    const savedUrl = localStorage.getItem('api_base_url');
    if (savedUrl) return savedUrl;

    // 2. 如果前后端同域（从 meoo.host 访问），用相对路径
    if (window.location.hostname.includes('meoo.host') || window.location.hostname.includes('meoo.space')) {
        return `${window.location.origin}/sb-api/functions/v1/film-archive`;
    }

    // 3. 其他域名（如 GitHub Pages）使用固定后端地址
    return BACKEND_URL;
}

const API_BASE_URL = detectApiBaseUrl();
console.log('API Base URL:', API_BASE_URL);

// API 状态
let apiAvailable = false;

// ============= Auth Token Management =============
const Auth = {
    getToken() {
        return localStorage.getItem('access_token');
    },

    getRefreshToken() {
        return localStorage.getItem('refresh_token');
    },

    setTokens(accessToken, refreshToken) {
        localStorage.setItem('access_token', accessToken);
        localStorage.setItem('refresh_token', refreshToken);
    },

    clearTokens() {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('current_user');
    },

    getUser() {
        const userJson = localStorage.getItem('current_user');
        return userJson ? JSON.parse(userJson) : null;
    },

    setUser(user) {
        localStorage.setItem('current_user', JSON.stringify(user));
    },

    isAuthenticated() {
        return !!this.getToken();
    }
};

// ============= API Client =============
const API = {
    async checkHealth() {
        try {
            const response = await fetch(`${API_BASE_URL}/health`, {
                method: 'GET',
                mode: 'cors',
                cache: 'no-cache',
                headers: { 'apikey': SUPABASE_ANON_KEY }
            });
            apiAvailable = response.ok;
            return response.ok;
        } catch (error) {
            console.warn('Backend not available:', error.message);
            apiAvailable = false;
            return false;
        }
    },

    async request(endpoint, options = {}) {
        const url = `${API_BASE_URL}${endpoint}`;
        const headers = {
            'Content-Type': 'application/json',
            'apikey': SUPABASE_ANON_KEY,
            ...options.headers
        };

        // Add user auth token if available, otherwise use anon key
        const token = Auth.getToken();
        headers['Authorization'] = token ? `Bearer ${token}` : `Bearer ${SUPABASE_ANON_KEY}`;

        try {
            const response = await fetch(url, {
                ...options,
                headers,
                mode: 'cors'
            });

            // Handle token expiration
            if (response.status === 401 && Auth.getRefreshToken()) {
                const refreshed = await this.refreshToken();
                if (refreshed) {
                    // Retry request with new token
                    headers['Authorization'] = `Bearer ${Auth.getToken()}`;
                    const retryResponse = await fetch(url, { ...options, headers, mode: 'cors' });
                    if (!retryResponse.ok) {
                        const error = await retryResponse.json().catch(() => ({ detail: 'Request failed' }));
                        throw new Error(error.detail || `HTTP ${retryResponse.status}`);
                    }
                    return retryResponse.json();
                }
            }

            if (!response.ok) {
                const error = await response.json().catch(() => ({ detail: 'Request failed' }));
                throw new Error(error.detail || `HTTP ${response.status}`);
            }

            return response.json();
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    },

    async refreshToken() {
        try {
            const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'apikey': SUPABASE_ANON_KEY,
                    'Authorization': `Bearer ${SUPABASE_ANON_KEY}`
                },
                body: JSON.stringify({ refresh_token: Auth.getRefreshToken() }),
                mode: 'cors'
            });

            if (!response.ok) {
                Auth.clearTokens();
                return false;
            }

            const data = await response.json();
            Auth.setTokens(data.access_token, data.refresh_token);
            return true;
        } catch {
            Auth.clearTokens();
            return false;
        }
    },

    // ============= Auth Endpoints =============
    auth: {
        async register(username, email, password) {
            return API.request('/auth/register', {
                method: 'POST',
                body: JSON.stringify({ username, email, password })
            });
        },

        async login(username, password) {
            const data = await API.request('/auth/login', {
                method: 'POST',
                body: JSON.stringify({ username, password })
            });
            Auth.setTokens(data.access_token, data.refresh_token);
            return data;
        },

        async me() {
            const user = await API.request('/auth/me');
            Auth.setUser(user);
            return user;
        },

        logout() {
            Auth.clearTokens();
        }
    },

    // ============= Roll Endpoints =============
    rolls: {
        async list(status = null) {
            const params = status ? `?status=${status}` : '';
            const data = await API.request(`/rolls${params}`);
            return data.items || [];
        },

        async create(rollData) {
            return API.request('/rolls', {
                method: 'POST',
                body: JSON.stringify(rollData)
            });
        },

        async get(rollId) {
            return API.request(`/rolls/${rollId}`);
        },

        async update(rollId, rollData) {
            return API.request(`/rolls/${rollId}`, {
                method: 'PUT',
                body: JSON.stringify(rollData)
            });
        },

        async delete(rollId) {
            return API.request(`/rolls/${rollId}`, {
                method: 'DELETE'
            });
        }
    },

    // ============= Photo Endpoints =============
    photos: {
        async list(rollId) {
            const data = await API.request(`/rolls/${rollId}/photos`);
            return data.items || [];
        },

        async create(rollId, photoData) {
            return API.request(`/rolls/${rollId}/photos`, {
                method: 'POST',
                body: JSON.stringify(photoData)
            });
        },

        async update(rollId, photoId, photoData) {
            return API.request(`/rolls/${rollId}/photos/${photoId}`, {
                method: 'PUT',
                body: JSON.stringify(photoData)
            });
        },

        async delete(rollId, photoId) {
            return API.request(`/rolls/${rollId}/photos/${photoId}`, {
                method: 'DELETE'
            });
        }
    },

    // ============= Sync Endpoints =============
    sync: {
        async upload(rolls, photos) {
            return API.request('/sync', {
                method: 'POST',
                body: JSON.stringify({ rolls, photos })
            });
        },

        async export() {
            return API.request('/sync/export');
        }
    }
};

// ============= Auth UI Management =============
const AuthUI = {
    showLoginModal() {
        // Check if backend is available first
        API.checkHealth().then(available => {
            if (!available) {
                alert('后端服务暂时无法连接，请稍后重试');
                return;
            }
            document.getElementById('auth-modal').classList.remove('hidden');
            document.getElementById('login-form').classList.remove('hidden');
            document.getElementById('register-form').classList.add('hidden');
        });
    },

    showRegisterModal() {
        document.getElementById('auth-modal').classList.remove('hidden');
        document.getElementById('login-form').classList.add('hidden');
        document.getElementById('register-form').classList.remove('hidden');
    },

    hideModal() {
        document.getElementById('auth-modal').classList.add('hidden');
    },

    switchToRegister() {
        document.getElementById('login-form').classList.add('hidden');
        document.getElementById('register-form').classList.remove('hidden');
    },

    switchToLogin() {
        document.getElementById('register-form').classList.add('hidden');
        document.getElementById('login-form').classList.remove('hidden');
    },

    updateUI() {
        const user = Auth.getUser();
        const authBtn = document.getElementById('auth-button');
        const userInfo = document.getElementById('user-info');
        const syncBtn = document.getElementById('sync-button');

        if (user) {
            if (authBtn) authBtn.classList.add('hidden');
            if (userInfo) {
                userInfo.classList.remove('hidden');
                userInfo.innerHTML = `
                    <span class="text-sm text-gray-600">${user.username}</span>
                    <button onclick="AuthUI.logout()" class="btn-archive-ghost btn-sm" style="color:var(--danger)">退出</button>
                `;
            }
            if (syncBtn) syncBtn.classList.remove('hidden');
        } else {
            if (authBtn) authBtn.classList.remove('hidden');
            if (userInfo) userInfo.classList.add('hidden');
            if (syncBtn) syncBtn.classList.add('hidden');
        }
    },

    async login() {
        const username = document.getElementById('login-username').value;
        const password = document.getElementById('login-password').value;

        if (!username || !password) {
            alert('请输入用户名和密码');
            return;
        }

        try {
            await API.auth.login(username, password);
            const user = await API.auth.me();
            Auth.setUser(user);
            this.hideModal();
            this.updateUI();
            showToast('登录成功');

            // Sync local data to server
            await this.syncToServer();
        } catch (error) {
            alert('登录失败: ' + error.message);
        }
    },

    async register() {
        const username = document.getElementById('reg-username').value;
        const email = document.getElementById('reg-email').value;
        const password = document.getElementById('reg-password').value;
        const confirmPassword = document.getElementById('reg-password-confirm').value;

        if (!username || !email || !password) {
            alert('请填写所有字段');
            return;
        }

        if (password !== confirmPassword) {
            alert('两次输入的密码不一致');
            return;
        }

        if (password.length < 6) {
            alert('密码至少需要6个字符');
            return;
        }

        try {
            await API.auth.register(username, email, password);
            // Auto login after registration
            await API.auth.login(username, password);
            const user = await API.auth.me();
            Auth.setUser(user);
            this.hideModal();
            this.updateUI();
            showToast('注册成功，已自动登录');

            // Sync local data to server
            await this.syncToServer();
        } catch (error) {
            alert('注册失败: ' + error.message);
        }
    },

    logout() {
        API.auth.logout();
        this.updateUI();
        showToast('已退出登录');
    },

    async syncToServer() {
        if (!Auth.isAuthenticated()) return;

        try {
            // Convert local storage format to API format
            const rolls = storage.rolls.map(r => ({
                roll_id: r.id,
                film_stock: r.filmType,
                camera: r.camera,
                iso: r.iso,
                total_frames: r.totalFrames || 36,
                status: r.status || 'shooting',
                note: r.notes,
                custom_data: {
                    name: r.name,
                    dateCreated: r.dateCreated,
                    dateFinished: r.dateFinished,
                    dateDeveloped: r.dateDeveloped
                }
            }));

            const photos = storage.scans.map(s => ({
                roll_id: s.rollId,
                frame_number: s.frameNumber,
                image_url: s.imageUrl,
                thumbnail_url: s.thumbnailUrl,
                note: s.notes,
                exif_data: s.exif || {},
                tags: s.tags || []
            }));

            if (rolls.length > 0 || photos.length > 0) {
                const result = await API.sync.upload(rolls, photos);
                if (result.success) {
                    showToast(`同步成功：${result.synced_rolls} 个胶卷, ${result.synced_photos} 张照片`);
                }
            }
        } catch (error) {
            console.error('Sync failed:', error);
            showToast('同步失败: ' + error.message);
        }
    },

    async syncFromServer() {
        if (!Auth.isAuthenticated()) return;

        try {
            const data = await API.sync.export();

            // Convert API format to local storage format
            const rolls = data.rolls.map(r => ({
                id: r.roll_id,
                name: r.custom_data?.name || r.roll_id,
                filmType: r.film_stock,
                camera: r.camera,
                iso: r.iso,
                totalFrames: r.total_frames,
                status: r.status,
                notes: r.note,
                dateCreated: r.custom_data?.dateCreated || r.date_created,
                dateFinished: r.custom_data?.dateFinished || r.date_finished,
                dateDeveloped: r.custom_data?.dateDeveloped || r.date_developed
            }));

            const scans = data.photos.map(p => ({
                id: `scan_${p.id}`,
                rollId: String(p.roll_id),
                frameNumber: p.frame_number,
                imageUrl: p.image_url,
                thumbnailUrl: p.thumbnail_url,
                notes: p.note,
                exif: p.exif_data,
                tags: p.tags || [],
                rating: p.rating
            }));

            // Merge with existing data (server data takes precedence)
            storage.rolls = rolls;
            storage.scans = scans;
            saveStorage();

            // Refresh UI
            updateStats();
            populateSelects();
            populatePreviewRollSelect();
            renderRecentPhotos();

            showToast('已从服务器同步数据');
        } catch (error) {
            console.error('Download sync failed:', error);
            showToast('下载同步失败: ' + error.message);
        }
    }
};

// Expose to global scope
globalThis.Auth = Auth;
globalThis.API = API;
globalThis.AuthUI = AuthUI;
globalThis.API_BASE_URL = API_BASE_URL;
