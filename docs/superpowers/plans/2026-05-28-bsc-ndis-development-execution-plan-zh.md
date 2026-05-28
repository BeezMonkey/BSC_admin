# Brisbane Star Care NDIS 在线管理系统开发执行计划

> **给 agentic workers:** REQUIRED SUB-SKILL: 使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 按任务逐项执行。本计划使用 checkbox (`- [ ]`) 跟踪进度。

**目标:** 将现有系统规划文档转成可直接执行的开发路线图，并先锁定 Phase 0 的基础建设任务。

**架构:** 采用 Django 单体应用优先，使用 Django Templates 负责页面渲染，HTMX/Alpine.js 只用于轻量交互。先完成稳定的业务链条：Participant -> Worker -> Assignment -> Shift -> Service Log -> Review -> Invoice，再考虑自动化、第三方集成和复杂界面。

**技术栈:** Django, Django Templates, SQLite 本地开发, PostgreSQL 生产准备, HTMX, Alpine.js, Tailwind CSS 或 clean CSS。

---

## 一、总体结论

这套系统的第一版不应从漂亮 dashboard、拖拽日历、Xero、PRODA 或 mobile app 开始。第一版的真正价值是让内部运营链条跑通：

```text
Create Participant
-> Create Worker
-> Assign Worker
-> Create Shift
-> Worker Confirm
-> Worker Complete Service Log
-> Admin Approve
-> Create Invoice
```

只要这条线稳定，系统就已经能替代大量 Excel、微信、纸质记录和人工追踪。其他功能应围绕这条线逐步加。

---

## 二、范围边界

### v1 必须包含

- 登录、登出、角色跳转。
- Super Admin、Admin、Support Worker、Accountant 四类角色。
- Participant 管理。
- Support Worker 管理。
- Participant-Worker assignment。
- Support item 管理。
- 基础排班和 roster。
- Worker 查看自己的 shift，并确认 shift。
- Worker 从 shift 完成 service log。
- Admin 审核、批准、拒绝 service log。
- 从 approved service logs 创建 invoice。
- PDF/CSV 导出。
- 文件上传和基础 documents 管理。
- 基础 audit log、安全配置和部署准备。

### v1 暂不做

- 拖拽式复杂 calendar。
- 自动智能排班。
- GPS check-in/check-out。
- 原生 mobile app。
- 复杂 payroll/award 计算。
- Xero API 自动同步。
- PRODA 自动 claim。
- Participant/family portal。
- 复杂 NDIS budget forecast。
- SMS/push notification automation。

---

## 三、已发现的规划修正点

- [ ] **修正 1: scheduling app 创建阶段统一**

当前文档在 Phase 0 和 Phase 6 都提到 scheduling app。建议 Phase 0 只创建 app skeleton，Phase 6 再实现 Shift model、views、forms、templates 和业务逻辑。

- [ ] **修正 2: manual service log 默认关闭**

`/sw/logs/new/` 应作为可配置功能。v1 默认关闭，只有 Super Admin 在 settings 中启用后，worker 才能提交 unrostered manual log。

- [ ] **修正 3: invoice 后锁定 service log**

ServiceLog 一旦进入 `invoiced` 状态，普通 admin 不允许直接编辑核心字段。更正应通过 audit trail、void/reissue invoice 或 credit note 流程处理。

- [ ] **修正 4: support item 历史价格保存**

InvoiceLine 必须保存生成当时的 item number、description、unit price、quantity、GST、line total。不要只依赖当前 SupportItem 价格。

- [ ] **修正 5: draft shift 是否参与冲突检查需明确**

建议 v1 中 `draft` 也参与 worker conflict check，原因是 draft 常用于内部预排；否则同一 worker 可能被多个草稿占用。若业务希望草稿不占用 worker，应增加 setting 控制。

---

## 四、推荐项目结构

Phase 0 建议创建以下结构：

