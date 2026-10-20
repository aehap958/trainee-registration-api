'use strict';

/* ============ الإعدادات ============ */
// عنوان الـ API. عند نشره على الإنترنت غيّره هنا وفي سياسة CSP داخل index.html
const API_BASE_URL = 'https://fq9usb8fc8.execute-api.eu-west-1.amazonaws.com/prod';
const REQUEST_TIMEOUT_MS = 8000;

/* ============ عناصر الصفحة ============ */
const $ = (selector) => document.querySelector(selector);
const form = $('#register-form');
const submitBtn = $('#submit-btn');
const formMessage = $('#form-message');
const formSection = $('#form-section');
const ticket = $('#ticket');
const statusEl = $('#server-status');
const FIELDS = ['name', 'email', 'track'];

/* ============ قواعد التحقق (نفس قواعد الخادم) ============ */
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

const validators = {
  name(v) {
    if (!v) return 'اكتب اسمك الكامل.';
    if (v.length < 2) return 'الاسم يجب أن يكون حرفين على الأقل.';
    if (v.length > 80) return 'الاسم أطول من 80 حرفًا.';
    return '';
  },
  email(v) {
    if (!v) return 'اكتب بريدك الإلكتروني.';
    if (v.length > 254 || !EMAIL_RE.test(v)) return 'اكتب بريدًا صحيحًا مثل name@example.com.';
    return '';
  },
  track(v) {
    return v ? '' : 'اختر المسار التدريبي.';
  },
};

const getValue = (field) => form.elements[field].value.trim();

/** عرض/مسح رسالة الخطأ تحت الحقل وتحديث حالته لقارئات الشاشة */
function setFieldError(field, message) {
  $(`#${field}-error`).textContent = message; // textContent وليس innerHTML: يمنع حقن HTML
  form.elements[field].setAttribute('aria-invalid', message ? 'true' : 'false');
}

function validateField(field) {
  const message = validators[field](getValue(field));
  setFieldError(field, message);
  return !message;
}

/** يتحقق من كل الحقول، ويضع المؤشر على أول حقل خاطئ */
function validateForm() {
  const results = FIELDS.map((field) => [field, validateField(field)]);
  const firstInvalid = results.find(([, ok]) => !ok);
  if (firstInvalid) form.elements[firstInvalid[0]].focus();
  return !firstInvalid;
}

/* ============ أدوات الواجهة ============ */
function showMessage(text) {
  formMessage.textContent = text;
  formMessage.hidden = false;
}

function setLoading(isLoading) {
  submitBtn.disabled = isLoading; // يمنع الإرسال المكرر
  submitBtn.setAttribute('aria-busy', String(isLoading));
  submitBtn.textContent = isLoading ? 'جارٍ التسجيل' : 'سجّل الآن';
}

function showTicket(data, traineeId) {
  $('#t-name').textContent = data.name;
  $('#t-email').textContent = data.email;
  $('#t-track').textContent = form.elements.track.selectedOptions[0].textContent;
  $('#t-id').textContent = traineeId;
  formSection.hidden = true;
  ticket.hidden = false;
  $('#ticket-title').focus();
}

function resetToForm() {
  form.reset();
  FIELDS.forEach((field) => setFieldError(field, ''));
  formMessage.hidden = true;
  ticket.hidden = true;
  formSection.hidden = false;
  form.elements.name.focus();
}

/* ============ الاتصال بالـ API ============ */
/** fetch مع مهلة زمنية حتى لا ينتظر المستخدم للأبد */
async function fetchWithTimeout(url, options = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}

/** فحص صحة الخادم عبر GET / وتحديث الشارة في الترويسة */
async function checkServer() {
  try {
    const res = await fetchWithTimeout(`${API_BASE_URL}/`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    statusEl.dataset.state = 'ok';
    statusEl.textContent = 'الخادم متصل';
  } catch {
    statusEl.dataset.state = 'error';
    statusEl.textContent = 'الخادم غير متاح';
  }
}

async function handleSubmit(event) {
  event.preventDefault();
  formMessage.hidden = true;
  if (!validateForm()) return; // لا نرسل شيئًا قبل نجاح التحقق

  const payload = Object.fromEntries(FIELDS.map((f) => [f, getValue(f)]));
  setLoading(true);

  try {
    const res = await fetchWithTimeout(`${API_BASE_URL}/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json().catch(() => ({})); // لا ينهار إن لم يكن الرد JSON

    if (res.status === 201) {
      showTicket(payload, data.trainee_id);
    } else if (res.status === 409) {
      setFieldError('email', 'هذا البريد مسجّل مسبقًا. استخدم بريدًا آخر.');
      form.elements.email.focus();
    } else if (res.status === 400) {
      // الخادم يعيد أسماء الحقول المرفوضة في data.fields
      (data.fields || []).filter((f) => FIELDS.includes(f))
        .forEach((f) => setFieldError(f, 'هذه القيمة غير مقبولة.'));
      showMessage('تعذّر قبول البيانات. راجع الحقول المحددة وحاول مجددًا.');
    } else {
      showMessage('حدث خطأ في الخادم. حاول بعد قليل.');
    }
  } catch (err) {
    showMessage(err.name === 'AbortError'
      ? 'انتهت مهلة الاتصال. حاول مرة أخرى.'
      : 'تعذّر الاتصال بالخادم. تأكد من تشغيله ثم أعد المحاولة.');
    checkServer();
  } finally {
    setLoading(false);
  }
}

/* ============ ربط الأحداث ============ */
FIELDS.forEach((field) => {
  const input = form.elements[field];
  input.addEventListener('blur', () => validateField(field)); // تحقق عند مغادرة الحقل
  input.addEventListener('input', () => {                      // وأثناء التصحيح بعد ظهور خطأ
    if (input.getAttribute('aria-invalid') === 'true') validateField(field);
  });
});

form.addEventListener('submit', handleSubmit);
$('#new-registration').addEventListener('click', resetToForm);
checkServer();
