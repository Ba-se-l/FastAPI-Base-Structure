# 🗄️ دليل البنية التحتية لترحيل قواعد البيانات ومرجع أوامر Alembic CLI

يحتوي هذا المجلد على ملفات ترحيل مخطط قواعد البيانات (Database Schema Migrations) وإعدادات بيئة التشغيل المدارة بواسطة **Alembic** و **SQLAlchemy 2.0 (Async)**. يمثل هذا المجلد المرجع الوحيد والمطلق لمتابعة التطور الهيكلي لجداول وقواعد بيانات المشروع.

---

## 📑 فهرس المحتويات

1. [المعمارية والمبادئ الهندسية الأساسية](#1-المعمارية-والمبادئ-الهندسية-الأساسية)
2. [دليل إعداد المطور لأول مرة (من الصفر إلى تشغيل القاعدة)](#2-دليل-إعداد-المطور-لأول-مرة-من-الصفر-إلى-تشغيل-القاعدة)
3. [المرجع الشامل لأوامر Alembic CLI الأساسية](#3-المرجع-الشامل-لأوامر-alembic-cli-الأساسية)
   - [`upgrade head`](#alembic-upgrade-head--تطبيق-كافة-الترحيلات-المعلقة)
   - [`downgrade`](#alembic-downgrade--التراجع-عن-الترحيلات)
   - [`revision --autogenerate`](#alembic-revision---autogenerate--توليد-ملفات-ترحيل-تلقائية)
   - [`check`](#alembic-check--فحص-تزامن-المخططات)
   - [`current`](#alembic-current--عرض-الإصدار-الحالي-المطبق)
   - [`history`](#alembic-history--عرض-السجل-الزمني-للترحيلات)
   - [`heads`](#alembic-heads--فحص-رؤوس-الفروع-المتشعبة)
   - [`merge`](#alembic-merge--دمج-الفروع-المتعارضة)
   - [`stamp`](#alembic-stamp--إعادة-محاذاة-حالة-القاعدة-دون-تنفيذ)
4. [التشريح المعماري للبيئة غير المتزامنة (`migrations/env.py`)](#4-التشريح-المعماري-للبيئة-غير-المتزامنة-migrationsenvpy)
   - [الربط الديناميكي مع الإعدادات ومجمع الاتصال](#الربط-الديناميكي-مع-الإعدادات-ومجمع-الاتصال)
   - [تسجيل المخططات المستهدفة (Target Metadata)](#تسجيل-المخططات-المستهدفة-target-metadata)
   - [معايير تسمية القيود الصارمة (Naming Conventions)](#معايير-تسمية-القيود-الصارمة-naming-conventions)
   - [وضع الدفعات لـ SQLite (`render_as_batch=True`)](#وضع-الدفعات-لـ-sqlite-render_as_batchtrue)
5. [مسارات عمل المطور خطوة بخطوة](#5-مسارات-عمل-المطور-خطوة-بخطوة)
   - [المسار أ: إضافة عمود جديد إلى جدول قائم](#المسار-أ-إضافة-عمود-جديد-إلى-جدول-قائم)
   - [المسار ب: إنشاء موديول ونموذج جدول جديد بالكامل](#المسار-ب-إنشاء-موديول-ونموذج-جدول-جديد-بالكامل)
   - [المسار ج: كتابة ترحيل بيانات مخصص (Data Migration)](#المسار-ج-كتابة-ترحيل-بيانات-مخصص-data-migration)
6. [استكشاف الأخطاء الشائعة وحلولها](#6-استكشاف-الأخطاء-الشائعة-وحولها)

---

## 1. المعمارية والمبادئ الهندسية الأساسية

في تطبيقات الخوادم الإنتاجية الضخمة، يُعد استدعاء `BaseModel.metadata.create_all()` عند إقلاع الخادم **ممارسة معمارية خاطئة (Anti-Pattern)** لعدة أسباب حتمية:
* دالة `create_all()` تقوم فقط بإنشاء الجداول **غير الموجودة مسبقاً**؛ ولا تستطيع إطلاقاً تعديل أعمدة قائمة، أو حذف فهارس مهملة، أو تغيير أنواع البيانات، أو فرض قيود جديدة.
* تصبح التغييرات على قاعدة البيانات غير موثقة، وغير قابلة للاسترجاع (Irreversible)، مما يسبب كابوس تباين البيانات بين أجهزة المطورين وبيئات الاختبار والإنتاج ("It works on my machine").

### كيف يحل Alembic هذه المشكلة في هذا المشروع؟
1. **التحكم بالإصدارات لـ DDL:** كل تعديل هيكلي يُكتب داخل ملف بايثون مؤرخ ومفهرس برمز تجزئة (Hash) فريد في مجلد `migrations/versions/`.
2. **قابلية التراجع التام (Reversibility):** كل ترحيل يحوي دالتين: `upgrade()` لتطبيق التغيير للأمام، و `downgrade()` للتراجع عن التغيير بأمان تام.
3. **دعم كامل للعمليات غير المتزامنة (100% Async Native):** مهيأ عبر `async_engine_from_config` ليتوافق بسلاسة مع `aiosqlite` (الافتراضي للتطوير) و `asyncpg` (لقواعد بيانات PostgreSQL في الإنتاج).
4. **ربط ديناميكي بدون تكرار إعدادات:** لا يتم كتابة رابط قاعدة البيانات نهائياً في `alembic.ini`، بل يتم حقنه برمجياً من إعدادات المشروع [src.settings.settings.database_url](file:///d:/_Python%20Projects-27-05-2026/fastapi-base-structure-dev/src/settings/settings.py).

---

## 2. دليل إعداد المطور لأول مرة (من الصفر إلى تشغيل القاعدة)

عند استنساخ هذا المشروع (Clone) لأول مرة على جهاز جديد، لن يكون ملف قاعدة البيانات موجوداً. اتبع الخطوات الثلاث التالية لتهيئة كل شيء بنجاح:

### الخطوة 1: التأكد من تثبيت الحزم وتفعيل البيئة الافتراضية
```bash
uv sync
```

### الخطوة 2: إنشاء ملف الإعدادات
انسخ ملف الإعدادات النموذجي:
```bash
cp .env.example .env
```
تأكد من وجود متغير `DATABASE_URL` (افتراضياً: `sqlite+aiosqlite:///./database.db`).

### الخطوة 3: تطبيق كافة الترحيلات السابقة
نفّذ أمر الترقية الشامل لتطبيق جميع ملفات الهجرة المتوفرة حتى أحدث إصدار:
```bash
uv run alembic upgrade head
```

**المخرجات المتوقعة في الطرفية:**
```text
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 023d924aba69, initial_schema
```

### الخطوة 4: التحقق من إصدار القاعدة الحالي
```bash
uv run alembic current
```
**المخرج المتوقع:**
```text
023d924aba69 (head)
```

أصبحت قاعدة بياناتك الآن مهيأة بالكامل وتحتوي على جميع الجداول الأساسية (`users`, `refresh_sessions`, `audit_logs`) والفهارس والقيود.

---

## 3. المرجع الشامل لأوامر Alembic CLI الأساسية

يجب تشغيل جميع أوامر Alembic دائماً عبر مدير الحزم الخاص بالمشروع (`uv run alembic <command>`).

---

### `alembic upgrade head` — تطبيق كافة الترحيلات المعلقة
يقوم بقراءة شجرة الترحيلات وتطبيق أي ملفات لم تُطبق بعد على قاعدة البيانات حتى أحدث إصدار (`head`).
```bash
uv run alembic upgrade head
```
* **متى يُستخدم؟** عند إعداد المشروع لأول مرة، أو بعد سحب كود جديد (`git pull`)، أو في مرحلة التوزيع الحي (Deployment).
* **تطبيق ترحيل محدد برمز الإصدار:**
  ```bash
  uv run alembic upgrade 023d924aba69
  ```

---

### `alembic downgrade` — التراجع عن الترحيلات
إلغاء التغييرات الهيكلية والرجوع خطوة أو خطوات إلى الوراء بأمان عبر استدعاء دوال `downgrade()`.

* **التراجع عن آخر ترحيل منفذ فقط (خطوة واحدة للخلف):**
  ```bash
  uv run alembic downgrade -1
  ```
* **التراجع عن جميع الترحيلات بالكامل (تفريغ القاعدة تماماً):**
  ```bash
  uv run alembic downgrade base
  ```
* **التراجع إلى إصدار محدد مسبقاً:**
  ```bash
  uv run alembic downgrade <revision_id>
  ```
* **متى يُستخدم؟** عند اختبار سلامة التراجع عن المخطط، أو عند ارتكاب خطأ أثناء التطوير المحلي والرغبة في إعادة صياغة الترحيل.

---

### `alembic revision --autogenerate` — توليد ملفات ترحيل تلقائية
يقوم بمقارنة نماذج SQLAlchemy (`BaseModel.metadata`) مع الحالة الفعلية للجداول في قاعدة البيانات المتصلة، ويولد كود DDL يمثل الفارق الدقيق.
```bash
uv run alembic revision --autogenerate -m "add_phone_number_to_users"
```
* **متى يُستخدم؟** فور الانتهاء من إضافة أو تعديل أو حذف أي حقول أو علاقات داخل نماذج الـ ORM.
* **النتيجة:** إنشاء ملف بايثون جديد داخل مجلد `migrations/versions/`.

> [!IMPORTANT]
> **مراجعة الكود المتولد إلزامية دائماً!** على الرغم من دقة Alembic العالية، يجب فتح الملف والتأكد من ملاءمته للغرض المعماري (خصوصاً عند تغيير أسماء الأعمدة أو جعلها إجبارية وغير فارغة).

---

### `alembic check` — فحص تزامن المخططات
يفحص ما إذا كانت النماذج البرمجية مطابقة بنسبة 100% للجداول الفعلية في قاعدة البيانات.
```bash
uv run alembic check
```
* **في حالة التزامن التام:** يطبع `No new upgrade operations detected.` ويخرج بكود نجاح `0`.
* **في حالة وجود تعديلات لم تُرحل:** يطبع الفروقات ويخرج بكود خطأ `11`.
* **متى يُستخدم؟** يُوضع في أنابيب الفحص المؤتمت (CI/CD) لمنع دمج أي Pull Request قام المطور فيه بتعديل نماذج ORM ونسي توليد وتضمين ملف الترحيل.

---

### `alembic current` — عرض الإصدار الحالي المطبق
يطبع رمز التجزئة (Hash) للترحيل المطبق حالياً على قاعدة البيانات النشطة.
```bash
uv run alembic current
```
* **الوضع المفصل:**
  ```bash
  uv run alembic current -v
  ```

---

### `alembic history` — عرض السجل الزمني للترحيلات
يعرض قائمة زمنية بجميع الترحيلات الموجودة في المستودع وترتيب تسلسلها.
```bash
uv run alembic history --verbose
```
* يوضح: رمز التجزئة، الترحيل الأب السابق، التاريخ، ووصف التعديل.

---

### `alembic heads` — فحص رؤوس الفروع المتشعبة
يعرض أحدث ترحيل على كل فرع.
```bash
uv run alembic heads
```
* في الحالة السليمة، يجب أن يظهر إصدار واحد فقط ينتهي بكلمة `(head)`.
* إذا قام مطوران بإنشاء ترحيلين في نفس الوقت على فرعين منفصلين في Git، سيظهر رأسان (`two heads`)، مما يعني ضرورة إجراء دمج.

---

### `alembic merge` — دمج الفروع المتعارضة
يقوم بدمج ترحيلين منفصلين لتوحيد شجرة الترحيلات في رأس واحد متصل.
```bash
uv run alembic merge -m "merge_user_and_order_branches" <rev1> <rev2>
```

---

### `alembic stamp` — إعادة محاذاة حالة القاعدة دون تنفيذ
يقوم بتحديث جدول المتابعة الداخلي `alembic_version` برمز ترحيل محدد **دون تشغيل أي كود SQL أو DDL**.
```bash
uv run alembic stamp head
```
* **متى يُستخدم؟** عند ربط Alembic بقاعدة بيانات قديمة تم إنشاؤها مسبقاً يدوياً بدون ترحيلات، أو عند إصلاح حالات التعارض يدوياً.

---

## 4. التشريح المعماري للبيئة غير المتزامنة (`migrations/env.py`)

الملف الحاكم لعملية الترحيل بأكملها هو [`migrations/env.py`](file:///d:/_Python%20Projects-27-05-2026/fastapi-base-structure-dev/migrations/env.py). وإليك تفاصيل تصميمه:

### الربط الديناميكي مع الإعدادات ومجمع الاتصال
بدلاً من تثبيت بيانات الاتصال يدوياً، يقرأ الملف الرابط من كائن الإعدادات الموحد:
```python
from src.settings import settings

# مزامنة رابط قاعدة البيانات برمجياً مع إعدادات المشروع
config.set_main_option("sqlalchemy.url", settings.database_url)
```
يضمن ذلك التوافق التلقائي مع أي تغيير في ملف `.env` بين بيئات التطوير والاختبار والإنتاج.

### تسجيل المخططات المستهدفة (Target Metadata)
حتى تكتشف ميزة `--autogenerate` النماذج الجديدة، **يجب** استيراد كلاسات النماذج داخل `env.py`:
```python
from src.database.base import BaseModel
from src.modules.user.model import User           # noqa: F401
from src.modules.auth.model import RefreshSession # noqa: F401
from src.modules.audit.model import AuditLog      # noqa: F401

target_metadata = BaseModel.metadata
```

> [!WARNING]
> إذا أنشأت موديولاً جديداً أو جدولاً جديداً ونسيت استيراد النموذج داخل `migrations/env.py`، فلن يكتشف Alembic الجدول الجديد إطلاقاً أثناء التوليد التلقائي!

### معايير تسمية القيود الصارمة (Naming Conventions)
يحتاج Alembic إلى أسماء قيود وفهارس واضحة وثابتة ليتمكن من حذفها أو تعديلها مستقبلاً بدون أخطاء. في ملف [`src/database/base.py`](file:///d:/_Python%20Projects-27-05-2026/fastapi-base-structure-dev/src/database/base.py)، تم تزويد `BaseModel` بهذه المعايير:
```python
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
```

### وضع الدفعات لـ SQLite (`render_as_batch=True`)
محرك SQLite لا يدعم أوامر `ALTER TABLE DROP COLUMN` أو تغيير القيود المباشرة في SQL. يحل Alembic هذا العائق عبر **وضع الدفعات (Batch Mode)** الذي يقوم تلقائياً بـ:
1. إنشاء جدول مؤقت بالمخطط الجديد.
2. نسخ كافة البيانات الحالية إليه.
3. حذف الجدول القديم.
4. إعادة تسمية الجدول المؤقت إلى الاسم الأصلي.

تم تفعيل هذا الخيار افتراضياً داخل `migrations/env.py`:
```python
context.configure(
    connection=connection,
    target_metadata=target_metadata,
    render_as_batch=True,  # ضروري لتوافقية SQLite
)
```

---

## 5. مسارات عمل المطور خطوة بخطوة

### المسار أ: إضافة عمود جديد إلى جدول قائم

1. **تعديل نموذج الـ ORM:**
   افتح ملف `src/modules/user/model.py` وأضف العمود:
   ```python
   phone_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
   ```

2. **توليد ملف الترحيل:**
   ```bash
   uv run alembic revision --autogenerate -m "add_phone_number_to_user"
   ```

3. **معاينة الملف المتولد:**
   افتح الملف الجديد داخل `migrations/versions/` وتأكد من الدالتين:
   ```python
   def upgrade() -> None:
       with op.batch_alter_table('users', schema=None) as batch_op:
           batch_op.add_column(sa.Column('phone_number', sa.String(length=20), nullable=True))

   def downgrade() -> None:
       with op.batch_alter_table('users', schema=None) as batch_op:
           batch_op.drop_column('phone_number')
   ```

4. **تطبيق الترحيل على القاعدة:**
   ```bash
   uv run alembic upgrade head
   ```

5. **فحص التزامن:**
   ```bash
   uv run alembic check
   ```

---

### المسار ب: إنشاء موديول ونموذج جدول جديد بالكامل

1. **إنشاء النموذج:**
   أنشئ ملف `src/modules/billing/model.py`:
   ```python
   from sqlalchemy import String, Numeric
   from sqlalchemy.orm import Mapped, mapped_column
   from src.database.base import BaseModel
   from src.database.mixin import DateTimeMixin

   class Invoice(BaseModel, DateTimeMixin):
       __tablename__ = "invoices"

       id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
       amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
   ```

2. **تسجيل النموذج في `migrations/env.py`:**
   أضف سطر الاستيراد:
   ```python
   from src.modules.billing.model import Invoice  # noqa: F401
   ```

3. **التوليد والتطبيق:**
   ```bash
   uv run alembic revision --autogenerate -m "create_invoices_table"
   uv run alembic upgrade head
   ```

---

### المسار ج: كتابة ترحيل بيانات مخصص (Data Migration)

إذا كنت بحاجة إلى تحديث بيانات موجودة أو ملء حقول جديدة ببيانات افتراضية:

1. **إنشاء ملف ترحيل فارغ:**
   ```bash
   uv run alembic revision -m "seed_initial_roles"
   ```

2. **كتابة منطق التعديل في `upgrade()`:**
   ```python
   from alembic import op
   import sqlalchemy as sa

   def upgrade() -> None:
       # تنفيذ كود SQL صريح لتعديل البيانات
       op.execute("UPDATE users SET is_active = 1 WHERE is_active IS NULL")

   def downgrade() -> None:
       pass
   ```

3. **التطبيق:**
   ```bash
   uv run alembic upgrade head
   ```

---

## 6. استكشاف الأخطاء الشائعة وحلولها

### الخطأ 1: "Target database is not up to date"
* **المشكلة:** قاعدة البيانات الحالية متأخرة عن شجرة الترحيلات ولا تحتوي على آخر تعديل.
* **الحل:** نفّذ `uv run alembic upgrade head` قبل محاولة توليد أي ترحيلات جديدة.

### الخطأ 2: التوليد التلقائي لم يرصد الجداول الجديدة
* **المشكلة:** نسيت استيراد نموذج الجدول الجديد داخل `migrations/env.py`.
* **الحل:** أضف استيراد النموذج الصريح في `migrations/env.py` وأعد تشغيل أمر `--autogenerate`.

### الخطأ 3: تعارض الرؤوس المتعددة (`MultipleHeadException`)
* **المشكلة:** وجود ملفين يحملان نفس الأب السابق بسبب العمل المتوازي على فروع Git.
* **الحل:** ادمج الفرعين عبر:
  ```bash
  uv run alembic merge -m "resolve_conflicts" head1 head2
  uv run alembic upgrade head
  ```

### الخطأ 4: إضافة عمود `NOT NULL` لجدول يحتوي على بيانات سابقة
* **المشكلة:** في SQLite، إضافة عمود غير فارغ دون قيمة افتراضية يؤدي لفشل العملية: `Cannot add a NOT NULL column with default value NULL`.
* **الحل:** إما جعل الحقل يقبل الفراغ مؤقتاً (`nullable=True`)، أو تزويده بقيمة افتراضية على مستوى الخادم:
  ```python
  status: Mapped[str] = mapped_column(String(50), nullable=False, server_default="active")
  ```
