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
7. [دليل تصفير وإخماد قاعدة البيانات تماماً (Database Reset & Data Purging)](#7-دليل-تصفير-وإخماد-قاعدة-البيانات-تماما-database-reset--data-purging)
   - [الخيار الأول: التراجع المعماري الكامل وإعادة البناء عبر Alembic (الموصى به)](#الخيار-الأول-التراجع-المعماري-الكامل-وإعادة-البناء-عبر-alembic-الموصى-به)
   - [الخيار الثاني: الحذف الفيزيائي الفوري لملف قاعدة البيانات (بيئة التطوير SQLite)](#الخيار-الثاني-الحذف-الفيزيائي-الفوري-لملف-قاعدة-البيانات-بيئة-التطوير-sqlite)
   - [الخيار الثالث: تصفير وتفريغ البيانات دون هدم الجداول (DML Purging / Truncate)](#الخيار-الثالث-تصفير-وتفريغ-البيانات-دون-هدم-الجداول-dml-purging--truncate)

---

## 1. المعمارية والمبادئ الهندسية الأساسية

في تطبيقات الخوادم الإنتاجية الضخمة، يُعد استدعاء `BaseModel.metadata.create_all()` عند إقلاع الخادم **ممارسة معمارية خاطئة (Anti-Pattern)** لعدة أسباب حتمية:
* دالة `create_all()` تقوم فقط بإنشاء الجداول **غير الموجودة مسبقاً**؛ ولا تستطيع إطلاقاً تعديل أعمدة قائمة، أو حذف فهارس مهملة، أو تغيير أنواع البيانات، أو فرض قيود جديدة.
* تصبح التغييرات على قاعدة البيانات غير موثقة، وغير قابلة للاسترجاع (Irreversible)، مما يسبب كابوس تباين البيانات بين أجهزة المطورين وبيئات الاختبار والإنتاج ("It works on my machine").

### كيف يحل Alembic هذه المشكلة في هذا المشروع؟
1. **التحكم بالإصدارات لـ DDL:** كل تعديل هيكلي يُكتب داخل ملف بايثون مؤرخ ومفهرس برمز تجزئة (Hash) فريد في مجلد `migrations/versions/`.
2. **قابلية التراجع التام (Reversibility):** كل ترحيل يحوي دالتين: `upgrade()` لتطبيق التغيير للأمام، و `downgrade()` للتراجع عن التغيير بأمان تام.
3. **دعم كامل للعمليات غير المتزامنة (100% Async Native):** مهيأ عبر `async_engine_from_config` ليتوافق بسلاسة مع `aiosqlite` (الافتراضي للتطوير) و `asyncpg` (لقواعد بيانات PostgreSQL في الإنتاج).
4. **ربط ديناميكي بدون تكرار إعدادات:** لا يتم كتابة رابط قاعدة البيانات نهائياً في `alembic.ini`، بل يتم حقنه برمجياً من إعدادات المشروع [src.settings.settings.database_url](../src/settings/settings.py).

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
INFO  [alembic.runtime.migration] Running upgrade 023d924aba69 -> bce235971d47, standardize_constraint_naming_conventions
INFO  [alembic.runtime.migration] Running upgrade bce235971d47 -> 1481b1cdf6a4, add_casbin_rule_table
INFO  [alembic.runtime.migration] Running upgrade 1481b1cdf6a4 -> f2001b0d2995, audit_log_limits_and_multi_sink
INFO  [alembic.runtime.migration] Running upgrade f2001b0d2995 -> 6aa8f9bfed61, fix_legacy_family_id_and_bump_security_version
```

### الخطوة 4: التحقق من إصدار القاعدة الحالي
```bash
uv run alembic current
```
**المخرج المتوقع:**
```text
6aa8f9bfed61 (head)
```

أصبحت قاعدة بياناتك الآن مهيأة بالكامل وتحتوي على جميع الجداول الأساسية (`users`, `refresh_sessions`, `audit_logs`, `casbin_rule`) والفهارس والقيود.

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

#### التسلسل الزمني لملفات الهجرة في المستودع

| رمز التجزئة (Revision) | الإصدار الأب (Parent) | الوصف والنطاق المعماري |
| :--- | :--- | :--- |
| `023d924aba69` | *لا يوجد (base)* | المخطط التأسيسي الأولي للجداول (`users`, `refresh_sessions`, `audit_logs`) |
| `bce235971d47` | `023d924aba69` | توحيد وضبط معايير تسمية القيود والفهارس (`ix_`, `uq_`, `ck_`, `fk_`, `pk_`) |
| `1481b1cdf6a4` | `bce235971d47` | إضافة جدول `casbin_rule` لتخزين سياسات وأذونات الصلاحيات الديناميكية |
| `f2001b0d2995` | `1481b1cdf6a4` | تحصين سعة أعمدة سجلات التدقيق وتطوير المصاب المزدوجة |
| `6aa8f9bfed61` | `f2001b0d2995` | **(head)** عزل عائلة الجلسات وتحديث عداد الحماية الأمنية |

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

الملف الحاكم لعملية الترحيل بأكملها هو [`migrations/env.py`](env.py). وإليك تفاصيل تصميمه:

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
يحتاج Alembic إلى أسماء قيود وفهارس واضحة وثابتة ليتمكن من حذفها أو تعديلها مستقبلاً بدون أخطاء. في ملف [`src/database/base.py`](../src/database/base.py)، تم تزويد `BaseModel` بهذه المعايير:
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

---

## 7. دليل تصفير وإخماد قاعدة البيانات تماماً (Database Reset & Data Purging)

في دورة حياة المشروع وبيئات التطوير والاختبار، يحتاج المطور أو مهندس العمليات لتفريغ البيانات أو إعادة تهيئة قاعدة البيانات من الصفر. تتوفر ثلاث استراتيجيات هندسية حسب الهدف والبيئة:

---

### الخيار الأول: التراجع المعماري الكامل وإعادة البناء عبر Alembic (الموصى به)

> [!CAUTION]
> **تحذير: عملية تدميرية للمخطط والبيانات:** يؤدي تنفيذ `alembic downgrade base` إلى التراجع عن كافة الهجرات وإسقاط الجداول والعلاقات والبيانات بالكامل وبشكل لا رجعة فيه. **يُحظر تماماً** تنفيذ هذا الأمر على قواعد بيانات الإنتاج أو البيئات المشتركة دون وجود نسخة احتياطية معزولة ومختبرة مسبقاً.

هذا المسار يعتمد حصراً على محرك ترحيل الإصدارات للتراجع عن كافة الترحيلات إلى نقطة البداية الصفرية (`base`)، ثم إعادة تطبيقها من جديد:

1. **إرجاع كافة الجداول وإلغاء المخططات التراكمية:**
   ```bash
   uv run alembic downgrade base
   ```
   > يقوم هذا الأمر بتنفيذ دوال `downgrade()` بالترتيب العكسي لجميع ملفات الترحيل، مما يسقط كافة الجداول بما فيها `users` و `casbin_rule` ويبقي فقط جدول `alembic_version` فارغاً.

2. **إعادة بناء المخططات بالكامل إلى أحدث إصدار:**
   ```bash
   uv run alembic upgrade head
   ```

3. **(اختياري) بذر البيانات التأسيسية والصلاحيات:**
   ```bash
   uv run python manage.py seed-policies
   ```

---

### الخيار الثاني: الحذف الفيزيائي الفوري لملف قاعدة البيانات (بيئة التطوير SQLite)

> [!CAUTION]
> **إبادة فيزيائية تامة للملف:** يؤدي حذف ملف `database.db` إلى ضياع كافة الهياكل والبيانات فورياً دون أي إمكانية للاسترجاع. هذا الإجراء مخصص حصراً لبيئة التطوير المحلية لجهاز المطور، ويُمنع منعاً باتاً تطبيقه على وحدات التخزين في بيئات الإنتاج أو الخوادم السحابية.

في بيئات التطوير المحلية حيث يُستخدم SQLite كملف محلي (`database.db`)، يمكن إبادة القاعدة وإعادة إنشائها بثوانٍ:

1. **حذف ملف قاعدة البيانات:**
   * **PowerShell (Windows):**
     ```powershell
     Remove-Item -Force database.db -ErrorAction SilentlyContinue
     ```
   * **Bash (Linux / macOS):**
     ```bash
     rm -f database.db
     ```

2. **إعادة بناء الهيكل بالكامل من الصفر عبر Alembic:**
   ```bash
   uv run alembic upgrade head
   ```

3. **التحقق من صحة المخطط التزامني:**
   ```bash
   uv run alembic check
   ```

---

### الخيار الثالث: تصفير وتفريغ البيانات دون هدم الجداول (DML Purging / Truncate)

إذا كنت ترغب في الاحتفاظ بهيكل الجداول والمخطط (Schema) سليماً وتفريغ السجلات والصفوف فقط (مثلاً قبل تشغيل مجموعة اختبارات E2E):

#### أ. عبر أوامر SQL المباشرة:
في قواعد البيانات التي تدعم المفاتيح الأجنبية، يجب مراعاة تعطيل فحص القيود مؤقتاً لتجنب أخطاء `FOREIGN KEY constraint failed`:

* **SQLite:**
  ```sql
  PRAGMA foreign_keys = OFF;
  DELETE FROM casbin_rule;
  DELETE FROM users;
  -- تصفير عدادات الترقيم التلقائي
  DELETE FROM sqlite_sequence WHERE name IN ('users', 'casbin_rule');
  PRAGMA foreign_keys = ON;
  VACUUM;
  ```

* **PostgreSQL:**
  ```sql
  TRUNCATE TABLE casbin_rule, users RESTART IDENTITY CASCADE;
  ```

#### ب. برمجياً عبر بايثون (سكربت سريع لتنظيف الجداول):
يمكنك تنفيذ تنظيف برمجي موحد عبر محرك المشروع غير المتزامن:
```python
import asyncio
from sqlalchemy import text
from src.database.engine import async_engine

async def purge_all_data() -> None:
    async with async_engine.begin() as conn:
        # تعطيل المفاتيح الأجنبية في SQLite
        await conn.execute(text("PRAGMA foreign_keys = OFF;"))
        await conn.execute(text("DELETE FROM casbin_rule;"))
        await conn.execute(text("DELETE FROM users;"))
        await conn.execute(text("PRAGMA foreign_keys = ON;"))
    print("Database data purged successfully.")

if __name__ == "__main__":
    asyncio.run(purge_all_data())
```