```text
bscare_ndis/
  manage.py
  requirements.txt
  README.md
  .env.example
  bscare_ndis/
    __init__.py
    settings.py
    urls.py
    wsgi.py
    asgi.py
  accounts/
    models.py
    views.py
    urls.py
    admin.py
    decorators.py
  core/
    views.py
    urls.py
  participants/
  workers/
  scheduling/
  service_logs/
  invoices/
  documents/
  templates/
    base.html
    admin_base.html
    worker_base.html
    accounts/login.html
    core/admin_dashboard.html
    core/worker_dashboard.html
    invoices/invoice_placeholder.html
  static/
    css/app.css
  media/
```

---

## 五、开发阶段路线图

### Phase 0: Project Setup

**目标:** 创建 Django 项目基础、登录登出、角色跳转和 placeholder dashboards。

**完成标准:**
- 本地项目可以运行。
- Django Admin 可以访问。
- UserProfile 有四类角色。
- 登录后按角色跳转。
- 未登录访问业务页面会跳转到 login。
- Worker 不能访问 admin dashboard。
- Admin 不能访问 worker dashboard。

### Phase 1: User Role and Permission

**目标:** 固化权限装饰器、角色判断、通用 access rules。

**完成标准:**
- Support Worker 只能访问 `/sw/*`。
- Admin/Super Admin 可以访问 admin operation pages。
- Accountant 只能访问 invoice/export 相关页面。
- 所有页面有明确 permission check。

### Phase 2: Participant Management

**目标:** Participant CRUD、列表、过滤、详情页。

**完成标准:**
- Admin 可以创建、编辑、搜索、归档 participant。
- Worker 看不到 NDIS number、plan manager、funding、internal notes。
- Participant detail 有 roster/logs/invoices/documents/assigned workers tabs。

### Phase 3: Support Worker Management

**目标:** Worker profile、登录账号、合规信息。

**完成标准:**
- Admin 创建 worker 时同步创建 Django User。
- Worker 可以登录。
- Worker profile 和 UserProfile 正确关联。
- Expired compliance document 显示 warning。

### Phase 4: Assignment

**目标:** 绑定 participant 和 worker。

**完成标准:**
- 同一 participant + worker 不能有重复 active assignment。
- End assignment 不删除历史 shift/log/invoice。
- Worker 只能基于 assigned participant 获得访问或提交权限。

### Phase 5: Support Item Management

**目标:** 管理 NDIS support items。

**完成标准:**
- Admin 可以维护 item number、name、category、unit、price、GST。
- 只有 active support items 出现在 shift/log/invoice form。
- 系统不自动编造真实 NDIS item number。

### Phase 6: Basic Scheduling

**目标:** 实现 Shift model、roster list、create/edit/detail、worker my shifts、confirm shift。

**完成标准:**
- Admin 可以创建 draft shift。
- Admin 可以 publish shift。
- Worker 只能看到自己的 published/confirmed shifts。
- Worker 可以 confirm published shift。
- Worker overlapping active shift 被阻止。
- Shift list filters 可用。

### Phase 7: Complete Shift to Service Log

**目标:** Worker 从 shift 完成并提交 service log。

**完成标准:**
- Worker 只能 complete 自己的 shift。
- 一个 shift 只能生成一个 service log。
- ServiceLog 创建后状态为 `submitted`。
- Shift 状态变为 `completed`，并写入 `completed_at`。
- Admin 可以看到 shift 和 service log 的关联。

### Phase 8: Admin Service Log Review

**目标:** Admin 审核 service logs。

**完成标准:**
- Submitted logs 可以 approve/reject。
- Reject 必须填写 reason。
- Worker 可以看到 rejection reason。
- Approved logs 才能进入 invoice。

### Phase 9: Invoice Generation

**目标:** 从 approved not-invoiced service logs 创建 invoice。

**完成标准:**
- Create invoice 页面按 participant 和 period 加载 logs。
- 只能加载 approved 且未 invoiced 的 logs。
- InvoiceLine 保存历史单价和描述。
- 创建 invoice 后相关 logs 状态变为 `invoiced`。

### Phase 10: Invoice PDF/CSV Export

**目标:** 生成 invoice PDF/CSV 并跟踪 sent/paid/cancelled 状态。

