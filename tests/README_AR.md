# 🧪 التوثيق الهندسي والمرجع الشامل لحزمة الاختبارات (`tests/`)

يحتوي هذا المجلد على حزمة الاختبارات الآلية الشاملة للبنية التحتية لمشروع **FastAPI Base Structure**. يغطي الدليل الاختبارات الوحدوية المعزولة، مسارات التكامل الشاملة (End-to-End)، والتحقق الأمني من نظام الصلاحيات المبني على الأدوار (RBAC).

---

## فهرس المحتويات
1. [الفلسفة الهندسية وعزل الاختبارات](#1-الفلسفة-الهندسية-وعزل-الاختبارات)
2. [المتطلبات الأساسية وتهيئة البيئة](#2-المتطلبات-الأساسية-وتهيئة-البيئة)
3. [ملف الإعدادات والفيكستشرز المركزية (`conftest.py`)](#3-ملف-الإعدادات-والفيكستشرز-المركزية-conftestpy)
4. [التشريح الفني التفصيلي لملفات الاختبارات](#4-التشريح-الفني-التفصيلي-لملفات-الاختبارات)
   - [`test_security.py`](#test_securitypy--التشفير-وتوكينز-jwt)
   - [`test_health.py`](#test_healthpy--نقاط-فحص-الجاهزية-والحياة)
   - [`test_auth_flow.py`](#test_auth_flowpy--دورة-حياة-المصادقة-والتوثيق)
   - [`test_user_rbac.py`](#test_user_rbacpy--نظام-الصلاحيات-rbac-والصفحات)
5. [دليل أوامر التشغيل عبر سطر الأوامر (CLI Guide)](#5-دليل-أوامر-التشغيل-عبر-سطر-الأوامر-cli-guide)
6. [عقود ونماذج البيانات بالتفصيل (الحالات الإيجابية مقابل السلبية)](#6-عقود-ونماذج-البيانات-بالتفصيل-الحالات-الإيجابية-مقابل-السلبية)
7. [المشاكل الشائعة وأفضل الممارسات الهندسية](#7-المشاكل-الشائعة-وأفضل-الممارسات-الهندسية)

---

## 1. الفلسفة الهندسية وعزل الاختبارات

تعتمد حزمة الاختبارات على 4 ركائز معمارية رئيسية:

1. **العزل الكامل لقاعدة البيانات في الذاكرة (In-Memory SQLite):**
   * تعمل جميع الاختبارات على قاعدة بيانات بالذاكرة العشوائية: `sqlite+aiosqlite:///:memory:`.
   * **انعدام التلوث:** قاعدة البيانات التطويرية الفيزيائية (`database.db`) لا يتم المساس بها نهائياً أثناء تنفيذ الاختبارات.
   * تُبنى الجداول وتُحذف دورياً مع كل اختبار لضمان بيئة نظيفة ومستقلة 100%.

2. **انعدام استهلاك الشبكة بالكامل (`ASGITransport`):**
   * يتم توجيه ومعالجة كافة طلبات HTTP داخلياً عبر `httpx.AsyncClient` المدعوم بـ `ASGITransport(app=app)`.
   * لا يتم فتح منافذ شبكية (TCP Sockets) أو تشغيل خوادم محلية، مما يمنح سرعة تنفيذ فائقة (كامل الحزمة تنتهي في نحو 3 ثوانٍ فقط).

3. **آلية استبدال التبعيات (Dependency Overrides):**
   * يتم استغلال ميزة `app.dependency_overrides` الخاصة بـ FastAPI لاستبدال جلسة قاعدة البيانات الإنتاجية `get_session` بجلسة الذاكرة المعزولة تلقائياً لكل طلب HTTP تجريه الاختبارات.

4. **التوافق غير المتزامن 100% (Async Native Flow):**
   * تُنفذ الاختبارات داخل حلقات أحداث `asyncio` حقيقية بنمط صارم عبر مكتبة `pytest-asyncio`.

---

## 2. المتطلبات الأساسية وتهيئة البيئة

تتطلب حزمة الاختبارات حزم التطوير التالية:
* `pytest` (>= 9.0)
* `pytest-asyncio` (>= 1.4)
* `httpx` (>= 0.28)
* `aiosqlite` (>= 0.22)

لتثبيت ومزامنة حزم الاختبارات بالكامل باستخدام مدير الحزم الحديث `uv`:

```bash
uv sync --extra dev
```

أو في حال إدارة الحزم يدوياً:

```bash
uv add --dev pytest pytest-asyncio
```

---

## 3. ملف الإعدادات والفيكستشرز المركزية (`conftest.py`)

الملف: [`tests/conftest.py`](file:///d:/_Python%20Projects-27-05-2026/fastapi-base-structure-dev/tests/conftest.py)

يمثل هذا الملف العمود الفقري لحزمة الاختبارات؛ حيث يقوم بتهيئة محرك قاعدة البيانات بالذاكرة وإعداد الفيكستشرز (Fixtures) المشتركة:

### المكونات الأساسية

* `TEST_DATABASE_URL = 'sqlite+aiosqlite:///:memory:'`:
  مسار الاتصال غير المتزامن بالذاكرة المؤقتة.
* `test_engine`:
  كائن `create_async_engine` مخصص للاختبارات مع تعطيل الـ `echo`.
* `TestSessionLocal`:
  مصنع الجلسات `async_sessionmaker` مع تعطيل الـ `autoflush` والـ `expire_on_commit`.

### الفيكستشرز المشتركة (Core Fixtures)

| اسم الفيكستشر | النطاق (Scope) | الدور والوظيفة |
|---|---|---|
| `init_test_database` | Function (`autouse=True`) | يقوم آلياً ببناء الجداول (`BaseModel.metadata.create_all`) قبل بدء كل اختبار، ثم يسقطها بالكامل (`drop_all`) فور انتهائه. |
| `db_session` | Function | يوفر كائن جلسة `AsyncSession` متصل بقاعدة بيانات الذاكرة لإجراء عمليات البذر الأولي المباشر للبيانات (Seeding). |
| `client` | Function | يوفر عميل الاختبارات `httpx.AsyncClient` مربوطاً بتطبيق FastAPI مع تفعيل `app.dependency_overrides[get_session]`، وتفريغ التجاوزات عند انتهاء الاختبار. |

---

## 4. التشريح الفني التفصيلي لملفات الاختبارات

### `test_security.py` — التشفير وتوكينز JWT
الملف: [`tests/test_security.py`](file:///d:/_Python%20Projects-27-05-2026/fastapi-base-structure-dev/tests/test_security.py)

اختبارات وحدوية بحتة (Unit Tests) للتحقق من خوارزميات التشفير وتوليد وفك رموز JWT في وحدة `src/security`:

* **`test_password_hashing_and_verification`**:
  * يتحقق من أن `hash_password(raw)` تعيد تجزئة bcrypt مملحة تختلف تماماً عن النص الأصلي.
  * يتحقق من أن `verify_password` تعيد `True` لكلمة المرور الصحيحة و `False` لكلمة المرور الخاطئة.
* **`test_access_token_creation_and_decoding`**:
  * يتحقق من أن `create_access_token(user_id)` تولد توكين JWT صالحاً يحمل الادعاءات: `sub`, `type=TokenType.ACCESS`, ووقت الانتهاء `exp`.
* **`test_refresh_token_creation_and_decoding`**:
  * يتحقق من أن `create_refresh_token(user_id)` تعيد زوجاً `(token, jti)`.
  * يفك شفرة التوكين ويتأكد من تطابق النوع `type=TokenType.REFRESH` وتطابق معرّف `jti` الست عشري المكون من 32 خانة.
* **`test_access_token_type_mismatch`**:
  * يضمن رفض استخدام refresh token في دوال فك access token عبر رفع استثناء `InvalidCredentialsException` (منع هجمات خلط وتبديل التوكينز).

---

### `test_health.py` — نقاط فحص الجاهزية والحياة
الملف: [`tests/test_health.py`](file:///d:/_Python%20Projects-27-05-2026/fastapi-base-structure-dev/tests/test_health.py)

اختبارات تكاملية لنقاط المراقبة والتشخيص في [main.py](file:///d:/_Python%20Projects-27-05-2026/fastapi-base-structure-dev/main.py):

* **`test_health_endpoints`**:
  * **فحص الحياة (`GET /health`)**: يتأكد من استجابة الخادم بـ `200 OK` وجسم JSON يوضح حالة النظام والبيئة ورقم الإصدار.
  * **فحص الجاهزية (`GET /health/ready`)**: يتأكد من قدرة الخادم على الاستعلام الحقيقي من قاعدة البيانات (`SELECT 1`) والرد بـ `200 OK` بحالة `checks: {"database": "ok"}`.

---

### `test_auth_flow.py` — دورة حياة المصادقة والتوثيق
الملف: [`tests/test_auth_flow.py`](file:///d:/_Python%20Projects-27-05-2026/fastapi-base-structure-dev/tests/test_auth_flow.py)

اختبار تكاملي شامل (End-to-End) ينفذ دورة حياة المستخدم الكاملة:

1. **تسجيل الحساب (`POST /api/v1/auth/register`)**:
   * تسجيل حساب جديد بكلمة مرور مشفرة، واستقبال كود `201 Created` مع مخطط `UserResponse`.
2. **منع تكرار البريد الإلكتروني (حالة سلبية)**:
   * إعادة إرسال نفس البريد؛ توقع كود `409 Conflict` مع كائن `ErrorResponse` يحمل الكود `USER_ALREADY_EXISTS`.
3. **رفض كلمات المرور الضعيفة (حالة سلبية)**:
   * إرسال كلمة مرور غير مستوفية للشروط (دون أحرف كبيرة أو أرقام أو رموز)؛ توقع كود `422 Unprocessable Entity`.
4. **تسجيل الدخول (`POST /api/v1/auth/login`)**:
   * إرسال بيانات صحيحة؛ استقبال كود `200 OK` وزوج التوكينز `TokenResponse`.
5. **تدوير الـ Refresh Token بالكامل (`POST /api/v1/auth/refresh`)**:
   * استبدال الـ refresh token بزوج جديد بالكامل؛ التحقق البرمجي من أن التوكينز الجديدة تختلف رياضياً عن السابقة (`new != old`).
6. **منع هجمات إعادة الاستخدام (Replay Attack Prevention) (حالة سلبية)**:
   * إعادة استخدام نفس الـ refresh token القديم بعد تدويره؛ توقع الرفض الفوري بـ `401 Unauthorized` وغلاف أخطاء يحمل الكود `TOKEN_REVOKED`.
7. **تسجيل الخروج من الجهاز الحالي (`POST /api/v1/auth/logout`)**:
   * إبطال جلسة التحديث النشطة واستقبال `200 OK` مع غلاف `MessageResponse`.

---

### `test_user_rbac.py` — نظام الصلاحيات (RBAC) والصفحات
الملف: [`tests/test_user_rbac.py`](file:///d:/_Python%20Projects-27-05-2026/fastapi-base-structure-dev/tests/test_user_rbac.py)

اختبارات تكاملية للتحقق من جدران الحماية الأمنية وتوزيع الصلاحيات:

* **الإعداد الأولي**: بذر مستخدم مشرف (`role=Roles.ADMIN`) ومستخدم عادي (`role=Roles.USER`).
* **استعراض الملف الشخصي (`GET /api/v1/users/me`)**:
  * دخول المستخدم العادي لملفه واسترجاع بياناته برتبة `user` بحالة `200 OK`.
* **جدار حماية الصلاحيات (`GET /api/v1/users`) (حالة سلبية)**:
  * محاولة المستخدم العادي استعراض قائمة المشرفين؛ توقع طرده الفوري بـ `403 Forbidden` ورسالة `ACCESS_DENIED`.
* **استعراض قائمة المستخدمين بصفحات (`GET /api/v1/users?page=1&page_size=10`) (حالة إيجابية)**:
  * طلب المشرف للقائمة؛ توقع كود `200 OK` مع غلاف `PaginatedResponse[UserResponse]`.
  * التحقق من سلامة الميتا: `total=2`, `page=1`, `pages=1`.

---

### `test_audit_logging.py` — سجل التدقيق والتتبع المحمول
الملف: [`tests/test_audit_logging.py`](file:///d:/_Python%20Projects-27-05-2026/fastapi-base-structure-dev/tests/test_audit_logging.py)

اختبارات وحدوية وتكاملية لوحدة سجلات التدقيق والمراقبة المستقلة:

* **عمليات طبقة الخدمة (`test_audit_service_operations`)**:
  * التحقق من حفظ الأحداث الإيجابية والسلبية عبر `save_success_event` و `save_failed_event` في جدول `audit_logs`.
  * التحقق من فلترة واستخراج السجلات الخاصة بمستخدم محدد عبر `get_user_audit_logs`.
  * التحقق من سلامة نواتج التصدير بالتنسيقات الثلاثة: **JSON** و **TXT** و **Markdown**.
* **المسارات الإدارية وحماية الصلاحيات (`test_audit_api_endpoints_and_rbac`)**:
  * التأكد من حرمان المستخدم العادي بـ `403 Forbidden` (`ACCESS_DENIED`) من مسارات الـ Audit.
  * التحقق من قدرة المشرف على تصفح السجلات بالصفحات، جلب سجلات مستخدم معين، وتنزيل ملفات التصدير.

---

## 5. دليل أوامر التشغيل عبر سطر الأوامر (CLI Guide)

### تشغيل كامل حزمة الاختبارات
لتشغيل كافة الاختبارات بالوضع القياسي:
```powershell
uv run pytest
```

### تشغيل الاختبارات بالنمط المفصل (`-v`)
يظهر اسم كل دالة اختبارية وحالتها ووقت تنفيذها بالمللي ثانية:
```powershell
uv run pytest -v
```

### تشغيل الاختبارات مع إظهار السجلات والمخرجات (`-s`)
يعرض الـ Logs ومخرجات `print()` التي تصدر أثناء تنفيذ الكود:
```powershell
uv run pytest -v -s
```

### تشغيل ملف اختباري محدد
```powershell
uv run pytest tests/test_security.py -v
uv run pytest tests/test_health.py -v
uv run pytest tests/test_auth_flow.py -v
uv run pytest tests/test_user_rbac.py -v
```

### تشغيل دالة اختبارية فردية ومحددة
```powershell
uv run pytest tests/test_auth_flow.py::test_auth_full_lifecycle -v
uv run pytest tests/test_user_rbac.py::test_rbac_and_user_endpoints -v
```

### فلترة وتشغيل الاختبارات بالاسم (`-k`)
```powershell
uv run pytest -k "token" -v
uv run pytest -k "rbac" -v
```

---

## 6. عقود ونماذج البيانات بالتفصيل (الحالات الإيجابية مقابل السلبية)

### أ. تسجيل الحساب (`POST /api/v1/auth/register`)

#### 1. الحالة الإيجابية (Success)
* **جسم الطلب (Request JSON):**
  ```json
  {
    "name": "Test Engineer",
    "email": "engineer@enterprise.io",
    "password": "StrongP@ssw0rd!"
  }
  ```
* **كود الاستجابة:** `201 Created`
* **جسم الرد (`UserResponse`):**
  ```json
  {
    "id": 1,
    "name": "Test Engineer",
    "email": "engineer@enterprise.io",
    "role": "user",
    "is_active": true,
    "created_at": "2026-09-28T19:58:44.519000Z",
    "updated_at": "2026-09-28T19:58:44.519000Z"
  }
  ```

#### 2. الحالة السلبية 1: تكرار البريد الإلكتروني (Conflict)
* **جسم الطلب:** إرسال نفس البريد الإلكتروني المسجل سابقاً.
* **كود الاستجابة:** `409 Conflict`
* **جسم الرد (`ErrorResponse`):**
  ```json
  {
    "success": false,
    "error": {
      "code": "USER_ALREADY_EXISTS",
      "message": "User with email 'engineer@enterprise.io' already exists.",
      "details": null
    },
    "request_id": "201d8bc8badf49f2b89a1b796adeb897"
  }
  ```

#### 3. الحالة السلبية 2: ضعف كلمة المرور (Validation Error)
* **جسم الطلب:**
  ```json
  {
    "name": "Test Engineer",
    "email": "engineer2@enterprise.io",
    "password": "simple"
  }
  ```
* **كود الاستجابة:** `422 Unprocessable Entity`
* **جسم الرد (غلاف `ErrorResponse` الموحد):**
  ```json
  {
    "success": false,
    "error": {
      "code": "VALIDATION_ERROR",
      "message": "Invalid request payload.",
      "details": [
        {
          "type": "value_error",
          "loc": ["body", "password"],
          "msg": "Value error, Password must contain at least one uppercase letter."
        }
      ]
    },
    "request_id": "201d8bc8badf49f2b89a1b796adeb897"
  }
  ```

---

### ب. تسجيل الدخول (`POST /api/v1/auth/login`)

#### 1. الحالة الإيجابية (Success)
* **جسم الطلب (Request JSON):**
  ```json
  {
    "email": "engineer@enterprise.io",
    "password": "StrongP@ssw0rd!"
  }
  ```
* **كود الاستجابة:** `200 OK`
* **جسم الرد (`TokenResponse`):**
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer"
  }
  ```

#### 2. الحالة السلبية: بيانات دخول خاطئة (Invalid Credentials)
* **جسم الطلب:**
  ```json
  {
    "email": "engineer@enterprise.io",
    "password": "WrongPassword123!"
  }
  ```
* **كود الاستجابة:** `401 Unauthorized`
* **جسم الرد (`ErrorResponse`):**
  ```json
  {
    "success": false,
    "error": {
      "code": "INVALID_CREDENTIALS",
      "message": "Invalid email or password.",
      "details": null
    },
    "request_id": "9b12f6a73c1d42a8b9821f5e8e3a2014"
  }
  ```

---

### ج. تدوير التوكين (`POST /api/v1/auth/refresh`)

#### 1. الحالة الإيجابية (Rotation Success)
* **جسم الطلب:**
  ```json
  {
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
  ```
* **كود الاستجابة:** `200 OK`
* **جسم الرد (`TokenResponse`):**
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...<NEW>",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...<NEW>",
    "token_type": "bearer"
  }
  ```

#### 2. الحالة السلبية: إعادة استخدام رمز ملغى (Token Revoked)
* **جسم الطلب:** إرسال نفس الـ refresh token القديم بعد تدويره مسبقاً.
* **كود الاستجابة:** `401 Unauthorized`
* **جسم الرد (`ErrorResponse`):**
  ```json
  {
    "success": false,
    "error": {
      "code": "TOKEN_REVOKED",
      "message": "Refresh token has been revoked or is invalid.",
      "details": null
    },
    "request_id": "3f8e12cb5d2a45a689b1c7820e14a519"
  }
  ```

---

### د. قائمة المستخدمين المحمية بالصلاحيات (`GET /api/v1/users`)

#### 1. الحالة الإيجابية (مشرف مع تصفح صفحات)
* **الترويسات:** `Authorization: Bearer <ADMIN_ACCESS_TOKEN>`
* **المعاملات:** `?page=1&page_size=10`
* **كود الاستجابة:** `200 OK`
* **جسم الرد (`PaginatedResponse[UserResponse]`):**
  ```json
  {
    "success": true,
    "data": [
      {
        "id": 1,
        "name": "Root Admin",
        "email": "admin@enterprise.io",
        "role": "admin",
        "is_active": true,
        "created_at": "2026-09-28T20:00:00.000000Z",
        "updated_at": "2026-09-28T20:00:00.000000Z"
      },
      {
        "id": 2,
        "name": "Normal User",
        "email": "user@enterprise.io",
        "role": "user",
        "is_active": true,
        "created_at": "2026-09-28T20:00:00.000000Z",
        "updated_at": "2026-09-28T20:00:00.000000Z"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 10,
      "total": 2,
      "pages": 1
    }
  }
  ```

#### 2. الحالة السلبية: محاولة وصول مستخدم عادي (Access Denied)
* **الترويسات:** `Authorization: Bearer <NORMAL_USER_ACCESS_TOKEN>`
* **كود الاستجابة:** `403 Forbidden`
* **جسم الرد (`ErrorResponse`):**
  ```json
  {
    "success": false,
    "error": {
      "code": "ACCESS_DENIED",
      "message": "Operation requires one of the following roles: ['admin'].",
      "details": null
    },
    "request_id": "e42d7a19c8f341b590e6a1278b30f452"
  }
  ```

---

## 7. المشاكل الشائعة وأفضل الممارسات الهندسية

### تصادم تواقيع التوكينز (Token Collisions)
* **المشكلة البرمجية:** عند توليد توكينز وصول لنفس المستخدم في نفس الثانية، فإن ادعاءات `sub`, `iat`, `exp` تكون متطابقة رياضياً بنسبة 100%، مما ينتج توكينز متطابقة تفشل اختبارات التدوير.
* **الحل المعماري المعتمد:** تم تزويد كل توكين وصول بمعرّف فريد خاص `jti = uuid.uuid4().hex` داخل [TokenPayload](file:///d:/_Python%20Projects-27-05-2026/fastapi-base-structure-dev/src/security/security.py) لضمان استحالة تشابه التوكينز.

### كيفية إضافة اختبار جديد للمشروع
عند بناء مسارات جديدة في المشروع، اتبع هذا النمط المعياري البسيط:

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_new_endpoint(client: AsyncClient):
    response = await client.get("/api/v1/my-path")
    assert response.status_code == 200
    assert response.json()["success"] is True
```

فيكستشر `client` يتولى آلياً تهيئة قاعدة بيانات الذاكرة، تمرير جلسات العمل، وتنظيف البيئة بعد الانتهاء دون أي تدخل يدوي.
