# دليل أداة الإدارة والتحكم المعمارية (`manage.py`)
## FastAPI Base Structure Administrative CLI Reference Manual

> **الوثيقة المرجعية الرسمية لإدارة المشروع، بذر الصلاحيات، وإنشاء وتعيين أدوار المسؤولين خارج النطاق (Out-of-Band Administration).**  
> 🌐 **[English Version (manage.md)](manage.md)**

---

## فهرس المحتويات
1. [الفلسفة المعمارية: لماذا يوجد `manage.py`؟](#1-الفلسفة-المعمارية-لماذا-يوجد-managepy)
   - [معضلة البداية الصفرية (The Chicken-and-Egg Problem)](#معضلة-البداية-الصفرية-the-chicken-and-egg-problem)
   - [الإدارة خارج النطاق (Out-of-Band Administration)](#الإدارة-خارج-النطاق-out-of-band-administration)
   - [حماية وصيانة مجمع الاتصال غير المتزامن](#حماية-وصيانة-مجمع-الاتصال-غير-المتزامن)
2. [التشريح المعماري للسكربت (Architectural Anatomy)](#2-التشريح-المعماري-للسكربت-architectural-anatomy)
   - [نمط المنظم (The Maestro / Dispatcher Pattern)](#نمط-المنظم-the-maestro--dispatcher-pattern)
   - [صمامات التحقق الصارمة مسبقاً (Validation Guards)](#صمامات-التحقق-الصارمة-مسبقا-validation-guards)
   - [صمام الأمان لمنع حبس المسؤولين (Fail-Safe Lockout Prevention)](#صمام-الأمان-لمنع-حبس-المسؤولين-fail-safe-lockout-prevention)
3. [المرجع الشامل للأوامر وسياق الاستخدام](#3-المرجع-الشامل-للأوامر-وسياق-الاستخدام)
   - [الأمر 1: بذر القواعد الافتراضية (`seed-policies`)](#1-seed-policies--بذر-القواعد-التأسيسية)
   - [الأمر 2: إنشاء حساب مسؤول جديد (`create-admin`)](#2-create-admin--إنشاء-مسؤول-جديد)
   - [الأمر 3: ترقية مستخدم حالي إلى مسؤول (`promote-admin`)](#3-promote-admin--ترقية-مستخدم-قائم)
   - [الأمر 4: منح صلاحية لدور (`grant`)](#4-grant--منح-صلاحية-لدور-معين)
   - [الأمر 5: سحب صلاحية من دور (`revoke`)](#5-revoke--سحب-صلاحية-من-دور-معين)
   - [الأمر 6: تعيين دور لمستخدم (`assign-role`)](#6-assign-role--ربط-مستخدم-بدور-إضافي)
   - [الأمر 7: إزالة دور من مستخدم (`unassign-role`)](#7-unassign-role--إلغاء-ربط-مستخدم-بدور)
   - [الأمر 8: عرض قائمة السياسات والتعيينات النشطة (`list-policies`)](#8-list-policies--استعراض-المخطط-الحالي)
4. [سيناريوهات واقعية خطوة بخطوة (Real-World Workflows)](#4-سيناريوهات-واقعية-خطوة-بخطوة-real-world-workflows)
   - [السيناريو أ: تهيئة بيئة عمل جديدة بالكامل (Fresh Install)](#السيناريو-أ-تهيئة-بيئة-عمل-جديدة-بالكامل-fresh-install)
   - [السيناريو ب: إنشاء دور وظيفي مخصص ومنحه لمستخدم (Custom Auditor Role)](#السيناريو-ب-إنشاء-دور-وظيفي-مخصص-ومنحه-لمستخدم-custom-auditor-role)
   - [السيناريو ج: إجراءات الطوارئ وإصلاح الصلاحيات (Break-Glass Procedure)](#السيناريو-ج-إجراءات-الطوارئ-وإصلاح-الصلاحيات-break-glass-procedure)
5. [الأتمتة وخطوط الإنتاج (Docker & CI/CD Pipelines)](#5-الأتمتة-وخطوط-الإنتاج-docker--cicd-pipelines)
6. [استكشاف الأخطاء الشائعة وحلولها (Troubleshooting)](#6-استكشاف-الأخطاء-الشائعة-وحولها-troubleshooting)
7. [أفضل الممارسات الأمنية (Security Best Practices)](#7-أفضل-الممارسات-الأمنية-security-best-practices)

---

## 1. الفلسفة المعمارية: لماذا يوجد `manage.py`؟

في بيئات الويب المؤسسية الحديثة المبنية على **FastAPI**، تُعد حماية الموارد عبر أنظمة الصلاحيات الصارمة (مثل Casbin RBAC) ركيزة أساسية. ولكن هذه القوة المعمارية تخلق تحديات تشغيلية محددة:

```
  +-------------------------------------------------------------+
  |              API Endpoints (FastAPI Application)            |
  |  - Requires valid JWT                                       |
  |  - Requires RBAC check (Users:Read, Users:Write)            |
  |  - FAILS CLOSED (Denies access if no admin/policies exist)   |
  +-------------------------------------------------------------+
                                 ^
                                 |  (Blocked! No admin exists yet)
                                 x
  +-------------------------------------------------------------+
  |                      manage.py (CLI Tool)                   |
  |  - Direct database access via AsyncEngineLocal              |
  |  - Out-of-band administrative execution                     |
  |  - Seeds policies, bootstraps root admin, assigns roles      |
  +-------------------------------------------------------------+
```

### معضلة البداية الصفرية (The Chicken-and-Egg Problem)
عند نشر تطبيق جديد لأول مرة، تكون قاعدة البيانات خالية تماماً من الجداول والبيانات:
1. تطبيق الويب مصمم بمبدأ **الإغلاق التلقائي عند انعدام الصلاحية (Fail-Closed Architecture)**؛ أي طلب نحو نقاط النهاية الإدارية المحمية (مثل `/api/v1/users` أو `/api/v1/audit/logs`) سيُرفض فوراً برمز `403 Forbidden` أو `401 Unauthorized`.
2. لا توجد نقطة نهاية عامة (Public API) تسمح بإنشاء حساب مسؤول؛ لأن فتح نقطة نهاية لإنشاء مسؤول في الإنتاج يُعد ثغرة أمنية كارثية.
3. فكيف يتم إنشاء المسؤول الأول؟ هنا يأتي دور `manage.py` كأداة سطر أوامر معزولة تعمل مباشرة على خادم النظام ولا تمر عبر واجهات HTTP العامة.

### الإدارة خارج النطاق (Out-of-Band Administration)
تتيح أداة `manage.py` لمهندسي النظام وإدارة العمليات (DevOps / SysAdmins):
* بذر وتحديث سياسات الصلاحيات في جدول `casbin_rule` دون الحاجة لكتابة استعلامات SQL يدوية خطرة.
* ترقية مستخدمين أو فك إغلاق الحسابات عند الطوارئ.
* التدقيق البصري الفوري للصلاحيات المطبقة في النظام عبر أوامر سهلة ومقروءة.

### حماية وصيانة مجمع الاتصال غير المتزامن
بما أن المشروع مبني بالكامل على معمارية غير متزامنة (AsyncIO + SQLAlchemy Async Engine)، فإن استدعاء السكربتات دون إغلاق المجمع يتسبب في تسريب اتصالات بقاعدة البيانات (Connection Leaks). يقوم `manage.py` بضمان التخلص من المجمع دائماً في كتلة `finally`:
```python
try:
    asyncio.run(handler())
finally:
    asyncio.run(AsyncEngineLocal.dispose())
```

---

## 2. التشريح المعماري للسكربت (Architectural Anatomy)

تم بناء `manage.py` وفقاً لـ **دستور بايثون المؤسسي (Enterprise Python Architecture Constitution)**:

### نمط المنظم (The Maestro / Dispatcher Pattern)
الدالة الرئيسية `main()` لا تحتوي على أي منطق عمل تجاري (Business Logic)؛ بل تقتصر مسؤوليتها على:
1. بناء شجرة الأوامر والخيارات عبر `build_parser()`.
2. استلام الأمر وتوجيهه للدالة المختصة عبر جدول توجيه نظيف (`command_handlers`).
3. عزل إدارة الاستثناءات وإرجاع رموز الخروج المعيارية للنظام (`sys.exit(0)` عند النجاح، و `sys.exit(1)` عند الفشل).

### صمامات التحقق الصارمة مسبقاً (Validation Guards)
قبل المساس بقاعدة البيانات أو إضافة أي سياسة لـ Casbin، تخضع كافة المدخلات لفحص حتمي استباقي:
* **`validate_role_name(role)`**:
  * تمنع استخدام البادئة المحجوزة `user:` لمنع حدوث التباس مع المعرفات الفردية للمستخدمين (`user:1`).
  * تفرض نمط التسمية بأحرف صغيرة مع خطوط سفلية بطول 2-50 حرفاً عبر Regex: `^[a-z][a-z0-9_]{1,49}$`.
* **`validate_resource(resource)`**:
  * تضمن مطابقة المورد للقائمة المعرفة حصراً في التعداد `Resource` (مثل: `users`, `audit`) أو الرمز الشامل `*`.
* **`validate_action(action)`**:
  * تضمن مطابقة العملية للقائمة المعرفة حصراً في التعداد `Action` (مثل: `create`, `read`, `update`, `delete`, `export`) أو الرمز الشامل `*`.
* **استخدام Pydantic Validation في `create-admin`**:
  * يتم تمرير بيانات المسؤول الجديد إلى نموذج `RegisterRequest` قبل لمس قاعدة البيانات للتأكد من قوة كلمة المرور، وصحة صيغة البريد الإلكتروني.

### صمام الأمان لمنع حبس المسؤولين (Fail-Safe Lockout Prevention)
لمنع قيام مهندس عمليات بحذف صلاحية المسؤول الشاملة عن طريق الخطأ:
```python
if args.role == 'admin' and args.resource == '*' and args.action == '*' and not args.force:
    print("Safety Warning: Revoking (admin, *, *) will lock out all administrators...")
    sys.exit(1)
```
يتطلب سحب القاعدة الشاملة التمرير الصريح لخيار `--force`.

---

## 3. المرجع الشامل للأوامر وسياق الاستخدام

يتم تشغيل كافة الأوامر عبر مدير الحزم `uv` لضمان العمل ضمن البيئة الافتراضية الصحيحة ومحاذاة التبعيات:

```bash
uv run python manage.py <command> [options]
```

---

### 1. `seed-policies` — بذر القواعد التأسيسية

* **الهدف:** بذر سياسات الصلاحيات الافتراضية اللازمة لعمل النظام لأول مرة في جدول `casbin_rule` دون تكرار القواعد الموجودة مسبقاً (Idempotent Operation).
* **القواعد التي يتم بذرها:**
  1. `(admin, *, *)`: يمنح دور المسؤول صلاحية كاملة على كل الموارد والعمليات.
  2. `(user, users, read)`: يمنح المستخدم العادي صلاحية قراءة الملفات الشخصية.
* **طريقة الاستخدام:**
  ```bash
  uv run python manage.py seed-policies
  ```
* **المخرجات المتوقعة:**
  ```text
  Successfully seeded default policies (2 new rule(s) added).
  ```
  *(إذا كانت القواعد موجودة مسبقاً، سيعيد `0 new rule(s) added` دون إحداث أي خلل).*

---

### 2. `create-admin` — إنشاء مسؤول جديد

* **الهدف:** إنشاء حساب مستخدم برتبة مسؤول (`role='admin'`) مشفر بـ Argon2id، ومفعل فوراً مع ضبط `security_version=1`.
* **الخيارات:**
  * `--email` (إجباري): البريد الإلكتروني للمسؤول.
  * `--name` (إجباري): الاسم الظاهر للمسؤول.
  * `--password` (اختياري): كلمة المرور. **(إذا تم إهمالها، يطلبها السكربت تفاعلياً ومخفياً عبر `getpass` لضمان أمان الطرفية)**.
* **طريقة الاستخدام التفاعلية (الموصى بها بشدة):**
  ```bash
  uv run python manage.py create-admin --email "admin@enterprise.io" --name "Super Admin"
  ```
  ```text
  Enter admin password: 
  Confirm admin password: 
  Admin user successfully created with ID 1 (email: admin@enterprise.io).
  ```
* **طريقة الاستخدام غير التفاعلية (خاصة بالـ CI/CD وسكربتات التهيئة):**
  ```bash
  uv run python manage.py create-admin --email "admin@enterprise.io" --name "Super Admin" --password "SuperSecretPass123!"
  ```

---

### 3. `promote-admin` — ترقية مستخدم قائم

* **الهدف:** تحويل حساب مستخدم عادي مسجل مسبقاً في النظام إلى رتبة مسؤول (`role='admin'`) مباشرة في قاعدة البيانات.
* **الشروط:**
  * يجب أن يكون الحساب موجوداً بالفعل.
  * يجب أن يكون الحساب نشطاً (`is_active=True`). لا يمكن ترقية حساب معطل.
* **الخيارات:**
  * `--email` (إجباري): البريد الإلكتروني للحساب المراد ترقيته.
* **طريقة الاستخدام:**
  ```bash
  uv run python manage.py promote-admin --email "jane.dev@enterprise.io"
  ```
* **المخرجات المتوقعة:**
  ```text
  User 'jane.dev@enterprise.io' (ID: 4) successfully promoted to Admin.
  ```

---

### 4. `grant` — منح صلاحية لدور معين

* **الهدف:** إنشاء قاعدة سياسة جديدة (`p`) تربط دوراً معيناً بمورد وعملية محددة.
* **المعاملات الترتيبية (Positional Arguments):**
  1. `role`: اسم الدور (مثال: `auditor`, `support`, `manager`).
  2. `resource`: المورد المستهدف (مثال: `users`, `audit`, أو `*`).
  3. `action`: العملية المسموحة (مثال: `read`, `export`, `create`, أو `*`).
* **أمثلة:**
  ```bash
  # منح دور مدقق الحسابات صلاحية قراءة سجلات التدقيق
  uv run python manage.py grant auditor audit read

  # منح دور مدقق الحسابات صلاحية تصدير سجلات التدقيق
  uv run python manage.py grant auditor audit export

  # منح دور مدير الدعم الفني صلاحية القراءة على جميع الموارد
  uv run python manage.py grant support * read
  ```
* **المخرجات المتوقعة:**
  ```text
  Successfully granted: (auditor, audit, read).
  ```

---

### 5. `revoke` — سحب صلاحية من دور معين

* **الهدف:** حذف سياسة صلاحية قائمة (`p`) من جدول التخزين وإلغاء مفعولها اللحظي.
* **المعاملات الترتيبية والخيارات:**
  1. `role`: اسم الدور.
  2. `resource`: المورد.
  3. `action`: العملية.
  4. `--force` (اختياري): مطلوب حصراً إذا كنت تحاول سحب الصلاحية الشاملة `admin * *`.
* **أمثلة:**
  ```bash
  # سحب صلاحية التصدير من دور auditor
  uv run python manage.py revoke auditor audit export

  # محاولة سحب صلاحية المسؤول الشاملة دون إجبار (ستفشل للأمان)
  uv run python manage.py revoke admin * *
  # المخرجات:
  # Safety Warning: Revoking (admin, *, *) will lock out all administrators.
  # If you really intend to do this, pass the --force flag.

  # سحب صلاحية المسؤول الشاملة مع تأكيد الإجبار
  uv run python manage.py revoke admin * * --force
  ```

---

### 6. `assign-role` — ربط مستخدم بدور إضافي

* **الهدف:** إنشاء قاعدة تجميع وتوريث (`g`) تربط مستخدماً محدداً (عبر معرفه الرقمي `user:<id>`) بدور من أدوار Casbin.
* **المعاملات الترتيبية:**
  1. `user_id`: المعرف الرقمي للمستخدم في جدول `users`.
  2. `role`: اسم الدور المراد إسناده إليه.
* **الفحص المسبق:** يتحقق السكربت من وجود المستخدم في قاعدة البيانات أولاً؛ فإذا كان الرقم غير موجود، يرفض العملية فوراً.
* **أمثلة:**
  ```bash
  # إسناد دور auditor للمستخدم صاحب المعرف رقم 2
  uv run python manage.py assign-role 2 auditor
  ```
* **المخرجات المتوقعة:**
  ```text
  Successfully assigned role 'auditor' to user 2 (user:2).
  ```

---

### 7. `unassign-role` — إلغاء ربط مستخدم بدور

* **الهدف:** حذف قاعدة التجميع (`g`) الخاصة بالمستخدم، مما يجرده فورياً من كافة الامتيازات المرتبطة بذلك الدور.
* **المعاملات الترتيبية:**
  1. `user_id`: المعرف الرقمي للمستخدم.
  2. `role`: اسم الدور المراد فك ارتباطه.
* **أمثلة:**
  ```bash
  uv run python manage.py unassign-role 2 auditor
  ```
* **المخرجات المتوقعة:**
  ```text
  Successfully removed role 'auditor' from user 2.
  ```

---

### 8. `list-policies` — استعراض المخطط الحالي

* **الهدف:** طباعة جدول نصي منسق يوضح كافة سياسات الصلاحيات النشطة (`p`)، وكافة تعيينات وتوريثات الأدوار للمستخدمين (`g`).
* **طريقة الاستخدام:**
  ```bash
  uv run python manage.py list-policies
  ```
* **مثال على المخرجات:**
  ```text
  --- Active Permission Policies ('p') ---
    ROLE / SUBJECT       RESOURCE        ACTION         
    --------------------------------------------------
    admin                *               *              
    user                 users           read           
    auditor              audit           read           
    auditor              audit           export         

  --- Active Role Groupings ('g') ---
    MEMBER               ROLE                
    ----------------------------------------
    user:2               auditor             
  ```

---

## 4. سيناريوهات واقعية خطوة بخطوة (Real-World Workflows)

### السيناريو أ: تهيئة بيئة عمل جديدة بالكامل (Fresh Install)
عند استنساخ المشروع أو تثبيته على سيرفر جديد، نفّذ التسلسل التالي بالترتيب:

```bash
# 1. تطبيق ترحيلات قاعدة البيانات
uv run alembic upgrade head

# 2. بذر السياسات التأسيسية لـ Casbin
uv run python manage.py seed-policies

# 3. إنشاء حساب المسؤول الأول
uv run python manage.py create-admin --email "root@enterprise.io" --name "Root Admin"

# 4. التحقق من اكتمال التهيئات
uv run python manage.py list-policies
```

---

### السيناريو ب: إنشاء دور وظيفي مخصص ومنحه لمستخدم (Custom Auditor Role)
افترض أنك تريد منح موظف في قسم الامتثال (البريد: `compliance@enterprise.io` ومعرفه `ID = 5`) صلاحية الاطلاع على وتصدير سجلات النظام المحمية `/api/v1/audit/logs` و `/api/v1/audit/export`:

```bash
# الخطوة 1: إنشاء السياسات وربطها بالدور الجديد 'auditor'
uv run python manage.py grant auditor audit read
uv run python manage.py grant auditor audit export

# الخطوة 2: ربط المستخدم (ID: 5) بالدور
uv run python manage.py assign-role 5 auditor

# الخطوة 3: التحقق
uv run python manage.py list-policies
```
* **النتيجة اللحظية:** بمجرد تنفيذ الأمر، وفي الطلب القادم للمستخدم نحو الـ API، سيتحقق `require_permission(Resource.AUDIT, Action.READ)` ويسمح له بالدخول فوراً دون الحاجة لإعادة تشغيل خادم FastAPI أو تعديل كود المشروع!

---

### السيناريو ج: إجراءات الطوارئ وإصلاح الصلاحيات (Break-Glass Procedure)
إذا حدث خلل وتم تعطيل أو حذف صلاحيات الوصول، أو تم قفل حساب المسؤول:

```bash
# ترقية حساب قائم على الفور إلى رتبة المسؤول الشامل
uv run python manage.py promote-admin --email "backup-admin@enterprise.io"

# التأكد من وجود الصلاحية الشاملة
uv run python manage.py grant admin * *
```

---

## 5. الأتمتة وخطوط الإنتاج (Docker & CI/CD Pipelines)

في بيئات النشر المؤتمتة (مثل Dockerfile أو Kubernetes Init-Containers أو GitHub Actions)، يمكن استخدام `manage.py` لتهيئة الحاويات قبل انطلاق سيرفر الويب:

### مثال على ملف Entrypoint (`entrypoint.sh`):
```bash
#!/usr/bin/env bash
set -e

echo "==> Running database migrations..."
uv run alembic upgrade head

echo "==> Seeding baseline authorization policies..."
uv run python manage.py seed-policies

# إنشاء مسؤول تلقائياً فقط إذا تم تزويد المتغيرات البيئية
if [ -n "$INITIAL_ADMIN_EMAIL" ] && [ -n "$INITIAL_ADMIN_PASSWORD" ]; then
    echo "==> Bootstrapping initial admin account..."
    uv run python manage.py create-admin \
        --email "$INITIAL_ADMIN_EMAIL" \
        --name "${INITIAL_ADMIN_NAME:-Administrator}" \
        --password "$INITIAL_ADMIN_PASSWORD" || true
fi

echo "==> Starting FastAPI Uvicorn Server..."
exec uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## 6. استكشاف الأخطاء الشائعة وحلولها (Troubleshooting)

| الخطأ / الرسالة | السبب المحتمل | الحل العلاجي |
| :--- | :--- | :--- |
| `Role names cannot begin with the reserved prefix 'user:'.` | محاولة تمرير دور اسمه `user:admin` أو مشابه. | البادئة `user:` محجوزة حصراً لمعرفات الأشخاص. استخدم اسماً مجرداً مثل `auditor` أو `manager`. |
| `Invalid role name 'Auditor-Team'. Must be 2-50 characters...` | استخدام أحرف كبيرة أو شرطات عادية أو رموز خاصة. | يجب أن تكون أسماء الأدوار بأحرف صغيرة مع خطوط سفلية فقط (Regex: `^[a-z][a-z0-9_]{1,49}$`)، مثل `auditor_team`. |
| `Unknown resource 'analytics'. Allowed values: ['audit', 'users', '*']` | محاولة منح صلاحية على مورد غير مسجل في `Resource Enum`. | أضف المورد الجديد أولاً إلى التعداد في `src/share/enum.py` ثم أعد تنفيذ الأمر. |
| `Unknown action 'download'. Allowed values: ['*', 'create', 'delete', 'export', 'read', 'update']` | محاولة منح عملية غير معرفة في `Action Enum`. | استخدم إحدى العمليات المعيارية المعتمدة في النظام. |
| `Error: User with ID 99 does not exist.` | محاولة ربط دور بمستخدم غير موجود في جدول `users`. | تأكد من المعرف الصحيح للمستخدم المسجل قبل استدعاء `assign-role`. |
| `Error: User '...' is deactivated and cannot be promoted.` | محاولة ترقية مستخدم تم إلغاء تفعيله (`is_active=False`). | يجب إعادة تفعيل حساب المستخدم في قاعدة البيانات أولاً قبل ترقيته إلى Admin. |

---

## 7. أفضل الممارسات الأمنية (Security Best Practices)

1. **تجنب كتابة كلمات المرور في الطرفية:**
   * عند استخدام `create-admin` في البيئة الإنتاجية أو على جهازك، لا تمرر `--password "..."` كمعامل؛ لأن ذلك يحفظ كلمة المرور كنص صريح في تاريخ الطرفية (`~/.bash_history` أو سجلات PowerShell).
   * اترك الأمر يطلبها تفاعلياً؛ حيث يستخدم `getpass` الذي يخفي الحروف المدخلة تماماً.
2. **الالتزام بمبدأ الحد الأدنى من الامتيازات (PoLP):**
   * لا تمنح دوراً صلاحية `* *` إلا لدور `admin`. للأدوار الوظيفية الأخرى، حدد المورد بدقة (مثل `audit`) والعملية بدقة (مثل `read`).
3. **التدقيق الدوري لسياسات الصلاحيات:**
   * قم بتشغيل `uv run python manage.py list-policies` بشكل دوري أو بعد كل تعديل للتحقق من عدم وجود قواعد متضاربة أو متروكة لمستخدمين غادروا مهامهم الوظيفية.
4. **عزل الوصول إلى الخادم:**
   * ملف `manage.py` هو أداة وصول جذري (Root Tool). يجب حصر إمكانية تشغيله على خوادم الإنتاج بمهندسي النظام المصرح لهم فقط عبر SSH مع مصادقة ثنائية ومفاتيح مشفرة.
