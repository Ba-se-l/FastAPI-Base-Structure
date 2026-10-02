# 🚀 البنية التحتية القياسية لتطبيقات FastAPI للمؤسسات (v1.0.0)

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141+-009688.svg)](https://fastapi.tiangolo.com)
[![SQLAlchemy 2.0](https://img.shields.io/badge/SQLAlchemy-2.0+-red.svg)](https://www.sqlalchemy.org/)
[![Alembic](https://img.shields.io/badge/Alembic-Async-orange.svg)](https://alembic.sqlalchemy.org/)
[![Pydantic v2](https://img.shields.io/badge/Pydantic-V2-green.svg)](https://docs.pydantic.dev/)
[![Code Style: PEP 8](https://img.shields.io/badge/code%20style-PEP%208-black.svg)](https://peps.python.org/pep-0008/)

بنية أساسية للمشاريع الخلفية (Backend Foundation) متقدمة، فائقة الأداء، وعالية التماسك، مبنية باستخدام **FastAPI** و **SQLAlchemy 2.0 (Async)** و **Pydantic V2**. صُممت وفق مبادئ التصميم الموجه بالنطاق (DDD-lite)، ونمط المنسق والخبير (Orchestrator-Specialist Pattern)، ومعايير صارمة تضمن الأمان وقابلية التوسع للمؤسسات الكبرى.

---

## 📑 فهرس المحتويات

- [الفلسفة المعمارية](#-الفلسفة-المعمارية)
- [هيكل المشروع والمجلدات](#-هيكل-المشروع-والمجلدات)
- [الأنظمة والوحدات الأساسية](#-الأنظمة-والوحدات-الأساسية)
  - [1. التوثيق والمصادقة ودورة حياة الـ JWT](#1-التوثيق-والمصادقة-ودورة-حياة-الـ-jwt)
  - [2. التحكم في الوصول المستند للأدوار (RBAC)](#2-التحكم-في-الوصول-المستند-للأدوار-rbac)
  - [3. قاعدة البيانات وهجرات Alembic اللازامنة](#3-قاعدة-البيانات-وهجرات-alembic-اللازامنة)
  - [4. نظام التدقيق الأمني والتتبع الشامل (Audit Logging & Telemetry)](#4-نظام-التدقيق-الأمني-والتتبع-الشامل-audit-logging--telemetry)
  - [5. قوالب وأغلفة الردود الموحدة (Unified Envelopes)](#5-قوالب-وأغلفة-الردود-الموحدة-unified-envelopes)
- [دليل البدء السريع (Quickstart)](#-دليل-البدء-السريع-quickstart)
  - [المتطلبات المسبقة](#المتطلبات-المسبقة)
  - [التثبيت والإعداد](#التثبيت-والإعداد)
  - [تهيئة متغيرات البيئة](#تهيئة-متغيرات-البيئة)
  - [تطبيق هجرات قاعدة البيانات](#تطبيق-هجرات-قاعدة-البيانات)
  - [تشغيل الخادم](#تشغيل-الخادم)
- [منظومة الاختبارات المؤتمتة (Testing Suite)](#-منظومة-الاختبارات-المؤتمتة-testing-suite)
- [دليل المطور: كيفية إضافة نطاق جديد للمشروع](#-دليل-المطور-كيفية-إضافة-نطاق-جديد-للمشروع)
- [الترخيص](#-الترخيص)

---

## 🏛 الفلسفة المعمارية

1. **المعمارية المعيارية الموجهة بالنطاق (Domain Modular Architecture):**
   يتم تقسيم منطق الأعمال إلى موديولات مستقلة بذاتها تحت `src/modules/` (`auth`, `user`, `audit`). كل موديول يحتوي داخلياً على نماذجه (Models)، مستودعاته (Repositories)، مخططاته (Schemas)، خدماته (Services)، ومساراته (Routers).
2. **نمط المنسق والخبير (Orchestrator-Specialist Pattern):**
   * **الراوترات (Routers):** مسؤولة حصرياً عن استقبال طلبات الـ HTTP والتحقق من التبعيات وتنسيق كود الاستجابة دون كتابة استعلامات SQL أو منطق أعمال بداخلها.
   * **الخدمات (Services - Maestros):** تنسيق العمليات الحيوية وتطبيق قواعد الأعمال المعقدة.
   * **المستودعات (Repositories - Specialists):** فئات CRUD عامة وغير متزامنة تتبع مبدأ المسؤولية الواحدة (SRP).
3. **عقود بيانات Pydantic V2 أولاً:**
   كل البيانات التي تعبر حدود النظام (HTTP أو قاعدة البيانات) يتم التحقق من صحتها وتدقيق أنواعها عبر نماذج Pydantic صارمة.
4. **الأنظمة النوعية الحديثة (Python 3.10+):**
   استخدام علامة الأنبوب `|` للأنواع، واستخدام `StrEnum` للحالات الثابتة، ومنع استخدام الأنواع الملغاة القديمة.
5. **إمكانية الرصد وتتبع الأخطاء:**
   حقن معرفات التتبع الفريدة (`X-Request-ID`) عبر جميع الطلبات وتوحيد غلاف الردود للأخطاء لسهولة المراقبة.

---

## 📂 هيكل المشروع والمجلدات

```text
fastapi-base-structure/
├── main.py                     # نقطة دخول التطبيق، دورة الحياة (Lifespan)، البرمجيات الوسيطة، ومعالجات الأخطاء
├── pyproject.toml              # بيانات المشروع والاعتماديات (مُدار عبر uv)
├── alembic.ini                 # إعدادات هجرات قاعدة البيانات Alembic
├── .env.example                # نموذج متغيرات البيئة المشروح
├── migrations/                 # بيئة هجرات Alembic غير المتزامنة
│   ├── env.py                  # ملف تشغيل الهجرات المربوط بالإعدادات والنماذج
│   ├── script.py.mako          # قالب التوليد التلقائي لملفات الهجرة
│   ├── README.md               # دليل التعامل مع الهجرات (English)
│   ├── README_AR.md            # دليل التعامل مع الهجرات (العربية)
│   └── versions/               # ملفات الهجرات المؤرخة والمفهرسة
├── src/
│   ├── database/               # بنية قاعدة البيانات التحتية
│   │   ├── __init__.py         # واجهة الاستيراد العامة
│   │   ├── base.py             # DeclarativeBase مع معايير التسمية القياسية للقيود
│   │   ├── base_repo.py        # المستودع العام BaseRepository[Model] (Async CRUD)
│   │   ├── engine.py           # محرك AsyncEngine وفاحص الاتصال الأولي
│   │   ├── mixin.py            # DateTimeMixin (حقول created_at و updated_at آلياً)
│   │   └── session.py          # مزود جلسة قاعدة البيانات غير المتزامنة (get_session)
│   ├── exc/                    # التسلسل الهرمي للاستثناءات
│   │   ├── __init__.py         # تصدير الاستثناءات العامة
│   │   └── base.py             # صنف AppException الأساسي
│   ├── modules/                # النطاقات الوظيفية (Domain-Driven)
│   │   ├── __init__.py         # الراوتر المركزي المجمّع لكل الموديولات
│   │   ├── auth/               # نطاق المصادقة وإدارة الجلسات
│   │   │   ├── dependencies.py # حقن التبعيات (get_current_user, require_role)
│   │   │   ├── model.py        # نموذج RefreshSession لقاعدة البيانات
│   │   │   ├── repo.py         # مستودع RefreshSessionRepository
│   │   │   ├── router.py       # مسارات المصادقة (/login, /register, /refresh, /logout)
│   │   │   ├── schemas.py      # مخططات Pydantic (LoginRequest, RegisterRequest)
│   │   │   └── service.py      # منطق الأعمال للمصادقة وتوليد التوكن والتدقيق
│   │   ├── user/               # نطاق إدارة المستخدمين
│   │   │   ├── model.py        # نموذج المستخدم User ORM
│   │   │   ├── repo.py         # مستودع UserRepository مع دعم الـ Overload
│   │   │   ├── router.py       # مسارات المستخدمين (/me, /{id}, list, update)
│   │   │   ├── schemas.py      # UserResponse, UserUpdate
│   │   │   └── service.py      # خدمات المستخدمين مع الفحص الأمني المسبق
│   │   └── audit/              # نطاق التدقيق الأمني وسجلات النظام
│   │       ├── enum.py         # تصنيفات الشدة (LogSeverity) والعمليات (LogAction)
│   │       ├── formatters.py   # منسقات السجلات إلى JSON (NDJSON)، نص، وMarkdown
│   │       ├── model.py        # نموذج AuditLog في قاعدة البيانات مع فهارس مركبة
│   │       ├── repo.py         # مستودع استعلام وتصفية السجلات AuditLogRepository
│   │       ├── router.py       # مسارات الاستعلام والتصدير للمدراء (/logs, /export)
│   │       ├── schemas.py      # مخططات LogEvent, LogResponse, LogQueryFilter
│   │       └── service.py      # منسق الحفظ متعدد المصادر (قاعدة بيانات + أقراص)
│   ├── security/               # خوارزميات التشفير وحماية البيانات
│   │   ├── __init__.py         # واجهة التصدير
│   │   └── security.py         # تشفير كلمات المرور (bcrypt) وتوليد/فك JWT
│   ├── settings/               # إدارة الإعدادات ومتغيرات البيئة
│   │   ├── __init__.py         # واجهة الإعدادات
│   │   └── settings.py         # كلاس Settings مع فحص صارم لبيئة الإنتاج
│   └── share/                  # العناصر المشتركة عبر النظام
│       ├── __init__.py         # واجهة التصدير
│       ├── enum.py             # الرتب (Roles) وأنواع التوكن (TokenType)
│       ├── responses.py        # قوالب الردود (ErrorResponse, PaginatedResponse, MessageResponse)
│       └── schemas.py          # كائن السياق AuditContext وتتبع الفروقات get_extra_dict_for_updates
└── tests/                      # حزمة الاختبارات المؤتمتة الشاملة (17 اختبار)
    ├── conftest.py             # تركيبات الاختبار مع SQLite في الذاكرة (Async)
    ├── test_security.py        # اختبارات التشفير والـ JWT
    ├── test_auth_flow.py       # دورة حياة التسجيل والدخول والخروج الكاملة
    ├── test_user_rbac.py       # اختبار الصلاحيات والترقيم
    ├── test_user_crud.py       # اختبارات التعديل والحذف وتدقيق البيانات
    ├── test_validation_envelope.py # اختبار شكل الأخطاء الموحد 422
    ├── test_pagination_edges.py # اختبار الحالات الحدية للترقيم
    ├── test_audit_logging.py   # اختبارات التدقيق الأمني، التصدير، وحجب كلمات المرور
    ├── test_audit_db_disabled.py # اختبار مرونة السجلات عند تعطيل الداتابيز
    ├── test_health.py          # اختبار مسارات الفحص الصحي
    ├── README.md               # دليل الاختبارات (English)
    └── README_AR.md            # دليل الاختبارات (العربية)
```

---

## ⚡ الأنظمة والوحدات الأساسية

### 1. التوثيق والمصادقة ودورة حياة الـ JWT
- **نظام التوكن الثنائي (Dual Token Pair):** إصدار توكن وصول قصير الأجل (30 دقيقة) وتوكن تحديث طويل الأجل (30 يوماً).
- **تتبع JTI التشفيري:** كل توكن تحديث يحمل معرّفاً فريداً (`jti`) مسجلاً في جدول `refresh_sessions`.
- **تدوير التوكن وكشف الهجمات (Rotation & Replay Attack Defense):** عند استخدام توكن تم استبداله أو إلغاؤه سابقاً، يكتشف النظام فوراً هجوماً محتملاً لسرقة الجلسة (Token Theft) ويقوم فوراً بإبطال جميع جلسات المستخدم وتسجيل حدث حرج `AUTH_TOKEN_REVOKED` بشدة `CRITICAL`.
- **تجزئة كلمات المرور الآمنة:** استخدام خوارزمية `bcrypt` القوية.

---

### 2. التحكم في الوصول المستند للأدوار (RBAC)
- **أدوار نوعية صارمة:** `Roles(StrEnum)` تحوي `USER` و `ADMIN`.
- **فحص الصلاحيات بحقن التبعيات:**
  ```python
  @router.get("", dependencies=[Depends(require_role(Roles.ADMIN))])
  async def list_users(...):
      ...
  ```
- **الحماية من استكشاف المستخدمين (User Enumeration Defense):** التحقق من الصلاحيات يتم **قبل** أي استعلام لقاعدة البيانات، مما يمنع المهاجم من التمييز بين المستخدم غير الموجود والمستخدم الممنوع من الوصول.

---

### 3. قاعدة البيانات وهجرات Alembic اللازامنة
- **SQLAlchemy 2.0 Async Native:** استخدام `AsyncEngine` و `async_sessionmaker`.
- **تسمية القيود الموحدة:** تضمن إنشاء وتعديل الجداول تلقائياً عبر Alembic بدون أخطاء عبر SQLite و PostgreSQL.
- **إدارة المخطط عبر الهجرات فقط:** منع التوليد العشوائي للجداول في الإنتاج وحصرها في ملفات الهجرات المحفوظة في المستودع.

---

### 4. نظام التدقيق الأمني والتتبع الشامل (Audit Logging & Telemetry)
- **حفظ متعدد المصادر (Multi-Sink):** كتابة السجل في نفس اللحظة لقاعدة البيانات والملفات النصية على القرص في مسار `logs/`.
- **صيغة NDJSON الصارمة:** كتابة سطر JSON واحد لكل سجل، مما يسمح لأدوات المراقبة الحديثة مثل Vector و Filebeat و Loki بقراءتها فوراً بدون أي تأخير.
- **كائن سياق التدقيق النقي (`AuditContext`):**
  كلاس `@dataclass(frozen=True, slots=True)` فائق السرعة وخفيف على الذاكرة، يتم حقنه في الراوتر بسطر واحد عبر:
  ```python
  audit_ctx: AuditContext = Depends(get_audit_context)
  ```
  يقوم الكائن تلقائياً باستخراج:
  * عنوان الـ IP الحقيقي (مع دعم كامل لخوادم البروكسي العكسي مثل Cloudflare و Nginx عبر `X-Forwarded-For`).
  * ترويسة المتصفح والعميل (`User-Agent`).
  * معرّف الطلب الموحد (`request_id`).
- **حظر تسريب كلمات المرور الصريح (Zero Credential Leakage):**
  استبعاد كلمات المرور الصريحة دائماً عند حفظ بيانات التسجيل (`extra_data={"email": user.email, "name": user.name}`) لمنع حفظ كلمات المرور في السجلات.
- **تتبع فروقات التعديل (`get_extra_dict_for_updates`):**
  التقاط الحالة القديمة للمستخدم قبل التحديث ومقارنتها بالقيم الجديدة لتوثيق: `{"name": {"old": "Ahmad", "new": "Ahmad Ali"}}`.
- **تصدير السجلات بثلاث صيغ:** مسارات إدارية تتيح تنزيل سجلات التدقيق بصيغ `JSON` و `TXT` و `Markdown Table`.

---

### 5. قوالب وأغلفة الردود الموحدة (Unified Envelopes)
* **غلاف القوائم المرقّمة (Paginated Envelope):**
  ```json
  {
    "success": true,
    "data": [ ... ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 100,
      "pages": 5
    }
  }
  ```
* **غلاف التأكيدات الإجرائية (Message Response):**
  ```json
  {
    "success": true,
    "message": "Logged out successfully."
  }
  ```
* **غلاف الأخطاء الموحد (Error Envelope):**
  شكل ثابت لا يتغير لأي خطأ في النظام (400, 401, 403, 404, 422, 500):
  ```json
  {
    "success": false,
    "error": {
      "code": "VALIDATION_ERROR",
      "message": "Invalid request payload.",
      "details": [ ... ]
    },
    "request_id": "9a4f6d8c0b2e4f..."
  }
  ```

---

## 🚀 دليل البدء السريع (Quickstart)

### المتطلبات المسبقة
- **Python 3.13** أو أحدث.
- أداة [**`uv`**](https://docs.astral.sh/uv/) (مدير الحزم السريع جداً لبايثون).

### التثبيت والإعداد
قم بنسخ المستودع وتثبيت الاعتماديات:
```bash
git clone <repository-url>
cd fastapi-base-structure
uv sync
```

### تهيئة متغيرات البيئة
انسخ ملف الإعدادات النموذجي:
```bash
cp .env.example .env
```
أهم المتغيرات:
| المتغير | القيمة الافتراضية | الوصف |
|:---|:---|:---|
| `ENVIRONMENT` | `dev` | بيئة التشغيل (`dev`, `test`, `staging`, `pro`) |
| `DATABASE_URL` | `sqlite+aiosqlite:///./database.db` | رابط الاتصال بقاعدة البيانات غير المتزامنة |
| `ACCESS_SECRET_KEY` | `...` | مفتاح تشفير توكن الوصول (JWT) |
| `REFRESH_SECRET_KEY` | `...` | مفتاح تشفير توكن التحديث (JWT) |
| `LOG_TO_DB` | `true` | تفعيل/تعطيل حفظ السجلات في قاعدة البيانات |
| `LOG_TO_FILE` | `true` | تفعيل/تعطيل كتابة السجلات في ملفات القرص |

### تطبيق هجرات قاعدة البيانات
لتطبيق جميع الهجرات وإنشاء الجداول:
```bash
uv run alembic upgrade head
```

### تشغيل الخادم
لتشغيل خادم التطوير مع التحديث التلقائي (Live Reload):
```bash
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000
```
يمكنك فتح التوثيق التفاعلي للـ API عبر:
- **Swagger UI:** `http://127.0.0.1:8000/docs`
- **ReDoc:** `http://127.0.0.1:8000/redoc`

---

## 🧪 منظومة الاختبارات المؤتمتة (Testing Suite)

يحتوي المشروع على حزمة اختبارات مؤتمتة بنسبة تغطية 100% لجميع المسارات والحالات الحرجة، وتعمل على قاعدة بيانات SQLite معزولة بالكامل في الذاكرة:

```bash
# تشغيل كامل الاختبارات
uv run pytest -v
```

المخرجات المتوقعة:
```text
tests\test_audit_db_disabled.py .
tests\test_audit_logging.py ...
tests\test_auth_flow.py .
tests\test_health.py .
tests\test_pagination_edges.py ..
tests\test_security.py ....
tests\test_user_crud.py .
tests\test_user_rbac.py .
tests\test_validation_envelope.py ...

============================= 17 passed in 7.93s ==============================
```

للمزيد من التفاصيل حول سيناريوهات الاختبار، راجع:
- [`tests/README_AR.md`](tests/README_AR.md)

---

## 🛠 دليل المطور: كيفية إضافة نطاق جديد للمشروع

لإضافة نطاق جديد (مثال: المنتجات `products`) اتبع الخطوات الخمس التالية:

### الخطوة 1: إنشاء مجلد النطاق
```bash
mkdir src/modules/products
```

### الخطوة 2: إنشاء نموذج قاعدة البيانات (`model.py`)
```python
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from src.database.base import BaseModel
from src.database.mixin import DateTimeMixin

class Product(BaseModel, DateTimeMixin):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
```

### الخطوة 3: إنشاء المستودع والمخططات (`repo.py` و `schemas.py`)
* ابنِ مخططات Pydantic للإدخال والإخراج (`ProductCreate`, `ProductResponse`).
* ابنِ المستودع بالوراثة من المستودع العام:
  ```python
  from src.database import BaseRepository
  from .model import Product

  class ProductRepository(BaseRepository[Product]):
      def __init__(self, session):
          super().__init__(class_=Product, session=session)
  ```

### الخطوة 4: كتابة الخدمة والراوتر (`service.py` و `router.py`)
* اربط استدعاءات التدقيق `save_success_event` أو `save_failed_event` عند العمليات الحساسة.
* استقبل `audit_ctx: AuditContext = Depends(get_audit_context)` في الراوتر ومرره للخدمة.

### الخطوة 5: تسجيل الراوتر وإنشاء ملف الهجرة
* أضف الراوتر الجديد في `src/modules/__init__.py`.
* استورد النموذج في `migrations/env.py`.
* نفذ أمر توليد الهجرة وتطبيقها:
  ```bash
  uv run alembic revision --autogenerate -m "add_products_table"
  uv run alembic upgrade head
  ```

---

## 📄 الترخيص
هذا المشروع مفتوح المصدر وموزع تحت رخصة [MIT License](LICENSE).