**完成标准:**
- Invoice detail 可下载 PDF。
- Invoice list/export 可下载 CSV。
- Payment status 可更新。
- Invoiced logs 不可直接修改核心字段。

### Phase 11: Recurring Shifts

**目标:** 简单 weekly/fortnightly repeated shifts。

**完成标准:**
- 创建前必须 preview。
- Worker conflicts 被 skip。
- 创建后显示 created count 和 skipped count。

### Phase 12: Documents and Hardening

**目标:** 文件上传、移动端 polish、安全、审计、生产配置。

**完成标准:**
- 文件可关联 participant/worker/invoice/service log。
- 文件权限遵守角色和对象权限。
- `.env` 管理 secrets。
- PostgreSQL-ready。
- Media backup 策略明确。
- AuditLog 覆盖 approve/reject/cancel/invoice/delete 等关键操作。

---

## 六、Phase 0 详细任务单

### Task 0.1: 创建项目环境

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `README.md`

- [ ] **Step 1: 创建 requirements.txt**

```text
Django>=5.0,<6.0
python-dotenv>=1.0,<2.0
Pillow>=10.0,<12.0
```

- [ ] **Step 2: 创建 Django 项目**

Run:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
django-admin startproject bscare_ndis .
```

Expected:

```text
manage.py exists
bscare_ndis/settings.py exists
```

- [ ] **Step 3: 创建 apps**

Run:

```bash
python manage.py startapp accounts
python manage.py startapp core
python manage.py startapp participants
python manage.py startapp workers
python manage.py startapp scheduling
python manage.py startapp service_logs
python manage.py startapp invoices
python manage.py startapp documents
```

Expected: 每个 app 文件夹存在，并包含 `models.py`, `views.py`, `admin.py`, `apps.py`。

### Task 0.2: 配置 settings

**Files:**
- Modify: `bscare_ndis/settings.py`
- Create: `templates/`
- Create: `static/css/app.css`
- Create: `media/`

- [ ] **Step 1: 加入 apps**

在 `INSTALLED_APPS` 中加入：

```python
"accounts",
"core",
"participants",
"workers",
"scheduling",
"service_logs",
"invoices",
"documents",
```

- [ ] **Step 2: 配置 templates/static/media**

确保 `DIRS` 指向 `BASE_DIR / "templates"`，并增加：

```python
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "role_redirect"
LOGOUT_REDIRECT_URL = "login"
```

### Task 0.3: UserProfile 和角色

**Files:**
- Modify: `accounts/models.py`
- Modify: `accounts/admin.py`

- [ ] **Step 1: 创建 UserProfile model**

```python
from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    class Role(models.TextChoices):
        SUPER_ADMIN = "super_admin", "Super Admin"
        ADMIN = "admin", "Admin"
        SUPPORT_WORKER = "support_worker", "Support Worker"
        ACCOUNTANT = "accountant", "Accountant"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=30, choices=Role.choices)
    phone = models.CharField(max_length=30, blank=True)
    is_active_worker = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.role}"
```

- [ ] **Step 2: 注册 admin**

```python
from django.contrib import admin
from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "phone", "is_active_worker", "created_at")
    list_filter = ("role", "is_active_worker")
    search_fields = ("user__username", "user__email", "phone")
```

- [ ] **Step 3: 运行 migration**

Run:

```bash
python manage.py makemigrations
python manage.py migrate
```

Expected: migrations 成功，无错误。

### Task 0.4: 登录、登出和角色跳转

**Files:**
- Create: `accounts/views.py`
- Create: `accounts/urls.py`
- Modify: `bscare_ndis/urls.py`
- Create: `templates/accounts/login.html`

- [ ] **Step 1: 创建 role_redirect view**

```python
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required


class BSCLoginView(LoginView):
    template_name = "accounts/login.html"


class BSCLogoutView(LogoutView):
    pass


@login_required
def role_redirect(request):
    profile = getattr(request.user, "userprofile", None)
    if profile is None:
        return redirect("login")
    if profile.role in ["super_admin", "admin"]:
        return redirect("admin_dashboard")
    if profile.role == "support_worker":
        return redirect("worker_dashboard")
    if profile.role == "accountant":
        return redirect("invoice_placeholder")
    return redirect("login")
```

- [ ] **Step 2: 创建 accounts urls**

```python
from django.urls import path
from .views import BSCLoginView, BSCLogoutView, role_redirect

urlpatterns = [
    path("login/", BSCLoginView.as_view(), name="login"),
    path("logout/", BSCLogoutView.as_view(), name="logout"),
    path("role-redirect/", role_redirect, name="role_redirect"),
]
```

### Task 0.5: 基础页面和权限

**Files:**
- Create: `accounts/decorators.py`
- Create: `core/views.py`
- Create: `core/urls.py`
- Create: `invoices/views.py`
- Create: `invoices/urls.py`
- Create: `templates/base.html`
- Create: `templates/admin_base.html`
- Create: `templates/worker_base.html`
- Create: `templates/core/admin_dashboard.html`
- Create: `templates/core/worker_dashboard.html`
- Create: `templates/invoices/invoice_placeholder.html`

- [ ] **Step 1: 创建角色装饰器**

```python
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            profile = getattr(request.user, "userprofile", None)
            if profile is None or profile.role not in roles:
                raise PermissionDenied
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
```

- [ ] **Step 2: 创建 placeholder views**

```python
from django.shortcuts import render
from accounts.decorators import role_required


@role_required("super_admin", "admin")
def admin_dashboard(request):
    return render(request, "core/admin_dashboard.html")


@role_required("support_worker")
def worker_dashboard(request):
    return render(request, "core/worker_dashboard.html")
```

Invoice placeholder:

```python
from django.shortcuts import render
from accounts.decorators import role_required


@role_required("super_admin", "admin", "accountant")
def invoice_placeholder(request):
    return render(request, "invoices/invoice_placeholder.html")
```

### Task 0.6: Phase 0 验收测试

- [ ] **Step 1: 创建 superuser**

Run:

```bash
python manage.py createsuperuser
```

- [ ] **Step 2: 给 superuser 创建 UserProfile**

在 Django Admin 中创建：

```text
user = created superuser
role = super_admin
```

- [ ] **Step 3: 手动测试**

Run:

```bash
python manage.py runserver
```

Manual checks:

```text
Open http://127.0.0.1:8000/login/
Login as super_admin -> redirects to /admin-dashboard/
Open /sw/dashboard/ as super_admin -> PermissionDenied
Create support_worker user and profile
Login as support_worker -> redirects to /sw/dashboard/
Open /admin-dashboard/ as support_worker -> PermissionDenied
Create accountant user and profile
Login as accountant -> redirects to /invoices/
```

---

## 七、安全、隐私和审计清单

- [ ] Worker querysets 必须始终按当前 worker profile 过滤。
- [ ] Worker 页面不得显示 participant NDIS number、funding、plan manager、invoice、internal notes。
- [ ] 所有 approve/reject/cancel/invoice/delete 操作写入 AuditLog。
- [ ] 文件上传必须限制类型和大小。
- [ ] 文件访问必须检查对象权限，不允许通过 URL 猜测下载。
- [ ] `.env` 保存 secret key、database URL、allowed hosts。
- [ ] 生产环境关闭 `DEBUG`。
- [ ] 数据库和 media 文件必须有备份策略。
- [ ] Invoiced logs 不允许普通编辑。
- [ ] 导出功能按角色限制字段。

---

## 八、建议执行方式

Plan complete and saved to `docs/superpowers/plans/2026-05-28-bsc-ndis-development-execution-plan-zh.md`.

两个执行选项：

**1. Subagent-Driven（推荐）** - 每个 phase 分给一个新 agent，主会话负责 review 和整合。

**2. Inline Execution** - 在当前会话中按 phase 执行，每完成一个 phase 做一次 checkpoint。

建议从 **Phase 0 Inline Execution** 开始，因为当前项目还没有代码，先把基础项目结构跑通最重要。
